"""Tests for 04-club-membership.md endpoints."""
import pytest


class TestJoinClub:
    """4.1 POST /api/clubs/{club_id}/join"""

    def test_join_public_club(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Joining a public club should instantly make user active member."""
        # First user creates a public club
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["role"] == "member"
        assert data["user_id"] == second_registered_user["user"]["id"]

    def test_join_by_request_club(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Joining a by_request club should create pending membership."""
        # First user creates a by_request club
        create_response = client.post("/api/clubs", json={
            "name": "Request Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    def test_join_private_club_rejected(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot join a private club directly."""
        create_response = client.post("/api/clubs", json={
            "name": "Private Club",
            "privacy": "private"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert response.status_code == 403

    def test_join_already_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot join a club twice."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        # Try to join again
        response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_join_club_not_found(self, client, auth_headers, registered_user):
        response = client.post("/api/clubs/99999/join", headers=auth_headers)
        assert response.status_code == 404


class TestApproveMembership:
    """4.2 PATCH /api/clubs/{club_id}/members/{membership_id}"""

    def test_approve_membership(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can approve pending membership."""
        # Create by_request club
        create_response = client.post("/api/clubs", json={
            "name": "Request Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        join_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        membership_id = join_response.json()["id"]

        # Owner approves
        response = client.patch(
            f"/api/clubs/{club_id}/members/{membership_id}",
            json={"status": "active"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_reject_membership(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can reject pending membership."""
        create_response = client.post("/api/clubs", json={
            "name": "Request Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        join_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        membership_id = join_response.json()["id"]

        response = client.patch(
            f"/api/clubs/{club_id}/members/{membership_id}",
            json={"status": "rejected"},
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_non_admin_cannot_approve(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user):
        """Non-admin cannot approve membership."""
        create_response = client.post("/api/clubs", json={
            "name": "Request Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        join_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        membership_id = join_response.json()["id"]

        # Third user (non-member) tries to approve
        response = client.patch(
            f"/api/clubs/{club_id}/members/{membership_id}",
            json={"status": "active"},
            headers=third_auth_headers
        )
        assert response.status_code == 403


class TestLeaveClub:
    """4.3 DELETE /api/clubs/{club_id}/members/me"""

    def test_leave_club_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Member can leave a club."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)

        # Second user leaves
        response = client.delete(f"/api/clubs/{club_id}/members/me", headers=second_auth_headers)
        assert response.status_code == 204

    def test_owner_cannot_leave(self, client, auth_headers, registered_user):
        """Owner cannot leave club."""
        create_response = client.post("/api/clubs", json={"name": "My Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.delete(f"/api/clubs/{club_id}/members/me", headers=auth_headers)
        assert response.status_code == 400
        assert "owner" in response.json()["detail"].lower()

    def test_leave_not_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot leave a club you're not a member of."""
        create_response = client.post("/api/clubs", json={"name": "My Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]

        response = client.delete(f"/api/clubs/{club_id}/members/me", headers=second_auth_headers)
        assert response.status_code == 404

    def test_can_rejoin_after_leaving(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Can rejoin a club after leaving."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Join
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        # Leave
        client.delete(f"/api/clubs/{club_id}/members/me", headers=second_auth_headers)
        # Rejoin
        response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert response.status_code == 201


class TestRemoveMember:
    """4.4 DELETE /api/clubs/{club_id}/members/{user_id}"""

    def test_owner_removes_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can remove a member."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        # Owner removes second user
        response = client.delete(f"/api/clubs/{club_id}/members/{second_user_id}", headers=auth_headers)
        assert response.status_code == 204

    def test_coach_cannot_remove_coach(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user):
        """Coach cannot remove another coach."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second and third users join
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        client.post(f"/api/clubs/{club_id}/join", headers=third_auth_headers)

        second_user_id = second_registered_user["user"]["id"]
        third_user_id = third_registered_user["user"]["id"]

        # Make both coaches
        client.patch(f"/api/clubs/{club_id}/members/{second_user_id}/role", json={"role": "coach"}, headers=auth_headers)
        client.patch(f"/api/clubs/{club_id}/members/{third_user_id}/role", json={"role": "coach"}, headers=auth_headers)

        # Second coach tries to remove third coach
        response = client.delete(f"/api/clubs/{club_id}/members/{third_user_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_member_cannot_remove_anyone(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user):
        """Regular member cannot remove anyone."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second and third users join
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        client.post(f"/api/clubs/{club_id}/join", headers=third_auth_headers)

        third_user_id = third_registered_user["user"]["id"]

        # Second member tries to remove third member
        response = client.delete(f"/api/clubs/{club_id}/members/{third_user_id}", headers=second_auth_headers)
        assert response.status_code == 403


class TestUpdateMemberRole:
    """4.5 PATCH /api/clubs/{club_id}/members/{user_id}/role"""

    def test_owner_promotes_to_coach(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can promote member to coach."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        response = client.patch(
            f"/api/clubs/{club_id}/members/{second_user_id}/role",
            json={"role": "coach"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["role"] == "coach"

    def test_owner_demotes_coach_to_member(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can demote coach to member."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        # Promote to coach
        client.patch(f"/api/clubs/{club_id}/members/{second_user_id}/role", json={"role": "coach"}, headers=auth_headers)

        # Demote to member
        response = client.patch(
            f"/api/clubs/{club_id}/members/{second_user_id}/role",
            json={"role": "member"},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["role"] == "member"

    def test_cannot_set_owner_role(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot set owner role directly - must use transfer ownership."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        response = client.patch(
            f"/api/clubs/{club_id}/members/{second_user_id}/role",
            json={"role": "owner"},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_coach_cannot_change_roles(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user):
        """Coach cannot change member roles."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        client.post(f"/api/clubs/{club_id}/join", headers=third_auth_headers)

        second_user_id = second_registered_user["user"]["id"]
        third_user_id = third_registered_user["user"]["id"]

        # Make second user a coach
        client.patch(f"/api/clubs/{club_id}/members/{second_user_id}/role", json={"role": "coach"}, headers=auth_headers)

        # Coach tries to promote third user
        response = client.patch(
            f"/api/clubs/{club_id}/members/{third_user_id}/role",
            json={"role": "coach"},
            headers=second_auth_headers
        )
        assert response.status_code == 403


class TestTransferOwnership:
    """4.6 POST /api/clubs/{club_id}/transfer-ownership"""

    def test_transfer_ownership_success(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Owner can transfer ownership to active member."""
        create_response = client.post("/api/clubs", json={
            "name": "My Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second user joins
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        # Transfer ownership
        response = client.post(
            f"/api/clubs/{club_id}/transfer-ownership",
            json={"new_owner_id": second_user_id},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["owner_id"] == second_user_id
        assert "transferred" in data["message"].lower()

    def test_transfer_to_non_member_fails(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Cannot transfer to non-member."""
        create_response = client.post("/api/clubs", json={"name": "My Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]
        second_user_id = second_registered_user["user"]["id"]

        response = client.post(
            f"/api/clubs/{club_id}/transfer-ownership",
            json={"new_owner_id": second_user_id},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_transfer_to_self_fails(self, client, auth_headers, registered_user):
        """Cannot transfer ownership to yourself."""
        create_response = client.post("/api/clubs", json={"name": "My Club"}, headers=auth_headers)
        club_id = create_response.json()["id"]
        user_id = registered_user["user"]["id"]

        response = client.post(
            f"/api/clubs/{club_id}/transfer-ownership",
            json={"new_owner_id": user_id},
            headers=auth_headers
        )
        assert response.status_code == 400

    def test_non_owner_cannot_transfer(self, client, auth_headers, second_auth_headers, third_auth_headers, registered_user, second_registered_user, third_registered_user):
        """Non-owner cannot transfer ownership."""
        create_response = client.post("/api/clubs", json={
            "name": "My Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Second and third users join
        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        client.post(f"/api/clubs/{club_id}/join", headers=third_auth_headers)

        third_user_id = third_registered_user["user"]["id"]

        # Second user tries to transfer
        response = client.post(
            f"/api/clubs/{club_id}/transfer-ownership",
            json={"new_owner_id": third_user_id},
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_old_owner_becomes_coach(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """After transfer, old owner becomes coach."""
        create_response = client.post("/api/clubs", json={
            "name": "My Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        second_user_id = second_registered_user["user"]["id"]

        # Transfer
        client.post(
            f"/api/clubs/{club_id}/transfer-ownership",
            json={"new_owner_id": second_user_id},
            headers=auth_headers
        )

        # Check club details - new owner can see
        response = client.get(f"/api/clubs/{club_id}", headers=second_auth_headers)
        assert response.status_code == 200
        assert response.json()["membership_role"] == "owner"

        # Old owner should be coach now
        response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["membership_role"] == "coach"


class TestMembershipIntegration:
    """Integration tests for club membership."""

    def test_full_membership_lifecycle(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Full lifecycle: join -> leave -> rejoin."""
        create_response = client.post("/api/clubs", json={
            "name": "Public Club",
            "privacy": "public"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Join
        join_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert join_response.status_code == 201
        assert join_response.json()["status"] == "active"

        # Leave
        leave_response = client.delete(f"/api/clubs/{club_id}/members/me", headers=second_auth_headers)
        assert leave_response.status_code == 204

        # Rejoin
        rejoin_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert rejoin_response.status_code == 201

    def test_pending_membership_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Full flow: request -> approve -> become active member."""
        create_response = client.post("/api/clubs", json={
            "name": "Request Club",
            "privacy": "by_request"
        }, headers=auth_headers)
        club_id = create_response.json()["id"]

        # Request to join
        join_response = client.post(f"/api/clubs/{club_id}/join", headers=second_auth_headers)
        assert join_response.json()["status"] == "pending"
        membership_id = join_response.json()["id"]

        # Check members count (should still be 1 - only owner)
        club_response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert club_response.json()["members_count"] == 1

        # Approve
        client.patch(
            f"/api/clubs/{club_id}/members/{membership_id}",
            json={"status": "active"},
            headers=auth_headers
        )

        # Check members count now (should be 2)
        club_response = client.get(f"/api/clubs/{club_id}", headers=auth_headers)
        assert club_response.json()["members_count"] == 2
