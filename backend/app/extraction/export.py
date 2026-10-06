from __future__ import annotations

import csv
import io
import json
from typing import Any

CSV_HEADERS = [
    "document_id",
    "filename",
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "gstin",
    "currency",
    "subtotal",
    "tax",
    "total",
    "item_position",
    "item_description",
    "item_quantity",
    "item_rate",
    "item_amount",
]

HEADER_FIELD_NAMES = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "gstin",
    "currency",
    "subtotal",
    "tax",
    "total",
]


def _get_final_field_value(fields_dict: dict[str, Any], field_name: str) -> str:
    """Extract final string value from field dictionary or raw value."""
    if not isinstance(fields_dict, dict):
        return ""
    val = fields_dict.get(field_name)
    if val is None:
        return ""
    if isinstance(val, dict):
        # Support dict format with reviewed_value / value
        reviewed = val.get("reviewed_value")
        if reviewed is not None and str(reviewed).strip() != "":
            return str(reviewed).strip()
        raw_val = val.get("value")
        return str(raw_val).strip() if raw_val is not None else ""
    return str(val).strip()


def to_csv(docs: list[dict[str, Any]]) -> str:
    """
    Export documents to CSV string matching Section 5.3 contract.
    One row per line item. Invoices with no line items yield one row with empty item columns.
    Uses standard CSV quoting for commas, quotes, and newlines.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")

    # Write header
    writer.writerow(CSV_HEADERS)

    for doc in docs:
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        filename = str(doc.get("filename") or "")
        fields = doc.get("fields") or {}

        field_vals = [_get_final_field_value(fields, fn) for fn in HEADER_FIELD_NAMES]

        line_items = doc.get("line_items") or []
        if not line_items:
            # Single row with empty line item values
            row = [doc_id, filename] + field_vals + ["", "", "", "", ""]
            writer.writerow(row)
        else:
            for idx, item in enumerate(line_items, 1):
                if isinstance(item, dict):
                    pos = str(item.get("position") if item.get("position") is not None else idx)
                    desc = str(item.get("description") or "")
                    qty = str(item.get("quantity") if item.get("quantity") is not None else "")
                    rate = str(item.get("rate") if item.get("rate") is not None else "")
                    amount = str(item.get("amount") if item.get("amount") is not None else "")
                else:
                    pos = str(getattr(item, "position", idx))
                    desc = str(getattr(item, "description", "") or "")
                    qty = str(getattr(item, "quantity", "") or "")
                    rate = str(getattr(item, "rate", "") or "")
                    amount = str(getattr(item, "amount", "") or "")

                row = [doc_id, filename] + field_vals + [pos, desc, qty, rate, amount]
                writer.writerow(row)

    return output.getvalue()


def to_json(docs: list[dict[str, Any]]) -> str:
    """
    Export documents to JSON string matching Section 5.3 contract.
    Array of { document_id, filename, fields: {...}, line_items: [...] }.
    """
    cleaned_docs = []
    for doc in docs:
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        filename = str(doc.get("filename") or "")
        raw_fields = doc.get("fields") or {}

        cleaned_fields = {
            fn: _get_final_field_value(raw_fields, fn) or None
            for fn in HEADER_FIELD_NAMES
        }

        cleaned_items = []
        for idx, item in enumerate(doc.get("line_items") or [], 1):
            if isinstance(item, dict):
                cleaned_items.append({
                    "position": item.get("position") if item.get("position") is not None else idx,
                    "description": item.get("description"),
                    "quantity": str(item.get("quantity")) if item.get("quantity") is not None else None,
                    "rate": str(item.get("rate")) if item.get("rate") is not None else None,
                    "amount": str(item.get("amount")) if item.get("amount") is not None else None,
                })
            else:
                cleaned_items.append({
                    "position": getattr(item, "position", idx),
                    "description": getattr(item, "description", None),
                    "quantity": str(getattr(item, "quantity", None)) if getattr(item, "quantity", None) is not None else None,
                    "rate": str(getattr(item, "rate", None)) if getattr(item, "rate", None) is not None else None,
                    "amount": str(getattr(item, "amount", None)) if getattr(item, "amount", None) is not None else None,
                })

        cleaned_docs.append({
            "document_id": doc_id,
            "filename": filename,
            "fields": cleaned_fields,
            "line_items": cleaned_items,
        })

    return json.dumps(cleaned_docs, indent=2)
