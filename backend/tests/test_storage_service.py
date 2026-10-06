from __future__ import annotations

from moto import mock_aws

from app.services.storage import StorageService


@mock_aws
def test_storage_service_put_get_and_presign(monkeypatch) -> None:
    monkeypatch.setattr("app.services.storage.settings.s3_endpoint_url", None)
    monkeypatch.setattr("app.services.storage.settings.s3_public_endpoint_url", None)
    monkeypatch.setattr("app.services.storage.settings.s3_region", "us-east-1")
    monkeypatch.setattr("app.services.storage.settings.s3_access_key", "testing")
    monkeypatch.setattr("app.services.storage.settings.s3_secret_key", "testing")
    monkeypatch.setattr("app.services.storage.settings.s3_bucket", "docflow-test")

    service = StorageService()
    service.client.create_bucket(Bucket=service.bucket)
    service.put_object("users/user-id/object-id", b"hello", "application/pdf")

    assert service.get_object("users/user-id/object-id") == b"hello"
    assert "users/user-id/object-id" in service.presign_get_url("users/user-id/object-id")


def test_presign_uses_browser_reachable_endpoint(monkeypatch) -> None:
    monkeypatch.setattr("app.services.storage.settings.s3_endpoint_url", "http://minio:9000")
    monkeypatch.setattr("app.services.storage.settings.s3_public_endpoint_url", "http://localhost:9000")
    monkeypatch.setattr("app.services.storage.settings.s3_access_key", "testing")
    monkeypatch.setattr("app.services.storage.settings.s3_secret_key", "testing")
    service = StorageService()
    assert service.client.meta.endpoint_url == "http://minio:9000"
    assert service.presign_get_url("users/u/key").startswith("http://localhost:9000/")
