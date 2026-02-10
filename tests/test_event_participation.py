"""Tests for 07-event-participation.md endpoints."""
import pytest


@pytest.fixture
def event_with_registration(client, auth_headers, registered_user):
    """Create an event with registration open."""
    response = client.post("/api/events", json={
        "name": "Test Event",
        "start_date": "2024-06-15",
        "end_date": "2024-06-16",
        "sport_kind": "orient",
        "privacy": "public"
    }, headers=auth_headers)
    event_id = response.json()["id"]

    # Open registration
    client.patch(f"/api/events/{event_id}", json={
        "status": "registration_open"
    }, headers=auth_headers)

    return event_id


@pytest.fixture
def by_request_event(client, auth_headers, registered_user):
    """Create an event with by_request privacy."""
    response = client.post("/api/events", json={
        "name": "Private Event",
        "start_date": "2024-06-15",
        "end_date": "2024-06-16",
        "sport_kind": "orient",
        "privacy": "by_request"
    }, headers=auth_headers)
    event_id = response.json()["id"]

    # Open registration
    client.patch(f"/api/events/{event_id}", json={
        "status": "registration_open"
    }, headers=auth_headers)

    return event_id


class TestJoinEvent:
    """7.1 POST /api/events/{event_id}/join"""

    def test_join_public_event_as_participant(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Participant auto-approved in public event."""
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "participant"
        assert data["status"] == "approved"

    def test_join_by_request_event_as_participant(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        """Participant pending in by_request event."""
        response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "participant"
        assert data["status"] == "pending"

    def test_join_already_participating(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Cannot join if already participating."""
        # First join
        client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        # Try to join again
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_join_team_role_recruitment_closed(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Cannot join as team role when recruitment is closed."""
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "judge"
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "recruitment" in response.json()["detail"].lower()

    def test_join_team_role_recruitment_open(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Can join as team role when recruitment is open."""
        # Open recruitment
        client.patch(f"/api/events/{event_with_registration}/recruitment", json={
            "recruitment_open": True,
            "needed_roles": ["judge", "volunteer"]
        }, headers=auth_headers)

        # Join as judge
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "judge"
        }, headers=second_auth_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "pending"

    def test_join_with_invite_token(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Join with invite token auto-approved."""
        # Create invite
        invite_response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "judge",
            "position": "deputy"
        }, headers=auth_headers)
        token = invite_response.json()["token"]

        # Join with token
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "token": token
        }, headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "judge"
        assert data["position"] == "deputy"
        assert data["status"] == "approved"

    def test_join_invalid_invite_token(self, client, second_auth_headers, second_registered_user, event_with_registration):
        """Invalid invite token rejected."""
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "token": "invalid_token"
        }, headers=second_auth_headers)
        assert response.status_code == 400

    def test_join_event_not_open_for_registration(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot join event not open for registration."""
        # Create planned event (not open)
        response = client.post("/api/events", json={
            "name": "Planned Event",
            "start_date": "2024-06-15",
            "end_date": "2024-06-16",
            "sport_kind": "orient"
        }, headers=auth_headers)
        event_id = response.json()["id"]

        response = client.post(f"/api/events/{event_id}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "not open" in response.json()["detail"].lower()

    def test_can_rejoin_after_rejection(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        """Rejected user can re-apply."""
        # Join (pending)
        join_response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        participation_id = join_response.json()["id"]

        # Reject
        client.patch(f"/api/events/{by_request_event}/requests/{participation_id}", json={
            "status": "rejected"
        }, headers=auth_headers)

        # Re-apply
        response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert response.status_code == 201


class TestListParticipants:
    """7.2 GET /api/events/{event_id}/participants"""

    def test_list_participants_empty(self, client, event_with_registration):
        response = client.get(f"/api/events/{event_with_registration}/participants")
        assert response.status_code == 200
        assert response.json()["participants"] == []
        assert response.json()["total"] == 0

    def test_list_participants_with_data(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        # Join as participant
        client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        response = client.get(f"/api/events/{event_with_registration}/participants")
        assert response.status_code == 200
        data = response.json()
        assert len(data["participants"]) == 1
        assert data["participants"][0]["status"] == "approved"

    def test_list_participants_pending_hidden_from_public(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        # Join (pending)
        client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        # Public cannot see pending
        response = client.get(f"/api/events/{by_request_event}/participants")
        assert response.status_code == 200
        assert len(response.json()["participants"]) == 0

    def test_list_participants_pending_visible_to_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        # Join (pending)
        client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        # Organizer can see pending
        response = client.get(f"/api/events/{by_request_event}/participants?status=pending", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["participants"]) == 1


class TestListRequests:
    """7.3 GET /api/events/{event_id}/requests"""

    def test_list_requests_empty(self, client, auth_headers, registered_user, by_request_event):
        response = client.get(f"/api/events/{by_request_event}/requests", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["requests"] == []

    def test_list_requests_with_data(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        # Join (pending)
        client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        response = client.get(f"/api/events/{by_request_event}/requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["requests"]) == 1

    def test_list_requests_forbidden_for_non_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        response = client.get(f"/api/events/{by_request_event}/requests", headers=second_auth_headers)
        assert response.status_code == 403


class TestApproveRejectRequest:
    """7.4 PATCH /api/events/{event_id}/requests/{participation_id}"""

    def test_approve_request(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        # Join (pending)
        join_response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        participation_id = join_response.json()["id"]

        # Approve
        response = client.patch(f"/api/events/{by_request_event}/requests/{participation_id}", json={
            "status": "approved"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        assert response.json()["joined_at"] is not None

    def test_reject_request(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        # Join (pending)
        join_response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        participation_id = join_response.json()["id"]

        # Reject
        response = client.patch(f"/api/events/{by_request_event}/requests/{participation_id}", json={
            "status": "rejected"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_update_request_not_organizer(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, by_request_event):
        # Second user joins (pending)
        join_response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        participation_id = join_response.json()["id"]

        # Third user cannot approve
        response = client.patch(f"/api/events/{by_request_event}/requests/{participation_id}", json={
            "status": "approved"
        }, headers=third_auth_headers)
        assert response.status_code == 403


class TestGetMyParticipation:
    """7.5 GET /api/events/{event_id}/participation/me"""

    def test_get_my_participation_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        # Join
        client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        response = client.get(f"/api/events/{event_with_registration}/participation/me", headers=second_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "participant"
        assert data["status"] == "approved"

    def test_get_my_participation_not_participating(self, client, second_auth_headers, second_registered_user, event_with_registration):
        response = client.get(f"/api/events/{event_with_registration}/participation/me", headers=second_auth_headers)
        assert response.status_code == 404


class TestLeaveEvent:
    """7.6 DELETE /api/events/{event_id}/participation/me"""

    def test_leave_event_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        # Join
        client.post(f"/api/events/{event_with_registration}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)

        # Leave
        response = client.delete(f"/api/events/{event_with_registration}/participation/me", headers=second_auth_headers)
        assert response.status_code == 204

        # Verify left
        response = client.get(f"/api/events/{event_with_registration}/participation/me", headers=second_auth_headers)
        assert response.status_code == 404

    def test_leave_not_participating(self, client, second_auth_headers, second_registered_user, event_with_registration):
        response = client.delete(f"/api/events/{event_with_registration}/participation/me", headers=second_auth_headers)
        assert response.status_code == 404

    def test_chief_organizer_cannot_leave(self, client, auth_headers, registered_user, event_with_registration):
        """Chief organizer cannot leave without transferring ownership."""
        response = client.delete(f"/api/events/{event_with_registration}/participation/me", headers=auth_headers)
        assert response.status_code == 400
        assert "transfer" in response.json()["detail"].lower()


class TestRecruitmentSettings:
    """7.7 PATCH /api/events/{event_id}/recruitment"""

    def test_update_recruitment_success(self, client, auth_headers, registered_user, event_with_registration):
        response = client.patch(f"/api/events/{event_with_registration}/recruitment", json={
            "recruitment_open": True,
            "needed_roles": ["judge", "volunteer"]
        }, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["recruitment_open"] is True
        assert "judge" in data["needed_roles"]
        assert "volunteer" in data["needed_roles"]

    def test_update_recruitment_not_organizer(self, client, second_auth_headers, second_registered_user, event_with_registration):
        response = client.patch(f"/api/events/{event_with_registration}/recruitment", json={
            "recruitment_open": True
        }, headers=second_auth_headers)
        assert response.status_code == 403


class TestInvites:
    """7.8-7.10 Invite endpoints"""

    def test_create_invite_success(self, client, auth_headers, registered_user, event_with_registration):
        response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "judge",
            "position": "deputy",
            "max_uses": 5
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "judge"
        assert data["position"] == "deputy"
        assert data["max_uses"] == 5
        assert data["uses_count"] == 0
        assert data["token"] is not None
        assert data["link"] is not None

    def test_create_invite_not_organizer(self, client, second_auth_headers, second_registered_user, event_with_registration):
        response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "judge"
        }, headers=second_auth_headers)
        assert response.status_code == 403

    def test_list_invites_success(self, client, auth_headers, registered_user, event_with_registration):
        # Create invite
        client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "judge"
        }, headers=auth_headers)

        response = client.get(f"/api/events/{event_with_registration}/invites", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["invites"]) == 1

    def test_revoke_invite_success(self, client, auth_headers, registered_user, event_with_registration):
        # Create invite
        create_response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "judge"
        }, headers=auth_headers)
        invite_id = create_response.json()["id"]

        # Revoke
        response = client.delete(f"/api/events/{event_with_registration}/invites/{invite_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify revoked
        list_response = client.get(f"/api/events/{event_with_registration}/invites", headers=auth_headers)
        assert len(list_response.json()["invites"]) == 0

    def test_invite_max_uses(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user, event_with_registration):
        """Invite with max_uses=1 can only be used once."""
        # Create invite with max_uses=1
        invite_response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "volunteer",
            "max_uses": 1
        }, headers=auth_headers)
        token = invite_response.json()["token"]

        # First user joins
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "token": token
        }, headers=second_auth_headers)
        assert response.status_code == 201

        # Second user cannot use same token
        response = client.post(f"/api/events/{event_with_registration}/join", json={
            "token": token
        }, headers=third_auth_headers)
        assert response.status_code == 400
        assert "maximum uses" in response.json()["detail"].lower()


class TestEventParticipationIntegration:
    """Integration tests for event participation."""

    def test_full_participation_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, by_request_event):
        """Full flow: request -> approve -> participate -> leave."""
        # Request to join
        join_response = client.post(f"/api/events/{by_request_event}/join", json={
            "role": "participant"
        }, headers=second_auth_headers)
        assert join_response.status_code == 201
        participation_id = join_response.json()["id"]
        assert join_response.json()["status"] == "pending"

        # Check in requests list
        requests = client.get(f"/api/events/{by_request_event}/requests", headers=auth_headers)
        assert len(requests.json()["requests"]) == 1

        # Approve
        client.patch(f"/api/events/{by_request_event}/requests/{participation_id}", json={
            "status": "approved"
        }, headers=auth_headers)

        # Check in participants list
        participants = client.get(f"/api/events/{by_request_event}/participants")
        assert len(participants.json()["participants"]) == 1

        # Get my participation
        my_participation = client.get(f"/api/events/{by_request_event}/participation/me", headers=second_auth_headers)
        assert my_participation.json()["status"] == "approved"

        # Leave
        leave_response = client.delete(f"/api/events/{by_request_event}/participation/me", headers=second_auth_headers)
        assert leave_response.status_code == 204

        # Verify left
        participants = client.get(f"/api/events/{by_request_event}/participants")
        assert len(participants.json()["participants"]) == 0

    def test_invite_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_registration):
        """Full invite flow: create -> use -> join."""
        # Create invite
        invite_response = client.post(f"/api/events/{event_with_registration}/invites", json={
            "role": "secretary",
            "position": "chief"
        }, headers=auth_headers)
        token = invite_response.json()["token"]

        # Use invite
        join_response = client.post(f"/api/events/{event_with_registration}/join", json={
            "token": token
        }, headers=second_auth_headers)
        assert join_response.status_code == 201
        assert join_response.json()["role"] == "secretary"
        assert join_response.json()["position"] == "chief"
        assert join_response.json()["status"] == "approved"

        # Check uses_count incremented
        invites = client.get(f"/api/events/{event_with_registration}/invites", headers=auth_headers)
        # Invite should be used up (max_uses=1 by default)
        assert len(invites.json()["invites"]) == 0
