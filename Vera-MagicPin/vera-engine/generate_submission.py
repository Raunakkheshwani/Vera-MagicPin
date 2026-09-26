"""
generate_submission.py — Generates submission.jsonl from expanded_dataset test_pairs.json
"""

import json
from pathlib import Path
from bot import compose

EXPANDED_DIR = Path(__file__).parent / "expanded_dataset"
OUT_FILE = Path(__file__).parent / "submission.jsonl"


def generate():
    pairs_file = EXPANDED_DIR / "test_pairs.json"
    if not pairs_file.exists():
        raise FileNotFoundError(f"Missing {pairs_file}. Has expanded_dataset been generated?")

    data = json.loads(pairs_file.read_text())
    test_pairs = data["pairs"]

    lines = []
    for pair in test_pairs:
        test_id = pair["test_id"]
        trigger_id = pair["trigger_id"]
        merchant_id = pair["merchant_id"]
        customer_id = pair.get("customer_id")

        # Load contexts
        trigger = json.loads((EXPANDED_DIR / "triggers" / f"{trigger_id}.json").read_text())
        merchant = json.loads((EXPANDED_DIR / "merchants" / f"{merchant_id}.json").read_text())
        category_slug = merchant["category_slug"]
        category = json.loads((EXPANDED_DIR / "categories" / f"{category_slug}.json").read_text())

        customer = None
        if customer_id:
            cust_path = EXPANDED_DIR / "customers" / f"{customer_id}.json"
            if cust_path.exists():
                customer = json.loads(cust_path.read_text())

        result = compose(category, merchant, trigger, customer)
        record = {"test_id": test_id, **result}
        lines.append(json.dumps(record, ensure_ascii=False))

    OUT_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Successfully generated {len(lines)} lines in {OUT_FILE}")


if __name__ == "__main__":
    generate()
