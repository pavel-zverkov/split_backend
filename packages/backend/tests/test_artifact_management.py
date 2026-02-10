"""Tests for 10-artifact-management.md endpoints."""
import io
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def event_with_competition(client, auth_headers, registered_user):
    """Create an event with a competition."""
    # Create event
    event_response = client.post("/api/events", json={
        "name": "Test Event",
        "start_date": "2024-06-15",
        "end_date": "2024-06-20",
        "sport_kind": "orient",
        "privacy": "public"
    }, headers=auth_headers)
    event_id = event_response.json()["id"]

    # Create competition
    comp_response = client.post(f"/api/events/{event_id}/competitions", json={
        "name": "Day 1 - Long",
        "date": "2024-06-15",
        "start_format": "separated_start"
    }, headers=auth_headers)

    return {
        "event_id": event_id,
        "competition_id": comp_response.json()["id"]
    }


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
def mock_minio():
    """Mock MinIO client for file operations."""
    with patch('src.artifact.artifact_controller.get_minio_client') as mock:
        minio_client = MagicMock()
        minio_client.bucket_exists.return_value = True
        minio_client.put_object.return_value = None
        minio_client.remove_object.return_value = None
        minio_client.presigned_get_object.return_value = "https://minio.example.com/bucket/file?token=abc123"
        mock.return_value = minio_client
        yield minio_client


class TestUploadCompetitionArtifact:
    """10.1 POST /api/competitions/{competition_id}/artifacts"""

    def test_upload_map_success(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Create a fake file
        file_content = b"fake image content"
        files = {"file": ("course_m21.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map", "tags": "sprint,urban"}

        response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 201
        result = response.json()
        assert result["kind"] == "map"
        assert result["file_name"] == "course_m21.jpg"
        assert result["competition_id"] == competition_id
        assert result["workout_id"] is None
        assert result["tags"] == ["sprint", "urban"]
        assert "file_path" in result

    def test_upload_course_success(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        file_content = b"fake course content"
        files = {"file": ("course.ocd", io.BytesIO(file_content), "application/octet-stream")}
        data = {"kind": "course"}

        response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 201
        assert response.json()["kind"] == "course"

    def test_upload_invalid_file_type(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        """Cannot upload invalid file type for kind."""
        competition_id = event_with_competition["competition_id"]

        # Try to upload .txt as map (should fail)
        file_content = b"fake text content"
        files = {"file": ("document.txt", io.BytesIO(file_content), "text/plain")}
        data = {"kind": "map"}

        response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "invalid file type" in response.json()["detail"].lower()

    def test_upload_invalid_kind_for_competition(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        """Cannot upload workout artifact kind to competition."""
        competition_id = event_with_competition["competition_id"]

        file_content = b"fake gpx content"
        files = {"file": ("track.gpx", io.BytesIO(file_content), "application/gpx+xml")}
        data = {"kind": "gps_track"}

        response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "invalid kind" in response.json()["detail"].lower()

    def test_upload_not_organizer(self, client, second_auth_headers, second_registered_user, event_with_competition, mock_minio):
        """Non-organizer cannot upload competition artifacts."""
        competition_id = event_with_competition["competition_id"]

        file_content = b"fake image content"
        files = {"file": ("map.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map"}

        response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_upload_competition_not_found(self, client, auth_headers, registered_user, mock_minio):
        file_content = b"fake image content"
        files = {"file": ("map.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map"}

        response = client.post(
            "/api/competitions/99999/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 404


class TestListCompetitionArtifacts:
    """10.2 GET /api/competitions/{competition_id}/artifacts"""

    def test_list_artifacts_empty(self, client, event_with_competition):
        competition_id = event_with_competition["competition_id"]

        response = client.get(f"/api/competitions/{competition_id}/artifacts")
        assert response.status_code == 200
        assert response.json()["artifacts"] == []
        assert response.json()["total"] == 0

    def test_list_artifacts_with_data(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload an artifact
        file_content = b"fake image content"
        files = {"file": ("course_m21.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map", "tags": "sprint"}

        client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )

        # List artifacts
        response = client.get(f"/api/competitions/{competition_id}/artifacts")
        assert response.status_code == 200
        result = response.json()
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["kind"] == "map"
        assert result["artifacts"][0]["file_name"] == "course_m21.jpg"
        assert "uploaded_by" in result["artifacts"][0]

    def test_list_artifacts_filter_by_kind(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload map
        files1 = {"file": ("map.jpg", io.BytesIO(b"map"), "image/jpeg")}
        client.post(f"/api/competitions/{competition_id}/artifacts", files=files1, data={"kind": "map"}, headers=auth_headers)

        # Upload photo
        files2 = {"file": ("photo.png", io.BytesIO(b"photo"), "image/png")}
        client.post(f"/api/competitions/{competition_id}/artifacts", files=files2, data={"kind": "photo"}, headers=auth_headers)

        # Filter by kind
        response = client.get(f"/api/competitions/{competition_id}/artifacts?kind=map")
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 1
        assert response.json()["artifacts"][0]["kind"] == "map"

    @pytest.mark.skip(reason="Tag filtering uses PostgreSQL ARRAY overlap, not supported in SQLite")
    def test_list_artifacts_filter_by_tags(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload with tag "sprint"
        files1 = {"file": ("map1.jpg", io.BytesIO(b"map1"), "image/jpeg")}
        client.post(f"/api/competitions/{competition_id}/artifacts", files=files1, data={"kind": "map", "tags": "sprint"}, headers=auth_headers)

        # Upload with tag "forest"
        files2 = {"file": ("map2.jpg", io.BytesIO(b"map2"), "image/jpeg")}
        client.post(f"/api/competitions/{competition_id}/artifacts", files=files2, data={"kind": "map", "tags": "forest"}, headers=auth_headers)

        # Filter by tag
        response = client.get(f"/api/competitions/{competition_id}/artifacts?tags=sprint")
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 1

    def test_list_artifacts_pagination(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload 3 artifacts
        for i in range(3):
            files = {"file": (f"map{i}.jpg", io.BytesIO(b"content"), "image/jpeg")}
            client.post(f"/api/competitions/{competition_id}/artifacts", files=files, data={"kind": "map"}, headers=auth_headers)

        # Get first page
        response = client.get(f"/api/competitions/{competition_id}/artifacts?limit=2&offset=0")
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 2
        assert response.json()["total"] == 3

        # Get second page
        response = client.get(f"/api/competitions/{competition_id}/artifacts?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 1


class TestGetArtifactDetails:
    """10.3 GET /api/artifacts/{artifact_id}"""

    def test_get_artifact_success(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload an artifact
        file_content = b"fake image content"
        files = {"file": ("course_m21.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map", "tags": "sprint,urban"}

        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Get details
        response = client.get(f"/api/artifacts/{artifact_id}")
        assert response.status_code == 200
        result = response.json()
        assert result["id"] == artifact_id
        assert result["kind"] == "map"
        assert result["file_name"] == "course_m21.jpg"
        assert result["tags"] == ["sprint", "urban"]
        assert "download_url" in result
        assert "uploaded_by" in result

    def test_get_artifact_not_found(self, client):
        response = client.get("/api/artifacts/99999")
        assert response.status_code == 404


class TestUpdateArtifact:
    """10.4 PATCH /api/artifacts/{artifact_id}"""

    def test_update_artifact_tags(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload an artifact
        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map", "tags": "sprint"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Update tags
        response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "tags": ["sprint", "forest", "night"]
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["tags"] == ["sprint", "forest", "night"]

    def test_update_artifact_kind(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload a photo
        files = {"file": ("image.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "photo"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Change kind to map
        response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "kind": "map"
        }, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["kind"] == "map"

    def test_update_artifact_invalid_kind(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        """Cannot change competition artifact to workout kind."""
        competition_id = event_with_competition["competition_id"]

        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Try to change to workout kind
        response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "kind": "gps_track"
        }, headers=auth_headers)
        assert response.status_code == 400

    def test_update_artifact_not_authorized(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_competition, mock_minio):
        """Non-organizer cannot update competition artifact."""
        competition_id = event_with_competition["competition_id"]

        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "tags": ["new"]
        }, headers=second_auth_headers)
        assert response.status_code == 403


class TestDeleteArtifact:
    """10.5 DELETE /api/artifacts/{artifact_id}"""

    def test_delete_artifact_success(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload an artifact
        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Delete
        response = client.delete(f"/api/artifacts/{artifact_id}", headers=auth_headers)
        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/api/artifacts/{artifact_id}")
        assert get_response.status_code == 404

    def test_delete_artifact_not_authorized(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, event_with_competition, mock_minio):
        """Non-organizer cannot delete competition artifact."""
        competition_id = event_with_competition["competition_id"]

        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        response = client.delete(f"/api/artifacts/{artifact_id}", headers=second_auth_headers)
        assert response.status_code == 403

    def test_delete_artifact_not_found(self, client, auth_headers, registered_user):
        response = client.delete("/api/artifacts/99999", headers=auth_headers)
        assert response.status_code == 404


class TestDownloadArtifact:
    """10.6 GET /api/artifacts/{artifact_id}/download"""

    def test_download_artifact_redirect(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        competition_id = event_with_competition["competition_id"]

        # Upload an artifact
        files = {"file": ("map.jpg", io.BytesIO(b"content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map"},
            headers=auth_headers
        )
        artifact_id = upload_response.json()["id"]

        # Download (expect redirect)
        response = client.get(f"/api/artifacts/{artifact_id}/download", follow_redirects=False)
        assert response.status_code == 302
        assert "location" in response.headers

    def test_download_artifact_not_found(self, client):
        response = client.get("/api/artifacts/99999/download", follow_redirects=False)
        assert response.status_code == 404


class TestUploadWorkoutArtifact:
    """10.7 POST /api/workouts/{workout_id}/artifacts"""

    def test_upload_gps_track_success(self, client, auth_headers, registered_user, user_workout, mock_minio):
        workout_id = user_workout["id"]

        file_content = b"fake gpx content"
        files = {"file": ("activity.gpx", io.BytesIO(file_content), "application/gpx+xml")}
        data = {"kind": "gps_track", "tags": "training,interval"}

        response = client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 201
        result = response.json()
        assert result["kind"] == "gps_track"
        assert result["file_name"] == "activity.gpx"
        assert result["workout_id"] == workout_id
        assert result["competition_id"] is None
        assert result["tags"] == ["training", "interval"]

    def test_upload_fit_file_success(self, client, auth_headers, registered_user, user_workout, mock_minio):
        workout_id = user_workout["id"]

        file_content = b"fake fit content"
        files = {"file": ("activity.fit", io.BytesIO(file_content), "application/vnd.ant.fit")}
        data = {"kind": "fit_file"}

        response = client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 201
        assert response.json()["kind"] == "fit_file"

    def test_upload_invalid_kind_for_workout(self, client, auth_headers, registered_user, user_workout, mock_minio):
        """Cannot upload competition artifact kind to workout."""
        workout_id = user_workout["id"]

        file_content = b"fake image content"
        files = {"file": ("map.jpg", io.BytesIO(file_content), "image/jpeg")}
        data = {"kind": "map"}

        response = client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 400
        assert "invalid kind" in response.json()["detail"].lower()

    def test_upload_not_owner(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, user_workout, mock_minio):
        """Non-owner cannot upload workout artifacts."""
        workout_id = user_workout["id"]

        file_content = b"fake gpx content"
        files = {"file": ("track.gpx", io.BytesIO(file_content), "application/gpx+xml")}
        data = {"kind": "gps_track"}

        response = client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data=data,
            headers=second_auth_headers
        )
        assert response.status_code == 403

    def test_upload_workout_not_found(self, client, auth_headers, registered_user, mock_minio):
        file_content = b"fake gpx content"
        files = {"file": ("track.gpx", io.BytesIO(file_content), "application/gpx+xml")}
        data = {"kind": "gps_track"}

        response = client.post(
            "/api/workouts/99999/artifacts",
            files=files,
            data=data,
            headers=auth_headers
        )
        assert response.status_code == 404


class TestListWorkoutArtifacts:
    """10.8 GET /api/workouts/{workout_id}/artifacts"""

    def test_list_artifacts_empty(self, client, auth_headers, registered_user, user_workout):
        workout_id = user_workout["id"]

        response = client.get(f"/api/workouts/{workout_id}/artifacts", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["artifacts"] == []
        assert response.json()["total"] == 0

    def test_list_artifacts_with_data(self, client, auth_headers, registered_user, user_workout, mock_minio):
        workout_id = user_workout["id"]

        # Upload an artifact
        files = {"file": ("track.gpx", io.BytesIO(b"content"), "application/gpx+xml")}
        client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data={"kind": "gps_track"},
            headers=auth_headers
        )

        # List artifacts
        response = client.get(f"/api/workouts/{workout_id}/artifacts", headers=auth_headers)
        assert response.status_code == 200
        result = response.json()
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["kind"] == "gps_track"

    def test_list_artifacts_filter_by_kind(self, client, auth_headers, registered_user, user_workout, mock_minio):
        workout_id = user_workout["id"]

        # Upload GPX
        files1 = {"file": ("track.gpx", io.BytesIO(b"gpx"), "application/gpx+xml")}
        client.post(f"/api/workouts/{workout_id}/artifacts", files=files1, data={"kind": "gps_track"}, headers=auth_headers)

        # Upload FIT
        files2 = {"file": ("activity.fit", io.BytesIO(b"fit"), "application/vnd.ant.fit")}
        client.post(f"/api/workouts/{workout_id}/artifacts", files=files2, data={"kind": "fit_file"}, headers=auth_headers)

        # Filter by kind
        response = client.get(f"/api/workouts/{workout_id}/artifacts?kind=gps_track", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 1
        assert response.json()["artifacts"][0]["kind"] == "gps_track"

    def test_list_public_workout_artifacts(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, user_workout, mock_minio):
        """Public workout artifacts visible to all."""
        workout_id = user_workout["id"]

        # Upload artifact
        files = {"file": ("track.gpx", io.BytesIO(b"content"), "application/gpx+xml")}
        client.post(f"/api/workouts/{workout_id}/artifacts", files=files, data={"kind": "gps_track"}, headers=auth_headers)

        # Other user can see (workout is public)
        response = client.get(f"/api/workouts/{workout_id}/artifacts", headers=second_auth_headers)
        assert response.status_code == 200
        assert len(response.json()["artifacts"]) == 1


class TestWorkoutArtifactPrivacy:
    """Test workout artifact privacy."""

    def test_private_workout_artifacts_hidden(self, client, auth_headers, second_auth_headers, registered_user, second_registered_user, mock_minio):
        """Private workout artifacts not visible to others."""
        # Create private workout
        workout_response = client.post("/api/workouts", json={
            "title": "Private Run",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "private"
        }, headers=auth_headers)
        workout_id = workout_response.json()["id"]

        # Upload artifact
        files = {"file": ("track.gpx", io.BytesIO(b"content"), "application/gpx+xml")}
        client.post(f"/api/workouts/{workout_id}/artifacts", files=files, data={"kind": "gps_track"}, headers=auth_headers)

        # Other user cannot see
        response = client.get(f"/api/workouts/{workout_id}/artifacts", headers=second_auth_headers)
        assert response.status_code == 403

    def test_owner_can_see_private_artifacts(self, client, auth_headers, registered_user, mock_minio):
        """Owner can always see their own artifacts."""
        # Create private workout
        workout_response = client.post("/api/workouts", json={
            "title": "Private Run",
            "sport_kind": "orient",
            "start_datetime": "2024-06-15T08:00:00Z",
            "privacy": "private"
        }, headers=auth_headers)
        workout_id = workout_response.json()["id"]

        # Upload artifact
        files = {"file": ("track.gpx", io.BytesIO(b"content"), "application/gpx+xml")}
        upload_response = client.post(f"/api/workouts/{workout_id}/artifacts", files=files, data={"kind": "gps_track"}, headers=auth_headers)
        artifact_id = upload_response.json()["id"]

        # Owner can see artifact details
        response = client.get(f"/api/artifacts/{artifact_id}", headers=auth_headers)
        assert response.status_code == 200


class TestArtifactIntegration:
    """Integration tests for artifact management."""

    def test_full_competition_artifact_flow(self, client, auth_headers, registered_user, event_with_competition, mock_minio):
        """Full flow: upload -> list -> get -> update -> download -> delete."""
        competition_id = event_with_competition["competition_id"]

        # Upload
        files = {"file": ("map.jpg", io.BytesIO(b"map content"), "image/jpeg")}
        upload_response = client.post(
            f"/api/competitions/{competition_id}/artifacts",
            files=files,
            data={"kind": "map", "tags": "sprint"},
            headers=auth_headers
        )
        assert upload_response.status_code == 201
        artifact_id = upload_response.json()["id"]

        # List
        list_response = client.get(f"/api/competitions/{competition_id}/artifacts")
        assert list_response.status_code == 200
        assert len(list_response.json()["artifacts"]) == 1

        # Get details
        get_response = client.get(f"/api/artifacts/{artifact_id}")
        assert get_response.status_code == 200
        assert get_response.json()["kind"] == "map"

        # Update
        update_response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "tags": ["sprint", "urban"]
        }, headers=auth_headers)
        assert update_response.status_code == 200
        assert update_response.json()["tags"] == ["sprint", "urban"]

        # Download
        download_response = client.get(f"/api/artifacts/{artifact_id}/download", follow_redirects=False)
        assert download_response.status_code == 302

        # Delete
        delete_response = client.delete(f"/api/artifacts/{artifact_id}", headers=auth_headers)
        assert delete_response.status_code == 204

        # Verify deleted
        verify_response = client.get(f"/api/artifacts/{artifact_id}")
        assert verify_response.status_code == 404

    def test_full_workout_artifact_flow(self, client, auth_headers, registered_user, user_workout, mock_minio):
        """Full flow for workout artifacts."""
        workout_id = user_workout["id"]

        # Upload
        files = {"file": ("activity.gpx", io.BytesIO(b"gpx content"), "application/gpx+xml")}
        upload_response = client.post(
            f"/api/workouts/{workout_id}/artifacts",
            files=files,
            data={"kind": "gps_track", "tags": "training"},
            headers=auth_headers
        )
        assert upload_response.status_code == 201
        artifact_id = upload_response.json()["id"]

        # List
        list_response = client.get(f"/api/workouts/{workout_id}/artifacts", headers=auth_headers)
        assert list_response.status_code == 200
        assert len(list_response.json()["artifacts"]) == 1

        # Update (owner can update workout artifact)
        update_response = client.patch(f"/api/artifacts/{artifact_id}", json={
            "tags": ["training", "race"]
        }, headers=auth_headers)
        assert update_response.status_code == 200

        # Delete
        delete_response = client.delete(f"/api/artifacts/{artifact_id}", headers=auth_headers)
        assert delete_response.status_code == 204
