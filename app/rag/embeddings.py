import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

_model = None
_model_name: Optional[str] = None


def _load_model(model_name: str):
    global _model, _model_name
    if _model is not None and _model_name == model_name:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model: {model_name}")
        _model = SentenceTransformer(model_name)
        _model_name = model_name
        logger.info("Embedding model loaded.")
        return _model
    except Exception as e:
        logger.error(f"Failed to load embedding model {model_name}: {e}")
        raise


def embed_texts(texts: list[str], model_name: str) -> list[list[float]]:
    """Embed a list of texts, returns list of float vectors."""
    model = _load_model(model_name)
    vectors = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
    return vectors.tolist()


def embed_query(query: str, model_name: str) -> list[float]:
    """Embed a single query string."""
    return embed_texts([query], model_name)[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))
