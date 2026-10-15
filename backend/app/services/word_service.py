import asyncio
import json
import logging
from typing import Dict, List, Tuple
from urllib.parse import quote

import aiohttp
import spacy
from fastapi import HTTPException
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
from sqlalchemy.orm import Session

from app.models.word import Word
from app.services.ml_service import MLService

logger = logging.getLogger(__name__)
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en"
_nlp = None
_lemmatizer = WordNetLemmatizer()
_ml_service = MLService()


def _get_nlp():
    """Load spaCy only when an NLP endpoint needs it."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError as exc:
            raise HTTPException(
                status_code=503,
                detail="NLP model is not installed. Run: python -m spacy download en_core_web_sm",
            ) from exc
    return _nlp


async def get_word_details(word: str) -> Dict:
    """Fetch a dictionary entry from the Free Dictionary API."""
    normalized = word.strip().lower()
    if not normalized:
        raise HTTPException(status_code=422, detail="Word must not be empty")

    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"{DICTIONARY_API_URL}/{quote(normalized, safe='')}"
            async with session.get(url) as response:
                if response.status == 404:
                    raise HTTPException(status_code=404, detail="Word not found")
                if response.status != 200:
                    logger.warning("Dictionary API returned HTTP %s", response.status)
                    raise HTTPException(status_code=503, detail="Dictionary provider is unavailable")
                payload = await response.json()
                if not isinstance(payload, list) or not payload:
                    raise HTTPException(status_code=404, detail="Word not found")
                return payload[0]
    except HTTPException:
        raise
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Dictionary API request failed: %s", exc)
        raise HTTPException(status_code=503, detail="Dictionary provider is unavailable") from exc


def process_dictionary_response(data: List[Dict]) -> Dict:
    meanings, examples, synonyms = [], [], set()
    for entry in data or []:
        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                definition_text = definition.get("definition")
                if definition_text:
                    meanings.append(definition_text)
                example = definition.get("example")
                if example:
                    examples.append(example)
            synonyms.update(meaning.get("synonyms", []))
    phonetics = next(
        (p.get("text", "") for e in (data or []) for p in e.get("phonetics", []) if p.get("text")),
        (data[0].get("phonetic", "") if data else ""),
    )
    return {
        "meanings": meanings[:5],
        "similar_words": sorted(synonyms)[:10],
        "context_examples": examples[:3],
        "phonetics": phonetics,
        "source": "Dictionary API",
        "sentiment": {
            "label": "UNAVAILABLE",
            "score": None,
            "reason": "No fine-tuned sentiment model is configured.",
        },
        "word_vector": [],
    }


async def get_meaning(word: str, db: Session) -> Dict:
    """Return cached or provider-backed dictionary data without model startup cost."""
    normalized = word.strip().lower()
    if not normalized:
        raise HTTPException(status_code=422, detail="Word must not be empty")

    cached = db.query(Word).filter(Word.text == normalized).first()
    if cached:
        def safe_json(value, fallback):
            try:
                return json.loads(value) if value else fallback
            except (TypeError, json.JSONDecodeError):
                return fallback

        # Older manual inserts stored a plain string instead of JSON-encoded definitions.
        meanings = safe_json(cached.meaning, [cached.meaning] if cached.meaning else [])
        embedding = safe_json(cached.bert_embedding, [])
        return {
            "word": normalized,
            "meanings": meanings if isinstance(meanings, list) else [str(meanings)],
            "sentiment": {
                "label": "UNAVAILABLE",
                "score": None,
                "reason": "No fine-tuned sentiment model is configured.",
            },
            "similar_words": safe_json(cached.similar_words, []),
            "context_examples": safe_json(cached.context_examples, []),
            "word_vector": embedding,
            "phonetics": cached.phonetics or "",
            "source": "cache",
        }

    try:
        details = await get_word_details(normalized)
        return {"word": normalized, **process_dictionary_response([details])}
    except HTTPException as exc:
        if exc.status_code == 503:
            logger.info("Dictionary provider unavailable; attempting WordNet fallback")
            return await get_fallback_meaning(normalized)
        if exc.status_code == 404:
            try:
                synsets = wordnet.synsets(normalized)
            except LookupError:
                synsets = []
            if synsets:
                return {
                    "word": normalized,
                    "meanings": [synset.definition() for synset in synsets[:3]],
                    "similar_words": sorted({
                        lemma.name().replace("_", " ")
                        for synset in synsets[:3] for lemma in synset.lemmas()
                    })[:10],
                    "context_examples": [
                        example for synset in synsets[:3] for example in synset.examples()
                    ][:3],
                    "phonetics": "",
                    "source": "WordNet",
                }
        raise


async def get_fallback_meaning(word: str) -> Dict:
    """Build a dictionary fallback from WordNet when the public API is unavailable."""
    normalized = word.strip().lower()
    try:
        synsets = wordnet.synsets(normalized)
    except LookupError:
        synsets = []
    return {
        "word": normalized,
        "meanings": [synset.definition() for synset in synsets[:3]] or ["No definition found"],
        "similar_words": sorted({
            lemma.name().replace("_", " ")
            for synset in synsets[:3] for lemma in synset.lemmas()
        })[:10],
        "context_examples": [example for synset in synsets[:3] for example in synset.examples()][:3],
        "phonetics": "",
        "source": "WordNet" if synsets else "fallback",
    }


def get_dictionary_meaning(word: str) -> List[str]:
    """Synchronous compatibility helper; prefer get_word_details in async routes."""
    import requests
    try:
        response = requests.get(
            f"{DICTIONARY_API_URL}/{quote(word.strip().lower(), safe='')}",
            timeout=10,
        )
        if response.status_code == 200:
            return process_dictionary_response(response.json()).get("meanings", [])
        return ["No meaning found"] if response.status_code == 404 else ["Dictionary provider unavailable"]
    except requests.RequestException:
        logger.exception("Dictionary provider request failed")
        return ["Dictionary provider unavailable"]


def analyze_sentiment(word: str) -> Dict:
    """Use the centralized ML service rather than initializing a duplicate model."""
    return _ml_service.get_sentiment(word)


def get_word_vector(word: str) -> List[float]:
    """Return an embedding preview from the centralized ML service."""
    embedding = _ml_service.get_word_embedding(word)
    return embedding[:5] if embedding is not None else []


def find_similar_words(word: str) -> List[str]:
    """Find related terms using WordNet without an extra network request."""
    normalized = word.strip().lower()
    try:
        synonyms = {
            lemma.name().replace("_", " ")
            for synset in wordnet.synsets(normalized)
            for lemma in synset.lemmas()
            if lemma.name().lower() != normalized
        }
        return sorted(synonyms)[:10]
    except LookupError:
        return []


async def generate_context(word: str) -> List[str]:
    """Return example sentences from the dictionary provider, when available."""
    try:
        details = await get_word_details(word)
        return process_dictionary_response([details]).get("context_examples", [])
    except HTTPException:
        return []


def pos_tagging(text: str) -> List[Tuple[str, str]]:
    return [(token.text, token.pos_) for token in _get_nlp()(text)]


def word_tokenization(text: str) -> List[str]:
    return word_tokenize(text)


def word_lemmatization(text: str) -> List[str]:
    return [token.lemma_ for token in _get_nlp()(text)]


def lemmatize_text(text: str) -> List[Tuple[str, str]]:
    return [(token.text, token.lemma_) for token in _get_nlp()(text)]


async def get_word_analysis(word: str) -> Dict:
    normalized = word.strip().lower()
    details = await get_word_details(normalized)
    return {
        "word": normalized,
        "meanings": process_dictionary_response([details]).get("meanings", []),
        "pos_tags": pos_tagging(normalized),
        "tokens": word_tokenization(normalized),
        "lemmas": lemmatize_text(normalized),
    }


async def initialize_ml_models():
    """Deprecated compatibility placeholder; MLService owns model initialization."""
    return _ml_service


async def get_advanced_analysis(word: str) -> Dict:
    """Return available model features without fabricating an untrained TF prediction."""
    normalized = word.strip().lower()
    basic = await get_word_analysis(normalized)
    embedding = _ml_service.get_word_embedding(normalized)
    return {
        **basic,
        "ml_analysis": {
            "sentiment": _ml_service.get_sentiment(normalized),
            "embedding_dimensions": int(len(embedding)) if embedding is not None else 0,
            "embedding_preview": embedding[:5] if embedding is not None else [],
            "note": "Embedding is a representation, not a dictionary definition or sentiment explanation.",
        },
    }


def translate_text(text: str, target_language: str = "hi"):
    """Translate text with googletrans; requires network access."""
    from googletrans import Translator
    return Translator().translate(text, dest=target_language).text


async def store_word_data(db: Session, word: str, word_data: dict) -> Word:
    """Insert or update a cached word, rolling back on persistence errors."""
    normalized = word.strip().lower()
    try:
        db_word = db.query(Word).filter(Word.text == normalized).first()
        values = {
            "text": normalized,
            "meaning": json.dumps(word_data.get("meanings", [])),
            "bert_embedding": json.dumps(word_data.get("word_vector", [])),
            "sentiment_score": word_data.get("sentiment", {}).get("score"),
            "similar_words": json.dumps(word_data.get("similar_words", [])),
            "context_examples": json.dumps(word_data.get("context_examples", [])),
            "phonetics": word_data.get("phonetics", ""),
        }
        if db_word is None:
            db_word = Word(**values)
            db.add(db_word)
        else:
            for key, value in values.items():
                setattr(db_word, key, value)
        db.commit()
        db.refresh(db_word)
        return db_word
    except Exception:
        db.rollback()
        logger.exception("Could not cache dictionary data for %s", normalized)
        raise


async def fetch_word_data(word: str) -> Dict:
    """Compatibility API used by older callers."""
    normalized = word.strip().lower()
    try:
        data = process_dictionary_response([await get_word_details(normalized)])
        embedding = _ml_service.get_word_embedding(normalized)
        return {
            **data,
            "word": normalized,
            "sentiment": _ml_service.get_sentiment(normalized),
            "word_vector": embedding if embedding is not None else [],
        }
    except HTTPException as exc:
        if exc.status_code == 404:
            fallback = await get_fallback_meaning(normalized)
            return {**fallback, "sentiment": {"label": "NEUTRAL", "score": 0.5}, "word_vector": []}
        raise


async def get_positive_words() -> List[Dict]:
    """Analyze a curated list, tolerating no model-specific extra capabilities."""
    positive_words = [
        "happy", "joy", "love", "peace", "wonderful", "excellent", "amazing",
        "beautiful", "success", "hope", "kindness", "gratitude", "courage", "inspire",
    ]
    result = []
    for word in positive_words:
        sentiment = _ml_service.get_sentiment(word)
        result.append({
            "word": word,
            "sentiment": sentiment,
            "similar_words": find_similar_words(word),
            "score": sentiment.get("score", 0.5),
        })
    result.sort(
        key=lambda item: item["score"] if isinstance(item["score"], (int, float)) else 0.5,
        reverse=True,
    )
    return result
