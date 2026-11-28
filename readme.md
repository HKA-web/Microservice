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

### B. ntfy (Self-Hosted Portable + FCM Wakeup)
1. **Siapkan Binary `ntfy`:**
   - Pastikan `bin/ntfy/ntfy.exe` tersedia (atau unduh rilis Windows dari [GitHub Releases `binwiederhier/ntfy`](https://github.com/binwiederhier/ntfy/releases)).
2. **Aktifkan FCM Wakeup *(agar notif masuk saat app Android di-kill)*:**
   - Unduh **Firebase Service Account JSON** dari Firebase Console (*Project Settings → Service accounts → Generate new private key*).
   - Letakkan file `.json` tersebut di `notification/engine/ntfy/` *(otomatis diabaikan `.gitignore`)*, lalu arahkan `firebase-key-file` di [server.yml](engine/ntfy/server.yml) ke path file tersebut.
   - Pastikan aplikasi Android (`ntfy_app`) memakai `android/app/google-services.json` dari project Firebase yang **sama**.
3. **Jalankan Service (3 terminal):**
   ```powershell
   .\env\Scripts\python.exe manage.py runntfy
   .\env\Scripts\python.exe manage.py runserver 8008
   .\env\Scripts\python.exe manage.py runhuey --queue notification
   ```
   *(Jika key FCM terbaca, terminal `runntfy` akan menampilkan `FCM wakeup aktif` dan server berjalan di `http://127.0.0.1:8085` tanpa login).*