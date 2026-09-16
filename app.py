"""
CineMatch — Streamlit Frontend
Premium movie recommendation UI powered by FastAPI + TMDB

This file is organised top-to-bottom in the order Streamlit actually
needs it: page config first, then CSS, then data-fetching helpers,
then small render helpers, then the page router at the bottom.
Every section below is labelled STEP N so you can trace exactly what
runs and when.
"""

import streamlit as st
import requests
from typing import Optional
from dotenv import load_dotenv
import os
import time

load_dotenv()

# ═════════════════════════════════════════════════════════════════════════
# STEP 1 — PAGE CONFIG
# Must be the very first Streamlit command in the whole script, before
# any other st.* call (including st.markdown for CSS). If you move the
# CSS injection above this, Streamlit will raise a StreamlitAPIException.
# ═════════════════════════════════════════════════════════════════════════
def configure_page() -> None:
    st.set_page_config(
        page_title="CineMatch",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",  # sidebar starts open
    )

configure_page()

# ═════════════════════════════════════════════════════════════════════════
# STEP 2 — CONFIG / CONSTANTS
# ═════════════════════════════════════════════════════════════════════════
TMDB_API_KEY = "https://cinematch-ai-02r3.onrender.com"
TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORI = "https://image.tmdb.org/t/p/original"
API_BASE     = "http://localhost:8000"  # your FastAPI backend, if you wire it in
PLACEHOLDER  = "https://via.placeholder.com/300x450/1a1a26/555555?text=No+Poster"

if not TMDB_API_KEY:
    # Don't crash the app — just warn once, up top, so it's obvious why
    # posters/data aren't loading instead of silently showing empty grids.
    st.sidebar.warning("⚠️ TMDB_API_KEY is not set. Add it to your .env file.")

# ═════════════════════════════════════════════════════════════════════════
# STEP 3 — GLOBAL CSS
#
# THIS IS WHERE THE SIDEBAR BUG WAS.
#
# The original stylesheet had:
#     #MainMenu, footer, header { visibility: hidden; }
#
# Hiding `header` also hides Streamlit's built-in sidebar collapse/expand
# arrow, because that control physically lives inside the header element.
# The sidebar itself was never broken — its "open/close" button had just
# been made invisible, so once it was collapsed (narrow window, accidental
# click, mobile view) there was no visible way to bring it back.
#
# Fix: keep the header but make it transparent, and force its buttons
# (which include the sidebar toggle) to stay visible/opaque.
# ═════════════════════════════════════════════════════════════════════════
def load_css() -> None:
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;900&family=DM+Sans:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; color: #e2e2e2; }
.stApp { background: #0b0b0f; }

/* Hide the hamburger menu and default footer, but NOT the header — the
   header carries the sidebar's open/close arrow. We make it transparent
   instead so it blends in but keeps working. */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 3rem;
}
/* Belt-and-braces: explicitly force any button living in the header
   (this includes the sidebar collapse/expand control) to stay visible. */
header[data-testid="stHeader"] button {
    visibility: visible !important;
    opacity: 1 !important;
}
/* Streamlit versions differ on the exact test-id for the collapse arrow;
   covering both known variants so this keeps working after upgrades. */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseControl"] {
    visibility: visible !important;
    display: flex !important;
}

.block-container { padding-top: 1.5rem !important; padding-bottom: 2rem !important; }

[data-testid="stSidebar"] {
    background: #0f0f14 !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { font-family: 'DM Sans', sans-serif !important; }

.sb-logo { text-align: center; padding: 1.6rem 0 1.2rem; }
.sb-logo-mark {
    font-family: 'Outfit', sans-serif; font-size: 2rem; font-weight: 900;
    letter-spacing: 3px;
    background: linear-gradient(135deg, #ff2d55, #ff6b35);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sb-logo-sub { font-size: 0.72rem; color: #555; letter-spacing: 1.5px; text-transform: uppercase; margin-top: 3px; }
.sb-section { font-size: 0.65rem; letter-spacing: 1.8px; text-transform: uppercase; color: #444; padding: 1rem 0 0.4rem; font-weight: 600; }
.sb-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; padding: 0.9rem 1rem; margin-top: 0.6rem; font-size: 0.82rem; color: #aaa; line-height: 1.6; }
.sb-card-title { font-size: 0.78rem; font-weight: 700; color: #fff; margin-bottom: 6px; letter-spacing: 0.5px; }
.sb-chip { display: inline-block; background: rgba(255,45,85,0.12); border: 1px solid rgba(255,45,85,0.25); color: #ff6b7a; font-size: 0.68rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; margin: 2px 2px; }
.sb-link { display: block; color: #aaa; font-size: 0.8rem; text-decoration: none; padding: 4px 0; }
.sb-link:hover { color: #ff2d55; }

.hero-wrap { position: relative; width: 100%; min-height: 380px; border-radius: 20px; overflow: hidden; margin-bottom: 2.4rem; box-shadow: 0 30px 80px rgba(0,0,0,0.7); }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #0d0d14 0%, #1a0a1e 40%, #0d1520 100%); z-index: 0; }
.hero-gradient { position: absolute; inset: 0; background: linear-gradient(to right, rgba(0,0,0,0.92) 40%, rgba(0,0,0,0.3) 100%), linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 60%); z-index: 2; }
.hero-content { position: relative; z-index: 3; padding: 3rem 3rem 3rem; max-width: 600px; }
.hero-eyebrow { font-size: 0.72rem; letter-spacing: 3px; text-transform: uppercase; color: #ff2d55; font-weight: 700; margin-bottom: 1rem; }
.hero-title { font-family: 'Outfit', sans-serif; font-size: clamp(2rem, 4vw, 3.4rem); font-weight: 900; color: #ffffff; line-height: 1.1; margin: 0 0 0.8rem; letter-spacing: -0.5px; }
.hero-title span { background: linear-gradient(135deg, #ff2d55, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-sub { font-size: 1rem; color: #999; line-height: 1.6; max-width: 480px; margin-bottom: 2rem; }

.stTextInput > div > div > input {
    background: rgba(255,255,255,0.07) !important; color: white !important;
    border: 1.5px solid rgba(255,255,255,0.12) !important; border-radius: 14px !important;
    font-size: 1rem !important; padding: 0.75rem 1.1rem !important;
    font-family: 'DM Sans', sans-serif !important; transition: border-color 0.2s, box-shadow 0.2s !important;
}
.stTextInput > div > div > input::placeholder { color: #555 !important; }
.stTextInput > div > div > input:focus {
    border-color: rgba(255,45,85,0.6) !important;
    box-shadow: 0 0 0 4px rgba(255,45,85,0.1) !important;
    background: rgba(255,255,255,0.09) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #ff2d55, #c9002a) !important;
    color: white !important; border: none !important; border-radius: 12px !important;
    font-weight: 700 !important; font-family: 'DM Sans', sans-serif !important;
    font-size: 0.9rem !important; letter-spacing: 0.3px !important;
    padding: 0.6rem 1.4rem !important; transition: all 0.2s ease !important;
    box-shadow: 0 4px 20px rgba(255,45,85,0.3) !important;
}
.stButton > button:hover { transform: translateY(-1px) !important; box-shadow: 0 6px 28px rgba(255,45,85,0.45) !important; }
.stButton > button:active { transform: translateY(0) !important; }

.sec-hdr {
    font-family: 'Outfit', sans-serif; font-size: 1.25rem; font-weight: 800; color: #ffffff;
    display: flex; align-items: center; gap: 10px; margin: 2rem 0 1.2rem; letter-spacing: -0.2px;
}
.sec-hdr::before { content: ''; display: block; width: 4px; height: 1.2em; background: linear-gradient(to bottom, #ff2d55, #ff6b35); border-radius: 2px; flex-shrink: 0; }

.movie-card { background: #13131a; border: 1px solid rgba(255,255,255,0.07); border-radius: 16px; overflow: hidden; transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease; height: 100%; }
.movie-card:hover { transform: translateY(-5px); box-shadow: 0 20px 50px rgba(0,0,0,0.6); border-color: rgba(255,45,85,0.3); }
.movie-card-img-wrap { position: relative; overflow: hidden; aspect-ratio: 2/3; background: #1a1a26; }
.movie-card-img-wrap img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform 0.35s ease; }
.movie-card:hover .movie-card-img-wrap img { transform: scale(1.04); }
.movie-card-rating { position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.82); backdrop-filter: blur(6px); border: 1px solid rgba(255,200,50,0.3); border-radius: 8px; padding: 3px 8px; font-size: 0.72rem; font-weight: 700; color: #ffd700; }
.movie-card-body { padding: 0.8rem 0.9rem 0.85rem; }
.movie-card-title { font-family: 'Outfit', sans-serif; font-size: 0.88rem; font-weight: 700; color: #fff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 3px; }
.movie-card-meta { font-size: 0.72rem; color: #666; display: flex; gap: 6px; }
.movie-card-year { color: #888; }
.movie-card-lang { background: rgba(255,255,255,0.07); border-radius: 4px; padding: 0 5px; text-transform: uppercase; font-weight: 600; color: #777; }

.detail-hero { position: relative; width: 100%; height: clamp(280px, 40vw, 440px); border-radius: 20px; overflow: hidden; margin-bottom: 2rem; box-shadow: 0 25px 70px rgba(0,0,0,0.65); }
.detail-hero img.backdrop { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.4) saturate(0.8); }
.detail-hero-overlay { position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,0.97) 0%, rgba(0,0,0,0.3) 60%, transparent 100%), linear-gradient(to right, rgba(0,0,0,0.7) 0%, transparent 60%); }
.detail-hero-content { position: absolute; bottom: 0; left: 0; right: 0; padding: 2rem 2.5rem; }
.detail-title { font-family: 'Outfit', sans-serif; font-size: clamp(1.5rem, 3vw, 2.4rem); font-weight: 900; color: #fff; margin: 0 0 0.3rem; line-height: 1.15; text-shadow: 0 2px 12px rgba(0,0,0,0.8); }
.detail-tagline { font-size: 0.95rem; color: #e0c97a; font-style: italic; margin: 0 0 0.7rem; }
.detail-meta-row { display: flex; flex-wrap: wrap; gap: 0.6rem; align-items: center; }
.d-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 8px; font-size: 0.78rem; font-weight: 600; }
.d-badge-rating { background: linear-gradient(135deg, #f5a623, #d4880a); color: #000; }
.d-badge-info { background: rgba(255,255,255,0.1); backdrop-filter: blur(4px); color: #ccc; border: 1px solid rgba(255,255,255,0.12); }

.stat-row { display: flex; gap: 0.8rem; flex-wrap: wrap; margin: 1rem 0; }
.stat-box { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 0.9rem 1.1rem; text-align: center; flex: 1; min-width: 90px; }
.stat-val { font-family: 'Outfit', sans-serif; font-size: 1.4rem; font-weight: 900; color: #ff2d55; line-height: 1; }
.stat-lbl { font-size: 0.7rem; color: #666; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.8px; font-weight: 600; }

.gpill { display: inline-block; background: rgba(255,45,85,0.1); border: 1px solid rgba(255,45,85,0.25); color: #ff7a8a; font-size: 0.72rem; font-weight: 600; padding: 3px 10px; border-radius: 20px; margin: 2px 3px; letter-spacing: 0.2px; }

.cast-row { display: flex; gap: 0.8rem; overflow-x: auto; padding-bottom: 6px; margin-top: 0.5rem; }
.cast-item { text-align: center; min-width: 80px; max-width: 80px; flex-shrink: 0; }
.cast-item img { width: 72px; height: 72px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(255,45,85,0.35); display: block; margin: 0 auto; }
.cast-name { font-size: 0.68rem; font-weight: 700; color: #ddd; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cast-char { font-size: 0.62rem; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.overview-block { font-size: 0.95rem; line-height: 1.8; color: #bbb; background: rgba(255,255,255,0.03); border-left: 3px solid #ff2d55; padding: 1rem 1.3rem; border-radius: 0 12px 12px 0; }

.stTabs [data-baseweb="tab-list"] { background: transparent !important; gap: 4px; border-bottom: 1px solid rgba(255,255,255,0.07) !important; }
.stTabs [data-baseweb="tab"] { background: transparent !important; color: #666 !important; font-weight: 600 !important; font-family: 'DM Sans', sans-serif !important; font-size: 0.88rem !important; border-radius: 8px 8px 0 0 !important; padding: 0.5rem 1.1rem !important; transition: color 0.15s !important; }
.stTabs [aria-selected="true"] { color: #fff !important; border-bottom: 2px solid #ff2d55 !important; }
.stTabs [data-baseweb="tab"]:hover { color: #ccc !important; }

.empty-state { text-align: center; padding: 3rem 1rem; color: #555; }
.empty-state-icon { font-size: 2.5rem; margin-bottom: 0.7rem; }
.empty-state-msg { font-size: 0.95rem; line-height: 1.6; }

@keyframes shimmer { 0% { background-position: -600px 0; } 100% { background-position: 600px 0; } }
.skeleton { background: linear-gradient(90deg, #1a1a26 25%, #23232f 50%, #1a1a26 75%); background-size: 600px 100%; animation: shimmer 1.4s infinite linear; border-radius: 10px; }
.skel-poster { width: 100%; aspect-ratio: 2/3; border-radius: 12px; }
.skel-line { height: 12px; margin: 6px 0; }
.skel-line-short { width: 60%; }

.footer { text-align: center; padding: 2rem 1rem; margin-top: 4rem; border-top: 1px solid rgba(255,255,255,0.05); }
.footer-title { font-family: 'Outfit', sans-serif; font-weight: 900; font-size: 1rem; color: #fff; letter-spacing: 2px; }
.footer-sub { font-size: 0.78rem; color: #555; margin-top: 6px; }
.footer-dev { font-size: 0.8rem; margin-top: 10px; color: #666; }
.footer-dev span { background: linear-gradient(135deg, #ff2d55, #ff6b35); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 700; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,45,85,0.35); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,45,85,0.6); }
img { border: none !important; }
</style>
""", unsafe_allow_html=True)

load_css()

# ═════════════════════════════════════════════════════════════════════════
# STEP 4 — TMDB DATA-FETCHING HELPERS
# Every function here is wrapped in @st.cache_data so flipping tabs or
# revisiting a movie doesn't re-hit the TMDB API every single rerun
# (Streamlit reruns the whole script on every interaction).
# ═════════════════════════════════════════════════════════════════════════
def tmdb_get(endpoint: str, **params) -> dict:
    """Low-level GET against the TMDB API. Returns {} on any failure so
    callers never need to defensively check for None."""
    if not TMDB_API_KEY:
        return {}
    params["api_key"] = TMDB_API_KEY
    params["language"] = "en-US"
    try:
        r = requests.get(f"{TMDB_BASE}/{endpoint}", params=params, timeout=8)
        return r.json() if r.status_code == 200 else {}
    except requests.RequestException:
        return {}


@st.cache_data(ttl=600, show_spinner=False)
def fetch_popular(page: int = 1) -> list:
    return tmdb_get("movie/popular", page=page).get("results", [])[:20]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_trending(window: str = "week") -> list:
    return tmdb_get(f"trending/movie/{window}").get("results", [])[:20]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_rated(page: int = 1) -> list:
    return tmdb_get("movie/top_rated", page=page).get("results", [])[:20]


@st.cache_data(ttl=600, show_spinner=False)
def fetch_movie_details(movie_id: int) -> dict:
    details = tmdb_get(f"movie/{movie_id}")
    credits = tmdb_get(f"movie/{movie_id}/credits")
    videos  = tmdb_get(f"movie/{movie_id}/videos")

    cast = [
        {
            "name": m["name"],
            "character": m["character"],
            "profile": f"{TMDB_IMG}{m['profile_path']}" if m.get("profile_path") else None,
        }
        for m in credits.get("cast", [])[:20]
    ]
    director = next((c["name"] for c in credits.get("crew", []) if c["job"] == "Director"), "N/A")
    trailer = next(
        (
            f"https://www.youtube.com/watch?v={v['key']}"
            for v in videos.get("results", [])
            if v.get("site") == "YouTube" and v.get("type") == "Trailer"
        ),
        None,
    )

    return {
        "id": movie_id,
        "title": details.get("title", ""),
        "overview": details.get("overview", ""),
        "poster": f"{TMDB_IMG}{details['poster_path']}" if details.get("poster_path") else None,
        "backdrop": f"{TMDB_IMG_ORI}{details['backdrop_path']}" if details.get("backdrop_path") else None,
        "rating": round(details.get("vote_average", 0), 1),
        "votes": details.get("vote_count", 0),
        "release_date": details.get("release_date", ""),
        "runtime": details.get("runtime"),
        "genres": [g["name"] for g in details.get("genres", [])],
        "tagline": details.get("tagline", ""),
        "director": director,
        "cast": cast,
        "trailer": trailer,
        "budget": details.get("budget", 0),
        "revenue": details.get("revenue", 0),
        "language": details.get("original_language", "").upper(),
        "status": details.get("status", ""),
    }


@st.cache_data(ttl=600, show_spinner=False)
def fetch_recommendations(movie_id: int, n: int = 20) -> list:
    return tmdb_get(f"movie/{movie_id}/similar").get("results", [])[:n]


@st.cache_data(ttl=300, show_spinner=False)
def search_movies(query: str) -> list:
    return tmdb_get("search/movie", query=query).get("results", [])[:20]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_genres() -> list:
    return tmdb_get("genre/movie/list").get("genres", [])


@st.cache_data(ttl=600, show_spinner=False)
def fetch_by_genre(genre_id: int, page: int = 1) -> list:
    return tmdb_get("discover/movie", with_genres=genre_id, sort_by="popularity.desc", page=page).get("results", [])[:30]


# ═════════════════════════════════════════════════════════════════════════
# STEP 5 — FORMATTING HELPERS
# Small pure functions that turn raw TMDB numbers into display strings.
# ═════════════════════════════════════════════════════════════════════════
def format_runtime(minutes: Optional[int]) -> str:
    if not minutes:
        return "N/A"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def format_money(amount: int) -> str:
    if not amount:
        return "N/A"
    if amount >= 1_000_000_000:
        return f"${amount/1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount/1_000_000:.1f}M"
    return f"${amount:,}"


def poster_url(m: dict) -> str:
    p = m.get("poster_path") or m.get("poster") or ""
    if p and not p.startswith("http"):
        return f"{TMDB_IMG}{p}"
    return p or PLACEHOLDER


# ═════════════════════════════════════════════════════════════════════════
# STEP 6 — SESSION STATE
# Streamlit reruns the whole script top-to-bottom on every click/input.
# session_state is how we remember things (like "which movie is open")
# across those reruns.
# ═════════════════════════════════════════════════════════════════════════
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""


# ═════════════════════════════════════════════════════════════════════════
# STEP 7 — SMALL UI-BUILDING BLOCKS
# (skeleton loaders, section headers, the movie grid, etc.)
# ═════════════════════════════════════════════════════════════════════════
def render_skeleton_grid(count: int = 5):
    """Shimmering placeholder cards shown while data loads."""
    cols = st.columns(count)
    for col in cols:
        with col:
            st.markdown(
                '<div class="skeleton skel-poster"></div>'
                '<div class="skeleton skel-line" style="margin-top:8px"></div>'
                '<div class="skeleton skel-line skel-line-short"></div>',
                unsafe_allow_html=True,
            )


LOAD_MSGS = [
    "🔍 Searching the cinematic universe...",
    "🎞️ Analyzing story arcs and genres...",
    "🎭 Matching cast and directors...",
    "✨ Curating your personal picks...",
]


def show_loading_sequence(placeholder, duration: float = 1.5):
    """Cycles through fun status messages for `duration` seconds total."""
    step = duration / len(LOAD_MSGS)
    for msg in LOAD_MSGS:
        placeholder.markdown(
            f'<div style="color:#888;font-size:0.88rem;padding:0.5rem 0;text-align:center">{msg}</div>',
            unsafe_allow_html=True,
        )
        time.sleep(step)
    placeholder.empty()


def section_header(text: str):
    st.markdown(f'<div class="sec-hdr">{text}</div>', unsafe_allow_html=True)


def render_movie_grid(movies: list, cols_count: int = 5, prefix: str = "grid"):
    """Renders a responsive grid of movie-poster cards, each with a
    'Details' button that sets session_state.selected_movie and reruns
    the app into the detail view."""
    if not movies:
        st.markdown(
            '<div class="empty-state"><div class="empty-state-icon">🎬</div>'
            '<div class="empty-state-msg">No movies found.<br>Try a different search or category.</div></div>',
            unsafe_allow_html=True,
        )
        return

    cols = st.columns(cols_count, gap="small")
    for i, m in enumerate(movies):
        with cols[i % cols_count]:
            url    = poster_url(m)
            title  = m.get("title", "Untitled")
            rating = round(float(m.get("vote_average") or m.get("rating") or 0), 1)
            year   = (m.get("release_date") or "")[:4]
            lang   = (m.get("original_language") or "").upper()

            lang_html = f"<span class='movie-card-lang'>{lang}</span>" if lang else ""
            st.markdown(f"""
<div class="movie-card">
    <div class="movie-card-img-wrap">
        <img src="{url}" alt="{title}" loading="lazy" />
        <div class="movie-card-rating">⭐ {rating}</div>
    </div>
    <div class="movie-card-body">
        <div class="movie-card-title" title="{title}">{title}</div>
        <div class="movie-card-meta">
            <span class="movie-card-year">{year}</span>
            {lang_html}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

            if st.button("Details", key=f"{prefix}_{m.get('id','noid')}_{i}", use_container_width=True):
                st.session_state.selected_movie = m.get("id")
                st.rerun()


# ═════════════════════════════════════════════════════════════════════════
# STEP 8 — MOVIE DETAIL PAGE
# ═════════════════════════════════════════════════════════════════════════
def show_movie_detail(movie_id: int):
    load_ph = st.empty()
    show_loading_sequence(load_ph, duration=0.8)
    m = fetch_movie_details(movie_id)

    if not m or not m.get("title"):
        st.markdown(
            '<div class="empty-state"><div class="empty-state-icon">⚠️</div>'
            '<div class="empty-state-msg">Couldn\'t load this movie. Check your connection and try again.</div></div>',
            unsafe_allow_html=True,
        )
        return

    if st.button("← Back", key="back_btn"):
        st.session_state.selected_movie = None
        st.rerun()

    st.markdown("<div style='margin-top:1rem'></div>", unsafe_allow_html=True)

    if m.get("backdrop"):
        tagline_html = f"<div class='detail-tagline'>\"{m['tagline']}\"</div>" if m.get("tagline") else ""
        st.markdown(f"""
<div class="detail-hero">
    <img class="backdrop" src="{m['backdrop']}" alt="{m['title']}" />
    <div class="detail-hero-overlay"></div>
    <div class="detail-hero-content">
        <div class="detail-title">{m['title']}</div>
        {tagline_html}
        <div class="detail-meta-row">
            <span class="d-badge d-badge-rating">⭐ {m['rating']} / 10</span>
            <span class="d-badge d-badge-info">📅 {(m.get('release_date') or '')[:4]}</span>
            <span class="d-badge d-badge-info">⏱ {format_runtime(m.get('runtime'))}</span>
            <span class="d-badge d-badge-info">🌐 {m.get('language','')}</span>
            <span class="d-badge d-badge-info">🗳 {m.get('votes',0):,} votes</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    col_poster, col_info = st.columns([1, 2.5], gap="large")
    with col_poster:
        if m.get("poster"):
            st.image(m["poster"], use_container_width=True)
        else:
            st.markdown(
                '<div style="aspect-ratio:2/3;background:#1a1a26;border-radius:12px;'
                'display:flex;align-items:center;justify-content:center;font-size:3rem">🎬</div>',
                unsafe_allow_html=True,
            )
        st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
        if m.get("trailer"):
            st.link_button("▶ Watch Trailer", m["trailer"], use_container_width=True)
        st.link_button("↗ Open on TMDB", f"https://www.themoviedb.org/movie/{m['id']}", use_container_width=True)

    with col_info:
        if not m.get("backdrop"):
            st.markdown(
                f"<h1 style='font-family:Outfit,sans-serif;color:#fff;font-size:2rem;font-weight:900;margin:0'>{m['title']}</h1>",
                unsafe_allow_html=True,
            )
            if m.get("tagline"):
                st.markdown(f'<p style="color:#e0c97a;font-style:italic;margin-top:4px">"{m["tagline"]}"</p>', unsafe_allow_html=True)

        if m.get("genres"):
            st.markdown(" ".join(f'<span class="gpill">{g}</span>' for g in m["genres"]), unsafe_allow_html=True)

        st.markdown(f"""
<div class="stat-row">
    <div class="stat-box"><div class="stat-val">⭐ {m['rating']}</div><div class="stat-lbl">Rating</div></div>
    <div class="stat-box"><div class="stat-val">{format_runtime(m.get('runtime'))}</div><div class="stat-lbl">Runtime</div></div>
    <div class="stat-box"><div class="stat-val">{format_money(m.get('budget',0))}</div><div class="stat-lbl">Budget</div></div>
    <div class="stat-box"><div class="stat-val">{format_money(m.get('revenue',0))}</div><div class="stat-lbl">Revenue</div></div>
</div>
<div style="font-size:0.88rem;color:#aaa;line-height:2;margin-top:0.5rem">
    <span style="color:#666;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;font-weight:600">Director</span><br>
    <span style="color:#fff;font-weight:600">{m.get('director','N/A')}</span>
</div>
<div style="font-size:0.88rem;color:#aaa;line-height:2;margin-top:0.6rem">
    <span style="color:#666;font-size:0.72rem;text-transform:uppercase;letter-spacing:1px;font-weight:600">Status</span><br>
    <span style="color:#fff;font-weight:600">{m.get('status','N/A')}</span>
</div>
""", unsafe_allow_html=True)

    section_header("📖 Overview")
    st.markdown(f'<div class="overview-block">{m.get("overview","No description available.")}</div>', unsafe_allow_html=True)

    if m.get("cast"):
        section_header("🎭 Cast")
        cast_html = '<div class="cast-row">'
        for actor in m["cast"]:
            img = actor.get("profile") or "https://via.placeholder.com/72x72/1a1a26/555?text=?"
            cast_html += (
                f'<div class="cast-item"><img src="{img}" alt="{actor["name"]}" loading="lazy"/>'
                f'<div class="cast-name">{actor["name"]}</div>'
                f'<div class="cast-char">{actor.get("character","")}</div></div>'
            )
        cast_html += "</div>"
        st.markdown(cast_html, unsafe_allow_html=True)

    section_header("🎯 You May Also Like")
    load_ph2 = st.empty()
    show_loading_sequence(load_ph2, duration=0.5)
    recs = fetch_recommendations(movie_id, 20)
    if recs:
        render_movie_grid(recs, cols_count=5, prefix=f"rec_{movie_id}")
    else:
        st.markdown(
            '<div class="empty-state"><div class="empty-state-icon">🤔</div>'
            '<div class="empty-state-msg">No similar movies found right now.</div></div>',
            unsafe_allow_html=True,
        )


# ═════════════════════════════════════════════════════════════════════════
# STEP 9 — SIDEBAR
# This is the piece you reported as broken. Functionally nothing here
# changed — the real fix lives in the CSS (STEP 3). This function just
# builds the sidebar content and returns which nav item is selected.
# ═════════════════════════════════════════════════════════════════════════
def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("""
<div class="sb-logo">
    <div class="sb-logo-mark">CINEMATCH</div>
    <div class="sb-logo-sub">AI Movie Discovery</div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="sb-section">Navigation</div>', unsafe_allow_html=True)
        nav = st.radio(
            "nav",
            ["🏠  Home", "🔥  Trending", "⭐  Top Rated", "🎭  By Genre", "🔍  Search"],
            label_visibility="collapsed",
        )

        if st.session_state.selected_movie:
            st.markdown("<div style='margin-top:0.8rem'></div>", unsafe_allow_html=True)
            if st.button("← Back to Browse", use_container_width=True):
                st.session_state.selected_movie = None
                st.rerun()

        st.markdown("<div style='margin-top:1.6rem'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sb-section">About</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="sb-card">
    <div class="sb-card-title">🎬 How it works</div>
    Search for any movie. Our engine uses TF-IDF content-based filtering to find similar titles, enriched with live TMDB metadata.
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="sb-section">Tech Stack</div>', unsafe_allow_html=True)
        st.markdown("""
<div style="padding-top:4px">
    <span class="sb-chip">FastAPI</span>
    <span class="sb-chip">Streamlit</span>
    <span class="sb-chip">TF-IDF</span>
    <span class="sb-chip">Cosine Similarity</span>
    <span class="sb-chip">TMDB API</span>
    <span class="sb-chip">scikit-learn</span>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="sb-section">Developer</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="sb-card">
    <div class="sb-card-title">Mosairul Alam Tyhan</div>
    <a class="sb-link" href="https://github.com/tyhan-data" target="_blank">⌥ GitHub</a>
    <a class="sb-link" href="https://linkedin.com/in/mosairul-alam-tyhan" target="_blank">🔗 LinkedIn</a>
    <a class="sb-link" href="https://mat-red.vercel.app/" target="_blank">🌐 Portfolio</a>
</div>
""", unsafe_allow_html=True)

        # NOTE: a `position:fixed` footer inside the sidebar can visually
        # overlap the links above it if the sidebar content grows taller
        # than the viewport. Kept here as-is since it's cosmetic, but flag
        # it if you add more sidebar sections later.
        st.markdown(
            '<div style="position:fixed;bottom:1rem;left:0;width:260px;text-align:center;'
            'font-size:0.65rem;color:#333;letter-spacing:0.5px">CineMatch v2.0 · Powered by TMDB</div>',
            unsafe_allow_html=True,
        )

        return nav


# ═════════════════════════════════════════════════════════════════════════
# STEP 10 — FOOTER (main page area, not the sidebar)
# ═════════════════════════════════════════════════════════════════════════
def render_footer() -> None:
    st.markdown("""
<div class="footer">
    <div class="footer-title">CINEMATCH</div>
    <div class="footer-sub">Made with ❤️ using Python · FastAPI · Streamlit · TMDB · Machine Learning</div>
    <div class="footer-dev">Developed by <span>M.A.T</span></div>
    <div style="margin-top:12px;font-size:0.68rem;color:#333">
        This product uses the TMDB API but is not endorsed or certified by TMDB.
    </div>
</div>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════
# STEP 11 — ROUTER
# Reads which sidebar nav item is active and renders the matching page.
# If a movie is selected (session_state.selected_movie is set), the
# detail page takes over regardless of which nav tab is highlighted.
# ═════════════════════════════════════════════════════════════════════════
def main() -> None:
    nav = render_sidebar()

    if st.session_state.selected_movie:
        show_movie_detail(st.session_state.selected_movie)
        return

    if nav == "🏠  Home":
        st.markdown("""
<div class="hero-wrap">
    <div class="hero-bg"></div>
    <div class="hero-gradient"></div>
    <div class="hero-content">
        <div class="hero-eyebrow">🎬 AI-Powered Discovery</div>
        <h1 class="hero-title">Find your next<br><span>great film.</span></h1>      
</div>
""", unsafe_allow_html=True)

        search_col, btn_col = st.columns([5, 3])
        with search_col:
            query = st.text_input(
                "", placeholder="🔍  Try 'Inception', 'The Godfather', 'Parasite'...",
                label_visibility="collapsed", key="home_search_input",
            )
        with btn_col:
            search_btn = st.button("Search", use_container_width=True, key="home_search_btn")

        did_search = search_btn and query.strip()

        if did_search:
            load_ph = st.empty()
            show_loading_sequence(load_ph, duration=1.2)
            results = search_movies(query.strip())
            if results:
                section_header(f'🔍 Results for "{query}"')
                render_movie_grid(results, cols_count=5, prefix="home_search")
            else:
                st.markdown(
                    '<div class="empty-state"><div class="empty-state-icon">🔎</div>'
                    '<div class="empty-state-msg">No movies matched that title.<br>Check your spelling or try a different name.</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            tabs = st.tabs(["🔥Trending This Week", "🌟 Popular Now", "⭐ Top Rated"])
            with tabs[0]:
                render_skeleton_grid(6)
                trending = fetch_trending("week")
                render_movie_grid(trending, cols_count=5, prefix="home_trending")
            with tabs[1]:
                popular = fetch_popular()
                render_movie_grid(popular, cols_count=5, prefix="home_popular")
            with tabs[2]:
                top = fetch_top_rated()
                render_movie_grid(top, cols_count=5, prefix="home_toprated")

    elif nav == "🔥  Trending":
        section_header("🔥 Trending Movies")
        window = st.radio("Period", ["This Week", "Today"], horizontal=True, key="trend_window")
        tw = "week" if window == "This Week" else "day"
        movies = fetch_trending(tw)
        render_movie_grid(movies, cols_count=5, prefix=f"trending_{tw}")

    elif nav == "⭐  Top Rated":
        section_header("⭐ Top Rated Movies")
        page_num = st.selectbox("Page", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], key="toprated_page")
        movies = fetch_top_rated(page_num)
        render_movie_grid(movies, cols_count=5, prefix=f"toprated_p{page_num}")

    elif nav == "🎭  By Genre":
        section_header("🎭 Browse by Genre")
        genres = fetch_genres()
        if genres:
            genre_map = {g["name"]: g["id"] for g in genres}
            selected_genre = st.selectbox("Choose a genre", list(genre_map.keys()), key="genre_select")
            if selected_genre:
                movies = fetch_by_genre(genre_map[selected_genre])
                section_header(f"🎬 {selected_genre}")
                render_movie_grid(movies, cols_count=5, prefix=f"genre_{genre_map[selected_genre]}")
        else:
            st.markdown(
                '<div class="empty-state"><div class="empty-state-icon">⚠️</div>'
                '<div class="empty-state-msg">Could not load genres. Check your API connection.</div></div>',
                unsafe_allow_html=True,
            )

    elif nav == "🔍  Search":
        section_header("🔍 Search Movies")
        query = st.text_input("", placeholder="Enter a movie title...", label_visibility="collapsed", key="search_page_input")
        if query.strip():
            load_ph = st.empty()
            show_loading_sequence(load_ph, duration=1.0)
            results = search_movies(query.strip())
            if results:
                section_header(f'Found {len(results)} results for "{query}"')
                render_movie_grid(results, cols_count=5, prefix="search_results")
            else:
                st.markdown(
                    '<div class="empty-state"><div class="empty-state-icon">🔎</div>'
                    '<div class="empty-state-msg">No results found.<br>Try a different title or check your spelling.</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            section_header("Popular Right Now")
            movies = fetch_popular()
            render_movie_grid(movies, cols_count=5, prefix="search_popular")


# ═════════════════════════════════════════════════════════════════════════
# STEP 12 — ENTRY POINT
# ═════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
    render_footer()