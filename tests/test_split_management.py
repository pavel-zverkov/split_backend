"""
Tests for Section 13: Split Management (WorkoutSplit)

Endpoints:
- GET /api/workouts/{workout_id}/splits - List workout splits
- POST /api/workouts/{workout_id}/splits - Manual split entry
- PATCH /api/workouts/{workout_id}/splits/{split_id} - Update single split
- DELETE /api/workouts/{workout_id}/splits - Delete all splits
"""

import pytest


# ===== Fixtures =====

@pytest.fixture
def workout(client, auth_headers, registered_user):
    """Create a workout for testing."""
    response = client.post("/api/workouts", json={
        "title": "Split Test Workout",
        "sport_kind": "orient",
        "start_datetime": "2024-06-15T10:00:00Z",
        "privacy": "public"
    }, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def private_workout(client, auth_headers, registered_user):
    """Create a private workout for testing."""
    response = client.post("/api/workouts", json={
        "title": "Private Split Test",
        "sport_kind": "orient",
        "start_datetime": "2024-06-15T10:00:00Z",
        "privacy": "private"
    }, headers=auth_headers)
    assert response.status_code == 201
    return response.json()


# ===== 13.1 List Workout Splits =====

class TestListWorkoutSplits:
    """Tests for GET /api/workouts/{workout_id}/splits"""

    def test_list_splits_empty(self, client, auth_headers, workout):
        """List splits for workout with no splits."""
        response = client.get(
            f"/api/workouts/{workout['id']}/splits",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["workout_id"] == workout["id"]
        assert data["splits"] == []
        assert data["total"] == 0

    def test_list_splits_public_anonymous(self, client, workout):
        """Anonymous user can view splits on public workout."""
        response = client.get(f"/api/workouts/{workout['id']}/splits")
        assert response.status_code == 200
        data = response.json()
        assert data["workout_id"] == workout["id"]

    def test_list_splits_private_owner(self, client, auth_headers, private_workout):
        """Owner can view splits on private workout."""
        response = client.get(
            f"/api/workouts/{private_workout['id']}/splits",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_list_splits_private_other_user(self, client, second_auth_headers, private_workout):
        """Other user cannot view splits on private workout."""
        response = client.get(
            f"/api/workouts/{private_workout['id']}/splits",
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_list_splits_workout_not_found(self, client, auth_headers):
        """List splits for non-existent workout."""
        response = client.get(
            "/api/workouts/99999/splits",
            headers=auth_headers
        )
        assert response.status_code == 404


# ===== 13.2 Manual Split Entry =====

class TestManualSplitEntry:
    """Tests for POST /api/workouts/{workout_id}/splits"""

    def test_create_splits_success(self, client, auth_headers, workout):
        """Successfully create splits."""
        splits_data = {
            "splits": [
                {
                    "sequence": 1,
                    "control_point": "31",
                    "distance_meters": 1200,
                    "cumulative_time": 150,
                    "split_time": 150
                },
                {
                    "sequence": 2,
                    "control_point": "45",
                    "distance_meters": 2400,
                    "cumulative_time": 312,
                    "split_time": 162
                }
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["workout_id"] == workout["id"]
        assert data["total"] == 2
        assert len(data["splits"]) == 2
        assert data["splits"][0]["sequence"] == 1
        assert data["splits"][0]["control_point"] == "31"
        assert data["splits"][1]["sequence"] == 2

    def test_create_splits_replaces_existing(self, client, auth_headers, workout):
        """Creating splits replaces existing splits."""
        # Create initial splits
        initial_splits = {
            "splits": [
                {"sequence": 1, "control_point": "A", "cumulative_time": 100, "split_time": 100}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=initial_splits,
            headers=auth_headers
        )
        assert response.status_code == 201

        # Create new splits (should replace)
        new_splits = {
            "splits": [
                {"sequence": 1, "control_point": "B", "cumulative_time": 200, "split_time": 200},
                {"sequence": 2, "control_point": "C", "cumulative_time": 400, "split_time": 200}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=new_splits,
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 2
        assert data["splits"][0]["control_point"] == "B"

    def test_create_splits_not_owner(self, client, second_auth_headers, workout):
        """Non-owner cannot create splits."""
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_create_splits_unauthenticated(self, client, workout):
        """Unauthenticated user cannot create splits."""
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data
        )
        assert response.status_code == 401

    def test_create_splits_empty_list(self, client, auth_headers, workout):
        """Create empty splits list (clears existing)."""
        # First create some splits
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )

        # Now submit empty list
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json={"splits": []},
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total"] == 0
        assert data["splits"] == []

    def test_create_splits_workout_not_found(self, client, auth_headers, registered_user):
        """Create splits for non-existent workout."""
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        response = client.post(
            "/api/workouts/99999/splits",
            json=splits_data,
            headers=auth_headers
        )
        assert response.status_code == 404


# ===== 13.3 Update Single Split =====

class TestUpdateSingleSplit:
    """Tests for PATCH /api/workouts/{workout_id}/splits/{split_id}"""

    @pytest.fixture
    def workout_with_splits(self, client, auth_headers, workout):
        """Create workout with splits for testing updates."""
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "distance_meters": 1200, "cumulative_time": 150, "split_time": 150},
                {"sequence": 2, "control_point": "45", "distance_meters": 2400, "cumulative_time": 312, "split_time": 162}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        return {
            "workout": workout,
            "splits": response.json()["splits"]
        }

    def test_update_split_control_point(self, client, auth_headers, workout_with_splits):
        """Update split control point."""
        split_id = workout_with_splits["splits"][0]["id"]
        workout_id = workout_with_splits["workout"]["id"]

        response = client.patch(
            f"/api/workouts/{workout_id}/splits/{split_id}",
            json={"control_point": "32"},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["control_point"] == "32"
        assert data["id"] == split_id

    def test_update_split_time_values(self, client, auth_headers, workout_with_splits):
        """Update split time values."""
        split_id = workout_with_splits["splits"][0]["id"]
        workout_id = workout_with_splits["workout"]["id"]

        response = client.patch(
            f"/api/workouts/{workout_id}/splits/{split_id}",
            json={"cumulative_time": 160, "split_time": 160},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["cumulative_time"] == 160
        assert data["split_time"] == 160

    def test_update_split_distance(self, client, auth_headers, workout_with_splits):
        """Update split distance."""
        split_id = workout_with_splits["splits"][0]["id"]
        workout_id = workout_with_splits["workout"]["id"]

        response = client.patch(
            f"/api/workouts/{workout_id}/splits/{split_id}",
            json={"distance_meters": 1300},
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["distance_meters"] == 1300

    def test_update_split_not_owner(self, client, second_auth_headers, workout_with_splits):
        """Non-owner cannot update split."""
        split_id = workout_with_splits["splits"][0]["id"]
        workout_id = workout_with_splits["workout"]["id"]

        response = client.patch(
            f"/api/workouts/{workout_id}/splits/{split_id}",
            json={"control_point": "99"},
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_update_split_not_found(self, client, auth_headers, workout):
        """Update non-existent split."""
        response = client.patch(
            f"/api/workouts/{workout['id']}/splits/99999",
            json={"control_point": "99"},
            headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_split_wrong_workout(self, client, auth_headers, workout_with_splits, registered_user):
        """Update split with wrong workout_id."""
        split_id = workout_with_splits["splits"][0]["id"]

        # Create another workout
        response = client.post("/api/workouts", json={
            "sport_kind": "orient",
            "start_datetime": "2024-06-16T10:00:00Z"
        }, headers=auth_headers)
        other_workout_id = response.json()["id"]

        # Try to update split using wrong workout_id
        response = client.patch(
            f"/api/workouts/{other_workout_id}/splits/{split_id}",
            json={"control_point": "99"},
            headers=auth_headers
        )
        assert response.status_code == 404


# ===== 13.4 Delete All Splits =====

class TestDeleteAllSplits:
    """Tests for DELETE /api/workouts/{workout_id}/splits"""

    def test_delete_splits_success(self, client, auth_headers, workout):
        """Successfully delete all splits."""
        # First create splits
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150},
                {"sequence": 2, "control_point": "45", "cumulative_time": 312, "split_time": 162}
            ]
        }
        client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )

        # Delete all splits
        response = client.delete(
            f"/api/workouts/{workout['id']}/splits",
            headers=auth_headers
        )
        assert response.status_code == 204

        # Verify splits are deleted
        response = client.get(
            f"/api/workouts/{workout['id']}/splits",
            headers=auth_headers
        )
        assert response.json()["total"] == 0

    def test_delete_splits_already_empty(self, client, auth_headers, workout):
        """Delete splits when none exist (idempotent)."""
        response = client.delete(
            f"/api/workouts/{workout['id']}/splits",
            headers=auth_headers
        )
        assert response.status_code == 204

    def test_delete_splits_not_owner(self, client, second_auth_headers, workout, auth_headers):
        """Non-owner cannot delete splits."""
        # First create splits as owner
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )

        # Try to delete as non-owner
        response = client.delete(
            f"/api/workouts/{workout['id']}/splits",
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_delete_splits_unauthenticated(self, client, workout):
        """Unauthenticated user cannot delete splits."""
        response = client.delete(f"/api/workouts/{workout['id']}/splits")
        assert response.status_code == 401

    def test_delete_splits_workout_not_found(self, client, auth_headers, registered_user):
        """Delete splits for non-existent workout."""
        response = client.delete(
            "/api/workouts/99999/splits",
            headers=auth_headers
        )
        assert response.status_code == 404


# ===== Integration Tests =====

class TestSplitIntegration:
    """Integration tests for split management."""

    def test_full_split_workflow(self, client, auth_headers, workout):
        """Test complete split workflow: create, update, list, delete."""
        workout_id = workout["id"]

        # 1. List empty splits
        response = client.get(
            f"/api/workouts/{workout_id}/splits",
            headers=auth_headers
        )
        assert response.json()["total"] == 0

        # 2. Create splits
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150},
                {"sequence": 2, "control_point": "45", "cumulative_time": 312, "split_time": 162}
            ]
        }
        response = client.post(
            f"/api/workouts/{workout_id}/splits",
            json=splits_data,
            headers=auth_headers
        )
        assert response.status_code == 201
        split_id = response.json()["splits"][0]["id"]

        # 3. Update a split
        response = client.patch(
            f"/api/workouts/{workout_id}/splits/{split_id}",
            json={"control_point": "32", "cumulative_time": 155},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["control_point"] == "32"

        # 4. List splits to verify
        response = client.get(
            f"/api/workouts/{workout_id}/splits",
            headers=auth_headers
        )
        assert response.json()["total"] == 2
        assert response.json()["splits"][0]["control_point"] == "32"

        # 5. Delete all splits
        response = client.delete(
            f"/api/workouts/{workout_id}/splits",
            headers=auth_headers
        )
        assert response.status_code == 204

        # 6. Verify deletion
        response = client.get(
            f"/api/workouts/{workout_id}/splits",
            headers=auth_headers
        )
        assert response.json()["total"] == 0

    def test_splits_visible_in_workout_detail(self, client, auth_headers, workout):
        """Verify splits appear in workout detail response."""
        # Create splits
        splits_data = {
            "splits": [
                {"sequence": 1, "control_point": "31", "cumulative_time": 150, "split_time": 150}
            ]
        }
        client.post(
            f"/api/workouts/{workout['id']}/splits",
            json=splits_data,
            headers=auth_headers
        )

        # Get workout detail
        response = client.get(
            f"/api/workouts/{workout['id']}",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["splits"] is not None
        assert len(data["splits"]) == 1
        assert data["splits"][0]["control_point"] == "31"
