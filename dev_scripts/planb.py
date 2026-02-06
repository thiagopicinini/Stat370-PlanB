"""
Flask Web Application for Major Recommender System

Provides a web interface for students to login and view alternative
major recommendations based on their completed coursework.
"""
import sys
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session
from major_recommender import MajorRecommender, authenticate_student

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, COURSES_JSON, get_filtered_enrollment_files

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-in-production'

# Initialize recommender with data files using centralized paths
enrollment_files = [str(f) for f in get_filtered_enrollment_files()]

print(f"Initializing recommender with {len(enrollment_files)} enrollment files...")
recommender = MajorRecommender(MAJORS_JSON, COURSES_JSON, enrollment_files)


@app.route('/')
def index():
    """Landing page with login form"""
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    """Handle login request"""
    student_id = request.form.get('student_id', '').strip()
    password = request.form.get('password', '').strip()
    
    if not student_id or not password:
        return render_template('login.html', error='Please enter both Student ID and Password')
    
    # Authenticate
    if not authenticate_student(student_id, password):
        return render_template('login.html', error='Invalid credentials. Use password "1234"')
    
    # Check if student exists
    student_info = recommender.get_student_info(student_id)
    if not student_info:
        return render_template('login.html', error=f'Student ID {student_id} not found')
    
    # Store student ID in session
    session['student_id'] = student_id
    
    return redirect(url_for('recommendations'))


@app.route('/recommendations')
def recommendations():
    """Display major recommendations for logged-in student"""
    student_id = session.get('student_id')
    
    if not student_id:
        return redirect(url_for('index'))
    
    # Get recommendations
    results = recommender.recommend_majors(student_id, top_n=5)
    
    if not results:
        return render_template('login.html', error='Unable to load student data')
    
    return render_template('recommendations.html', results=results)


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)
