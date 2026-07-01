from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Text, Table, Integer
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import json
from app.core.database import Base

# Many-to-Many Association Tables for Tags
memory_tag_association = Table(
    "memory_tags",
    Base.metadata,
    Column("memory_id", String, ForeignKey("memory_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

note_tag_association = Table(
    "note_tags",
    Base.metadata,
    Column("note_id", String, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

task_tag_association = Table(
    "task_tags",
    Base.metadata,
    Column("task_id", String, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)


class Tag(Base):
    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, unique=True, nullable=False)


class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False)
    category = Column(String, default="general")  # 'conversation', 'preference', 'note', 'document', 'general'
    vector_id = Column(String, nullable=True)  # Key inside vector database (ChromaDB)
    importance = Column(Float, default=0.5)  # Semantic importance score
    created_at = Column(DateTime, default=datetime.utcnow)
    _metadata = Column("metadata", Text, default="{}")  # Serialized metadata JSON dictionary

    # Relationships
    tags = relationship("Tag", secondary=memory_tag_association, backref="memories")

    @property
    def metadata_dict(self) -> dict:
        try:
            return json.loads(self._metadata or "{}")
        except Exception:
            return {}

    @metadata_dict.setter
    def metadata_dict(self, val: dict):
        self._metadata = json.dumps(val or {})


class Note(Base):
    __tablename__ = "notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tags = relationship("Tag", secondary=note_tag_association, backref="notes")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    mime_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="todo")  # 'todo', 'in_progress', 'done'
    priority = Column(String, default="medium")  # 'low', 'medium', 'high'
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    tags = relationship("Tag", secondary=task_tag_association, backref="tasks")


class MemoryRelationship(Base):
    __tablename__ = "memory_relationships"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String, ForeignKey("memory_entries.id", ondelete="CASCADE"), nullable=False)
    target_id = Column(String, ForeignKey("memory_entries.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String, default="relates_to")  # 'relates_to', 'depends_on', 'part_of'
    created_at = Column(DateTime, default=datetime.utcnow)
