import React, { useState, useEffect } from 'react';
import { getPositiveWords } from '../api/api';
import './PositiveWords.css';

const PositiveWords = () => {
    const [words, setWords] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        loadPositiveWords();
    }, []);

    const loadPositiveWords = async () => {
        try {
            setLoading(true);
            const data = await getPositiveWords();
            setWords(Array.isArray(data.words) ? data.words : []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="positive-words-container">
            <h2>Positive Words Analysis</h2>
            
            {loading && (
                <div className="loading-spinner">
                    <div className="spinner"></div>
                    <p>Loading positive words...</p>
                </div>
            )}

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {!loading && !error && (
                <div className="words-grid">
                    {words.map((item, index) => (
                        <div key={index} className="word-card" 
                             style={{
                                 '--sentiment-score': Number.isFinite(item.score) ? `${item.score * 100}%` : '0%'
                             }}>
                            <h3>{item.word}</h3>
                            <div className="sentiment-bar">
                                <div className="sentiment-fill"></div>
                                <span>{Number.isFinite(item.score) ? `${(item.score * 100).toFixed(1)}% Positive` : 'Sentiment model not configured'}</span>
                            </div>
                            {item.similar_words.length > 0 && (
                                <div className="similar-words">
                                    <h4>Similar Words:</h4>
                                    <div className="similar-tags">
                                        {item.similar_words.map((word, idx) => (
                                            <span key={idx} className="similar-tag">
                                                {word}
                                            </span>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PositiveWords; 