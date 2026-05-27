"""
CineMatch — Streamlit Frontend
Beautiful movie recommendation web app powered by FastAPI + TMDB
"""

import streamlit as st
import requests
from typing import Optional

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CineMatch 🎬",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Config ───────────────────────────────────────────────────────────────────

try:
    TMDB_API_KEY = st.secrets["TMDB_API_KEY"]
except Exception:
    st.error("⚠️ TMDB API key not found")
    st.stop()

TMDB_BASE    = "https://api.themoviedb.org/3"
TMDB_IMG     = "https://image.tmdb.org/t/p/w500"
TMDB_IMG_ORI = "https://image.tmdb.org/t/p/original"

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp {
    background: linear-gradient(135deg, #0d0d0d 0%, #1a1a2e 50%, #16213e 100%);
    color: #e8e8e8;
}
.hero-banner {
    position: relative; width: 100%; height: 420px;
    border-radius: 20px; overflow: hidden; margin-bottom: 2rem;
    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
}
.hero-backdrop { width: 100%; height: 100%; object-fit: cover; filter: brightness(0.45); }
.hero-content {
    position: absolute; bottom: 0; left: 0; right: 0;
    padding: 2rem 2.5rem;
    background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, transparent 100%);
}
.hero-title { font-size: 2.4rem; font-weight: 900; color: #ffffff; margin: 0 0 0.4rem 0; text-shadow: 0 2px 8px rgba(0,0,0,0.8); }
.hero-tagline { font-size: 1.1rem; color: #e0c97a; font-style: italic; margin: 0 0 0.8rem 0; }
.hero-meta { font-size: 0.9rem; color: #ccc; display: flex; gap: 1.2rem; flex-wrap: wrap; }
.rating-badge {
    display: inline-flex; align-items: center; gap: 4px;
    background: linear-gradient(135deg, #f5a623, #e8860a);
    color: #000; font-weight: 700; font-size: 0.85rem;
    padding: 3px 10px; border-radius: 20px;
}
.section-header {
    font-size: 1.4rem; font-weight: 800; color: #ffffff;
    border-left: 4px solid #e5091a; padding-left: 12px;
    margin: 1.5rem 0 1rem 0;
}
.cast-grid { display: flex; gap: 1rem; overflow-x: auto; padding-bottom: 8px; }
.cast-card { text-align: center; min-width: 90px; max-width: 90px; }
.cast-card img { width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2px solid rgba(229,9,20,0.5); }
.cast-name { font-size: 0.72rem; font-weight: 600; color: #ddd; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cast-char { font-size: 0.65rem; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.genre-pill {
    display: inline-block; background: rgba(229,9,20,0.15);
    border: 1px solid rgba(229,9,20,0.3); color: #ff6b7a;
    font-size: 0.75rem; font-weight: 600; padding: 3px 10px;
    border-radius: 20px; margin: 2px 3px;
}
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.08) !important; color: white !important;
    border: 1.5px solid rgba(255,255,255,0.15) !important;
    border-radius: 12px !important; font-size: 1rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #e5091a !important;
    box-shadow: 0 0 0 3px rgba(229,9,20,0.2) !important;
}
[data-testid="stSidebar"] { background: rgba(10,10,20,0.95) !important; border-right: 1px solid rgba(255,255,255,0.05); }
.stButton > button {
    background: linear-gradient(135deg, #e5091a, #b00714) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
    padding: 0.5rem 1.5rem !important; transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
.stTabs [data-baseweb="tab"] { color: #999 !important; font-weight: 600; }
.stTabs [aria-selected="true"] { color: #ffffff !important; border-bottom-color: #e5091a !important; }
.stat-box {
    background: rgba(255,255,255,0.05); border-radius: 12px;
    padding: 1rem 1.2rem; border: 1px solid rgba(255,255,255,0.08); text-align: center;
}
.stat-value { font-size: 1.6rem; font-weight: 900; color: #e5091a; }
.stat-label { font-size: 0.78rem; color: #888; margin-top: 2px; }
.overview-text {
    font-size: 0.95rem; line-height: 1.7; color: #ccc;
    background: rgba(255,255,255,0.03); border-left: 3px solid #e5091a;
    padding: 1rem 1.2rem; border-radius: 0 10px 10px 0;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: rgba(255,255,255,0.03); }
::-webkit-scrollbar-thumb { background: rgba(229,9,20,0.4); border-radius: 3px; }
img { border: none; }
</style>
""", unsafe_allow_html=True)


# ── TMDB helpers ─────────────────────────────────────────────────────────────
def tmdb_get(endpoint: str, **params) -> dict:
    params["api_key"] = TMDB_API_KEY
    params["language"] = "en-US"
    try:
        r = requests.get(f"{TMDB_BASE}/{endpoint}", params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        else:
            st.warning(f"TMDB API error {r.status_code}: {r.text[:100]}")
            return {}
    except Exception as e:
        st.error(f"Network error: {e}")
        return {}

def fetch_popular(page=1):
    return tmdb_get("movie/popular", page=page).get("results", [])[:20]



def fetch_trending(window="week"):
    return tmdb_get(f"trending/movie/{window}").get("results", [])[:20]

def fetch_top_rated(page=1):
    return tmdb_get("movie/top_rated", page=page).get("results", [])[:20]

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
        for m in credits.get("cast", [])[:8]
    ]
    director = next((c["name"] for c in credits.get("crew", []) if c["job"] == "Director"), "N/A")
    trailer  = next(
        (f"https://www.youtube.com/watch?v={v['key']}"
         for v in videos.get("results", [])
         if v.get("site") == "YouTube" and v.get("type") == "Trailer"),
        None,
    )
    return {
        "id": movie_id,
        "title": details.get("title", ""),
        "overview": details.get("overview", ""),
        "poster":   f"{TMDB_IMG}{details['poster_path']}"       if details.get("poster_path")   else None,
        "backdrop": f"{TMDB_IMG_ORI}{details['backdrop_path']}" if details.get("backdrop_path") else None,
        "rating":       round(details.get("vote_average", 0), 1),
        "votes":        details.get("vote_count", 0),
        "release_date": details.get("release_date", ""),
        "runtime":      details.get("runtime"),
        "genres":  [g["name"] for g in details.get("genres", [])],
        "tagline": details.get("tagline", ""),
        "director": director,
        "cast":    cast,
        "trailer": trailer,
        "budget":  details.get("budget", 0),
        "revenue": details.get("revenue", 0),
        "language": details.get("original_language", "").upper(),
        "status":   details.get("status", ""),
    }

def fetch_recommendations(movie_id: int, n=10):
    return tmdb_get(f"movie/{movie_id}/similar").get("results", [])[:n]

def search_movies(query: str):
    return tmdb_get("search/movie", query=query).get("results", [])[:10]

def fetch_genres():
    return tmdb_get("genre/movie/list").get("genres", [])

def fetch_by_genre(genre_id: int, page=1):
    return tmdb_get("discover/movie", with_genres=genre_id, sort_by="popularity.desc", page=page).get("results", [])[:20]


# ── Session state ─────────────────────────────────────────────────────────────
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "search_query" not in st.session_state:
    st.session_state.search_query = ""


# ── Helpers ───────────────────────────────────────────────────────────────────
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


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:1rem 0 1.5rem 0">
        <div style="font-size:2.5rem">🎬</div>
        <div style="font-size:1.5rem;font-weight:900;color:#fff;letter-spacing:2px">CineMatch</div>
        <div style="font-size:0.75rem;color:#888;margin-top:4px">Your AI Movie Guide</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    nav = st.radio("Navigate", ["🏠 Home", "🔥 Trending", "⭐ Top Rated", "🎭 By Genre", "🔍 Search"], label_visibility="collapsed")
    st.markdown("---")
    if st.session_state.selected_movie:
        if st.button("← Back", use_container_width=True):
            st.session_state.selected_movie = None
            st.rerun()
    st.markdown('<div style="position:fixed;bottom:1rem;left:0;width:260px;text-align:center;font-size:0.7rem;color:#444">Powered by TMDB & Streamlit</div>', unsafe_allow_html=True)


# ── Movie detail ──────────────────────────────────────────────────────────────
def show_movie_detail(movie_id: int):
    with st.spinner("Loading movie details..."):
        m = fetch_movie_details(movie_id)
    if not m or not m.get("title"):
        st.error("Could not load movie details.")
        return

    if m.get("backdrop"):
        st.markdown(f"""
        <div class="hero-banner">
            <img class="hero-backdrop" src="{m['backdrop']}" />
            <div class="hero-content">
                <div class="hero-title">{m['title']}</div>
                {"<div class='hero-tagline'>" + m['tagline'] + "</div>" if m.get('tagline') else ''}
                <div class="hero-meta">
                    <span class="rating-badge">⭐ {m['rating']} / 10</span>
                    <span>📅 {m.get('release_date','')[:4]}</span>
                    <span>⏱ {format_runtime(m.get('runtime'))}</span>
                    <span>🌐 {m.get('language','').upper()}</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    col_poster, col_info = st.columns([1, 2.5], gap="large")
    with col_poster:
        if m.get("poster"):
            st.image(m["poster"], use_container_width=True)
        if m.get("trailer"):
            st.link_button("▶ Watch Trailer", m["trailer"], use_container_width=True)

    with col_info:
        st.markdown(f"<h1 style='color:white;font-size:2rem;margin:0'>{m['title']}</h1>", unsafe_allow_html=True)
        if m.get("tagline"):
            st.markdown(f"<p style='color:#e0c97a;font-style:italic;font-size:1rem'>\"{m['tagline']}\"</p>", unsafe_allow_html=True)
        if m.get("genres"):
            genre_html = " ".join(f'<span class="genre-pill">{g}</span>' for g in m["genres"])
            st.markdown(genre_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        s1, s2, s3, s4 = st.columns(4)
        with s1: st.markdown(f'<div class="stat-box"><div class="stat-value">⭐ {m["rating"]}</div><div class="stat-label">Rating</div></div>', unsafe_allow_html=True)
        with s2: st.markdown(f'<div class="stat-box"><div class="stat-value">{format_runtime(m.get("runtime"))}</div><div class="stat-label">Runtime</div></div>', unsafe_allow_html=True)
        with s3: st.markdown(f'<div class="stat-box"><div class="stat-value">{format_money(m.get("budget",0))}</div><div class="stat-label">Budget</div></div>', unsafe_allow_html=True)
        with s4: st.markdown(f'<div class="stat-box"><div class="stat-value">{format_money(m.get("revenue",0))}</div><div class="stat-label">Revenue</div></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**🎬 Director:** {m.get('director','N/A')}")
        st.markdown(f"**📊 Votes:** {m.get('votes',0):,}")
        st.markdown(f"**📌 Status:** {m.get('status','N/A')}")

    st.markdown('<div class="section-header">📖 Overview</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="overview-text">{m.get("overview","No description available.")}</div>', unsafe_allow_html=True)

    if m.get("cast"):
        st.markdown('<div class="section-header">🎭 Cast</div>', unsafe_allow_html=True)
        cast_html = '<div class="cast-grid">'
        for actor in m["cast"]:
            img = actor["profile"] or "https://via.placeholder.com/80x80?text=?"
            cast_html += f'<div class="cast-card"><img src="{img}" alt="{actor["name"]}"/><div class="cast-name">{actor["name"]}</div><div class="cast-char">{actor.get("character","")}</div></div>'
        cast_html += "</div>"
        st.markdown(cast_html, unsafe_allow_html=True)

    st.markdown('<div class="section-header">🎯 You May Also Like</div>', unsafe_allow_html=True)
    with st.spinner("Finding recommendations..."):
        recs = fetch_recommendations(movie_id, 8)
    if recs:
        cols = st.columns(4)
        for i, rec in enumerate(recs[:8]):
            with cols[i % 4]:
                poster = rec.get("poster_path", "")
                poster_url = f"{TMDB_IMG}{poster}" if poster else "https://via.placeholder.com/300x450?text=No+Image"
                st.image(poster_url, use_container_width=True)
                st.caption(f"**{rec['title']}** ⭐{round(rec.get('vote_average',0),1)}")
                if st.button("Details", key=f"detail_rec_{movie_id}_{rec['id']}_{i}", use_container_width=True):
                    st.session_state.selected_movie = rec["id"]
                    st.rerun()


# ── Movie grid renderer ───────────────────────────────────────────────────────
def render_movie_grid(movies: list, cols_count: int = 5, prefix: str = "grid"):
    if not movies:
        st.info("No movies found.")
        return
    cols = st.columns(cols_count)
    for i, m in enumerate(movies):
        with cols[i % cols_count]:
            poster = m.get("poster_path") or m.get("poster") or ""
            if poster and not poster.startswith("http"):
                poster = f"{TMDB_IMG}{poster}"
            title  = m.get("title", "")
            rating = m.get("vote_average") or m.get("rating") or 0
            year   = (m.get("release_date") or "")[:4]

            if poster:
                st.image(poster, use_container_width=True)
            else:
                st.markdown('<div style="height:200px;background:#1a1a2e;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#555">🎬</div>', unsafe_allow_html=True)

            st.markdown(f"<div style='font-size:0.82rem;font-weight:700;color:#fff;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap' title='{title}'>{title}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size:0.75rem;color:#aaa'>⭐ {round(float(rating),1)} &nbsp;|&nbsp; {year}</div>", unsafe_allow_html=True)

            btn_key = f"{prefix}_{m.get('id', 'noid')}_{i}"
            if st.button("Details", key=btn_key, use_container_width=True):
                st.session_state.selected_movie = m.get("id")
                st.rerun()


# ── Router ────────────────────────────────────────────────────────────────────
if st.session_state.selected_movie:
    show_movie_detail(st.session_state.selected_movie)

else:
    if nav == "🏠 Home":
        st.markdown("""
        <div style="text-align:center;padding:2rem 0 1rem 0">
            <div style="font-size:3rem">🎬</div>
            <h1 style="font-size:2.8rem;font-weight:900;color:#fff;margin:0;letter-spacing:3px">CineMatch</h1>
            <p style="color:#888;font-size:1rem;margin-top:8px">Discover movies you'll love · Powered by AI</p>
        </div>
        """, unsafe_allow_html=True)

        search_col, btn_col = st.columns([4, 1])
        with search_col:
            query = st.text_input("", placeholder="🔍 Search for a movie...", label_visibility="collapsed")
        with btn_col:
            search_btn = st.button("Search", use_container_width=True)

        if search_btn and query:
            with st.spinner("Searching..."):
                results = search_movies(query)
            if results:
                st.markdown('<div class="section-header">🔍 Search Results</div>', unsafe_allow_html=True)
                render_movie_grid(results, cols_count=5, prefix="home_search")
            else:
                st.warning("No movies found for your search.")
        else:
            tabs = st.tabs(["🔥 Trending This Week", "🌟 Popular Now", "⭐ Top Rated"])
            with tabs[0]:
                with st.spinner("Loading trending movies..."):
                    trending = fetch_trending("week")
                render_movie_grid(trending, cols_count=5, prefix="home_trending")
            with tabs[1]:
                with st.spinner("Loading popular movies..."):
                    popular = fetch_popular()
                render_movie_grid(popular, cols_count=5, prefix="home_popular")
            with tabs[2]:
                with st.spinner("Loading top rated..."):
                    top = fetch_top_rated()
                render_movie_grid(top, cols_count=5, prefix="home_toprated")

    elif nav == "🔥 Trending":
        st.markdown('<h1 style="color:white">🔥 Trending Movies</h1>', unsafe_allow_html=True)
        window = st.radio("Period", ["This Week", "Today"], horizontal=True)
        tw = "week" if window == "This Week" else "day"
        with st.spinner("Loading..."):
            movies = fetch_trending(tw)
        render_movie_grid(movies, cols_count=5, prefix=f"trending_{tw}")

    elif nav == "⭐ Top Rated":
        st.markdown('<h1 style="color:white">⭐ Top Rated Movies</h1>', unsafe_allow_html=True)
        page_num = st.selectbox("Page", [1, 2, 3, 4, 5])
        with st.spinner("Loading..."):
            movies = fetch_top_rated(page_num)
        render_movie_grid(movies, cols_count=5, prefix=f"toprated_p{page_num}")

    elif nav == "🎭 By Genre":
        st.markdown('<h1 style="color:white">🎭 Browse by Genre</h1>', unsafe_allow_html=True)
        with st.spinner("Loading genres..."):
            genres = fetch_genres()
        if genres:
            genre_map = {g["name"]: g["id"] for g in genres}
            selected_genre = st.selectbox("Choose a genre", list(genre_map.keys()))
            if selected_genre:
                with st.spinner(f"Loading {selected_genre} movies..."):
                    movies = fetch_by_genre(genre_map[selected_genre])
                st.markdown(f'<div class="section-header">🎬 {selected_genre} Movies</div>', unsafe_allow_html=True)
                render_movie_grid(movies, cols_count=5, prefix=f"genre_{genre_map[selected_genre]}")

    elif nav == "🔍 Search":
        st.markdown('<h1 style="color:white">🔍 Search Movies</h1>', unsafe_allow_html=True)
        query = st.text_input("", placeholder="Enter a movie title...", label_visibility="collapsed")
        if query:
            with st.spinner("Searching..."):
                results = search_movies(query)
            if results:
                st.markdown(f'<div class="section-header">Found {len(results)} results for "{query}"</div>', unsafe_allow_html=True)
                render_movie_grid(results, cols_count=5, prefix="search_results")
            else:
                st.warning("No results found. Try a different title.")
        else:
            st.markdown('<div class="section-header">Popular Movies</div>', unsafe_allow_html=True)
            with st.spinner("Loading..."):
                movies = fetch_popular()
            render_movie_grid(movies, cols_count=5, prefix="search_popular")


# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align: center; padding: 2rem; margin-top: 3rem; background: linear-gradient(145deg, #1e1e24, #141417); border-radius: 12px; border: 1px solid rgba(255, 255, 255, 0.05);">
    <div style="font-weight: 700; color: #ffffff; font-size: 0.95rem; letter-spacing: 1.2px; text-transform: uppercase;">
        🎬 CineMatch <span style="color: #666; font-weight: 300; margin: 0 8px;">|</span>
        <span style="color: #00f2fe; font-size: 0.85rem;">Built with Streamlit</span>
    </div>
    <div style="margin-top: 12px; font-size: 0.85rem; color: #aaa;">
        Developed by <span style="color:#ff416c; font-weight: 800; font-size: 0.9rem;">Mosairul Alam Tyhan</span>
    </div>
    <hr style="border: 0; height: 1px; background: rgba(255,255,255,0.1); margin: 15px auto; width: 60%;">
    <div style="font-size: 0.72rem; color: #666; line-height: 1.4;">
        ✨ Powered by <span style="color: #01b4e4; font-weight: 600;">TMDB API</span>.
        This product uses the TMDB API but is not endorsed or certified by TMDB.
    </div>
</div>
""", unsafe_allow_html=True)
