import csv
import io
import json
import pytest

from app.extraction.export import to_csv, to_json, CSV_HEADERS


def _sample_docs():
    return [
        {
            "document_id": "doc-uuid-1",
            "filename": "inv1.pdf",
            "fields": {
                "vendor_name": "Apex Infotech Solutions Pvt Ltd",
                "invoice_number": "INV-2026-001",
                "invoice_date": "2026-09-15",
                "gstin": "27AABCA1234F1Z5",
                "currency": "INR",
                "subtotal": "10000.00",
                "tax": "1800.00",
                "total": "11800.00",
            },
            "line_items": [
                {"position": 1, "description": "Cloud Hosting, Tier 1", "quantity": "1", "rate": "5000.00", "amount": "5000.00"},
                {"position": 2, "description": "Technical Support \"Pro\"", "quantity": "10", "rate": "350.00", "amount": "3500.00"},
                {"position": 3, "description": "SSL Cert\n1-Year", "quantity": "1", "rate": "1500.00", "amount": "1500.00"},
            ],
        },
        {
            "document_id": "doc-uuid-2",
            "filename": "inv2_no_items.pdf",
            "fields": {
                "vendor_name": {"value": "Old Name", "reviewed_value": "Acme Reviewed"},
                "invoice_number": "INV-002",
                "invoice_date": "2026-09-10",
                "gstin": "29AABCB5678G1Z2",
                "currency": "INR",
                "subtotal": "2000.00",
                "tax": "360.00",
                "total": "2360.00",
            },
            "line_items": [],
        },
    ]


def test_csv_headers_and_order():
    csv_str = to_csv([])
    reader = list(csv.reader(io.StringIO(csv_str)))
    assert len(reader) == 1
    assert reader[0] == CSV_HEADERS


def test_csv_row_counts_and_line_items():
    docs = _sample_docs()
    csv_str = to_csv(docs)
    reader = list(csv.reader(io.StringIO(csv_str)))

    # 1 header + 3 rows from doc 1 + 1 row from doc 2 = 5 rows
    assert len(reader) == 5

    # Check doc 1 items
    assert reader[1][0] == "doc-uuid-1"
    assert reader[1][1] == "inv1.pdf"
    assert reader[1][2] == "Apex Infotech Solutions Pvt Ltd"
    assert reader[1][10] == "1"
    assert reader[1][11] == "Cloud Hosting, Tier 1"
    assert reader[1][14] == "5000.00"

    assert reader[2][10] == "2"
    assert reader[2][11] == 'Technical Support "Pro"'

    # Check doc 2 with reviewed_value and empty line items
    assert reader[4][0] == "doc-uuid-2"
    assert reader[4][2] == "Acme Reviewed"  # used reviewed_value over value
    assert reader[4][10] == ""  # empty position
    assert reader[4][11] == ""  # empty description
    assert reader[4][14] == ""  # empty amount


def test_to_json_structure():
    docs = _sample_docs()
    json_str = to_json(docs)
    parsed = json.loads(json_str)

    assert isinstance(parsed, list)
    assert len(parsed) == 2

    # Doc 1
    d1 = parsed[0]
    assert d1["document_id"] == "doc-uuid-1"
    assert d1["fields"]["vendor_name"] == "Apex Infotech Solutions Pvt Ltd"
    assert len(d1["line_items"]) == 3
    assert d1["line_items"][0]["description"] == "Cloud Hosting, Tier 1"

    # Doc 2
    d2 = parsed[1]
    assert d2["document_id"] == "doc-uuid-2"
    assert d2["fields"]["vendor_name"] == "Acme Reviewed"
    assert len(d2["line_items"]) == 0
