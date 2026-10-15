# LexiFlow AI

**An AI-powered dictionary and language-analysis platform** built around a Python API, NLP/ML capabilities, and a React web application. The project is being evolved toward a modular platform with a separate Java Spring Boot inference gateway.

> **Project status:** Existing dictionary backend and frontend; inference gateway is planned and not yet part of the repository.

## Current capabilities

- Word definitions and lookup using the Free Dictionary API, with database-backed caching.
- Related words, example sentences, phonetics, and WordNet fallback.
- NLP utilities for tokenization, part-of-speech tagging, and lemmatization.
- Sentiment and embedding experiments using Transformer/PyTorch models.
- Search-history and frequency endpoints.
- React + Vite interface for dictionary search, analysis, and history.

Some ML features load pretrained models and may require a first-run download, network access, and additional RAM/CPU. Model outputs depend on the model and its training; validate them before using them for decisions.

## Architecture today

```text
React + Vite frontend
        |
        | HTTP / JSON
        v
FastAPI backend  -----> Free Dictionary API
        |         ----> NLTK / WordNet / Transformers
        v
      MySQL
```

## Planned evolution

```text
React frontend
     |
     v
Spring Boot inference gateway  (planned)
  - routing and request validation
  - timeout / concurrency limits
  - metrics and health checks
     |
     v
Python FastAPI NLP service
     |
     +---- MySQL
     +---- Dictionary API / NLP models
```

The gateway is a roadmap item; the current frontend talks directly to the FastAPI API.

## Repository layout

```text
.
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models/
│   │   ├── routes/
│   │   ├── services/
│   │   └── utils/
│   ├── requirements.txt
│   ├── .env.example
│   └── run.py
└── frontend/
    ├── src/
    │   ├── api/
    │   ├── components/
    │   └── context/
    └── package.json
```

Generated virtual environments and downloaded NLP corpora should be installed locally rather than maintained as source files.

## Quick start

### Requirements

- Python 3.11 or 3.12
- Node.js 20+
- MySQL 8+
- Git

### 1. Configure the backend

```bash
cd backend
python -m venv .venv
```

Activate it, then install dependencies:

**Linux/macOS**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a MySQL database (default name: `word_dictionary`) and copy `.env.example` to `.env`. Update the credentials before starting the application.

Start the API from the `backend` directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Start the frontend

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

The Vite development server typically runs at [http://localhost:5173](http://localhost:5173). Configure `VITE_API_URL` if the backend is hosted elsewhere; it should point to the API base, e.g. `http://localhost:8000/api`.

## Configuration and safety

- Never commit real credentials, tokens, or private environment files.
- Use `.env.example` as a template and provide your own local `.env`.
- Database startup must never drop existing tables. For schema changes, use explicit migrations or a deliberate maintenance procedure.
- The service currently loads large NLP/ML dependencies and may download pretrained models at startup. Expect a slow first start and plan sufficient disk and memory.
- CORS, API authentication, request limits, and production deployment settings should be reviewed before exposing the service publicly.

## Development roadmap

- [ ] Establish reliable tests for the existing API contracts.
- [ ] Separate configuration, database lifecycle, and ML model initialization.
- [ ] Add a Spring Boot inference gateway as an independent service.
- [ ] Add request timeouts, bounded concurrency, health checks, and metrics.
- [ ] Add Docker Compose for local development.
- [ ] Add CI for Python tests, frontend lint, and production build.
- [ ] Remove previously committed generated environments and corpora from Git tracking.

## Contributing

Issues and pull requests are welcome. Please open an issue before large architectural changes, include reproducible steps for bugs, and avoid committing generated artifacts or secrets.

## License

See [LICENSE](LICENSE).
