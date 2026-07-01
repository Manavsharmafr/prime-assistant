from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

from app.models.conversation import Conversation, Message
from app.memory.semantic_memory import retrieval_service
from app.memory.semantic_memory import ContextBuilder

class ConversationManagerService:
    def get_or_create_conversation(self, db: Session, conversation_id: Optional[str] = None) -> Conversation:
        """Fetch existing conversation or create a new one if not found."""
        if conversation_id:
            convo = db.query(Conversation).filter(Conversation.id == conversation_id).first()
            if convo:
                return convo
        
        new_id = conversation_id or str(uuid.uuid4())
        convo = Conversation(id=new_id, title="New Conversation Thread", created_at=datetime.utcnow())
        db.add(convo)
        db.commit()
        db.refresh(convo)
        return convo

    def add_message(
        self,
        db: Session,
        conversation_id: str,
        sender: str,
        content: str,
        message_type: str = "text"
    ) -> Message:
        """Append a message to the conversation history thread."""
        convo = self.get_or_create_conversation(db, conversation_id)
        msg = Message(
            id=str(uuid.uuid4()),
            conversation_id=convo.id,
            sender=sender,
            content=content,
            message_type=message_type,
            timestamp=datetime.utcnow()
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    def build_prompt_with_context(
        self,
        db: Session,
        conversation_id: str,
        current_user_message: str,
        max_history_turns: int = 10
    ) -> str:
        """Construct the prompt payload incorporating historical messages and injected semantic memories."""
        # 1. Retrieve relevant memories semantically
        similar_memories = retrieval_service.retrieve_similar_memories(
            db=db,
            query=current_user_message,
            limit=4
        )
        memory_context = ContextBuilder.build_context(similar_memories)

        # 2. Get recent conversation turns
        messages = db.query(Message)\
            .filter(Message.conversation_id == conversation_id)\
            .order_by(Message.timestamp.desc())\
            .limit(max_history_turns * 2)\
            .all()
        
        # Reverse to get chronological order
        messages.reverse()

        history_lines = []
        for msg in messages:
            sender_label = "User" if msg.sender == "user" else "Assistant"
            history_lines.append(f"{sender_label}: {msg.content}")

        # Combine everything
        prompt_parts = []
        if memory_context:
            prompt_parts.append(memory_context)
            prompt_parts.append("\nNote: Use the context above to inform your answers if relevant.\n")

        if history_lines:
            prompt_parts.append("=== CONVERSATION HISTORY ===")
            prompt_parts.extend(history_lines)
            prompt_parts.append("============================\n")

        prompt_parts.append(f"User: {current_user_message}")
        prompt_parts.append("Assistant:")

        return "\n".join(prompt_parts)

conversation_manager = ConversationManagerService()
