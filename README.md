# 🛡️ Asset Management System (EASM)

Hệ thống quản lý tài sản kỹ thuật số — External Attack Surface Management.  
Xây dựng với **FastAPI** + **Next.js 14** + **PostgreSQL**.

**Họ tên:** Ngô Văn Sang  
**Repository:** https://github.com/SANG01022005/asset-management-python  
**Branch:** `homework`  
**Demo:** https://sang-asset.duckdns.org  
**Demo Swagger:** http://42.96.43.186:8001/docs
---


## 📑 Mục Lục
- [Bài đã hoàn thành](#bài-đã-hoàn-thành)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cài đặt và chạy](#cài-đặt-và-chạy)
- [API Documentation](#api-documentation)
- [Unit Tests](#unit-tests)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deploy CMC Cloud VM](#deploy-cloud-vm)
- [HTTPS với Caddy](#https-với-caddy)

---

---

## 📊 Bài đã hoàn thành

| Bài | Mô tả | Điểm | Trạng thái |
|---|---|---|---|
| Bài 1 | IP Scanner (Geolocation + ASN) + Port Scanner | 25 | ✅ |
| Bài 2 | Unit Tests — ~127 tests, coverage 68%+ | 25 | ✅ |
| Bài 3 | Frontend Next.js 14 — list/create/scan/stats | 20 | ✅ |
| Bài 4 | CI/CD GitHub Actions — pytest + bandit + safety + gitleaks | 25 | ✅ |
| Bài 5 | Docker Compose — db + backend + frontend | 15 | ✅ |
| Bài 6 | Asset Tags + Export Reports (CSV + JSON) | 15 | ✅ Bonus |
| Bài 7 | Deploy CloudCMC VM — 42.96.43.186 | 20 | ✅ Bonus |
| Bài 8 | DuckDNS + HTTPS/TLS Caddy | 15 | ✅ Bonus |

---

## 🏗️ Kiến trúc hệ thống

```
asset-management-python/                 ← ROOT REPO
├── .github/
│   └── workflows/
│       └── ci.yml                       # Bài 4: CI — pytest + bandit + safety + gitleaks
├── asset-management-backend/            # Bài 1: FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── assets.py               # CRUD endpoints
│   │   │   ├── health.py               # Health check
│   │   │   ├── scan.py                 # Direct scan endpoints
│   │   │   ├── scan_router.py          # Background scan jobs
│   │   │   ├── tags_router.py          # Bài 6.2: Asset Tags
│   │   │   └── export_router.py        # Bài 6.5: Export Reports
│   │   ├── domain/
│   │   │   ├── models.py               # SQLAlchemy ORM
│   │   │   ├── schemas.py              # Pydantic schemas
│   │   │   ├── scan_schemas.py         # Scan job schemas
│   │   │   ├── scan_service.py         # Background scan logic
│   │   │   └── scanners/
│   │   │       ├── base_scanner.py     # Abstract base
│   │   │       ├── ip_scanner.py       # IP Geolocation + ASN
│   │   │       └── port_scanner.py     # TCP Port scanner
│   │   └── infrastructure/
│   │       └── database.py             # DB connection + retry
│   ├── tests/                          # Bài 2: Unit Tests
│   │   ├── conftest.py                 # Fixtures: SQLite + mock lifespan
│   │   ├── test_api.py                 # API integration tests
│   │   ├── test_models.py              # ORM model tests
│   │   ├── test_ip_scanner.py          # IP Scanner unit tests
│   │   ├── test_port_scanner.py        # Port Scanner unit tests
│   │   ├── test_scan_service.py        # Scan service tests
│   │   └── test_tags_export.py         # Tags + Export tests
│   ├── main.py
│   ├── Dockerfile                      # Bài 5: Docker
│   ├── requirements.txt
│   ├── requirements-test.txt
│   └── pytest.ini
├── asset-management-frontend/          # Bài 3: Next.js 14 Frontend
│   ├── app/
│   │   ├── page.tsx                    # Main UI (list/create/stats)
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   └── page.module.css
│   ├── next.config.js                  # Rewrite /api/* → backend
│   ├── tsconfig.json                   # target: ES2017
│   └── Dockerfile                      # Next.js standalone
├── docker-compose.yml                  # Bài 5: Docker Compose
├── .env
├── .env.example
└── README.md
```

---

## 🚀 Cài đặt và chạy

### Option 1 — Docker Compose (Khuyến nghị)

```bash
# 1. Clone repo
git clone https://github.com/SANG01022005/asset-management-python.git
cd asset-management-python
git checkout homework

# 2. Tạo .env
cp .env.example .env
# Điền POSTGRES_PASSWORD vào .env

# 3. Build và chạy
docker compose up -d --build

# 4. Kiểm tra
docker compose ps
```

| Service | URL | Mô tả |
|---|---|---|
| Frontend | http://localhost:3000 | Next.js UI |
| Backend | http://localhost:8080/docs | Swagger API |
| Health | http://localhost:8080/health | Health check |

---

### Option 2 — Local Development

#### Backend

```bash
cd asset-management-backend

# Tạo virtual environment
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# Cài dependencies
pip install -r requirements.txt

# Tạo .env
cp .env.example .env
# Điền DATABASE_URL

# Chạy
python main.py
# → http://localhost:8080/docs
```

#### Frontend

```bash
cd asset-management-frontend
npm install
npm run dev
# → http://localhost:3000
```

---

## 📖 API Documentation

**Local Swagger UI:** http://localhost:8080/docs  

### Assets

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/health` | Health check + DB status |
| POST | `/assets/batch` | Tạo nhiều assets (201) |
| DELETE | `/assets/batch?ids=...` | Xóa nhiều assets |
| GET | `/assets` | Danh sách (phân trang + filter) |
| GET | `/assets/search?q=` | Tìm kiếm theo tên |
| GET | `/assets/stats` | Thống kê theo type/status |
| GET | `/assets/count` | Đếm assets |

### Scan

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/assets/{id}/scan` | Khởi tạo background scan (202) |
| GET | `/scan/jobs/{id}` | Poll scan job status |
| GET | `/scan/jobs` | Danh sách scan jobs |
| DELETE | `/scan/jobs/{id}` | Xóa scan job |
| POST | `/scan/ip` | IP Geolocation trực tiếp |
| POST | `/scan/ports` | Port scan (internal IPs only) |

### Tags (Bài 6.2)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/tags` | Danh sách tags |
| POST | `/tags` | Tạo tag |
| DELETE | `/tags/{id}` | Xóa tag |
| POST | `/assets/{id}/tags` | Gán tags cho asset |
| GET | `/assets/{id}/tags` | Tags của asset |
| DELETE | `/assets/{id}/tags/{tag_id}` | Xóa tag khỏi asset |

### Export (Bài 6.5)

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/export/assets` | Export CSV assets |
| GET | `/export/scan-results` | Export CSV scan results |
| GET | `/export/report` | JSON summary report |

### Ví dụ curl

```bash
# Tạo asset
curl -X POST http://localhost:8080/assets/batch \
  -H "Content-Type: application/json" \
  -d '{"assets":[{"name":"google.com","type":"domain","status":"active"}]}'

# Khởi tạo scan
curl -X POST http://localhost:8080/assets/{asset_id}/scan

# Poll kết quả
curl http://localhost:8080/scan/jobs/{job_id}

# Export CSV
curl http://localhost:8080/export/assets -o assets.csv

# Tạo tag
curl -X POST http://localhost:8080/tags \
  -H "Content-Type: application/json" \
  -d '{"name":"production","color":"#22d3a0"}'
```

---

## 🧪 Unit Tests

```bash
cd asset-management-backend

# Cài test dependencies
pip install -r requirements-test.txt

# Chạy toàn bộ tests
python -m pytest tests/ -v

# Chạy với coverage report
python -m pytest tests/ --cov=app --cov-report=html

# Mở báo cáo HTML
start htmlcov/index.html   # Windows
open htmlcov/index.html    # Mac
```

### Kết quả

| File test | Tests | Module được test |
|---|---|---|
| `test_api.py` | ~40 | Tất cả HTTP endpoints |
| `test_models.py` | ~16 | SQLAlchemy ORM models |
| `test_ip_scanner.py` | ~13 | IP Geolocation scanner |
| `test_port_scanner.py` | ~24 | TCP Port scanner |
| `test_scan_service.py` | ~4 | Background scan service |
| `test_tags_export.py` | ~30 | Tags + Export API |
| **Tổng** | **~127** | **Coverage: 68%+** |

### Chiến lược test

- **SQLite in-memory** — không cần PostgreSQL thật
- **Mock lifespan** — tránh `connect_with_retry()` crash khi test
- **Patch đúng path** — patch tại nơi import, không phải nơi định nghĩa
- **`joinedload`** — tránh lazy loading sau khi session đóng

---

## ⚙️ CI/CD Pipeline (Bài 4)

Pipeline chạy tự động khi tạo **Pull Request vào `main`**:

```
PR → main
  ├── 🧪 pytest + coverage (fail-under=20%)
  ├── 🔒 Bandit — SAST, phát hiện SQL injection, unsafe ops
  ├── 🔒 Safety — CVE check cho dependencies
  ├── 🔒 Gitleaks — phát hiện hardcoded secrets
  └── ✅ Gate — block merge nếu bất kỳ job nào fail
```

### Setup Branch Protection

Vào **GitHub → Settings → Branches → Add rule**:
- Branch: `main`
- ✅ Require status checks: `✅ All checks passed`
- ✅ Require branches to be up to date

### Xem kết quả

```
https://github.com/SANG01022005/asset-management-python/actions
```

---

## ☁️ Deploy Cloud VM — CloudCMC (Bài 7)

**VM IP:** `42.96.43.186`  
**OS:** Ubuntu 22.04  
**Provider:** CloudCMC  

```bash
# SSH vào VM
ssh root@42.96.43.186

# Clone và deploy
git clone https://github.com/SANG01022005/asset-management-python.git
cd asset-management-python
git checkout homework
cp .env.example .env && nano .env

docker compose up -d --build
docker compose ps
```

**Kết quả:**

```
NAME             STATUS      PORTS
asset_db         Up (healthy) 0.0.0.0:5432->5432/tcp
asset_backend    Up (healthy) 0.0.0.0:8080->8080/tcp
asset_frontend   Up           0.0.0.0:3000->3000/tcp
```

---

## 🔒 HTTPS với Caddy + DuckDNS (Bài 8)

**Domain:** https://sang-asset.duckdns.org  
**SSL:** Let's Encrypt (tự động qua DNS challenge)  
**Reverse proxy:** Caddy  

```bash
# Caddyfile
{
    acme_dns duckdns <DUCKDNS_TOKEN>
}

sang-asset.duckdns.org {
    handle /api/* {
        uri strip_prefix /api
        reverse_proxy localhost:8080
    }
    handle {
        reverse_proxy localhost:3000
    }
}
```

```bash
# Kiểm tra HTTPS
curl -I https://sang-asset.duckdns.org
# HTTP/2 200 ✅
# via: 1.1 Caddy ✅
```

---

## 📋 Biến môi trường

```env
# .env (root — dùng cho Docker Compose)
POSTGRES_DB=my_assets
POSTGRES_USER=sang
POSTGRES_PASSWORD=your_password
CORS_ORIGINS=http://localhost,http://localhost:3000
VITE_API_BASE_URL=
```

```env
# asset-management-backend/.env (local development)
DATABASE_URL=postgresql://sang:password@localhost:5432/my_assets
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

## 🔗 Links

| Mô tả | URL |
|---|---|
| GitHub Repository | https://github.com/SANG01022005/asset-management-python |
| Frontend (HTTPS) | https://sang-asset.duckdns.org |
| Backend Swagger | http://42.96.43.186:8080/docs |
| GitHub Actions | https://github.com/SANG01022005/asset-management-python/actions |
| Branch | `homework` |