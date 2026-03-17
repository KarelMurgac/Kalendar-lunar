# ☽ Lunar Legion Guild Calendar

Flask aplikace pro správu guild eventů s veřejným kalendářem a admin rozhraním.

## Funkce
- 📅 Veřejný interaktivní kalendář (FullCalendar.js)
- 🔐 Admin přihlášení (Flask-Login)
- 🏷️ Kategorie eventů s barvami
- 🔁 Opakující se eventy (denně / týdně / měsíčně)
- 🗄️ SQLite databáze (žádný server)

---

## Lokální spuštění

```bash
# 1. Nainstaluj závislosti
pip install -r requirements.txt

# 2. Zkopíruj a uprav .env
cp .env.example .env
# Změň SECRET_KEY a ADMIN_PASSWORD!

# 3. Spusť app (vytvoří DB + výchozí admin)
python app.py
```

Aplikace poběží na http://localhost:5000  
Admin: http://localhost:5000/admin/login  
Výchozí přihlášení: `admin` / `lunarlegion123`

---

## Deploy na Render.com (doporučeno – Python free tier)

1. Vytvoř účet na [render.com](https://render.com)
2. **New → Web Service** → připoj svůj GitHub repozitář
3. Nastav:
   - **Runtime:** Python 3
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn app:app`
4. Přidej **Environment Variables:**
   - `SECRET_KEY` = (vygeneruj náhodný řetězec)
   - `ADMIN_PASSWORD` = tvoje heslo

> Nezapomeň přidat `gunicorn` do `requirements.txt` pro produkční deploy!

### Pro produkci přidej do requirements.txt:
```
gunicorn==21.2.0
```

---

## Struktura projektu
```
lunar-legion/
├── app.py              # Hlavní Flask app, routes
├── models.py           # SQLAlchemy modely
├── extensions.py       # db, login_manager
├── requirements.txt
├── .env.example
├── templates/
│   ├── base.html
│   ├── calendar.html   # Veřejný kalendář
│   └── admin/
│       ├── login.html
│       ├── dashboard.html
│       ├── event_form.html
│       └── categories.html
└── static/
    └── css/style.css
```

---

## Přidání dalšího admina

```python
# V Python shellu nebo přidej dočasnou route
from app import app
from extensions import db
from models import Admin

with app.app_context():
    a = Admin(username="novyadmin")
    a.set_password("heslo123")
    db.session.add(a)
    db.session.commit()
```
