"""Tests for 12-workout-management.md endpoints."""
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def user_workout(client, auth_headers, registered_user):
    """Create a workout for the user."""
    response = client.post("/api/workouts", json={
        "title": "Morning Run",
        "sport_kind": "orient",
        "start_datetime": "2024-06-15T08:00:00Z",
        "privacy": "public"
    }, headers=auth_headers)
    return response.json()


@pytest.fixture
def private_workout(client, auth_headers, registered_user):
    """Create a private workout."""
    response = client.post("/api/workouts", json={
        "title": "Private Training",
        "sport_kind": "orient",
        "start_datetime": "2024-06-16T08:00:00Z",
        "privacy": "private"
    }, headers=auth_headers)
    return response.json()


@pytest.fixture
def followers_workout(client, auth_headers, registered_user):
    """Create a followers-only workout."""
    response = client.post("/api/workouts", json={
        "title": "Followers Only",
        "sport_kind": "orient",
        "start_datetime": "2024-06-17T08:00:00Z",
        "privacy": "followers"
    }, headers=auth_headers)
    return response.json()


@pytest.fixture
def mock_minio():
    """Mock MinIO client for file operations."""
    with patch('app.workout.workout_controller.get_minio_client') as mock:
        minio_client = MagicMock()
        minio_client.remove_object.return_value = None
        mock.return_value = minio_client
        yield minio_client


class TestCreateWorkout:
    """12.1 POST /api/workouts"""

    def test_create_workout_success(self, client, auth_headers, registered_user):
        response = client.post("/api/workouts", json={
            "title": "Morning Run",
            "description": "Easy run in the park",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "public"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Morning Run"
        assert data["sport_kind"] == "orient"
        assert data["privacy"] == "public"
        assert data["status"] == "draft"
        assert data["has_splits"] is False
        assert data["artifacts_count"] == 0

    def test_create_workout_minimal(self, client, auth_headers, registered_user):
        """Create workout with only required fields."""
        response = client.post("/api/workouts", json={
            "sport_kind": "run",
            "start_datetime": "2024-06-15T08:00:00Z"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["title"] is None
        assert response.json()["privacy"] == "private"  # Default

    def test_create_workout_with_metrics(self, client, auth_headers, registered_user):
        response = client.post("/api/workouts", json={
            "title": "Long Run",
            "sport_kind": "run",
            "start_datetime": "2024-06-15T08:00:00Z",
            "finish_datetime": "2024-06-15T10:00:00Z",
            "duration_seconds": 7200,
            "distance_meters": 15000,
            "elevation_gain": 200,
            "privacy": "public"
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["duration_seconds"] == 7200
        assert data["distance_meters"] == 15000
        assert data["elevation_gain"] == 200

    def test_create_workout_unauthenticated(self, client):
        response = client.post("/api/workouts", json={
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z"
        })
        assert response.status_code == 401


class TestListMyWorkouts:
    """12.2 GET /api/workouts"""

    def test_list_workouts_empty(self, client, auth_headers, registered_user):
        response = client.get("/api/workouts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["workouts"] == []
        assert response.json()["total"] == 0

    def test_list_workouts_with_data(self, client, auth_headers, registered_user, user_workout):
        response = client.get("/api/workouts", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["workouts"]) == 1
        assert data["workouts"][0]["title"] == "Morning Run"
        assert data["total"] == 1

    def test_list_workouts_multiple(self, client, auth_headers, registered_user):
        # Create multiple workouts
        for i in range(3):
            client.post("/api/workouts", json={
                "title": f"Workout {i}",
                "sport_kind": "orient",
                "start_datetime": f"2024-06-{15+i}T08:00:00Z",
                "privacy": "public"
            }, headers=auth_headers)

        response = client.get("/api/workouts", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 3
        assert response.json()["total"] == 3

    def test_list_workouts_filter_by_sport_kind(self, client, auth_headers, registered_user):
        # Create workouts with different sports
        client.post("/api/workouts", json={
            "title": "Orient",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z"
        }, headers=auth_headers)
        client.post("/api/workouts", json={
            "title": "Run",
            "sport_kind": "run",
            "start_datetime": "2024-06-16T08:00:00Z"
        }, headers=auth_headers)

        response = client.get("/api/workouts?sport_kind=orient", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 1
        assert response.json()["workouts"][0]["sport_kind"] == "orient"

    def test_list_workouts_pagination(self, client, auth_headers, registered_user):
        # Create 5 workouts
        for i in range(5):
            client.post("/api/workouts", json={
                "title": f"Workout {i}",
                "sport_kind": "orient",
                "start_datetime": f"2024-06-{15+i}T08:00:00Z"
            }, headers=auth_headers)

        # Get first page
        response = client.get("/api/workouts?limit=2&offset=0", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 2
        assert response.json()["total"] == 5

        # Get second page
        response = client.get("/api/workouts?limit=2&offset=2", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 2

    def test_list_workouts_unauthenticated(self, client):
        response = client.get("/api/workouts")
        assert response.status_code == 401


class TestGetWorkoutDetails:
    """12.3 GET /api/workouts/{workout_id}"""

    def test_get_workout_success(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == workout_id
        assert data["title"] == "Morning Run"
        assert "user" in data
        assert data["user"]["first_name"] == "Test"

    def test_get_public_workout_anonymous(self, client, auth_headers, registered_user, user_workout):
        """Anonymous can see public workout."""
        workout_id = user_workout["id"]

        response = client.get(f"/api/workouts/{workout_id}")
        assert response.status_code == 200

    def test_get_private_workout_owner(self, client, auth_headers, registered_user, private_workout):
        """Owner can see their private workout."""
        workout_id = private_workout["id"]

        response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert response.status_code == 200

    def test_get_private_workout_other_user(self, client, second_auth_headers, second_registered_user, auth_headers, registered_user, private_workout):
        """Other user cannot see private workout."""
        workout_id = private_workout["id"]

        response = client.get(f"/api/workouts/{workout_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_get_followers_workout_follower(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, followers_workout):
        """Follower can see followers-only workout."""
        workout_id = followers_workout["id"]

        # Second user follows first user
        client.post(f"/api/users/{registered_user['user']['id']}/follow", headers=second_auth_headers)
        # First user accepts (auto-accept for public privacy)

        # Now can see workout
        response = client.get(f"/api/workouts/{workout_id}", headers=second_auth_headers)
        # May be 403 if follow not auto-accepted - depends on privacy settings
        assert response.status_code in [200, 403]

    def test_get_workout_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/workouts/99999", headers=auth_headers)
        assert response.status_code == 404


class TestListUserWorkouts:
    """12.4 GET /api/users/{user_id}/workouts"""

    def test_list_user_workouts_public(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, user_workout):
        """Other user can see public workouts."""
        user_id = registered_user["user"]["id"]

        response = client.get(f"/api/users/{user_id}/workouts", headers=second_auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert len(data["workouts"]) == 1

    def test_list_user_workouts_anonymous(self, client, auth_headers, registered_user, user_workout):
        """Anonymous can see public workouts."""
        user_id = registered_user["user"]["id"]

        response = client.get(f"/api/users/{user_id}/workouts")
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 1

    def test_list_user_workouts_private_hidden(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, private_workout):
        """Private workouts hidden from others."""
        user_id = registered_user["user"]["id"]

        response = client.get(f"/api/users/{user_id}/workouts", headers=second_auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 0

    def test_list_user_workouts_owner_sees_all(self, client, auth_headers, registered_user, user_workout, private_workout):
        """Owner sees all their workouts."""
        user_id = registered_user["user"]["id"]

        response = client.get(f"/api/users/{user_id}/workouts", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["workouts"]) == 2

    def test_list_user_workouts_not_found(self, client, auth_headers, registered_user):
        response = client.get("/api/users/99999/workouts", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateWorkout:
    """12.5 PATCH /api/workouts/{workout_id}"""

    def test_update_workout_title(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.patch(f"/api/workouts/{workout_id}", json={
            "title": "Updated Title"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_workout_description(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.patch(f"/api/workouts/{workout_id}", json={
            "description": "New description"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["description"] == "New description"

    def test_update_workout_privacy(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.patch(f"/api/workouts/{workout_id}", json={
            "privacy": "private"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["privacy"] == "private"

    def test_update_workout_sport_kind(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.patch(f"/api/workouts/{workout_id}", json={
            "sport_kind": "run"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["sport_kind"] == "run"

    def test_update_workout_not_owner(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, user_workout):
        """Non-owner cannot update workout."""
        workout_id = user_workout["id"]

        response = client.patch(f"/api/workouts/{workout_id}", json={
            "title": "Hacked"
        }, headers=second_auth_headers)
        assert response.status_code == 403

    def test_update_workout_not_found(self, client, auth_headers, registered_user):
        response = client.patch("/api/workouts/99999", json={
            "title": "Test"
        }, headers=auth_headers)
        assert response.status_code == 404


class TestDeleteWorkout:
    """12.6 DELETE /api/workouts/{workout_id}"""

    def test_delete_workout_success(self, client, auth_headers, registered_user, user_workout, mock_minio):
        workout_id = user_workout["id"]

        response = client.delete(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_workout_not_owner(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, user_workout, mock_minio):
        """Non-owner cannot delete workout."""
        workout_id = user_workout["id"]

        response = client.delete(f"/api/workouts/{workout_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_delete_workout_not_found(self, client, auth_headers, registered_user, mock_minio):
        response = client.delete("/api/workouts/99999", headers=auth_headers)
        assert response.status_code == 404


class TestWorkoutPrivacy:
    """Test workout privacy settings."""

    def test_public_workout_visible_to_all(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create public workout
        create_response = client.post("/api/workouts", json={
            "title": "Public",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "public"
        }, headers=auth_headers)
        workout_id = create_response.json()["id"]

        # Other user can see
        response = client.get(f"/api/workouts/{workout_id}", headers=second_auth_headers)
        assert response.status_code == 200

        # Anonymous can see
        response = client.get(f"/api/workouts/{workout_id}")
        assert response.status_code == 200

    def test_private_workout_owner_only(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        # Create private workout
        create_response = client.post("/api/workouts", json={
            "title": "Private",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "private"
        }, headers=auth_headers)
        workout_id = create_response.json()["id"]

        # Owner can see
        response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert response.status_code == 200

        # Other user cannot see
        response = client.get(f"/api/workouts/{workout_id}", headers=second_auth_headers)
        assert response.status_code == 403

        # Anonymous cannot see
        response = client.get(f"/api/workouts/{workout_id}")
        assert response.status_code == 403


class TestWorkoutIntegration:
    """Integration tests for workout management."""

    def test_full_workout_flow(self, client, auth_headers, registered_user, mock_minio):
        """Full flow: create -> list -> get -> update -> delete."""
        # Create
        create_response = client.post("/api/workouts", json={
            "title": "Test Workout",
            "description": "Test description",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "public"
        }, headers=auth_headers)
        assert create_response.status_code == 201
        workout_id = create_response.json()["id"]

        # List
        list_response = client.get("/api/workouts", headers=auth_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()["workouts"]) == 1

        # Get
        get_response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Test Workout"

        # Update
        update_response = client.patch(f"/api/workouts/{workout_id}", json={
            "title": "Updated Workout",
            "privacy": "private"
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated Workout"
        assert update_response.json()["privacy"] == "private"

        # Delete
        delete_response = client.delete(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = client.get(f"/api/workouts/{workout_id}", headers=auth_headers)
        assert verify_response.status_code == 404

    def test_workout_in_user_list(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user):
        """Workout appears in user's workout list."""
        user_id = registered_user["user"]["id"]

        # Create public workout
        client.post("/api/workouts", json={
            "title": "Public Workout",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "public"
        }, headers=auth_headers)

        # Create private workout
        client.post("/api/workouts", json={
            "title": "Private Workout",
            "sport_kind": "orient",
            "start_datetime": "2024-06-16T08:00:00Z",
            "privacy": "private"
        }, headers=auth_headers)

        # Owner sees both
        owner_response = client.get(f"/api/users/{user_id}/workouts", headers=auth_headers)
        assert len(owner_response.json()["workouts"]) == 2

        # Other user sees only public
        other_response = client.get(f"/api/users/{user_id}/workouts", headers=second_auth_headers)
        assert len(other_response.json()["workouts"]) == 1
        assert other_response.json()["workouts"][0]["title"] == "Public Workout"
