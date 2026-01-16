# SSL Certificate Dashboard

A comprehensive SSL certificate monitoring and management dashboard built with Django (backend) and Next.js (frontend). This application provides real-time SSL certificate analytics, vulnerability monitoring, and certificate lifecycle management.

## 🏗️ Architecture

- **Frontend**: Next.js 16.1.1 with TypeScript, Tailwind CSS, and Recharts
- **Backend**: Django 5.2.9 with REST API
- **Database**: MongoDB available
- **Caching**: Redis support for performance optimization

## 📋 Prerequisites

Before running this application, make sure you have the following installed:

- **Python 3.8+** (for Django backend)
- **Node.js 18+** (for Next.js frontend)
- **npm or yarn** (package manager)
- **Redis** (optional, for caching)
- **Git** (for cloning the repository)

### Installing Prerequisites

#### Windows
```bash
# Install Python (if not already installed)
# Download from: https://www.python.org/downloads/

# Install Node.js (if not already installed)
# Download from: https://nodejs.org/

# Install Redis (optional)
# Download from: https://redis.io/download
```

#### Linux/Ubuntu
```bash
# Update package list
sudo apt update

# Install Python 3 and pip
sudo apt install python3 python3-pip python3-venv

# Install Node.js and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Redis (optional)
sudo apt install redis-server
```

#### macOS
```bash
# Install Python 3 (using Homebrew)
brew install python3

# Install Node.js (using Homebrew)
brew install node

# Install Redis (optional)
brew install redis
```

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd arslan-dashboard
```

### 2. Backend Setup (Django)

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install django djangorestframework django-cors-headers

# Install Redis (if using Redis for caching)
pip install redis>=5.0.0

# Run database migrations
python manage.py migrate

# (Optional) Create superuser for Django admin
python manage.py createsuperuser

# Start Django development server
python manage.py runserver
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup (Next.js)

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start Next.js development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

## 🗄️ Database Configuration

### SQLite (Default)
The application uses SQLite by default. No additional configuration required.

### MongoDB (Alternative)
To use MongoDB instead of SQLite:

1. Install MongoDB on your system
2. Uncomment the MongoDB configuration in `backend/ssl_dashboard/settings.py`
3. Comment out the SQLite configuration
4. Install djongo: `pip install djongo`

```python
# In backend/ssl_dashboard/settings.py, replace DATABASES section:

DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': 'ssl_database',
        'CLIENT': {
            'host': 'localhost',
            'port': 27017,
        }
    }
}
```

## 🔧 Environment Variables

### Frontend Environment Variables

Create a `.env.local` file in the `frontend` directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

### Backend Environment Variables (Optional)

Create a `.env` file in the `backend` directory:

```env
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
```

## 🏃‍♂️ Running the Application

### Development Mode

1. **Start Backend** (Terminal 1):
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   python manage.py runserver
   ```

2. **Start Frontend** (Terminal 2):
   ```bash
   cd frontend
   npm run dev
   ```

3. **Open Browser**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/api
   - Django Admin: http://localhost:8000/admin

### Production Build

#### Frontend Production Build
```bash
cd frontend
npm run build
npm start
```

#### Backend Production Setup
```bash
cd backend
# Set DEBUG=False in settings.py
# Configure ALLOWED_HOSTS for your domain
# Use a production WSGI server like Gunicorn
pip install gunicorn
gunicorn ssl_dashboard.wsgi:application --bind 0.0.0.0:8000
```

## 📚 API Documentation

The backend provides RESTful APIs for SSL certificate management:

### Core Endpoints

- `GET /api/dashboard/global-health/` - Global SSL health metrics
- `GET /api/certificates/` - List certificates with filtering and pagination
- `GET /api/certificates/{id}/` - Get certificate details
- `GET /api/certificates/download/` - Download certificate data
- `GET /api/unique-filters/` - Get available filter options

### Analytics Endpoints

- `GET /api/encryption-strength/` - Encryption strength distribution
- `GET /api/validity-trends/` - Certificate validity trends
- `GET /api/ca-analytics/` - Certificate Authority analytics
- `GET /api/geographic-distribution/` - Geographic certificate distribution
- `GET /api/future-risk/` - Future risk projections

### Additional Endpoints

- `GET /api/vulnerabilities/` - Certificate vulnerabilities
- `GET /api/notifications/` - System notifications
- `GET /api/validity-stats/` - Certificate validity statistics
- `GET /api/validity-distribution/` - Validity period distribution
- `GET /api/issuance-timeline/` - Certificate issuance timeline

## 🔍 Features

- **Real-time SSL Monitoring**: Continuous certificate health tracking
- **Interactive Dashboard**: Modern UI with charts and analytics
- **Certificate Management**: CRUD operations for SSL certificates
- **Vulnerability Detection**: Automated security vulnerability scanning
- **Geographic Analytics**: Certificate distribution by country
- **Expiration Alerts**: Proactive notification system
- **Advanced Filtering**: Multi-criteria certificate filtering
- **Data Export**: Certificate data download functionality

## 🛠️ Development

### Frontend Development
```bash
cd frontend
npm run lint  # Run ESLint
npm run build  # Build for production
```

### Backend Development
```bash
cd backend
python manage.py test  # Run Django tests
python manage.py makemigrations  # Create database migrations
python manage.py migrate  # Apply migrations
```

## 🔧 Troubleshooting

### Common Issues

1. **Port Conflicts**
   - Backend uses port 8000, frontend uses port 3000
   - Change ports in settings if needed

2. **CORS Issues**
   - Ensure CORS_ALLOWED_ORIGINS includes your frontend URL in Django settings
   - Default: `http://localhost:3000`

3. **Database Connection**
   - For MongoDB: Ensure MongoDB is running on port 27017
   - For SQLite: File is created automatically in backend directory

4. **Redis Connection**
   - Ensure Redis server is running if using Redis caching
   - Default Redis URL: `redis://localhost:6379`

5. **Node Modules Issues**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

6. **Python Virtual Environment Issues**
   ```bash
   cd backend
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

### Getting Help

If you encounter issues:
1. Check the console/logs for error messages
2. Verify all prerequisites are installed
3. Ensure ports 3000 and 8000 are available
4. Check database connectivity
5. Review environment variables

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

**Happy Coding! 🚀**