"""Tests for 01-user-management.md endpoints."""
import pytest


class TestAuthRegister:
    """1.1 POST /api/auth/register"""

    def test_register_success(self, client, test_user_data):
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 201
        data = response.json()
        assert data["user"]["username"] == test_user_data["username"]
        assert data["user"]["first_name"] == test_user_data["first_name"]
        assert data["user"]["account_type"] == "registered"
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username(self, client, test_user_data):
        client.post("/api/auth/register", json=test_user_data)
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_user_data, second_user_data):
        client.post("/api/auth/register", json=test_user_data)
        second_user_data["email"] = test_user_data["email"]
        response = client.post("/api/auth/register", json=second_user_data)
        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_register_weak_password(self, client, test_user_data):
        test_user_data["password"] = "short"
        response = client.post("/api/auth/register", json=test_user_data)
        assert response.status_code == 422


class TestAuthLogin:
    """1.2 POST /api/auth/login"""

    def test_login_with_username(self, client, test_user_data):
        client.post("/api/auth/register", json=test_user_data)
        response = client.post("/api/auth/login", json={
            "login": test_user_data["username"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == test_user_data["username"]

    def test_login_with_email(self, client, test_user_data):
        client.post("/api/auth/register", json=test_user_data)
        response = client.post("/api/auth/login", json={
            "login": test_user_data["email"],
            "password": test_user_data["password"]
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client, test_user_data):
        client.post("/api/auth/register", json=test_user_data)
        response = client.post("/api/auth/login", json={
            "login": test_user_data["username"],
            "password": "wrongpassword"
        })
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/auth/login", json={
            "login": "nonexistent",
            "password": "password123"
        })
        assert response.status_code == 401


class TestAuthRefresh:
    """1.3 POST /api/auth/refresh"""

    def test_refresh_token_success(self, client, registered_user):
        response = client.post("/api/auth/refresh", json={
            "refresh_token": registered_user["refresh_token"]
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_invalid_token(self, client):
        response = client.post("/api/auth/refresh", json={
            "refresh_token": "invalid_token"
        })
        assert response.status_code == 401


class TestAuthLogout:
    """1.4 POST /api/auth/logout"""

    def test_logout_success(self, client, registered_user, auth_headers):
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": registered_user["refresh_token"]},
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_logout_unauthorized(self, client):
        response = client.post("/api/auth/logout", json={"refresh_token": "token"})
        assert response.status_code == 401


class TestGetCurrentUser:
    """1.6 GET /api/users/me"""

    def test_get_me_success(self, client, registered_user, auth_headers, test_user_data):
        response = client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["first_name"] == test_user_data["first_name"]

    def test_get_me_unauthorized(self, client):
        response = client.get("/api/users/me")
        assert response.status_code == 401


class TestUpdateProfile:
    """1.7 PATCH /api/users/me"""

    def test_update_profile_success(self, client, auth_headers, registered_user):
        response = client.patch("/api/users/me", json={
            "first_name": "Updated",
            "bio": "New bio"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert data["bio"] == "New bio"

    def test_update_birthday(self, client, auth_headers, registered_user):
        response = client.patch("/api/users/me", json={
            "birthday": "1990-05-15"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["birthday"] == "1990-05-15"

    def test_update_future_birthday_rejected(self, client, auth_headers, registered_user):
        response = client.patch("/api/users/me", json={
            "birthday": "2030-01-01"
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_update_privacy(self, client, auth_headers, registered_user):
        response = client.patch("/api/users/me", json={
            "privacy_default": "private"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["privacy_default"] == "private"


class TestGetPublicProfile:
    """1.9 GET /api/users/{user_id}"""

    def test_get_public_profile(self, client, registered_user, second_registered_user, second_auth_headers):
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}", headers=second_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert "username_display" in data
        assert "followers_count" in data
        assert "following_count" in data

    def test_get_public_profile_not_found(self, client, auth_headers):
        response = client.get("/api/users/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_public_profile_unauthenticated(self, client, registered_user):
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["follow_status"] is None


class TestSearchUsers:
    """1.10 GET /api/users"""

    def test_search_users_by_name(self, client, registered_user, second_registered_user, auth_headers):
        response = client.get("/api/users?q=Test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert data["total"] >= 1

    def test_search_users_pagination(self, client, auth_headers, registered_user):
        response = client.get("/api/users?limit=5&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestDeleteAccount:
    """1.17 DELETE /api/users/me"""

    def test_soft_delete_account(self, client, auth_headers, registered_user):
        response = client.delete("/api/users/me", headers=auth_headers)
        assert response.status_code == 204

        # Cannot login after deletion
        login_response = client.post("/api/auth/login", json={
            "login": "test_user",
            "password": "testpassword123"
        })
        assert login_response.status_code == 401

    def test_hard_delete_account(self, client, auth_headers, registered_user):
        response = client.delete("/api/users/me?hard=true", headers=auth_headers)
        assert response.status_code == 204
