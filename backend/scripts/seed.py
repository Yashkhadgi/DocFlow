from __future__ import annotations

from sqlalchemy.orm import Session

from app.auth.security import hash_password, normalize_email
from app.db import SessionLocal
from app.models import User

DEMO_EMAIL = "demo@docflow.app"
DEMO_PASSWORD = "Demo@1234"


def seed_demo_user(db: Session) -> User:
    email = normalize_email(DEMO_EMAIL)
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user is not None:
        return existing_user

    user = User(
        email=email,
        password_hash=hash_password(DEMO_PASSWORD),
        full_name="Demo User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def main() -> None:
    db = SessionLocal()
    try:
        user = seed_demo_user(db)
        print(f"Seeded demo user: {user.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
