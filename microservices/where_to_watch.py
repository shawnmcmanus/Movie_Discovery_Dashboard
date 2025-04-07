from flask import Flask, jsonify, request
import requests
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
app = Flask(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def init_db():
    conn = sqlite3.connect("where_to_watch.db")
    cursor = conn.cursor()
    cursor.execute("""
       CREATE TABLE IF NOT EXISTS watch_providers (
            movie_id INTEGER PRIMARY KEY,
            title TEXT UNIQUE NOT NULL,
            services TEXT NOT NULL,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )                                             
    """)
    conn.commit()
    conn.close()
    print("Database initialized!")

init_db()

def get_watch_providers(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
    response = requests.get(url).json()
    providers = response.get("results", {}).get("US", {}).get("flatrate", [])
    return [p["provider_name"] for p in providers] if providers else []

def cache_watch_providers(movie_id, title, services):
    conn = sqlite3.connect("where_to_watch.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO watch_providers (movie_id, title, services, last_updated)
        VALUES (?, ?, ?, datetime('now'))                  
    """, (movie_id, title, "|".join(services)))
    conn.commit()
    conn.close()

def get_cached_watch_provider(movie_id):
    conn = sqlite3.connect("where_to_watch.db")
    cursor = conn.cursor()
    cursor.execute("SELECT services FROM watch_providers WHERE movie_id = ?", (movie_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0].split("|") if result else None
    
def should_refresh_cache(movie_id):
    conn = sqlite3.connect("where_to_watch.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_updated FROM watch_providers WHERE movie_id = ?", (movie_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return True
    
    last_updated = datetime.strptime(result[0], "%Y-%m-%d %H:%M:%S")
    return last_updated < datetime.now() - timedelta(hours=24)
    
@app.route("/watch/<title>/<movie_id>", methods=["GET"])
def where_to_watch(title, movie_id):
    print(f"Received request: title={title}, movie_id={movie_id}")
    if not movie_id:
        return jsonify({"Error": "Movie not found"}), 404

    if not should_refresh_cache(movie_id):
        return jsonify({"title": title, "services": get_cached_watch_provider(movie_id)})
    
    services = get_watch_providers(movie_id)
    if services:
        cache_watch_providers(movie_id, title, services)

    return jsonify({"title": title, "services": services})

@app.route("/watch/<title>/refresh", methods=["GET"])
def refresh_watch_providers(movie_id, title):
    if not movie_id:
        return jsonify({"Error": "Movie not found"}), 404
    
    services = get_watch_providers(movie_id)
    if services:
        cache_watch_providers(movie_id, title, services)

    return jsonify({"title": title, "services": services, "status": "Refreshed"})

def run_where_to_watch_service():
    app.run(port=8082)

if __name__ == "__main__":
    run_where_to_watch_service() 