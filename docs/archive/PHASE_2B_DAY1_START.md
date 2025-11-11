# Phase 2B Day 1: Embedding Generation - Started

**Date**: November 11, 2025, 10:30 AM EST  
**Status**: Dependencies installed, ready to implement  
**Timeline**: Day 1-2 of 10-day Phase 2B

---

## ✅ **Dependencies Installed**

### **Core Embeddings Stack**
```bash
✓ openai 2.7.2       # OpenAI embeddings API
✓ pgvector 0.x       # PostgreSQL vector extension client  
✓ numpy 2.2.6        # Numerical operations
✓ scipy 1.15.3       # Similarity calculations
```

### **Updated pyproject.toml**
Added new `[embeddings]` optional dependency group:
```toml
embeddings = [
    "openai>=1.0.0",
    "pgvector>=0.2.0",
    "numpy>=1.24.0",
    "scipy>=1.10.0",
]
```

Install with: `pip install -e '.[embeddings]'`

---

## ⚠️ **Known Issues**

### **sentence-transformers Dependency Conflict**
- `transformers` package has import errors
- Cannot import `PreTrainedModel` 
- Local embeddings temporarily disabled
- Will add later after resolving conflicts

**Strategy**: Start with OpenAI embeddings, add local later

---

## 🎯 **Implementation Plan - Day 1**

### **Phase 1: Core Architecture** (2-3 hours)

#### **1.1 Create Module Structure**
```
whitemagic/
├── embeddings/
│   ├── __init__.py         # Public API
│   ├── base.py             # Abstract base provider
│   ├── openai_provider.py  # OpenAI embeddings
│   ├── local_provider.py   # Local embeddings (stub for now)
│   └── config.py           # Configuration management
```

#### **1.2 Base Provider Interface**
```python
# whitemagic/embeddings/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Embedding dimensions."""
        pass
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier."""
        pass
```

#### **1.3 OpenAI Provider Implementation**
```python
# whitemagic/embeddings/openai_provider.py
from .base import EmbeddingProvider
from openai import AsyncOpenAI

class OpenAIEmbeddings(EmbeddingProvider):
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        dimensions: int = 1536
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self._dimensions = dimensions
    
    async def embed(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        response = await self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [item.embedding for item in response.data]
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    @property
    def model_name(self) -> str:
        return self.model
```

#### **1.4 Configuration Management**
```python
# whitemagic/embeddings/config.py
from typing import Optional
from pydantic import BaseModel, Field

class EmbeddingConfig(BaseModel):
    provider: str = Field(default="openai", description="Provider: 'openai' or 'local'")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model: str = Field(default="text-embedding-3-small", description="Model name")
    dimensions: int = Field(default=1536, description="Embedding dimensions")
    batch_size: int = Field(default=100, description="Batch processing size")
    
    @classmethod
    def from_env(cls) -> "EmbeddingConfig":
        """Load configuration from environment variables."""
        import os
        return cls(
            provider=os.getenv("WM_EMBEDDING_PROVIDER", "openai"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("WM_EMBEDDING_MODEL", "text-embedding-3-small"),
            dimensions=int(os.getenv("WM_EMBEDDING_DIMENSIONS", "1536")),
            batch_size=int(os.getenv("WM_EMBEDDING_BATCH_SIZE", "100"))
        )
```

#### **1.5 Public API**
```python
# whitemagic/embeddings/__init__.py
from .base import EmbeddingProvider
from .openai_provider import OpenAIEmbeddings
from .config import EmbeddingConfig

def get_embedding_provider(config: EmbeddingConfig) -> EmbeddingProvider:
    """Factory function to get embedding provider."""
    if config.provider == "openai":
        if not config.openai_api_key:
            raise ValueError("OpenAI API key required")
        return OpenAIEmbeddings(
            api_key=config.openai_api_key,
            model=config.model,
            dimensions=config.dimensions
        )
    elif config.provider == "local":
        raise NotImplementedError("Local embeddings not yet implemented")
    else:
        raise ValueError(f"Unknown provider: {config.provider}")

__all__ = [
    "EmbeddingProvider",
    "OpenAIEmbeddings",
    "EmbeddingConfig",
    "get_embedding_provider"
]
```

---

## 📋 **Day 1 Checklist**

### **Morning** (Done)
- [x] Install dependencies (openai, pgvector, numpy, scipy)
- [x] Update pyproject.toml
- [x] Document dependency issues

### **Afternoon** (Next)
- [ ] Create embeddings module structure
- [ ] Implement base provider interface
- [ ] Implement OpenAI provider
- [ ] Add configuration management
- [ ] Write unit tests
- [ ] Test embedding generation

### **Evening** (If time)
- [ ] Add error handling and retries
- [ ] Add rate limiting
- [ ] Add cost tracking
- [ ] Document API usage

---

## 🎯 **Success Criteria for Day 1**

1. ✅ Dependencies installed
2. ⏳ Module structure created
3. ⏳ Base provider interface defined
4. ⏳ OpenAI provider working
5. ⏳ Configuration from environment
6. ⏳ Basic tests passing
7. ⏳ Can generate embeddings via API

---

## 📝 **Notes**

### **Design Decisions**
- **Async-first**: All embedding operations are async
- **Provider pattern**: Easy to add new providers
- **Pydantic config**: Type-safe configuration
- **Environment-driven**: Config from env vars
- **Batch support**: Efficient bulk operations

### **Cost Considerations**
- OpenAI text-embedding-3-small: $0.02 per 1M tokens
- Average memory ~100 tokens = $0.000002 per memory
- 10,000 memories = ~$0.02
- Very affordable at scale

### **Next Steps (Day 2)**
- Database schema for embeddings table
- pgvector setup and migrations
- Auto-embedding on memory create/update
- Batch migration script for existing memories

---

**Status**: ✅ **READY TO IMPLEMENT**

Let's build the embedding service! 🚀
