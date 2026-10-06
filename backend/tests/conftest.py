from collections.abc import Generator

import email_validator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

email_validator.TEST_ENVIRONMENT = True


from app.db import SessionLocal
from app.main import app
from app.models import Document, Job, User


@pytest.fixture()
def db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup_test_users(db: Session) -> Generator[None, None, None]:
    delete_test_users(db)
    yield
    delete_test_users(db)


def delete_test_users(db: Session) -> None:
    test_user_ids = [
        user_id
        for (user_id,) in db.query(User.id)
        .filter((User.email.like("%@example.test")) | (User.email == "demo@docflow.app"))
        .all()
    ]
    if test_user_ids:
        document_ids = [
            document_id
            for (document_id,) in db.query(Document.id).filter(Document.user_id.in_(test_user_ids)).all()
        ]
        if document_ids:
            db.query(Job).filter(Job.document_id.in_(document_ids)).delete(synchronize_session=False)
            db.query(Document).filter(
                Document.id.in_(document_ids),
                Document.status == "duplicate",
            ).delete(synchronize_session=False)
            db.query(Document).filter(Document.id.in_(document_ids)).delete(synchronize_session=False)
    db.query(User).filter(User.email.like("%@example.test")).delete(synchronize_session=False)
    db.query(User).filter(User.email == "demo@docflow.app").delete(synchronize_session=False)
    db.commit()
