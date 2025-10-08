# Inbox Party - Waitlist Platform

Email prospecting tool with built-in lead enrichment and tracking. Join the waitlist to get early access.

## Project Structure

```
.
├── frontend/           # Static HTML/CSS/JS frontend
│   ├── index.html     # Landing page with waitlist signup
│   ├── admin.html     # Admin dashboard
│   ├── main.js        # Waitlist form logic
│   ├── admin.js       # Admin dashboard logic
│   ├── styles.css     # Styles for both pages
│   └── assets/        # Images and logos
├── backend/           # Python API server
│   ├── server.py      # Minimal HTTP server with SQLite
│   └── waitlist.db    # SQLite database (created on first run)
└── render.yaml        # Render deployment configuration
```

## Features

- **Waitlist Signup**: Clean landing page with email capture
- **Admin Dashboard**: View signups and export to CSV
- **Dual Database Support**: SQLite for local dev, PostgreSQL/Supabase for production
- **Data Persistence**: PostgreSQL ensures data survives service restarts
- **CORS Support**: Ready for local development and production deployment

## Local Development

### Backend (Python API)

Requirements: Python 3.8+

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API server (uses SQLite by default)
python backend/server.py

# Server runs on http://localhost:8000
# Health check: http://localhost:8000/health
```

### Frontend

```bash
# Serve frontend with any static server, e.g.:
cd frontend
python -m http.server 3000

# Or use: npx serve frontend -p 3000
```

Visit `http://localhost:3000` to see the landing page.

## API Endpoints

### `POST /api/waitlist`
Add user to waitlist
```json
{
  "name": "Taylor Sender",
  "email": "name@domain.com"
}
```

### `GET /api/waitlist`
Get total waitlist count
```json
{
  "count": 42
}
```

### `GET /api/waitlist/entries`
List all waitlist entries (JSON or CSV)
- Query param: `?format=csv` for CSV export
- Query param: `?limit=10` to limit results

### `GET /health`
Health check endpoint

## Deployment

### Render (Recommended)

The project includes `render.yaml` for one-click deployment:

1. Push to GitHub
2. Connect repository to Render
3. Render auto-detects `render.yaml` and deploys both frontend and backend

### Environment Variables

- `PORT` - Server port (default: 8000)
- `PYTHON_VERSION` - Python runtime version (default: 3.11.0)
- `DATABASE_URL` - PostgreSQL connection string (optional, uses SQLite if not set)

### Supabase Setup (Recommended for Production)

1. **Create a Supabase project** at https://supabase.com
2. **Get your connection string**:
   - Go to Project Settings → Database
   - Copy the "Connection string" (URI format)
   - Use the "Transaction" pooler mode for better performance
3. **Add to Render**:
   - In your Render service, go to Environment
   - Add `DATABASE_URL` with your Supabase connection string
   - Format: `postgresql://user:password@host:port/database`
4. **Deploy**: The backend will automatically detect and use PostgreSQL

The table schema will be created automatically on first run.

## Admin Access

Access the admin dashboard at `/admin.html` to:
- View all waitlist signups
- Monitor total count
- Export data as CSV

## Database

The backend supports both SQLite and PostgreSQL:

**Local Development (SQLite)**:
- Automatically created at `backend/waitlist.db`
- No configuration needed
- Data resets when deploying to Render free tier

**Production (PostgreSQL/Supabase)**:
- Persistent data storage
- Set `DATABASE_URL` environment variable
- Recommended for deployed applications

**Schema** (auto-created on first run):
```sql
-- PostgreSQL
CREATE TABLE waitlist (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- SQLite (fallback)
CREATE TABLE waitlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

## License

© 2025 Inbox Party. Early access opens soon.
