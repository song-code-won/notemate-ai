"""
Tests for Note CRUD operations, SQLite persistence, and search functionality.
"""

import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use a temporary database for test isolation
temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
temp_db_path = temp_db.name
temp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{temp_db_path}"

from app.database import init_db
from app.main import app
from app.services.note_service import NoteService
from app.models import NoteCreate, NoteUpdate


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()
    yield
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass


@pytest.fixture
def client():
    return TestClient(app)


def test_create_and_get_note(client):
    """Test creating a new note and retrieving it by ID."""
    payload = {
        "title": "Docker Architecture Lecture",
        "content": "Docker uses client-server architecture. Docker daemon manages images, containers, and networks.",
        "tags": "docker, devops, study",
    }
    response = client.post("/api/notes", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["title"] == payload["title"]
    assert data["content"] == payload["content"]
    assert data["tags"] == payload["tags"]
    assert "created_at" in data
    assert "updated_at" in data

    # Retrieve by ID
    get_res = client.get(f"/api/notes/{data['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == payload["title"]


def test_update_note(client):
    """Test updating existing note content, title, and tags."""
    create_res = client.post(
        "/api/notes",
        json={"title": "Original Title", "content": "Original content", "tags": "v1"},
    )
    note_id = create_res.json()["id"]

    update_payload = {
        "title": "Updated Title",
        "content": "Updated content with more details",
        "tags": "v2, updated",
        "summary": "AI summary text here",
    }
    update_res = client.put(f"/api/notes/{note_id}", json=update_payload)
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["title"] == "Updated Title"
    assert updated_data["content"] == "Updated content with more details"
    assert updated_data["tags"] == "v2, updated"
    assert updated_data["summary"] == "AI summary text here"


def test_delete_note(client):
    """Test deleting a note and verifying 404 on subsequent get."""
    create_res = client.post(
        "/api/notes",
        json={"title": "To be deleted", "content": "Temporary note", "tags": "temp"},
    )
    note_id = create_res.json()["id"]

    del_res = client.delete(f"/api/notes/{note_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/notes/{note_id}")
    assert get_res.status_code == 404


def test_search_and_filter_notes(client):
    """Test searching notes by query and filtering by tag."""
    client.post(
        "/api/notes",
        json={
            "title": "Quantum Computing Basics",
            "content": "Qubits and superposition allow exponential parallel calculations.",
            "tags": "physics, quantum",
        },
    )
    client.post(
        "/api/notes",
        json={
            "title": "Grocery Shopping List",
            "content": "Buy oats, almond milk, bananas, and coffee beans.",
            "tags": "personal, shopping",
        },
    )

    # Search for quantum
    search_res = client.get("/api/notes?q=superposition")
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any("Quantum Computing" in r["title"] for r in results)

    # Filter by tag
    tag_res = client.get("/api/notes?tag=shopping")
    assert tag_res.status_code == 200
    tag_results = tag_res.json()
    assert len(tag_results) >= 1
    assert all("shopping" in r["tags"] for r in tag_results)


def test_database_persistence():
    """Verify notes persist in SQLite database across service calls."""
    data = NoteCreate(
        title="Persistence Verification",
        content="Testing direct SQLite persistence.",
        tags="test, persistence",
    )
    created = NoteService.create_note(data)
    assert created.id > 0

    fetched = NoteService.get_note(created.id)
    assert fetched is not None
    assert fetched.title == "Persistence Verification"
    assert fetched.content == "Testing direct SQLite persistence."
