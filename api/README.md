# Feature Flag Promotion Dashboard - Backend API

Phase 1 implementation of the Feature Flag Promotion Dashboard POC (Backend + Basic Frontend).

## Setup Instructions

### Prerequisites
- Python 3.9+
- PostgreSQL 15+
- Node.js 18+ and npm
- pip

## Backend Setup

### Installation

1. **Navigate to the api directory**
```bash
cd api
```

2. **Create virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```bash
DATABASE_URL=postgresql+asyncpg://postgres:admin@localhost:5432/flag_dashboard
GROWTHBOOK_API_KEY=your_growthbook_api_key_here
GROWTHBOOK_BASE_URL=https://api.growthbook.io
CORS_ORIGINS=http://localhost:5173
```

### Running the Backend

1. **Start the server**
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Access the API**
- API Root: http://localhost:8000
- Health Check: http://localhost:8000/health
- Interactive Docs: http://localhost:8000/docs

The application will automatically:
- Create the PostgreSQL database if it doesn't exist
- Create the required tables (markets, flags)
- Seed the India market on first startup

## Frontend Setup

### Installation

1. **Navigate to the web directory**
```bash
cd web
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment variables**
```bash
cp .env.example .env.local
```

Edit `.env.local` with your configuration:
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### Running the Frontend

1. **Start the dev server**
```bash
npm run dev
```

2. **Access the application**
- Frontend: http://localhost:5173

## Running Both Services

Open two terminals:

**Terminal 1 (Backend):**
```bash
cd api
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd web
npm run dev
```

## API Endpoints

### Markets

#### Get all markets
```bash
GET /api/v1/markets
```

#### Get market by ID
```bash
GET /api/v1/markets/{market_id}
```

#### Create market
```bash
POST /api/v1/markets
Content-Type: application/json

{
  "name": "india",
  "env_flow": "dev->qa->uat->prod"
}
```

### Flags

#### Get all flags (optionally filter by market)
```bash
GET /api/v1/flags?market_id=1
```

#### Create flag
```bash
POST /api/v1/flags
Content-Type: application/json

{
  "key": "enable_checkout",
  "market_id": 1,
  "growthbook_feature_id": "feat_checkout_01"
}
```

#### Update flag
```bash
PUT /api/v1/flags/{flag_id}
Content-Type: application/json

{
  "key": "enable_checkout_v2",
  "growthbook_feature_id": "feat_checkout_02"
}
```

## Database Schema

### markets
- `id` (INTEGER, PRIMARY KEY)
- `name` (VARCHAR(100), UNIQUE, NOT NULL)
- `env_flow` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMP, DEFAULT NOW())

### flags
- `id` (INTEGER, PRIMARY KEY)
- `key` (VARCHAR(255), NOT NULL)
- `market_id` (INTEGER, FOREIGN KEY -> markets.id)
- `growthbook_feature_id` (VARCHAR(255), NOT NULL)
- `created_at` (TIMESTAMP, DEFAULT NOW())
- `updated_at` (TIMESTAMP, DEFAULT NOW(), ON UPDATE)

## Project Structure

```
api/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── db.py                # Database configuration and connection
│   ├── seed.py              # Database seeding logic
│   ├── models/              # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── market.py
│   │   └── flag.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── market.py
│   │   └── flag.py
│   ├── routers/             # API route handlers
│   │   ├── __init__.py
│   │   ├── markets.py
│   │   └── flags.py
│   └── services/            # Business logic (for future phases)
│       └── __init__.py
├── requirements.txt
├── .env.example
└── README.md

web/
├── src/
│   ├── components/          # React components
│   │   ├── MarketSelector.jsx
│   │   ├── FlagInventory.jsx
│   │   └── FlagRegistration.jsx
│   ├── services/            # API client
│   │   └── api.js
│   ├── App.jsx              # Main application
│   ├── App.css              # Styles
│   └── main.jsx             # Entry point
├── package.json
├── vite.config.js
└── README.md
```

## Phase 1 Features

### Backend
- ✅ Backend structure setup
- ✅ PostgreSQL database with async SQLAlchemy
- ✅ Market and Flag models
- ✅ Pydantic schemas for validation
- ✅ Market CRUD endpoints
- ✅ Flag CRUD endpoints
- ✅ CORS configuration
- ✅ Basic logging
- ✅ Error handling
- ✅ Auto database creation on startup
- ✅ India market seeding

### Frontend
- ✅ Vite + React setup
- ✅ Market Selector dropdown
- ✅ Flag Inventory table
- ✅ Flag Registration form
- ✅ Basic layout and styling
- ✅ API integration with backend

## Testing

### Manual Testing

1. **Start both services**
```bash
# Terminal 1 - Backend
cd api
source .venv/bin/activate
python -m uvicorn app.main:app --reload

# Terminal 2 - Frontend
cd web
npm run dev
```

2. **Test health endpoint**
```bash
curl http://localhost:8000/health
```

3. **Test frontend**
- Open http://localhost:5173 in browser
- Select "india" market
- View flags for the market
- Register a new flag
- Verify flag appears in the table

## Next Steps

Phase 1 is complete. The following phases will be implemented:

- **Phase 2**: GrowthBook Integration
- **Phase 3**: Comparison Engine
- **Phase 4**: Promotion Engine
- **Phase 5**: Testing & Polish

## Troubleshooting

### Database connection error
Ensure PostgreSQL is running and the credentials in `.env` are correct.

### Port already in use
Kill the process using port 8000:
```bash
lsof -ti:8000 | xargs kill -9
```

### Module not found
Ensure the virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend not connecting to backend
- Ensure backend is running on port 8000
- Check CORS configuration in backend
- Verify VITE_API_BASE_URL in `.env.local`

