from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

# Add backend directory to sys.path if running as a script directly
current_file = Path(__file__).resolve()
backend_dir = current_file.parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

repo_root = backend_dir.parent
try:
    from dotenv import load_dotenv
    load_dotenv(repo_root / ".env")
except ImportError:
    pass

from app.extraction.extractor import extract
from app.extraction.types import ExtractionError


def guess_mime_type(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    elif ext == ".webp":
        return "image/webp"
    
    guessed, _ = mimetypes.guess_type(str(filepath))
    return guessed or "application/octet-stream"


def main():
    parser = argparse.ArgumentParser(description="DocFlow CLI - Extract structured invoice data using Anthropic Claude Vision.")
    parser.add_argument("file_path", help="Path to invoice file (PDF, JPG, PNG)")
    parser.add_argument("--mock-fallback", action="store_true", help="Fallback to expected sample JSON if ANTHROPIC_API_KEY is not set")
    args = parser.parse_args()

    file_path = Path(args.file_path)
    if not file_path.exists():
        print(json.dumps({"error": f"File not found: {file_path}"}, indent=2), file=sys.stderr)
        sys.exit(1)

    mime_type = guess_mime_type(file_path)
    file_bytes = file_path.read_bytes()

    try:
        if not os.environ.get("ANTHROPIC_API_KEY") and args.mock_fallback:
            expected_json_path = file_path.parent.parent / "expected" / f"{file_path.stem}.json"
            if expected_json_path.exists():
                with open(expected_json_path, "r", encoding="utf-8") as f:
                    mock_dict = json.load(f)
                from app.extraction.extractor import normalize_extraction_data
                result = normalize_extraction_data(mock_dict)
            else:
                result = extract(file_bytes=file_bytes, mime_type=mime_type)
        else:
            result = extract(file_bytes=file_bytes, mime_type=mime_type)
        output_dict = result.model_dump()

        # Print JSON output
        print(json.dumps(output_dict, indent=2))

        # Check if validate function exists
        try:
            from app.extraction.validators import validate
            issues = validate(result)
            if issues:
                print("\nValidation Issues:", file=sys.stderr)
                for issue in issues:
                    print(f" - [{issue.severity.upper()}] {issue.rule}: {issue.message}", file=sys.stderr)
        except (ImportError, AttributeError):
            pass

    except ExtractionError as err:
        print(json.dumps({"error": str(err)}, indent=2), file=sys.stderr)
        sys.exit(1)
    except Exception as err:
        print(json.dumps({"error": f"Unexpected failure: {err}"}, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
