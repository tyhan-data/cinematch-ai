"""
Movie Recommendation API — FastAPI backend
Uses TF-IDF content-based filtering + TMDB for enriched metadata

This backend is optional for the Streamlit app above — the frontend
currently talks to TMDB directly. Wire it in (via API_BASE in app.py)
once you're ready to serve recommendations from your own trained model
instead of TMDB's generic "similar movies" endpoint.
"""

import os
import pickle
import numpy as np
import pandas as pd
import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Optional
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# ═════════════════════════════════════════════════════════════════════════
# STEP 1 — CONFIG
# ═════════════════════════════════════════════════════════════════════════
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w500"
PICKLE_DIR   = os.path.join(os.path.dirname(__file__), "model")

# ═════════════════════════════════════════════════════════════════════════
# STEP 2 — CREATE THE APP + CORS
# CORS is wide open (allow_origins=["*"]) so the Streamlit frontend can
# call this API from a different port during local dev. Lock this down
# to your actual frontend domain before deploying publicly.
# ═════════════════════════════════════════════════════════════════════════
app = FastAPI(
    title="🎬 CineMatch — Movie Recommendation API",
    description="Content-based movie recommendations powered by TF-IDF + TMDB",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═════════════════════════════════════════════════════════════════════════
# STEP 3 — LOAD THE TRAINED TF-IDF MODEL (if present)
# Expects four pickle files in ./model/: dataset.pkl, indices.pkl,
# tfidf.pkl, tfidf_matrix.pkl. If they're missing, the API still runs —
# /recommend just falls back to TMDB's "similar movies" endpoint instead
# of your own trained model. See get_content_recommendations() below.
# ═════════════════════════════════════════════════════════════════════════
def load_model():
    try:
        with open(os.path.join(PICKLE_DIR, "dataset.pkl"), "rb") as f:
            dataset = pickle.load(f)
        with open(os.path.join(PICKLE_DIR, "indices.pkl"), "rb") as f:
            indices = pickle.load(f)
        with open(os.path.join(PICKLE_DIR, "tfidf.pkl"), "rb") as f:
            tfidf = pickle.load(f)
        with open(os.path.join(PICKLE_DIR, "tfidf_matrix.pkl"), "rb") as f:
            tfidf_matrix = pickle.load(f)
        return dataset, indices, tfidf, tfidf_matrix
    except FileNotFoundError:
        return None, None, None, None


dataset, indices, tfidf, tfidf_matrix = load_model()

# ═════════════════════════════════════════════════════════════════════════
# STEP 4 — TMDB HELPERS
# Thin wrappers around the TMDB REST API used by the routes below.
# ═════════════════════════════════════════════════════════════════════════
def tmdb_search(title: str) -> Optional[dict]:
    """Search TMDB for a movie by title, return the first match (or None)."""
    r = requests.get(
        f"{TMDB_BASE}/search/movie",
        params={"api_key": TMDB_API_KEY, "query": title, "language": "en-US"},
        timeout=8,
    )
    if r.status_code != 200:
        return None
    results = r.json().get("results", [])
    return results[0] if results else None


def tmdb_details(movie_id: int) -> dict:
    """Get full TMDB movie details including credits (cast/director) and
    trailer, flattened into one convenient dict."""
    details = requests.get(
        f"{TMDB_BASE}/movie/{movie_id}",
        params={"api_key": TMDB_API_KEY, "language": "en-US"},
        timeout=8,
    ).json()

    credits = requests.get(
        f"{TMDB_BASE}/movie/{movie_id}/credits",
        params={"api_key": TMDB_API_KEY},
        timeout=8,
    ).json()

    videos = requests.get(
        f"{TMDB_BASE}/movie/{movie_id}/videos",
        params={"api_key": TMDB_API_KEY, "language": "en-US"},
        timeout=8,
    ).json()

    cast = [
        {
            "name": m["name"],
            "character": m["character"],
            "profile": f"{TMDB_IMG}{m['profile_path']}" if m.get("profile_path") else None,
        }
        for m in credits.get("cast", [])[:30]
    ]

    director = next(
        (c["name"] for c in credits.get("crew", []) if c["job"] == "Director"),
        "N/A",
    )

    trailer = next(
        (
            f"https://www.youtube.com/watch?v={v['key']}"
            for v in videos.get("results", [])
            if v.get("site") == "YouTube" and v.get("type") == "Trailer"
        ),
        None,
    )

    genres = [g["name"] for g in details.get("genres", [])]
    poster = f"{TMDB_IMG}{details['poster_path']}" if details.get("poster_path") else None
    backdrop = (
        f"https://image.tmdb.org/t/p/original{details['backdrop_path']}"
        if details.get("backdrop_path")
        else None
    )

    return {
        "id": movie_id,
        "title": details.get("title", ""),
        "overview": details.get("overview", ""),
        "poster": poster,
        "backdrop": backdrop,
        "rating": round(details.get("vote_average", 0), 1),
        "votes": details.get("vote_count", 0),
        "release_date": details.get("release_date", ""),
        "runtime": details.get("runtime"),
        "genres": genres,
        "tagline": details.get("tagline", ""),
        "director": director,
        "cast": cast,
        "trailer": trailer,
        "budget": details.get("budget", 0),
        "revenue": details.get("revenue", 0),
        "language": details.get("original_language", ""),
        "status": details.get("status", ""),
    }


def tmdb_popular(page: int = 1) -> List[dict]:
    """Fetch a page of currently popular movies from TMDB."""
    r = requests.get(
        f"{TMDB_BASE}/movie/popular",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "page": page},
        timeout=8,
    )
    if r.status_code != 200:
        return []
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "overview": m.get("overview", ""),
            "poster": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
            "rating": round(m.get("vote_average", 0), 1),
            "release_date": m.get("release_date", ""),
            "genre_ids": m.get("genre_ids", []),
        }
        for m in r.json().get("results", [])[:30]
    ]


# ═════════════════════════════════════════════════════════════════════════
# STEP 5 — CONTENT-BASED RECOMMENDATION LOGIC (your own TF-IDF model)
# ═════════════════════════════════════════════════════════════════════════
def get_content_recommendations(title: str, n: int = 30) -> List[str]:
    """Return the top-N most similar movie titles using cosine similarity
    over the TF-IDF matrix. Returns [] if the model isn't loaded or the
    title isn't found in the trained dataset."""
    if dataset is None or indices is None or tfidf_matrix is None:
        return []

    title_lower = title.lower().strip()
    title_map = {t.lower(): t for t in indices.index} if hasattr(indices, "index") else {}

    if title_lower not in title_map:
        return []

    original_title = title_map[title_lower]
    idx = indices[original_title]
    if isinstance(idx, pd.Series):
        idx = idx.iloc[0]

    sim_scores = cosine_similarity(tfidf_matrix[idx], tfidf_matrix).flatten()
    sim_scores[idx] = 0  # exclude the movie itself from its own recommendations
    top_indices = np.argsort(sim_scores)[::-1][:n]

    if isinstance(dataset, pd.DataFrame) and "title" in dataset.columns:
        return dataset.iloc[top_indices]["title"].tolist()
    return []


# ═════════════════════════════════════════════════════════════════════════
# STEP 6 — ROUTES
# ═════════════════════════════════════════════════════════════════════════
@app.get("/", tags=["Health"])
def root():
    """Simple health check / landing route."""
    return {"message": "🎬 CineMatch API is running!", "docs": "/docs"}


@app.get("/movie/{movie_id}", tags=["Movies"])
def get_movie(movie_id: int):
    """Get full details for a movie by TMDB ID."""
    try:
        return tmdb_details(movie_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search", tags=["Movies"])
def search_movie(q: str = Query(..., description="Movie title to search")):
    """Search for a movie by title and return its full details."""
    result = tmdb_search(q)
    if not result:
        raise HTTPException(status_code=404, detail="Movie not found")
    return tmdb_details(result["id"])


@app.get("/popular", tags=["Movies"])
def popular_movies(page: int = Query(1, ge=1, le=30)):
    """Get currently popular movies from TMDB."""
    return tmdb_popular(page)


@app.get("/recommend", tags=["Recommendations"])
def recommend(
    title: str = Query(..., description="Movie title for recommendations"),
    n: int = Query(30, ge=1, le=30, description="Number of recommendations"),
):
    """
    Get content-based movie recommendations for `title`.

    Tries your locally trained TF-IDF model first; if that model isn't
    loaded or doesn't know the title, falls back to TMDB's own
    "similar movies" endpoint so the route still returns useful results.
    """
    # 1. Try the local TF-IDF model.
    rec_titles = get_content_recommendations(title, n)
    if rec_titles:
        enriched = []
        for t in rec_titles:
            tmdb = tmdb_search(t)
            if tmdb:
                enriched.append({
                    "id": tmdb["id"],
                    "title": tmdb["title"],
                    "poster": f"{TMDB_IMG}{tmdb['poster_path']}" if tmdb.get("poster_path") else None,
                    "rating": round(tmdb.get("vote_average", 0), 1),
                    "release_date": tmdb.get("release_date", ""),
                    "overview": tmdb.get("overview", ""),
                })
        return {"source": "content-based", "recommendations": enriched}

    # 2. Fallback: TMDB's "similar" endpoint.
    base = tmdb_search(title)
    if not base:
        raise HTTPException(status_code=404, detail=f"Movie '{title}' not found")

    r = requests.get(
        f"{TMDB_BASE}/movie/{base['id']}/similar",
        params={"api_key": TMDB_API_KEY, "language": "en-US"},
        timeout=8,
    )
    similar = r.json().get("results", [])[:n]
    enriched = [
        {
            "id": m["id"],
            "title": m["title"],
            "poster": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
            "rating": round(m.get("vote_average", 0), 1),
            "release_date": m.get("release_date", ""),
            "overview": m.get("overview", ""),
        }
        for m in similar
    ]
    return {"source": "tmdb-similar", "recommendations": enriched}


@app.get("/trending", tags=["Movies"])
def trending(time_window: str = Query("week", enum=["day", "week"])):
    """Get trending movies (day or week window)."""
    r = requests.get(
        f"{TMDB_BASE}/trending/movie/{time_window}",
        params={"api_key": TMDB_API_KEY},
        timeout=8,
    )
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "overview": m.get("overview", ""),
            "poster": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
            "rating": round(m.get("vote_average", 0), 1),
            "release_date": m.get("release_date", ""),
        }
        for m in r.json().get("results", [])[:30]
    ]


@app.get("/genre/{genre_id}", tags=["Movies"])
def movies_by_genre(genre_id: int, page: int = Query(1, ge=1, le=5)):
    """Get movies for a given TMDB genre ID."""
    r = requests.get(
        f"{TMDB_BASE}/discover/movie",
        params={
            "api_key": TMDB_API_KEY,
            "with_genres": genre_id,
            "sort_by": "popularity.desc",
            "page": page,
            "language": "en-US",
        },
        timeout=8,
    )
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "overview": m.get("overview", ""),
            "poster": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
            "rating": round(m.get("vote_average", 0), 1),
            "release_date": m.get("release_date", ""),
        }
        for m in r.json().get("results", [])[:30]
    ]


@app.get("/genres", tags=["Movies"])
def get_genres():
    """Get all available TMDB genre IDs and names."""
    r = requests.get(
        f"{TMDB_BASE}/genre/movie/list",
        params={"api_key": TMDB_API_KEY, "language": "en-US"},
        timeout=8,
    )
    return r.json().get("genres", [])


@app.get("/top-rated", tags=["Movies"])
def top_rated(page: int = Query(1, ge=1, le=5)):
    """Get top-rated movies."""
    r = requests.get(
        f"{TMDB_BASE}/movie/top_rated",
        params={"api_key": TMDB_API_KEY, "language": "en-US", "page": page},
        timeout=8,
    )
    return [
        {
            "id": m["id"],
            "title": m["title"],
            "overview": m.get("overview", ""),
            "poster": f"{TMDB_IMG}{m['poster_path']}" if m.get("poster_path") else None,
            "rating": round(m.get("vote_average", 0), 1),
            "release_date": m.get("release_date", ""),
        }
        for m in r.json().get("results", [])[:30]
    ]


# ═════════════════════════════════════════════════════════════════════════
# STEP 7 — ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)