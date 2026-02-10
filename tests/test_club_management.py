"""Tests for 03-club-management.md endpoints."""
import pytest


class TestCreateClub:
    """3.1 POST /api/clubs"""

    def test_create_club_success(self, client, auth_headers, registered_user):
        response = client.post("/api/clubs", json={
            "name": "Test Club",
            "description": "A test club",
            "privacy": "public",
            "location": "Moscow, Russia"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Club"
        assert data["description"] == "A test club"
        assert data["privacy"] == "public"
        assert data["owner_id"] == registered_user["user"]["id"]
        assert data["members_count"] == 1

    def test_create_club_duplicate_name(self, client, auth_headers, registered_user):
        client.post("/api/clubs", json={"name": "Unique Club"}, headers=auth_headers)
        response = client.post("/api/clubs", json={"name": "Unique Club"}, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_club_unauthorized(self, client):
        response = client.post("/api/clubs", json={"name": "Test Club"})
        assert response.status_code == 401

    def test_create_club_by_request_privacy(self, client, auth_headers, registered_user):
        response = client.post("/api/clubs", json={
            "name": "Private Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["privacy"] == "by_request"


class TestGetClub:
    """3.2 GET /api/clubs/{club_id}"""

    def test_get_club_success(self, client, auth_headers, registered_user):
        # Create club first
        create_response = client.post("/api/clubs", json={
            "name": "Test Club",
            "description": "A test club"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == club_id
        assert data["name"] == "Test Club"
        assert data["owner"]["id"] == registered_user["user"]["id"]
        assert data["membership_status"] == "active"
        assert data["membership_role"] == "owner"

    def test_get_club_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/clubs/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_club_unauthenticated(self, client, auth_headers, registered_user):
        # Create public club
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Access without auth
        response = client.get(f"/api/clubs/{club_id}")
        assert response.status_code == 200
        assert response.json()["membership_status"] is None

    def test_get_private_club_non_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create private club
        create_response = client.post("/api/clubs", json={
            "name": "Private Club",
            "privacy": "private"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Try to access as non-member
        response = client.get(f"/api/clubs/{club_id}", headers=second_auth_headers)
        assert response.status_code == 404


class TestListClubs:
    """3.3 GET /api/clubs"""

    def test_list_clubs_empty(self, client):
        response = client.get("/api/clubs")
        assert response.status_code == 200
        data = response.json()
        assert "clubs" in data
        assert data["limit"] == 20
        assert data["offset"] == 0

    def test_list_clubs_with_data(self, client, auth_headers, registered_user):
        # Create some clubs
        client.post("/api/clubs", json={"name": "Club A"}, headers=auth_headers)
        client.post("/api/clubs", json={"name": "Club B"}, headers=auth_headers)

        response = client.get("/api/clubs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["clubs"]) >= 2

    def test_list_clubs_search(self, client, auth_headers, registered_user):
        client.post("/api/clubs", json={"name": "Moscow Runners"}, headers=auth_headers)
        client.post("/api/clubs", json={"name": "Berlin Club"}, headers=auth_headers)

        response = client.get("/api/clubs?q=Moscow", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert any("Moscow" in club["name"] for club in data["clubs"])

    def test_list_clubs_privacy_filter(self, client, auth_headers, registered_user):
        client.post("/api/clubs", json={"name": "Public Club", "privacy": "public"}, headers=auth_headers)
        client.post("/api/clubs", json={"name": "Private Club", "privacy": "by_request"}, headers=auth_headers)

        response = client.get("/api/clubs?privacy=public", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        for club in data["clubs"]:
            assert club["privacy"] == "public"

    def test_private_clubs_hidden_from_non_members(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create private club
        client.post("/api/clubs", json={"name": "Secret Club", "privacy": "private"}, headers=auth_headers)

        # Second user should not see it
        response = client.get("/api/clubs", headers=second_auth_headers)
        data = response.json()
        assert not any(club["name"] == "Secret Club" for club in data["clubs"])


class TestUpdateClub:
    """3.4 PATCH /api/clubs/{club_id}"""

    def test_update_club_success(self, client, auth_headers, registered_user):
        # Create club
        create_response = client.post("/api/clubs", json={"name": "Original Name"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Update
        response = client.patch(f"/api/clubs/{club_id}", json={
            "name": "Updated Name",
            "description": "Updated description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_club_not_admin(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create club
        create_response = client.post("/api/clubs", json={"name": "Test Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Try update as non-member
        response = client.patch(f"/api/clubs/{club_id}", json={"name": "Hacked"}, headers=second_auth_headers)
        assert response.status_code == 403

    def test_update_club_duplicate_name(self, client, auth_headers, registered_user):
        # Create two clubs
        client.post("/api/clubs", json={"name": "Club A"}, headers=auth_headers)
        create_response = client.post("/api/clubs", json={"name": "Club B"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Try to rename B to A
        response = client.patch(f"/api/clubs/{club_id}", json={"name": "Club A"}, headers=auth_headers)
        assert response.status_code == 400


class TestGetClubMembers:
    """3.6 GET /api/clubs/{club_id}/members"""

    def test_get_members_success(self, client, auth_headers, registered_user):
        # Create club
        create_response = client.post("/api/clubs", json={"name": "Test Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.get(f"/api/clubs/{club_id}/members", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["members"]) == 1
        assert data["members"][0]["role"] == "owner"
        assert data["members"][0]["status"] == "active"

    def test_get_members_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/clubs/99999/members", headers=auth_headers)
        assert response.status_code == 404

    def test_get_members_pagination(self, client, auth_headers, registered_user):
        create_response = client.post("/api/clubs", json={"name": "Test Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.get(f"/api/clubs/{club_id}/members?limit=5&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestDeleteClub:
    """3.7 DELETE /api/clubs/{club_id}"""

    def test_delete_club_success(self, client, auth_headers, registered_user):
        # Create club
        create_response = client.post("/api/clubs", json={"name": "To Delete"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/clubs/{club_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_club_not_owner(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create club
        create_response = client.post("/api/clubs", json={"name": "Test Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Try delete as non-owner
        response = client.delete(f"/api/clubs/{club_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_delete_club_not_found(self, client, auth_headers, registered_user):
        response = client.delete("/api/clubs/99999", headers=auth_headers)
        assert response.status_code == 404


class TestClubIntegration:
    """Integration tests for club management."""

    def test_full_club_lifecycle(self, client, auth_headers, registered_user):
        # Create
        create_response = client.post("/api/clubs", json={
            "name": "Lifecycle Club",
            "description": "Testing lifecycle",
            "privacy": "public"
        }, headers=auth_headers)
        assert create_response.status_code == 201
        club_id = create_response.json()["id"]

        # Read
        get_response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Lifecycle Club"

        # Update
        update_response = client.patch(f"/api/clubs/{club_id}", json={
            "description": "Updated lifecycle"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["description"] == "Updated lifecycle"

        # List members
        members_response = client.get(f"/api/clubs/{club_id}/members", headers=auth_headers)
        assert members_response.status_code == 200
        assert members_response.json()["total"] == 1

        # Delete
        delete_response = client.delete(f"/api/clubs/{club_id}", headers=auth_headers)
        assert delete_response.status_code == 204

    def test_club_visibility_by_privacy(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create public club
        public_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        public_id = public_response.json()["id"]

        # Create private club
        private_response = client.post("/api/clubs", json={
            "name": "Private Club",
            "privacy": "private"
        }, headers=auth_headers)
        private_id = private_response.json()["id"]

        # Second user can see public
        response = client.get(f"/api/clubs/{public_id}", headers=second_auth_headers)
        assert response.status_code == 200

        # Second user cannot see private
        response = client.get(f"/api/clubs/{private_id}", headers=second_auth_headers)
        assert response.status_code == 404
