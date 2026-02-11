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
import random

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, MERGED_ENROLLMENT


def load_data():
    """Load majors and student enrollment data."""
    print("Loading data files...")
    with open(MAJORS_JSON, 'r') as f:
        majors_data = json.load(f)
    
    student_data = pd.read_csv(MERGED_ENROLLMENT, sep='\t')
    return majors_data, student_data


def get_student_courses(student_data, student_id):
    """Get all passed courses for a specific student."""
    student_records = student_data[student_data['LID'].astype(str) == str(student_id)]
    
    if len(student_records) == 0:
        return None, None, set()
    
    # Get student info
    latest_record = student_records.sort_values('Term', ascending=False).iloc[0]
    
    # Get passed courses
    passed_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'P']
    passed_courses = student_records[student_records['FinalGrade'].isin(passed_grades)]
    
    # Build set of course codes
    student_course_codes = set()
    for _, row in passed_courses.iterrows():
        subject = str(row.get('Subject', '')).strip()
        catalog_num = str(row.get('CatalogNumber', '')).strip()
        if subject and catalog_num:
            course_code = f"{subject} {catalog_num}"
            student_course_codes.add(course_code)
    
    return latest_record, passed_courses, student_course_codes


def analyze_student(student_data, majors_data, student_id):
    """Analyze a single student's course history and potential matches."""
    
    print(f"Analyzing Student {student_id}")
    print('-'*60)
    
    # Get all student records
    student_records = student_data[student_data['LID'].astype(str) == str(student_id)]
    
    if len(student_records) == 0:
        print(f"Student {student_id} not found in database")
        return None
    
    latest_record, passed_courses, student_course_codes = get_student_courses(student_data, student_id)
    
    # Display student info
    print(f"\nStudent Name: {latest_record['Name']}")
    print(f"Current Major: {latest_record['Active_Plan_List']}")
    print(f"Total records: {len(student_records)}")
    
    # List all semesters enrolled
    semesters = sorted(student_records['Term'].unique())
    print(f"\nSemesters Enrolled ({len(semesters)} total):")
    for semester in semesters:
        courses_in_semester = len(student_records[student_records['Term'] == semester])
        print(f"  • {semester} ({courses_in_semester} courses)")
    
    # Separate passed and not passed courses
    passed_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'P']
    not_passed_courses = student_records[~student_records['FinalGrade'].isin(passed_grades)]
    
    print(f"\nTotal courses passed: {len(passed_courses)}")
    print(f"Unique courses passed: {len(student_course_codes)}")
    print(f"Total courses NOT passed: {len(not_passed_courses)}")
    
    # Show ALL passed courses
    print(f"\nPASSED COURSES ({len(passed_courses)} total):")
    print('-'*60)
    for idx, (_, row) in enumerate(passed_courses.iterrows(), 1):
        subject = str(row.get('Subject', '')).strip()
        catalog_num = str(row.get('CatalogNumber', '')).strip()
        course_code = f"{subject} {catalog_num}"
        credits = row.get('Units_Earned', 'N/A')
        term = row.get('Term', 'N/A')
        print(f"  {idx}. {course_code:<15} Grade: {row['FinalGrade']:<3} Credits: {credits:<4} Term: {term}")
    
    # Show ALL not passed courses
    if len(not_passed_courses) > 0:
        print(f"\nNOT PASSED COURSES ({len(not_passed_courses)} total):")
        print('-'*60)
        for idx, (_, row) in enumerate(not_passed_courses.iterrows(), 1):
            subject = str(row.get('Subject', '')).strip()
            catalog_num = str(row.get('CatalogNumber', '')).strip()
            course_code = f"{subject} {catalog_num}"
            credits = row.get('Units_Earned', 'N/A')
            term = row.get('Term', 'N/A')
            print(f"  {idx}. {course_code:<15} Grade: {row['FinalGrade']:<3} Credits: {credits:<4} Term: {term}")
    
    # Find matches
    matches_found = find_major_matches(majors_data, student_course_codes)
    
    
    print(f"Majors with at least one matched course: {len(matches_found)}")
    
    
    if matches_found:
        print("\nTop 5 matches:")
        sorted_matches = sorted(matches_found.items(), key=lambda x: len(x[1]), reverse=True)
        for major_name, courses in sorted_matches[:5]:
            print(f"\n {major_name}: {len(courses)} courses matched")
            print(f"     Matched: {', '.join(courses[:10])}")
            if len(courses) > 10:
                print(f"     ... and {len(courses) - 10} more")
    else:
        print("\nNO MATCHES FOUND!")
    
    return {
        'student_id': student_id,
        'name': latest_record['Name'],
        'current_major': latest_record['Active_Plan_List'],
        'total_courses': len(passed_courses),
        'unique_courses': len(student_course_codes),
        'matches': len(matches_found),
        'top_match': sorted(matches_found.items(), key=lambda x: len(x[1]), reverse=True)[0] if matches_found else None
    }


def find_major_matches(majors_data, student_course_codes):
    """Find which majors match student's completed courses."""
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
    
    return matches_found


def analyze_majors_data(majors_data):
    """Analyze the structure of majors data."""
    
    print("Analyzing Majors Database")
    
    print(f"\nTotal majors in database: {len(majors_data['programs'])}")
    
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
    
    print(f"\nMajors WITH required courses: {majors_with_courses} ")
    print(f"Majors WITHOUT required courses: {majors_without_courses} ")
    
    print("\nSample majors WITH required courses:")
    for name, count in sample_majors_with_courses:
        print(f"  - {name}: {count} courses")
    
    print("\nSample majors WITHOUT required courses:")
    for name in sample_majors_without_courses:
        print(f"  - {name}")
    
    # Show example major
    if sample_majors_with_courses:
        major_name, _ = sample_majors_with_courses[0]
        major_info = majors_data['programs'][major_name]
        print(f"\nExample Major: {major_name}")
        print(f"Required courses (first 10):")
        for course in major_info['required_courses'][:10]:
            print(f"  - {course}")


def test_random_students(student_data, majors_data, n=5):
    """Test n random students from the database."""
    unique_students = student_data['LID'].unique()
    print(f"Testing {n} Random Students")
    print(f"Total students in database: {len(unique_students)}")
    # Select random students
    sample_size = min(n, len(unique_students))
    random_students = random.sample(list(unique_students), sample_size)
    
    results = []
    for student_id in random_students:
        result = analyze_student(student_data, majors_data, student_id)
        if result:
            results.append(result)
    
    # Summary of results
    print("Summary of Random Student Analysis")
    print(f"\nStudents analyzed: {len(results)}")
    
    students_with_matches = sum(1 for r in results if r['matches'] > 0)
    print(f"Students with matches: {students_with_matches}/{len(results)}")
    
    if results:
        avg_courses = sum(r['unique_courses'] for r in results) / len(results)
        avg_matches = sum(r['matches'] for r in results) / len(results)
        print(f"Average unique courses: {avg_courses:.1f}")
        print(f"Average major matches: {avg_matches:.1f}")

if __name__ == "__main__":
    majors_data, student_data = load_data()
    #analyze_majors_data(majors_data)
    #analyze_student(student_data, majors_data, '7997347')
    test_random_students(student_data, majors_data, n=100)

