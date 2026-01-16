# SSL Certificate Dashboard

A comprehensive, full-stack SSL certificate monitoring system. This application provides real-time analytics, vulnerability scanning, and lifecycle management for SSL certificates, powered by **Django** (Backend) and **Next.js** (Frontend).

## 🏗️ Tech Stack

- **Frontend:** Next.js 16, TypeScript, Tailwind CSS
- **Backend:** Django 5, Django REST Framework
- **Database:** MongoDB (via Djongo)
- **Caching:** Redis
- **Language:** Python 3.11+, Node.js v18+

---

## 📋 Prerequisites & Verification

Before installing, open your terminal (Command Prompt or PowerShell on Windows) and verify you have the necessary tools.

### 1. Check Node.js & npm
Required for the frontend.
```powershell
node -v
npm -v
```
Missing? Download "LTS" from [Nodejs](https://nodejs.org/)

### 2. Check Python 
Required for the backend.
```powershell
python --version
```

Missing? Download Python 3.11+ from [python](https://www.python.org)
.
Note: Ensure you check "Add Python to PATH" during installation.


### 3. Check MongoDB (Required)
We have used the MongoDB as the primary database.

```powershell
mongod --version
```

Missing? Install MongoDB Community Server and MongoDB Compass from [mongodb](https://www.mongodb.com)
Ensure the MongoDB Service is running in the background.

### 4. Check Redis (optional)
it's better to install it for caching and performance optimization.

```powershell
redis-cli ping
```

Output should be: PONG

if it's missing install it from [Redis](https://github.com/tporadowski/redis/releases)

## 🚀 Installation Guide
#### Phase 1: Clone the Repository
The dashboard code resides in the arslan branch. You can download it using one of the methods below:

#### Option A: Clone ONLY the dashboard branch (Recommended)

```powershel
git clone --branch arslan --single-branch https://github.com/EbadJunaid/FYP/
cd arslan-dashboard
```

#### Option B: Clone entire repo and switch

```powershel
git clone https://github.com/EbadJunaid/FYP/
cd arslan-dashboard
git checkout arslan
```

#### Phase 2: Backend Setup (Django)
-  Navigate to the backend directory
```powershel
cd backend
```

- It's highly recommended to use the python virtual environment 

```powershel
# Windows
python -m venv venv

# Windows
venv\Scripts\activate


# Mac/Linux
python3 -m venv venv

# Mac/Linux
source venv/bin/activate
```

- you use also use conda environments and pyenv for this purpose 

- Install Dependencies

```powershel
pip install django djangorestframework django-cors-headers djongo redis
```


Configure MongoDB database name 

Open `arslan-dashboard/backend/certificates/db.py` and then change the name of database in ` return cls._client['your-db-name']`




-  Start the Backend Server
```powershel
python manage.py runserver
```

The API is now running at: http://localhost:8000/api


#### Phase 3: Frontend Setup (Next.js)
- Navigate to the frontend directory
 
```powershel
 cd frontend
```

-  Install Node Packages
```powershel
 npm install
```

(If you encounter dependency errors,  try: `npm install --legacy-peer-deps`)


-  Start the Development Server

```powershel
npm run dev
```

The Dashboard is now running at: http://localhost:3000