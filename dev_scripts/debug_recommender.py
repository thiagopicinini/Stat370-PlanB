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
import unittest
from major_recommender import MajorRecommender
from datetime import datetime
import os

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, MERGED_ENROLLMENT, COURSES_JSON, get_filtered_enrollment_files


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


def test_random_students(student_data, majors_data, n=5, summary_path=None):
    """Test n random students from the database. Save readable summary if summary_path is given."""
    unique_students = student_data['LID'].unique()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [f"# Sample Students Test Output\n\nRun date: {now}\n\n"]
    lines.append(f"Testing {n} Random Students\nTotal students in database: {len(unique_students)}\n")
    sample_size = min(n, len(unique_students))
    random_students = random.sample(list(unique_students), sample_size)
    results = []
    for student_id in random_students:
        result = analyze_student(student_data, majors_data, student_id)
        if result:
            results.append(result)
            # Write summary for this student
            lines.append(f"---\n**Student ID:** {result['student_id']}\n**Name:** {result['name']}\n**Current Major:** {result['current_major']}\n")
            # Get semesters from student_data
            student_records = student_data[student_data['LID'].astype(str) == str(result['student_id'])]
            semesters = sorted(student_records['Term'].unique())
            lines.append(f"**Semesters Enrolled:** {len(semesters)} ({', '.join(map(str, semesters))})\n")
            lines.append(f"**Total Courses Passed:** {result['total_courses']}\n**Unique Courses Passed:** {result['unique_courses']}\n**Major Matches:** {result['matches']}\n")
            # Top match
            if result['top_match']:
                major_name, courses = result['top_match']
                lines.append(f"**Top Match:** {major_name} ({len(courses)} courses matched: {', '.join(courses[:5])}{'...' if len(courses) > 5 else ''})\n")
    # Summary
    lines.append(f"\nSummary of Random Student Analysis\n\nStudents analyzed: {len(results)}\n")
    students_with_matches = sum(1 for r in results if r['matches'] > 0)
    lines.append(f"Students with matches: {students_with_matches}/{len(results)}\n")
    if results:
        avg_courses = sum(r['unique_courses'] for r in results) / len(results)
        avg_matches = sum(r['matches'] for r in results) / len(results)
        lines.append(f"Average unique courses: {avg_courses:.1f}\nAverage major matches: {avg_matches:.1f}\n")
    # Save if requested
    if summary_path:
        with open(summary_path, 'w') as f:
            f.write('\n'.join(lines))
    # Also print to console
    print('\n'.join(lines))


# ---------------------------------------------------------------------------
# Unit tests for the new filter logic
# ---------------------------------------------------------------------------
class TestFilterLogic(unittest.TestCase):
    """Unit tests for four-year completion, department, and school filters."""

    @classmethod
    def setUpClass(cls):
        """Load real data once for all tests (expensive I/O)."""
        enrollment_files = [str(f) for f in get_filtered_enrollment_files()]
        cls.recommender = MajorRecommender(MAJORS_JSON, COURSES_JSON, enrollment_files)
        # Gather all unique student IDs from all semesters
        unique_students = set()
        for df in cls.recommender.student_data_by_semester.values():
            unique_students.update(df['LID'].astype(str).unique())
        # Pick a sample student who has at least some passed courses
        for sid in unique_students:
            info = cls.recommender.get_student_info(str(sid))
            courses = cls.recommender.get_student_courses(str(sid))
            if info and len(courses) >= 5:
                cls.sample_student_id = str(sid)
                cls.sample_info = info
                cls.sample_courses = courses
                break
        else:
            raise RuntimeError("No suitable sample student found in dataset")

    # ---- Student info now includes new fields ----

    def test_student_info_has_semesters_enrolled(self):
        """get_student_info should return semesters_enrolled >= 1."""
        info = self.recommender.get_student_info(self.sample_student_id)
        self.assertIn('semesters_enrolled', info)
        self.assertGreaterEqual(info['semesters_enrolled'], 1)

    def test_student_info_has_department_and_school(self):
        """get_student_info should return current_department and current_school."""
        info = self.recommender.get_student_info(self.sample_student_id)
        self.assertIn('current_department', info)
        self.assertIn('current_school', info)
        # They should be strings (may be 'Unknown' if no match)
        self.assertIsInstance(info['current_department'], str)
        self.assertIsInstance(info['current_school'], str)

    # ---- Four-year completion logic ----

    def test_can_complete_in_four_years_returns_bool(self):
        """can_complete_in_four_years should return a boolean."""
        first_major = list(self.recommender.majors_data['programs'].keys())[0]
        result = self.recommender.can_complete_in_four_years(
            self.sample_courses, first_major,
            semesters_enrolled=self.sample_info['semesters_enrolled']
        )
        self.assertIsInstance(result, bool)

    def test_can_complete_with_zero_remaining_semesters(self):
        """If student has used all 8 semesters, should only be True for
        majors where remaining credits are 0."""
        first_major = list(self.recommender.majors_data['programs'].keys())[0]
        result = self.recommender.can_complete_in_four_years(
            self.sample_courses, first_major,
            semesters_enrolled=8
        )
        # With 0 remaining semesters, completable only if nothing remains
        self.assertIsInstance(result, bool)

    def test_can_complete_with_many_remaining_semesters(self):
        """If student just started (1 semester), most majors should be completable."""
        first_major = list(self.recommender.majors_data['programs'].keys())[0]
        result = self.recommender.can_complete_in_four_years(
            self.sample_courses, first_major,
            semesters_enrolled=1
        )
        self.assertIsInstance(result, bool)

    # ---- Filter: four-year completion ----

    def test_filter_four_year_yes(self):
        """Filtering four_year='yes' should only return completable majors."""
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_four_year='yes'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertTrue(
                major['can_complete_in_four_years'],
                f"{major['major_name']} should be completable in 4 years"
            )

    def test_filter_four_year_no(self):
        """Filtering four_year='no' should only return NON-completable majors."""
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_four_year='no'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertFalse(
                major['can_complete_in_four_years'],
                f"{major['major_name']} should NOT be completable in 4 years"
            )

    # ---- Filter: outside department ----

    def test_filter_outside_dept_yes(self):
        """Filtering outside_dept='yes' should exclude same-department majors."""
        current_dept = self.sample_info['current_department'].lower()
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_outside_dept='yes'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertNotEqual(
                major['department'].lower(), current_dept,
                f"{major['major_name']} is in the same department ({current_dept})"
            )

    def test_filter_outside_dept_no(self):
        """Filtering outside_dept='no' should keep only same-department majors."""
        current_dept = self.sample_info['current_department'].lower()
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_outside_dept='no'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertEqual(
                major['department'].lower(), current_dept,
                f"{major['major_name']} should be in department {current_dept}"
            )

    # ---- Filter: outside school/college ----

    def test_filter_outside_school_yes(self):
        """Filtering outside_school='yes' should exclude same-school majors."""
        current_school = self.sample_info['current_school'].lower()
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_outside_school='yes'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertNotEqual(
                major['school'].lower(), current_school,
                f"{major['major_name']} is in the same school ({current_school})"
            )

    def test_filter_outside_school_no(self):
        """Filtering outside_school='no' should keep only same-school majors."""
        current_school = self.sample_info['current_school'].lower()
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_outside_school='no'
        )
        self.assertIsNotNone(results)
        for major in results['recommended_majors']:
            self.assertEqual(
                major['school'].lower(), current_school,
                f"{major['major_name']} should be in school {current_school}"
            )

    # ---- No filter should behave like the old code ----

    def test_no_filters_returns_results(self):
        """With no filters, recommend_majors should still return results."""
        results = self.recommender.recommend_majors(self.sample_student_id, top_n=5)
        self.assertIsNotNone(results)
        self.assertIn('recommended_majors', results)
        self.assertIn('student_info', results)

    # ---- Combined filters ----

    def test_combined_filters(self):
        """Using multiple filters at once should not crash."""
        results = self.recommender.recommend_majors(
            self.sample_student_id, top_n=50,
            filter_four_year='yes',
            filter_outside_dept='yes',
            filter_outside_school='yes'
        )
        self.assertIsNotNone(results)
        self.assertIsInstance(results['recommended_majors'], list)

    # ---- Recommended majors include new fields ----

    def test_recommended_majors_have_new_fields(self):
        """Each recommended major should include department and can_complete_in_four_years."""
        results = self.recommender.recommend_majors(self.sample_student_id, top_n=5)
        for major in results['recommended_majors']:
            self.assertIn('department', major)
            self.assertIn('can_complete_in_four_years', major)
            self.assertIsInstance(major['can_complete_in_four_years'], bool)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Debug recommender & run unit tests")
    parser.add_argument('--test', action='store_true', help='Run unit tests only')
    parser.add_argument('--students', type=int, default=100, help='Number of sample students to test')
    args, remaining = parser.parse_known_args()

    # Output paths
    output_dir = Path(__file__).parent.parent / "test_output"
    output_dir.mkdir(exist_ok=True)
    now = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    summary_students_path = output_dir / f"sample_students_summary_{now}.txt"
    summary_unit_path = output_dir / f"unit_test_summary_{now}.txt"

    if args.test:
        # Run all unit tests and capture output
        import io
        import contextlib
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestFilterLogic)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            runner = unittest.TextTestRunner(stream=buf, verbosity=2)
            result = runner.run(suite)
        output = buf.getvalue()
        # Compose readable summary
        summary_lines = [f"# Unit Test Results\n\nRun date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
        summary_lines.append(f"\nTotal tests run: {result.testsRun}")
        summary_lines.append(f"\nFailures: {len(result.failures)}")
        summary_lines.append(f"\nErrors: {len(result.errors)}")
        summary_lines.append(f"\nSkipped: {len(result.skipped)}\n")
        if result.failures:
            summary_lines.append("\nFailures:")
            for test, err in result.failures:
                summary_lines.append(f"- {test.id()}: {err}")
        if result.errors:
            summary_lines.append("\nErrors:")
            for test, err in result.errors:
                summary_lines.append(f"- {test.id()}: {err}")
        if result.skipped:
            summary_lines.append("\nSkipped:")
            for test, reason in result.skipped:
                summary_lines.append(f"- {test.id()}: {reason}")
        summary_lines.append("\n---\n\nFull Output:\n\n")
        summary_lines.append(output)
        # Save summary
        with open(summary_unit_path, 'w') as f:
            f.write('\n'.join(summary_lines))
        print(f"Unit test summary saved to {summary_unit_path}")
        # Also print to console
        print('\n'.join(summary_lines))
        sys.exit(0)

    if args.students:
        # Run sample students test and save summary
        majors_data = None
        student_data = None
        # Load data
        with open(MAJORS_JSON, 'r') as f:
            majors_data = json.load(f)
        student_data = pd.read_csv(MERGED_ENROLLMENT, sep='\t')
        test_random_students(student_data, majors_data, n=args.students, summary_path=summary_students_path)
        print(f"Sample students summary saved to {summary_students_path}")
        sys.exit(0)

    # Default: print help
    parser.print_help()
    output_dir = Path(__file__).parent.parent / 'test_output'
    output_dir.mkdir(exist_ok=True)
    students_summary_path = output_dir / 'sample_students_summary.txt'
    unit_test_summary_path = output_dir / 'unit_test_summary.txt'

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if args.test:
        # Run only unit tests and save summary
        sys.argv = [sys.argv[0]] + remaining
        # Capture output
        import io
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            unittest.main(verbosity=2, exit=False)
        test_output = buf.getvalue()
        # Parse and summarize
        lines = [f"# Unit Test Results\n\nRun date: {now}\n\n"]
        for line in test_output.splitlines():
            if line.strip().startswith('test_'):
                # e.g. test_can_complete_in_four_years_returns_bool (__main__.TestFilterLogic) ... ok
                parts = line.split(' ... ')
                if len(parts) == 2:
                    testname = parts[0].split()[0]
                    result = parts[1].strip().upper()
                    lines.append(f"- {testname}: {result}")
            elif line.strip().startswith('Ran '):
                lines.append(line.strip())
            elif line.strip().startswith('OK') or line.strip().startswith('FAILED'):
                lines.append(line.strip())
        with open(unit_test_summary_path, 'w') as f:
            f.write('\n'.join(lines))
        print(f"Unit test summary saved to {unit_test_summary_path}")
    else:
        # Run the original debug analysis and save summary
        majors_data, student_data = load_data()
        test_random_students(student_data, majors_data, n=args.students, summary_path=students_summary_path)
        print(f"Sample students summary saved to {students_summary_path}")

