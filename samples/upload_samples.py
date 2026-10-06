"""
DocFlow V1: Sample Document Uploader & Live Data Seeder (Task P5)
Uploads sample invoices to the live API or local backend via official contract endpoints.
"""

import argparse
import getpass
import json
import mimetypes
import os
import sys
import time
from pathlib import Path
from typing import Any

# Use requests for HTTP interaction
try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install via: pip install requests", file=sys.stderr)
    sys.exit(1)

# Default demo files to exclude so they stay fresh for the live 3-minute demo
DEFAULT_DEMO_EXCLUSIONS = [
    "clean_invoice_copy.pdf",      # Used in demo Step 4 (same-file hash duplicate check)
    "same_invoice_resaved.pdf",   # Used in demo Step 4 (business duplicate check)
    "failme.pdf",                 # Used in demo Step 5 (worker retries and backoff demo)
    "wrong_total.pdf",            # Used in demo Step 3 (split-screen review & edit demo)
]


def guess_mime(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext == ".pdf":
        return "application/pdf"
    elif ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    elif ext == ".png":
        return "image/png"
    return "application/octet-stream"


def wait_for_server_health(base_url: str, max_retries: int = 6, backoff: float = 2.0) -> bool:
    """Handle Render free-tier cold starts by pinging /health before starting."""
    # Derive health check URL: replace /api/v1 with /health or /api/v1/health
    health_url = base_url.rstrip("/") + "/health" if "/api/v1" in base_url else base_url.rstrip("/") + "/api/v1/health"
    print(f"Pinging server health at {health_url} (handling cold starts)...")

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(health_url, timeout=10.0)
            if resp.status_code == 200:
                print(f"[OK] Server is live and healthy (attempt {attempt})!\n")
                return True
        except requests.RequestException as e:
            print(f"Waiting for server warm-up (attempt {attempt}/{max_retries})...")
            time.sleep(backoff)
            backoff *= 1.5

    print("[WARN] Server did not respond to /health in time, proceeding anyway...\n", file=sys.stderr)
    return False


def login(base_url: str, email: str, password: str) -> str:
    """Authenticate with DocFlow API and retrieve JWT Bearer token."""
    login_url = f"{base_url.rstrip('/')}/auth/login"
    print(f"Logging in as '{email}'...")
    try:
        resp = requests.post(
            login_url,
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=15.0,
        )
        if resp.status_code != 200:
            print(f"Login failed (HTTP {resp.status_code}): {resp.text}", file=sys.stderr)
            sys.exit(1)

        token = resp.json().get("access_token")
        if not token:
            print("Error: No access_token found in login response.", file=sys.stderr)
            sys.exit(1)
        print("[OK] Authentication successful!\n")
        return token
    except requests.RequestException as err:
        print(f"Connection error during login: {err}", file=sys.stderr)
        sys.exit(1)


def upload_batch(base_url: str, token: str, file_paths: list[Path]) -> list[dict[str, Any]]:
    """Upload documents in batches of up to 20 files via multipart/form-data."""
    upload_url = f"{base_url.rstrip('/')}/documents/upload"
    headers = {"Authorization": f"Bearer {token}"}

    results = []
    # Split into batches of 20
    for i in range(0, len(file_paths), 20):
        batch = file_paths[i : i + 20]
        print(f"Uploading batch of {len(batch)} document(s)...")

        files_payload = []
        opened_files = []
        try:
            for p in batch:
                f_obj = open(p, "rb")
                opened_files.append(f_obj)
                files_payload.append(("files", (p.name, f_obj, guess_mime(p))))

            resp = requests.post(upload_url, headers=headers, files=files_payload, timeout=60.0)
            if resp.status_code not in (200, 207):
                print(f"Upload batch failed (HTTP {resp.status_code}): {resp.text}", file=sys.stderr)
                continue

            batch_results = resp.json().get("results", [])
            results.extend(batch_results)
            print(f"[OK] Batch processed ({len(batch_results)} results received).\n")
        except requests.RequestException as e:
            print(f"Network error during upload: {e}", file=sys.stderr)
        finally:
            for f in opened_files:
                f.close()

    return results


def poll_document_statuses(base_url: str, token: str, timeout_seconds: int = 60) -> dict[str, Any]:
    """Poll GET /documents until no jobs remain in queued or processing status."""
    docs_url = f"{base_url.rstrip('/')}/documents"
    headers = {"Authorization": f"Bearer {token}"}

    print(f"Waiting for asynchronous background workers to finish (timeout {timeout_seconds}s)...")
    start_time = time.time()

    last_counts = {}
    while time.time() - start_time < timeout_seconds:
        try:
            resp = requests.get(docs_url, headers=headers, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                counts = data.get("counts", {})
                last_counts = counts

                queued = counts.get("queued", 0)
                processing = counts.get("processing", 0)

                print(
                    f" - Status: Queued={queued}, Processing={processing}, Needs Review={counts.get('needs_review', 0)}, "
                    f"Approved={counts.get('approved', 0)}, Failed={counts.get('failed', 0)}, Duplicate={counts.get('duplicate', 0)}"
                )

                if queued == 0 and processing == 0:
                    print("\n[OK] All uploaded documents processed!")
                    return counts

            time.sleep(3.0)
        except requests.RequestException:
            time.sleep(3.0)

    print("\n[WARN] Polling timed out while some jobs were still processing.", file=sys.stderr)
    return last_counts


def mock_dry_run(file_paths: list[Path]):
    """Simulate upload workflow locally when API server is offline."""
    print("=== RUNNING IN MOCK DRY-RUN MODE ===")
    print(f"Found {len(file_paths)} candidate files to upload:")
    for p in file_paths:
        print(f" - {p.name:<28} ({guess_mime(p)}, {p.stat().st_size} bytes)")
    print("\n[OK] Mock upload simulation complete. File paths and MIME types verified.")


def main():
    parser = argparse.ArgumentParser(description="DocFlow V1 Demo Data Loader")
    parser.add_argument("--base-url", default=os.getenv("VITE_API_BASE_URL", "http://localhost:8000/api/v1"), help="API Base URL")
    parser.add_argument("--email", default="demo@docflow.app", help="User email")
    parser.add_argument("--password", default=os.getenv("DEMO_PASSWORD", "Demo@1234"), help="User password")
    parser.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent / "invoices", help="Directory containing invoices")
    parser.add_argument("--only", type=str, default=None, help="Comma-separated list of filenames to upload")
    parser.add_argument("--exclude", type=str, default=",".join(DEFAULT_DEMO_EXCLUSIONS), help="Comma-separated list of filenames to exclude")
    parser.add_argument("--wait", action="store_true", help="Poll /documents until worker queue completes")
    parser.add_argument("--dry-run", action="store_true", help="Run local validation without sending network requests")
    args = parser.parse_args()

    invoices_dir = args.dir
    if not invoices_dir.exists():
        print(f"Error: Invoices directory not found: {invoices_dir}", file=sys.stderr)
        sys.exit(1)

    all_files = sorted([
        f for f in invoices_dir.iterdir()
        if f.is_file() and f.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png", ".webp")
    ])

    # Filter by --only or --exclude
    if args.only:
        only_set = set(x.strip() for x in args.only.split(",") if x.strip())
        target_files = [f for f in all_files if f.name in only_set]
    else:
        exclude_set = set(x.strip() for x in args.exclude.split(",") if x.strip())
        target_files = [f for f in all_files if f.name not in exclude_set]

    if not target_files:
        print("No files matched the upload criteria.", file=sys.stderr)
        sys.exit(0)

    if args.dry_run:
        mock_dry_run(target_files)
        return

    password = args.password
    if not password:
        password = getpass.getpass(f"Enter password for {args.email}: ")

    # 1. Server Health Warm-up
    wait_for_server_health(args.base_url)

    # 2. Login
    token = login(args.base_url, args.email, password)

    # 3. Upload batch
    results = upload_batch(args.base_url, token, target_files)

    print("=" * 80)
    print(f"{'Filename':<28} | {'Status':<12} | {'Duplicate Of':<20} | {'Error'}")
    print("=" * 80)
    for r in results:
        fname = r.get("filename", "unknown")
        status = r.get("status") or "N/A"
        dup_of = r.get("duplicate_of_id") or "-"
        err = r.get("error", {}).get("message") if r.get("error") else "-"
        print(f"{fname:<28} | {status:<12} | {dup_of:<20} | {err}")
    print("=" * 80)

    # 4. Optional polling
    if args.wait:
        final_counts = poll_document_statuses(args.base_url, token)
        print("\nFinal Document Counts:")
        print(json.dumps(final_counts, indent=2))


if __name__ == "__main__":
    main()
