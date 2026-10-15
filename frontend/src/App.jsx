import { BrowserRouter as Router, Route, Routes } from "react-router-dom";

import Dictionary from "./components/Dictionary";
import SearchHistory from "./components/SearchHistory";
import SearchHistoryWithCounts from "./components/SearchHistoryWithCounts";
import Navbar from "./components/Navbar";
import WordAnalysis from "./components/WordAnalysis";
import { ThemeProvider } from "./context/ThemeContext";
import "./App.css";

function App() {
  return (
    <ThemeProvider>
      <Router>
        <div className="app-container">
          <Navbar />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dictionary />} />
              <Route path="/analysis" element={<WordAnalysis />} />
              <Route path="/history" element={<SearchHistory />} />
              <Route path="/frequency" element={<SearchHistoryWithCounts />} />
            </Routes>
          </main>
          <footer className="app-footer">
            <p>© 2026 LexiFlow AI. All rights reserved.</p>
          </footer>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;
