from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
import datetime

from app.core.database import get_db
from app.models.memory import MemoryEntry, Note, Document, Task, Tag
from app.models.conversation import Conversation, Message
from app.memory.semantic_memory import memory_service, retrieval_service

router = APIRouter(prefix="/memory", tags=["Memory & Database Engine"])


# --- Pydantic Schemas ---
class MemoryCreateSchema(BaseModel):
    content: str
    category: str = "general"
    metadata: Optional[Dict] = None

class MemoryResponseSchema(BaseModel):
    id: str
    content: str
    category: str
    importance: float
    created_at: datetime.datetime
    metadata: Optional[Dict] = None

    class Config:
        from_attributes = True

class NoteCreateSchema(BaseModel):
    title: str
    content: str
    tags: Optional[List[str]] = None

class NoteResponseSchema(BaseModel):
    id: str
    title: str
    content: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    tags: List[str] = []

    class Config:
        from_attributes = True


# --- REST API Endpoints ---

@router.post("/", response_model=MemoryResponseSchema)
async def create_memory_entry(payload: MemoryCreateSchema, db: Session = Depends(get_db)):
    """Create a new semantic memory entry."""
    try:
        memory = memory_service.create_memory(
            db=db,
            content=payload.content,
            category=payload.category,
            metadata=payload.metadata
        )
        return MemoryResponseSchema(
            id=memory.id,
            content=memory.content,
            category=memory.category,
            importance=memory.importance,
            created_at=memory.created_at,
            metadata=memory.metadata_dict
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create memory: {str(e)}")


@router.get("/", response_model=List[MemoryResponseSchema])
async def list_memories(
    category: Optional[str] = None, 
    limit: int = 50, 
    db: Session = Depends(get_db)
):
    """Retrieve list of indexed memory entries."""
    query = db.query(MemoryEntry)
    if category:
        query = query.filter(MemoryEntry.category == category)
    memories = query.order_by(MemoryEntry.created_at.desc()).limit(limit).all()
    
    return [
        MemoryResponseSchema(
            id=m.id,
            content=m.content,
            category=m.category,
            importance=m.importance,
            created_at=m.created_at,
            metadata=m.metadata_dict
        ) for m in memories
    ]


@router.get("/search", response_model=List[MemoryResponseSchema])
async def search_memories(
    query: str = Query(..., description="Query string for semantic search"),
    category: Optional[str] = None,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Semantic search query across vector index and database memories."""
    try:
        results = retrieval_service.retrieve_similar_memories(
            db=db,
            query=query,
            limit=limit,
            category=category
        )
        return [
            MemoryResponseSchema(
                id=m.id,
                content=m.content,
                category=m.category,
                importance=m.importance,
                created_at=m.created_at,
                metadata=m.metadata_dict
            ) for m in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search query failed: {str(e)}")


@router.put("/{memory_id}", response_model=MemoryResponseSchema)
async def update_memory_entry(memory_id: str, payload: MemoryCreateSchema, db: Session = Depends(get_db)):
    """Update content and index settings of a specific memory."""
    memory = memory_service.update_memory(db=db, memory_id=memory_id, new_content=payload.content)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory entry not found.")
        
    return MemoryResponseSchema(
        id=memory.id,
        content=memory.content,
        category=memory.category,
        importance=memory.importance,
        created_at=memory.created_at,
        metadata=memory.metadata_dict
    )


@router.delete("/{memory_id}")
async def delete_memory_entry(memory_id: str, db: Session = Depends(get_db)):
    """Delete a memory from backend databases."""
    success = memory_service.delete_memory(db=db, memory_id=memory_id)
    if not success:
        raise HTTPException(status_code=404, detail="Memory entry not found.")
    return {"status": "success", "message": "Memory deleted successfully."}


# --- Notes Management ---

@router.post("/notes", response_model=NoteResponseSchema)
async def create_note(payload: NoteCreateSchema, db: Session = Depends(get_db)):
    """Create a new note with optional tags."""
    note = Note(title=payload.title, content=payload.content)
    
    # Process Tags
    if payload.tags:
        for tag_name in payload.tags:
            tag = db.query(Tag).filter(Tag.name == tag_name.lower()).first()
            if not tag:
                tag = Tag(name=tag_name.lower())
                db.add(tag)
            note.tags.append(tag)
            
    db.add(note)
    db.commit()
    db.refresh(note)
    
    # Save a copy of the note to semantic memory for search vector indexing
    memory_service.create_memory(
        db=db,
        content=f"Note: {note.title}\nContent: {note.content}",
        category="note",
        metadata={"note_id": note.id}
    )
    
    return NoteResponseSchema(
        id=note.id,
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
        tags=[t.name for t in note.tags]
    )


@router.get("/notes", response_model=List[NoteResponseSchema])
async def list_notes(db: Session = Depends(get_db)):
    """List all notes in database."""
    notes = db.query(Note).order_by(Note.created_at.desc()).all()
    return [
        NoteResponseSchema(
            id=n.id,
            title=n.title,
            content=n.content,
            created_at=n.created_at,
            updated_at=n.updated_at,
            tags=[t.name for t in n.tags]
        ) for n in notes
    ]


# --- Document Import ---

@router.post("/import-document")
async def import_document(
    filename: str = Query(..., description="Document filename"),
    filepath: Optional[str] = Query(None, description="Local document filepath"),
    db: Session = Depends(get_db),
    file: UploadFile = File(...)
):
    """Upload and import document text into SQL and VectorDB search indexes."""
    try:
        content_bytes = await file.read()
        content = content_bytes.decode("utf-8", errors="ignore")
        
        doc = Document(
            filename=filename,
            filepath=filepath,
            content=content,
            mime_type=file.content_type
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        # Segment text into smaller sections and write to vector memory
        # Very large text blocks are split to maintain semantic density
        chunks = [content[i:i+1000] for i in range(0, len(content), 800)]
        for idx, chunk in enumerate(chunks):
            memory_service.create_memory(
                db=db,
                content=f"Document chunk ({filename} - Part {idx+1}):\n{chunk}",
                category="document",
                metadata={"document_id": doc.id, "part": idx+1}
            )
            
        return {"status": "success", "document_id": doc.id, "chunks_indexed": len(chunks)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document import failed: {str(e)}")


# --- Conversation History ---

@router.get("/conversations")
async def list_conversations(db: Session = Depends(get_db)):
    """Get active conversation threads list."""
    threads = db.query(Conversation).order_by(Conversation.created_at.desc()).all()
    return [{"id": t.id, "title": t.title, "created_at": t.created_at} for t in threads]


@router.get("/conversations/{conversation_id}/messages")
async def list_messages(conversation_id: str, db: Session = Depends(get_db)):
    """Retrieve messages matching a conversation thread."""
    messages = db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.timestamp.asc()).all()
    return [
        {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "type": m.message_type,
            "timestamp": m.timestamp
        } for m in messages
    ]
