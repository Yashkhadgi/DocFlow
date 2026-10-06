"""Exercise the deployed API and worker without printing credentials or tokens."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


SAMPLE = Path(__file__).resolve().parents[1] / "samples/invoices/clean_invoice.pdf"
TIMEOUT_SECONDS = 120


def request(url: str, *, method: str = "GET", token: str | None = None,
            body: bytes | None = None, content_type: str | None = None) -> tuple[int, bytes]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=30) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"{'PASS' if condition else 'FAIL'} {name}{': ' + detail if detail else ''}")
    if not condition:
        raise RuntimeError(name)


def main() -> int:
    base = os.environ.get("BASE_URL", "").rstrip("/")
    email = os.environ.get("EMAIL")
    password = os.environ.get("PASSWORD")
    if not base or not email or not password:
        print("FAIL configuration: set BASE_URL, EMAIL, and PASSWORD")
        return 1
    if base.endswith("/api/v1"):
        base = base[:-len("/api/v1")]
    api = base + "/api/v1"

    try:
        status, raw = request(api + "/health")
        check("health", status == 200 and json.loads(raw).get("status") == "ok")

        status, raw = request(
            api + "/auth/login", method="POST",
            body=json.dumps({"email": email, "password": password}).encode(),
            content_type="application/json",
        )
        login = json.loads(raw)
        check("login", status == 200 and bool(login.get("access_token")))
        token = login["access_token"]

        boundary = "docflow-" + uuid4().hex
        pdf = SAMPLE.read_bytes()
        multipart = (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; "
            f"filename=\"{SAMPLE.name}\"\r\nContent-Type: application/pdf\r\n\r\n"
        ).encode() + pdf + f"\r\n--{boundary}--\r\n".encode()
        status, raw = request(
            api + "/documents/upload", method="POST", token=token,
            body=multipart, content_type=f"multipart/form-data; boundary={boundary}",
        )
        upload = json.loads(raw)
        item = (upload.get("results") or [{}])[0]
        check("upload", status == 200 and item.get("status") in {"queued", "duplicate"})
        document_id = item.get("duplicate_of_id") or item.get("document_id")
        check("document id", bool(document_id))

        deadline = time.monotonic() + TIMEOUT_SECONDS
        detail = {}
        while time.monotonic() < deadline:
            status, raw = request(api + f"/documents/{document_id}", token=token)
            detail = json.loads(raw) if status == 200 else {}
            if detail.get("status") in {"needs_review", "approved", "failed"}:
                break
            time.sleep(2)
        check("worker completion", detail.get("status") in {"needs_review", "approved"},
              f"status={detail.get('status', 'unavailable')}")
        check("detail", status == 200 and bool(detail.get("fields")))

        file_url = detail.get("file_url")
        check("presigned URL", bool(file_url))
        file_status, downloaded = request(file_url)
        check("file download", file_status == 200 and downloaded.startswith(b"%PDF"))

        query = urlencode({"format": "csv", "status": detail["status"], "ids": document_id})
        csv_status, csv_data = request(api + "/export?" + query, token=token)
        check("CSV export", csv_status == 200 and document_id.encode() in csv_data)
        return 0
    except (RuntimeError, ValueError, KeyError, OSError, URLError) as exc:
        if not isinstance(exc, RuntimeError):
            print(f"FAIL request: {type(exc).__name__}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
