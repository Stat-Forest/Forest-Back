# «Яшил маҳалла» модули: жойлаштириш ва тиклаш йўриқномаси

Ҳужжат ТТ §19.1 бўйича топшириладиган «жойлаштириш ва тиклаш йўриқномаси» ҳисобланади. ТТ §16, §17.2, §17.3, §19.2 талабларига таянади.

**Ўқувчилар:** платформа маъмури (серверда буйруқ бажарувчи) ва буюртмачи вакили.
**Ҳолат санаси:** 2026 йил 30 октябрь.

**Белгилар:**

- `<сервер>` — ишчи сервер, `<api-домен>` — API домени, `<тест-сервер>` — синов сервери. Ҳақиқий манзиллар бу ҳужжатга ёзилмайди.
- `<STAMP>` — захира вақт белгиси, `YYYY-mm-dd_HH` кўринишида (масалан `2026-11-02_14`).
- Барча сервер буйруқлари `/root/Forest-Back` папкасида бажарилади. Бу йўлни деплой сценарийси (`.github/workflows/deploy.yml`) ишлатади.
- Буйруқларни платформа маъмури бажаради. Сирлар (парол, калит, токен) буйруқ қаторига ҳам, ҳужжатга ҳам ёзилмайди.

Қисқа ёзув учун:

```bash
cd /root/Forest-Back
COMPOSE="docker-compose -f docker/prod/docker-compose-prod.yml"
```

---

## 1. Компонентлар

Модул алоҳида сервис эмас. У STAT-URMON backend'ининг `apps/yashil` иловаси, API `/api/v1/yashil/` йўлида ишлайди. Фронтенд эса Forest-Web SPA ичидаги `/yashil/*` саҳифаларидан иборат. Ишчи муҳит `docker/prod/docker-compose-prod.yml` билан кўтарилади.

| Сервис (контейнер) | Умумий вазифаси | Модул учун аҳамияти |
|---|---|---|
| `forest_app` (`forest_app_prod`) | gunicorn, бутун REST API | `/api/v1/yashil/` барча амаллари: буюртма, акт, омбор, ҳисобот, импорт, PDF. Ишга тушишда `makemigrations` → `migrate` → `collectstatic` бажарилади (`docker/prod/entrypoint.sh`). 2000 қаторгача бўлган экспорт шу ерда тайёрланади. `media/`, `src/`, `backups/` папкалари уланган |
| `forest_ws` (`forest_ws_prod`) | daphne, фақат `/ws/` (чат) | Модул WebSocket ишлатмайди |
| `forest_celery_worker` (`forest_celery_worker_prod`) | Celery фон вазифалари | Даврий вазифалар ва 2000 қатордан катта экспорт (`yashil.export_job`) шу ерда бажарилади. Фон экспорт файли `media/` га ёзилади (контейнерга `../../media` уланган) |
| `forest_celery_beat` (`forest_celery_beat_prod`) | Даврий вазифалар жадвали | Қуйидаги жадвалга қаранг |
| `forest_postgres` (`forest_postgres_prod`) | PostgreSQL 16 | Модулнинг барча жадваллари, жумладан имзолар (`pkcs7`) ва омбор ҳаракатлари. `shm_size: 512mb` |
| `forest_redis` (`forest_redis_prod`) | Redis 7.0.15 | DB 0 — Celery навбати. DB 1 — Django кеши (модул калитлари `yashil:*`). DB 2 — WebSocket |
| `forest_nginx` (`forest_nginx_prod`) | nginx 1.29.8, TLS, статика | `/media/documents/` ҳимояланган: файл фақат Django берган имзоли `?t=` ҳавола билан очилади (`X-Accel-Redirect`). SPA `/var/www/stat-ormon` дан берилади, жумладан `/yashil/verify/<token>` QR саҳифаси |
| `e_imzo_server` (`e_imzo_server_prod`) | E-IMZO сервери (ишлаб чиқарувчининг Java дастури) | Имзони текшириш. Порт ташқарига очилмайди, backend унга ички тармоқда `e_imzo_server:8080` орқали уланади. Калитлар `e-imzo-server/keys/` да туради, гитда йўқ |
| `forest_certbot` | Let's Encrypt (бир марталик) | Модулга бевосита алоқаси йўқ |

Фронтенд (Forest-Web) алоҳида деплой қилинади: `main` га қўшилгач GitHub Actions `npm run build` ни бажаради ва натижани серверга `rsync` билан `/var/www/stat-ormon/` га юклайди.

### 1.1 Модулнинг даврий вазифалари (Celery beat)

Манба: `src/config/settings/celery.py` (`CELERY_BEAT_SCHEDULE`).

| Жадвал номи | Вазифа | Даври | Нима қилади |
|---|---|---|---|
| `yashil-deadline-reminders` | `yashil.deadline_reminders` | ҳар куни 08:00 | Аввал очиқ буюртмаларнинг кечикиш устунларини (`review_due`, `late_workdays`, `overdue_stage`) қайта ҳисоблайди. Сўнг эслатма юборади: кўриб чиқишга 1 иш куни қолганда; етказишга 3 ва 1 иш куни қолганда; муддат бузилганда ҳар куни. Далолатнома маҳалла тасдиғида `act_review_reminder_days` (3) иш кунидан ортиқ турса, маҳаллага эслатма боради |
| `yashil-reconcile` | `yashil.reconcile` | ҳар куни 02:30 | ТТ §22.3 бўйича тунги солиштириш. Текширилади: қолдиқ ҳаракатлар йиғиндисига тенг; ҳар қабул сатрида битта ажратиш бор; қабул миқдори буюртмадан ошмаган; ёпилган буюртма тўлиқ. Топилганлар `ReconcileIssue` га ёзилади ва кузатувчига хабар берилади. Манфий ўрмон қолдиғи хато эмас, етказиб берувчига «таъминлаш керак» хабари кетади |
| `yashil-export-cleanup` | `yashil.export_cleanup` | ҳар куни 03:15 | Муддати (7 кун) ўтган экспорт файлларини ўчиради |
| (жадвалсиз) | `yashil.export_job` | сўров бўйича | 2000 қатордан катта ҳисобот экспортини тайёрлайди |

**Муҳим:** кунлик вазифалар соат вақти бўйича (`crontab`, `CELERY_TIMEZONE`, стандарт `Asia/Tashkent`) ишлайди. Beat контейнери ҳар деплойда қайта яратилса ҳам навбатдаги вақтда ишга тушади. Вазифаларни қўлда ишга тушириш 7-бўлимда берилган.

### 1.2 Хост даражасидаги cron вазифалари

| Қатор | Вазифа |
|---|---|
| `5 * * * *  /root/Forest-Back/docker/prod/backup-hourly.sh >> /root/Forest-Back/backups/hourly/backup.log 2>&1` | Соатлик захира (5-бўлим) |
| `*/5 * * * * /root/Forest-Back/docker/prod/watchdog.sh >> /var/log/forest-watchdog.log 2>&1` | Сайт, API ва Celery worker назорати. Worker жавоб бермаса, у қайта яратилади (30 дақиқада кўпи билан бир марта) |

---

## 2. Муҳит ўзгарувчилари

Backend'нинг `.env` файли гитда йўқ. Ҳар деплойда у GitHub'даги `ENV_FILE` сиридан ёзилади. `ADMIN_ALLOWED_IPS` алоҳида сир сифатида сақланади. Шу `.env` дан иккита файл ажратилади: `.env.postgres` (фақат `POSTGRES_*`) ва `.env.eimzo` (фақат `VPN_KEY_PASSWORD`). Намуна файл — `.env.example` (қийматларсиз). Қуйидаги жадвалда фақат номлар ва маънолари берилган. Ҳақиқий қийматлар ҳеч қаерга ёзилмайди.

### 2.1 Backend (`.env`)

| Ўзгарувчи | Маъноси | Намуна |
|---|---|---|
| `SECRET_KEY` | Django махфий калити | `<махфий-калит>` |
| `DEBUG` | Ишчи муҳитда `False`. `True` бўлса синов буйруқлари ҳимоясиз қолади | `False` |
| `DB_ENGINE` | Маълумотлар базаси драйвери | `django.db.backends.postgresql` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | База номи, фойдаланувчиси, пароли (`.env.postgres` га ҳам ўтади) | `<база>`, `<фойдаланувчи>`, `<парол>` |
| `DB_HOST`, `DB_PORT` | База манзили (ички тармоқда) | `forest_postgres`, `5432` |
| `REDIS_HOST`, `REDIS_PORT` | WebSocket учун Redis. Кеш манзили `redis_setup.py` да қатъий: `forest_redis:6379/1` | `forest_redis`, `6379` |
| `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Celery навбати | `redis://forest_redis:6379/0` |
| `CELERY_TIMEZONE` | Celery вақт зонаси; бўлмаса `Asia/Tashkent`. Кунлик вазифалар соатлари шу зонада | `Asia/Tashkent` |
| `YASHIL_PUBLIC_BASE_URL` | QR текшириш ҳаволасининг асоси. Синов серверида ўз домени берилади | `https://stat-urmon.uz` |
| `EIMZO_REQUIRE_TIMESTAMP` | `True` бўлса, вақт тамғаси (TSA) олинмаган имзо рад этилади (стандарт `False`) | `False` |
| `CELERY_TASK_ALWAYS_EAGER` | `True` бўлса вазифалар фонда эмас, сўров ичида бажарилади. Ишчи муҳитда берилмайди | (бўш) |
| `GUNICORN_WORKERS` | API жараёнлари сони, одатда 2×CPU+1 | `9` |
| `VPN_KEY_PASSWORD` | E-IMZO VPN калити пароли (`.env.eimzo` орқали фақат `e_imzo_server` га берилади) | `<парол>` |
| `ADMIN_ALLOWED_IPS` | `/admin/` ва `/billing-admin/` очиладиган IP/CIDR рўйхати. Модулнинг SPA маъмурий экранларига таъсир қилмайди | `<IP-рўйхат>` |
| `USER_THROTTLE_RATE` | Фойдаланувчи учун API лимити | `600/min` |
| `YASHIL_ALLOW_LOAD_SEED` | Фақат синов серверида, юклама маълумотини яратиш учун (`yashil_seed_load --force`). Ишчи серверда **берилмайди** | `1` |
| `EMAIL_*`, `MIB_PUSH_*` | Платформанинг бошқа қисмлари учун. Модул хабарномалари фақат кабинет ичида | — |

### 2.2 Фронтенд (Forest-Web, йиғиш пайтида)

| Ўзгарувчи | Маъноси | Намуна |
|---|---|---|
| `VITE_API_URL` | API манзили | `https://<api-домен>/api/v1` |
| `VITE_WS_URL` | WebSocket манзили (модулда ишлатилмайди) | `wss://<api-домен>/ws` |
| `VITE_EIMZO_API_KEYS` | Браузердаги E-IMZO клиенти учун домен калитлари. Калит рўйхатида йўқ доменда имзолаш ишламайди | `<домен>:<калит>` |

### 2.3 Захира ва тиклаш скриптлари

| Ўзгарувчи | Скрипт | Стандарт қиймати | Маъноси |
|---|---|---|---|
| `ROOT` | иккаласи | скрипт турган жойдан `../..` | Лойиҳа папкаси |
| `BACKUP_DIR` | иккаласи | `$ROOT/backups/hourly` | Захира папкаси |
| `PG_CONTAINER`, `APP_CONTAINER` | `backup-hourly.sh` | `forest_postgres_prod`, `forest_app_prod` | Контейнер номлари |
| `KEEP_HOURS` | `backup-hourly.sh` | `48` | Соатлик нусхалар неча соат сақланади |
| `KEEP_DAYS` | `backup-hourly.sh` | `30` | Кунлик (соат 00 даги) нусхалар ва конфигурация неча кун сақланади |
| `OFFSITE_TARGET` | `backup-hourly.sh` | бўш | Ташқи нусха жойи, `user@host:/path` (ssh орқали rsync). Ҳозир бўш: жой ажратилмаган |
| `APP_IMAGE` | `restore-test.sh` | `forest_app_prod` нинг image'и | Текширув учун image |
| `APP_UID` | `restore-test.sh` | image фойдаланувчиси (1000) | Иш папкаси шу UID'га берилади |

### 2.4 Кодда белгиланадиган созламалар (муҳит ўзгарувчиси эмас)

Қуйидагилар `django.conf.settings` дан ўқилади. Улар учун `.env` боғланиши йўқ: ўзгартириш учун `src/config/settings/` га PR керак. Ҳозир бу созламалар settings файлларида берилмаган, шунинг учун стандарт қийматлар амал қилади.

| Созлама | Стандарт | Қаерда ишлатилади |
|---|---|---|
| `YASHIL_EXPORT_SYNC_LIMIT` | 2000 | Шу қаторгача экспорт сўров ичида, каттаси фонда (`apps/yashil/conf.py`) |
| `YASHIL_EXPORT_PDF_LIMIT` | 5000 | PDF ҳисобот учун қаторлар чегараси |
| `YASHIL_EXPORT_MAX_ACTIVE` | 3 | Бир фойдаланувчида бир вақтда фаол экспортлар |
| `YASHIL_EXPORT_RETENTION_DAYS` | 7 | Тайёр экспорт файли неча кун сақланади |
| `YASHIL_EXPORT_CHUNK` | 1000 | Базадан ўқиш бўлаги |
| `YASHIL_MAP_MAX_POINTS` | 5000 | Харитага бир сўровда бериладиган нуқталар |

---

## 3. Биринчи ўрнатиш ва янгилаш

### 3.1 Янгилаш тартиби

1. Ҳар ўзгариш `origin/main` дан олинган янги `jr-<ном>` branch'ида тайёрланади ва PR очилади.
2. PR'ни лойиҳа эгаси `main` га қўшади. `main` га бевосита push қилинмайди.
3. Backend ва фронтенд бирга ўзгарса, аввал backend PR'и қўшилиб деплой бўлади, кейин фронтенд.
4. `main` га қўшилгач GitHub Actions (`CI/CD Deployment`) деплойни ўзи бажаради.

Деплой ҳолатини кўриш:

```bash
gh run list -R Stat-Forest/Forest-Back -L 3
gh run list -R Stat-Forest/Forest-Web -L 3
```

### 3.2 Backend деплойи нима қилади

`.github/workflows/deploy.yml` қадамлари:

1. Сирдан `.env` ни ёзади ва серверга нусхалайди.
2. Кодни `rsync --inplace` билан `/root/Forest-Back/` га юклайди. `media/`, `staticfiles/`, `backups/` ва `.env` юкланмайди.
3. Папкаларни контейнер фойдаланувчисига (UID 1000) беради ва `.env.postgres`, `.env.eimzo` файлларини ажратади.
4. Боғлиқ сервисларни (`forest_postgres`, `forest_redis`, `e_imzo_server`) `up -d --no-recreate` билан фақат ишга туширади, уларни қайта яратмайди.
5. App сервисларини (`forest_app`, `forest_ws`, `forest_celery_worker`, `forest_celery_beat`) тўлиқ ўчиради, image'ни қайта йиғади ва `up -d --no-deps` билан янгидан яратади.
6. nginx конфигини `nginx -t` билан текширади ва тўғри бўлса `reload` қилади. nginx контейнери қайта яратилмайди.

### 3.3 Миграциялар

Миграция файллари гитда сақланмайди (`.gitignore`: `src/apps/*/migrations/0*`). Улар серверда `forest_app` ишга тушганда `makemigrations` билан яратилади ва `migrate` билан қўлланади. `src` хостдан уланган, шунинг учун яратилган файллар `/root/Forest-Back/src/apps/*/migrations/` да сақланиб қолади.

- Миграция вақтида биринчи 1–2 дақиқада API 502 қайтариши мумкин. Бу кутилган ҳолат.
- `makemigrations` хато берса, деплой логида `!!! makemigrations FAILED` қатори чиқади, контейнер эса тўхтамайди. Бундай ҳолда:

  ```bash
  docker logs --tail 100 forest_app_prod
  docker exec forest_app_prod python manage.py showmigrations yashil
  ```

- Миграция файллари соатлик захирага **кирмайди** (5.3-бандга қаранг).

### 3.4 Боғлиқ сервислар қўлда янгиланади

Деплой `forest_postgres`, `forest_redis`, `e_imzo_server` ва `forest_nginx` ни қайта яратмайди. Уларнинг `docker-compose-prod.yml` даги созламаси ўзгарса (image версияси, `shm_size`, `command`, volume), серверда қўлда қайта яратилади. Масалан, postgres учун (тахминан 10 сония узилиш, маълумот volume'да сақланади):

```bash
$COMPOSE stop forest_postgres
$COMPOSE rm -f forest_postgres
$COMPOSE up -d --no-deps forest_postgres
docker exec forest_postgres_prod df -h /dev/shm     # 512M кўриниши керак
```

`forest_redis`, `e_imzo_server` ва `forest_nginx` учун ҳам худди шу уч буйруқ, фақат сервис номи бошқа.

### 3.5 Маълум муаммо: `KeyError: 'ContainerConfig'`

Серверда `docker-compose` 1.29.2 (V1) ва янги Docker Engine ишлайди. Контейнерни қайта яратишда (Recreating) V1 шу хатони беради. Деплой скрипти бу йўлдан қочади, лекин compose файли ўзгарган деплойда хато яна чиқиши мумкин: масалан, worker «Recreating» йўлига кириб қолади.

Ечим:

1. Деплой логида қайси сервислар яратилганини кўринг (`Creating`, `Recreating`, `ERROR` қаторлари).
2. Йиқилган job'ни қайта ишга туширинг. Скриптнинг 2-қадами эски контейнерларни label бўйича ҳам тозалайди.

   ```bash
   gh run rerun <run-id> -R Stat-Forest/Forest-Back --failed
   ```

3. Серверда текширинг: тўртала app контейнери `Up` бўлиши, логда «nomi buzilgan konteynerlar» огоҳлантириши бўлмаслиги керак.

   ```bash
   $COMPOSE ps
   docker ps -a --format '{{.Names}}' | grep -E '^[0-9a-f]{12}_' || echo "тоза"
   ```

### 3.6 Янги серверга биринчи ўрнатиш

Ишчи сервер ҳозир мавжуд ва ишламоқда. Янги серверга кўчириш тўлиқ синовдан ўтказилмаган, шунинг учун қадамлар умумий кўринишда берилган (**аниқлаштирилади**).

1. Docker Engine ва `docker-compose` 1.29.2 ўрнатилади (ишчи сервердаги версия билан бир хил).
2. GitHub'да `HOST`, `USER`, `SSH_PRIVATE_KEY`, `SSH_KNOWN_HOSTS`, `ENV_FILE`, `ADMIN_ALLOWED_IPS` сирлари янги серверга мосланади (бу ишни репозиторий эгаси бажаради).
3. Гитда йўқ файллар серверга қўлда қўйилади:
   - `e-imzo-server/keys/` — VPN калити ва truststore;
   - `keys/mib/` — бошқа модул учун;
   - TLS сертификатлари — `docker/prod/certbot/etc`.
4. Деплой ишга туширилади (Actions → `CI/CD Deployment` → re-run ёки `main` га навбатдаги қўшилиш).
5. Маълумот кўчирилса, 6.3-банддаги тартиб бажарилади. Бўш база бўлса, 4-бўлим бўйича маълумот юкланади.
6. 1.2-банддаги cron қаторлари қўшилади.
7. Фронтенд деплойи (Forest-Web) янги серверга йўналтирилади.

### 3.7 Деплойдан кейинги текширув

```bash
# 1) Контейнерлар
$COMPOSE ps

# 2) API: токенсиз ҳимояланган йўл 401, нотўғри QR токени 404 қайтариши керак
curl -s -o /dev/null -w "%{http_code}\n" https://<api-домен>/api/v1/yashil/orders/                # 401
curl -s -o /dev/null -w "%{http_code}\n" https://<api-домен>/api/v1/yashil/admin/settings/        # 401
curl -s -o /dev/null -w "%{http_code}\n" https://<api-домен>/api/v1/yashil/verify/notatoken/      # 404

# 3) Фронтенд: SPA саҳифаси 200
curl -s -o /dev/null -w "%{http_code}\n" https://<веб-домен>/yashil/verify/notatoken              # 200

# 4) Worker модул вазифаларини танийди (ишга тушиш баннеридаги [tasks] рўйхати)
docker logs forest_celery_worker_prod 2>&1 | grep "yashil\."

# 5) Beat жадвалида модул вазифалари бор
docker exec forest_app_prod python manage.py shell -c \
  "from django.conf import settings; print([k for k in settings.CELERY_BEAT_SCHEDULE if k.startswith('yashil')])"

# 6) Маълумот ва созламалар ҳолати
docker exec forest_app_prod python manage.py yashil_readiness
```

4-қадамда `yashil.deadline_reminders`, `yashil.reconcile`, `yashil.export_cleanup`, `yashil.export_job` кўриниши керак. `docker logs forest_celery_beat_prod | grep yashil` эса вазифа юборилгандагина натижа беради, яъни жадвалдаги навбатдаги вақтдан кейин (1.1-банд).

Агар деплой кечикиш устунларига тегадиган ўзгариш олиб келса (масалан муддат ҳисоби ёки календарь мантиқи), устунлар дарҳол қайта ҳисобланади:

```bash
docker exec forest_app_prod python manage.py yashil_recalc_deadlines
```

---

## 4. Бошланғич маълумот юклаш

Тартиб ТТ §19.2 га асосланган: аввал ташкилотлар, маҳаллалар, хўжалик бириктиришлари, каталог ва бошланғич қолдиқлар текширилади. Сўнг пилот, ундан кейин ишчи муҳит келади. Ҳозир серверда фақат синов маълумотлари бор, ҳақиқий рўйхатлар буюртмачидан кутилмоқда.

Ҳар бир импорт аввал **текширув режимида** ўтказилади: буйруқларда `--dry-run`, экранда «Текшириш». Хатолар тузатилгач, ҳақиқий юкланади.

- **Буйруқлар** хатоли қаторни ташлаб ўтади ва қолганини ёзади. Ҳисоботда хатолар қатор рақами билан кўрсатилади.
- **Модул маъмури экранидаги импорт** (`/yashil/admin`) «ҳаммаси ёки ҳеч нарса» тамойилида ишлайди: битта хато бўлса ҳам ҳеч нарса ёзилмайди. Текширув режими у ерда стандарт.

Файлни контейнерга узатиш:

```bash
docker exec -i forest_app_prod sh -c 'cat > /tmp/import.xlsx' < mahallalar.xlsx
```

Бу усулда файл контейнер фойдаланувчиси (UID 1000) номидан ёзилади. `docker cp` эса хостдаги эгаси ва ҳуқуқини сақлайди: root'нинг 600 ҳуқуқли файли контейнерда ўқилмай қолади.

| № | Маълумот | Восита | Изоҳ |
|---|---|---|---|
| 1 | Ташкилотлар (ўрмон хўжаликлари, ДМ) | STAT-URMON ташкилотлар маълумотномаси (`general.Organization`) + `/yashil/admin` → «Етказиб берувчилар» | Модул ташкилотни ўзи яратмайди: мавжуд ташкилот қидирилади ва унга тур (ўрмон / ДМ) ҳамда СТИР билан етказиб берувчи профили берилади. ДМ ташкилоти маълумотномада бўлмаса, уни платформа маъмури қўшади |
| 2 | Уюшма бўлинмалари | `/yashil/admin` → «Уюшма бўлинмалари» | Excel импорт йўқ, экранда киритилади |
| 3 | Маҳаллалар | `yashil_import_mahallas` ёки `/yashil/admin` → «Маҳаллалар» → импорт | Устунлар: манба коди, вилоят коди, туман коди, маҳалла номи, манзил, фаол, амал бошланиши [, амал тугаши]. Вилоят/туман кодлари — MHOBT. `source_code` бўйича такрор юклаш хавфсиз |
| 4 | Маҳалла → ўрмон хўжалиги бириктиришлари | `yashil_import_assignments` ёки экрандаги «Бириктиришлар» импорти | Устунлар: маҳалла коди, хўжалик (ташкилот UUID ёки аниқ номи), амал бошланиши, амал тугаши. Даврлар кесишса қатор рад этилади. `--source` — асос ҳужжат реквизити |
| 5 | Маҳалла → уюшма бўлинмаси йўналишлари | Фақат экранда: «Йўналишлар» импорти (`admin/routes/import/`) | Буйруқ йўқ |
| 6 | Каталог | `/yashil/admin` → «Каталог» | Excel импорт йўқ. Позиция экранда киритилади, кодни кейин ўзгартириб бўлмайди. Мавсумлар, объект турлари ва меъёрлар (`NormRule`) фақат Django `/admin/` орқали киритилади, у эса `ADMIN_ALLOWED_IPS` билан ёпиқ |
| 7 | Иш кунлари календари | `yashil_import_calendar` ёки экрандаги «Календарь» | Устунлар: сана, тури («байрам / дам олиш» ёки «иш куни»), изоҳ. Сана бўйича такрор юклаш хавфсиз. `--source` — расмий ҳужжат реквизити. Жорий йил календари бўлмаса, `yashil_readiness` буни блокловчи деб кўрсатади |
| 8 | Аъзоликлар (ваколатлар) | `/yashil/admin` → «Аъзоликлар» | Фойдаланувчи STAT-URMON фойдаланувчилар бўлимида олдиндан бўлиши керак. Модул экранида у қидирилади ва аъзолик берилади: тайёрлаш, имзолаш, ваколат ҳужжати, амал даври |
| 9 | Бошланғич қолдиқлар | Етказиб берувчи кабинети → «Омбор» → «Бошланғич қолдиқ» ёки Excel импорт (`stock/opening/import/`) | Устунлар: каталог коди, миқдор, ҳужжат рақами, ҳужжат санаси. Ҳар позиция бир марта киритилади. Импорт фақат етказиб берувчи кабинетидан бажарилади (маъмур номидан эмас), шунинг учун 8-қадам бундан олдин туриши керак |
| 10 | ДМ хизмат қуввати (ойлик) | `/yashil/admin` → «Хизмат қуввати» ёки ДМ имзоловчиси ўз кабинетидан | `yashil_readiness` жорий ой учун қувватсиз ДМ'ни кўрсатади |

Буйруқлар намунаси:

```bash
# Маҳаллалар
docker exec -i forest_app_prod sh -c 'cat > /tmp/mahallalar.xlsx' < mahallalar.xlsx
docker exec forest_app_prod python manage.py yashil_import_mahallas --file /tmp/mahallalar.xlsx --dry-run
docker exec forest_app_prod python manage.py yashil_import_mahallas --file /tmp/mahallalar.xlsx

# Бириктиришлар
docker exec -i forest_app_prod sh -c 'cat > /tmp/biriktirish.xlsx' < biriktirish.xlsx
docker exec forest_app_prod python manage.py yashil_import_assignments --file /tmp/biriktirish.xlsx --source "<асос ҳужжат>" --dry-run
docker exec forest_app_prod python manage.py yashil_import_assignments --file /tmp/biriktirish.xlsx --source "<асос ҳужжат>"

# Календарь
docker exec -i forest_app_prod sh -c 'cat > /tmp/kalendar.xlsx' < kalendar.xlsx
docker exec forest_app_prod python manage.py yashil_import_calendar --file /tmp/kalendar.xlsx --source "<ҳужжат реквизити>" --dry-run
docker exec forest_app_prod python manage.py yashil_import_calendar --file /tmp/kalendar.xlsx --source "<ҳужжат реквизити>"

# Якуний текширув
docker exec forest_app_prod python manage.py yashil_readiness --strict
```

Ишчи серверда `yashil_seed_demo` ва `yashil_seed_load` **ишлатилмайди**. Иккаласи ҳам синов маълумоти яратади: биринчиси `DEBUG=False` да `--force` сиз ишламайди, иккинчиси `YASHIL_ALLOW_LOAD_SEED=1` сиз ишламайди.

---

## 5. Захира

### 5.1 Соатлик захира (`docker/prod/backup-hourly.sh`)

ТТ §17.3 мақсади: маълумот йўқотиш оралиғи (RPO) 1 соатдан ошмайди. Скрипт хостда root номидан cron орқали ишлайди:

```
5 * * * *  /root/Forest-Back/docker/prod/backup-hourly.sh >> /root/Forest-Back/backups/hourly/backup.log 2>&1
```

Ҳар сафар бир хил вақт белгиси (`<STAMP>`) билан қуйидагилар сақланади:

| Нима | Қаерда (`backups/hourly/` ичида) | Изоҳ |
|---|---|---|
| База | `db/forest_<STAMP>.dump` | `pg_dump -Fc -Z 6`. Аввал вақтинчалик файлга ёзилади, `pg_restore -l` билан текширилади, кейин номи ўзгартирилади. Имзолар (`pkcs7`) ва омбор ҳаракатлари базада, шунинг учун шу нусхага киради |
| Яхлитлик бармоқ изи | `db/forest_<STAMP>.integrity.json` | `yashil_integrity_check --json --no-files` натижаси, тиклашда солиштириш учун |
| Файллар (media) | `media/<STAMP>/` | `rsync --link-dest`: ўзгармаган файллар олдинги нусхага hardlink, жой фақат ўзгарганлар учун кетади. `media/latest` — охирги нусхага символик ҳавола. PDF, иловалар, ваколат ҳужжатлари ва календарь файллари шу ерда |
| Конфигурация (кунига бир марта) | `config/<YYYY-mm-dd>/` | `e-imzo-server/keys`, `keys`, `.env`, `.env.postgres`, `.env.eimzo`, серверда яратилган миграциялар (`migrations.tgz`). Ҳуқуқ фақат root'га (`go-rwx`) |

**Сақлаш муддати:**

- соатлик нусхалар — `KEEP_HOURS` (48) соат;
- соат 00 даги нусхалар (`*_00`) — `KEEP_DAYS` (30) кун;
- конфигурация — 30 кун.

**Бир вақтда икки нусха:** `flock` билан тўсилади. Олдинги нусха тугамаган бўлса, янгиси «o'tkazib yuborildi» деб чиқиб кетади.

**Ташқи нусха:** `OFFSITE_TARGET` берилса, охирги база дампи, бармоқ изи ва media нусхаси шу манзилга `rsync` билан юборилади. Ҳозир алоҳида захира жойи ажратилмаган, шунинг учун ҳамма нусхалар ишчи сервернинг ўз дискида. Ишчи қабулдан олдин бу ҳал қилиниши керак (буюртмачи қарори кутилмоқда). Қўлда ишга тушириш:

```bash
OFFSITE_TARGET="<user>@<захира-сервер>:/path" ./docker/prod/backup-hourly.sh
```

Доимий фойдаланиш учун ўзгарувчи cron қаторига қўшилади.

**Ҳажм (2026-10-29 ҳолати):** база дампи тахминан 31 МБ, media 2112 та файл, бир нусха тахминан 40 сония. Модулда ишчи маълумот кўпайгач ҳажм қайта баҳоланади.

### 5.2 Текшириш

```bash
tail -n 20 backups/hourly/backup.log
ls -lt backups/hourly/db | head
ls -l backups/hourly/media/latest
```

Логда «zaxira tugadi» қатори бўлиши керак. «ogohlantirish: yashil_integrity_check ishlamadi» чиқса, `forest_app_prod` ишлаётганини текширинг.

### 5.3 Захирага кирмайдиганлар

| Нима | Оқибати | Тавсия |
|---|---|---|
| Redis | Кеш, навбатдаги фон вазифалар, имзолаш сўровларининг вақтинчалик ёзувлари | Тиклашда керак эмас, лекин модул кеш калитлари тозаланади (6.4-банд) |
| Лог файллари (`/var/log/forest-back`) | — | Аудит базада (`logs` ва модул ҳодисалари), алоҳида сақлаш шарт эмас |

Эски `docker/prod/backup.sh` (кунлик ZIP, 3 йил сақлаш) ҳам репозиторийда бор. Унинг серверда жадвалга қўйилгани **аниқлаштирилади**.

---

## 6. Тиклаш

ТТ §17.3 мақсади: тиклаш вақти (RTO) 4 соатдан ошмайди. Захирадан тиклаш синови топширишдан олдин ўтказилади (Q36).

### 6.1 Тиклаш синови (`docker/prod/restore-test.sh`) — ишчи базага тегмайди

Скрипт қуйидагиларни бажаради:

1. Вақтинчалик тармоқ ва вақтинчалик `postgres:16` контейнерини (тасодифий парол билан) кўтаради.
2. Танланган дампни `pg_restore -j 4` билан тиклайди.
3. Media нусхасини вақтинчалик папкага кўчиради.
4. Ишчи image'дан текширув контейнерини ишга туширади ва `yashil_integrity_check --strict --compare snapshot.json` билан захира пайтидаги бармоқ изига солиштиради.
5. Тиклаш вақтини (RTO) ва захира ёшини (RPO) ўлчайди.
6. Ҳамма вақтинчалик нарсаларни ўчиради.

```bash
./docker/prod/restore-test.sh                 # охирги соатлик захира
./docker/prod/restore-test.sh <STAMP>          # аниқ вақт белгиси
```

Натижа экранга чиқади ва `backups/hourly/restore-test-<сана>.log` га ёзилади:

- `Zaxira yoshi: N daqiqa` — RPO мезони ≤ 60;
- `Umumiy tiklash vaqti: N s` — RTO мезони ≤ 14400 s;
- `NATIJA: O'TDI` ёки `NATIJA: O'TMADI (kod N)` ва фарқлар рўйхати.

Синовни ойда бир марта ва ҳар катта ўзгаришдан кейин ўтказиш тавсия этилади. 2026-10-30 даги натижа: ўтди (база 11 с, media 26 с, жами 42 с). Ўша пайтда модулда ишчи маълумот йўқ эди, шунинг учун ҳужжат хэши ва имзо текшируви бўш тўпламда ўтган. Ишчи маълумот пайдо бўлгач, синов такрорланади.

### 6.2 Ишчи базани соатлик захирадан тиклаш

**Бу амал ишчи маълумотни алмаштиради.** У фақат буюртмачи масъули қарори билан бажарилади. Танланган вақт белгисидан кейин киритилган маълумотлар йўқолади.

`docker/prod/restore.sh` фақат эски `backup.sh` ZIP архиви учун ёзилган: у оддий SQL'ни `psql` билан, хатоларни ўтказиб юбориб (`ON_ERROR_STOP=0`) қўллайди. Соатлик `.dump` учун у **ишлатилмайди**, қуйидаги қадамлар бажарилади.

```bash
cd /root/Forest-Back
COMPOSE="docker-compose -f docker/prod/docker-compose-prod.yml"
STAMP=<YYYY-mm-dd_HH>
NOW=$(date +%Y%m%d_%H%M)

# 0) Танланган нусха бор-йўқлигини текшириш
ls -l backups/hourly/db/forest_$STAMP.dump backups/hourly/db/forest_$STAMP.integrity.json
ls -d backups/hourly/media/$STAMP

# 1) Соатлик захира cron'ини вақтинча ўчириш (crontab -e, backup-hourly.sh қатори бошига #).
#    Акс ҳолда тиклаш пайтида ярим ҳолат захираланади.

# 2) Ёзувчи сервисларни тўхтатиш (контейнерлар ўчирилмайди, фақат тўхтайди)
$COMPOSE stop forest_app forest_ws forest_celery_worker forest_celery_beat

# 3) Жорий ҳолатнинг хавфсизлик нусхаси (алоҳида номда: соатлик нусха устидан ёзилмасин)
docker exec forest_postgres_prod sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/pre-restore-$NOW.dump
rsync -a media/ backups/media-pre-restore-$NOW/

# 4) Базани қайта яратиш ва дампни тиклаш
docker exec forest_postgres_prod sh -c 'dropdb --force -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'
docker exec -i forest_postgres_prod sh -c 'cat > /tmp/restore.dump' < backups/hourly/db/forest_$STAMP.dump
docker exec forest_postgres_prod sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner -j 4 /tmp/restore.dump; rm -f /tmp/restore.dump'

# 5) Файлларни тиклаш (папканинг ўзи сақланади: nginx уланишига тегмайди)
rsync -a --delete backups/hourly/media/$STAMP/ media/
chown -R 1000:1000 media

# 6) Сервисларни ишга тушириш (start — қайта яратиш эмас; entrypoint migrate'ни ўзи бажаради)
$COMPOSE start forest_app forest_ws forest_celery_worker forest_celery_beat
docker logs --tail 50 forest_app_prod
```

Сўнг 6.4-банддаги текширувлар бажарилади ва 1-қадамда ўчирилган cron қатори қайта ёқилади. Хавфсизлик нусхалари (`backups/pre-restore-*`, `backups/media-pre-restore-*`) натижа тасдиқлангач қўлда ўчирилади.

### 6.3 Бошқа серверга тиклаш (сервер йўқолганда)

1. Янги сервер 3.6-банд бўйича тайёрланади.
2. Ташқи жойдан `backups/hourly/` (база, бармоқ изи, media, конфигурация) олинади. Конфигурация нусхасидаги калитлар ва `.env` тегишли жойга қўйилади.
3. Миграция файллари захиранинг `config/<сана>/migrations.tgz` нусхасидан `src/` ичига биринчи деплойдан **олдин** очилади (`tar -xzf migrations.tgz -C src`): база айнан шу миграциялар билан яратилган. Акс ҳолда деплой янги номли миграциялар яратади ва `migrate` хато бериши мумкин. Бу қадам синов серверида текширилиши керак (**аниқлаштирилади**).
4. Деплойдан кейин 6.2-банддаги 2–6-қадамлар бажарилади.
5. 6.4-банддаги текширувлар бажарилади.

### 6.4 Тиклашдан кейинги текширув

```bash
# 1) Яхлитлик: захира пайтидаги бармоқ изи билан солиштириш (файллар ҳам текширилади)
docker exec -i forest_app_prod sh -c 'cat > /tmp/snapshot.json' < backups/hourly/db/forest_$STAMP.integrity.json
docker exec forest_app_prod python manage.py yashil_integrity_check --strict --compare /tmp/snapshot.json

# 2) Модул кеши (Redis DB 1, «yashil:» калитлари): календарь 1 соат, қоидалар 60 с, статистика 5 дақиқа
#    сақланади, улар тикланган маълумотга мос келмаслиги мумкин.
#    FLUSHDB ишлатилмайди: шу DB'да чиқиш қилган сессиялар рўйхати ҳам бор.
docker exec forest_redis_prod sh -c "redis-cli -n 1 --scan --pattern '*yashil:*' | xargs -r redis-cli -n 1 del"

# 3) Кечикиш устунлари ва тайёрлик
docker exec forest_app_prod python manage.py yashil_recalc_deadlines
docker exec forest_app_prod python manage.py yashil_readiness

# 4) API ва сайт (3.7-банд)
curl -s -o /dev/null -w "%{http_code}\n" https://<api-домен>/api/v1/yashil/orders/   # 401
```

`yashil_integrity_check` чиқиши ва мезонлари:

- `ok: true` — ҳужжат хэшлари мазмунга, имзолар хэшга мос; йўқолган файл йўқ; ledger хатоси йўқ.
- `--compare` фарқ топмаса, сонлар, ҳолатлар, омбор йиғиндилари ва бармоқ излари захира пайтидаги билан бир хил.
- `--strict` муаммо бўлса нолдан фарқли код қайтаради.

---

## 7. Назорат буйруқлари

| Буйруқ | Қаерда | Вазифаси | Асосий параметрлар |
|---|---|---|---|
| `yashil_readiness` | Ишчи ва синов сервери | Пилот ва ишчи муҳитдан олдинги текширув (ТТ §19.2). **Блокловчи:** ўрмон хўжалиги ёки уюшма бўлинмаси бириктирилмаган маҳаллалар, жорий йил календари йўқлиги, фаол каталог позицияси йўқ йўналишлар. **Огоҳлантириш:** имзоловчисиз маҳалла ва етказиб берувчилар, бошланғич қолдиқсиз ўрмон хўжаликлари, жорий ой қувватисиз ДМ, кузатувчи йўқлиги. Амалдаги қоидалар қийматини ҳам кўрсатади | `--date YYYY-MM-DD`, `--json`, `--strict` (блокловчи бўлса хато коди), `--limit` |
| `yashil_integrity_check` | Ишчи ва синов сервери | Ҳужжат хэшлари ва имзолар, файллар мавжудлиги, ledger солиштируви, сонлар ва бармоқ излари | `--json`, `--no-files`, `--compare <файл>`, `--strict` |
| `yashil_recalc_deadlines` | Ишчи сервер | `Order.review_due` / `late_workdays` / `overdue_stage` устунларини қайта ҳисоблайди | `--today YYYY-MM-DD` |
| `yashil_import_mahallas`, `yashil_import_assignments`, `yashil_import_calendar` | Ишчи сервер | Excel импорт (4-бўлим) | `--file`, `--dry-run`, `--source` |
| `yashil_acceptance_protocol` | **Фақат синов сервери ёки локал** | Q01–Q36 автоматик синовларини ишга туширади ва DOCX баённома ёзади. Синовлар алоҳида синов базасида ишлайди ва `CREATEDB` ҳуқуқи керак, шунинг учун ишчи серверда ишлатилмайди | `--out <docx>`, `--environment "<муҳит номи>"`, `--note`, `--json <файл>`, `--no-run` (бўш шакл) |
| `yashil_seed_load` + `scripts/yashil_loadtest.py` | **Фақат синов сервери** | Q35 юклама синови: 100 000 буюртма, 100 фойдаланувчи; P95 ҳисоботи | 9-бандга қаранг |
| `yashil_seed_demo` | Фақат локал/синов | Намойиш учун синтетик маълумот | Ишчи серверда ишлатилмайди |

Мисоллар:

```bash
docker exec forest_app_prod python manage.py yashil_readiness --json > readiness.json
docker exec forest_app_prod python manage.py yashil_integrity_check --strict

# Кунлик вазифаларни қўлда ишга тушириш (масалан деплойдан кейин, 1.1-банд)
docker exec forest_celery_worker_prod celery -A config call yashil.deadline_reminders
docker exec forest_celery_worker_prod celery -A config call yashil.reconcile
docker logs --tail 50 forest_celery_worker_prod
```

**Қабул баённомаси (синов серверида):**

```bash
docker exec <app-контейнер> python manage.py yashil_acceptance_protocol \
    --out /tmp/yashil-bayonnoma.docx --environment "синов сервери" --json /tmp/yashil-bayonnoma.json
docker cp <app-контейнер>:/tmp/yashil-bayonnoma.docx .
```

Баённомадаги «қўлда натижа» устуни синов комиссияси томонидан тўлдирилади.

**Юклама синови (синов серверида):**

```bash
# 1) Маълумот ва токенлар. Синов сервери .env файлида YASHIL_ALLOW_LOAD_SEED=1 бўлиши керак.
#    Токен файли /tmp га ёзилади: media/ папкасига ЁЗИЛМАЙДИ, у nginx орқали очиқ бўлиши мумкин.
docker exec <app-контейнер> python manage.py yashil_seed_load --force --orders 100000 --users 100 \
    --password '<синов-пароли>' --tokens-out /tmp/load-tokens.json
docker cp <app-контейнер>:/tmp/load-tokens.json .

# 2) Ўлчаш (исталган компьютерда, фақат requests кутубхонаси керак)
python3 scripts/yashil_loadtest.py --base https://<тест-сервер>/api/v1/yashil --tokens load-tokens.json \
    --duration 300 --out natija.json

# 3) Тозалаш
docker exec <app-контейнер> python manage.py yashil_seed_load --purge
```

Токенлар 15 дақиқа амал қилади. Синов узоқроқ бўлса, `yashil_seed_load --tokens-only --tokens-out ...` билан янгиланади. Қабул мезони: «registry» ва «card» гуруҳларида P95 ≤ 3 сония. Синтетик маълумот `LOAD-…` / `LD-…` / `load.*@load.test` белгилари билан ажратилади ва `--purge` фақат шуларни ўчиради.

---

## 8. Муаммолар ва ечимлар

| Белги | Сабаби | Ечим |
|---|---|---|
| Оғир ҳисобот сўровларида 500, PostgreSQL логида `could not resize shared memory segment ... No space left on device` | Docker стандарт `/dev/shm` = 64 МБ | Compose'да `shm_size: 512mb` бор. Деплой postgres'ни қайта яратмайди, шунинг учун у қўлда қайта яратилади (3.4-банд); `df -h /dev/shm` 512M кўрсатиши керак |
| Деплойдан кейинги биринчи дақиқада 502 | `forest_app` миграция ва `collectstatic` бажаряпти | 1–2 дақиқа кутинг. Давом этса: `docker logs --tail 100 forest_app_prod` |
| Деплой `KeyError: 'ContainerConfig'` билан йиқилди | `docker-compose` V1 ва янги Docker Engine | 3.5-банд: `gh run rerun <id> --failed`, кейин `compose ps` |
| `restore-test.sh`: «Media nusxasi topilmadi» | `rsync -a` нусха папкасига асл `media/` нинг эски вақтини ёзади ва муддат тозалаши янги нусхани ўчиради | Тузатилган: скрипт нусхага `touch` қилади. Скрипт ўзгартирилса, бу қатор сақланиши шарт |
| `restore-test.sh`: `PermissionError: /restore/snapshot.json` | Скрипт root номидан ишлайди (umask 077), image эса UID 1000 билан | Тузатилган: иш папкаси image UID'ига берилади (`APP_UID`). Бошқа скриптларда ҳам root файлини контейнерга узатишда `docker exec -i ... sh -c 'cat > ...'` ишлатилади |
| `restore-test.sh` солиштиришда кичик фарқ (`counts.*`) | Бармоқ изи дампдан бир неча сония кейин олинади. Шу оралиқда ёзилган маълумот фарқ сифатида чиқади | Иш кам бўлган соатдаги нусха билан қайта синанг. Фарқ ўша оралиқдаги амалга мос бўлса, хато эмас |
| Календарь ёки қоида ўзгарди, лекин муддат эски | Кеш: календарь 1 соат, қоидалар 60 с. Экран ва импорт орқали сақлашда кеш ўзи тозаланади | 60 с кутинг. Базага тўғридан-тўғри ёзилган бўлса: `redis-cli -n 1 --scan --pattern '*yashil:*'` калитларини ўчиринг (6.4-банд) ва `yashil_recalc_deadlines` |
| Статистика карточкалари янгиланмади | Натижа 5 дақиқа кешланади | 5 дақиқа кутинг ёки модул кеш калитларини тозаланг |
| Эслатма ёки «муддати бузилган» хабарлари келмаяпти | Beat ишламаяпти ёки вазифа хато билан тугаган | `docker logs --tail 100 forest_celery_beat_prod` ва worker логи; қўлда: `celery -A config call yashil.deadline_reminders` (7-бўлим) |
| Катта экспорт «queued» ҳолатида қолди | Celery worker ишламаяпти | `docker exec forest_celery_worker_prod celery -A config inspect ping`; watchdog ҳар 5 дақиқада текширади ва жавоб бермаса worker'ни қайта яратади (30 дақиқада кўпи билан бир марта); `docker logs forest_celery_worker_prod` |
| Катта (2000+ қатор) экспорт «done», лекин файл очилмайди (404) | Worker контейнери эски compose билан яратилган (`media/` уланмаган) | `docker inspect forest_celery_worker_prod` да `/app/media` борлигини текширинг; бўлмаса worker'ни қайта яратинг (деплой буни қилади) |
| Имзолашда 503 `eimzo_unavailable` | `e_imzo_server` ишламаяпти ёки жавоб бермаяпти | `docker ps \| grep e_imzo`; `docker logs --tail 50 e_imzo_server_prod`; керак бўлса `docker restart e_imzo_server_prod` |
| Имзо `challenge` режимида бўляпти | `/ping` 503: VPN калити муддати ўтган. Ҳозирги кутилган ҳолат | Текшириш: `docker exec forest_app_prod curl -s -o /dev/null -w '%{http_code}' http://e_imzo_server:8080/ping`. Янги калит келгач, созламалар паспортидаги тартиб бўйича `document` режимига ўтилади |
| Скрипт билан кўп `curl` қилганда 429 | API лимити: аноним 30/дақ., фойдаланувчи 600/дақ., экспорт 10/дақ. | Сўровлар орасига пауза қўшинг |
| Импорт «Majburiy ustunlar topilmadi» | Сарлавҳалар мос эмас | Сарлавҳалар кирилл ёки лотинда, 4-бўлимдаги номлар билан. Катта-кичик ҳарф ва бўшлиқ аҳамиятсиз |
| QR ҳаволаси синов серверида ишчи доменга олиб боради | `YASHIL_PUBLIC_BASE_URL` берилмаган, стандарт қиймат ишчи домен | Синов серверининг `.env` ига `YASHIL_PUBLIC_BASE_URL=https://<синов-домени>` ёзиб, app'ни қайта ишга туширинг |
