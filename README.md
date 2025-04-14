# 🌳 Statik-Urmon

**Statik-Urmon** — is a digital monitoring and management system developed for the Ministry of Ecology, Environmental Protection and Climate Change of the Republic of Uzbekistan, specifically for the city of Tashkent. The goal of this system is to monitor, map, and manage artificial (static) forests located in and around urban areas.

---

## 📌 Project Purpose

This system aims to improve the ecological condition by automating the processes of monitoring and expanding green areas. Key features include:

- Registering static forest zones
- Determining geolocation via GPS
- Collecting forest-related statistics
- Recording inspections carried out by employees
- Visualizing green areas on an online map

---

## 🔧 Technologies Used

- **Python** & **Django** –  For backend logic
- **PostgreSQL** – Database management
- **Docker** –Containerization of the project
- **Celery** & **Redis** – For asynchronous task handling
- **GitHub Actions** – CI/CD integration
- **Mapbox / LeafletJS** –  For mapping and geolocation features

---

## 🗂️ Main Project Modules

| Module name   | Description |
|---------------|---------|
| `forests`     | CRUD operations for static forests |
| `inspections` |Reports on forest condition inspections |
| `users`       | Management of staff and inspection teams |
| `reports`     | Annual and monthly statistical analyses |
| `api`         | API endpoints for mobile applications and external systems|

---

## 🚀 Installation (Local Development)

```bash
git clone https://github.com/YOUR_ORG/statik-urmon.git
cd statik-urmon
cp .env.example .env
docker-compose up --build