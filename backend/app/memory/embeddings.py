from abc import ABC, abstractmethod
from typing import List
import os
import hashlib
import numpy as np
import requests
from app.core.config import settings

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def get_embedding(self, text: str) -> List[float]:
        """Generate vector embedding for a single text string."""
        pass

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for a list of text strings."""
        return [self.get_embedding(t) for t in texts]


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.configured = True
        else:
            self.configured = False

    def get_embedding(self, text: str) -> List[float]:
        if not self.configured:
            raise ValueError("Gemini API Key not set.")
        import google.generativeai as genai
        # Gemini embedding dimension is 768
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result["embedding"]


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        if self.api_key:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self.configured = True
        else:
            self.configured = False

    def get_embedding(self, text: str) -> List[float]:
        if not self.configured:
            raise ValueError("OpenAI API Key not set.")
        # text-embedding-3-small dimension is 1536
        response = self.client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return response.data[0].embedding


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self):
        self.host = settings.OLLAMA_HOST
        self.model = settings.OLLAMA_MODEL

    def get_embedding(self, text: str) -> List[float]:
        try:
            url = f"{self.host}/api/embeddings"
            resp = requests.post(url, json={"model": self.model, "prompt": text}, timeout=10)
            if resp.status_code == 200:
                return resp.json()["embedding"]
            raise RuntimeError(f"Ollama returned status code: {resp.status_code}")
        except Exception as e:
            raise RuntimeError(f"Ollama connection error: {str(e)}")


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Local SentenceTransformer embedding provider (all-MiniLM-L6-v2) that operates offline."""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.configured = False
        self.model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
            self.configured = True
        except ImportError:
            # PyTorch or sentence-transformers is not available
            pass

    def get_embedding(self, text: str) -> List[float]:
        if not self.configured or self.model is None:
            raise ValueError("SentenceTransformers model is not loaded. Ensure PyTorch is installed.")
        embedding = self.model.encode(text)
        # Normalize the embedding to match cosine standard
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding.tolist()


class HeuristicOfflineEmbeddingProvider(BaseEmbeddingProvider):
    """Fallback offline embedding provider that produces deterministic mock embeddings.
    Avoids requiring a 500MB PyTorch dependency during initial test phases, while maintaining consistency.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def get_embedding(self, text: str) -> List[float]:
        # Generate a deterministic vector using hashlib
        # This is extremely useful for offline testing/verification
        sha256 = hashlib.sha256(text.encode('utf-8')).digest()
        # Seed generator with digest
        np.random.seed(int.from_bytes(sha256[:4], byteorder='big'))
        vector = np.random.uniform(-1.0, 1.0, self.dimension)
        # L2 Normalize the vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()


# Global lookup mapping for testing simulation lookup
_embedding_text_lookup = {}

class EmbeddingService:
    def __init__(self, provider_name: str = "offline"):
        self.provider_name = provider_name
        
        # Instantiate fallback options
        self.local_transformer = SentenceTransformerEmbeddingProvider()
        self.hash_fallback = HeuristicOfflineEmbeddingProvider()
        
        self.provider = self._select_provider(provider_name)

    def _select_provider(self, name: str) -> BaseEmbeddingProvider:
        name = name.lower()
        if name == "gemini":
            return GeminiEmbeddingProvider()
        elif name == "openai":
            return OpenAIEmbeddingProvider()
        elif name == "ollama":
            return OllamaEmbeddingProvider()
        else:
            # If offline, use local SentenceTransformer if installed, else fallback to hashlib
            if self.local_transformer.configured:
                print("Defaulting offline provider to local SentenceTransformers ('all-MiniLM-L6-v2')")
                return self.local_transformer
            return self.hash_fallback

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding, automatically cascading fallbacks on failure."""
        # 1. Try selected provider
        try:
            vector = self.provider.get_embedding(text)
            _embedding_text_lookup[tuple(vector)] = text
            return vector
        except Exception as e:
            print(f"Embedding generation with provider '{self.provider_name}' failed: {str(e)}")
            
        # 2. Try SentenceTransformer fallback
        if self.local_transformer.configured and self.provider != self.local_transformer:
            try:
                print("Attempting local SentenceTransformers fallback...")
                vector = self.local_transformer.get_embedding(text)
                _embedding_text_lookup[tuple(vector)] = text
                return vector
            except Exception as err:
                print(f"Local SentenceTransformers fallback failed: {str(err)}")
                
        # 3. Last resort hashlib fallback
        print("Falling back to hashlib-based offline hash representation (last resort)...")
        vector = self.hash_fallback.get_embedding(text)
        _embedding_text_lookup[tuple(vector)] = text
        return vector

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Get list of embeddings, automatically cascading fallbacks on failure."""
        vectors = []
        for text in texts:
            vectors.append(self.get_embedding(text))
        return vectors


# Default embedding service
embedding_service = EmbeddingService(provider_name="offline")
