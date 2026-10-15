import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import api from './api/index';
import SearchResults from './components/SearchResults';
import Dictionary from './components/Dictionary';
import SearchHistory from './components/SearchHistory';
import SearchHistoryWithCounts from './components/SearchHistoryWithCounts';
import VoiceSearch from './components/VoiceSearch';
import DownloadHistory from './components/DownloadHistory';
import './App.css';
import { searchWord } from './api/api';
import Navbar from './components/Navbar';
import WordAnalysis from './components/WordAnalysis';
import { ThemeProvider } from './context/ThemeContext';

function App() {
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchHistory, setSearchHistory] = useState([]);
  const [result, setResult] = useState(null);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchTerm.trim()) return;

    setLoading(true);
    setError(null);
    try {
      const data = await searchWord(searchTerm);
      console.log('API Response:', data);
      setResult(data);
      setSearchResults(data);
      updateSearchHistory(searchTerm);
    } catch (err) {
      setError(err.detail || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setSearchTerm(e.target.value);
    if (error) setError(null);
  };

  const updateSearchHistory = (newWord) => {
    setSearchHistory((prevHistory) => [...prevHistory, newWord]);
  };

  const handleVoiceSearch = async (query) => {
    const response = await fetch(`/api/search?query=${query}`);
    const data = await response.json();
    setResult(data);
    setSearchResults(data);
    updateSearchHistory(query);
  };

  return (
    <ThemeProvider>
      <Router>
        <div className="app-container">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dictionary updateSearchHistory={updateSearchHistory} />} />
              <Route path="/analysis" element={<WordAnalysis />} />
              <Route path="/history" element={<SearchHistory />} />
              <Route path="/frequency" element={<SearchHistoryWithCounts />} />
            </Routes>
          </main>
          <footer className="app-footer">
            <p>© 2024 AI Dictionary. All rights reserved.</p>
          </footer>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
