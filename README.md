# 🌳 Statik-Urmon

**Statik-Urmon** — bu Toshkentdagi O‘zbekiston Respublikasi Ekologiya, atrof-muhitni muhofaza qilish va iqlim o‘zgarishi vazirligi uchun ishlab chiqilgan raqamli monitoring va boshqaruv tizimi bo‘lib, shahar va shahar atrofi hududlaridagi sun’iy (statik) o‘rmonlarni nazorat qilish, xaritalash va boshqarishni maqsad qilgan.

---

## 📌 Loyiha maqsadi

Ushbu tizim orqali ekologik holatni yaxshilash, yashil hududlarni nazorat ostida saqlash va ularni kengaytirish vazifalari avtomatlashtiriladi. Shu bilan birga:

- Statik o‘rmon hududlarini ro‘yxatdan o‘tkazish
- GPS orqali geolokatsiyasini aniqlash
- O‘rmonlarga oid statistikani yig‘ish
- Hodimlar tomonidan o‘tkazilgan inspeksiyalarni qayd etish
- Yashil hududlarni onlayn xaritada vizualizatsiya qilish

---

## 🔧 Texnologiyalar

- **Python** & **Django** – Backend logikasi uchun
- **PostgreSQL** – Ma’lumotlar ombori
- **Docker** – Loyihani konteynerlash
- **Celery** & **Redis** – Asinxron vazifalar uchun
- **GitHub Actions** – CI/CD integratsiyasi
- **Mapbox / LeafletJS** – Xarita va geolokatsiyalar bilan ishlash

---

## 🗂️ Loyihaning asosiy modullari

| Modul nomi | Tavsifi |
|------------|---------|
| `forests` | Statik o‘rmonlar bo‘yicha CRUD amallar |
| `inspections` | O‘rmon holatini tekshiruvlar bo‘yicha hisobotlar |
| `users` | Hodimlar va inspeksiya guruhlari boshqaruvi |
| `reports` | Yillik va oylik statistik tahlillar |
| `api` | Mobil ilovalar va tashqi tizimlar uchun API endpointlar |

---

## 🚀 O‘rnatish (Local Development)

```bash
git clone https://github.com/YOUR_ORG/statik-urmon.git
cd statik-urmon
cp .env.example .env
docker-compose up --build
# Forest-Back
