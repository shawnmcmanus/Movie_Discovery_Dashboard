# Movie Streaming Database

This project was the culmination of my Software Engineering I class. It is a CLI app that allows users to make an account and review movies, receive recommendations based on previous reviews, 
search the top movies in specific genres or by name, and answer film trivia. 

The main priority of this project was the correct implementation of microservices. There are four microservices total that are in the folder of the same name:
 - Movie Search
 - Trivia
 - Recommendations
 - Where to Watch

## Technologies
The microservices communicate with the main app through a Flask framework. The user information is stored locally with a SQLite approach, with bcrypt used for password encryption. The TMDB API is used by the movie-searching apparatus to fetch accurate info.
