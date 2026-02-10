"""Tests for 09-competition-registration.md endpoints."""
import pytest


@pytest.fixture
def event_with_competition(client, auth_headers, registered_user):
    """Create an event with a competition open for registration."""
    # Create event
    event_response = client.post("/api/events", json={
        "name": "Test Event",
        "start_date": "2024-06-15",
        "end_date": "2024-06-20",
        "sport_kind": "orient",
        "privacy": "public"
    }, headers=auth_headers)
    event_id = event_response.json()["id"]

    # Open registration
    client.patch(f"/api/events/{event_id}", json={
        "status": "registration_open"
    }, headers=auth_headers)

    # Create competition
    comp_response = client.post(f"/api/events/{event_id}/competitions", json={
        "name": "Day 1 - Long",
        "date": "2024-06-15",
        "class_list": ["M21", "M35", "W21", "W35"],
        "start_format": "separated_start"
    }, headers=auth_headers)

    return {
        "event_id": event_id,
        "competition_id": comp_response.json()["id"]
    }


@pytest.fixture
def participant_in_event(client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_competition):
    """Add second user as approved participant in the event."""
    event_id = event_with_competition["event_id"]

    # Second user joins as participant
    client.post(f"/api/events/{event_id}/join", json={
        "role": "participant"
    }, headers=second_auth_headers)

    return event_with_competition


class TestRegisterForCompetition:
    """9.1 POST /api/competitions/{competition_id}/register"""

    def test_register_success(self, client, second_auth_headers, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["class"] == "M21"
        assert data["status"] == "registered"
        assert data["bib_number"] is None
        assert data["start_time"] is None

    def test_register_invalid_class(self, client, second_auth_headers, second_registered_user, participant_in_event):
        """Cannot register with class not in class_list."""
        competition_id = participant_in_event["competition_id"]

        response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M99"
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "invalid class" in response.json()["detail"].lower()

    def test_register_already_registered(self, client, second_auth_headers, second_registered_user, participant_in_event):
        """Cannot register twice."""
        competition_id = participant_in_event["competition_id"]

        # First registration
        client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Second attempt
        response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M35"
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_no_event_participation(self, client, third_auth_headers, third_registered_user, participant_in_event):
        """Cannot register without event participation."""
        competition_id = participant_in_event["competition_id"]

        response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=third_auth_headers)
        assert response.status_code == 403

    def test_register_competition_not_found(self, client, second_auth_headers, second_registered_user):
        response = client.post("/api/competitions/99999/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        assert response.status_code == 404


class TestGetMyRegistration:
    """9.2 GET /api/competitions/{competition_id}/registrations/me"""

    def test_get_my_registration_success(self, client, second_auth_headers, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register first
        client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Get my registration
        response = client.get(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["class"] == "M21"
        assert data["status"] == "registered"

    def test_get_my_registration_not_registered(self, client, second_auth_headers, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)
        assert response.status_code == 404


class TestListRegistrations:
    """9.3 GET /api/competitions/{competition_id}/registrations"""

    def test_list_registrations_empty(self, client, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/registrations")
        assert response.status_code == 200
        assert response.json()["registrations"] == []
        assert response.json()["total"] == 0

    def test_list_registrations_confirmed_only_for_public(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register
        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        # Not confirmed yet - public cannot see
        response = client.get(f"/api/competitions/{competition_id}/registrations")
        assert response.status_code == 200
        assert len(response.json()["registrations"]) == 0

        # Organizer confirms
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "status": "confirmed",
            "bib_number": "101"
        }, headers=auth_headers)

        # Now public can see
        response = client.get(f"/api/competitions/{competition_id}/registrations")
        assert response.status_code == 200
        assert len(response.json()["registrations"]) == 1

    def test_list_registrations_organizer_sees_all(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register (status=registered, not confirmed)
        client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Organizer can see registered status
        response = client.get(f"/api/competitions/{competition_id}/registrations?status=registered", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["registrations"]) == 1

    def test_list_registrations_filter_by_class(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, participant_in_event):
        event_id = participant_in_event["event_id"]
        competition_id = participant_in_event["competition_id"]

        # Third user joins event
        client.post(f"/api/events/{event_id}/join", json={
            "role": "participant"
        }, headers=third_auth_headers)

        # Second user registers M21
        reg1 = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Third user registers W21
        reg2 = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "W21"
        }, headers=third_auth_headers)

        # Confirm both
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg1.json()['id']}", json={
            "status": "confirmed", "bib_number": "101"
        }, headers=auth_headers)
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg2.json()['id']}", json={
            "status": "confirmed", "bib_number": "201"
        }, headers=auth_headers)

        # Filter by class
        response = client.get(f"/api/competitions/{competition_id}/registrations?class=M21")
        assert response.status_code == 200
        assert len(response.json()["registrations"]) == 1
        assert response.json()["registrations"][0]["class"] == "M21"


class TestGetStartList:
    """9.4 GET /api/competitions/{competition_id}/start-list"""

    def test_get_start_list_empty(self, client, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/start-list")
        assert response.status_code == 200
        assert response.json()["start_list"] == []
        assert response.json()["total"] == 0

    def test_get_start_list_with_data(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register and confirm
        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "status": "confirmed",
            "bib_number": "101",
            "start_time": "2024-06-15T10:00:00Z"
        }, headers=auth_headers)

        # Get start list
        response = client.get(f"/api/competitions/{competition_id}/start-list")
        assert response.status_code == 200
        data = response.json()
        assert len(data["start_list"]) == 1
        assert data["start_list"][0]["bib_number"] == "101"
        assert data["competition"]["id"] == competition_id

    def test_get_start_list_filter_by_class(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, participant_in_event):
        event_id = participant_in_event["event_id"]
        competition_id = participant_in_event["competition_id"]

        # Third user joins
        client.post(f"/api/events/{event_id}/join", json={"role": "participant"}, headers=third_auth_headers)

        # Register both
        reg1 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M21"}, headers=second_auth_headers)
        reg2 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "W21"}, headers=third_auth_headers)

        # Confirm both
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg1.json()['id']}", json={
            "status": "confirmed", "bib_number": "101", "start_time": "2024-06-15T10:00:00Z"
        }, headers=auth_headers)
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg2.json()['id']}", json={
            "status": "confirmed", "bib_number": "201", "start_time": "2024-06-15T11:00:00Z"
        }, headers=auth_headers)

        # Filter by class
        response = client.get(f"/api/competitions/{competition_id}/start-list?class=M21")
        assert response.status_code == 200
        assert len(response.json()["start_list"]) == 1


class TestUpdateRegistration:
    """9.5 PATCH /api/competitions/{competition_id}/registrations/{registration_id}"""

    def test_update_registration_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register
        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        # Update
        response = client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "bib_number": "142",
            "start_time": "2024-06-15T10:30:00Z",
            "status": "confirmed"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["bib_number"] == "142"
        assert data["status"] == "confirmed"

    def test_update_registration_duplicate_bib(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, participant_in_event):
        """Cannot assign duplicate bib number."""
        event_id = participant_in_event["event_id"]
        competition_id = participant_in_event["competition_id"]

        # Third user joins
        client.post(f"/api/events/{event_id}/join", json={"role": "participant"}, headers=third_auth_headers)

        # Register both
        reg1 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M21"}, headers=second_auth_headers)
        reg2 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M35"}, headers=third_auth_headers)

        # Assign bib to first
        client.patch(f"/api/competitions/{competition_id}/registrations/{reg1.json()['id']}", json={
            "bib_number": "101"
        }, headers=auth_headers)

        # Try same bib for second
        response = client.patch(f"/api/competitions/{competition_id}/registrations/{reg2.json()['id']}", json={
            "bib_number": "101"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already assigned" in response.json()["detail"].lower()

    def test_update_registration_change_class(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        """Can change registration class."""
        competition_id = participant_in_event["competition_id"]

        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        response = client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "class": "M35"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["class"] == "M35"

    def test_update_registration_not_organizer(self, client, second_auth_headers, third_auth_headers, second_registered_user, third_registered_user, participant_in_event):
        """Non-organizer cannot update registrations."""
        competition_id = participant_in_event["competition_id"]

        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        response = client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "bib_number": "101"
        }, headers=third_auth_headers)
        assert response.status_code == 403


class TestBatchUpdate:
    """9.6 POST /api/competitions/{competition_id}/registrations/batch"""

    def test_batch_update_success(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, participant_in_event):
        event_id = participant_in_event["event_id"]
        competition_id = participant_in_event["competition_id"]

        # Third user joins
        client.post(f"/api/events/{event_id}/join", json={"role": "participant"}, headers=third_auth_headers)

        # Register both
        reg1 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M21"}, headers=second_auth_headers)
        reg2 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M35"}, headers=third_auth_headers)

        # Batch update
        response = client.post(f"/api/competitions/{competition_id}/registrations/batch", json={
            "registrations": [
                {"registration_id": reg1.json()["id"], "bib_number": "101", "start_time": "2024-06-15T10:00:00Z"},
                {"registration_id": reg2.json()["id"], "bib_number": "102", "start_time": "2024-06-15T10:01:00Z"}
            ],
            "set_status": "confirmed"
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["updated"] == 2
        assert len(data["registrations"]) == 2

    def test_batch_update_duplicate_bibs_in_batch(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, participant_in_event):
        """Cannot have duplicate bibs in batch."""
        event_id = participant_in_event["event_id"]
        competition_id = participant_in_event["competition_id"]

        client.post(f"/api/events/{event_id}/join", json={"role": "participant"}, headers=third_auth_headers)

        reg1 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M21"}, headers=second_auth_headers)
        reg2 = client.post(f"/api/competitions/{competition_id}/register", json={"class": "M35"}, headers=third_auth_headers)

        response = client.post(f"/api/competitions/{competition_id}/registrations/batch", json={
            "registrations": [
                {"registration_id": reg1.json()["id"], "bib_number": "101"},
                {"registration_id": reg2.json()["id"], "bib_number": "101"}  # Duplicate
            ]
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "duplicate" in response.json()["detail"].lower()


class TestCancelMyRegistration:
    """9.7 DELETE /api/competitions/{competition_id}/registrations/me"""

    def test_cancel_registration_success(self, client, second_auth_headers, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register
        client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Cancel
        response = client.delete(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)
        assert response.status_code == 204

        # Verify cancelled
        get_response = client.get(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)
        assert get_response.status_code == 404

    def test_cancel_registration_not_registered(self, client, second_auth_headers, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.delete(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)
        assert response.status_code == 404


class TestRemoveRegistration:
    """9.8 DELETE /api/competitions/{competition_id}/registrations/{registration_id}"""

    def test_remove_registration_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        # Register
        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        # Remove
        response = client.delete(f"/api/competitions/{competition_id}/registrations/{reg_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_remove_registration_not_organizer(self, client, second_auth_headers, third_auth_headers, second_registered_user, third_registered_user, participant_in_event):
        """Non-organizer cannot remove registrations."""
        competition_id = participant_in_event["competition_id"]

        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        reg_id = reg_response.json()["id"]

        response = client.delete(f"/api/competitions/{competition_id}/registrations/{reg_id}", headers=third_auth_headers)
        assert response.status_code == 403

    def test_remove_registration_not_found(self, client, auth_headers, registered_user, participant_in_event):
        competition_id = participant_in_event["competition_id"]

        response = client.delete(f"/api/competitions/{competition_id}/registrations/99999", headers=auth_headers)
        assert response.status_code == 404


class TestRegistrationIntegration:
    """Integration tests for competition registration."""

    def test_full_registration_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, participant_in_event):
        """Full flow: register -> confirm -> appear in start list."""
        competition_id = participant_in_event["competition_id"]

        # Register
        reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)
        assert reg_response.status_code == 201
        reg_id = reg_response.json()["id"]
        assert reg_response.json()["status"] == "registered"

        # Not in public list yet
        list_response = client.get(f"/api/competitions/{competition_id}/registrations")
        assert len(list_response.json()["registrations"]) == 0

        # Organizer confirms with bib and start time
        update_response = client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
            "bib_number": "142",
            "start_time": "2024-06-15T10:30:00Z",
            "status": "confirmed"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["status"] == "confirmed"

        # Now in public list
        list_response = client.get(f"/api/competitions/{competition_id}/registrations")
        assert len(list_response.json()["registrations"]) == 1

        # Appears in start list
        start_list = client.get(f"/api/competitions/{competition_id}/start-list")
        assert len(start_list.json()["start_list"]) == 1
        assert start_list.json()["start_list"][0]["bib_number"] == "142"

    def test_reregister_after_cancel(self, client, second_auth_headers, second_registered_user, participant_in_event):
        """Can re-register after cancelling."""
        competition_id = participant_in_event["competition_id"]

        # Register
        client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M21"
        }, headers=second_auth_headers)

        # Cancel
        client.delete(f"/api/competitions/{competition_id}/registrations/me", headers=second_auth_headers)

        # Re-register with different class
        response = client.post(f"/api/competitions/{competition_id}/register", json={
            "class": "M35"
        }, headers=second_auth_headers)
        assert response.status_code == 201
        assert response.json()["class"] == "M35"
