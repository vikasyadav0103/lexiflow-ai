import logging
import os
import threading
from typing import Dict, List, Optional

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


class MLService:
    """Lazily initialized text embedding service.

    The original implementation used an untrained BERT classification head and
    reported its arbitrary logits as sentiment. Until a real fine-tuned
    sentiment checkpoint is configured, sentiment is reported as unavailable
    rather than fabricated.
    """

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialization_lock = threading.Lock()
        return cls._instance

    def __init__(self):
        # Model loading is lazy; API startup should not download multi-GB assets.
        if not hasattr(self, "_model_name"):
            self._model_name = os.getenv("LEXIFLOW_EMBEDDING_MODEL", "bert-base-uncased")
            self._tokenizer = None
            self._model = None
            self._device = torch.device(
                "cuda" if torch.cuda.is_available() else "cpu"
            )

    @property
    def _initialized(self) -> bool:
        return self._model is not None and self._tokenizer is not None

    def initialize_models(self) -> None:
        """Load the embedding model only when a feature requires it."""
        if self._initialized:
            return
        with self._initialization_lock:
            if self._initialized:
                return
            local_only = os.getenv("LEXIFLOW_LOCAL_MODELS_ONLY", "false").lower() == "true"
            try:
                tokenizer = AutoTokenizer.from_pretrained(
                    self._model_name,
                    local_files_only=local_only,
                )
                model = AutoModel.from_pretrained(
                    self._model_name,
                    local_files_only=local_only,
                )
                model.to(self._device)
                model.eval()
                self._tokenizer = tokenizer
                self._model = model
                logger.info("Loaded embedding model %s on %s", self._model_name, self._device)
            except Exception:
                logger.exception("Unable to load embedding model %s", self._model_name)
                raise

    def get_word_embedding(self, text: str) -> Optional[np.ndarray]:
        """Return a mean-pooled contextual embedding or None when unavailable."""
        if not text or not text.strip():
            return None
        try:
            self.initialize_models()
            inputs = self._tokenizer(
                text.strip(),
                return_tensors="pt",
                truncation=True,
                max_length=128,
            )
            inputs = {key: value.to(self._device) for key, value in inputs.items()}
            with torch.inference_mode():
                outputs = self._model(**inputs)
                mask = inputs.get("attention_mask")
                hidden = outputs.last_hidden_state
                if mask is not None:
                    mask = mask.unsqueeze(-1).to(hidden.dtype)
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
                else:
                    pooled = hidden.mean(dim=1)
            return pooled[0].detach().cpu().numpy()
        except Exception:
            logger.exception("Embedding generation failed")
            return None

    def get_bert_embeddings(self, text: str) -> List[float]:
        """Compatibility method returning a compact five-dimension preview."""
        embedding = self.get_word_embedding(text)
        return embedding.tolist()[:5] if embedding is not None else []

    def get_sentiment(self, text: str) -> Dict:
        """Sentiment is unavailable until a trained classifier is configured."""
        return {
            "label": "UNAVAILABLE",
            "score": None,
            "reason": "No fine-tuned sentiment model is configured.",
        }

    def get_tf_analysis(self, text: str) -> List[float]:
        """Compatibility method; an untrained TensorFlow model is not used."""
        return []

    def get_similar_words(self, word: str, n: int = 5) -> List[str]:
        """Similarity ranking requires a corpus/index; return empty until configured."""
        return []
