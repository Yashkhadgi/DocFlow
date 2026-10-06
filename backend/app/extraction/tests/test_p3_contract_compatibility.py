import inspect
import json
from pathlib import Path
import pytest

import app.extraction as extraction_module
from app.extraction.types import (
    DuplicateMatch,
    ExtractionError,
    ExtractionResult,
    FieldValue,
    LineItem,
    ValidationIssue,
)
from app.extraction.extractor import normalize_extraction_data
from app.extraction.validators import validate
from app.extraction.review import low_confidence_fields, needs_review
from app.extraction.duplicates import find_business_duplicate
from app.extraction.export import to_csv, to_json

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent


def test_section_5_4_extraction_schema_conformity():
    schema_path = REPO_ROOT / "contracts" / "extraction_schema.json"
    if schema_path.exists():
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

        required_root_props = schema.get("required", [])
        assert "document_type" in required_root_props
        assert "fields" in required_root_props
        assert "line_items" in required_root_props

    # Build ExtractionResult
    res = ExtractionResult(
        document_type="invoice",
        fields={
            "vendor_name": FieldValue(value="Acme Corp", confidence=0.98, bbox=None),
            "invoice_number": FieldValue(value="INV-001", confidence=0.99, bbox=None),
            "invoice_date": FieldValue(value="2026-09-15", confidence=0.95, bbox=None),
            "gstin": FieldValue(value="27AABCA1234F1Z5", confidence=0.90, bbox=None),
            "currency": FieldValue(value="INR", confidence=0.95, bbox=None),
            "subtotal": FieldValue(value="10000.00", confidence=0.96, bbox=None),
            "tax": FieldValue(value="1800.00", confidence=0.94, bbox=None),
            "total": FieldValue(value="11800.00", confidence=0.97, bbox=None),
        },
        line_items=[
            LineItem(description="Item 1", quantity="1", rate="10000.00", amount="10000.00", confidence=0.95)
        ],
        raw_model_output=None,
    )
    serialized = res.model_dump()
    assert serialized["document_type"] == "invoice"
    assert len(serialized["fields"]) == 8
    for f_name in ["vendor_name", "invoice_number", "invoice_date", "gstin", "currency", "subtotal", "tax", "total"]:
        assert f_name in serialized["fields"]
        assert "value" in serialized["fields"][f_name]
        assert "confidence" in serialized["fields"][f_name]
        assert "bbox" in serialized["fields"][f_name]


def test_section_5_5_function_signatures():
    # 1. extract(file_bytes: bytes, mime_type: str) -> ExtractionResult
    sig_extract = inspect.signature(extraction_module.extract)
    assert list(sig_extract.parameters.keys()) == ["file_bytes", "mime_type"]

    # 2. validate(result: ExtractionResult) -> list[ValidationIssue]
    sig_validate = inspect.signature(extraction_module.validate)
    assert list(sig_validate.parameters.keys()) == ["result"]

    # 3. needs_review(result: ExtractionResult, issues: list[ValidationIssue], threshold: float | None = None) -> bool
    sig_nr = inspect.signature(extraction_module.needs_review)
    assert list(sig_nr.parameters.keys()) == ["result", "issues", "threshold"]
    assert sig_nr.parameters["threshold"].default is None

    # 4. low_confidence_fields(result: ExtractionResult, threshold: float | None = None) -> list[str]
    sig_lcf = inspect.signature(extraction_module.low_confidence_fields)
    assert list(sig_lcf.parameters.keys()) == ["result", "threshold"]
    assert sig_lcf.parameters["threshold"].default is None

    # 5. find_business_duplicate(result: ExtractionResult, existing: list[dict]) -> DuplicateMatch | None
    sig_dup = inspect.signature(extraction_module.find_business_duplicate)
    assert list(sig_dup.parameters.keys()) == ["result", "existing"]

    # 6. to_csv(docs: list[dict]) -> str
    sig_csv = inspect.signature(extraction_module.to_csv)
    assert list(sig_csv.parameters.keys()) == ["docs"]

    # 7. to_json(docs: list[dict]) -> str
    sig_json = inspect.signature(extraction_module.to_json)
    assert list(sig_json.parameters.keys()) == ["docs"]


def test_fixture_compatibility_needs_review():
    fixture_path = REPO_ROOT / "contracts" / "fixtures" / "document_detail_needs_review.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        fixture = json.load(f)

    # Convert fixture fields list to dict
    fields_dict = {
        item["field_name"]: {
            "value": item.get("reviewed_value") or item.get("value"),
            "confidence": item.get("confidence", 0.9),
            "bbox": item.get("bbox"),
        }
        for item in fixture.get("fields", [])
    }
    raw_payload = {
        "document_type": "invoice",
        "fields": fields_dict,
        "line_items": fixture.get("line_items", []),
    }
    res = normalize_extraction_data(raw_payload)

    issues = validate(res)
    # The fixture wrong_total has total mismatch
    assert any(i.rule == "total_mismatch" for i in issues)
    assert needs_review(res, issues) is True
    # GSTIN confidence in fixture is 0.62 (< 0.85)
    low_fields = low_confidence_fields(res)
    assert "gstin" in low_fields


def test_edge_cases_never_raise_exceptions():
    # Empty / all-null result
    res_empty = ExtractionResult(document_type="invoice", fields={}, line_items=[])
    issues = validate(res_empty)
    assert len(issues) >= 4  # missing_required errors
    assert needs_review(res_empty, issues) is True
    assert len(low_confidence_fields(res_empty)) == 7

    # Edge duplicates input
    assert find_business_duplicate(res_empty, []) is None
    assert find_business_duplicate(res_empty, [{"id": "1", "vendor_name": None, "invoice_number": None}]) is None

    # Edge export input
    csv_out = to_csv([])
    assert "document_id,filename,vendor_name" in csv_out
    json_out = to_json([])
    assert json_out == "[]"


def test_export_accepts_arbitrary_person_a_dict_structures():
    # Test case where A passes document with fields dictionary, line items with string/int positions
    a_doc = {
        "document_id": "test-uuid-1",
        "filename": "sample.pdf",
        "fields": {
            "vendor_name": "Vendor A",
            "invoice_number": "INV-101",
            "invoice_date": "2026-09-01",
            "gstin": "27AABCA1234F1Z5",
            "currency": "INR",
            "subtotal": "500.00",
            "tax": "90.00",
            "total": "590.00",
        },
        "line_items": [
            {"position": 1, "description": "Consulting", "quantity": "1", "rate": "500.00", "amount": "500.00"}
        ],
    }

    csv_res = to_csv([a_doc])
    assert "Vendor A" in csv_res
    assert "INV-101" in csv_res

    json_res = to_json([a_doc])
    parsed = json.loads(json_res)
    assert len(parsed) == 1
    assert parsed[0]["fields"]["vendor_name"] == "Vendor A"
