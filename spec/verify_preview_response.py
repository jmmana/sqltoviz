"""Validate actual Python preview plans and invalid wire examples."""
import json
from pathlib import Path
import sys

from jsonschema import Draft202012Validator

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "packages/python"))
from sqltoviz import recommend


def main():
    schema = json.loads((root / "spec/preview-response-v0.1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    fixtures = json.loads((root / "parity/preview-v0.1.json").read_text())["charts"]
    for case in fixtures:
        validator.validate(recommend(case["sql"], case["rows"]))

    scalar = recommend("SELECT 1", [{"value": 1}])
    for invalid in (
        {**scalar, "contract_version": "preview-v9"},
        {**scalar, "encodings": {}},
        {**scalar, "encodings": {"x": "label", "y": "value"}},
        {**scalar, "chartType": "table"},
        {**scalar, "chartType": "line"},
    ):
        if validator.is_valid(invalid):
            raise ValueError(f"Invalid response accepted: {invalid}")
    print(f"Validated {len(fixtures)} preview responses and rejected 5 invalid responses.")


if __name__ == "__main__":
    main()
