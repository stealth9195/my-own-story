"""실행: uv run --env-file .env uvicorn app.lab.server:app --port 8000"""

from app.lab.api import create_app

app = create_app()
