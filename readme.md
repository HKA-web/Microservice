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

# Install dependensi (bisa menggunakan requirements-linux.txt atau wheel lokal)
pip install -r requirements-linux.txt
```

### 2. Konfigurasi Sistem
Pastikan konfigurasi di `microservice.yaml` sudah sesuai dengan database PostgreSQL dan Redis Anda:
- `DATABASES.postgres`: Database utama microservice
- `DATABASES.WHATSAPP`: Database penyimpanan WhatsApp (`session`, `command`, `inbox`, `outbox`, dll.)
- `CACHES.redis.LOCATION`: URL server Redis
- `WHATSAPP.PORT`: Port server WhatsApp engine (`3002`)
- `WHATSAPP.WEBHOOK_URL`: URL webhook ke Django (`http://127.0.0.1:8008/whatsapp/webhook/`)

Jalankan migrasi database utama jika diperlukan:
```bash
python manage.py migrate
```