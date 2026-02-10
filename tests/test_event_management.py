"""Tests for 06-event-management.md endpoints."""
import pytest


class TestCreateEvent:
    """6.1 POST /api/events"""

    def test_create_event_success(self, client, auth_headers, registered_user):
        response = client.post("/api/events", json={
            "name": "Moscow Open 2024",
            "description": "Annual orienteering competition",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "location": "Moscow Region",
            "sport_kind": "orient",
            "privacy": "public",
            "max_participants": 500
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Moscow Open 2024"
        assert data["description"] == "Annual orienteering competition"
        assert data["start_date"] == "2024-06-15"
        assert data["end_date"] == "2024-06-16"
        assert data["location"] == "Moscow Region"
        assert data["sport_kind"] == "orient"
        assert data["privacy"] == "public"
        assert data["status"] == "planned"
        assert data["max_participants"] == 500
        assert data["organizer_id"] == registered_user["user"]["id"]
        assert data["team_count"] == 1
        assert data["participants_count"] == 0
        assert data["competitions_count"] == 0

    def test_create_event_minimal(self, client, auth_headers, registered_user):
        """Can create event with only required fields."""
        response = client.post("/api/events", json={
            "name": "Simple Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Simple Event"
        assert data["description"] is None
        assert data["location"] is None
        assert data["privacy"] == "public"
        assert data["status"] == "planned"

    def test_create_event_with_draft_status(self, client, auth_headers, registered_user):
        """Can create event with draft status."""
        response = client.post("/api/events", json={
            "name": "Draft Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "draft"

    def test_create_event_invalid_status(self, client, auth_headers, registered_user):
        """Cannot create event with invalid status."""
        response = client.post("/api/events", json={
            "name": "Invalid Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "in_progress"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "draft or planned" in response.json()["detail"].lower()

    def test_create_event_unauthorized(self, client):
        response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        })
        assert response.status_code == 401


class TestGetEvent:
    """6.2 GET /api/events/{event_id}"""

    def test_get_event_success(self, client, auth_headers, registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "description": "Test description",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "location": "Test Location",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Get event
        response = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Event"
        assert data["description"] == "Test description"
        assert data["organizer"]["id"] == registered_user["user"]["id"]
        assert data["my_role"] == "organizer"
        assert data["my_position"] == "chief"

    def test_get_event_unauthenticated(self, client, auth_headers, registered_user):
        """Unauthenticated user can view public event."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Public Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Get event without auth
        response = client.get(f"/api/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Public Event"
        assert data["my_role"] is None
        assert data["my_position"] is None

    def test_get_draft_event_team_member(self, client, auth_headers, registered_user):
        """Team member can view draft event."""
        # Create draft event
        create_response = client.post("/api/events", json={
            "name": "Draft Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Get as organizer
        response = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_get_draft_event_non_team_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Non-team member cannot view draft event."""
        # Create draft event
        create_response = client.post("/api/events", json={
            "name": "Draft Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Get as another user
        response = client.get(f"/api/events/{event_id}", headers=second_auth_headers)
        assert response.status_code == 404

    def test_get_event_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/events/99999", headers=auth_headers)
        assert response.status_code == 404


class TestListEvents:
    """6.3 GET /api/events"""

    def test_list_events_empty(self, client):
        response = client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert data["events"] == []
        assert data["total"] == 0

    def test_list_events_with_data(self, client, auth_headers, registered_user):
        # Create events
        client.post("/api/events", json={
            "name": "Event 1",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        client.post("/api/events", json={
            "name": "Event 2",
            "start_date": "2024-06-17",
            "end_date": "2024-06-18",
            "sport_kind": "run"
        }, headers=auth_headers)

        response = client.get("/api/events")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["total"] == 2

    def test_list_events_search_by_name(self, client, auth_headers, registered_user):
        client.post("/api/events", json={
            "name": "Moscow Open 2024",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        client.post("/api/events", json={
            "name": "St Petersburg Cup",
            "start_date": "2024-06-17",
            "end_date": "2024-06-18",
            "sport_kind": "orient"
        }, headers=auth_headers)

        response = client.get("/api/events?q=Moscow")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "Moscow Open 2024"

    def test_list_events_filter_by_sport(self, client, auth_headers, registered_user):
        client.post("/api/events", json={
            "name": "Orient Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        client.post("/api/events", json={
            "name": "Run Event",
            "start_date": "2024-06-17",
            "end_date": "2024-06-18",
            "sport_kind": "run"
        }, headers=auth_headers)

        response = client.get("/api/events?sport_kind=orient")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 1
        assert data["events"][0]["name"] == "Orient Event"

    def test_list_events_filter_by_status(self, client, auth_headers, registered_user):
        client.post("/api/events", json={
            "name": "Planned Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "planned"
        }, headers=auth_headers)
        client.post("/api/events", json={
            "name": "Draft Event",
            "start_date": "2024-06-17",
            "end_date": "2024-06-18",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)

        # Public query excludes draft
        response = client.get("/api/events")
        assert response.status_code == 200
        assert len(response.json()["events"]) == 1

        # Explicit filter for draft as team member
        response = client.get("/api/events?status=draft", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["events"]) == 1

    def test_list_events_draft_hidden_from_non_team_members(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Draft events are hidden from non-team members."""
        client.post("/api/events", json={
            "name": "Draft Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)

        # Second user cannot see draft
        response = client.get("/api/events", headers=second_auth_headers)
        assert response.status_code == 200
        assert len(response.json()["events"]) == 0

        # Organizer can see draft
        response = client.get("/api/events", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["events"]) == 1

    def test_list_events_pagination(self, client, auth_headers, registered_user):
        # Create 3 events
        for i in range(3):
            client.post("/api/events", json={
                "name": f"Event {i}",
                "start_date": f"2024-06-{15+i}",
                "end_date": f"2024-06-{16+i}",
                "sport_kind": "orient"
            }, headers=auth_headers)

        response = client.get("/api/events?limit=2&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2
        assert data["offset"] == 0


class TestUpdateEvent:
    """6.4 PATCH /api/events/{event_id}"""

    def test_update_event_success(self, client, auth_headers, registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Original Name",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Update event
        response = client.patch(f"/api/events/{event_id}", json={
            "name": "Updated Name",
            "description": "New description"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "New description"

    def test_update_event_status_transition(self, client, auth_headers, registered_user):
        # Create planned event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "planned"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Valid transition: planned -> registration_open
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "registration_open"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "registration_open"

    def test_update_event_invalid_status_transition(self, client, auth_headers, registered_user):
        # Create planned event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "planned"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Invalid transition: planned -> finished
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "finished"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "invalid status transition" in response.json()["detail"].lower()

    def test_update_event_not_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Non-organizer cannot update event."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Second user tries to update
        response = client.patch(f"/api/events/{event_id}", json={
            "name": "Hacked Name"
        }, headers=second_auth_headers)
        assert response.status_code == 403

    def test_update_event_not_found(self, client, auth_headers, registered_user):
        response = client.patch("/api/events/99999", json={
            "name": "Test"
        }, headers=auth_headers)
        assert response.status_code == 404


class TestDeleteEvent:
    """6.5 DELETE /api/events/{event_id}"""

    def test_delete_event_success(self, client, auth_headers, registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Delete event
        response = client.delete(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        response = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_delete_event_not_chief_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Only chief organizer can delete event."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add second user as deputy organizer
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "organizer",
            "position": "deputy"
        }, headers=auth_headers)

        # Deputy cannot delete
        response = client.delete(f"/api/events/{event_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_delete_event_in_progress_rejected(self, client, auth_headers, registered_user):
        """Cannot delete event in progress."""
        # Create event and move to in_progress
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Transition: planned -> registration_open -> in_progress
        client.patch(f"/api/events/{event_id}", json={"status": "registration_open"}, headers=auth_headers)
        client.patch(f"/api/events/{event_id}", json={"status": "in_progress"}, headers=auth_headers)

        # Try to delete
        response = client.delete(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 400
        assert "in progress" in response.json()["detail"].lower()

    def test_delete_event_not_found(self, client, auth_headers, registered_user):
        response = client.delete("/api/events/99999", headers=auth_headers)
        assert response.status_code == 404


class TestListTeamMembers:
    """6.6 GET /api/events/{event_id}/team"""

    def test_get_team_members_success(self, client, auth_headers, registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Get team
        response = client.get(f"/api/events/{event_id}/team", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["team"]) == 1
        assert data["team"][0]["role"] == "organizer"
        assert data["team"][0]["position"] == "chief"
        assert data["team"][0]["user"]["id"] == registered_user["user"]["id"]
        assert data["total"] == 1

    def test_get_team_members_filter_by_role(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add secretary
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)

        # Filter by organizer
        response = client.get(f"/api/events/{event_id}/team?role=organizer", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["team"]) == 1
        assert response.json()["team"][0]["role"] == "organizer"

    def test_get_team_members_invalid_role(self, client, auth_headers, registered_user):
        """Filtering by participant/spectator is rejected."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.get(f"/api/events/{event_id}/team?role=participant", headers=auth_headers)
        assert response.status_code == 400

    def test_get_team_members_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/events/99999/team", headers=auth_headers)
        assert response.status_code == 404


class TestAddTeamMember:
    """6.7 POST /api/events/{event_id}/team"""

    def test_add_team_member_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add team member
        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "judge",
            "position": "chief"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == second_registered_user["user"]["id"]
        assert data["role"] == "judge"
        assert data["position"] == "chief"
        assert data["status"] == "approved"

    def test_add_team_member_already_exists(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot add user who is already a team member."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add team member
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary"
        }, headers=auth_headers)

        # Try to add again
        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "judge"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_add_team_member_chief_exists(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, third_auth_headers, third_registered_user):
        """Cannot add chief if chief already exists for role."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add chief secretary
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)

        # Try to add another chief secretary
        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "chief already exists" in response.json()["detail"].lower()

    def test_add_team_member_invalid_role(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot add participant/spectator via team endpoint."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "participant"
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_add_team_member_not_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, third_auth_headers, third_registered_user):
        """Non-organizer cannot add team members."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add second user as secretary
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary"
        }, headers=auth_headers)

        # Secretary cannot add team members
        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "volunteer"
        }, headers=second_auth_headers)
        assert response.status_code == 403

    def test_add_team_member_user_not_found(self, client, auth_headers, registered_user):
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.post(f"/api/events/{event_id}/team", json={
            "user_id": 99999,
            "role": "volunteer"
        }, headers=auth_headers)
        assert response.status_code == 404


class TestUpdateTeamMember:
    """6.8 PATCH /api/events/{event_id}/team/{user_id}"""

    def test_update_team_member_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create event and add secretary
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary"
        }, headers=auth_headers)

        # Update role to judge
        response = client.patch(f"/api/events/{event_id}/team/{second_registered_user['user']['id']}", json={
            "role": "judge",
            "position": "chief"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "judge"
        assert data["position"] == "chief"

    def test_update_chief_organizer_role_rejected(self, client, auth_headers, registered_user):
        """Cannot change chief organizer's role."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.patch(f"/api/events/{event_id}/team/{registered_user['user']['id']}", json={
            "role": "secretary"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "transfer ownership" in response.json()["detail"].lower()

    def test_update_team_member_not_found(self, client, auth_headers, registered_user):
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.patch(f"/api/events/{event_id}/team/99999", json={
            "role": "volunteer"
        }, headers=auth_headers)
        assert response.status_code == 404


class TestRemoveTeamMember:
    """6.9 DELETE /api/events/{event_id}/team/{user_id}"""

    def test_remove_team_member_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create event and add secretary
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary"
        }, headers=auth_headers)

        # Remove team member
        response = client.delete(f"/api/events/{event_id}/team/{second_registered_user['user']['id']}", headers=auth_headers)
        assert response.status_code == 204

        # Verify removed
        team_response = client.get(f"/api/events/{event_id}/team", headers=auth_headers)
        assert len(team_response.json()["team"]) == 1  # Only organizer left

    def test_remove_self_rejected(self, client, auth_headers, registered_user):
        """Cannot remove yourself from team."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.delete(f"/api/events/{event_id}/team/{registered_user['user']['id']}", headers=auth_headers)
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_remove_chief_organizer_rejected(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot remove chief organizer."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add second user as deputy organizer
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "organizer",
            "position": "deputy"
        }, headers=auth_headers)

        # Deputy cannot remove chief
        response = client.delete(f"/api/events/{event_id}/team/{registered_user['user']['id']}", headers=second_auth_headers)
        # This should fail because deputy doesn't have permission AND chief can't be removed
        assert response.status_code == 400 or response.status_code == 403


class TestTransferOwnership:
    """6.10 POST /api/events/{event_id}/transfer-ownership"""

    def test_transfer_ownership_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create event and add team member
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)

        # Transfer ownership
        response = client.post(f"/api/events/{event_id}/transfer-ownership", json={
            "new_organizer_id": second_registered_user["user"]["id"]
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["organizer_id"] == second_registered_user["user"]["id"]
        assert "transferred" in data["message"].lower()

        # Verify old organizer is now deputy
        event = client.get(f"/api/events/{event_id}", headers=auth_headers)
        assert event.json()["my_role"] == "organizer"
        assert event.json()["my_position"] == "deputy"

        # Verify new organizer is chief
        event = client.get(f"/api/events/{event_id}", headers=second_auth_headers)
        assert event.json()["my_role"] == "organizer"
        assert event.json()["my_position"] == "chief"

    def test_transfer_to_non_team_member_rejected(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot transfer to non-team member."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.post(f"/api/events/{event_id}/transfer-ownership", json={
            "new_organizer_id": second_registered_user["user"]["id"]
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "team member" in response.json()["detail"].lower()

    def test_transfer_to_self_rejected(self, client, auth_headers, registered_user):
        """Cannot transfer to yourself."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        response = client.post(f"/api/events/{event_id}/transfer-ownership", json={
            "new_organizer_id": registered_user["user"]["id"]
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_transfer_not_chief_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, third_auth_headers, third_registered_user):
        """Only chief organizer can transfer."""
        create_response = client.post("/api/events", json={
            "name": "Test Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add deputy organizer and third user
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "organizer",
            "position": "deputy"
        }, headers=auth_headers)
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "secretary"
        }, headers=auth_headers)

        # Deputy cannot transfer
        response = client.post(f"/api/events/{event_id}/transfer-ownership", json={
            "new_organizer_id": third_registered_user["user"]["id"]
        }, headers=second_auth_headers)
        assert response.status_code == 403


class TestEventIntegration:
    """Integration tests for event management."""

    def test_full_event_lifecycle(self, client, auth_headers, registered_user):
        """Full lifecycle: create -> update -> transitions -> delete."""
        # Create
        create_response = client.post("/api/events", json={
            "name": "Full Lifecycle Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient",
            "status": "draft"
        }, headers=auth_headers)
        assert create_response.status_code == 201
        event_id = create_response.json()["id"]
        assert create_response.json()["status"] == "draft"

        # Update: draft -> planned
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "planned"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "planned"

        # planned -> registration_open
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "registration_open"
        }, headers=auth_headers)
        assert response.status_code == 200

        # registration_open -> in_progress
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "in_progress"
        }, headers=auth_headers)
        assert response.status_code == 200

        # Cannot delete in_progress
        response = client.delete(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 400

        # in_progress -> finished
        response = client.patch(f"/api/events/{event_id}", json={
            "status": "finished"
        }, headers=auth_headers)
        assert response.status_code == 200

        # Delete finished event
        response = client.delete(f"/api/events/{event_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_team_management_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, third_auth_headers, third_registered_user):
        """Full team management flow."""
        # Create event
        create_response = client.post("/api/events", json={
            "name": "Team Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = create_response.json()["id"]

        # Add secretary
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": second_registered_user["user"]["id"],
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)

        # Add volunteer
        client.post(f"/api/events/{event_id}/team", json={
            "user_id": third_registered_user["user"]["id"],
            "role": "volunteer"
        }, headers=auth_headers)

        # Verify team
        team_response = client.get(f"/api/events/{event_id}/team", headers=auth_headers)
        assert len(team_response.json()["team"]) == 3

        # Transfer ownership to secretary
        client.post(f"/api/events/{event_id}/transfer-ownership", json={
            "new_organizer_id": second_registered_user["user"]["id"]
        }, headers=auth_headers)

        # New organizer removes old organizer
        response = client.delete(f"/api/events/{event_id}/team/{registered_user['user']['id']}", headers=second_auth_headers)
        assert response.status_code == 204

        # Verify final team
        team_response = client.get(f"/api/events/{event_id}/team", headers=second_auth_headers)
        assert len(team_response.json()["team"]) == 2
