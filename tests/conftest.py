import os
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Role, User
from app.seed import seed_reference_data
from app.security import hash_password


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    seed_reference_data(db)
    admin_role = db.query(Role).filter_by(name="Admin").one()
    viewer_role = db.query(Role).filter_by(name="Viewer").one()
    db.add(User(email="admin@test.local", display_name="Admin", password_hash=hash_password("Password12345!"), role_id=admin_role.id, active=True))
    db.add(User(email="viewer@test.local", display_name="Viewer", password_hash=hash_password("Password12345!"), role_id=viewer_role.id, active=True))
    db.commit()
    db.close()

    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
