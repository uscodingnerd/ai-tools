const API_BASE = process.env.REACT_APP_API_URL;

export async function searchMovies(query) {
  if (!query.trim()) return [];
  const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error(`Search failed (${res.status})`);
  const data = await res.json();
  return data.results;
}
