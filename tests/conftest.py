import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.main import app
from app.database import engine, get_db, Base


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables once per test session."""
    Base.metadata.create_all(bind=engine)
    yield
    # Optionally drop tables after all tests
    # Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a database session with transaction rollback after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()

    # Each time a transaction ends, start a new one
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        nonlocal nested
        if transaction.nested and not transaction._parent.nested:
            nested = connection.begin_nested()

    yield session

    # Rollback the transaction to undo all changes
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """Create test client with overridden database session."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Standard test user registration data."""
    return {
        "username": "test_user",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com"
    }


@pytest.fixture
def second_user_data():
    """Second test user for follow tests."""
    return {
        "username": "second_user",
        "password": "testpassword123",
        "first_name": "Second",
        "last_name": "User",
        "email": "second@example.com"
    }


@pytest.fixture
def third_user_data():
    """Third test user for follow tests."""
    return {
        "username": "third_user",
        "password": "testpassword123",
        "first_name": "Third",
        "last_name": "User",
        "email": "third@example.com"
    }


@pytest.fixture
def registered_user(client, test_user_data):
    """Register a user and return user data with tokens."""
    response = client.post("/api/auth/register", json=test_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def auth_headers(registered_user):
    """Return authorization headers for registered user."""
    return {"Authorization": f"Bearer {registered_user['access_token']}"}


@pytest.fixture
def second_registered_user(client, second_user_data):
    """Register second user and return user data with tokens."""
    response = client.post("/api/auth/register", json=second_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def second_auth_headers(second_registered_user):
    """Return authorization headers for second user."""
    return {"Authorization": f"Bearer {second_registered_user['access_token']}"}


@pytest.fixture
def third_registered_user(client, third_user_data):
    """Register third user and return user data with tokens."""
    response = client.post("/api/auth/register", json=third_user_data)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def third_auth_headers(third_registered_user):
    """Return authorization headers for third user."""
    return {"Authorization": f"Bearer {third_registered_user['access_token']}"}
