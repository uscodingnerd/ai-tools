import React, { useState } from "react";

export default function SearchBar({ onSearch }) {
  const [value, setValue] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(value.trim());
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", gap: 8 }}>
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Search movies by title..."
        style={{
          flex: 1,
          padding: "10px 14px",
          fontSize: 16,
          borderRadius: 6,
          border: "1px solid #ccc",
        }}
      />
      <button
        type="submit"
        style={{
          padding: "10px 20px",
          fontSize: 16,
          borderRadius: 6,
          border: "none",
          background: "#2563eb",
          color: "#fff",
          cursor: "pointer",
        }}
      >
        Search
      </button>
    </form>
  );
}
