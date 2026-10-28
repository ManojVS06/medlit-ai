# MedLit AI

**AI-Powered Medical Literature Summarization and Research Assistant**

MedLit AI helps medical researchers efficiently review scientific literature by searching PubMed, generating structured summaries of research abstracts using AI, and comparing evidence across multiple studies.

> ⚠️ **Disclaimer**: This tool assists research — it does not provide clinical recommendations. AI-generated summaries require expert verification.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Backend

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# Copy environment config
copy .env.example .env  # Windows
# cp .env.example .env  # macOS/Linux

# Start the backend
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open http://localhost:5173 in your browser.

### Verify

- Backend health: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

## Project Structure

```
medlit-ai/
├── backend/              # Python FastAPI backend
│   ├── app/
│   │   ├── api/          # Route handlers
│   │   ├── core/         # Configuration
│   │   ├── schemas/      # Pydantic models (request/response validation)
│   │   ├── models/       # Database models
│   │   ├── services/     # Business logic
│   │   └── main.py       # Application entry point
│   └── tests/            # Backend tests
├── frontend/             # React + TypeScript frontend
│   └── src/
│       ├── components/   # Reusable UI components
│       ├── pages/        # Page-level components
│       ├── services/     # API client functions
│       └── types/        # TypeScript type definitions
├── data/                 # Sample data and evaluation datasets
├── docs/                 # Project documentation
├── .env.example          # Environment variable template
└── .gitignore
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React, TypeScript, Vite, Tailwind CSS v4 |
| Backend | Python, FastAPI, Pydantic |
| Database | SQLite (development) → PostgreSQL (production) |
| AI | Mock provider (default), Google Gemini, Ollama |
| Literature | PubMed / NCBI E-utilities API |
| Testing | Pytest, Vitest |

## Current Status

- [x] Milestone 0: Requirements & Technical Plan
- [x] Milestone 1: Development Environment
- [x] Milestone 2: First Vertical Slice
- [ ] Milestone 3: PubMed Integration
- [ ] Milestone 4: LLM Integration
- [ ] Milestone 5: Screening & Batch Processing
- [ ] Milestone 6: Database Persistence
- [ ] Milestone 7: Cross-Study Comparison
- [ ] Milestone 8: Quality Evaluation
- [ ] Milestone 9: Frontend Polish
- [ ] Milestone 10: Testing & Security
- [ ] Milestone 11: Docker & Deployment
- [ ] Milestone 12: Final Documentation

## License

This project is for educational purposes.
