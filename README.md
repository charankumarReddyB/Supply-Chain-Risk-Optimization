# Supply Chain Risk Analysis & Optimization — System Architecture & Deployment

A production-ready enterprise supply chain risk analysis platform. Features include machine learning-based risk prediction, Monte Carlo scenario simulation, robust ETL pipelines, OLAP data warehousing (Star Schema), PDF/Excel reporting, and a responsive frontend dashboard.

---

## Technical Stack & Modernizations

| Layer | Technology | Description |
|---|---|---|
| **Frontend** | React + Vite + TypeScript | High-performance interactive UI hosted on Netlify |
| **Backend** | Python Flask 3.0 + Gunicorn | Scalable WSGI backend hosted on Render |
| **Database** | PostgreSQL (Neon Serverless) | Star schema data warehouse and operational OLTP schema |
| **Authentication**| Flask-JWT-Extended | Role-Based Access Control (RBAC) with token trimming |
| **Machine Learning**| Scikit-Learn Decision Tree | Real-time shipment risk classifier (Low/Medium/High) |
| **Simulation** | NumPy Monte Carlo | 10,000 runs across 4 distinct delay scenarios |
| **Reports** | ReportLab + Pandas + OpenPyXL | Automatic multi-format reporting with PDF and Excel downloads |

---

## Project Features & Upgrades

1. **PostgreSQL Migration**: Fully migrated the database layer from MySQL to serverless PostgreSQL (Neon). Replaced MySQL-specific sorting functions (such as `FIELD()`) with standard SQL `CASE` ordering, and fixed PostgreSQL alias lowercase folding using double-quoted identifiers.
2. **Robust Type Handling**: Handled psycopg2 `decimal.Decimal` float mismatches inside the risk calculations and analytics aggregation controllers.
3. **Build & Runtime Isolation**: Isolated build-time tasks (generating data & training models) from run-time database operations using a `--build-only` CLI flag. This prevents db connection blocks during deployment builds.
4. **Resilient DB Connections**: Integrated a `connect_timeout=3` parameter inside both psycopg2 raw connections and SQLAlchemy engines to avoid long TCP hangs during cold starts or transient database restarts.
5. **CORS Auto-Configuration**: Defaulted allowed origins in production to include Netlify frontend URLs and development localhost targets (`http://localhost:5173`).
6. **Zero-Config Frontend Builds**: Embedded the backend endpoint `VITE_API_BASE_URL` directly within `netlify.toml` for hands-off deployment compilation.

---

## Project Structure

```
.
├── backend/                        # Flask Backend
│   ├── app.py                      # Flask app factory, CORS, and startup seeding
│   ├── config.py                   # Configuration parameters (DB, JWT, paths)
│   ├── requirements.txt            # Pinned dependencies (Flask, scikit-learn, psycopg2)
│   ├── database_setup.sql          # Complete DDL: OLTP + OLAP Star Schema
│   │
│   ├── routes/                     # Blueprint endpoints
│   │   ├── auth.py                 # /api/auth/* (User Registration, Login, Profiles)
│   │   ├── dashboard.py            # /api/dashboard/* (Admin & Public metrics)
│   │   ├── analytics.py            # /api/analytics/* (OLAP OLAP aggregates)
│   │   ├── risk.py                 # /api/risk/* (Risk scores & ML model predictions)
│   │   └── ...
│   │
│   ├── controllers/                # Business logic & Database interaction
│   │   ├── auth_controller.py
│   │   ├── dashboard_controller.py
│   │   ├── risk_controller.py
│   │   └── analytics_controller.py
│   │
│   ├── ml/                         # Machine learning & simulation models
│   │   ├── train.py                # Model training entry point
│   │   ├── predict.py              # Singleton predictor class
│   │   └── monte_carlo.py          # Monte Carlo simulator engine
│   │
│   └── utils/                      # Shell utilities
│       ├── init_system.py          # One-command full system initialization
│       ├── test_apis.py            # Public smoke tests
│       └── test_roles_and_localization.py # Security and RBAC validation suite
│
└── frontend/                       # React Frontend
    ├── src/
    │   ├── app/                    # UI Components and views
    │   │   └── App.tsx             # Main dashboard UI
    │   └── services/
    │       └── apiService.ts       # Backend integration layer
    └── netlify.toml                # Build settings & API redirect bindings
```

---

## Quick Start (Local Development)

### 1. Backend Setup

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv
.venv\Scripts\activate   # On Windows
source .venv/bin/activate # On Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Create .env config file
copy .env.example .env
```

Edit the `.env` file to match your PostgreSQL server details:
```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_NAME=supply_chain_db
JWT_SECRET_KEY=fallback-dev-key-change-in-production
```

### 2. Initialize System & Seed Data
Run the system initialization script to build schemas, generate a mock dataset (18,500 records), run the ETL pipeline, and train the ML model:
```bash
python -m utils.init_system
```

### 3. Run Backend
```bash
python -m app
# Runs at http://localhost:5000
```

### 4. Frontend Setup
```bash
cd ../frontend
npm install
npm run dev
# Runs at http://localhost:5173
```

---

## Testing & Verification

We have created two local verification scripts in `backend/utils` to validate the live backend's functionality.

### Run Smoke Tests
Tests user signup, login, dashboard stats endpoints, and ML predictions:
```bash
python backend/utils/test_apis.py https://supply-chain-risk-analysis-and-qk0t.onrender.com
```

### Run Security & RBAC Tests
Verifies standard user role limitations, field-level data trimming (restricted supplier rating details), and admin-only endpoint blocks:
```bash
python backend/utils/test_roles_and_localization.py https://supply-chain-risk-analysis-and-qk0t.onrender.com
```

---

## Production Deployments

- **Backend**: Hosted on Render and configured to run self-healing database auto-migrations on startup if tables are absent.
  - Active URL: `https://supply-chain-risk-analysis-and-qk0t.onrender.com/`
- **Frontend**: Deployed on Netlify, integrated with automatic builds on push.
  - Active URL: `https://supplychainrisk.netlify.app/`

---

## Security Roles & Credentials

- **Admin Account**:
  - Username: `admin`
  - Password: `admin123`
- **Standard User Account**:
  - Username: `user`
  - Password: `user123`

---

## Production Deployment & WSGI Serving

For production, serve the application using a WSGI server like **Gunicorn**:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 backend.app:app
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `FLASK_ENV` | `development` | Set to `production` to activate production settings and seed safety checks |
| `FLASK_DEBUG` | `false` | Enable/disable Flask debug mode |
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_USER` | `postgres` | PostgreSQL username |
| `DB_PASSWORD` | *(empty)* | PostgreSQL password |
| `DB_NAME` | `supply_chain_db` | Database name |
| `DATABASE_URL`| *(empty)* | Full PostgreSQL Connection URI (preferred for cloud platforms like Neon/Render) |
| `JWT_SECRET_KEY` | *(required)* | JWT signing key (Must be set in production; startup will fail if missing) |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:5000,https://supplychainrisk.netlify.app` | Comma-separated list of allowed CORS origins |

---

## License

B.Tech Capstone Project — Supply Chain Risk Optimization
