"""Tests for 08-competition-management.md endpoints."""
import pytest


@pytest.fixture
def event_with_team(client, auth_headers, second_auth_headers, registered_user, second_registered_user):
    """Create an event with a team."""
    response = client.post("/api/events", json={
        "name": "Test Event",
        "start_date": "2024-06-15",
        "end_date": "2024-06-20",
        "sport_kind": "orient"
    }, headers=auth_headers)
    event_id = response.json()["id"]

    # Add second user as chief secretary
    client.post(f"/api/events/{event_id}/team", json={
        "user_id": second_registered_user["user"]["id"],
        "role": "secretary",
        "position": "chief"
    }, headers=auth_headers)

    return event_id


class TestCreateCompetition:
    """8.1 POST /api/events/{event_id}/competitions"""

    def test_create_competition_success(self, client, auth_headers, registered_user, event_with_team):
        response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1 - Long Distance",
            "description": "Classic long distance race",
            "date": "2024-06-15",
            "start_format": "separated_start",
            "class_list": ["M21", "M35", "W21"],
            "control_points_list": ["31", "45", "78", "finish"],
            "distance_meters": 12500,
            "location": "Forest Park"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Day 1 - Long Distance"
        assert data["description"] == "Classic long distance race"
        assert data["date"] == "2024-06-15"
        assert data["start_format"] == "separated_start"
        assert data["status"] == "planned"
        assert data["sport_kind"] == "orient"  # Inherited from event

    def test_create_competition_minimal(self, client, auth_headers, registered_user, event_with_team):
        response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Sprint",
            "date": "2024-06-16"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Sprint"
        assert data["class_list"] is None
        assert data["control_points_list"] is None

    def test_create_competition_chief_secretary_can_create(self, client, second_auth_headers, second_registered_user, event_with_team):
        """Chief secretary can create competitions."""
        response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 2",
            "date": "2024-06-17"
        }, headers=second_auth_headers)
        assert response.status_code == 201

    def test_create_competition_non_chief_forbidden(self, client, auth_headers, third_auth_headers, registered_user, third_registered_user, event_with_team):
        """Non-chief team member cannot create competitions."""
        # Add third user as regular volunteer
        client.post(f"/api/events/{event_with_team}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "volunteer"
        }, headers=auth_headers)

        response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 3",
            "date": "2024-06-18"
        }, headers=third_auth_headers)
        assert response.status_code == 403

    def test_create_competition_event_not_found(self, client, auth_headers, registered_user):
        response = client.post("/api/events/99999/competitions", json={
            "name": "Test",
            "date": "2024-06-15"
        }, headers=auth_headers)
        assert response.status_code == 404


class TestListCompetitions:
    """8.2 GET /api/events/{event_id}/competitions"""

    def test_list_competitions_empty(self, client, event_with_team):
        response = client.get(f"/api/events/{event_with_team}/competitions")
        assert response.status_code == 200
        assert response.json()["competitions"] == []
        assert response.json()["total"] == 0

    def test_list_competitions_with_data(self, client, auth_headers, registered_user, event_with_team):
        # Create competitions
        client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 2",
            "date": "2024-06-16"
        }, headers=auth_headers)

        response = client.get(f"/api/events/{event_with_team}/competitions")
        assert response.status_code == 200
        data = response.json()
        assert len(data["competitions"]) == 2
        assert data["total"] == 2

    def test_list_competitions_filter_by_status(self, client, auth_headers, registered_user, event_with_team):
        # Create and update competitions
        resp1 = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = resp1.json()["id"]

        client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 2",
            "date": "2024-06-16"
        }, headers=auth_headers)

        # Start first competition
        client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)

        # Filter by status
        response = client.get(f"/api/events/{event_with_team}/competitions?status=planned")
        assert response.status_code == 200
        assert len(response.json()["competitions"]) == 1
        assert response.json()["competitions"][0]["name"] == "Day 2"


class TestGetCompetition:
    """8.3 GET /api/events/{event_id}/competitions/{competition_id}"""

    def test_get_competition_success(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1 - Long",
            "description": "Long distance",
            "date": "2024-06-15",
            "class_list": ["M21", "W21"]
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Get competition
        response = client.get(f"/api/events/{event_with_team}/competitions/{comp_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Day 1 - Long"
        assert data["event"]["id"] == event_with_team
        assert "team_count" in data

    def test_get_competition_not_found(self, client, event_with_team):
        response = client.get(f"/api/events/{event_with_team}/competitions/99999")
        assert response.status_code == 404

    def test_get_competition_wrong_event(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Create another event
        event2 = client.post("/api/events", json={
            "name": "Other Event",
            "start_date": "2024-07-01",
            "end_date": "2024-07-02",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event2_id = event2.json()["id"]

        # Try to get competition from wrong event
        response = client.get(f"/api/events/{event2_id}/competitions/{comp_id}")
        assert response.status_code == 404


class TestUpdateCompetition:
    """8.4 PATCH /api/events/{event_id}/competitions/{competition_id}"""

    def test_update_competition_success(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Update
        response = client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "name": "Day 1 - Updated",
            "description": "New description"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["name"] == "Day 1 - Updated"
        assert response.json()["description"] == "New description"

    def test_update_competition_status_transition(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Valid transition: planned -> in_progress
        response = client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "in_progress"

    def test_update_competition_invalid_status_transition(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Invalid transition: planned -> finished
        response = client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "finished"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "invalid status transition" in response.json()["detail"].lower()


class TestDeleteCompetition:
    """8.5 DELETE /api/events/{event_id}/competitions/{competition_id}"""

    def test_delete_competition_success(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Delete
        response = client.delete(f"/api/events/{event_with_team}/competitions/{comp_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/events/{event_with_team}/competitions/{comp_id}")
        assert get_response.status_code == 404

    def test_delete_competition_in_progress_rejected(self, client, auth_headers, registered_user, event_with_team):
        # Create and start competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)

        # Try to delete
        response = client.delete(f"/api/events/{event_with_team}/competitions/{comp_id}", headers=auth_headers)
        assert response.status_code == 400
        assert "in progress" in response.json()["detail"].lower()

    def test_delete_competition_chief_secretary_can_delete(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_team):
        """Chief secretary can delete competitions."""
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Secretary deletes
        response = client.delete(f"/api/events/{event_with_team}/competitions/{comp_id}", headers=second_auth_headers)
        assert response.status_code == 204


class TestCompetitionTeam:
    """8.6-8.8 Competition team endpoints"""

    def test_list_competition_team(self, client, auth_headers, registered_user, event_with_team):
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # List team (should inherit from event)
        response = client.get(f"/api/competitions/{comp_id}/team")
        assert response.status_code == 200
        data = response.json()
        # Event has organizer and secretary
        assert data["total"] >= 2

    def test_assign_team_member(self, client, auth_headers, third_auth_headers, registered_user, third_registered_user, event_with_team):
        """Assign a team member to competition."""
        # Add third user to event team
        client.post(f"/api/events/{event_with_team}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "volunteer"
        }, headers=auth_headers)

        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Assign with different role
        response = client.post(f"/api/competitions/{comp_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "judge"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["role"] == "judge"
        assert response.json()["inherited"] is False

    def test_assign_non_event_member_rejected(self, client, auth_headers, third_auth_headers, registered_user, third_registered_user, event_with_team):
        """Cannot assign user who is not an event team member."""
        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Try to assign non-event member
        response = client.post(f"/api/competitions/{comp_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "judge"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "not an event team member" in response.json()["detail"].lower()

    def test_remove_from_competition_team(self, client, auth_headers, third_auth_headers, registered_user, third_registered_user, event_with_team):
        """Remove a team member from competition."""
        # Add third user to event team
        client.post(f"/api/events/{event_with_team}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "volunteer"
        }, headers=auth_headers)

        # Create competition
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Day 1",
            "date": "2024-06-15"
        }, headers=auth_headers)
        comp_id = create_response.json()["id"]

        # Remove from competition team
        response = client.delete(f"/api/competitions/{comp_id}/team/{third_registered_user['user']['id']}", headers=auth_headers)
        assert response.status_code == 204


class TestCompetitionIntegration:
    """Integration tests for competition management."""

    def test_full_competition_lifecycle(self, client, auth_headers, registered_user, event_with_team):
        """Full lifecycle: create -> update -> status transitions -> delete."""
        # Create
        create_response = client.post(f"/api/events/{event_with_team}/competitions", json={
            "name": "Lifecycle Test",
            "date": "2024-06-15",
            "class_list": ["M21", "W21"]
        }, headers=auth_headers)
        assert create_response.status_code == 201
        comp_id = create_response.json()["id"]
        assert create_response.json()["status"] == "planned"

        # Update
        update_response = client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "name": "Lifecycle Test - Updated"
        }, headers=auth_headers)
        assert update_response.status_code == 200

        # Status: planned -> in_progress
        client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)

        # Status: in_progress -> finished
        client.patch(f"/api/events/{event_with_team}/competitions/{comp_id}", json={
            "status": "finished"
        }, headers=auth_headers)

        # Delete finished competition
        delete_response = client.delete(f"/api/events/{event_with_team}/competitions/{comp_id}", headers=auth_headers)
        assert delete_response.status_code == 204

    def test_multiple_competitions_in_event(self, client, auth_headers, registered_user, event_with_team):
        """Create multiple competitions in one event."""
        for i in range(3):
            response = client.post(f"/api/events/{event_with_team}/competitions", json={
                "name": f"Day {i + 1}",
                "date": f"2024-06-{15 + i}"
            }, headers=auth_headers)
            assert response.status_code == 201

        # Verify all created
        list_response = client.get(f"/api/events/{event_with_team}/competitions")
        assert len(list_response.json()["competitions"]) == 3
