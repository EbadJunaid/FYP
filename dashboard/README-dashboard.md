# SSL Certificate Analytics Dashboard

<!--
  BADGES — notes / TODO (these reflect the repository's real state at setup time):
  • CI / Build: no GitHub Actions workflow exists yet. After adding one at
    `.github/workflows/ci.yml`, replace the static CI badge below with the live one:
    https://img.shields.io/github/actions/workflow/status/EbadJunaid/FYP/ci.yml?branch=main&logo=githubactions&label=CI
  • Release: no Git tag / GitHub Release exists yet, so the Release badge will render
    "no releases" until you publish one (e.g. `git tag v1.0.0 && git push --tags`).
  • License: no LICENSE file exists yet. After adding one (e.g. MIT), replace the static
    License badge below with the auto-detecting one: https://img.shields.io/github/license/EbadJunaid/FYP
  • This dashboard is a Python (Django) + TypeScript (Next.js) app — there is no C++/CMake,
    so the "language version" and "build system version" badges are mapped to the real
    toolchain: Python 3.11+, Node.js 18+, and Django 5.
-->


A full‑stack web application for **exploring and auditing SSL/TLS certificates at scale**.
It takes the certificates collected by this project's crawlers and turns them into interactive charts, tables, and security reports — Certificate Authority market share, encryption strength, validity periods, shared‑key reuse, SAN sprawl,
signature/hash algorithms, renewal trends, and a ranked **vulnerabilities** view.

- **Backend:** Django 5 (REST‑style JSON API) talking directly to **MongoDB** via `pymongo`, with optional **Redis** caching.
- **Frontend:** Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4, fetching data with **SWR** and drawing charts with **Recharts**.

> **New to this project? Read this whole file top‑to‑bottom once, then follow
> [Part 1 → Part 5](#-how-to-run-step-by-step-beginner-friendly) in order.** The single most
> common reason the dashboard shows empty pages is **missing data in MongoDB** — see
> [⚠️ The dataset requirement](#️-the-dataset-requirement).

---

## Table of contents

1. [What the dashboard does](#-what-the-dashboard-does)
2. [Architecture at a glance](#-architecture-at-a-glance)
3. [Tech stack](#-tech-stack)
4. [⚠️ The dataset requirement](#️-the-dataset-requirement)
5. [Prerequisites (install these once)](#-prerequisites-install-these-once)
6. [How to run — step by step](#-how-to-run-step-by-step-beginner-friendly)
7. [Configuration reference](#-configuration-reference)
8. [API endpoints](#-api-endpoints)
9. [Project structure](#-project-structure)
10. [Troubleshooting](#-troubleshooting)

---

## 🔎 What the dashboard does

The dashboard reads a large collection of parsed certificates and presents them across **18 pages**.
Each page is a different "lens" on the same dataset:

| Page (URL under `/dashboard`) | What it shows |
|---|---|
| `overview` | Home page: total / active / expiring‑soon / expired certificate counts, plus a searchable, paginated certificate table. |
| `ca-analytics` | Certificate Authority market share, top CAs, issuer × validation‑level matrix, self‑signed analysis. |
| `validity-analytics` | Validity period analysis — average lifetime, expiring in 30/90 days, compliance with the 398‑day rule, issuance timeline. |
| `signature-hash` | Signature algorithms, hash compliance %, weak‑hash alerts, key‑size distribution, adoption trends. |
| `san-analytics` | Subject Alternative Names — SANs per certificate, wildcard vs standard, top TLDs, multi‑domain ("blast radius") certs. |
| `shared-keys` | Public‑key **reuse** detection (a security risk): groups of certificates sharing the same key. Drill into a group via `shared-keys/[publicKeyHash]`. |
| `vulnerabilities` | A **ranked risk view** scoring each certificate. See [`vulnerablities.md`](./vulnerablities.md) for the exact scoring formula. |
| `active-vs-expired` | Detailed breakdown of active, expiring, and expired certificates |
| `issuer-countries` | Distribution of certificates by country — e.g. how many belong to Pakistan (`.pk`), based on our dataset. |
| `cas-vs-domains` | Shows how many certificates each Certificate Authority has issued — e.g. how many were issued by Let's Encrypt |

Two extra detail pages:

- `/certificate/[id]` — full inspection of a single certificate (validity, issuer, subject, fingerprints, SANs, key usage, ZLint results etc).
- `/dashboard/shared-keys/[publicKeyHash]` — every certificate that shares one public key.

**Key cross‑cutting features**

- **Scope switcher** — the same physical database can be sliced by country (Global, Pakistan, India, …). The frontend appends a `?scope=` parameter to every request; the backend filters accordingly. (Switcher UI in the header; backed by `Scopes.json`.)
- **Dark / light theme**, global search and advanced filtering. 

---

## 🏗 Architecture at a glance

```
                 Browser (you)
                       │  http://localhost:3000
                       ▼
        ┌──────────────────────────────┐
        │   Frontend — Next.js 16       │   React 19 + Tailwind v4 + SWR + Recharts
        │   src/app/dashboard/*         │
        └──────────────┬───────────────┘
                       │  fetch JSON  →  http://localhost:8000/api/...?scope=all
                       ▼
        ┌──────────────────────────────┐
        │   Backend — Django 5          │   views → controllers → db_queries
        │   certificates/ app           │   (+ optional Redis cache)
        └──────────────┬───────────────┘
                       │  pymongo
                       ▼
        ┌──────────────────────────────┐
        │   MongoDB  (localhost:27017)  │
        │   • hugging-face-700k         │  ← raw parsed certificates
        │   • hugging-face-700k-results │  ← PRE-COMPUTED analytics (for speed)
        └──────────────────────────────┘
```

**Backend request flow (per analytics module):** every sub‑module under `certificates/`
(`ca_analytics`, `overview`, `san_analytics`, `shared_keys`, `Tignature_hash`,
`validity_analysis`, `shared_apis`) follows the same clean layering:

```
urls.py  →  views.py  →  controllers.py  →  db_queries.py  →  MongoDB
                              │
                              └─ checks Redis cache first (if available)
```

To keep pages fast, heavy aggregations are **pre‑computed** into the `*-results` database by the
scripts in `pre-compute-scripts/`. The live API mostly reads those
pre‑computed collections instead of scanning millions of documents on every click.

---

## 🧰 Tech stack

| Layer | Technology | Version (from code) |
|---|---|---|
| Frontend framework | Next.js (App Router) | 16.1.1 |
| UI library | React / React DOM | 19.2.3 |
| Language | TypeScript | 5.x |
| Styling | Tailwind CSS | v4 |
| Data fetching | SWR | 2.3.x |
| Charts | Recharts | 3.6.x |
| Icons | @heroicons/react | 2.2.x |
| Backend framework | Django | 5.x (built on 5.2) |
| Mongo driver | pymongo | 4.6+ |
| CORS | django‑cors‑headers | 4.3+ |
| Cache (optional) | redis | 5.0+ |
| Database | MongoDB | 27017 (local) |

> Note: The project talks to MongoDB **directly with `pymongo`** (not Djongo, and not Django REST
> Framework). Django's own `DATABASES` setting only uses a tiny local SQLite file (`internal_db`)
> for Django internals (admin/sessions). All certificate data lives in MongoDB.





## ⚠️ The dataset requirement 

This repository contains the application code, **not** the certificate dataset. The dashboard needs two MongoDB databases to exist and be populated before it can show any data:

| Database | Purpose 
|---|---|
| `hugging-face-700k` | The raw parsed certificates (collection: `certificates`)
| `hugging-face-700k-results` | Pre-computed analytics collections (CA stats, geo distribution, SAN, shared keys, signature/hash, validity)

If you skip this step, the backend will still start, but the pages will be empty or throw errors, because the queries have no data to return. The database names are configured in `backend/certificates/db.py`.

💡 Not sure what the data actually looks like? Check [`data-sample.json`](data-sample.json) for a quick preview before downloading or crawling anything.


You have **three ways** to get the data in, from fastest to most flexible:

### Option 1 — Use our ready-made dataset (fastest)
Download both the main dataset and the pre-computed results dataset from our [SSL Certificates Dataset on Hugging Face](https://huggingface.co/datasets/EbadJunaid/hugging-face-700k/tree/main).

After downloading, you should have two files:
- `hugging-face-700k.archive.gz`
- `hugging-face-700k-results.archive.gz`

Restore the dump into MongoDB by running the following commands.

**Step 1: Move to the folder where you downloaded the datsets**


**For Windows:**
```powershell
cd path\to\downloaded\files
```

**For Linux/macOS:**
```bash
cd path/to/downloaded/files
```

**Step 2: Restore both databases**

The `mongorestore` command is the same on Windows, macOS, and Linux, as long as MongoDB Database Tools are installed:

```bash
mongorestore --archive="hugging-face-700k.archive.gz" --gzip
mongorestore --archive="hugging-face-700k-results.archive.gz" --gzip
```

- The first command restores the main dataset (`hugging-face-700k`).
- The second command restores the pre-computed results dataset (`hugging-face-700k-results`).
- For this option, **run both commands** — you need both databases.

**Note:** The pre-computed results stay accurate almost all the time. The only part that can go slightly out of date is the issuance timeline graph (the monthly analysis), and only once a full month has passed — it just won't show the newest month yet. Everything else stays correct.

### Option 2 — Keep the results always up to date
If you want the pre-computed results to always be 100% current, you can build them yourself instead of using our ready-made version.

**Step 1:** Download only the [main dataset](https://huggingface.co/datasets/EbadJunaid/hugging-face-700k/blob/main/hugging-face-700k.archive.gz) and restore it:

```bash
mongorestore --archive="hugging-face-700k.archive.gz" --gzip
```

(Run this from the folder where you downloaded the file, same as in Option 1.)

**Step 2:** Run the pre-compute script:

Open your terminal and navigate to the pre-compute scripts folder inside the repo and then run the file by using below commands:

**For Windows:**
```powershell
cd dashboard\backend\pre-compute-scripts\generic
python run-generic.py
```

**For Linux/macOS:**
```bash
cd dashboard/backend/pre-compute-scripts/generic
python3 run-generic.py
```


This script rebuilds the pre-computed results from scratch. It processes a large amount of data, so it takes about **1 hour** to finish. Once done, both databases will be fully in sync.





### Option 3 — Run the crawler yourself (most flexible)
This is the most advanced option. Use this if you want freshly-crawled data instead of a static dump.

The crawler script is `crawler-args.py`. By default, it crawls our list of domains ([`global-dataset.csv`](../ct-logs-renewal-pipeline/global-dataset.csv)) and writes to the default database. You can optionally point it at your own CSV file and/or your own database name using command-line flags — no code editing required for basic use.

**Step 1: Move to the crawler folder**

**Windows:**
```powershell
cd ..\ssl-certificates-crawler\domain-based-crawler\src
```

**macOS / Linux:**
```bash
cd ../ssl-certificates-crawler/domain-based-crawler/src
```

**Step 2: Run the crawler**

Simplest way — crawl our dataset into the default database:

**Windows:**
```powershell
python crawler-args.py
```

**macOS / Linux:**
```bash
python3 crawler-args.py
```

**Optional flags:**

| Flag | Purpose | Example |
|---|---|---|
| `--db-name` | Use your own database name instead of the default | `--db-name your_db_name` |
| `--csv-file` | Crawl your own list of domains instead of ours | `--csv-file path/to/your.csv` |
| *(others)* | Thread count, connection timeout, retry attempts, retry toggle | See `crawler-config-guide.md` |

Example — using both a custom database and your own CSV:

**Windows:**
```powershell
python crawler-args.py --db-name your_db_name --csv-file path\to\your.csv
```

**macOS / Linux:**
```bash
python3 crawler-args.py --db-name your_db_name --csv-file path/to/your.csv
```

> ⚠️ **Important:** the crawler needs a MongoDB instance running locally before you start it.

---

#### ⚠️ If you use `--db-name`, read this

Changing the database name means every other script that expects the default name also needs to be updated, or things will break. How much you need to update depends on what you plan to use:

**Minimum required — just to run the dashboard:**

| # | File | What to change |
|---|---|---|
| 1 | `dashboard/backend/pre-compute-scripts/databases.json` | `"main"` and `"results"` — all pre-compute scripts read this |
| 2 | `dashboard/backend/certificates/db.py` (lines 24–25) | `_BASE_MAIN_DB` and `_BASE_RESULTS_DB` — the Django backend's primary definition |

**If you also want to keep your data fresh using the [CT-logs renewal pipeline](../ct-logs-renewal-pipeline/README.md):**

| # | File | What to change |
|---|---|---|
| 3 | `ct-logs-renewal-pipeline/data-renew-merge.py` (line 43) | `MAIN_DB_NAME` |
| 4 | `ct-logs-renewal-pipeline/new-data.py` (line 38) | `TARGET_DB` |
| 5 | `ct-logs-renewal-pipeline/fetch-domains-names.py` (line 46) | `DATABASE_NAME` |

**Optional — only if you want every helper script to also work correctly:**

| # | File | What to change |
|---|---|---|
| 6 | `ssl-certificates-crawler/domain-based-crawler/src/crawler.py` (line 29) | `DB_NAME` |
| 7 | `ssl-certificates-crawler/domain-based-crawler/src/crawler-args.py` (line 30) | `DB_NAME` |
| 8 | `useful-scripts/data-removal.py` (line 19) | `DATABASE_NAME` |

#### ⚠️ If you use `--csv-file`, read this

Similarly, if you crawl your own CSV instead of `global-dataset.csv`, some scripts still reference the default filename directly and need to be updated to point at yours:

| # | File | Line | Variable |
|---|---|---|---|
| 1 | `ct-logs-renewal-pipeline/fetch-domains-names.py` | 50 | `OUTPUT_CSV = "global-dataset.csv"` |
| 2 | `ct-logs-renewal-pipeline/data-renew.py` | 22 | `INPUT_CSV = "global-dataset.csv"` |
| 3 | `ct-logs-renewal-pipeline/new-data.py` | 36 | `GLOBAL_CSV = Path("global-dataset.csv")` |
| 4 | `ct-logs-renewal-pipeline/main.py` | 87 | `GLOBAL_DATASET_CSV = BASE_DIR / "global-dataset.csv"` |
| 5 | `ssl-certificates-crawler/domain-based-crawler/src/crawler.py` | 34 | `CSV_FILE` key |
| 6 | `ssl-certificates-crawler/domain-based-crawler/src/crawler-args.py` | 35 | `CSV_FILE` key |
| 7 | `useful-scripts/csv-domain-cleaner.py` | 12 | `open(...)` path |

**Optional settings:** if you want to change thread count, connection timeout, maximum retry attempts, or retry toggles, either pass them as command-line arguments or edit the configuration in the crawler file directly. See `crawler-config-guide.md` for details.

---

### After crawling: build the pre-computed results

Once the crawler has finished, run the pre-compute script so the analytics database (`-results`) is built from your freshly-crawled data:

**Windows:**
```powershell
cd dashboard\backend\pre-compute-scripts\generic
python run-generic.py
```

**macOS / Linux:**
```bash
cd dashboard/backend/pre-compute-scripts/generic
python3 run-generic.py
```








## ✅ Prerequisites (install these once)

You need three things installed, plus one optional tool. Open a terminal (PowerShell on Windows) and check each one.

### 1. Python 3.11+ (for the backend)
Check if it's already installed:

**Windows:**
```powershell
python --version
```

**macOS / Linux:**
```bash
python3 --version
```

Missing? Install from <https://www.python.org/> and **tick "Add Python to PATH"** during setup (Windows).

We'll use Python's built-in `venv` + `pip` to manage dependencies — no extra tools needed.

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

> Already using `pyenv`, `pyenv-virtualenv`, or Conda? That's fine too — use whichever environment manager you're comfortable with, the steps in this README will work the same way once your environment is activated.

### 2. Node.js + npm (for the frontend)
Check if it's already installed:
```bash
npm --version
```
Missing? Install Node.js (npm comes bundled with it) from <https://nodejs.org/>.

> This project should also work with `bun` since it's mostly compatible with `npm`, but only the `npm` workflow has been tested with this project.

### 3. MongoDB (the database — **required**)

You need three separate pieces: the **MongoDB Server** itself, **MongoDB Shell (`mongosh`)**, and **MongoDB Database Tools** (`mongorestore` / `mongodump`) — these are used throughout this README to restore the dataset.

**Check if already installed:**
```bash
mongod --version
mongosh --version
mongorestore --version
```

**Missing? Install:**
- **MongoDB Community Server** (the database itself) — <https://www.mongodb.com/try/download/community>
- **MongoDB Shell (`mongosh`)** — <https://www.mongodb.com/try/download/shell>
- **MongoDB Database Tools** (`mongorestore`, `mongodump`) — <https://www.mongodb.com/try/download/database-tools>
- *(Optional)* **MongoDB Compass**, a GUI for browsing your data — <https://www.mongodb.com/try/download/compass>

Make sure the **MongoDB service is running** in the background (on Windows it usually installs as an auto-start service listening on `localhost:27017`; on macOS/Linux you may need to start it manually — see the install page for your OS).

### 4. Redis (optional — improves speed via caching)
Check if it's already installed:
```bash
redis-cli ping
```
This should print `PONG` if Redis is running. Missing is OK — the backend automatically runs without caching if Redis is not present.

**To install:**

**Windows:**
See <https://github.com/tporadowski/redis/releases>

**macOS:**
```bash
brew install redis
brew services start redis
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

---






## 🚀 How to run — step by step (beginner friendly)

> Throughout, `FYP` is the project root and the dashboard lives in `FYP/dashboard`.
> You will use **two terminals**: one for the backend, one for the frontend. Keep both open.

### Part 0 — Get the code and open the dashboard folder
```powershell
# If you haven't cloned yet:
git clone https://github.com/EbadJunaid/FYP
cd FYP/dashboard
```
If you already have the repo, just `cd` into `FYP/dashboard`.

### Part 1 — Start MongoDB
Make sure MongoDB is running and reachable on `localhost:27017`. On Windows it typically runs as a
service automatically. To check quickly:
```powershell
mongosh --eval "db.runCommand({ ping: 1 })"
```
You should see `{ ok: 1 }`. (If `mongosh` isn't installed, opening MongoDB Compass and connecting to
`mongodb://localhost:27017` works too.)

### Part 2 — Load the certificate data
Follow [⚠️ The data requirement](#️-the-data-requirement-read-this-first). At minimum, the
`hugging-face-700k` database with a `certificates` collection must exist before the dashboard is useful.

### Part 3 — Set up and start the **backend** (Terminal 1)

1. Go into the backend folder:
   ```powershell
   cd backend
   ```

2. Create an isolated Python environment with **uv**:
   ```powershell
   uv venv
   ```

3. Activate it:
   ```powershell
   # Windows (PowerShell)
   .venv\Scripts\activate

   # macOS / Linux
   source .venv/bin/activate
   ```

4. Install the Python dependencies (from `requirements.txt`) with **uv**:
   ```powershell
   uv pip install -r requirements.txt
   ```

   <details>
   <summary>Alternatives (Conda or plain venv + pip)</summary>

   ```powershell
   # Conda
   conda create -n ssl-dashboard python=3.11 -y
   conda activate ssl-dashboard
   pip install -r requirements.txt

   # Plain venv + pip
   python -m venv venv
   venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
   pip install -r requirements.txt
   ```
   </details>

5. **Point the backend at your database** (only if your DB names differ from the defaults).
   Open `backend/certificates/db.py` and edit these two lines near the top:
   ```python
   _BASE_MAIN_DB    = 'hugging-face-700k'           # your raw certificates DB
   _BASE_RESULTS_DB = 'hugging-face-700k-results'    # your pre-computed results DB
   ```
   The MongoDB connection string (`mongodb://localhost:27017/`) is also set in this file — change it
   only if your MongoDB is not on localhost.

6. **Build indexes + pre‑computed analytics** (do this once after loading data; re‑run whenever the
   data changes). From the backend folder:
   ```powershell
   cd pre-compute-scripts/generic
   python run-generic.py
   cd ../..
   ```
   This reads `databases.json`, creates MongoDB indexes, and fills the `*-results` database that the
   analytics pages rely on. (Helpful flags: `--dry-run`, `--verify-collections`, `--only <script.py>`.)

7. Initialize Django's internal tables (creates the small local `internal_db` SQLite file for
   sessions/admin — this does **not** touch your certificate data):
   ```powershell
   python manage.py migrate
   ```

8. Start the API server:
   ```powershell
   python manage.py runserver
   ```
   ✅ The backend is now running at **http://localhost:8000**. Test it in a browser:
   `http://localhost:8000/api/databases/available/` should return JSON.

   **Leave this terminal running.**

### Part 4 — Set up and start the **frontend** (Terminal 2)

1. Open a **new** terminal and go to the frontend folder:
   ```powershell
   cd FYP/dashboard/frontend
   ```

2. Install the JavaScript packages with **Bun**:
   ```powershell
   bun install
   ```
   <details>
   <summary>Alternative (npm)</summary>

   ```powershell
   npm install          # if you hit peer-dependency errors: npm install --legacy-peer-deps
   ```
   </details>

3. *(Optional)* Tell the frontend where the backend is. It **defaults to**
   `http://localhost:8000/api`, so you only need this if your backend runs elsewhere. Create a file
   named `.env.local` in the `frontend` folder:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

4. Start the development server:
   ```powershell
   bun run dev
   ```
   <details>
   <summary>Alternative (npm)</summary>

   ```powershell
   npm run dev
   ```
   </details>

   ✅ The dashboard is now running at **http://localhost:3000**.

### Part 5 — Open it
Open **http://localhost:3000** in your browser. You should land on the dashboard. Use the sidebar to
move between pages and the header's **scope switcher** to filter by country.

> Quick mental model: **MongoDB (data) → Django :8000 (API) → Next.js :3000 (UI)**.
> All three must be up at the same time.

---

## ⚙️ Configuration reference

| What | Where | Default | Change when… |
|---|---|---|---|
| MongoDB connection URI | `backend/certificates/db.py` | `mongodb://localhost:27017/` | MongoDB is remote/non‑default. |
| Main DB name | `backend/certificates/db.py` → `_BASE_MAIN_DB` | `hugging-face-700k` | your certificates DB is named differently. |
| Results DB name | `backend/certificates/db.py` → `_BASE_RESULTS_DB` | `hugging-face-700k-results` | your results DB is named differently. |
| Databases to pre‑compute | `backend/pre-compute-scripts/databases.json` | `hugging-face-700k` | adding more datasets/countries. |
| Country scopes | `backend/certificates/Scopes.json` | many | adding/removing scope options in the switcher. |
| Allowed frontend origin (CORS) | `backend/ssl_dashboard/settings.py` → `CORS_ALLOWED_ORIGINS` | `http://localhost:3000` | the frontend runs on another host/port. |
| Backend port | `python manage.py runserver 0.0.0.0:8000` | `8000` | port 8000 is taken. |
| Frontend → backend URL | `frontend/.env.local` → `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api` | backend runs elsewhere. |
| Redis host/port | `backend/certificates/cache_service.py` | `localhost:6379` | Redis is remote (optional). |

> ⚠️ The `SECRET_KEY` and `DEBUG = True` in `settings.py` are development defaults. **Change them
> before any public deployment.**

---

## 🌐 API endpoints

All endpoints live under `http://localhost:8000/api/`. Every analytics request accepts a
`?scope=<id>` query parameter (e.g. `?scope=all`, `?scope=pk`). A selection:

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/databases/available/` | List available scopes/databases (used by the switcher). |
| GET | `/api/databases/current/` | Currently selected database/scope. |
| POST | `/api/databases/switch/` | Switch active database. |
| GET | `/api/overview/...` | Overview metrics, filters, encryption strength, future risk, vulnerabilities. |
| GET | `/api/ca/ca-stats/` | CA metric cards and stats. |
| GET | `/api/ca/issuer-validation-matrix/` | Issuer × validation‑level heatmap. |
| GET | `/api/validity/validity-stats/` (+ distribution, timeline) | Validity analytics. |
| GET | `/api/san/...` | SAN analytics. |
| GET | `/api/signature-hash/...` | Signature & hash analytics. |
| GET | `/api/shared-keys/...` | Shared public‑key groups. |
| GET | `/api/trends/...` | Time‑series trends. |
| GET | `/api/shared/...` | Shared endpoints (global health, geographic distribution, certificate list/detail). |
| GET | `/api/certificates/download/`, `/export/` | CSV export. |

Exact routes are defined in `backend/certificates/urls.py` and each sub‑module's `urls.py`.

---

## 📁 Project structure

```
dashboard/
├── README.md                  ← this file
├── vulnerablities.md          ← exact risk-scoring formula for the Vulnerabilities page
│
├── backend/                   ← Django 5 API
│   ├── manage.py              ← Django entry point (runserver, migrate, …)
│   ├── requirements.txt       ← Python dependencies
│   ├── ssl_dashboard/         ← Django project (settings.py, urls.py, wsgi/asgi)
│   ├── certificates/          ← the main app
│   │   ├── db.py              ← MongoDB connection + DB/scope config (EDIT HERE)
│   │   ├── Scopes.json        ← country/scope definitions
│   │   ├── scope_middleware.py← reads ?scope= / header and applies it
│   │   ├── cache_service.py   ← optional Redis cache
│   │   ├── urls.py / views.py / controllers.py
│   │   └── <module>/          ← ca_analytics, overview, san_analytics, shared_keys,
│   │                            signature_hash, trends, validity_analysis, shared_apis
│   │                            (each: urls.py → views.py → controllers.py → db_queries.py)
│   ├── pre-compute-scripts/
│   │   └──            ← run-generic.py + index/compute scripts (build the -results DB)
│   └── country-domain-extractors/   ← split certs into per-country databases
│
└── frontend/                  ← Next.js 16 app (App Router)
    ├── package.json           ← scripts: dev / build / start / lint
    └── src/
        ├── app/               ← routes; app/dashboard/<page>/page.tsx = each dashboard page
        ├── components/        ← Card, DataTable, charts/, dashboard/ cards, layout/ (Sidebar…)
        ├── context/           ← DashboardContext, SearchContext, ThemeContext (dark mode)
        ├── hooks/             ← useApi, useDatabaseKey (scope/db cache keys)
        ├── services/          ← apiClient.ts (all backend calls; injects ?scope=)
        └── providers/         ← SWRProvider (global SWR config)
```

---

## 🩺 Troubleshooting

| Symptom | Likely cause & fix |
|---|---|
| Pages load but are **empty / show zeros** | MongoDB has no data, or `db.py` points at the wrong DB name. Load data (Part 2) and verify `_BASE_MAIN_DB`. |
| Charts/analytics are empty but the certificate table works | You haven't run the pre‑compute scripts. Run `python run-generic.py` (Part 3, Step 6). |
| Backend error: **connection refused / ServerSelectionTimeout** | MongoDB isn't running, or the URI in `db.py` is wrong. Start MongoDB (Part 1). |
| Frontend loads but every request fails (CORS / network error) | Backend isn't running on `:8000`, or `NEXT_PUBLIC_API_URL` is wrong, or your frontend origin isn't in `CORS_ALLOWED_ORIGINS`. |
| `bun: command not found` / `uv: command not found` | Re‑open the terminal after installing, or use the npm/pip alternatives shown above. |
| Port already in use | Run the backend on another port (`python manage.py runserver 8001`) and update `NEXT_PUBLIC_API_URL`, or start the frontend on another port (`bun run dev -- -p 3001`) and add it to `CORS_ALLOWED_ORIGINS`. |
| "You have unapplied migrations" warning | Run `python manage.py migrate` once (Part 3, Step 7). Harmless — it only sets up Django's internal SQLite tables. |
| Slow first load | Expected on large datasets. Install Redis (Part 5 of prerequisites) and re‑run pre‑compute scripts for best performance. |
