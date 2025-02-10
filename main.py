import sqlite3
import bcrypt
import requests
import urllib.parse
import os
from dotenv import load_dotenv
# from flask import Flask

load_dotenv()
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
if not TMDB_API_KEY:
    raise ValueError("The TMDB_API_KEY is missing from the .env file.")
# app = Flask(__name__) (*for microservices)
# app.secret_key = "your_secret_key"

def fetch_movie_from_tmdb(title):
    """
    param: title:- Movie title
    Fetch movie details from the TMDB API for a user to review
    """
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}"
    response = requests.get(url)
    data = response.json()

    if data["results"]:
        movie = data["results"][0]
        return movie["id"], movie["title"], movie["release_date"][:4]
    
    return None


def print_movie_details(title, release_date, overview, genre_str, director):
    """
    param: title:- Movie title
    param: release_date:- Release date of the movie title (YYYY-MM-DD)
    param: overview:- Summary of the movie from TMDB
    param: genre_str:- All the genres of said movie
    param: director:- Name of movie director
    Prints out movie details for user search
    """
    print("\n🎬 **Movie Details** 🎬")
    print(f"📌 Title: {title}")
    print(f"📅 Release Date: {release_date}")
    print(f"🎭 Genre(s): {genre_str}")
    print(f"🎬 Director: {director}")
    print(f"📖 Summary: {overview}")


def handle_search_results(movie_data):
    print("\n🔍 **Search Results:**")
    for i, movie in enumerate(movie_data["results"][:5], start=1):
        print(f"{i}. {movie['title']} ({movie.get('release_date', 'Unknown')[:4]})")

    choice = input("\nEnter the number of the correct movie (or press Enter to pick the first one): ").strip()
    
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(movie_data["results"]):
            selected_movie = movie_data["results"][index]
        else:
            print("Invalid selection. Defaulting to first result.")
            selected_movie = movie_data["results"][0]
    else:
        selected_movie = movie_data["results"][0]

    return selected_movie["id"]


def search_for_movie_from_tmdb(title):
    """
    param: title:- Movie title for search
    Search for a specific movie and return detailed information
    """
    query = urllib.parse.quote(title.strip())  # Ensure special characters are handled
    url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={query}"

    response = requests.get(url)
    data = response.json()

    if not data["results"]:
        print("Movie not found. Try refining your search.")
        return None

    movie_id = handle_search_results(data)

    details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits"
    details_response = requests.get(details_url)
    details_data = details_response.json()

    title = details_data.get("title", "Unknown Title")
    release_date = details_data.get("release_date", "N/A")
    overview = details_data.get("overview", "No summary available.")
    genres = [genre["name"] for genre in details_data.get("genres", [])]
    genre_str = ", ".join(genres) if genres else "N/A"

    director = "N/A"
    for crew_member in details_data.get("credits", {}).get("crew", []):
        if crew_member["job"] == "Director":
            director = crew_member["name"]
            break

    print_movie_details(title, release_date, overview, genre_str, director)


def get_genre_id(genre_name):
    """
    param: genre_name:- genre name
    Fetch all the genre ids from TMDB and return a specified genre's ID
    """
    url = f"https://api.themoviedb.org/3/genre/movie/list?api_key={TMDB_API_KEY}&language=en-US"
    response = requests.get(url)
    data = response.json()

    for genre in data["genres"]:
        if genre["name"].lower() == genre_name.lower():
            return genre["id"]
        
    return None


def print_genre_list(top_movies, genre_name, num_of_movies):
    """
    param: top_movies:- list of top X number of movies
    param: genre_name:- name of genre
    param: num_of_movies:- number of movies in result
    Prints out list of top movies from a genre
    """
    print(f"\nTop {num_of_movies} {genre_name.capitalize()} Movies Based on TMDB Ratings:\n")
    for i, movie in enumerate(top_movies, start=1):
        title = movie.get("title", "Unknown Title")
        release_date = movie.get("release_date", "N/A")
        rating = movie.get("vote_average", "N/A")
        
        print(f"{i}. {title} ({release_date}) - ⭐ {rating}/10")       


def fetch_genre_from_tmdb(genre_name, num_of_movies):
    """
    param: genre_name:- The name of the user specified genre
    param: num_of_movies:- number of movies the user wants in results
    Fetch top X movies of a specified genre based on TMDB ratings
    """
    genre_id = get_genre_id(genre_name)

    if genre_id is None:
        print("Genre not found. Please check your entry and try again.")
        return []
    
    all_movies = []
    page = 1 # Start results at page 1

    while len(all_movies) < num_of_movies:
        url = (f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}"
           f"&with_genres={genre_id}&sort_by=vote_average.desc&vote_count.gte=100"
           f"&page={page}")
        response = requests.get(url)
        data = response.json()

        if "results" in data:
            all_movies.extend(data["results"])
        else:
            break

        page += 1

    top_movies = all_movies[:num_of_movies]
    print_genre_list(top_movies, genre_name, num_of_movies)


def init_movie_db():
    with sqlite3.connect("movies.db") as conn:
        cursor = conn.cursor()

        # Movies Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tmdb_id INTEGER UNIQUE NOT NULL,
            title TEXT NOT NULL,
            release_year INTEGER
        )""")
        
        # Reviews table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                movie_id INTEGER,
                rating INTEGER,
                review_text TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (movie_id) REFERENCES movies(id)
            )""")

        conn.commit()


# Initialize movie database for revies
init_movie_db()

def init_user_db():
    """
    Initialize user database that will hold a unique ID, username, and password
    """
    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )""")
        
        conn.commit()


# Initialize user database for authetication
init_user_db()


def signup():
    """
    Handles the signup and account creation for a new user
    """
    username = input("Enter username: ")
    password = input("Enter password: ")

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    with sqlite3.connect("users.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        print("Sign up successful!")


def login():
    """
    Logs in user by checking entered username and password by decryption
    """
    while True:
        username = input("Enter username: ")
        password = input("Enter password: ").encode("utf-8")
        
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()

            # Fetch the stored hashed password for the given username
            cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user:
                user_id, stored_hashed_password = user
                stored_hashed_password = stored_hashed_password

                if bcrypt.checkpw(password, stored_hashed_password):
                    print("Login successful")
                    return user_id
                else:
                    print("Invalid login credentials. Please try again.")
            else:    
                print("Invalid login credentials. Please try again.")
   

def login_or_signup():
    """
    Prompts the user to login or signup (contains functionality to ensure 
    one of those two options)
    """
    while True:
        choice = input("Enter option: 1. Login  |  2. Sign up: ")
        if choice == "1":
            user_id = login()
            return user_id
        elif choice == "2":
            user_id = signup()
            return user_id
        else:
            print("Please select option '1' or '2'.") 


def intro():
    """
    Prints the intro message to the user
    """
    print("\n<=====Welcome to Your Movie Review Dashboard=====>\n")
    print("You can lookup movies, review ones that you watched, and browse \
          \nby genres. Please login to save your reviews for later.\n")
    
    user_id = login_or_signup()
    return user_id


def main_menu():
    """
    Provides the main menu of options
    """
    print("\n<===Main Menu===>")
    print("1. Add Review")
    print("2. View Reviews")
    #print("3. Receive Recommendation")
    print("3. Browse Genres")
    print("4. Search Movie")
    print("5. Help")
    print("6. Quit")


def add_review(user_id):
    """
    param: user_id:- The logged in user's id
    Makes a review that is tethered to a specific user's library of reviews
    """
    with sqlite3.connect("movies.db") as conn:
        cursor = conn.cursor()

        while True:
            # Get movie details
            movie_title = input("Enter movie title: ")
            movie_data = fetch_movie_from_tmdb(movie_title)

            if not movie_data:
                print("Movie not found in TMDB.")
                return
            
            tmdb_id, title, release_year = movie_data

            # Check if movie exists in database
            cursor.execute("SELECT id FROM movies WHERE tmdb_id = ?", (tmdb_id,))
            movie = cursor.fetchone()

            if not movie:
                cursor.execute("INSERT INTO movies (tmdb_id, title, release_year) VALUES (?, ?, ?)",
                               (tmdb_id, title, release_year))
                conn.commit()
                movie_id = cursor.lastrowid
            else:
                movie_id = movie[0]

            rating = float(input("Enter rating (1.0-10.0): "))
            review_text = input("Enter your review: ")

            cursor.execute("INSERT INTO reviews (user_id, movie_id, rating, review_text) VALUES (?, ?, ?, ?)",
                           (user_id, movie_id, rating, review_text))
            conn.commit()

            print("Review added successfully!")

            choice = input("\nEnter 1 to make another review (or press Enter to skip): ")

            if choice == "1":
                continue
            else:
                return        


def delete_review(review_id, user_id):
    """
    param: review_id:- The ID of the review to be deleted
    param: user_id:- The ID of the user's review to be deleted
    Deletes a review by ID if it belongs to the user
    """
    with sqlite3.connect("movies.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM reviews WHERE id = ? AND user_id = ?", (review_id, user_id))
        review = cursor.fetchone()

        if not review:
            print("Review not found in your database.")
            return
        while True:
            choice = input("Are you sure you would like to permanently delete this review? [Y] [N]: ")
            if choice.upper() == "Y":
                cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
                conn.commit()
                print("✅ Review deleted successfully!")
                return
            elif choice.upper() == "N":
                print("Review deletion cancelled.")
                return
            else:
                print("Enter a valid input.\n")


def view_reviews(user_id):
    """
    param: user_id:- Used to view specific user's list of reviews
    View the entire list of a user's reviews
    """
    with sqlite3.connect("movies.db") as conn:
        cursor = conn.cursor()

        # Fetch user reviews
        cursor.execute("""
            SELECT reviews.id, movies.title, reviews.rating, reviews.review_text
            FROM reviews
            JOIN movies ON reviews.movie_id = movies.id
            WHERE reviews.user_id = ?
        """, (user_id,))

        reviews = cursor.fetchall()

        if not reviews:
            print("No reviews found.")
            return
        
        print("\nYour Reviews:")
        for review_id, title, rating, review in reviews:
            print(f"ID: {review_id} | 🎬 Movie: {title}\n⭐ Rating: {rating}/10.0\n📝 Review: {review}\n")

        delete_choice = input("Enter the ID of the review to delete (or press Enter to skip): ")
        if delete_choice.isdigit():
            delete_review(int(delete_choice), user_id)

# def receive_rec(user_id):
#    pass

def browse_genres_instructions():
    """
    Presents instructions for user to browse through genres
    """
    print(f"\nBrowse the following genres to see the top rated movies in each category:")
    print("1. Comedy")
    print("2. Action")
    print("3. Drama")
    print("4. Animation")
    print("5. Science Fiction")
    print("6. Mystery")


def genre_choice(choice, num_of_movies):
        """
        param: choice:- The genre choice of the user (presented as numerical string)
        param: num_of_movies:- The total movies the user wants to see from said genre
        Interprets user's genre choice approriately
        """
        if choice == "1":
            fetch_genre_from_tmdb("Comedy", num_of_movies)
        elif choice == "2":
            fetch_genre_from_tmdb("Action", num_of_movies)
        elif choice == "3":
            fetch_genre_from_tmdb("Drama", num_of_movies)
        elif choice == "4":
            fetch_genre_from_tmdb("Animation", num_of_movies)
        elif choice == "5":
            fetch_genre_from_tmdb("Science Fiction", num_of_movies)
        elif choice == "6":
            fetch_genre_from_tmdb("Mystery", num_of_movies)
        else: 
            print("Please enter a valid option.")


def browse_genres():
    """
    Parent function that controls all genre browsing functionality
    """
    browse_genres_instructions()

    while True:
        choice = input("\nEnter a number for genre choice or 'B' to go Back: ")
        if choice.upper() == "B":
            return
        num_of_movies = int(input("Enter the number of movies you would like to generate (1-100): "))
        if num_of_movies < 1 or num_of_movies > 100:
            print("Enter a valid number of movies.")
            continue

        genre_choice(choice, num_of_movies)


def search():
    """
    Parent function that controls all search functionality
    """
    title = input("Enter the title of the movie you would like to search (*include the full name as best you can): ")
    search_for_movie_from_tmdb(title)


def help():
    """
    Provides basic info to the user to enhance experience
    """
    print("<===HELP===>")
    print("- Utilize the main menu to navigate around.\n"
          "- 'Add Review' allows you to add a review to your library of existing reviews.\n"
          "- 'View Review' allows you to bring up the entire list of all your reviews and delete them as you wish.\n"
          "- 'Browse Genres' allows you to visit multiple genres and generate a list of the top movies from them.\n"
          "- 'Search' allows you to type in the specific name of a movie and have all the basic details provided to you\n"
          "- 'Quit' allows you to exist the program which will automatically log you out and save any review changes made."
        )


def main():
    user_id = intro()
    while True:
        main_menu()
        user_input = input("Enter your choice by number: ")
        if user_input == "1":
            add_review(user_id)
        elif user_input == "2":
            view_reviews(user_id)
        #elif user_input == "3": (for microservice)
            #receive_rec(user_id)
        elif user_input == "3":
            browse_genres()
        elif user_input == "4":
            search()
        elif user_input == "5":
            help()
        elif user_input == "6":
            break
        else:
            print("\nPlease enter a valid input.")

    print("\nThanks for using Your Movie Review Dashboard.\n")


if __name__ == "__main__":
    main()