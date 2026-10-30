# «Яшил маҳалла» модули — топшириладиган ҳужжатлар

STAT-URMON «Яшил маҳалла» модули (ТТ 8.0 таҳрир) бўйича ҳужжатлар тўплами. ТТ §19.1 да санаб ўтилган ишлаб чиқиш натижалари ва уларнинг жойи:

| ТТ §19.1 натижаси | Ҳужжат ёки манба |
|---|---|
| Ишлайдиган модул ва манба код | `src/apps/yashil/` (сервер), Forest-Web репозиторийси `src/features/yashil/`, `src/views/Dashboard/Yashil/` (интерфейс) |
| База схемаси ва миграциялар | `src/apps/yashil/models/`; миграциялар деплойда яратилади ва ҳар куни захирага олинади ([жойлаштириш](joylashtirish-va-tiklash.md)) |
| API тавсифи | [api.md](api.md), [openapi-yashil.yaml](openapi-yashil.yaml) |
| Роль-ваколат матрицаси | [rol-vakolat-matritsasi.md](rol-vakolat-matritsasi.md) |
| Ҳужжат шаблонлари ва имзо интеграцияси созламалари | [sozlamalar-pasporti.md](sozlamalar-pasporti.md) (3–4-бўлимлар) |
| Жойлаштириш ва тиклаш йўриқномаси | [joylashtirish-va-tiklash.md](joylashtirish-va-tiklash.md) |
| Фойдаланувчи қўлланмаси | [умумий қисм](qollanma-umumiy.md), [маҳалла](qollanma-mahalla.md), [уюшма](qollanma-uyushma.md), [етказиб берувчи (ўрмон хўжалиги ва ДМ)](qollanma-yetkazib-beruvchi.md), [кузатувчи](qollanma-kuzatuvchi.md), [модул маъмури](qollanma-maamur.md) |
| Синов баённомаси (Q01–Q36) | `python manage.py yashil_acceptance_protocol --out <файл>.docx` — автоматик қисм; қўлда текшириладиган устун синов серверида тўлдирилади |
| Ишчи муҳит параметрлари (ТТ §24) | [sozlamalar-pasporti.md](sozlamalar-pasporti.md) |
| Пилот ва ишга тушириш (ТТ §19.2) | [pilot-rejasi.md](pilot-rejasi.md) |

Расмлар (`rasmlar/`) локал синов муҳитида, намуна маълумотлар билан олинган; уларда ҳақиқий ташкилот ва шахс маълумотлари йўқ.

## Назорат буйруқлари

| Буйруқ | Вазифаси |
|---|---|
| `yashil_readiness [--strict]` | Пилот ва ишчи муҳитга тайёрлик: бириктиришлар, йўналишлар, имзоловчилар, календарь, каталог, бошланғич қолдиқлар |
| `yashil_integrity_check [--compare <файл>] [--strict]` | Ҳужжат хэшлари, имзолар, файллар, омбор ҳисоби; захирадан тиклашдан кейин солиштириш |
| `yashil_acceptance_protocol --out <файл>` | Q01–Q36 синов баённомаси (DOCX) |
| `yashil_openapi --out docs/yashil/openapi-yashil.yaml [--check]` | API тавсифини коддан яратиш ёки мослигини текшириш |
| `yashil_recalc_deadlines` | Очиқ буюртмалар муддат устунларини қайта ҳисоблаш |
| `docker/prod/backup-hourly.sh`, `docker/prod/restore-test.sh` | Соатлик захира ва тиклаш синови |
