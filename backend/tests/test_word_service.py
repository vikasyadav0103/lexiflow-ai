import pytest

from app.services.ml_service import MLService
from app.services.word_service import process_dictionary_response


def test_process_dictionary_response_extracts_definitions_examples_and_synonyms():
    payload = [
        {
            "word": "bright",
            "phonetic": "/braɪt/",
            "phonetics": [{"text": "/braɪt/"}],
            "meanings": [
                {
                    "partOfSpeech": "adjective",
                    "synonyms": ["clever"],
                    "definitions": [
                        {
                            "definition": "Giving out or reflecting much light.",
                            "example": "A bright room.",
                            "synonyms": ["radiant"],
                        },
                        {"definition": "Intelligent and quick-witted."},
                    ],
                }
            ],
        }
    ]

    result = process_dictionary_response(payload)

    assert result["meanings"] == [
        "Giving out or reflecting much light.",
        "Intelligent and quick-witted.",
    ]
    assert result["context_examples"] == ["A bright room."]
    assert result["similar_words"] == ["clever", "radiant"]
    assert result["phonetics"] == "/braɪt/"
    assert result["source"] == "Dictionary API"
    assert result["sentiment"]["label"] == "UNAVAILABLE"
    assert result["word_vector"] == []


def test_process_dictionary_response_handles_empty_payload():
    result = process_dictionary_response([])

    assert result["meanings"] == []
    assert result["similar_words"] == []
    assert result["context_examples"] == []
    assert result["phonetics"] == ""
    assert result["word_vector"] == []


def test_ml_service_stays_lazy_and_does_not_fake_sentiment():
    service = MLService()

    assert service._initialized is False
    sentiment = service.get_sentiment("excellent")

    assert sentiment["label"] == "UNAVAILABLE"
    assert sentiment["score"] is None
