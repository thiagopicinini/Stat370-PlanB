"""
Major Recommender System

Analyzes student transcripts and recommends alternative majors based on
credits earned toward major requirements. Uses enrollment data and scraped
major requirements to calculate best-fit alternative majors for students.
"""
import json
import sys
import math
from pathlib import Path
import pandas as pd
from collections import defaultdict
from typing import Dict, List, Tuple, Union, Optional

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
        
        # Load the shorthand major map (created from enrollment data)
        shorthand_map_file = Path(__file__).parent / 'major_shorthand_map.json'
        if shorthand_map_file.exists():
            shorthand_map_data = self._load_json(str(shorthand_map_file))
            self.shorthand_to_full = shorthand_map_data.get('shorthand_to_full', {})
        else:
            self.shorthand_to_full = {}
        
        self.student_data_by_semester = self._load_student_data_by_semester(enrollment_files)

    def _extract_semester_from_file(self, file_path: Union[str, Path], df: pd.DataFrame) -> str:
        """Extract semester code from file name or DataFrame content."""
        fname = str(file_path)
        for code in ['Fall2016', 'Fall2017', 'Fall2018', 'Fall2019', 'Fall2020',
                     'Spring2017', 'Spring2018', 'Spring2019', 'Spring2020', 'Spring2021']:
            if code in fname:
                return code
        if 'Term' in df.columns and not df.empty:
            return str(df['Term'].iloc[0])
        return fname

    def _load_student_data_by_semester(self, enrollment_files: List[Union[str, Path]]) -> Dict[str, pd.DataFrame]:
        data_by_semester = {}
        for file in enrollment_files:
            df = pd.read_csv(file, sep='\t')
            if 'Career' in df.columns:
                df = df[df['Career'] == 'UGRD']
            semester_key = self._extract_semester_from_file(file, df)
            data_by_semester[semester_key] = df
            print(f"Loaded {semester_key}: {len(df)} undergraduate rows")
        return data_by_semester
        
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
        """Get student information including department and school of current major.
        
        Logic:
        1. Try Active_Plan_List first
        2. If not found, search Plan_List_Start_ofTerm_* columns
        3. Extract ONLY the major (not minor) from the plan code
        4. Use shorthand_to_full map to resolve major name
        5. Fall back to fuzzy matching if shorthand map doesn't have the code
        """
        all_records = []
        for df in self.student_data_by_semester.values():
            records = df[df['LID'].astype(str) == str(student_id)]
            if not records.empty:
                all_records.append(records)
        if not all_records:
            return None
        student_records = pd.concat(all_records, ignore_index=True)
        latest_record = student_records.sort_values('Term', ascending=False).iloc[0]
        
        # Try to find current major from Active_Plan_List first
        current_major = latest_record.get('Active_Plan_List', None)
        if pd.isna(current_major) or not current_major:
            # Fall back to Plan_List_Start_ofTerm_* columns
            plan_list_cols = [col for col in latest_record.index if col.startswith('Plan_List_Start_ofTerm_')]
            if plan_list_cols:
                for col in sorted(plan_list_cols, reverse=True):  # Start with latest term
                    val = latest_record[col]
                    if not pd.isna(val) and val:
                        current_major = val
                        break
        
        if pd.isna(current_major) or not current_major:
            current_major = 'Undeclared'
        else:
            current_major = str(current_major).strip()
        
        # Extract ONLY the major from the plan code (remove minors, certificates, etc.)
        # Format: "MAJOR-DEGREE,MINOR-MINR" or "MAJOR-DEGREE,CERT-CERT"
        # We want only the first part before the comma
        if ',' in current_major:
            current_major = current_major.split(',')[0].strip()
        
        current_department = 'Unknown'
        current_school = 'Unknown'
        
        # First, try to use the shorthand map to resolve the major name
        shorthand_str = str(current_major).strip()
        if shorthand_str in self.shorthand_to_full:
            # Got a match in the shorthand map - use it
            full_major_name = self.shorthand_to_full[shorthand_str]
            # Now search for this major in the programs data
            for prog_name, prog_info in self.majors_data.get('programs', {}).items():
                if prog_name.lower() == full_major_name.lower():
                    current_department = prog_info.get('department', 'Unknown')
                    current_school = prog_info.get('school_college', 'Unknown')
                    break
        else:
            # Fallback: use fuzzy matching for majors not in the shorthand map
            # Extract the major code prefix (e.g., "BIOL" from "BIOL-BS")
            major_code_prefix = str(current_major).split('-')[0].upper() if current_major != 'Undeclared' else ''
            
            for prog_name, prog_info in self.majors_data.get('programs', {}).items():
                plan_code = str(current_major).lower().strip()
                major_name_base = prog_info.get('major_name', '').lower()
                prog_name_lower = prog_name.lower().strip()
                
                # Try multiple matching strategies
                # Strategy 1: Exact match on program name
                if prog_name_lower == plan_code:
                    current_department = prog_info.get('department', 'Unknown')
                    current_school = prog_info.get('school_college', 'Unknown')
                    break
                # Strategy 2: Look for major_name in the plan code (e.g., "acct" in "acct-bba")
                if major_name_base and major_name_base in plan_code.replace('-', ' '):
                    current_department = prog_info.get('department', 'Unknown')
                    current_school = prog_info.get('school_college', 'Unknown')
                    break
                # Strategy 3: Look for plan code in program name  (e.g., "acct" in "Accounting (BBA)")
                if plan_code.replace('-', ' ') in prog_name_lower:
                    current_department = prog_info.get('department', 'Unknown')
                    current_school = prog_info.get('school_college', 'Unknown')
                    break
                # Strategy 4: Match by major code prefix (e.g., "BIOL" from "BIOL-BS" matches "Biology (BS)")
                if major_code_prefix:
                    if major_name_base.startswith(major_code_prefix[:3].lower()) or \
                       major_name_base.startswith(major_code_prefix[:4].lower()):
                        current_department = prog_info.get('department', 'Unknown')
                        current_school = prog_info.get('school_college', 'Unknown')
                        break
        
        semesters_enrolled = int(student_records['Term'].nunique())
        return {
            'student_id': student_id,
            'name': latest_record.get('Name', 'Unknown'),
            'current_major': current_major,
            'class_standing': latest_record.get('Academic_Level', 'Unknown'),
            'current_department': current_department,
            'current_school': current_school,
            'semesters_enrolled': semesters_enrolled
        }
    
    def get_student_courses(self, student_id: str) -> List[Dict]:
        """Get all courses a student has taken and passed (searching all semesters).
        
        Normalizes course codes to use regular spaces for consistent matching.
        """
        all_records = []
        for df in self.student_data_by_semester.values():
            records = df[df['LID'].astype(str) == str(student_id)]
            if not records.empty:
                all_records.append(records)
        if not all_records:
            return []
        student_records = pd.concat(all_records, ignore_index=True)
        passed_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'P']
        passed_courses = student_records[student_records['FinalGrade'].isin(passed_grades)]
        courses = []
        seen_courses = set()
        for _, row in passed_courses.iterrows():
            subject = str(row.get('Subject', '')).strip()
            catalog_num = str(row.get('CatalogNumber', '')).strip()
            course_code = f"{subject} {catalog_num}" if subject and catalog_num else None
            if course_code and course_code != 'nan nan':
                # Normalize to regular space (in case data has non-breaking spaces)
                course_code = course_code.replace('\xa0', ' ')
                course_term_key = (course_code, row['Term'])
                if course_term_key not in seen_courses:
                    seen_courses.add(course_term_key)
                    credits = row.get('Units_Earned', 0)
                    if pd.isna(credits) or credits == 0:
                        credits = 3
                    courses.append({
                        'course': course_code,
                        'credits': credits,
                        'grade': row['FinalGrade'],
                        'term': row['Term']
                    })
        return courses
    
    def _extract_all_courses_from_requirements(self, requirements: List[Dict]) -> set:
        """Extract all unique course codes from a major's requirements recursively.
        
        Handles:
        - Regular course objects with 'code' key
        - Nested subgroups (elective groups)
        - Non-breaking spaces in course codes (\\xa0)
        """
        all_courses = set()
        
        for req_group in requirements:
            if not isinstance(req_group, dict):
                continue
            
            # Get courses from this group
            courses = req_group.get('courses', [])
            for course in courses:
                if isinstance(course, dict):
                    code = course.get('code', '').strip()
                    # Normalize non-breaking spaces to regular spaces
                    code = code.replace('\xa0', ' ')
                    if code and code != ' ':
                        all_courses.add(code)
                elif isinstance(course, str):
                    code = course.strip()
                    # Normalize non-breaking spaces to regular spaces
                    code = code.replace('\xa0', ' ')
                    if code and code != ' ':
                        all_courses.add(code)
            
            # Recursively extract from subgroups (elective groups)
            subgroups = req_group.get('subgroups', [])
            if subgroups:
                all_courses.update(self._extract_all_courses_from_requirements(subgroups))
        
        return all_courses
    
    def calculate_major_match(self, student_courses: List[Dict], major_name: str) -> Dict:
        """
        Calculate how many credits a student has earned toward a specific major.
        Works with the new scrape_v2 structured requirements format with selection rules.
        
        Handles OR requirements correctly: if a major requires "STAT 203 or STAT 335",
        only ONE of those courses counts toward the requirement (not both).
        """
        if major_name not in self.majors_data.get('programs', {}):
            return {'matched_courses': [], 'total_credits': 0, 'course_count': 0, 'total_required': 0}
        
        major_info = self.majors_data['programs'][major_name]
        
        # Parse requirements into a list of requirement items (each can be a single course or OR group)
        requirement_items = []  # List of either single courses or OR groups
        
        if 'requirements' in major_info:
            # New structured format from scrape_v2 - extract using existing method
            all_required_courses = self._extract_all_courses_from_requirements(major_info.get('requirements', []))
            # For new format, just treat all courses as individual requirements
            requirement_items = list(all_required_courses)
        else:
            # Fallback to old format with special handling for OR requirements
            required_courses_list = major_info.get('required_courses', [])
            
            for req_course in required_courses_list:
                if isinstance(req_course, str):
                    # Check for "or" pattern like "STAT 203 or STAT 335"
                    cleaned = req_course.replace('\xa0', ' ')
                    if ' or ' in cleaned:
                        # This is an OR group - store as a list of options
                        or_options = []
                        for code in cleaned.split(' or '):
                            code_clean = code.strip()
                            if not code_clean.startswith('['):
                                or_options.append(code_clean)
                        if or_options:
                            requirement_items.append(or_options)
                    else:
                        # Single course requirement
                        code_clean = cleaned.strip()
                        if not code_clean.startswith('['):
                            requirement_items.append(code_clean)
                elif isinstance(req_course, dict) and 'options' in req_course:
                    # Handle dictionary format with 'options' key as an OR group
                    or_options = [code.replace('\xa0', ' ').strip() for code in req_course['options']]
                    if or_options:
                        requirement_items.append(or_options)
        
        # Create set of all possible required courses (for reference)
        all_required_courses = set()
        for item in requirement_items:
            if isinstance(item, list):
                all_required_courses.update(item)
            else:
                all_required_courses.add(item)
        
        # Get student's courses
        student_course_dict = {c['course'].strip().replace('\xa0', ' '): c for c in student_courses}
        
        # Match student courses to requirements
        matched_courses = []
        total_credits = 0
        satisfied_requirements = set()  # Track which requirement indices are satisfied
        
        for req_idx, requirement in enumerate(requirement_items):
            if isinstance(requirement, list):
                # OR group - find the FIRST student course that satisfies any option
                for course_option in requirement:
                    if course_option in student_course_dict:
                        student_course = student_course_dict[course_option]
                        matched_courses.append({
                            'course': course_option,
                            'credits': student_course.get('credits', 0)
                        })
                        try:
                            total_credits += int(student_course.get('credits', 0))
                        except (ValueError, TypeError):
                            total_credits += 0
                        satisfied_requirements.add(req_idx)
                        break  # Only count ONE course from the OR group
            else:
                # Single course requirement
                if requirement in student_course_dict:
                    student_course = student_course_dict[requirement]
                    matched_courses.append({
                        'course': requirement,
                        'credits': student_course.get('credits', 0)
                    })
                    try:
                        total_credits += int(student_course.get('credits', 0))
                    except (ValueError, TypeError):
                        total_credits += 0
                    satisfied_requirements.add(req_idx)
        
        return {
            'matched_courses': matched_courses,
            'total_credits': total_credits,
            'course_count': len(matched_courses),
            'total_required': len(requirement_items)
        }
    
    def can_complete_in_four_years(self, student_courses: List[Dict],
                                    major_name: str,
                                    semesters_enrolled: int,
                                    credits_per_semester: int = 18) -> bool:
        """
        Determine if a student can complete a prospective major plus university
        core requirements within 8 total semesters (4 years).

        Args:
            student_courses: Courses the student has already passed.
            major_name: Name of the prospective major.
            semesters_enrolled: Number of semesters the student has already been enrolled.
            credits_per_semester: Assumed max credits per semester (default 18).

        Returns:
            True if remaining requirements can fit in the remaining semesters.
        """
        total_semesters = 8  # 4 years = 8 semesters
        remaining_semesters = max(total_semesters - semesters_enrolled, 0)

        # Credits the student can still earn
        remaining_capacity = remaining_semesters * credits_per_semester

        # ---- Major remaining credits ----
        match_info = self.calculate_major_match(student_courses, major_name)
        major_info = self.majors_data['programs'].get(major_name, {})
        total_required = match_info['total_required']
        courses_matched = match_info['course_count']
        remaining_major_courses = total_required - courses_matched
        # Estimate 3 credits per remaining major course
        remaining_major_credits = remaining_major_courses * 3

        # ---- University core remaining credits ----
        core_info = self.majors_data.get('university_core', {})
        # Parse total core credit hours (approx 34-37, use 36 as midpoint)
        total_core_str = core_info.get('total_credit_hours', '')
        try:
            # Try to pull numeric value from string like "Approximately 34-37 credit hours"
            nums = [int(s) for s in total_core_str.split() if s.isdigit()]
            total_core_credits = sum(nums) // len(nums) if nums else 36
        except Exception:
            total_core_credits = 36

        # Estimate how many core credits the student has already satisfied.
        # Simpler heuristic: count student credits that are NOT major-matched
        matched_course_codes = {c['course'] for c in match_info['matched_courses']}
        total_student_credits = sum(c['credits'] for c in student_courses)
        major_matched_credits = match_info['total_credits']
        non_major_credits = total_student_credits - major_matched_credits
        core_credits_earned = min(non_major_credits, total_core_credits)
        remaining_core_credits = max(total_core_credits - core_credits_earned, 0)

        # Total remaining credits needed
        total_remaining = remaining_major_credits + remaining_core_credits

        return total_remaining <= remaining_capacity

    def recommend_majors(self, student_id: str, top_n: int = 5,
                         credits_per_semester: int = 18,
                         filter_four_year: Optional[str] = None,
                         filter_outside_dept: Optional[str] = None,
                         filter_outside_school: Optional[str] = None) -> Dict:
        """
        Recommend top N alternative majors for a student with optional filters.

        Args:
            student_id: The student LID.
            top_n: Number of recommendations to return.
            credits_per_semester: Maximum credits per semester (default 18). Can be customized.
            filter_four_year: 'yes' to keep only majors completable in 4 years,
                              'no' to keep only those that are NOT, None to skip.
            filter_outside_dept: 'yes' to exclude same-department majors,
                                 'no' to keep only same-department, None to skip.
            filter_outside_school: 'yes' to exclude same-school majors,
                                   'no' to keep only same-school, None to skip.
        
        NOTE: When filters are applied, we fetch up to 3x the requested top_n majors,
              apply filters, then return top_n results. This ensures filters don't
              reduce results below the requested number when possible.
        """
        
        # When filters are active, fetch more candidates to ensure we get top_n results after filtering
        has_filters = any([filter_four_year, filter_outside_dept, filter_outside_school])
        fetch_n = min(top_n * 3, 100) if has_filters else top_n
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
        
        current_department = student_info.get('current_department', 'Unknown')
        current_school = student_info.get('current_school', 'Unknown')
        semesters_enrolled = student_info.get('semesters_enrolled', 0)
        
        # Resolve current major name using shorthand map
        # This is the PRIMARY place to identify the current major program name
        current_major_program_name = None
        if current_major_code in self.shorthand_to_full:
            current_major_program_name = self.shorthand_to_full[current_major_code]
        else:
            # Fallback: extract major code prefix (e.g., "ACCT" from "ACCT-BBA")
            current_major_prefix = current_major_code.split('-')[0].upper() if current_major_code != 'Undeclared' else ''
            # We'll use this for fuzzy matching below
        
        # Calculate match for all majors
        major_matches = []
        
        for major_name in self.majors_data.get('programs', {}).keys():
            match_info = self.calculate_major_match(student_courses, major_name)
            
            # Only include majors where student has matched at least one course
            # (Don't require total_credits > 0, as credits may be 0 if courses aren't in data)
            if match_info['course_count'] > 0:
                major_info = self.majors_data['programs'][major_name]
                major_dept = major_info.get('department', 'N/A')
                major_school = major_info.get('school_college', 'N/A')
                
                # Check if this is the current major using the shorthand map FIRST
                is_current_major = False
                
                if current_major_program_name:
                    # We have a resolved major name from the shorthand map
                    is_current_major = (major_name.lower() == current_major_program_name.lower())
                else:
                    # Fallback to prefix matching if we don't have a shorthand map entry
                    major_base_name = major_name.split('(')[0].strip().lower()
                    major_base_name_no_space = major_base_name.replace(' ', '')
                    major_name_base = major_info.get('major_name', '').lower()
                    
                    # For prefix matching: only match if major name STARTS with the prefix abbreviation
                    prefix_abbrev = current_major_prefix.lower()[:3]  # First 3 chars for matching
                    major_starts_with_prefix = (
                        major_name_base.startswith(prefix_abbrev) or
                        major_base_name_no_space.startswith(prefix_abbrev)
                    )
                    
                    # Additional check: make sure it's not a specialized variant
                    # e.g., Accounting is OK, but "Accounting and Analytics" is NOT just Accounting
                    is_variant = ' and ' in major_name or len(major_name.split('(')[0].split()) > 2
                    
                    prefix_matches = (
                        current_major_prefix and major_starts_with_prefix and not is_variant
                    )
                    
                    is_current_major = (
                        ((major_dept.lower() == current_department.lower() and 
                          major_school.lower() == current_school.lower()) and
                         (major_base_name == major_info.get('major_name', '').lower())) or
                        prefix_matches
                    )

                # --- Apply filters ---

                # Four-year completion filter
                completable = self.can_complete_in_four_years(
                    student_courses, major_name, semesters_enrolled, credits_per_semester
                ) if student_courses else False

                if filter_four_year == 'yes' and not completable:
                    continue
                if filter_four_year == 'no' and completable:
                    continue

                # Outside department filter
                same_dept = (major_dept.lower() == current_department.lower())
                if filter_outside_dept == 'yes' and same_dept:
                    continue
                if filter_outside_dept == 'no' and not same_dept:
                    continue

                # Outside school filter
                same_school = (major_school.lower() == current_school.lower())
                if filter_outside_school == 'yes' and same_school:
                    continue
                if filter_outside_school == 'no' and not same_school:
                    continue

                major_matches.append({
                    'major_name': major_name,
                    'degree_type': major_info.get('degree_type', 'N/A'),
                    'school': major_school,
                    'department': major_dept,
                    'credits_earned': match_info['total_credits'],
                    'courses_matched': match_info['course_count'],
                    'total_required_courses': match_info['total_required'],
                    'completion_percentage': round((match_info['course_count'] / match_info['total_required'] * 100) if match_info['total_required'] > 0 else 0, 1),
                    'matched_courses': match_info['matched_courses'],
                    'is_current_major': is_current_major,
                    'can_complete_in_four_years': completable
                })
        
        # Sort by courses matched (descending), then credits earned, but filter out current major
        major_matches = [m for m in major_matches if not m['is_current_major']]
        # Primary sort: courses_matched (descending), secondary: credits_earned (descending)
        # This ensures we prioritize majors where student has matched more requirements
        major_matches.sort(key=lambda x: (x['courses_matched'], x['credits_earned']), reverse=True)
        
        # Remove the is_current_major flag before returning
        for major in major_matches:
            del major['is_current_major']
        
        # Trim to top_n AFTER all filtering is applied
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
    
    # Get unique student IDs from all semester data
    all_student_data = pd.concat(list(recommender.student_data_by_semester.values()), ignore_index=True)
    unique_students = all_student_data['LID'].unique()
    print(f"Total rows in combined dataset: {len(all_student_data)}")
    print(f"Total unique students: {len(unique_students)}")
    print(f"Columns in dataset: {list(all_student_data.columns)}")
    
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
                student_all_records = all_student_data[all_student_data['LID'].astype(str) == str(student_id)]
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
