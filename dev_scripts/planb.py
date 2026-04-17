"""
Flask Web Application for Major Recommender System

Provides a web interface for students to login and view alternative
major recommendations based on their completed coursework.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from dev_scripts.major_recommender import MajorRecommender, authenticate_student
from utils.paths import MAJORS_JSON, COURSES_JSON, get_filtered_enrollment_files

app = Flask(__name__)
app.secret_key = 'secret-key-here-change-in-production' # Needed for session management, replace with a secure key in production, 
#this is just for demonstration purposes and a POC. 

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
    
    # Read filter values from request.args - explicitly handle empty strings
    filters = {
        'credits_per_semester': request.args.get('credits_per_semester', '').strip(),
        'four_year': request.args.get('four_year', '').strip(),
        'outside_dept': request.args.get('outside_dept', '').strip(),
        'outside_school': request.args.get('outside_school', '').strip()
    }
    
    # Convert credits_per_semester to int, default to 18
    try:
        credits_per_semester = int(filters['credits_per_semester']) if filters['credits_per_semester'] else 18
    except (ValueError, TypeError):
        credits_per_semester = 18
    
    # Convert empty strings to None for optional filters
    four_year_filter = filters['four_year'] if filters['four_year'] else None
    outside_dept_filter = filters['outside_dept'] if filters['outside_dept'] else None
    outside_school_filter = filters['outside_school'] if filters['outside_school'] else None
    
    # Get recommendations with filters
    results = recommender.recommend_majors(
        student_id,
        top_n=5,
        credits_per_semester=credits_per_semester,
        filter_four_year=four_year_filter,
        filter_outside_dept=outside_dept_filter,
        filter_outside_school=outside_school_filter
    )
    
    if not results:
        return render_template('login.html', error='Unable to load student data')
    
    # Create response with cache-busting headers to ensure fresh data
    response = make_response(render_template('recommendations.html', results=results, filters=filters))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True, port=5001)
