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
    """Fetch word details from the Free Dictionary API"""
    try:
        timeout = aiohttp.ClientTimeout(total=10)  # 10 seconds timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(DICTIONARY_API_URL.format(word=word)) as response:
                if response.status == 200:
                    data = await response.json()
                    return data[0]  # Returns first entry
                else:
                    error_data = await response.text()
                    logger.error(f"API Error: {error_data}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Word not found or API error"
                    )
    except aiohttp.ClientError as e:
        logger.error(f"Network error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

def process_dictionary_response(data: List[Dict]) -> Dict:
    """Process the dictionary API response"""
    try:
        if not data or not isinstance(data, list):
            return {
                "meanings": ["No definition found"],
                "similar_words": [],
                "context_examples": []
            }

        entry = data[0]
        meanings = []
        examples = []
        similar_words = set()

        for meaning in entry.get("meanings", []):
            for definition in meaning.get("definitions", []):
                if "definition" in definition:
                    meanings.append(definition["definition"])
                if "example" in definition:
                    examples.append(definition["example"])
            similar_words.update(meaning.get("synonyms", []))

        return {
            "meanings": meanings[:5],
            "similar_words": list(similar_words)[:5],
            "context_examples": examples[:3],
            "phonetics": entry.get("phonetic", ""),
            "source": "Dictionary API"
        }

    except Exception as e:
        logger.error(f"Error processing dictionary response: {str(e)}")
        return {
            "meanings": ["Error processing definition"],
            "similar_words": [],
            "context_examples": [],
            "error": str(e)
        }

async def get_meaning(word: str, db: Session) -> Dict:
    """Get word meaning with database caching"""
    try:
        # Check cache first
        db_word = db.query(Word).filter(Word.text == word.lower()).first()
        
        if db_word:
            # Return cached data
            return {
                "meanings": json.loads(db_word.meaning),
                "sentiment": {
                    "score": db_word.sentiment_score,
                    "label": "POSITIVE" if db_word.sentiment_score > 0.5 else "NEGATIVE"
                },
                "similar_words": json.loads(db_word.similar_words or '[]'),
                "context_examples": json.loads(db_word.context_examples or '[]'),
                "word_vector": json.loads(db_word.bert_embedding or '[]'),
                "phonetics": db_word.phonetics,
                "source": "cache"
            }
            
        # If not in cache, fetch from API
        word_data = await fetch_word_data(word)
        
        # Store in database
        await store_word_data(db, word, word_data)
        
        return word_data
        
    except Exception as e:
        logger.error(f"Error in get_meaning: {str(e)}")
        return await get_fallback_meaning(word)

async def get_fallback_meaning(word: str) -> Dict:
    """Fallback method for word meaning using WordNet"""
    try:
        synsets = wordnet.synsets(word)
        
        if synsets:
            meanings = []
            examples = []
            similar_words = set()
            
            for synset in synsets[:3]:  # Take top 3 synsets
                meanings.append(synset.definition())
                if synset.examples():
                    examples.extend(synset.examples()[:2])
                similar_words.update([lemma.name() for lemma in synset.lemmas()])
            
            return {
                "meanings": meanings,
                "similar_words": list(similar_words)[:5],
                "context_examples": examples[:3],
                "source": "WordNet"
            }
        
        return {
            "meanings": ["No definition found"],
            "similar_words": [],
            "context_examples": [],
            "source": "WordNet"
        }
        
    except Exception as e:
        logger.error(f"Fallback error for '{word}': {str(e)}")
        return {
            "meanings": ["Unable to fetch meaning"],
            "similar_words": [],
            "context_examples": [],
            "error": str(e)
        }

def get_dictionary_meaning(word: str) -> List[str]:
    """Get dictionary meanings"""
    try:
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            meanings = []
            
            for entry in data:
                for meaning in entry.get('meanings', []):
                    for definition in meaning.get('definitions', []):
                        if definition.get('definition'):
                            meanings.append(definition['definition'])
            
            return meanings if meanings else ["No meaning found"]
            
    except Exception as e:
        logger.error(f"Error fetching meaning: {str(e)}")
        return ["Unable to fetch meaning"]

def analyze_sentiment(word: str) -> Dict:
    """Analyze word sentiment using BERT"""
    try:
        result = sentiment_analyzer(word)[0]
        return {
            "label": result["label"],
            "score": float(result["score"])
        }
    except Exception as e:
        return {"error": str(e)}

def get_word_vector(word: str) -> List[float]:
    """Get word embedding using BERT"""
    try:
        inputs = tokenizer(word, return_tensors="pt", padding=True, truncation=True)
        with torch.no_grad():
            outputs = bert_model(**inputs)
        # Get the word embedding and convert to list
        word_vector = outputs.last_hidden_state.mean(dim=1).squeeze().tolist()
        # Return first 5 dimensions for readability
        return word_vector[:5] if isinstance(word_vector, list) else word_vector.tolist()[:5]
    except Exception as e:
        logger.error(f"Error getting word vector: {str(e)}")
        return [0.0] * 5

def find_similar_words(word: str) -> List[str]:
    """Find similar words using WordNet"""
    try:
        synonyms = set()
        for syn in wordnet.synsets(word):
            for lemma in syn.lemmas():
                if lemma.name() != word:
                    synonyms.add(lemma.name())
        
        # Get related words from dictionary API
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for entry in data:
                for meaning in entry.get('meanings', []):
                    synonyms.update(meaning.get('synonyms', []))
        
        return list(synonyms)[:5] if synonyms else [f"No similar words found for: {word}"]
    except Exception as e:
        logger.error(f"Error finding similar words: {str(e)}")
        return [f"Error finding similar words: {str(e)}"]

def generate_context(word: str) -> List[str]:
    """Generate example contexts using dictionary API and templates"""
    try:
        examples = []
        
        # Get examples from dictionary API
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word.lower()}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for entry in data:
                for meaning in entry.get('meanings', []):
                    for definition in meaning.get('definitions', []):
                        if definition.get('example'):
                            examples.append(definition['example'])
        
        # If no examples found, generate some
        if not examples:
            templates = [
                f"The {word} was used in this context.",
                f"Here's an example with '{word}'.",
                f"You might use '{word}' in a sentence like this."
            ]
            examples = templates
        
        return examples[:3]  # Return up to 3 examples
    except Exception as e:
        logger.error(f"Error generating context: {str(e)}")
        return [f"Error generating examples: {str(e)}"]

def pos_tagging(text: str) -> List[Tuple[str, str]]:
    """Get POS tags using spaCy"""
    doc = nlp(text)
    return [(token.text, token.pos_) for token in doc]

def word_tokenization(text: str) -> List[str]:
    """Perform word tokenization using NLTK."""
    tokens = word_tokenize(text)
    return tokens

def word_lemmatization(text: str) -> List[str]:
    """Perform lemmatization using spaCy."""
    doc = nlp(text)
    lemmas = [token.lemma_ for token in doc]
    return lemmas

def lemmatize_text(text: str) -> List[Tuple[str, str]]:
    """Perform lemmatization using both NLTK and spaCy"""
    # SpaCy lemmatization
    doc = nlp(text)
    spacy_lemmas = [(token.text, token.lemma_) for token in doc]
    
    # NLTK lemmatization
    words = word_tokenize(text)
    nltk_lemmas = [(word, lemmatizer.lemmatize(word)) for word in words]
    
    return list(set(spacy_lemmas + nltk_lemmas))

async def get_word_analysis(word: str) -> Dict:
    """Get complete word analysis including meanings, POS, tokens, and lemmas"""
    text = word.strip().lower()
    
    # Get word details asynchronously
    word_details = await get_word_details(text)
    
    return {
        "word": text,
        "meanings": word_details.get("meanings", []),
        "pos_tags": pos_tagging(text),
        "tokens": word_tokenization(text),
        "lemmas": lemmatize_text(text)
    }

# TensorFlow and PyTorch models for advanced processing
def initialize_ml_models():
    """Initialize TensorFlow and PyTorch models"""
    # TensorFlow text classification
    tf_model = tf.keras.Sequential([
        tf.keras.layers.Embedding(10000, 16),
        tf.keras.layers.GlobalAveragePooling1D(),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')
    ])
    
    # PyTorch transformer model
    tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    pt_model = AutoModelForSequenceClassification.from_pretrained("bert-base-uncased")
    
    return tf_model, pt_model, tokenizer

async def get_advanced_analysis(word: str) -> Dict:
    """Get advanced analysis using ML models"""
    try:
        # Get basic analysis
        basic_analysis = await get_word_analysis(word)
        
        # Get ML analysis
        bert_embeddings = ml_service.get_bert_embeddings(word)
        sentiment = ml_service.get_sentiment(word)
        tf_analysis = ml_service.get_tf_analysis(word)
        
        return {
            **basic_analysis,
            "ml_analysis": {
                "bert_embeddings": bert_embeddings,
                "sentiment": sentiment,
                "tf_features": tf_analysis
            }
        }
    except Exception as e:
        logger.error(f"Error in advanced analysis: {str(e)}")
        return {
            "error": str(e),
            "basic_analysis": basic_analysis
        }

def translate_text(text: str, target_language: str = "hi"):
    return translator.translate(text, dest=target_language).text

async def store_word_data(db: Session, word: str, word_data: dict) -> Word:
    """Store word data in database"""
    try:
        # Check if word exists
        db_word = db.query(Word).filter(Word.text == word.lower()).first()
        
        # Prepare word data
        word_dict = {
            'text': word.lower(),
            'meaning': json.dumps(word_data.get('meanings', [])),
            'bert_embedding': json.dumps(word_data.get('word_vector', [])),
            'sentiment_score': word_data.get('sentiment', {}).get('score'),
            'similar_words': json.dumps(word_data.get('similar_words', [])),
            'context_examples': json.dumps(word_data.get('context_examples', [])),
            'phonetics': word_data.get('phonetics', '')
        }
        
        if db_word:
            # Update existing word
            for key, value in word_dict.items():
                setattr(db_word, key, value)
        else:
            # Create new word
            db_word = Word(**word_dict)
            db.add(db_word)
            
        db.commit()
        db.refresh(db_word)
        return db_word
        
    except Exception as e:
        logger.error(f"Database error while storing word data: {str(e)}")
        db.rollback()
        raise

async def fetch_word_data(word: str) -> Dict:
    """Fetch word data from dictionary API and enrich with ML features"""
    try:
        # Initialize ML service
        ml_service = MLService()
        
        # Fetch from dictionary API
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{DICTIONARY_API_URL}/{word}") as response:
                if response.status == 200:
                    api_data = await response.json()
                    processed_data = process_dictionary_response(api_data)
                else:
                    # Use fallback if API fails
                    processed_data = await get_fallback_meaning(word)

        # Enrich with sentiment analysis
        sentiment = ml_service.get_sentiment(word)
        
        # Get word vector (BERT embedding)
        word_vector = ml_service.get_word_embedding(word)
        
        # Combine all data
        return {
            "meanings": processed_data.get("meanings", []),
            "similar_words": processed_data.get("similar_words", []),
            "context_examples": processed_data.get("context_examples", []),
            "phonetics": processed_data.get("phonetics", ""),
            "sentiment": sentiment,
            "word_vector": word_vector.tolist() if word_vector is not None else [],
            "source": processed_data.get("source", "combined")
        }
        
    except Exception as e:
        logger.error(f"Error fetching word data: {str(e)}")
        # Use fallback on error
        return await get_fallback_meaning(word)

async def get_positive_words() -> List[Dict]:
    """Get a list of positive words with their analysis"""
    try:
        # Common positive words
        positive_words = [
            "happy", "joy", "love", "peace", "wonderful",
            "excellent", "amazing", "beautiful", "success",
            "hope", "kindness", "gratitude", "courage", "inspire"
        ]
        
        ml_service = MLService()
        results = []
        
        for word in positive_words:
            try:
                # Get sentiment analysis
                sentiment = ml_service.get_sentiment(word)
                
                # Get word embedding
                embedding = ml_service.get_word_embedding(word)
                
                # Get similar words
                similar = ml_service.get_similar_words(word, n=3)
                
                results.append({
                    "word": word,
                    "sentiment": sentiment,
                    "similar_words": similar,
                    "score": sentiment.get("score", 0)
                })
                
            except Exception as word_error:
                logger.error(f"Error analyzing word {word}: {str(word_error)}")
                continue
        
        # Sort by sentiment score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results
        
    except Exception as e:
        logger.error(f"Error getting positive words: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error getting positive words: {str(e)}"
        )
