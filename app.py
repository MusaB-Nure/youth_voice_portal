from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# Database initialization
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            votes INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Submitted'
        )
    ''')
    conn.commit()
    conn.close()

# Route to serve the main dashboard page
@app.route('/')
def index():
    return render_template('index.html')

# Route to serve the suggestion/submission page
@app.route('/submit')
def submit_page():
    return render_template('submit.html')

# API: Get all issues ordered by votes
@app.route('/api/issues', methods=['GET'])
def get_issues():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM issues ORDER BY votes DESC')
    rows = cursor.fetchall()
    conn.close()
    
    issues = []
    for row in rows:
        issues.append({
            "id": row[0], 
            "title": row[1], 
            "description": row[2],
            "category": row[3], 
            "votes": row[4], 
            "status": row[5]
        })
    return jsonify(issues)

# API: Add a new issue
@app.route('/api/issues', methods=['POST'])
def add_issue():
    data = request.json
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO issues (title, description, category) 
        VALUES (?, ?, ?)
    ''', (data['title'], data['description'], data['category']))
    conn.commit()
    conn.close()
    return jsonify({"message": "Issue submitted successfully!"}), 201

# API: Upvote an issue
@app.route('/api/issues/<int:issue_id>/vote', methods=['POST'])
def vote_issue(issue_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE issues SET votes = votes + 1 WHERE id = ?', (issue_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Vote recorded successfully!"})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)