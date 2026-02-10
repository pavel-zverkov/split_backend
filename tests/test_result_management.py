"""Tests for 11-result-management.md endpoints."""
import io
import pytest


@pytest.fixture
def event_with_competition(client, auth_headers, registered_user):
    """Create an event with a competition that has control points."""
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

    # Create competition with control points
    comp_response = client.post(f"/api/events/{event_id}/competitions", json={
        "name": "Day 1 - Long",
        "date": "2024-06-15",
        "class_list": ["M21", "M35", "W21"],
        "control_points_list": ["31", "45", "78", "finish"],
        "start_format": "separated_start"
    }, headers=auth_headers)

    return {
        "event_id": event_id,
        "competition_id": comp_response.json()["id"]
    }


@pytest.fixture
def registered_participant(client, auth_headers, second_auth_headers, second_registered_user, event_with_competition):
    """Register second user as participant with confirmed registration."""
    event_id = event_with_competition["event_id"]
    competition_id = event_with_competition["competition_id"]

    # Join event
    client.post(f"/api/events/{event_id}/join", json={
        "role": "participant"
    }, headers=second_auth_headers)

    # Register for competition
    reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
        "class": "M21"
    }, headers=second_auth_headers)
    reg_id = reg_response.json()["id"]

    # Organizer confirms with bib
    client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
        "status": "confirmed",
        "bib_number": "101"
    }, headers=auth_headers)

    return {
        **event_with_competition,
        "registration_id": reg_id,
        "user_id": second_registered_user["user"]["id"]
    }


@pytest.fixture
def third_registered_participant(client, auth_headers, third_auth_headers, third_registered_user, event_with_competition):
    """Register third user as participant."""
    event_id = event_with_competition["event_id"]
    competition_id = event_with_competition["competition_id"]

    # Join event
    client.post(f"/api/events/{event_id}/join", json={
        "role": "participant"
    }, headers=third_auth_headers)

    # Register for competition
    reg_response = client.post(f"/api/competitions/{competition_id}/register", json={
        "class": "M21"
    }, headers=third_auth_headers)
    reg_id = reg_response.json()["id"]

    # Organizer confirms with bib
    client.patch(f"/api/competitions/{competition_id}/registrations/{reg_id}", json={
        "status": "confirmed",
        "bib_number": "102"
    }, headers=auth_headers)

    return {
        **event_with_competition,
        "registration_id": reg_id,
        "user_id": third_registered_user["user"]["id"]
    }


class TestCreateResult:
    """11.1 POST /api/competitions/{competition_id}/results"""

    def test_create_result_success(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 245},
                {"control_point": "45", "cumulative_time": 512},
                {"control_point": "78", "cumulative_time": 890},
                {"control_point": "finish", "cumulative_time": 3845}
            ]
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert data["class"] == "M21"
        assert data["time_total"] == 3845
        assert data["status"] == "ok"
        assert data["position"] == 1
        assert len(data["splits"]) == 4
        # Check split times are calculated
        assert data["splits"][0]["split_time"] == 245
        assert data["splits"][1]["split_time"] == 267  # 512 - 245

    def test_create_result_without_splits(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["splits"] is None

    def test_create_result_dns_status(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "status": "dns"
        }, headers=auth_headers)
        assert response.status_code == 201
        assert response.json()["status"] == "dns"
        assert response.json()["time_total"] is None

    def test_create_result_user_not_registered(self, client, auth_headers, registered_user, event_with_competition):
        """Cannot create result for non-registered user."""
        competition_id = event_with_competition["competition_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": 99999,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"].lower()

    def test_create_result_already_exists(self, client, auth_headers, registered_user, registered_participant):
        """Cannot create duplicate result."""
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # First result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)

        # Duplicate
        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3900,
            "status": "ok"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_result_invalid_class(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M99",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "invalid class" in response.json()["detail"].lower()

    def test_create_result_invalid_control_points(self, client, auth_headers, registered_user, registered_participant):
        """Splits must match competition control points."""
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok",
            "splits": [
                {"control_point": "wrong", "cumulative_time": 245},
                {"control_point": "finish", "cumulative_time": 3845}
            ]
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "control points" in response.json()["detail"].lower()

    def test_create_result_not_authorized(self, client, second_auth_headers, second_registered_user, registered_participant):
        """Non-organizer cannot create results."""
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=second_auth_headers)
        assert response.status_code == 403


class TestListResults:
    """11.2 GET /api/competitions/{competition_id}/results"""

    def test_list_results_empty(self, client, event_with_competition):
        competition_id = event_with_competition["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/results")
        assert response.status_code == 200
        assert response.json()["results"] == []
        assert response.json()["total"] == 0

    def test_list_results_with_data(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 245},
                {"control_point": "45", "cumulative_time": 512},
                {"control_point": "78", "cumulative_time": 890},
                {"control_point": "finish", "cumulative_time": 3845}
            ]
        }, headers=auth_headers)

        # List results
        response = client.get(f"/api/competitions/{competition_id}/results")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["class"] == "M21"
        assert data["results"][0]["has_splits"] is True
        assert "competition" in data
        assert "classes" in data

    def test_list_results_filter_by_class(self, client, auth_headers, registered_user, registered_participant, third_registered_participant):
        competition_id = registered_participant["competition_id"]

        # Create result for M21
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": registered_participant["user_id"],
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)

        # Create result for M35 (change class for third user)
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": third_registered_participant["user_id"],
            "class": "M35",
            "time_total": 4000,
            "status": "ok"
        }, headers=auth_headers)

        # Filter by class
        response = client.get(f"/api/competitions/{competition_id}/results?class=M21")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 1
        assert response.json()["results"][0]["class"] == "M21"

    def test_list_results_sorted_by_position(self, client, auth_headers, registered_user, registered_participant, third_registered_participant):
        competition_id = registered_participant["competition_id"]

        # Create slower result first
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": registered_participant["user_id"],
            "class": "M21",
            "time_total": 4000,
            "status": "ok"
        }, headers=auth_headers)

        # Create faster result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": third_registered_participant["user_id"],
            "class": "M21",
            "time_total": 3800,
            "status": "ok"
        }, headers=auth_headers)

        response = client.get(f"/api/competitions/{competition_id}/results")
        assert response.status_code == 200
        results = response.json()["results"]
        assert results[0]["position"] == 1
        assert results[0]["time_total"] == 3800
        assert results[1]["position"] == 2
        assert results[1]["time_total"] == 4000


class TestGetResultDetail:
    """11.3 GET /api/competitions/{competition_id}/results/{result_id}"""

    def test_get_result_with_splits(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 245},
                {"control_point": "45", "cumulative_time": 512},
                {"control_point": "78", "cumulative_time": 890},
                {"control_point": "finish", "cumulative_time": 3845}
            ]
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Get detail
        response = client.get(f"/api/competitions/{competition_id}/results/{result_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == result_id
        assert "user" in data
        assert "competition" in data
        assert len(data["splits"]) == 4
        # Check split positions are calculated
        assert data["splits"][0]["position"] == 1  # Only one result, so position 1

    def test_get_result_not_found(self, client, event_with_competition):
        competition_id = event_with_competition["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/results/99999")
        assert response.status_code == 404


class TestGetMyResult:
    """11.4 GET /api/competitions/{competition_id}/results/me"""

    def test_get_my_result_success(self, client, auth_headers, second_auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Organizer creates result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)

        # User gets their own result
        response = client.get(f"/api/competitions/{competition_id}/results/me", headers=second_auth_headers)
        assert response.status_code == 200
        assert response.json()["class"] == "M21"

    def test_get_my_result_not_found(self, client, second_auth_headers, second_registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/results/me", headers=second_auth_headers)
        assert response.status_code == 404


class TestUpdateResult:
    """11.5 PATCH /api/competitions/{competition_id}/results/{result_id}"""

    def test_update_result_time(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Update time
        response = client.patch(f"/api/competitions/{competition_id}/results/{result_id}", json={
            "time_total": 3850
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["time_total"] == 3850

    def test_update_result_status(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        response = client.patch(f"/api/competitions/{competition_id}/results/{result_id}", json={
            "status": "dsq"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "dsq"

    def test_update_result_replace_splits(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 245},
                {"control_point": "45", "cumulative_time": 512},
                {"control_point": "78", "cumulative_time": 890},
                {"control_point": "finish", "cumulative_time": 3845}
            ]
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Replace splits with new times
        response = client.patch(f"/api/competitions/{competition_id}/results/{result_id}", json={
            "time_total": 3850,
            "splits": [
                {"control_point": "31", "cumulative_time": 250},
                {"control_point": "45", "cumulative_time": 520},
                {"control_point": "78", "cumulative_time": 900},
                {"control_point": "finish", "cumulative_time": 3850}
            ]
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["splits"][0]["cumulative_time"] == 250

    def test_update_result_not_authorized(self, client, auth_headers, second_auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        response = client.patch(f"/api/competitions/{competition_id}/results/{result_id}", json={
            "time_total": 3850
        }, headers=second_auth_headers)
        assert response.status_code == 403


class TestDeleteResult:
    """11.6 DELETE /api/competitions/{competition_id}/results/{result_id}"""

    def test_delete_result_success(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        response = client.delete(f"/api/competitions/{competition_id}/results/{result_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/competitions/{competition_id}/results/{result_id}")
        assert get_response.status_code == 404

    def test_delete_result_not_found(self, client, auth_headers, registered_user, event_with_competition):
        competition_id = event_with_competition["competition_id"]

        response = client.delete(f"/api/competitions/{competition_id}/results/99999", headers=auth_headers)
        assert response.status_code == 404


class TestRecalculatePositions:
    """11.7 POST /api/competitions/{competition_id}/results/recalculate"""

    def test_recalculate_positions_success(self, client, auth_headers, registered_user, registered_participant, third_registered_participant):
        competition_id = registered_participant["competition_id"]

        # Create results
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": registered_participant["user_id"],
            "class": "M21",
            "time_total": 4000,
            "status": "ok"
        }, headers=auth_headers)

        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": third_registered_participant["user_id"],
            "class": "M21",
            "time_total": 3800,
            "status": "ok"
        }, headers=auth_headers)

        # Recalculate
        response = client.post(f"/api/competitions/{competition_id}/results/recalculate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["recalculated"] is True
        assert data["results_count"] == 2
        assert data["classes_count"] == 1

    def test_recalculate_positions_not_authorized(self, client, second_auth_headers, second_registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]

        response = client.post(f"/api/competitions/{competition_id}/results/recalculate", headers=second_auth_headers)
        assert response.status_code == 403


class TestImportResults:
    """11.8 POST /api/competitions/{competition_id}/results/import"""

    def test_import_results_success(self, client, auth_headers, registered_user, registered_participant, third_registered_participant):
        competition_id = registered_participant["competition_id"]

        csv_content = """bib_number,time_total,status,split_31,split_45,split_78,split_finish
101,3845,ok,245,512,890,3845
102,4000,ok,260,530,920,4000
"""
        files = {"file": ("results.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        data = {"format": "csv"}

        response = client.post(
            f"/api/competitions/{competition_id}/results/import",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["imported"] == 2
        assert result["errors"] == []

    def test_import_results_with_errors(self, client, auth_headers, registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]

        csv_content = """bib_number,time_total,status
101,3845,ok
999,4000,ok
"""
        files = {"file": ("results.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        data = {"format": "csv"}

        response = client.post(
            f"/api/competitions/{competition_id}/results/import",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert result["imported"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["bib_number"] == "999"

    def test_import_results_not_authorized(self, client, second_auth_headers, second_registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]

        csv_content = "bib_number,time_total,status\n101,3845,ok\n"
        files = {"file": ("results.csv", io.BytesIO(csv_content.encode()), "text/csv")}
        data = {"format": "csv"}

        response = client.post(
            f"/api/competitions/{competition_id}/results/import",
            files=files,
            data=data,
            headers=second_auth_headers
        )
        assert response.status_code == 403


class TestLinkWorkout:
    """11.9 PATCH /api/results/{result_id}/link-workout"""

    def test_link_workout_by_owner(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Create workout for the participant (matching date)
        workout_response = client.post("/api/workouts", json={
            "title": "Competition Run",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T10:00:00Z",
            "privacy": "public"
        }, headers=second_auth_headers)
        workout_id = workout_response.json()["id"]

        # Link workout (by participant)
        response = client.patch(f"/api/results/{result_id}/link-workout", json={
            "workout_id": workout_id
        }, headers=second_auth_headers)
        assert response.status_code == 200
        assert response.json()["workout_id"] == workout_id

    def test_link_workout_by_organizer(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, registered_participant):
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Create workout for the participant
        workout_response = client.post("/api/workouts", json={
            "title": "Competition Run",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T10:00:00Z",
            "privacy": "public"
        }, headers=second_auth_headers)
        workout_id = workout_response.json()["id"]

        # Link workout (by organizer)
        response = client.patch(f"/api/results/{result_id}/link-workout", json={
            "workout_id": workout_id
        }, headers=auth_headers)
        assert response.status_code == 200

    def test_link_workout_wrong_user(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, registered_participant):
        """Cannot link workout that belongs to different user."""
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result for participant
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Create workout for organizer (different user)
        workout_response = client.post("/api/workouts", json={
            "title": "My Run",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T10:00:00Z",
            "privacy": "public"
        }, headers=auth_headers)
        workout_id = workout_response.json()["id"]

        # Try to link
        response = client.patch(f"/api/results/{result_id}/link-workout", json={
            "workout_id": workout_id
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "does not belong" in response.json()["detail"].lower()

    def test_link_workout_wrong_date(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, registered_participant):
        """Cannot link workout with mismatched date."""
        competition_id = registered_participant["competition_id"]
        user_id = registered_participant["user_id"]

        # Create result
        create_response = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": user_id,
            "class": "M21",
            "time_total": 3845,
            "status": "ok"
        }, headers=auth_headers)
        result_id = create_response.json()["id"]

        # Create workout with wrong date (competition is 2024-06-15)
        workout_response = client.post("/api/workouts", json={
            "title": "Wrong Date Run",
            "sport_kind": "orient",
            "start_datetime": "2024-07-01T10:00:00Z",
            "privacy": "public"
        }, headers=second_auth_headers)
        workout_id = workout_response.json()["id"]

        # Try to link
        response = client.patch(f"/api/results/{result_id}/link-workout", json={
            "workout_id": workout_id
        }, headers=second_auth_headers)
        assert response.status_code == 400
        assert "date" in response.json()["detail"].lower()


class TestResultIntegration:
    """Integration tests for result management."""

    def test_full_result_flow(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, registered_participant, third_registered_participant):
        """Full flow: create -> list -> get -> update -> recalculate."""
        competition_id = registered_participant["competition_id"]

        # Create first result (slower)
        r1 = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": registered_participant["user_id"],
            "class": "M21",
            "time_total": 4000,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 260},
                {"control_point": "45", "cumulative_time": 540},
                {"control_point": "78", "cumulative_time": 920},
                {"control_point": "finish", "cumulative_time": 4000}
            ]
        }, headers=auth_headers)
        assert r1.status_code == 201
        result1_id = r1.json()["id"]

        # Create second result (faster)
        r2 = client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": third_registered_participant["user_id"],
            "class": "M21",
            "time_total": 3800,
            "status": "ok",
            "splits": [
                {"control_point": "31", "cumulative_time": 240},
                {"control_point": "45", "cumulative_time": 500},
                {"control_point": "78", "cumulative_time": 870},
                {"control_point": "finish", "cumulative_time": 3800}
            ]
        }, headers=auth_headers)
        assert r2.status_code == 201

        # Check leaderboard
        list_response = client.get(f"/api/competitions/{competition_id}/results")
        results = list_response.json()["results"]
        assert results[0]["time_total"] == 3800  # Fastest first
        assert results[0]["position"] == 1
        assert results[1]["time_total"] == 4000
        assert results[1]["position"] == 2

        # Check time behind leader
        detail = client.get(f"/api/competitions/{competition_id}/results/{result1_id}")
        assert detail.json()["time_behind_leader"] == 200  # 4000 - 3800

        # Update first result to be faster
        client.patch(f"/api/competitions/{competition_id}/results/{result1_id}", json={
            "time_total": 3700
        }, headers=auth_headers)

        # Verify positions recalculated
        list_response = client.get(f"/api/competitions/{competition_id}/results")
        results = list_response.json()["results"]
        assert results[0]["time_total"] == 3700  # Now fastest
        assert results[0]["position"] == 1

    def test_position_calculation_with_different_statuses(self, client, auth_headers, registered_user, registered_participant, third_registered_participant):
        """DNF/DNS results should be ranked after OK results."""
        competition_id = registered_participant["competition_id"]

        # Create OK result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": registered_participant["user_id"],
            "class": "M21",
            "time_total": 4000,
            "status": "ok"
        }, headers=auth_headers)

        # Create DNF result
        client.post(f"/api/competitions/{competition_id}/results", json={
            "user_id": third_registered_participant["user_id"],
            "class": "M21",
            "status": "dnf"
        }, headers=auth_headers)

        # Check positions
        list_response = client.get(f"/api/competitions/{competition_id}/results")
        results = list_response.json()["results"]
        assert results[0]["status"] == "ok"
        assert results[0]["position"] == 1
        assert results[1]["status"] == "dnf"
        assert results[1]["position"] == 2
