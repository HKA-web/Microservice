## Requirements
- Python : 3.12.4
- Django : 5.2
- Node.js : v20+
- PostgreSQL
- Redis

---

## Cara Instalasi

### 1. Setup Backend (Python)
Buat dan aktifkan virtual environment, kemudian install dependencies:
```bash
# Windows
python -m venv env
.\env\Scripts\activate

# Install dependensi
pip install -r requirements.txt
```

### 2. Konfigurasi Sistem
Pastikan konfigurasi di `microservice.yaml` sudah sesuai dengan database PostgreSQL dan Redis Anda.

Jalankan migrasi database utama jika diperlukan:
```bash
python manage.py migrate
```

### 3. Jalankan Server
```bash
python manage.py runserver
```