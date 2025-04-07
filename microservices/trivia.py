from flask import Flask, jsonify, request
import random
import sqlite3
import os
import requests
from dotenv import load_dotenv
import html

load_dotenv()

app = Flask(__name__)
TRIVIA_API_KEY = os.getenv("TRIVIA_API_KEY")
if not TRIVIA_API_KEY:
    raise ValueError("API key is missing! Set the API key in the .env file.")

def init_db():
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trivia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT,
            correct_answer TEXT,
            incorrect_answers TEXT    
        )               
    """)
    conn.commit()
    conn.close()

init_db()

def fetch_trivia_from_api():
    response = requests.get(TRIVIA_API_KEY)
    if response.status_code == 200:
        return response.json().get("results", [])
    return []

def cache_questions():
    trivia_data = fetch_trivia_from_api()             
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()

    for item in trivia_data:
        normalized_question = html.unescape(item["question"]).strip()
        cursor.execute("""
            INSERT INTO trivia (question, correct_answer, incorrect_answers)
            SELECT ?, ?, ?
            WHERE NOT EXISTS (
                SELECT 1 FROM trivia WHERE LOWER(TRIM(question)) = ?
            )  
        """, (normalized_question, item["correct_answer"], "|".join(item["incorrect_answers"]), normalized_question))
    
    conn.commit()
    conn.close()

@app.route("/trivia/random", methods=['GET'])
def get_random_trivia():
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question, correct_answer, incorrect_answers FROM trivia ORDER BY RANDOM() LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    
    if result:
        question, correct_answer, incorrect_answers = result
        question = html.unescape(question)
        correct_answer = html.unescape(correct_answer)

        incorrect_list = [html.unescape(opt) for opt in incorrect_answers.split("|")]

        while len(incorrect_list) < 3:
            incorrect_list.append("N/A")

        options = random.sample([correct_answer] + incorrect_list[:3], 4)
        
        return jsonify({
            "question": question,
            "options": options,
            "correct_answer": correct_answer
        })
    else:
        return jsonify({"Error": "No trivia found, please reload cache"})
    
@app.route("/trivia/cache", methods=['GET'])
def get_cached_questions():
    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()
    cursor.execute("SELECT question FROM trivia")
    questions = cursor.fetchall()
    conn.close()
    return jsonify({"cached_questions": [q[0] for q in questions]})

@app.route("/trivia/answer", methods=['POST'])
def check_answer():
    data = request.get_json()
    question = html.unescape(data.get("question", "").strip())
    user_answer = data.get("answer", "").strip()

    conn = sqlite3.connect("trivia.db")
    cursor = conn.cursor()

    

    cursor.execute("SELECT question, correct_answer FROM trivia")
    all_questions = cursor.fetchall()

    """
    print("DEBUG: Stored Questions in DB:")
    for q in all_questions:
        print(f" - {html.unescape(q[0]).strip()}")
"""

    cursor.execute("SELECT question, COUNT(*) FROM trivia GROUP BY question HAVING COUNT(*) > 1")
    duplicates = cursor.fetchall()
    print("DEBUG: Duplicate Questions in DB:")
    for dup in duplicates:
        print(f"- '{dup[0]}' appears {dup[1]} times")

    normalized_question = html.unescape(question).strip().lower()

    cursor.execute("SELECT correct_answer FROM trivia WHERE LOWER(TRIM(question)) = ?", (normalized_question,))
    result = cursor.fetchone()
    conn.close()

    print(f"Result: {result}")

    if result:
        correct_answer = html.unescape(result[0].strip())  # Normalize stored answer
        print(f"Comparing: '{correct_answer.lower()}' vs '{user_answer.lower()}'")  # Debugging

        correct = result[0].strip().lower() == user_answer.strip().lower()
        return jsonify({"correct": correct}), 200
    else:
        return jsonify({"Error": "Question not found"}), 404

def run_trivia_service():
    app.run(port=8081)

if __name__ == '__main__':
    cache_questions()
    run_trivia_service()