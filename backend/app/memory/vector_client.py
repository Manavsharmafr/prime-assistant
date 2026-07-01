from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import os
from app.core.config import settings

class VectorDBClientInterface(ABC):
    @abstractmethod
    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> bool:
        """Add text documents alongside metadatas and IDs to the vector database."""
        pass

    @abstractmethod
    def similarity_search_by_vector(self, query_embedding: List[float], k: int = 4) -> List[Dict[str, Any]]:
        """Return the top k documents similar to the query embedding."""
        pass

    @abstractmethod
    def delete_texts(self, ids: List[str]) -> bool:
        """Delete text documents by ID from the vector database."""
        pass

    @abstractmethod
    def reset(self) -> bool:
        """Clear all contents inside the index/collection."""
        pass


class ChromaDBClient(VectorDBClientInterface):
    def __init__(self, collection_name: str = "prime_memory"):
        self.collection_name = collection_name
        self.collection = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            # Setup local persistent database path
            persist_dir = os.path.join(settings.PRIME_WORKSPACE_PATH, "chroma_db")
            os.makedirs(persist_dir, exist_ok=True)
            
            # Initialize persistent client
            self.client = chromadb.PersistentClient(path=persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
        except ImportError:
            print("WARNING: chromadb package is not installed. ChromaDBClient will run in fallback simulation mode.")
            self.client = None
            self.collection = None
            self._simulation_storage: Dict[str, Dict[str, Any]] = {}

    def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> bool:
        if self.collection is not None:
            try:
                # We supply the raw embeddings separately from our embedding layer.
                # However, if we do not specify embeddings in collection.add, chromadb uses its default.
                # Since we want to use our custom EmbeddingService, we will store them.
                # The ChromaDB collection.add supports 'embeddings' argument!
                # Here we expect the metadatas to contain the embeddings or we will add them.
                embeddings = [m.pop("embedding", None) for m in metadatas]
                
                # Check if any embedding is missing. If so, let chromadb use its default model.
                if None in embeddings:
                    self.collection.add(
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                else:
                    self.collection.add(
                        embeddings=embeddings,
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                return True
            except Exception as e:
                print(f"ChromaDB add error: {str(e)}")
                return False
        else:
            # Fallback simulator storage
            for t, m, i in zip(texts, metadatas, ids):
                self._simulation_storage[i] = {"document": t, "metadata": m, "id": i}
            return True

    def similarity_search_by_vector(self, query_embedding: List[float], k: int = 4) -> List[Dict[str, Any]]:
        if self.collection is not None:
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k
                )
                
                documents = results.get("documents", [[]])[0]
                metadatas = results.get("metadatas", [[]])[0]
                ids = results.get("ids", [[]])[0]
                distances = results.get("distances", [[]])[0]
                
                formatted = []
                for doc, meta, id_val, dist in zip(documents, metadatas, ids, distances):
                    formatted.append({
                        "id": id_val,
                        "text": doc,
                        "metadata": meta,
                        "score": float(1.0 - dist)  # Convert distance to similarity score
                    })
                return formatted
            except Exception as e:
                print(f"ChromaDB search error: {str(e)}")
                return []
        else:
            # Simulated similarity search: performs keyword intersection scoring
            from app.memory.embeddings import _embedding_text_lookup
            query_text = _embedding_text_lookup.get(tuple(query_embedding), "").lower()
            
            results = []
            if query_text:
                query_words = {w for w in query_text.replace('.', '').replace(',', '').split() if len(w) > 2}
                for item in self._simulation_storage.values():
                    doc_text = item["document"].lower()
                    doc_words = {w for w in doc_text.replace('.', '').replace(',', '').split() if len(w) > 2}
                    
                    overlap = len(query_words.intersection(doc_words))
                    # Map to a simulated cosine similarity score [0.5, 0.9]
                    score = 0.5 + 0.4 * (overlap / len(query_words) if len(query_words) > 0 else 0)
                    results.append((item, score))
            else:
                for item in self._simulation_storage.values():
                    results.append((item, 0.5))
                    
            # Sort by simulated relevance score descending
            results.sort(key=lambda x: x[1], reverse=True)

            formatted = []
            for item, sim in results[:k]:
                formatted.append({
                    "id": item["id"],
                    "text": item["document"],
                    "metadata": item["metadata"],
                    "score": sim
                })
            return formatted

    def delete_texts(self, ids: List[str]) -> bool:
        if self.collection is not None:
            try:
                self.collection.delete(ids=ids)
                return True
            except Exception as e:
                print(f"ChromaDB delete error: {str(e)}")
                return False
        else:
            for i in ids:
                self._simulation_storage.pop(i, None)
            return True

    def reset(self) -> bool:
        if self.collection is not None:
            try:
                self.client.delete_collection(self.collection_name)
                self.collection = self.client.create_collection(self.collection_name)
                return True
            except Exception as e:
                print(f"ChromaDB reset error: {str(e)}")
                return False
        else:
            self._simulation_storage = {}
            return True


_vector_client_instance = None

# Factory to get swap-able client
def get_vector_db_client(collection_name: str = "prime_memory") -> VectorDBClientInterface:
    global _vector_client_instance
    if _vector_client_instance is None:
        _vector_client_instance = ChromaDBClient(collection_name)
    return _vector_client_instance
