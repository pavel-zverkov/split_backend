"""Tests for 05-user-qualification.md endpoints."""
import pytest


class TestAddQualification:
    """5.1 POST /api/users/me/qualifications"""

    def test_add_qualification_success(self, client, auth_headers, registered_user):
        response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS",
            "issued_date": "2023-05-15",
            "document_number": "123456"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["type"] == "athlete"
        assert data["sport_kind"] == "orient"
        assert data["rank"] == "CMS"
        assert data["document_number"] == "123456"
        assert data["confirmed"] is None

    def test_add_qualification_minimal(self, client, auth_headers, registered_user):
        """Can add qualification with only required fields."""
        response = client.post("/api/users/me/qualifications", json={
            "type": "referee",
            "sport_kind": "run",
            "rank": "3rd category"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["issued_date"] is None
        assert data["valid_until"] is None
        assert data["document_number"] is None

    def test_add_qualification_duplicate(self, client, auth_headers, registered_user):
        """Cannot add duplicate qualification (same type + sport_kind + rank)."""
        qual_data = {
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }
        client.post("/api/users/me/qualifications", json=qual_data, headers=auth_headers)
        response = client.post("/api/users/me/qualifications", json=qual_data, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_add_qualification_same_type_different_rank(self, client, auth_headers, registered_user):
        """Can add same type+sport with different rank."""
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "MS"
        }, headers=auth_headers)
        assert response.status_code == 201

    def test_add_qualification_unauthorized(self, client):
        response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        })
        assert response.status_code == 401


class TestGetMyQualifications:
    """5.2 GET /api/users/me/qualifications"""

    def test_get_my_qualifications_empty(self, client, auth_headers, registered_user):
        response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["qualifications"] == []

    def test_get_my_qualifications_with_data(self, client, auth_headers, registered_user):
        # Add some qualifications
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        client.post("/api/users/me/qualifications", json={
            "type": "referee",
            "sport_kind": "orient",
            "rank": "2nd category"
        }, headers=auth_headers)

        response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["qualifications"]) == 2

    def test_get_my_qualifications_includes_document_number(self, client, auth_headers, registered_user):
        """Own qualifications include document_number."""
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS",
            "document_number": "SECRET123"
        }, headers=auth_headers)

        response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["qualifications"][0]["document_number"] == "SECRET123"


class TestGetUserQualifications:
    """5.3 GET /api/users/{user_id}/qualifications"""

    def test_get_public_user_qualifications(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Can view public user's qualifications."""
        # Make first user public and add qualification
        client.patch("/api/users/me", json={"privacy_default": "public"}, headers=auth_headers)
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS",
            "document_number": "SECRET123"
        }, headers=auth_headers)

        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/qualifications", headers=second_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["qualifications"]) == 1
        # Document number should be hidden
        assert "document_number" not in data["qualifications"][0]

    def test_get_private_user_qualifications_denied(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot view private user's qualifications."""
        # First user is private by default
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)

        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/qualifications", headers=second_auth_headers)
        assert response.status_code == 403

    def test_get_followers_only_qualifications_as_follower(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Follower can view followers-only qualifications."""
        # Make first user followers-only
        client.patch("/api/users/me", json={"privacy_default": "followers"}, headers=auth_headers)
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)

        # Second user follows first user (need to make first user public temporarily or use follow endpoint)
        user_id = registered_user["user"]["id"]
        # First, make public to allow following
        client.patch("/api/users/me", json={"privacy_default": "public"}, headers=auth_headers)
        client.post(f"/api/users/{user_id}/follow", headers=second_auth_headers)
        # Now set back to followers
        client.patch("/api/users/me", json={"privacy_default": "followers"}, headers=auth_headers)

        response = client.get(f"/api/users/{user_id}/qualifications", headers=second_auth_headers)
        assert response.status_code == 200

    def test_get_followers_only_qualifications_as_non_follower(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Non-follower cannot view followers-only qualifications."""
        # Make first user followers-only
        client.patch("/api/users/me", json={"privacy_default": "followers"}, headers=auth_headers)
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)

        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/qualifications", headers=second_auth_headers)
        assert response.status_code == 403

    def test_get_user_qualifications_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/users/99999/qualifications", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateQualification:
    """5.4 PATCH /api/users/me/qualifications/{qualification_id}"""

    def test_update_qualification_success(self, client, auth_headers, registered_user):
        # Create qualification
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        qual_id = create_response.json()["id"]

        # Update
        response = client.patch(f"/api/users/me/qualifications/{qual_id}", json={
            "rank": "MS",
            "issued_date": "2024-01-10"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rank"] == "MS"
        assert data["issued_date"] == "2024-01-10"

    def test_update_qualification_not_found(self, client, auth_headers, registered_user):
        response = client.patch("/api/users/me/qualifications/99999", json={
            "rank": "MS"
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_update_qualification_others_denied(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot update another user's qualification."""
        # First user creates qualification
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        qual_id = create_response.json()["id"]

        # Second user tries to update
        response = client.patch(f"/api/users/me/qualifications/{qual_id}", json={
            "rank": "MS"
        }, headers=second_auth_headers)
        assert response.status_code == 404

    def test_update_qualification_duplicate_rank(self, client, auth_headers, registered_user):
        """Cannot update to create duplicate."""
        # Create two qualifications
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "MS"
        }, headers=auth_headers)
        qual_id = create_response.json()["id"]

        # Try to update second to same rank as first
        response = client.patch(f"/api/users/me/qualifications/{qual_id}", json={
            "rank": "CMS"
        }, headers=auth_headers)
        assert response.status_code == 400


class TestDeleteQualification:
    """5.5 DELETE /api/users/me/qualifications/{qualification_id}"""

    def test_delete_qualification_success(self, client, auth_headers, registered_user):
        # Create qualification
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        qual_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/users/me/qualifications/{qual_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        list_response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert len(list_response.json()["qualifications"]) == 0

    def test_delete_qualification_not_found(self, client, auth_headers, registered_user):
        response = client.delete("/api/users/me/qualifications/99999", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_qualification_others_denied(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot delete another user's qualification."""
        # First user creates qualification
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)
        qual_id = create_response.json()["id"]

        # Second user tries to delete
        response = client.delete(f"/api/users/me/qualifications/{qual_id}", headers=second_auth_headers)
        assert response.status_code == 404


class TestQualificationIntegration:
    """Integration tests for qualifications."""

    def test_full_qualification_lifecycle(self, client, auth_headers, registered_user):
        """Full lifecycle: create -> read -> update -> delete."""
        # Create
        create_response = client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS",
            "document_number": "123456"
        }, headers=auth_headers)
        assert create_response.status_code == 201
        qual_id = create_response.json()["id"]

        # Read
        list_response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert len(list_response.json()["qualifications"]) == 1

        # Update
        update_response = client.patch(f"/api/users/me/qualifications/{qual_id}", json={
            "rank": "MS",
            "issued_date": "2024-01-15"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["rank"] == "MS"

        # Delete
        delete_response = client.delete(f"/api/users/me/qualifications/{qual_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify deleted
        list_response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert len(list_response.json()["qualifications"]) == 0

    def test_multiple_qualifications(self, client, auth_headers, registered_user):
        """Can have multiple qualifications of different types."""
        # Athlete qualification
        client.post("/api/users/me/qualifications", json={
            "type": "athlete",
            "sport_kind": "orient",
            "rank": "CMS"
        }, headers=auth_headers)

        # Referee qualification
        client.post("/api/users/me/qualifications", json={
            "type": "referee",
            "sport_kind": "orient",
            "rank": "2nd category"
        }, headers=auth_headers)

        # Coach qualification
        client.post("/api/users/me/qualifications", json={
            "type": "coach",
            "sport_kind": "orient",
            "rank": "1st category"
        }, headers=auth_headers)

        response = client.get("/api/users/me/qualifications", headers=auth_headers)
        assert len(response.json()["qualifications"]) == 3
