# Weather API (FastAPI)

Simple weather API backed by the OpenWeather API.

## Setup

1. Create a virtual environment and install dependencies:
   - `python -m venv .venv`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
   - `pip install -r requirements.txt`
2. Create a `.env` file (see `.env.example`).

## Run

- `uvicorn main:app --reload`
- `uvicorn app.main:app --reload` (if your platform is configured this way)

Open Swagger UI at `http://127.0.0.1:8000/docs`.
