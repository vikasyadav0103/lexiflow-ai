# LexiFlow AI — Python API

This directory contains the Python/FastAPI dictionary backend. For the full project architecture, Spring Boot gateway, React frontend, and contribution workflow, see the [root README](../README.md).

## Responsibilities

- Dictionary lookups via the Free Dictionary API.
- MySQL persistence and lookup history.
- WordNet fallback where the corpus is installed.
- Optional NLP features using NLTK and spaCy.
- Optional Transformer embeddings through a separately installed ML dependency set.

## Install

From this directory:

```bash
python -m venv .venv
```

Activate the environment, then install the core API:

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

Configure MySQL and copy `.env.example` to `.env`. Then install the language assets used by NLP routes:

```bash
python -m spacy download en_core_web_sm
python -c "import nltk; [nltk.download(p) for p in ('punkt', 'punkt_tab', 'wordnet', 'averaged_perceptron_tagger_eng')]"
```

Transformer-based embeddings are optional. To enable them, install:

```bash
pip install -r requirements-ml.txt
```

This installs PyTorch and Transformers; the configured embedding model is downloaded on first use. Dictionary-only lookup does not require that model stack.

## Run

With the working directory set to `backend/`:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- Liveness: [http://localhost:8000/health/live](http://localhost:8000/health/live)
- Readiness: [http://localhost:8000/health/ready](http://localhost:8000/health/ready)

## Notes

- Database initialization creates missing tables and does not drop existing data.
- Use a migration tool for future schema changes.
- Sentiment is reported as unavailable until a real fine-tuned classifier is configured. The previously used classification head was not trained for sentiment and should not be treated as a valid prediction.
- Do not commit local virtual environments, downloaded corpora, model caches, or secrets.
