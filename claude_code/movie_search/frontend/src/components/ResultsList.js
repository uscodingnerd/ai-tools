import React from "react";

function runtime(secs) {
  if (!secs) return null;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function ResultsList({ results, loading, error }) {
  if (loading) return <p style={{ color: "#666", marginTop: 24 }}>Searching...</p>;
  if (error)   return <p style={{ color: "#dc2626", marginTop: 24 }}>Error: {error}</p>;
  if (!results) return null;
  if (results.length === 0) return <p style={{ color: "#666", marginTop: 24 }}>No results found.</p>;

  return (
    <ul style={{ listStyle: "none", padding: 0, marginTop: 24 }}>
      {results.map((movie, i) => (
        <li
          key={i}
          style={{
            display: "flex",
            gap: 16,
            padding: 16,
            marginBottom: 12,
            borderRadius: 8,
            border: "1px solid #e5e7eb",
            background: "#fff",
          }}
        >
          {movie.image_url && (
            <img
              src={movie.image_url}
              alt={movie.title}
              style={{ width: 80, objectFit: "cover", borderRadius: 4, flexShrink: 0 }}
            />
          )}
          <div style={{ flex: 1 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
              <strong style={{ fontSize: 18 }}>{movie.title}</strong>
              {movie.year && (
                <span style={{ color: "#888", fontSize: 14 }}>{movie.year}</span>
              )}
              {movie.rating && (
                <span style={{
                  background: "#fef9c3", color: "#92400e",
                  fontSize: 12, padding: "1px 6px", borderRadius: 4,
                }}>
                  ★ {movie.rating}
                </span>
              )}
              {runtime(movie.running_time_secs) && (
                <span style={{ color: "#888", fontSize: 13 }}>
                  {runtime(movie.running_time_secs)}
                </span>
              )}
            </div>

            {movie.genres && movie.genres.length > 0 && (
              <div style={{ marginTop: 4 }}>
                {movie.genres.map((g) => (
                  <span key={g} style={{
                    display: "inline-block", marginRight: 4,
                    background: "#eff6ff", color: "#1d4ed8",
                    fontSize: 11, padding: "1px 6px", borderRadius: 4,
                  }}>{g}</span>
                ))}
              </div>
            )}

            <p style={{ margin: "8px 0 4px", color: "#444", fontSize: 14 }}>{movie.plot}</p>

            {movie.actors && movie.actors.length > 0 && (
              <p style={{ margin: 0, color: "#666", fontSize: 13 }}>
                <strong>Cast:</strong> {movie.actors.join(", ")}
              </p>
            )}
            {movie.directors && movie.directors.length > 0 && (
              <p style={{ margin: "2px 0 0", color: "#666", fontSize: 13 }}>
                <strong>Director:</strong> {movie.directors.join(", ")}
              </p>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}
