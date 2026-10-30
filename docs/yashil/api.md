# «Яшил маҳалла» модули API тавсифи

Ушбу ҳужжат STAT-URMON «Яшил маҳалла» модули API шартномасини (ТТ §16.2, §21) тавсифлайди. Тўлиқ машина ўқийдиган тавсиф — [`openapi-yashil.yaml`](openapi-yashil.yaml) (OpenAPI 3.0). Файл коддан яратилади:

```bash
python manage.py yashil_openapi --out ../docs/yashil/openapi-yashil.yaml          # Forest-Back/src ичида
python manage.py yashil_openapi --out ../docs/yashil/openapi-yashil.yaml --check  # файл кодга мослигини текшириш
```

Ҳар бир амалнинг қисқа тавсифи, сўров ва жавоб тузилмаси `src/apps/yashil/openapi.py` да сақланади; `apps.yashil.tests.test_openapi` синови барча маршрутлар тавсифланганини ва схема хатосиз яратилишини текширади. Swagger саҳифаси ишчи серверда фақат платформа маъмури учун очиқ.

## 1. Умумий қоидалар

| Мавзу | Қоида |
|---|---|
| Манзил | `https://<api-домен>/api/v1/yashil/…`. Барча маршрутлар `/` билан тугайди. |
| Авторизация | STAT-URMON ягона кириши: `POST /api/v1/authentications/login/` → `access` токен (15 дақиқа) ва HttpOnly `refresh` cookie (1 кун); янгилаш — `POST /api/v1/authentications/token/refresh/`. Ҳар сўровда `Authorization: Bearer <access>`. |
| Кабинет | Бир нечта ташкилотга ваколати бор фойдаланувчи кабинетни `X-Yashil-Cabinet: <аъзолик ID>` сарлавҳаси билан танлайди; бўлмаса биринчи фаол аъзолик олинади. Кабинетлар рўйхати — `GET /me/`. Бегона кабинет ID — 403 `cabinet_forbidden`. |
| Тил | Хабарлар (`message`, `detail`), хабарномалар, ҳисобот экспорти ва филтр матнлари `Accept-Language` бўйича: `ru` — рус тилида, бошқа қиймат ёки сарлавҳасиз — ўзбек (лотин). Экспорт файли сўров пайтидаги тилда тузилади. Фойдаланувчи ёзган матн (изоҳ, сабаб, номлар) ўгирилмайди. Каталог маълумотларида `item_lat` — номнинг лотин ёзуви. |
| Ҳужжат тили | Буюртманома, далолатнома ва бекор қилиш ҳужжати яратилган пайтдаги `Accept-Language` тилида тузилади ва `content.lang` (`uz` / `ru`) да сақланади; HTML, PDF ва кўриниш шу тилда. Каталог номлари иккала тилда лотинда, маълумотнома номлари `uz` да лотинга ўгирилади, фойдаланувчи матни ўзгармайди. `lang` йўқ эски ҳужжатлар (template_version 1) кириллда қолади. Бекор қилиш ҳужжатида натижа матни — `result_label`. |
| Ваколат | Роль, кабинет тури, тайёрлаш/имзолаш ҳуқуқи ва объект кўлами ҳар сўровда серверда текширилади ([роль-ваколат матрицаси](rol-vakolat-matritsasi.md)). Кўламдан ташқари объект — 404 (мавжудлиги ошкор қилинмайди). |
| Версия | Буюртма ва акт `version_no` га эга. Ўзгартирувчи сўровда жорий `version_no` юборилади; эскиси бўлса 409 `version_conflict` — янги маълумотни очиш керак. |
| Такрор сўров | Ҳолатни ўзгартирувчи POST амаллар (жадвалда ¹) `Idempotency-Key` сарлавҳасини талаб қилади. Бир хил калит ва бир хил мазмун — аввалги жавоб қайтарилади, дубликат яратилмайди; бошқа мазмун — 409 `idempotency_mismatch`; калитсиз — 400 `idempotency_key_required`. Фақат 2xx/4xx жавоблар сақланади, 5xx дан кейин қайта уриниш амални бажаради. |
| Жавоб | Объект жавоби `id`, `version_no`, ҳолат (`state` / `status`, кирилл ёрлиғи `*_cyr`) ва `actions` — шу кабинет учун рухсат этилган кейинги амаллар рўйхатини (ТТ даги `next_action`) қайтаради. Рўйхатлар саҳифаланган: `count`, `next`, `previous`, `results`; `page`, `per_page`. |
| Сана ва сон | Сана — `YYYY-MM-DD`, вақт — ISO 8601 (UTC). Миқдорлар — ўнли сон матн кўринишида (`"12.5"`). |
| Файллар | Илова ва PDF ҳаволалари нисбий ва вақтинча имзоли (`?t=`); муддати ўтган ҳавола очилмайди. |
| Сўров лимити | Аноним — 30/дақ (QR текширув), фойдаланувчи — 600/дақ, экспорт — 10/дақ. Ошса 429. |

## 2. Хато шартномаси

Барча хатолар бир хил тузилмада қайтади (`YashilError`):

```json
{
  "error_code": "version_conflict",
  "field": "version_no",
  "message": "Буюртма бошқа фойдаланувчи томонидан ўзгартирилган — саҳифани янгиланг",
  "request_id": "3f2a…",
  "detail": {}
}
```

`request_id` — сўровдаги `X-Request-ID` сарлавҳаси (бўлса) ёки сервер берган идентификатор; мурожаатда шуни кўрсатинг. Махфий ички маълумот (стек, SQL, калит) жавобга чиқмайди.

| HTTP | Маъноси | Асосий `error_code` |
|---|---|---|
| 400 | Формат хатоси | `invalid_format`, `validation`, `required`, `invalid_file`, `idempotency_key_required` |
| 401 | Сессия йўқ ёки тугаган | `unauthenticated` |
| 403 | Ваколат йўқ | `forbidden`, `cabinet_forbidden`, `not_member`, `cannot_prepare`, `cannot_sign`, `signer_mismatch` |
| 404 | Объект топилмади ёки очиш ҳуқуқи йўқ | `not_found` |
| 409 | Версия ёки ҳолат тўқнашуви | `version_conflict`, `state_conflict`, `idempotency_mismatch`, `act_in_progress`, `cancel_pending`, `acceptance_exists` |
| 422 | Бизнес қоидаси | `qty_exceeds_remaining`, `norm_violation`, `stock_insufficient`, `reason_required`, `comment_required`, `import_has_errors`, … |
| 429 | Сўров лимити | `rate_limited`, `too_many_exports` |
| 503 | Ташқи хизмат (E-IMZO) вақтинча ишламайди | `eimzo_unavailable` |

## 3. ТТ §21 базавий маршрутлари ва якуний URLлар

| ТТ (§21) | Якуний маршрут (`/api/v1/yashil` дан кейин) | Изоҳ |
|---|---|---|
| `POST /yashil/orders` | `POST /orders/` | Тўлиқ бўлмаган қоралама мумкин |
| `PATCH /orders/{id}` | `PATCH /orders/{id}/` | Фақат қоралама ёки қайтарилган ҳолат |
| `POST /orders/{id}/document` | `POST /orders/{id}/document/` | Ҳужжат версияси ва имзо топшириғи |
| `POST /orders/{id}/submit` | `POST /orders/{id}/submit/` ¹ | Имзо ва хэш текширилади |
| `POST /orders/{id}/review` | `POST /orders/{id}/review/` ¹ | |
| `POST /orders/{id}/forward` | `POST /orders/{id}/forward/` ¹ | Имзодаги етказиб берувчи ўзгармайди |
| `POST /orders/{id}/return` | `POST /orders/{id}/return/` ¹ | Сабаб ва изоҳ |
| `POST /orders/{id}/accept` | `POST /orders/{id}/accept/` ¹ | Бир марта |
| `POST /orders/{id}/acts` | `POST /orders/{id}/acts/` ¹ | Қолган қабул ҳажми |
| `POST /acts/{id}/send` | `POST /acts/{id}/sign-task/` → `POST /acts/{id}/sign/` ¹ | Етказиб берувчи имзоси акт юборишдир |
| `POST /acts/{id}/approve` | `POST /acts/{id}/sign-task/` → `POST /acts/{id}/sign/` ¹ | Маҳалла имзоси актни қабул қилишдир |
| `POST /acts/{id}/return` | `POST /acts/{id}/return/` ¹ | Миқдор ва омбор ўзгармайди |
| `POST /stock/receipts` | `POST /stock/receipts/` ¹ | |
| `GET /orders, /stock, /map; POST /exports` | `GET /orders/`, `GET /stock/`, `GET /map/points/`, `POST /reports/exports/` | Кўлам серверда |

Актни юбориш ва қабул қилиш алоҳида маршрут эмас: имзо ўзи амални бажаради. Ким имзолаётганига қараб (етказиб берувчи ёки маҳалла) сервер ҳолатни ўзгартиради.

## 4. Имзолаш оқими

1. `POST /orders/{id}/document/` (ёки `POST /acts/{id}/sign-task/`) — сервер ҳужжатнинг ўзгармас версиясини, унинг хэшини ва имзоланадиган топшириқни (challenge) қайтаради.
2. Браузер E-IMZO орқали топшириқни имзолайди (PKCS#7).
3. `POST /orders/{id}/submit/` (ёки `POST /acts/{id}/sign/`) — имзо, ҳужжат версияси ва `Idempotency-Key` юборилади. Сервер имзони, хэшни ва имзоловчи ваколатини текширади; ҳолат, омбор ва аудит битта транзакцияда ўзгаради.
4. QR код `GET /verify/{token}/` саҳифасига олиб боради (кириш талаб этилмайди, шахсий маълумот чиқмайди). Мазмуни ўзгартирилган ҳужжат ҳақиқий деб кўрсатилмайди, алмаштирилган версия «алмаштирилган» деб белгиланади.

## 5. Буюртма ҳолатлари

| Код | Ҳолат |
|---|---|
| `draft` | Қоралама |
| `union_new` | Уюшмада янги |
| `union_review` | Уюшма кўриб чиқмоқда |
| `returned` | Маҳаллага қайтарилган |
| `supplier_new` | Етказиб берувчида янги |
| `supplier_review` | Етказиб берувчи кўриб чиқмоқда |
| `execution` | Ижрода |
| `partial` | Қисман бажарилган |
| `closed` | Бажарилган |
| `cancelled` | Бекор қилинган |

## 6. Маршрутлар рўйхати

¹ — `Idempotency-Key` сарлавҳаси мажбурий. Барча маршрутлар `/api/v1/yashil` дан кейин келади; `{…}` — UUID.

### Маълумотномалар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/calendar/` | Иш кунлари календари |
| GET | `/calendar/due/` | 3 ва 10 иш кунлик муддатлар ҳисоби |
| GET | `/catalog/` | Каталог (йўналиш бўйича) |
| GET | `/me/` | Фойдаланувчи кабинетлари ва фаол кабинет |
| GET | `/reference/districts/` | Туманлар |
| GET | `/reference/mahallas/` | Маҳаллалар (кабинет кўламида) |
| GET | `/reference/object-types/` | Объект турлари |
| GET | `/reference/regions/` | Вилоятлар |
| GET | `/reference/seasons/` | Мавсумлар |
| GET | `/suppliers/for-mahalla/{mahalla_id}/` | Маҳалла учун етказиб берувчилар (асосий, муқобил, ДМ, уюшма) |

### Буюртмалар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/orders/` | Буюртмалар рўйхати |
| POST | `/orders/` | Буюртма қораламасини яратиш |
| GET | `/orders/{order_id}/` | Буюртма тафсилоти |
| PATCH | `/orders/{order_id}/` | Қоралама ёки қайтарилган буюртмани таҳрирлаш |
| POST | `/orders/{order_id}/accept/` | Етказиб берувчи ижрога қабул қилади ¹ |
| POST | `/orders/{order_id}/acts/` | Етказишни қайд этиш ва акт қораламаси ¹ |
| POST | `/orders/{order_id}/attachments/` | Буюртмага файл илова қилиш |
| DELETE | `/orders/{order_id}/attachments/{attachment_id}/` | Иловани ўчириш (фақат таҳрирланадиган ҳолатда) |
| POST | `/orders/{order_id}/cancel/` | Бекор қилиш (қоралама — дарҳол, бошқалари — сўров) ¹ |
| POST | `/orders/{order_id}/document/` | Буюртманома ҳужжатини тайёрлаш ва имзо топшириғи |
| GET | `/orders/{order_id}/events/` | Ҳолатлар тарихи |
| POST | `/orders/{order_id}/forward/` | Уюшма етказиб берувчига йўллайди ¹ |
| POST | `/orders/{order_id}/return/` | Сабаб билан қайтариш ¹ |
| POST | `/orders/{order_id}/review/` | Уюшма кўриб чиқишни бошлайди ¹ |
| POST | `/orders/{order_id}/submit/` | Имзолаб юбориш ¹ |

### Бекор қилиш

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/cancel/` | Бекор қилиш сўровлари |
| GET | `/cancel/{request_id}/` | Бекор қилиш сўрови |
| POST | `/cancel/{request_id}/agree/` | Бекор қилишга рози бўлиш ¹ |
| POST | `/cancel/{request_id}/approve/` | Бекор қилишни тасдиқлаш ¹ |
| POST | `/cancel/{request_id}/reject/` | Бекор қилишни рад этиш ¹ |

### Далолатномалар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/acts/` | Актлар рўйхати |
| GET | `/acts/{act_id}/` | Акт тафсилоти |
| PATCH | `/acts/{act_id}/` | Акт қораламасини таҳрирлаш |
| POST | `/acts/{act_id}/attachments/` | Актга файл илова қилиш |
| DELETE | `/acts/{act_id}/attachments/{attachment_id}/` | Акт иловасини ўчириш |
| POST | `/acts/{act_id}/cancel/` | Акт қораламасини бекор қилиш ¹ |
| POST | `/acts/{act_id}/return/` | Маҳалла актни изоҳ билан қайтаради ¹ |
| POST | `/acts/{act_id}/sign/` | Актни имзолаш (етказиб берувчи — юбориш, маҳалла — қабул) ¹ |
| POST | `/acts/{act_id}/sign-task/` | Акт ҳужжатини тайёрлаш ва имзо топшириғи |

### Омбор

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/stock/` | Омбор қолдиқлари |
| GET | `/stock/capacity/` | ДМ хизмат қуввати |
| PUT | `/stock/capacity/` | ДМ хизмат қувватини киритиш |
| GET | `/stock/movements/` | Омбор ҳаракатлари |
| POST | `/stock/opening/` | Бошланғич қолдиқ ¹ |
| POST | `/stock/opening/import/` | Бошланғич қолдиқларни файлдан юклаш |
| GET | `/stock/organizations/` | Омбори бор етказиб берувчилар |
| POST | `/stock/receipts/` | Кирим ¹ |
| POST | `/stock/returns/` | Қайтарилган товар кирими ¹ |
| POST | `/stock/reversals/` | Ҳаракатни бекор қилиш сўрови ¹ |
| POST | `/stock/reversals/{movement_id}/approve/` | Бекор қилиш сўровини тасдиқлаш ¹ |
| POST | `/stock/reversals/{movement_id}/reject/` | Бекор қилиш сўровини рад этиш ¹ |

### Ҳисоботлар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/reports/exports/` | Экспорт вазифалари рўйхати |
| POST | `/reports/exports/` | Экспорт яратиш (кичиги дарҳол, каттаси фонда) |
| GET | `/reports/exports/{job_id}/` | Экспорт ҳолати ва юклаб олиш ҳаволаси |
| GET | `/reports/filters/` | Ҳисобот фильтрлари учун луғатлар |
| GET | `/reports/registry/` | Кабинетлар реестри (қатор — буюртма позицияси) |
| GET | `/reports/registry/summary/` | Реестр йиғиндиси |

### Статистика ва харита

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/map/points/` | Қабул қилинган буюртмалар харитаси |
| GET | `/stats/cards/` | Статистика карточкалари |
| GET | `/stats/organizations/` | Орқада қолаётган ташкилотлар |
| GET | `/stats/seedlings/` | Кўчатлар бўйича фарқ |

### Ҳужжатлар ва QR

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/documents/{version_id}/` | Ҳужжат версияси (мазмун, хэш, имзолар) |
| GET | `/documents/{version_id}/html/` | Ҳужжатнинг босма кўриниши (HTML) |
| GET | `/documents/{version_id}/pdf/` | Ҳужжат PDF ҳаволаси |
| GET | `/verify/{token}/` | QR орқали ҳужжатни текшириш (очиқ, шахсий маълумотсиз) |

### Хабарномалар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/notifications/` | Хабарномалар |
| POST | `/notifications/{notification_id}/read/` | Хабарномани ўқилган деб белгилаш |
| POST | `/notifications/read-all/` | Барчасини ўқилган деб белгилаш |

### Маъмурий созламалар

| Метод | Манзил | Амал |
|---|---|---|
| GET | `/admin/assignments/` | Маҳалла — хўжалик бириктиришлари |
| POST | `/admin/assignments/` | Бириктириш қўшиш |
| PATCH | `/admin/assignments/{id}/` | Бириктиришни ўзгартириш |
| DELETE | `/admin/assignments/{id}/` | Бириктиришни ўчириш |
| POST | `/admin/assignments/import/` | Бириктиришларни файлдан юклаш |
| GET | `/admin/audit/` | Маъмурий ўзгаришлар журнали |
| GET | `/admin/calendar/` | Календарь кунлари |
| POST | `/admin/calendar/` | Календарь кунини қўшиш |
| PATCH | `/admin/calendar/{id}/` | Календарь кунини ўзгартириш |
| DELETE | `/admin/calendar/{id}/` | Календарь кунини ўчириш |
| POST | `/admin/calendar/import/` | Календарни файлдан юклаш |
| GET | `/admin/capacity/` | ДМ хизмат қуввати (маъмур) |
| PUT | `/admin/capacity/` | ДМ хизмат қувватини киритиш (маъмур) |
| GET | `/admin/catalog/` | Каталог (маъмур) |
| POST | `/admin/catalog/` | Каталог позицияси қўшиш |
| PATCH | `/admin/catalog/{id}/` | Каталог позициясини ўзгартириш |
| DELETE | `/admin/catalog/{id}/` | Каталог позициясини ўчириш (фаолсизлантириш) |
| GET | `/admin/mahallas/` | Маҳаллалар маълумотномаси |
| POST | `/admin/mahallas/` | Маҳалла қўшиш |
| PATCH | `/admin/mahallas/{id}/` | Маҳаллани ўзгартириш |
| DELETE | `/admin/mahallas/{id}/` | Маҳаллани ўчириш (фаолсизлантириш) |
| POST | `/admin/mahallas/import/` | Маҳаллаларни файлдан юклаш |
| GET | `/admin/memberships/` | Кабинет аъзоликлари |
| POST | `/admin/memberships/` | Аъзолик қўшиш |
| PATCH | `/admin/memberships/{id}/` | Аъзоликни ўзгартириш |
| DELETE | `/admin/memberships/{id}/` | Аъзоликни ўчириш |
| GET | `/admin/organizations/search/` | Ташкилот қидириш |
| GET | `/admin/routes/` | Маҳалла — уюшма йўналишлари |
| POST | `/admin/routes/` | Йўналиш қўшиш |
| PATCH | `/admin/routes/{id}/` | Йўналишни ўзгартириш |
| DELETE | `/admin/routes/{id}/` | Йўналишни ўчириш |
| POST | `/admin/routes/import/` | Йўналишларни файлдан юклаш |
| GET | `/admin/settings/` | Бизнес қоидалари ва сиёсатлар |
| PUT | `/admin/settings/` | Қоида қийматини ўзгартириш (effective_from билан) |
| GET | `/admin/suppliers/` | Етказиб берувчилар |
| POST | `/admin/suppliers/` | Етказиб берувчи қўшиш |
| PATCH | `/admin/suppliers/{id}/` | Етказиб берувчини ўзгартириш |
| DELETE | `/admin/suppliers/{id}/` | Етказиб берувчини ўчириш |
| GET | `/admin/union-units/` | Уюшма бўлинмалари |
| POST | `/admin/union-units/` | Уюшма бўлинмаси қўшиш |
| PATCH | `/admin/union-units/{id}/` | Уюшма бўлинмасини ўзгартириш |
| DELETE | `/admin/union-units/{id}/` | Уюшма бўлинмасини ўчириш |
| GET | `/admin/users/search/` | Фойдаланувчи қидириш |
