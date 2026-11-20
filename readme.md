## Requirements
- Python : 3.12.4
- Django : 5.2
- Node.js : v18+ / v20+
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

### 3. Setup Database WhatsApp (DDL PostgreSQL)
Karena tabel modul WhatsApp menggunakan konfigurasi unmanaged (`managed = False`), tabel-tabel ini tidak dibuat otomatis oleh `python manage.py migrate`. Eksekusi query DDL pada database yang ditunjuk oleh `DATABASES.WHATSAPP`.

File query DDL dapat diakses di [whatsapp/schema.sql](whatsapp/schema.sql) dan data awal / contoh di [whatsapp/dummy_data.sql](whatsapp/dummy_data.sql):
```bash
# 1. Eksekusi query pembuatan schema & tabel
psql -h <host> -U <user> -d <db_name> -f whatsapp/schema.sql

# 2. (Opsional) Masukkan data awal / contoh command & session
psql -h <host> -U <user> -d <db_name> -f whatsapp/dummy_data.sql
```

### 4. Setup WhatsApp Machine (Node.js)
Masuk ke direktori engine WhatsApp dan install paket dependencies:
```bash
cd whatsapp/machine
npm install
npm run build
cd ../..
```

---

## Cara Menjalankan Layanan

Jalankan ketiga service berikut pada terminal terpisah:

### 1. Jalankan Django Server (Port 8008)
```bash
python manage.py runserver 8008
```

### 2. Jalankan Worker Antrean Huey (Inbox & Outbox)
```bash
python manage.py runhuey --queue whatsapp
```

### 3. Jalankan WhatsApp Engine (Port 3002)
```bash
cd whatsapp/machine
npm run dev
```

---

## Dokumentasi & Akses API

- **Django Base URL:** `http://localhost:8008`
- **WhatsApp Swagger UI:** `http://localhost:3002/docs`
- **Raw OpenAPI Spec:** `http://localhost:3002/openapi.json`
- **WhatsApp Management REST API:** `http://localhost:8008/whatsapp/api/`

---

## Database DDL (Schema WhatsApp)

Berikut adalah query DDL PostgreSQL lengkap untuk skema dan tabel-tabel modul WhatsApp:

```sql
-- =============================================================================
-- DDL SCHEMA WHATSAPP (PostgreSQL)
-- Database yang ditunjuk oleh konfigurasi DATABASES.WHATSAPP di microservice.yaml
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS "whatsapp";

-- -----------------------------------------------------------------------------
-- 1. Table: session
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."session" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "session_id" VARCHAR(25) NOT NULL,
    "session_name" VARCHAR(255) NOT NULL,
    "data" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "status" VARCHAR(100) NOT NULL DEFAULT 'STOPPED',
    "premised" BOOLEAN NOT NULL DEFAULT FALSE,
    "server" VARCHAR(255) NULL,
    CONSTRAINT "session_pkey" PRIMARY KEY ("session_id")
);

-- -----------------------------------------------------------------------------
-- 2. Table: template
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."template" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "template_id" VARCHAR(100) NOT NULL,
    "template_name" VARCHAR(255) NOT NULL,
    "template" TEXT NOT NULL,
    "status" VARCHAR(100) NOT NULL DEFAULT 'ACTIVE',
    "session_id" VARCHAR(25) NULL,
    CONSTRAINT "template_pkey" PRIMARY KEY ("template_id"),
    CONSTRAINT "template_template_session_id_c9403ca1_uniq" UNIQUE ("template", "session_id"),
    CONSTRAINT "template_session_id_f41b1804_fk_session_session_id" 
        FOREIGN KEY ("session_id") REFERENCES "whatsapp"."session"("session_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- 3. Table: command
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."command" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "command_id" VARCHAR(255) NOT NULL,
    "command_name" VARCHAR(255) NOT NULL,
    "command" VARCHAR(255) NOT NULL,
    "command_type" VARCHAR(50) NOT NULL DEFAULT 'TEXT',
    "process" TEXT[] NOT NULL DEFAULT '{}'::TEXT[],
    "required_parameter" VARCHAR(255)[] NULL,
    "check_parameter" BOOLEAN NOT NULL DEFAULT FALSE,
    "required_permission" BIGINT[] NULL,
    "check_permission" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_finish" BOOLEAN NOT NULL DEFAULT TRUE,
    "status" VARCHAR(100) NOT NULL DEFAULT 'ACTIVE',
    "mirror_id" VARCHAR(255) NULL,
    "session_id" VARCHAR(25) NULL,
    CONSTRAINT "command_pkey" PRIMARY KEY ("command_id"),
    CONSTRAINT "command_command_session_id_d74acc50_uniq" UNIQUE ("command", "session_id"),
    CONSTRAINT "command_mirror_id_91efbbe1_fk_command_command_id" 
        FOREIGN KEY ("mirror_id") REFERENCES "whatsapp"."command"("command_id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "command_session_id_e2cdb3a8_fk_session_session_id" 
        FOREIGN KEY ("session_id") REFERENCES "whatsapp"."session"("session_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- 4. Table: command_active
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."command_active" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "id" VARCHAR(25) NOT NULL,
    "parameter" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "command_by" VARCHAR(50) NOT NULL,
    "command_date" TIMESTAMPTZ NULL DEFAULT NOW(),
    "command_id" VARCHAR(255) NOT NULL,
    "previous_command_id" VARCHAR(255) NULL,
    CONSTRAINT "command_active_pkey" PRIMARY KEY ("id"),
    CONSTRAINT "command_active_command_id_command_by_77c2a9f8_uniq" UNIQUE ("command_id", "command_by"),
    CONSTRAINT "command_active_command_id_0e498e55_fk_command_command_id" 
        FOREIGN KEY ("command_id") REFERENCES "whatsapp"."command"("command_id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "command_active_previous_command_id_a76d6402_fk_command_c" 
        FOREIGN KEY ("previous_command_id") REFERENCES "whatsapp"."command"("command_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- 5. Table: inbox
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."inbox" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "inbox_id" VARCHAR(100) NOT NULL,
    "message" TEXT NULL,
    "message_type" VARCHAR(50) NOT NULL DEFAULT 'text',
    "inbox_by" VARCHAR(100) NOT NULL,
    "inbox_date" TIMESTAMPTZ NULL DEFAULT NOW(),
    "is_processed" BOOLEAN NOT NULL DEFAULT FALSE,
    "data" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "status" VARCHAR(100) NOT NULL DEFAULT 'RECEIVED',
    "session_id" VARCHAR(25) NULL,
    CONSTRAINT "inbox_pkey" PRIMARY KEY ("inbox_id"),
    CONSTRAINT "inbox_session_id_dac84edb_fk_session_session_id" 
        FOREIGN KEY ("session_id") REFERENCES "whatsapp"."session"("session_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- 6. Table: outbox
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."outbox" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "outbox_id" VARCHAR(100) NOT NULL,
    "sent_id" VARCHAR(100) NOT NULL,
    "message" TEXT NULL,
    "message_type" VARCHAR(50) NOT NULL DEFAULT 'text',
    "outbox_for" VARCHAR(100) NOT NULL,
    "prepare_date" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "retry" INTEGER NOT NULL DEFAULT 0,
    "scheduled" BOOLEAN NOT NULL DEFAULT FALSE,
    "scheduled_date" TIMESTAMPTZ NULL,
    "is_interactive" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_answered" BOOLEAN NOT NULL DEFAULT FALSE,
    "answered_date" TIMESTAMPTZ NULL,
    "data" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "status" VARCHAR(100) NOT NULL DEFAULT 'QUEUED',
    "session_id" VARCHAR(25) NULL,
    "template_id" VARCHAR(100) NULL,
    CONSTRAINT "outbox_pkey" PRIMARY KEY ("outbox_id"),
    CONSTRAINT "outbox_session_id_57a00989_fk_session_session_id" 
        FOREIGN KEY ("session_id") REFERENCES "whatsapp"."session"("session_id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "outbox_template_id_c5914d7e_fk_template_template_id" 
        FOREIGN KEY ("template_id") REFERENCES "whatsapp"."template"("template_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- 7. Table: sent
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "whatsapp"."sent" (
    "created" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "modified" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "is_removed" BOOLEAN NOT NULL DEFAULT FALSE,
    "read_only" BOOLEAN NOT NULL DEFAULT FALSE,
    "enable" BOOLEAN NOT NULL DEFAULT TRUE,
    "properties" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "description" TEXT NULL,
    "sent_id" VARCHAR(100) NOT NULL,
    "message" TEXT NULL,
    "message_type" VARCHAR(50) NOT NULL DEFAULT 'text',
    "sent_for" VARCHAR(100) NOT NULL,
    "sent_date" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "prepare_date" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    "retry" INTEGER NOT NULL DEFAULT 0,
    "scheduled" BOOLEAN NOT NULL DEFAULT FALSE,
    "scheduled_date" TIMESTAMPTZ NULL,
    "is_interactive" BOOLEAN NOT NULL DEFAULT FALSE,
    "is_answered" BOOLEAN NOT NULL DEFAULT FALSE,
    "answered_date" TIMESTAMPTZ NULL,
    "data" JSONB NOT NULL DEFAULT '{}'::jsonb,
    "status" VARCHAR(100) NOT NULL DEFAULT 'SENT',
    "session_id" VARCHAR(25) NULL,
    "template_id" VARCHAR(100) NULL,
    CONSTRAINT "sent_pkey" PRIMARY KEY ("sent_id"),
    CONSTRAINT "sent_session_id_7560a0b1_fk_session_session_id" 
        FOREIGN KEY ("session_id") REFERENCES "whatsapp"."session"("session_id") DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "sent_template_id_0211a79e_fk_template_template_id" 
        FOREIGN KEY ("template_id") REFERENCES "whatsapp"."template"("template_id") DEFERRABLE INITIALLY DEFERRED
);

-- -----------------------------------------------------------------------------
-- Indexes
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS "inbox_session_id_dac84edb" ON "whatsapp"."inbox" ("session_id");
CREATE INDEX IF NOT EXISTS "outbox_session_id_57a00989" ON "whatsapp"."outbox" ("session_id");
CREATE INDEX IF NOT EXISTS "outbox_template_id_c5914d7e" ON "whatsapp"."outbox" ("template_id");
CREATE INDEX IF NOT EXISTS "sent_session_id_7560a0b1" ON "whatsapp"."sent" ("session_id");
CREATE INDEX IF NOT EXISTS "sent_template_id_0211a79e" ON "whatsapp"."sent" ("template_id");
CREATE INDEX IF NOT EXISTS "command_session_id_e2cdb3a8" ON "whatsapp"."command" ("session_id");
CREATE INDEX IF NOT EXISTS "command_mirror_id_91efbbe1" ON "whatsapp"."command" ("mirror_id");
CREATE INDEX IF NOT EXISTS "command_active_command_id_0e498e55" ON "whatsapp"."command_active" ("command_id");
CREATE INDEX IF NOT EXISTS "command_active_previous_command_id_a76d6402" ON "whatsapp"."command_active" ("previous_command_id");
CREATE INDEX IF NOT EXISTS "template_session_id_f41b1804" ON "whatsapp"."template" ("session_id");
```

---

## Dummy Data SQL (Data Contoh)

```sql

-- 1. Dummy Session (Sesi WhatsApp Bot)
INSERT INTO "whatsapp"."session" (
    "created", "modified", "is_removed", "read_only", "enable", "properties",
    "session_id", "session_name", "status", "premised", "server", "data"
) VALUES (
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'default', 'Bot Utama WhatsApp', 'START', FALSE, '127.0.0.1', '{}'::jsonb
) ON CONFLICT ("session_id") DO UPDATE 
SET "session_name" = EXCLUDED."session_name", "status" = EXCLUDED."status";

-- 2. Dummy Template (Pesan Template Notifikasi/Balasan)
INSERT INTO "whatsapp"."template" (
    "created", "modified", "is_removed", "read_only", "enable", "properties",
    "template_id", "template_name", "template", "status", "session_id"
) VALUES 
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'TPL_WELCOME', 'Template Sambutan', 
    'Halo {{nama}}, terima kasih telah menghubungi layanan kami. Ketik *menu* untuk melihat opsi.', 
    'ACTIVE', 'default'
),
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'TPL_NOTIFIKASI', 'Template Notifikasi Transaksi', 
    'Pemberitahuan: Transaksi dengan ID {{transaksi_id}} berhasil diproses.', 
    'ACTIVE', 'default'
)
ON CONFLICT ("template_id") DO NOTHING;

-- 3. Dummy Command: Single-Turn (Perintah Langsung Selesai)
INSERT INTO "whatsapp"."command" (
    "created", "modified", "is_removed", "read_only", "enable", "properties",
    "command_id", "command_name", "command", "command_type", "process", 
    "check_parameter", "check_permission", "is_finish", "status", "session_id"
) VALUES 
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_HALO', 'Command Halo', 'halo', 'txt', 
    ARRAY['Halo! Selamat datang di Layanan Pelanggan. Ada yang bisa kami bantu? Ketik *menu* untuk informasi lebih lanjut.'], 
    FALSE, FALSE, TRUE, 'ACTIVE', 'default'
),
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_BANTUAN', 'Command Bantuan', 'bantuan', 'txt', 
    ARRAY['Berikut adalah perintah yang dapat Anda gunakan:' || E'\n' || '- *menu* : Melihat daftar layanan interaktif' || E'\n' || '- *halo* : Sapaan bot' || E'\n' || '- *info* : Memeriksa performa server bot' || E'\n' || '- *ping* : Mengecek status bot'], 
    FALSE, FALSE, TRUE, 'ACTIVE', 'default'
)
ON CONFLICT ("command_id") DO UPDATE 
SET "command" = EXCLUDED."command", "process" = EXCLUDED."process";

-- 4. Dummy Command: Multi-Turn / Percakapan Berkelanjutan (CommandActive)
-- User mengetik 'menu' -> Bot menyimpan CommandActive -> User membalas angka '1', '2', atau '3'
INSERT INTO "whatsapp"."command" (
    "created", "modified", "is_removed", "read_only", "enable", "properties",
    "command_id", "command_name", "command", "command_type", "process", 
    "check_parameter", "check_permission", "is_finish", "status", "session_id"
) VALUES 
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_MENU_UTAMA', 'Menu Utama Layanan', 'menu', 'txt', 
    ARRAY['Silakan pilih menu layanan kami:' || E'\n' || '1. Layanan Informasi Akun' || E'\n' || '2. Cek Status Pesanan' || E'\n' || '3. Hubungi Customer Service' || E'\n\n' || 'Ketik angka *1*, *2*, atau *3* untuk melanjutkan.'], 
    FALSE, FALSE, FALSE, 'ACTIVE', 'default'
),
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_MENU_1', 'Menu 1: Informasi Akun', 'menu/1', 'txt', 
    ARRAY['📌 *Layanan Informasi Akun*' || E'\n' || 'Untuk mengakses akun Anda, silakan kunjungi portal kami di https://example.com/akun'], 
    FALSE, FALSE, TRUE, 'ACTIVE', 'default'
),
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_MENU_2', 'Menu 2: Status Pesanan', 'menu/2', 'txt', 
    ARRAY['📦 *Status Pesanan*' || E'\n' || 'Pesanan Anda saat ini sedang dikemas oleh tim gudang. Terima kasih atas kesabaran Anda!'], 
    FALSE, FALSE, TRUE, 'ACTIVE', 'default'
),
(
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'CMD_MENU_3', 'Menu 3: Customer Service', 'menu/3', 'txt', 
    ARRAY['👨‍💼 *Customer Service*' || E'\n' || 'Mohon tunggu sejenak, petugas kami akan segera membalas pesan Anda.'], 
    FALSE, FALSE, TRUE, 'ACTIVE', 'default'
)
ON CONFLICT ("command_id") DO UPDATE 
SET "command" = EXCLUDED."command", "process" = EXCLUDED."process", "is_finish" = EXCLUDED."is_finish";

-- 5. Dummy Outbox (Contoh Antrean Pesan Keluar)
INSERT INTO "whatsapp"."outbox" (
    "created", "modified", "is_removed", "read_only", "enable", "properties",
    "outbox_id", "sent_id", "message", "message_type", "outbox_for", "prepare_date", "retry", "scheduled", 
    "is_interactive", "is_answered", "data", "status", "session_id"
) VALUES (
    NOW(), NOW(), FALSE, FALSE, TRUE, '{}'::jsonb,
    'OUTBOX_DUMMY_001', 'SENT_DUMMY_001', 
    'Halo! Ini adalah contoh pesan outbox WhatsApp.', 
    'conversation', '6281234567890', NOW(), 0, FALSE, FALSE, FALSE, 
    '{}'::jsonb, 'QUEUED', 'default'
)
ON CONFLICT ("outbox_id") DO NOTHING;
```
