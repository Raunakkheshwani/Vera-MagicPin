from pathlib import Path

from app.state.context_store import ContextStore
from app.state.dataset_loader import ensure_expanded_dataset, load_official_dataset

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ensure_expanded_dataset_produces_expected_counts():
    expanded_dir = ensure_expanded_dataset(REPO_ROOT)
    assert (expanded_dir / "test_pairs.json").exists()
    assert len(list((expanded_dir / "categories").glob("*.json"))) == 5
    assert len(list((expanded_dir / "merchants").glob("*.json"))) == 50
    assert len(list((expanded_dir / "customers").glob("*.json"))) == 200
    assert len(list((expanded_dir / "triggers").glob("*.json"))) == 100


def test_load_official_dataset_into_store():
    expanded_dir = ensure_expanded_dataset(REPO_ROOT)
    store = ContextStore()
    counts = load_official_dataset(store, expanded_dir)

    assert counts == {"category": 5, "merchant": 50, "customer": 200, "trigger": 100}

    # Spot-check a real seed merchant is retrievable
    dentist_category = store.get("category", "dentists")
    assert dentist_category is not None
    assert dentist_category["slug"] == "dentists"