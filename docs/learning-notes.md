# MedLit AI — Learning Notes & Progress

## Completed Milestones

### Milestone 0: Requirements & Feasibility ✅
- Defined the problem: help researchers search, summarize, and compare medical literature
- Created 16 user stories (8 MVP, 6 post-MVP, 2 stretch)
- Identified API dependencies: PubMed (free), Gemini Flash (free tier), Ollama (local)
- Designed modular monolithic architecture
- Drew architecture diagram and request-flow sequence diagram
- Estimated ~7 weeks for full project, ~3 weeks for MVP

### Milestone 1: Development Environment ✅
- Initialized Git repository
- Created Python virtual environment (`.venv/`)
- Installed FastAPI + Pydantic + HTTPX + Pytest
- Created React + TypeScript frontend with Vite
- Installed Tailwind CSS v4 with Vite plugin
- Set up `.env.example` (committed) and `.env` (gitignored)
- Built `/health` endpoint — verified with 3 passing tests
- Created landing page that fetches backend status

## Key Concepts Learned

### Virtual Environments
- Isolate Python dependencies per project
- Created with `python -m venv .venv`
- Activated with `.venv\Scripts\activate` (Windows)
- `pip install -r requirements.txt` recreates the exact environment

### Git & .gitignore
- `.gitignore` prevents secrets (`.env`) and large directories (`node_modules/`, `.venv/`) from being tracked
- `.env.example` with placeholders IS committed — so anyone cloning knows what variables to set

### FastAPI Basics
- `app = FastAPI()` creates the web server
- `@app.get("/health")` registers a route handler
- CORS middleware allows cross-origin requests (React on :5173 → API on :8000)
- `lifespan` context manager handles startup/shutdown logic

### Pydantic Settings
- `pydantic-settings` reads configuration from `.env` files automatically
- Type validation at startup — misconfigured values caught early
- Single `settings` instance imported wherever config is needed

### Testing
- `TestClient` sends requests to FastAPI in-memory (no server needed)
- `pytest` auto-discovers functions starting with `test_`
- Always assert both status code AND response body

## Commands Reference

```bash
# Backend
cd backend
.venv\Scripts\python.exe -m pytest tests/ -v     # Run tests
.venv\Scripts\uvicorn app.main:app --reload       # Start dev server

# Frontend
cd frontend
npm run dev                                        # Start dev server
```

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| Modular monolith | Simpler than microservices; all code in one repo, one deployment |
| Mock LLM provider as default | Tests run without API keys; development works offline |
| SQLite first, PostgreSQL later | Reduces setup complexity for early milestones |
| Pydantic for all I/O | Catches bad data at system boundaries, not deep inside business logic |
| Tailwind CSS v4 | CSS-first config, native Vite plugin, no extra PostCSS setup |

## Known Issues

- None yet

## Next Steps

- **Milestone 2**: Build first vertical slice — paste an abstract, get a mock structured summary, display it
