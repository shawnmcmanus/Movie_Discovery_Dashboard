from flask import Flask, request, jsonify
import requests
import sqlite3
import os
import random
#from dotenv import load_dotenv
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor

MOVIES_REVIEWS_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "movies.db"))
MICROSERVICE_SEARCH_URL = "http://localhost:8080/movies"

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("API key is missing! Set TMDB_API_KEY in the .env file.")

app = Flask(__name__)

def fetch_reviews(user_id):
    reviews = []

    with sqlite3.connect(MOVIES_REVIEWS_DB) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT reviews.id, movies.title, reviews.rating
            FROM reviews
            JOIN movies ON reviews.movie_id = movies.id
            WHERE reviews.user_id = ?     
        """, (user_id,))

    reviews_data = cursor.fetchall()

    if reviews_data:
        for review_id, title, rating in reviews_data:
            reviews.append({
                "review_id": review_id,
                "title": title,
                "rating": rating,
                #"review_text": review_text
            })

    return reviews

genre_cache = {}
movie_cache = {}

def get_genre_id(genre_name):
    """
    param: genre_name:- genre name
    Fetch all the genre ids from TMDB and return a specified genre's ID
    """
    if not genre_cache:
        # Fetch all genres from TMDB and populate the cache
        url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            for genre in data.get("genres", []):
                if genre and isinstance(genre, dict) and genre.get("name"):
                    genre_cache[genre["name"].lower()] = genre["id"]
        else:
            print(f"Error fetching genres: {response.status_code}")
            return None

    # Return the genre ID from the cache
    return genre_cache.get(genre_name.lower())

@lru_cache(maxsize=1000)
def get_movie_genre_from_tmdb(movie_id):
    TMDB_MOVIE_URL = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY
    }

    response = requests.get(TMDB_MOVIE_URL, params=params)

    if response.status_code == 200:
        movie_data = response.json()
        genres = movie_data.get("genres", [])

        if genres:
            return genres[0]["name"].lower()
        
    return None

def get_similar_movies(movie_id, user_reviewed_ids):
    genre = get_movie_genre_from_tmdb(movie_id)

    # Ensure genre is valid before proceeding
    if not genre:
        print(f"Error: Could not fetch genre for movie ID {movie_id}")
        return []

    genre_id = get_genre_id(genre)
    
    if not genre_id:
        print(f"Error: Could not fetch genre ID for genre '{genre}'")
        return []
    
    if genre_id in movie_cache:
        print(f"Using cached movie list for genre {genre} (ID: {genre_id})")
        movie_results = movie_cache[genre_id]

    print(f"Fetching movies from microservice for genre {genre} (ID: {genre_id})")

    response = requests.get(f"{MICROSERVICE_SEARCH_URL}?genre={genre_id}&num_of_movies=20")
    print(f"Response status code: {response.status_code}")
    if response.status_code != 200:
        print(f"Error: Movie search service failed for genre '{genre}'")
        return []
    
    movie_results = response.json()
    movie_cache[genre_id] = movie_results

    recommended_movies = [
        (movie["id"], movie["title"]) for movie in movie_results if movie["id"] not in user_reviewed_ids
    ]

    return recommended_movies

def get_recommendations(user_reviews):
    recommendations = []
    reviewed_movie_ids = [review['review_id'] for review in user_reviews if review['rating'] >= 7]

    all_recommended_movies = set()

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(get_similar_movies, review['review_id'], reviewed_movie_ids)
            for review in user_reviews if review['rating'] > 7
        ]
        for future in futures:
            similar_movies = future.result()
            all_recommended_movies.update(similar_movies)

    all_recommended_movies = list(all_recommended_movies)
    random.shuffle(all_recommended_movies)
    recommendations = all_recommended_movies[:5]

    if not recommendations:
        recommendations.append({"suggestion": "No similar movies found. Try reviewing more!"})

    return recommendations

@app.route("/recommendations", methods=["GET"])
def recommend_movies():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"Error": "User ID is required"}), 400
    
    reviews = fetch_reviews(user_id)
    if not reviews:
        return jsonify({"Error": "No reviews found for this user"}), 404
    
    recommendations = get_recommendations(reviews)
    return jsonify(recommendations), 200

def run_recommendation_service():
    app.run(port=8083)

if __name__ == "__main__":
    run_recommendation_service()