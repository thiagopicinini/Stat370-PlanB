"""
Debug script to diagnose major recommendation system issues.

This script helps identify why the major recommender might not be
returning expected results by analyzing student data, major requirements,
and matching logic.
"""
import json
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, MERGED_ENROLLMENT

# Load the data
print("Loading data files...")
with open(MAJORS_JSON, 'r') as f:
    majors_data = json.load(f)

# Load student data
student_data = pd.read_csv(MERGED_ENROLLMENT, sep='\t')

# Pick a student (7997347 from the example)
student_id = '7997347'
print(f"\n=== Analyzing Student {student_id} ===")

# Get student records
student_records = student_data[student_data['LID'].astype(str) == str(student_id)]
print(f"Found {len(student_records)} total records for this student")

# Get student info
latest_record = student_records.sort_values('Term', ascending=False).iloc[0]
print(f"\nStudent Name: {latest_record['Name']}")
print(f"Current Major: {latest_record['Active_Plan_List']}")

# Get passed courses
passed_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'P']
passed_courses = student_records[student_records['FinalGrade'].isin(passed_grades)]
print(f"\nTotal courses passed: {len(passed_courses)}")

# Show sample courses
print("\nSample of passed courses:")
for idx, (_, row) in enumerate(passed_courses.head(10).iterrows()):
    subject = str(row.get('Subject', '')).strip()
    catalog_num = str(row.get('CatalogNumber', '')).strip()
    course_code = f"{subject} {catalog_num}"
    print(f"  {course_code} - Grade: {row['FinalGrade']}, Credits: {row.get('Units_Earned', 'N/A')}")

# Check majors data
print(f"\n=== Analyzing Majors Data ===")
print(f"Total majors in database: {len(majors_data['programs'])}")

# Count how many majors have required courses
majors_with_courses = 0
majors_without_courses = 0
sample_majors_with_courses = []
sample_majors_without_courses = []

for major_name, major_info in majors_data['programs'].items():
    required_courses = major_info.get('required_courses', [])
    if required_courses:
        majors_with_courses += 1
        if len(sample_majors_with_courses) < 5:
            sample_majors_with_courses.append((major_name, len(required_courses)))
    else:
        majors_without_courses += 1
        if len(sample_majors_without_courses) < 5:
            sample_majors_without_courses.append(major_name)

print(f"\nMajors WITH required courses: {majors_with_courses}")
print(f"Majors WITHOUT required courses: {majors_without_courses}")

print("\nSample majors WITH required courses:")
for name, count in sample_majors_with_courses:
    print(f"  - {name}: {count} courses")

print("\nSample majors WITHOUT required courses:")
for name in sample_majors_without_courses:
    print(f"  - {name}")

# Check a specific major with courses
if sample_majors_with_courses:
    major_name, _ = sample_majors_with_courses[0]
    major_info = majors_data['programs'][major_name]
    print(f"\n=== Example Major with Courses: {major_name} ===")
    print(f"Required courses (first 10):")
    for course in major_info['required_courses'][:10]:
        print(f"  - {course}")

# Now check if student courses match ANY major requirements
print(f"\n=== Checking for Matches ===")
student_course_codes = set()
for _, row in passed_courses.iterrows():
    subject = str(row.get('Subject', '')).strip()
    catalog_num = str(row.get('CatalogNumber', '')).strip()
    course_code = f"{subject} {catalog_num}"
    if subject and catalog_num:
        student_course_codes.add(course_code)

print(f"Student has {len(student_course_codes)} unique passed courses")

# Try to match against majors
matches_found = {}
for major_name, major_info in majors_data['programs'].items():
    required_courses = major_info.get('required_courses', [])
    if not required_courses:
        continue
    
    matched = []
    for req_course in required_courses:
        course_options = []
        
        if isinstance(req_course, str):
            course_options = [c.strip() for c in req_course.split(' or ')]
        elif isinstance(req_course, dict):
            if 'options' in req_course:
                # Clean up non-breaking spaces
                course_options = [c.replace('\xa0', ' ').strip() for c in req_course['options']]
        
        for course_option in course_options:
            if course_option in student_course_codes:
                matched.append(course_option)
                break
    
    if matched:
        matches_found[major_name] = matched

print(f"\nMajors with at least one matched course: {len(matches_found)}")
if matches_found:
    print("\nTop matches:")
    for major_name, courses in list(matches_found.items())[:5]:
        print(f"  {major_name}: {len(courses)} courses matched")
        print(f"    Matched: {', '.join(courses[:5])}")
else:
    print("\nNO MATCHES FOUND!")
    print("\nThis explains why you're getting no recommendations.")
    print("\nPossible reasons:")
    print("1. Most majors have empty 'required_courses' arrays in the JSON")
    print("2. Course codes might not match exactly")
    print("3. Need to populate the majors JSON with actual course requirements")
