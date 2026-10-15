import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)


class MLService:
    """Lazily initialized text embedding service.

    Model libraries are imported only if an embedding is requested, so the
    dictionary API does not need to load PyTorch/Transformers at startup.

    Sentiment is deliberately unavailable until a fine-tuned classifier is
    configured. An untrained BERT classification head is not a valid sentiment
    model.
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
        if not hasattr(self, "_model_name"):
            self._model_name = os.getenv(
                "LEXIFLOW_EMBEDDING_MODEL", "bert-base-uncased"
            )
            self._tokenizer = None
            self._model = None
            self._torch = None
            self._device: Any = None

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
            try:
                import torch
                from transformers import AutoModel, AutoTokenizer

                local_only = os.getenv(
                    "LEXIFLOW_LOCAL_MODELS_ONLY", "false"
                ).lower() == "true"
                tokenizer = AutoTokenizer.from_pretrained(
                    self._model_name,
                    local_files_only=local_only,
                )
                model = AutoModel.from_pretrained(
                    self._model_name,
                    local_files_only=local_only,
                )
                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model.to(device)
                model.eval()

                self._torch = torch
                self._device = device
                self._tokenizer = tokenizer
                self._model = model
                logger.info(
                    "Loaded embedding model %s on %s",
                    self._model_name,
                    self._device,
                )
            except Exception:
                logger.exception("Unable to initialize embedding model %s", self._model_name)
                raise

    def get_word_embedding(self, text: str) -> list[float] | None:
        """Return a mean-pooled contextual embedding as plain Python numbers."""
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
            inputs = {
                key: value.to(self._device)
                for key, value in inputs.items()
            }
            with self._torch.inference_mode():
                outputs = self._model(**inputs)
                hidden = outputs.last_hidden_state
                mask = inputs.get("attention_mask")
                if mask is not None:
                    mask = mask.unsqueeze(-1).to(hidden.dtype)
                    pooled = (
                        (hidden * mask).sum(dim=1)
                        / mask.sum(dim=1).clamp(min=1)
                    )
                else:
                    pooled = hidden.mean(dim=1)

            return pooled[0].detach().cpu().tolist()
        except Exception:
            logger.exception("Embedding generation failed")
            return None

    def get_bert_embeddings(self, text: str) -> list[float]:
        """Compatibility method returning a five-value embedding preview."""
        embedding = self.get_word_embedding(text)
        return embedding[:5] if embedding is not None else []

    def get_sentiment(self, text: str) -> dict:
        """Report unavailable until a fine-tuned sentiment classifier is set up."""
        return {
            "label": "UNAVAILABLE",
            "score": None,
            "reason": "No fine-tuned sentiment model is configured.",
        }

    def get_tf_analysis(self, text: str) -> list[float]:
        """Compatibility method; the prior random/untrained TF output is removed."""
        return []

    def get_similar_words(self, word: str, n: int = 5) -> list[str]:
        """Requires a semantic index/corpus; not implemented yet."""
        return []
