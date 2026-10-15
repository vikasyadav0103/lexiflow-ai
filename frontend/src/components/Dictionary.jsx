import { useState } from 'react';
import { searchWord } from '../api/api';
import SearchResults from './SearchResults';
import './Dictionary.css';

const Dictionary = () => {
  const [word, setWord] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [meaningsFound, setMeaningsFound] = useState(true);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!word.trim()) return;

    setLoading(true);
    setError(null);
    setMeaningsFound(true);
    try {
      const data = await searchWord(word);
      setResult(data);

      if (!data.meanings || data.meanings.length === 0) {
        setMeaningsFound(false);
      } else {

      }
    } catch (err) {
      setError(err.message || 'Failed to search for this word. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="dictionary-container">
      <div className="search-container">
        <form onSubmit={handleSubmit} className="search-form">
          <input
            type="text"
            value={word}
            onChange={(e) => setWord(e.target.value)}
            placeholder="Enter a word..."
            className="search-input"
            disabled={loading}
          />
          <button 
            type="submit" 
            className={`search-button ${loading ? 'loading' : ''}`}
            disabled={loading || !word.trim()}
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      {error && (
        <div className="error-container">
          <p className="error-message">{error}</p>
        </div>
      )}

      {loading && (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Searching for "{word}"...</p>
        </div>
      )}

      {result && !loading && (
        <>
          <SearchResults word={word} result={result} />
          {!meaningsFound && result.meanings && result.meanings.length === 0 && (
            <div className="no-meanings-message">
              No meanings found for this word.
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default Dictionary;
