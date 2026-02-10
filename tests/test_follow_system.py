"""Tests for 02-follow-system.md endpoints."""
import pytest


class TestFollowUser:
    """2.1 POST /api/users/{user_id}/follow"""

    def test_follow_public_user(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Following a public user should auto-accept."""
        # Make second user public
        client.patch("/api/users/me", json={"privacy_default": "public"}, headers=second_auth_headers)

        target_user_id = second_registered_user["user"]["id"]
        response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "accepted"
        assert data["following_id"] == target_user_id

    def test_follow_private_user(self, client, registered_user, second_registered_user, second_auth_headers, auth_headers):
        """Following a private user should create pending request."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        target_user_id = second_registered_user["user"]["id"]
        response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    def test_follow_self_rejected(self, client, registered_user, auth_headers):
        """Cannot follow yourself."""
        user_id = registered_user["user"]["id"]
        response = client.post(f"/api/users/{user_id}/follow", headers=auth_headers)
        assert response.status_code == 400
        assert "yourself" in response.json()["detail"].lower()

    def test_follow_already_following(self, client, registered_user, second_registered_user, auth_headers):
        """Cannot follow someone twice."""
        target_user_id = second_registered_user["user"]["id"]
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    def test_follow_nonexistent_user(self, client, auth_headers, registered_user):
        """Cannot follow non-existent user."""
        response = client.post("/api/users/99999/follow", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateFollowRequest:
    """2.2 PATCH /api/users/follow-requests/{follow_id}"""

    def test_accept_follow_request(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Target user can accept follow request."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        # First user follows second user
        target_user_id = second_registered_user["user"]["id"]
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        follow_id = follow_response.json()["id"]

        # Second user accepts
        response = client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "accepted"},
            headers=second_auth_headers
        )
        assert response.status_code == 200

    def test_reject_follow_request(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Target user can reject follow request."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        # First user follows second user
        target_user_id = second_registered_user["user"]["id"]
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        follow_id = follow_response.json()["id"]

        # Second user rejects
        response = client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "rejected"},
            headers=second_auth_headers
        )
        assert response.status_code == 200

    def test_only_target_can_update(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Only target user can accept/reject."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        # First user follows second user
        target_user_id = second_registered_user["user"]["id"]
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        follow_id = follow_response.json()["id"]

        # First user (follower) tries to accept - should fail
        response = client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "accepted"},
            headers=auth_headers
        )
        assert response.status_code == 403


class TestUnfollowUser:
    """2.3 DELETE /api/users/{user_id}/follow"""

    def test_unfollow_success(self, client, registered_user, second_registered_user, auth_headers):
        """Can unfollow a user."""
        target_user_id = second_registered_user["user"]["id"]
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        response = client.delete(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 204

    def test_unfollow_not_following(self, client, registered_user, second_registered_user, auth_headers):
        """Cannot unfollow if not following."""
        target_user_id = second_registered_user["user"]["id"]
        response = client.delete(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 404

    def test_can_refollow_after_unfollow(self, client, registered_user, second_registered_user, auth_headers):
        """Can follow again after unfollowing."""
        target_user_id = second_registered_user["user"]["id"]
        # Follow
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        # Unfollow
        client.delete(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        # Follow again
        response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 201


class TestGetFollowers:
    """2.4 GET /api/users/{user_id}/followers"""

    def test_get_followers_empty(self, client, registered_user, auth_headers):
        """Get empty followers list."""
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/followers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["followers"] == []
        assert data["total"] == 0

    def test_get_followers_with_data(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Get followers list with one follower."""
        # Make first user public so follow is auto-accepted
        client.patch("/api/users/me", json={"privacy_default": "public"}, headers=auth_headers)

        target_user_id = registered_user["user"]["id"]
        # Second user follows first user
        client.post(f"/api/users/{target_user_id}/follow", headers=second_auth_headers)

        response = client.get(f"/api/users/{target_user_id}/followers", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["followers"]) == 1
        assert data["followers"][0]["id"] == second_registered_user["user"]["id"]

    def test_get_followers_pagination(self, client, registered_user, auth_headers):
        """Test pagination parameters."""
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/followers?limit=5&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestGetFollowing:
    """2.5 GET /api/users/{user_id}/following"""

    def test_get_following_empty(self, client, registered_user, auth_headers):
        """Get empty following list."""
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/following", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["following"] == []
        assert data["total"] == 0

    def test_get_following_with_data(self, client, registered_user, second_registered_user, auth_headers):
        """Get following list."""
        target_user_id = second_registered_user["user"]["id"]
        # First user follows second user
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)

        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/following", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["following"]) == 1
        assert data["following"][0]["id"] == target_user_id

    def test_self_sees_all_statuses(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Self can see pending/rejected as pending."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        target_user_id = second_registered_user["user"]["id"]
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)

        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/following", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["following"][0]["status"] == "pending"

    def test_others_see_only_accepted(self, client, registered_user, second_registered_user, third_registered_user, auth_headers, second_auth_headers, third_auth_headers):
        """Others only see accepted follows."""
        # Make second user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        target_user_id = second_registered_user["user"]["id"]
        client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)

        # Third user views first user's following list
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/following", headers=third_auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Pending follows should not be visible to others
        assert data["total"] == 0


class TestGetPendingFollowRequests:
    """2.6 GET /api/users/me/follow-requests"""

    def test_get_pending_requests_empty(self, client, registered_user, auth_headers):
        """Get empty pending requests list."""
        response = client.get("/api/users/me/follow-requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["requests"] == []
        assert data["total"] == 0

    def test_get_pending_requests_with_data(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Get pending requests list."""
        # Make first user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=auth_headers)

        # Second user requests to follow first user
        target_user_id = registered_user["user"]["id"]
        client.post(f"/api/users/{target_user_id}/follow", headers=second_auth_headers)

        # First user checks pending requests
        response = client.get("/api/users/me/follow-requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["requests"]) == 1
        assert data["requests"][0]["follower"]["id"] == second_registered_user["user"]["id"]

    def test_rejected_not_in_pending(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Rejected requests not shown in pending list."""
        # Make first user private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=auth_headers)

        # Second user requests to follow first user
        target_user_id = registered_user["user"]["id"]
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=second_auth_headers)
        follow_id = follow_response.json()["id"]

        # First user rejects
        client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "rejected"},
            headers=auth_headers
        )

        # First user checks pending requests - should be empty
        response = client.get("/api/users/me/follow-requests", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0


class TestFollowIntegration:
    """Integration tests for follow system."""

    def test_full_follow_flow_public_user(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Full flow: follow public user -> check followers/following."""
        # Make second user public
        client.patch("/api/users/me", json={"privacy_default": "public"}, headers=second_auth_headers)

        target_user_id = second_registered_user["user"]["id"]
        follower_id = registered_user["user"]["id"]

        # Follow
        response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "accepted"

        # Check target's followers
        response = client.get(f"/api/users/{target_user_id}/followers")
        assert response.status_code == 200
        assert response.json()["total"] == 1

        # Check follower's following
        response = client.get(f"/api/users/{follower_id}/following")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_full_follow_flow_private_user(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Full flow: request follow -> accept -> check lists."""
        target_user_id = second_registered_user["user"]["id"]

        # Make target private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        # Request follow
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        assert follow_response.status_code == 201
        assert follow_response.json()["status"] == "pending"
        follow_id = follow_response.json()["id"]

        # Target checks pending requests
        response = client.get("/api/users/me/follow-requests", headers=second_auth_headers)
        assert response.json()["total"] == 1

        # Target accepts
        response = client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "accepted"},
            headers=second_auth_headers
        )
        assert response.status_code == 200

        # Check target's followers
        response = client.get(f"/api/users/{target_user_id}/followers")
        assert response.status_code == 200
        assert response.json()["total"] == 1

    def test_rejected_masked_as_pending(self, client, registered_user, second_registered_user, auth_headers, second_auth_headers):
        """Rejected status shown as pending to follower."""
        target_user_id = second_registered_user["user"]["id"]

        # Make target private
        client.patch("/api/users/me", json={"privacy_default": "private"}, headers=second_auth_headers)

        # Request follow
        follow_response = client.post(f"/api/users/{target_user_id}/follow", headers=auth_headers)
        follow_id = follow_response.json()["id"]

        # Target rejects
        client.patch(
            f"/api/users/follow-requests/{follow_id}",
            json={"status": "rejected"},
            headers=second_auth_headers
        )

        # Follower sees their following list - rejected masked as pending
        user_id = registered_user["user"]["id"]
        response = client.get(f"/api/users/{user_id}/following", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["following"][0]["status"] == "pending"  # Masked!
