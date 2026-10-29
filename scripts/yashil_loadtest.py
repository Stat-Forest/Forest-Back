#!/usr/bin/env python3
"""
«Яшил маҳалла» yuklama sinovi (TZ §17.3, Q35): N bir vaqtdagi foydalanuvchi, P95 hisoboti.

Tayyorgarlik (test serverda):
    docker exec forest_app python manage.py yashil_seed_load --force --orders 100000 --users 100 \
        --password '<parol>' --tokens-out /app/media/load-tokens.json      # YASHIL_ALLOW_LOAD_SEED=1 bilan
Ishga tushirish (istalgan kompyuterda, faqat `requests` kerak):
    python3 yashil_loadtest.py --base https://test.stat-urmon.uz/api/v1/yashil --tokens load-tokens.json \
        --duration 300 --out natija.json
Tokenlar 15 daqiqa amal qiladi — sinov uzoqroq bo'lsa `yashil_seed_load --tokens-only` bilan yangilang.

Har virtual foydalanuvchi o'z kabinetiga mos so'rovlar yuboradi (ro'yxat → kartochka → reestr → statistika),
so'rovlar orasida `--think` soniya kutadi. Natija: guruhlar bo'yicha so'rovlar soni, xatolar, P50/P95/P99.
Qabul mezoni: «registry» va «card» guruhlarida P95 ≤ `--p95-limit` (standart 3 s).
"""
import argparse
import json
import random
import statistics
import sys
import threading
import time
from collections import defaultdict

import requests

GROUPS_FOR_ACCEPTANCE = ("registry", "card")


class Stats:
    def __init__(self):
        self.lock = threading.Lock()
        self.samples = defaultdict(list)
        self.errors = defaultdict(int)
        self.codes = defaultdict(lambda: defaultdict(int))

    def add(self, group, seconds, code, recording):
        if not recording:
            return
        with self.lock:
            self.samples[group].append(seconds)
            self.codes[group][code] += 1
            if code >= 400 or code == 0:
                self.errors[group] += 1


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    k = max(0, min(len(values) - 1, int(round(p / 100 * len(values) + 0.5)) - 1))
    return values[k]


class VirtualUser(threading.Thread):
    def __init__(self, row, args, stats, stop_at, record_from):
        super().__init__(daemon=True)
        self.row, self.args, self.stats = row, args, stats
        self.stop_at, self.record_from = stop_at, record_from
        self.rnd = random.Random(row["email"])
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {row['token']}", "X-Yashil-Cabinet": row["cabinet"]})
        self.order_ids = []
        self.registry_pages = 1

    def get(self, group, path, params=None):
        url = self.args.base.rstrip("/") + path
        started = time.monotonic()
        try:
            res = self.session.get(url, params=params, timeout=self.args.timeout)
            code = res.status_code
            data = res.json() if code == 200 and "json" in res.headers.get("content-type", "") else None
        except requests.RequestException:
            code, data = 0, None
        self.stats.add(group, time.monotonic() - started, code, time.monotonic() >= self.record_from)
        return data

    def remember(self, data, key="id"):
        rows = (data or {}).get("results") or []
        ids = [r.get(key) for r in rows if r.get(key)]
        if ids:
            self.order_ids = ids[:50]

    def card(self):
        if self.order_ids:
            self.get("card", f"/orders/{self.rnd.choice(self.order_ids)}/")

    def registry(self):
        # Filtrsiz so'rovda ma'lum bo'lgan sahifalar oralig'idan (mavjud bo'lmagan sahifa 404 bo'ladi)
        params = {"page": self.rnd.randint(1, min(5, self.registry_pages))}
        if self.rnd.random() < 0.3:
            params = {"page": 1, "route": self.rnd.choice(["forest", "dm"])}
            if self.rnd.random() < 0.5:
                params["state"] = self.rnd.choice(["execution", "partial", "closed", "supplier_new"])
        data = self.get("registry", "/reports/registry/", params)
        if data and "route" not in params:
            self.registry_pages = max(1, -(-int(data.get("count") or 0) // 50))
        self.remember(data, key="order_id")

    def scenario(self):
        kind = self.row["kind"]
        step = self.rnd.random()
        if kind == "observer":
            if step < 0.45:
                self.registry()
            elif step < 0.6:
                self.get("registry", "/reports/registry/summary/", {"route": self.rnd.choice(["forest", "dm"])})
            elif step < 0.8:
                self.card()
            else:
                self.get("stats", "/stats/cards/")
            return
        if step < 0.35:
            params = {"page": self.rnd.randint(1, 3)}
            if kind == "union" and self.rnd.random() < 0.5:
                params["state"] = "union_new"
            self.remember(self.get("list", "/orders/", params))
        elif step < 0.7:
            self.card()
        elif step < 0.85:
            self.registry()
        elif kind in ("forest", "dm") and step < 0.93:
            self.get("stock", "/stock/")
        else:
            self.get("stats", "/stats/cards/")

    def run(self):
        time.sleep(self.rnd.uniform(0, self.args.ramp))
        self.remember(self.get("list", "/orders/"))
        while time.monotonic() < self.stop_at:
            self.scenario()
            time.sleep(self.args.think * self.rnd.uniform(0.5, 1.5))


def report(stats, args, wall):
    rows, total = [], 0
    for group in sorted(stats.samples):
        s = stats.samples[group]
        total += len(s)
        rows.append({
            "group": group, "requests": len(s), "errors": stats.errors[group],
            "p50": round(statistics.median(s), 3), "p95": round(percentile(s, 95), 3), "p99": round(percentile(s, 99), 3),
            "max": round(max(s), 3), "codes": dict(stats.codes[group]),
        })
    key_rows = [r for r in rows if r["group"] in GROUPS_FOR_ACCEPTANCE]
    errors = sum(r["errors"] for r in rows)
    # Mezon: ikkala guruh o'lchangan, P95 chegarada, xatolar 1% dan oshmaydi
    passed = (len(key_rows) == len(GROUPS_FOR_ACCEPTANCE) and all(r["p95"] <= args.p95_limit for r in key_rows)
              and errors <= 0.01 * max(1, total))
    return {"users": args.users_used, "duration_s": args.duration, "warmup_s": args.warmup, "think_s": args.think,
            "requests": total, "rps": round(total / max(1, wall), 1), "p95_limit_s": args.p95_limit, "passed": passed, "groups": rows}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base", required=True, help="https://<host>/api/v1/yashil")
    p.add_argument("--tokens", required=True, help="yashil_seed_load --tokens-out fayli")
    p.add_argument("--users", type=int, default=100)
    p.add_argument("--duration", type=int, default=300, help="soniya (qizdirish bilan)")
    p.add_argument("--warmup", type=int, default=30, help="hisobga olinmaydigan boshlang'ich soniyalar")
    p.add_argument("--ramp", type=float, default=20, help="foydalanuvchilar shu soniya ichida qo'shiladi")
    p.add_argument("--think", type=float, default=1.0, help="so'rovlar orasidagi o'rtacha pauza, s")
    p.add_argument("--timeout", type=float, default=30)
    p.add_argument("--p95-limit", type=float, default=3.0)
    p.add_argument("--out", default="", help="JSON hisobot fayli")
    args = p.parse_args(argv)

    with open(args.tokens, encoding="utf-8") as fh:
        rows = json.load(fh)
    if not rows:
        sys.exit("tokenlar fayli bo'sh")
    users = [rows[i % len(rows)] for i in range(args.users)]
    args.users_used = len(users)
    stats = Stats()
    start = time.monotonic()
    stop_at, record_from = start + args.duration, start + args.warmup
    threads = [VirtualUser(r, args, stats, stop_at, record_from) for r in users]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=args.duration + args.timeout + 60)
    result = report(stats, args, time.monotonic() - record_from)

    print(f"Foydalanuvchilar: {result['users']}, davomiylik: {args.duration} s (qizdirish {args.warmup} s), "
          f"so'rovlar: {result['requests']}, {result['rps']} so'rov/s")
    print(f"{'guruh':<10}{'so`rov':>8}{'xato':>6}{'P50':>8}{'P95':>8}{'P99':>8}{'max':>8}")
    for r in result["groups"]:
        print(f"{r['group']:<10}{r['requests']:>8}{r['errors']:>6}{r['p50']:>8.3f}{r['p95']:>8.3f}{r['p99']:>8.3f}{r['max']:>8.3f}")
    print(("O'TDI" if result["passed"] else "O'TMADI") + f": registry va card P95 ≤ {args.p95_limit} s, xatolar ≤ 1%")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False, indent=2)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
