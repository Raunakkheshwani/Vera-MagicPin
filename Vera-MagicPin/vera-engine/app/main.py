from pathlib import Path

from fastapi import FastAPI

from app.api.routes import context_store, router
from app.state.dataset_loader import ensure_expanded_dataset, load_official_dataset


def create_app() -> FastAPI:
    app = FastAPI(title="Vera Engine — magicpin AI Challenge")
    app.include_router(router)

    @app.on_event("startup")
    async def _load_dataset_on_startup() -> None:
        repo_root = Path(__file__).resolve().parents[2]  # .../Vera-MagicPin
        expanded_dir = ensure_expanded_dataset(repo_root)
        counts = load_official_dataset(context_store, expanded_dir)
        print(f"[startup] Loaded official dataset: {counts}")

    return app


app = create_app()