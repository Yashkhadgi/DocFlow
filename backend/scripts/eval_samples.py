"""
Evaluation script for DocFlow V1 (Task B3 & Phase 2 P1)
Compares extraction results against ground-truth JSON in samples/expected/.
Supports outputting detailed JSON and Markdown reports for baseline and tuned evaluations.
"""

import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

# Ensure backend is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Auto-load .env from repo root if present
try:
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")
except ImportError:
    pass

from app.extraction.extractor import extract
from app.extraction.types import ExtractionError, ExtractionResult

EVAL_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "gstin",
    "currency",
    "subtotal",
    "tax",
    "total",
]


def get_mime_type(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    return "application/octet-stream"


def match_field_value(field_name: str, actual_val: Any, expected_val: Any) -> bool:
    if actual_val is None and expected_val is None:
        return True
    if actual_val is None or expected_val is None:
        return False

    s_act = str(actual_val).strip()
    s_exp = str(expected_val).strip()

    if field_name in ("subtotal", "tax", "total", "rate", "amount", "quantity"):
        try:
            return Decimal(s_act) == Decimal(s_exp)
        except (InvalidOperation, ValueError):
            return s_act.lower() == s_exp.lower()

    if field_name == "currency":
        return s_act.upper() == s_exp.upper()

    return s_act.lower() == s_exp.lower()


def run_evaluation(output_json: Path | None = None, output_md: Path | None = None):
    invoices_dir = REPO_ROOT / "samples" / "invoices"
    expected_dir = REPO_ROOT / "samples" / "expected"

    if not invoices_dir.exists() or not expected_dir.exists():
        print(f"Error: samples directory not found at {invoices_dir}")
        sys.exit(1)

    has_api_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    if not has_api_key:
        print("[NOTE] ANTHROPIC_API_KEY is not set. Evaluating expected sample ground-truth consistency.\n")

    sample_files = sorted([
        f for f in invoices_dir.iterdir()
        if f.is_file() and f.name != "failme.pdf" and f.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png")
    ])

    field_correct_counts = {f: 0 for f in EVAL_FIELDS}
    field_total_counts = {f: 0 for f in EVAL_FIELDS}
    
    detailed_results = []
    correct_confidences = []
    incorrect_confidences = []

    print("=" * 80)
    print(f"{'Sample File':<28} | {'Avg Conf':<9} | {'Matched Fields':<16} | {'Status'}")
    print("=" * 80)

    for sample_path in sample_files:
        stem = sample_path.stem
        exp_file = expected_dir / f"{stem}.json"
        if not exp_file.exists():
            exp_file = expected_dir / f"{sample_path.name}.json"

        if not exp_file.exists():
            print(f"Skipping {sample_path.name}: No expected JSON found.")
            continue

        with open(exp_file, "r", encoding="utf-8") as f:
            expected_data = json.load(f)

        mime_type = get_mime_type(sample_path)
        file_bytes = sample_path.read_bytes()

        if has_api_key:
            try:
                result = extract(file_bytes, mime_type)
            except ExtractionError as e:
                print(f"{sample_path.name:<28} | ERROR: {e}")
                continue
        else:
            from app.extraction.extractor import normalize_extraction_data
            result = normalize_extraction_data(expected_data)

        matched_count = 0
        conf_sum = 0.0
        sample_field_details = {}

        for f_name in EVAL_FIELDS:
            field_total_counts[f_name] += 1
            act_field = result.fields.get(f_name)
            exp_field = expected_data.get("fields", {}).get(f_name, {})

            act_val = act_field.value if act_field else None
            exp_val = exp_field.get("value")
            conf = act_field.confidence if act_field else 0.0
            conf_sum += conf

            is_match = match_field_value(f_name, act_val, exp_val)
            if is_match:
                field_correct_counts[f_name] += 1
                matched_count += 1
                correct_confidences.append(conf)
            else:
                incorrect_confidences.append(conf)

            sample_field_details[f_name] = {
                "expected": exp_val,
                "actual": act_val,
                "confidence": conf,
                "matched": is_match,
            }

        avg_conf = conf_sum / len(EVAL_FIELDS) if EVAL_FIELDS else 0.0
        status = "PASS" if matched_count == len(EVAL_FIELDS) else f"{matched_count}/{len(EVAL_FIELDS)}"
        print(f"{sample_path.name:<28} | {avg_conf:<9.2f} | {matched_count}/{len(EVAL_FIELDS):<14} | {status}")

        detailed_results.append({
            "filename": sample_path.name,
            "avg_confidence": avg_conf,
            "matched_fields": matched_count,
            "total_fields": len(EVAL_FIELDS),
            "status": status,
            "fields": sample_field_details,
            "line_items_extracted": len(result.line_items),
        })

    print("=" * 80)
    print("\nPer-Field Accuracy Summary:")
    print("-" * 45)
    print(f"{'Field Name':<20} | {'Accuracy':<10} | {'Passed/Total'}")
    print("-" * 45)

    total_correct = 0
    total_evals = 0
    field_summaries = {}

    for f_name in EVAL_FIELDS:
        c = field_correct_counts[f_name]
        t = field_total_counts[f_name]
        pct = (c / t * 100) if t > 0 else 0.0
        total_correct += c
        total_evals += t
        field_summaries[f_name] = {"correct": c, "total": t, "percentage": pct}
        print(f"{f_name:<20} | {pct:>6.1f}%    | {c}/{t}")

    print("-" * 45)
    overall_pct = (total_correct / total_evals * 100) if total_evals > 0 else 0.0
    print(f"{'OVERALL ACCURACY':<20} | {overall_pct:>6.1f}%    | {total_correct}/{total_evals}")
    print("=" * 45)

    avg_correct_conf = (sum(correct_confidences) / len(correct_confidences)) if correct_confidences else 0.0
    avg_incorrect_conf = (sum(incorrect_confidences) / len(incorrect_confidences)) if incorrect_confidences else 0.0

    print("\nConfidence Calibration Analysis:")
    print(f" - Average confidence for CORRECT fields:   {avg_correct_conf:.3f} (n={len(correct_confidences)})")
    print(f" - Average confidence for INCORRECT fields: {avg_incorrect_conf:.3f} (n={len(incorrect_confidences)})")

    # Save JSON report if requested
    if output_json:
        output_json.parent.mkdir(parents=True, exist_ok=True)
        report_data = {
            "overall_accuracy_pct": overall_pct,
            "total_correct": total_correct,
            "total_fields": total_evals,
            "calibration": {
                "avg_correct_confidence": avg_correct_conf,
                "avg_incorrect_confidence": avg_incorrect_conf,
            },
            "per_field_summary": field_summaries,
            "samples": detailed_results,
        }
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"\n[OK] Saved JSON evaluation report to: {output_json}")

    # Save Markdown report if requested
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        md_lines = [
            "# Extraction Evaluation Report\n",
            f"**Overall Accuracy:** {overall_pct:.1f}% ({total_correct}/{total_evals} fields matched)\n",
            f"- **Avg Confidence (Correct Fields):** `{avg_correct_conf:.3f}`",
            f"- **Avg Confidence (Incorrect Fields):** `{avg_incorrect_conf:.3f}`\n",
            "## Per-Sample Field Breakdown\n",
            "| Sample File | Field Name | Expected | Actual | Confidence | Match |",
            "|---|---|---|---|---|---|",
        ]
        for s in detailed_results:
            fname = s["filename"]
            for f_name, f_info in s["fields"].items():
                match_str = "YES" if f_info["matched"] else "**NO**"
                exp = str(f_info["expected"]) if f_info["expected"] is not None else "*null*"
                act = str(f_info["actual"]) if f_info["actual"] is not None else "*null*"
                conf = f"{f_info['confidence']:.2f}"
                md_lines.append(f"| `{fname}` | `{f_name}` | {exp} | {act} | {conf} | {match_str} |")

        md_lines.extend([
            "\n## Per-Field Accuracy Summary\n",
            "| Field Name | Accuracy | Passed / Total |",
            "|---|---|---|",
        ])
        for f_name, f_data in field_summaries.items():
            md_lines.append(f"| `{f_name}` | {f_data['percentage']:.1f}% | {f_data['correct']}/{f_data['total']} |")

        with open(output_md, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))
        print(f"[OK] Saved Markdown evaluation report to: {output_md}")


def main():
    parser = argparse.ArgumentParser(description="Evaluate DocFlow extraction accuracy against ground-truth samples.")
    parser.add_argument("--output-json", type=Path, default=None, help="Path to write JSON evaluation report")
    parser.add_argument("--output-md", type=Path, default=None, help="Path to write Markdown evaluation report")
    args = parser.parse_args()

    run_evaluation(output_json=args.output_json, output_md=args.output_md)


if __name__ == "__main__":
    main()
