from __future__ import annotations

import csv
import io
import json
from typing import Any, Callable

from app.models import Document

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


def sanitize_csv_cell(value: Any) -> str:
    """
    Protect against CSV formula injection.
    Prefix with single quote if cell starts with =, +, -, or @.
    """
    if value is None:
        return ""
    val_str = str(value)
    if val_str and val_str[0] in ("=", "+", "-", "@"):
        return f"'{val_str}"
    return val_str


def get_final_field_value(fields_dict: dict[str, Any], field_name: str) -> str:
    """Extract final string value from field dictionary (reviewed_value if not null else value)."""
    if not isinstance(fields_dict, dict):
        return ""
    val = fields_dict.get(field_name)
    if val is None:
        return ""
    if isinstance(val, dict):
        reviewed = val.get("reviewed_value")
        if reviewed is not None:
            return str(reviewed).strip()
        raw_val = val.get("value")
        return str(raw_val).strip() if raw_val is not None else ""
    return str(val).strip()


def local_to_csv(docs: list[dict[str, Any]]) -> str:
    """
    Local fallback for exporting documents to CSV format.
    One row per line item; one row with empty item columns when no line items.
    Uses standard CSV quoting and CSV formula injection protection.
    """
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(CSV_HEADERS)

    for doc in docs:
        doc_id = sanitize_csv_cell(doc.get("document_id") or doc.get("id") or "")
        filename = sanitize_csv_cell(doc.get("filename") or "")
        fields = doc.get("fields") or {}

        field_vals = [
            sanitize_csv_cell(get_final_field_value(fields, fn))
            for fn in HEADER_FIELD_NAMES
        ]

        line_items = doc.get("line_items") or []
        if not line_items:
            row = [doc_id, filename] + field_vals + ["", "", "", "", ""]
            writer.writerow(row)
        else:
            for idx, item in enumerate(line_items, 1):
                if isinstance(item, dict):
                    pos = str(item.get("position") if item.get("position") is not None else idx)
                    desc = item.get("description")
                    qty = item.get("quantity") if item.get("quantity") is not None else ""
                    rate = item.get("rate") if item.get("rate") is not None else ""
                    amount = item.get("amount") if item.get("amount") is not None else ""
                else:
                    pos = str(getattr(item, "position", idx))
                    desc = getattr(item, "description", "") or ""
                    qty = getattr(item, "quantity", "") if getattr(item, "quantity", None) is not None else ""
                    rate = getattr(item, "rate", "") if getattr(item, "rate", None) is not None else ""
                    amount = getattr(item, "amount", "") if getattr(item, "amount", None) is not None else ""

                row = [
                    doc_id,
                    filename,
                ] + field_vals + [
                    sanitize_csv_cell(pos),
                    sanitize_csv_cell(desc),
                    sanitize_csv_cell(qty),
                    sanitize_csv_cell(rate),
                    sanitize_csv_cell(amount),
                ]
                writer.writerow(row)

    return output.getvalue()


def local_to_json(docs: list[dict[str, Any]]) -> str:
    """
    Local fallback for exporting documents to JSON format.
    Array of { document_id, filename, fields: {final values}, line_items: [...] }.
    """
    cleaned_docs = []
    for doc in docs:
        doc_id = str(doc.get("document_id") or doc.get("id") or "")
        filename = str(doc.get("filename") or "")
        raw_fields = doc.get("fields") or {}

        cleaned_fields = {
            fn: get_final_field_value(raw_fields, fn) or None
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


def get_export_formatter(format_type: str) -> tuple[Callable[[list[dict[str, Any]]], str], str, str]:
    """
    Select the contract-preserving formatter and its response metadata.

    B's exporter treats an explicitly cleared reviewed_value as absent, so the
    local formatter remains in use until that contract mismatch is resolved.
    """
    fmt = format_type.lower().strip()

    if fmt == "csv":
        return local_to_csv, "text/csv; charset=utf-8", "csv"
    elif fmt == "json":
        return local_to_json, "application/json", "json"
    else:
        raise ValueError(f"Unsupported format: {format_type}")


def build_export_payload(documents: list[Document]) -> list[dict[str, Any]]:
    """Build the list of document dicts from database models for export formatting."""
    docs_data: list[dict[str, Any]] = []
    for doc in documents:
        fields_dict: dict[str, dict[str, Any]] = {}
        for f in doc.fields:
            fields_dict[f.field_name] = {
                "value": f.value,
                "reviewed_value": f.reviewed_value,
            }

        line_items_data: list[dict[str, Any]] = []
        for li in sorted(doc.line_items, key=lambda item: item.position):
            line_items_data.append({
                "position": li.position,
                "description": li.description,
                "quantity": str(li.quantity) if li.quantity is not None else None,
                "rate": str(li.rate) if li.rate is not None else None,
                "amount": str(li.amount) if li.amount is not None else None,
            })

        docs_data.append({
            "document_id": str(doc.id),
            "filename": doc.filename,
            "fields": fields_dict,
            "line_items": line_items_data,
        })

    return docs_data
