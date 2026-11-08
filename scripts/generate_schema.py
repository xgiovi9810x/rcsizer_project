"""Esporta lo JSON Schema dello schema di input in schema.json."""
import json
from pathlib import Path
from rcsizer.core.schema import InputSchema

if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "schema.json"
    out.write_text(
        json.dumps(InputSchema.model_json_schema(), indent=2),
        encoding="utf-8",
    )
    print(f"Scritto {out}")
