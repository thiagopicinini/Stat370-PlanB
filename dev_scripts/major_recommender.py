"""
Major Recommender System

Analyzes student transcripts and recommends alternative majors based on
credits earned toward major requirements. Uses enrollment data and scraped
major requirements to calculate best-fit alternative majors for students.
"""
import json
import sys
from pathlib import Path
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Tuple, Union

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, COURSES_JSON, get_filtered_enrollment_files


class MajorRecommender:
    def __init__(self, majors_file: Union[str, Path], courses_file: Union[str, Path], enrollment_files: List[Union[str, Path]]):
        """
        Initialize the recommender with data files.
        
        Args:
            majors_file: Path to bachelors_majors_web.json
            courses_file: Path to courses.json
            enrollment_files: List of paths to enrollment TSV files
        """
        self.majors_data = self._load_json(majors_file)
        self.courses_data = self._load_json(courses_file)
        self.student_data = self._load_student_data(enrollment_files)
        
    def _load_json(self, filepath: str) -> dict:
        """Load JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    def _load_student_data(self, enrollment_files: List[str]) -> pd.DataFrame:
        """Load and merge all student enrollment data"""
        dfs = []
        for file in enrollment_files:
            df = pd.read_csv(file, sep='\t')
            dfs.append(df)
        
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Filter for undergraduate students only (Career = 'UGRD')
        if 'Career' in combined_df.columns:
            undergrad_df = combined_df[combined_df['Career'] == 'UGRD']
            print(f"Filtered to undergraduate only: {len(combined_df)} total rows -> {len(undergrad_df)} undergraduate rows")
            return undergrad_df
        else:
            print("Warning: 'Career' column not found, returning all data")
            return combined_df
    
    def get_student_info(self, student_id: str) -> Dict:
        """Get student information"""
        student_records = self.student_data[self.student_data['LID'].astype(str) == str(student_id)]
        
        if student_records.empty:
            return None
        
        # Get most recent record for student info
        latest_record = student_records.sort_values('Term', ascending=False).iloc[0]
        
        # Get current major, handle NaN with fallback to Plan_List_Start_ofTerm columns
        current_major = latest_record.get('Active_Plan_List', 'Undeclared')
        if pd.isna(current_major):
            # Try to find Plan_List_Start_ofTerm_* columns as fallback
            plan_list_cols = [col for col in latest_record.index if col.startswith('Plan_List_Start_ofTerm_')]
            if plan_list_cols:
                # Use the first non-NaN value from Plan_List_Start_ofTerm columns
                for col in plan_list_cols:
                    if not pd.isna(latest_record[col]):
                        current_major = latest_record[col]
                        break
                else:
                    current_major = 'Undeclared'
            else:
                current_major = 'Undeclared'
        
        return {
            'student_id': student_id,
            'name': latest_record.get('Name', 'Unknown'),
            'current_major': current_major,
            'class_standing': latest_record.get('Academic_Level', 'Unknown')
        }
    
    def get_student_courses(self, student_id: str) -> List[Dict]:
        """Get all courses a student has taken and passed"""
        student_records = self.student_data[self.student_data['LID'].astype(str) == str(student_id)]
        
        # Filter for passed courses (grades A, B, C, or P)
        passed_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'P']
        passed_courses = student_records[student_records['FinalGrade'].isin(passed_grades)]
        
        courses = []
        seen_courses = set()  # Track unique course-term combinations to avoid duplicates
        
        for _, row in passed_courses.iterrows():
            # Combine Subject and CatalogNumber to get course code
            subject = str(row.get('Subject', '')).strip()
            catalog_num = str(row.get('CatalogNumber', '')).strip()
            course_code = f"{subject} {catalog_num}" if subject and catalog_num else None
            
            if course_code and course_code != 'nan nan':
                # Use course + term as unique identifier to avoid counting duplicates
                course_term_key = (course_code, row['Term'])
                
                if course_term_key not in seen_courses:
                    seen_courses.add(course_term_key)
                    
                    # Get credits, handle NaN
                    credits = row.get('Units_Earned', 0)
                    if pd.isna(credits) or credits == 0:
                        credits = 3  # Default to 3 if not specified or 0
                    
                    courses.append({
                        'course': course_code,
                        'credits': credits,
                        'grade': row['FinalGrade'],
                        'term': row['Term']
                    })
        
        return courses
    
    def calculate_major_match(self, student_courses: List[Dict], major_name: str) -> Dict:
        """Calculate how many credits a student has earned toward a specific major"""
        if major_name not in self.majors_data.get('programs', {}):
            return {'matched_courses': [], 'total_credits': 0, 'course_count': 0}
        
        major_info = self.majors_data['programs'][major_name]
        required_courses = major_info.get('required_courses', [])
        
        # Get list of course codes student has passed
        student_course_codes = [c['course'] for c in student_courses]
        
        matched_courses = []
        total_credits = 0
        
        # Check which required courses the student has completed
        for req_course in required_courses:
            course_options = []
            
            # Handle different data types
            if isinstance(req_course, str):
                # Handle "or" cases like "CJC 399 or CJC 390"
                course_options = [c.strip() for c in req_course.split(' or ')]
            elif isinstance(req_course, dict):
                # Handle dictionary format with 'options' key
                if 'options' in req_course:
                    # Clean up course codes (remove non-breaking spaces and normalize)
                    course_options = [c.replace('\xa0', ' ').strip() for c in req_course['options']]
                else:
                    # Skip other dict formats
                    continue
            elif isinstance(req_course, list):
                # If it's a list, skip (might be metadata)
                continue
            else:
                continue
            
            # Check if student has any of the course options
            for course_option in course_options:
                if course_option in student_course_codes:
                    # Find the course details
                    course_detail = next((c for c in student_courses if c['course'] == course_option), None)
                    if course_detail:
                        matched_courses.append({
                            'course': course_option,
                            'credits': course_detail['credits']
                        })
                        total_credits += course_detail['credits']
                        break  # Only count once if multiple options match
        
        return {
            'matched_courses': matched_courses,
            'total_credits': total_credits,
            'course_count': len(matched_courses),
            'total_required': len(required_courses) if required_courses else 0
        }
    
    def recommend_majors(self, student_id: str, top_n: int = 5) -> Dict:
        """Recommend top N alternative majors for a student"""
        student_info = self.get_student_info(student_id)
        
        if not student_info:
            return None
        
        student_courses = self.get_student_courses(student_id)
        current_major_code = student_info['current_major']
        
        # Handle missing or NaN major code
        if pd.isna(current_major_code):
            current_major_code = 'Undeclared'
        else:
            current_major_code = str(current_major_code)
        
        # Calculate match for all majors (don't skip current major in matching logic,
        # we'll just rank them differently)
        major_matches = []
        
        for major_name in self.majors_data.get('programs', {}).keys():
            match_info = self.calculate_major_match(student_courses, major_name)
            
            # Only include majors where student has earned at least some credits
            if match_info['total_credits'] > 0:
                major_info = self.majors_data['programs'][major_name]
                
                # Check if this is the current major (compare different formats)
                is_current_major = (
                    major_name == current_major_code or
                    major_info.get('major_name', '') in current_major_code or
                    current_major_code in major_name
                )
                
                major_matches.append({
                    'major_name': major_name,
                    'degree_type': major_info.get('degree_type', 'N/A'),
                    'school': major_info.get('school_college', 'N/A'),
                    'credits_earned': match_info['total_credits'],
                    'courses_matched': match_info['course_count'],
                    'total_required_courses': match_info['total_required'],
                    'completion_percentage': round((match_info['course_count'] / match_info['total_required'] * 100) if match_info['total_required'] > 0 else 0, 1),
                    'matched_courses': match_info['matched_courses'],
                    'is_current_major': is_current_major
                })
        
        # Sort by credits earned (descending), but filter out current major
        major_matches = [m for m in major_matches if not m['is_current_major']]
        major_matches.sort(key=lambda x: (x['credits_earned'], x['courses_matched']), reverse=True)
        
        # Remove the is_current_major flag before returning
        for major in major_matches:
            del major['is_current_major']
        
        return {
            'student_info': student_info,
            'total_courses_passed': len(student_courses),
            'total_credits_earned': sum(c['credits'] for c in student_courses),
            'recommended_majors': major_matches[:top_n]
        }


def authenticate_student(student_id: str, password: str) -> bool:
    """Simple authentication (POC only - password is '1234' for all students)"""
    return password == "1234"


def test_random_students():
    """Test the recommender with 10 random students from the dataset."""
    import random
    
    # Initialize recommender using centralized paths
    enrollment_files = [str(f) for f in get_filtered_enrollment_files()]
    
    print(f"Loading data from {len(enrollment_files)} files...")
    print(f"Files found: {sorted([Path(f).name for f in enrollment_files])}")
    recommender = MajorRecommender(MAJORS_JSON, COURSES_JSON, enrollment_files)
    
    # Get unique student IDs
    unique_students = recommender.student_data['LID'].unique()
    print(f"Total rows in combined dataset: {len(recommender.student_data)}")
    print(f"Total unique students: {len(unique_students)}")
    print(f"Columns in dataset: {list(recommender.student_data.columns)}")
    
    # Select 10 random students
    random_students = random.sample(list(unique_students), min(10, len(unique_students)))
    
    print("\n" + "="*80)
    print("TESTING 10 RANDOM STUDENTS")
    print("="*80)
    
    for idx, student_id in enumerate(random_students, 1):
        print(f"\n{'='*80}")
        print(f"STUDENT {idx}: {student_id}")
        print(f"{'='*80}")
        
        try:
            # Get student info and courses first
            student_info = recommender.get_student_info(str(student_id))
            student_courses = recommender.get_student_courses(str(student_id))
            
            if student_info:
                # Debug: Check how many total records exist for this student
                student_all_records = recommender.student_data[recommender.student_data['LID'].astype(str) == str(student_id)]
                print(f"Name: {student_info['name']}")
                print(f"Class Standing: {student_info['class_standing']}")
                print(f"Current Major: {student_info['current_major']}")
                print(f"Total Records in Dataset: {len(student_all_records)}")
                print(f"Total Courses Passed: {len(student_courses)}")
                print(f"Total Credits Earned: {sum(c['credits'] for c in student_courses)}")
                
                # Debug: Show unique terms
                unique_terms = sorted(student_all_records['Term'].unique())
                print(f"Terms Found: {', '.join(map(str, unique_terms))}")
                
                # Display enrollment history
                print(f"\nEnrollment History (Passed Courses):")
                if student_courses:
                    # Sort by term
                    sorted_courses = sorted(student_courses, key=lambda x: x['term'])
                    for course in sorted_courses:
                        print(f"  - {course['course']} (Grade: {course['grade']}, Credits: {course['credits']}, Term: {course['term']})")
                else:
                    print("  No passed courses found")
                
                # Get recommendations
                results = recommender.recommend_majors(str(student_id), top_n=5)
                
                print(f"\nTop 5 Recommended Alternative Majors:")
                if results and results['recommended_majors']:
                    for rank, major in enumerate(results['recommended_majors'], 1):
                        print(f"\n  {rank}. {major['major_name']}")
                        print(f"     Degree: {major['degree_type']}")
                        print(f"     School: {major['school']}")
                        print(f"     Credits Earned: {major['credits_earned']}")
                        print(f"     Courses Matched: {major['courses_matched']}/{major['total_required_courses']}")
                        print(f"     Completion: {major['completion_percentage']}%")
                        print(f"     Matched Courses: {', '.join([c['course'] for c in major['matched_courses'][:5]])}{'...' if len(major['matched_courses']) > 5 else ''}")
                else:
                    print("  No recommendations found (student may not have passed courses matching any major requirements)")
            else:
                print(f"  ERROR: Student {student_id} not found in dataset")
                
        except Exception as e:
            print(f"  ERROR processing student {student_id}: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*80}")
    print("TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    test_random_students()
