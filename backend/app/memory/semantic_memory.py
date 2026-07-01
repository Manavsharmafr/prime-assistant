import json
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.memory import MemoryEntry, Tag, Note, Document, Task
from app.memory.embeddings import embedding_service
from app.memory.vector_client import get_vector_db_client

class MemoryRanker:
    @staticmethod
    def calculate_score(similarity: float, importance: float, age_hours: float) -> float:
        """Calculate final relevance score using hybrid ranking.
        Final = 0.5 * similarity + 0.3 * importance + 0.2 * recency_decay
        """
        # Recency decay: exponential decay over hours
        recency = 1.0 / (1.0 + (age_hours / 168.0))  # Halflife of 1 week (168 hours)
        return (0.5 * similarity) + (0.3 * importance) + (0.2 * recency)


class ContextBuilder:
    @staticmethod
    def build_context(memories: List[MemoryEntry]) -> str:
        """Construct a formatted text context block from retrieved memory entries."""
        if not memories:
            return ""

        context_lines = ["=== RETRIEVED CONTEXT MEMORIES ==="]
        
        # Group by category for cleaner context layout
        by_category = {}
        for m in memories:
            by_category.setdefault(m.category, []).append(m)

        for cat, items in by_category.items():
            context_lines.append(f"\n[{cat.upper()} MEMORIES]:")
            for idx, item in enumerate(items, 1):
                context_lines.append(f"  {idx}. {item.content} (Importance: {item.importance})")

        context_lines.append("\n==================================")
        return "\n".join(context_lines)


class MemoryService:
    def __init__(self):
        self.vector_client = get_vector_db_client()

    def detect_duplicate(self, db: Session, content: str) -> Optional[MemoryEntry]:
        """Simple duplicate check: looks for exact text matches in database."""
        return db.query(MemoryEntry).filter(MemoryEntry.content == content).first()

    def calculate_importance(self, content: str) -> float:
        """Heuristic importance scoring based on key phrases. Can be expanded to LLM scoring."""
        importance = 0.4  # Default baseline
        text = content.lower()
        
        # High importance signals
        high_signals = ["always", "never", "must", "important", "remember", "prefer", "key", "todo", "goal"]
        for signal in high_signals:
            if signal in text:
                importance += 0.15
        
        # Low importance signals
        low_signals = ["maybe", "temporary", "test", "simulated", "random"]
        for signal in low_signals:
            if signal in text:
                importance -= 0.1
                
        # Limit boundary to [0.1, 1.0]
        return max(0.1, min(1.0, importance))

    def create_memory(self, db: Session, content: str, category: str = "general", metadata: Optional[Dict] = None) -> MemoryEntry:
        """Create and index a new memory in both SQLite and ChromaDB."""
        # 1. Check duplicate
        duplicate = self.detect_duplicate(db, content)
        if duplicate:
            # Touch timestamp and return existing
            duplicate.created_at = datetime.datetime.utcnow()
            db.commit()
            return duplicate

        # 2. Score importance
        importance = self.calculate_importance(content)
        
        # 3. Save memory details in SQLite database
        memory = MemoryEntry(
            content=content,
            category=category,
            importance=importance
        )
        if metadata:
            memory.metadata_dict = metadata
        
        db.add(memory)
        db.commit()
        db.refresh(memory)

        # 4. Generate vector embedding and index in ChromaDB
        embedding = embedding_service.get_embedding(content)
        vector_id = f"vec_{memory.id}"
        
        # Combine database metadata
        vector_meta = {
            "category": category,
            "importance": importance,
            "created_at": memory.created_at.isoformat(),
            "embedding": embedding  # Injected for vector_client integration
        }
        if metadata:
            vector_meta.update(metadata)

        success = self.vector_client.add_texts(
            texts=[content],
            metadatas=[vector_meta],
            ids=[vector_id]
        )

        if success:
            memory.vector_id = vector_id
            db.commit()

        return memory

    def delete_memory(self, db: Session, memory_id: str) -> bool:
        """Delete a memory from SQLite and ChromaDB."""
        memory = db.query(MemoryEntry).filter(MemoryEntry.id == memory_id).first()
        if not memory:
            return False

        # Delete from ChromaDB
        if memory.vector_id:
            self.vector_client.delete_texts([memory.vector_id])

        # Delete from SQLite
        db.delete(memory)
        db.commit()
        return True

    def update_memory(self, db: Session, memory_id: str, new_content: str) -> Optional[MemoryEntry]:
        """Update the content of a memory in SQL and re-index vector embedding."""
        memory = db.query(MemoryEntry).filter(MemoryEntry.id == memory_id).first()
        if not memory:
            return None

        # Update SQL details
        memory.content = new_content
        memory.importance = self.calculate_importance(new_content)
        db.commit()

        # Update ChromaDB vector
        if memory.vector_id:
            embedding = embedding_service.get_embedding(new_content)
            vector_meta = {
                "category": memory.category,
                "importance": memory.importance,
                "created_at": memory.created_at.isoformat(),
                "embedding": embedding
            }
            # Add existing metadata
            vector_meta.update(memory.metadata_dict)

            # overwrite in vector store
            self.vector_client.add_texts(
                texts=[new_content],
                metadatas=[vector_meta],
                ids=[memory.vector_id]
            )

        return memory


class RetrievalService:
    def __init__(self):
        self.vector_client = get_vector_db_client()

    def retrieve_similar_memories(self, db: Session, query: str, limit: int = 5, category: Optional[str] = None) -> List[MemoryEntry]:
        """Perform semantic search using hybrid ranking algorithm."""
        # 1. Create query embedding
        query_vector = embedding_service.get_embedding(query)
        
        # 2. Get matches from VectorDB
        matches = self.vector_client.similarity_search_by_vector(query_vector, k=limit * 2)
        
        # 3. Pull SQL DB records and score them
        ranked_memories = []
        now = datetime.datetime.utcnow()

        for match in matches:
            vector_id = match["id"]
            # Convert vector ID back to SQLite ID (vec_UUID -> UUID)
            sql_id = vector_id.replace("vec_", "")
            
            memory = db.query(MemoryEntry).filter(MemoryEntry.id == sql_id).first()
            if not memory:
                continue
                
            # Filter by category if specified
            if category and memory.category != category:
                continue

            similarity = match["score"]
            age_hours = (now - memory.created_at).total_seconds() / 3600.0
            
            # Hybrid relevance calculation
            final_score = MemoryRanker.calculate_score(similarity, memory.importance, age_hours)
            
            ranked_memories.append((memory, final_score))

        # Sort by final hybrid score descending
        ranked_memories.sort(key=lambda x: x[1], reverse=True)
        
        # Return top items
        return [item[0] for item in ranked_memories[:limit]]


# Default service instantiations
memory_service = MemoryService()
retrieval_service = RetrievalService()
