import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import os
import shutil

from main import app
from app.core.database import Base, get_db
from app.models.memory import MemoryEntry, Tag, Note, Document, Task
from app.memory.embeddings import embedding_service
from app.memory.vector_client import get_vector_db_client
from app.memory.semantic_memory import memory_service, retrieval_service

# Setup a clean SQLite database file for testing
TEST_DB_URL = "sqlite:///./test_prime.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    app.dependency_overrides[get_db] = override_get_db
    # Create tables
    Base.metadata.create_all(bind=engine)
    # Clear vector client for fresh test index
    memory_service.vector_client.reset()
    
    yield
    
    # Drop tables
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    # Remove test databases
    if os.path.exists("./test_prime.db"):
        os.remove("./test_prime.db")
    # Clean chroma directory
    test_chroma_dir = os.path.join(os.path.expanduser("~"), ".gemini", "antigravity-ide", "scratch", "prime-workspace", "chroma_db")
    if os.path.exists(test_chroma_dir):
        try:
            shutil.rmtree(test_chroma_dir)
        except Exception:
            pass


def test_database_crud():
    """Test SQL database CRUD operations for Note, Document and Task tables."""
    db = TestingSessionLocal()
    try:
        # 1. Create a Tag
        tag = Tag(name="rust")
        db.add(tag)
        db.commit()
        assert tag.id is not None
        
        # 2. Create Note
        note = Note(title="Rust Learnings", content="Memory safety is guaranteed without GC.")
        note.tags.append(tag)
        db.add(note)
        db.commit()
        db.refresh(note)
        assert note.id is not None
        assert note.tags[0].name == "rust"
        
        # 3. Create Task
        task = Task(title="Finish compiler project", status="todo", priority="high")
        db.add(task)
        db.commit()
        db.refresh(task)
        assert task.id is not None
        assert task.status == "todo"
        
        # 4. Create Document
        doc = Document(filename="rust_guide.md", content="Ownership rules: one owner, no cycles.")
        db.add(doc)
        db.commit()
        db.refresh(doc)
        assert doc.id is not None
        assert "Ownership" in doc.content

    finally:
        db.close()


def test_embedding_generation():
    """Test abstraction layer embedding generation."""
    text = "Machine Learning optimization methods"
    embedding = embedding_service.get_embedding(text)
    assert isinstance(embedding, list)
    assert len(embedding) == 384  # HeuristicOffline dimension size
    assert all(isinstance(val, float) for val in embedding)


def test_vector_storage_and_semantic_search():
    """Test vector storage inserts, semantic searches and safety deletions."""
    db = TestingSessionLocal()
    try:
        # Create semantic memories
        m1 = memory_service.create_memory(db, "User always likes to write Rust code.", category="preference")
        m2 = memory_service.create_memory(db, "The meeting with engineering is tomorrow at 2 PM.", category="general")
        m3 = memory_service.create_memory(db, "Pytest verification sweeps require DB mocks.", category="general")
        
        assert m1.id is not None
        assert m1.category == "preference"
        
        # Search memories semantically
        results = retrieval_service.retrieve_similar_memories(db, "Rust preferences", limit=2)
        assert len(results) > 0
        # The best match should be the Rust preference entry
        assert "Rust" in results[0].content
        
        # Search memories matching meeting timing
        results_meeting = retrieval_service.retrieve_similar_memories(db, "meeting schedule", limit=1)
        assert "2 PM" in results_meeting[0].content
        
        # Delete memory entry
        delete_success = memory_service.delete_memory(db, m2.id)
        assert delete_success is True
        
        # Re-query deleted
        deleted_check = db.query(MemoryEntry).filter(MemoryEntry.id == m2.id).first()
        assert deleted_check is None

    finally:
        db.close()


def test_api_memory_endpoints():
    """Test REST API routes using TestClient."""
    # 1. Post a memory entry
    payload = {"content": "Always prioritize dark theme aesthetics", "category": "preference"}
    response = client.post("/api/memory/", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "Always prioritize dark theme aesthetics"
    assert data["category"] == "preference"
    assert data["importance"] > 0.5  # Importance scored higher due to "Always" signal
    
    memory_id = data["id"]
    
    # 2. List memories
    list_res = client.get("/api/memory/?category=preference")
    assert list_res.status_code == 200
    assert len(list_res.json()) > 0
    
    # 3. Search memories
    search_res = client.get("/api/memory/search?query=theme%20colors")
    assert search_res.status_code == 200
    assert len(search_res.json()) > 0
    assert "dark theme" in search_res.json()[0]["content"]
    
    # 4. Post a Note
    note_payload = {"title": "Design Specs", "content": "Cyan and purple glows match retro cyber design.", "tags": ["ui", "design"]}
    note_res = client.post("/api/memory/notes", json=note_payload)
    assert note_res.status_code == 200
    assert note_res.json()["title"] == "Design Specs"
    assert "ui" in note_res.json()["tags"]
    
    # 5. List notes
    notes_list = client.get("/api/memory/notes")
    assert notes_list.status_code == 200
    assert len(notes_list.json()) > 0
