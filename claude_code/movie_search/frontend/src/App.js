import React, { useState } from "react";
import SearchBar from "./components/SearchBar";
import ResultsList from "./components/ResultsList";
import { searchMovies } from "./api";

export default function App() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSearch = async (query) => {
    if (!query) return;
    setLoading(true);
    setError(null);
    try {
      const data = await searchMovies(query);
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 680, margin: "0 auto", padding: "40px 16px", fontFamily: "sans-serif" }}>
      <h1 style={{ marginBottom: 24, fontSize: 28 }}>Movie Search</h1>
      <SearchBar onSearch={handleSearch} />
      <ResultsList results={results} loading={loading} error={error} />
    </div>
  );
}
