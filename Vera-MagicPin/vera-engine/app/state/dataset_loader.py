"""
vera-engine/app/state/dataset_loader.py

Runs the OFFICIAL, unmodified dataset/generate_dataset.py (via subprocess,
so the ZIP itself is never touched) and loads its output into our
ContextStore at startup — simulating what the judge's real warmup phase
does: push all 5 categories, 50 merchants, 200 customers, 100 triggers
before the test window begins.

Output is written to vera-engine's OWN local folder (not inside the
official ZIP folder), so re-running this never modifies the source of
truth.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from app.state.context_store import ContextStore

EXPANDED_DIR_NAME = "expanded_dataset"  # lives under vera-engine/, gitignore-able


def _find_official_zip_dir(repo_root: Path) -> Path:
    """Locate the official ZIP's extracted root by finding generate_dataset.py."""
    matches = [
        p for p in repo_root.rglob("generate_dataset.py")
        if ".venv" not in p.parts and "expanded_dataset" not in p.parts
    ]
    if not matches:
        raise FileNotFoundError(
            f"Could not find generate_dataset.py anywhere under {repo_root}. "
            f"Is the official ZIP extracted somewhere in this repo?"
        )
    # generate_dataset.py lives at <zip_root>/dataset/generate_dataset.py
    return matches[0].parent


def ensure_expanded_dataset(repo_root: Path) -> Path:
    """
    Runs the official generator once (idempotent — SEED is fixed, so
    re-running always produces the same output) and returns the path to
    the expanded dataset folder.
    """
    dataset_dir = _find_official_zip_dir(repo_root)  # .../dataset/
    out_dir = repo_root / "vera-engine" / EXPANDED_DIR_NAME

    if not (out_dir / "test_pairs.json").exists():
        result = subprocess.run(
            [sys.executable, str(dataset_dir / "generate_dataset.py"),
             "--seed-dir", str(dataset_dir), "--out", str(out_dir)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"generate_dataset.py failed:\n{result.stderr}")

    return out_dir


def load_official_dataset(store: ContextStore, expanded_dir: Path) -> dict:
    """
    Walks the expanded dataset and pushes every record into the given
    ContextStore, exactly as the judge's warmup would. Returns counts
    loaded, for logging/verification.
    """
    counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}

    for f in sorted((expanded_dir / "categories").glob("*.json")):
        data = json.loads(f.read_text())
        store.push("category", data["slug"], version=1, payload=data)
        counts["category"] += 1

    for f in sorted((expanded_dir / "merchants").glob("*.json")):
        data = json.loads(f.read_text())
        store.push("merchant", data["merchant_id"], version=1, payload=data)
        counts["merchant"] += 1

    for f in sorted((expanded_dir / "customers").glob("*.json")):
        data = json.loads(f.read_text())
        store.push("customer", data["customer_id"], version=1, payload=data)
        counts["customer"] += 1

    for f in sorted((expanded_dir / "triggers").glob("*.json")):
        data = json.loads(f.read_text())
        store.push("trigger", data["id"], version=1, payload=data)
        counts["trigger"] += 1

    return counts