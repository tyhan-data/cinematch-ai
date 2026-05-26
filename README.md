# 🎬 CineMatch — Movie Recommendation App

A full-stack movie discovery and recommendation web app built with **FastAPI** (backend) and **Streamlit** (frontend), powered by **TMDB API** and a local **TF-IDF content-based filtering** model.

---

## 📁 Project Structure

```
movie_recommender/
├── main.py              ← FastAPI backend (API server)
├── app.py               ← Streamlit frontend (web UI)
├── requirements.txt     ← Python dependencies
├── model/               ← ML model files (place your .pkl files here)
│   ├── dataset.pkl
│   ├── indices.pkl
│   ├── tfidf.pkl
│   └── tfidf_matrix.pkl
└── README.md
```

---

## ⚙️ Setup (Local)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Place model files
Copy your pickle files into the `model/` directory:
```bash
mkdir model
cp path/to/dataset.pkl model/
cp path/to/indices.pkl  model/
cp path/to/tfidf.pkl    model/
cp path/to/tfidf_matrix.pkl model/
```

### 3. Run FastAPI backend
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
API docs available at: http://localhost:8000/docs

### 4. Run Streamlit frontend (in a separate terminal)
```bash
streamlit run app.py
```
Opens at: http://localhost:8501

---

## 🌐 API Endpoints

| Endpoint | Description |
|---|---|
| `GET /` | Health check |
| `GET /popular` | Popular movies |
| `GET /trending` | Trending movies |
| `GET /top-rated` | Top-rated movies |
| `GET /search?q=Inception` | Search by title |
| `GET /movie/{id}` | Full movie details |
| `GET /recommend?title=Inception` | Content-based recommendations |
| `GET /genres` | All genre categories |
| `GET /genre/{id}` | Movies by genre |

---

## 🚀 Deploy on Streamlit Cloud

1. Push this project to a **GitHub repository**
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"** → connect your GitHub repo
4. Set **Main file path** to `app.py`
5. Add secrets (optional — API key is already in the code):
   ```toml
   # .streamlit/secrets.toml
   TMDB_API = "759efa35e9286f4ae3cfd0d2320c96ddd"
   ```
6. Click **Deploy** — your app goes live in ~2 minutes!

> **Note:** The Streamlit app works standalone (direct TMDB calls) — FastAPI is optional for local enrichment with your custom model.

---

## 🎯 Features

- 🏠 **Home** — Trending, Popular, Top Rated tabs
- 🔍 **Search** — Find any movie by title
- 🎬 **Movie Detail** — Poster, backdrop, rating, runtime, cast, director, trailer link, budget/revenue stats
- 🎯 **Recommendations** — Similar movies (TF-IDF model or TMDB fallback)
- 🎭 **Browse by Genre** — All TMDB genres
- 🔥 **Trending** — Daily and weekly trending
- ⭐ **Top Rated** — TMDB's highest-rated films

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Backend API | FastAPI + Uvicorn |
| ML Model | TF-IDF + Cosine Similarity (scikit-learn) |
| Movie Data | TMDB API |
| Language | Python 3.10+ |
