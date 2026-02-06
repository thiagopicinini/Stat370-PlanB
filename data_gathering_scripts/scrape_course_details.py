"""
Scrape course details from Loyola catalog.

This script extracts detailed information for all courses referenced in major
requirements and enrollment data, including titles, descriptions, credits,
prerequisites, and corequisites.
"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON, MERGED_ENROLLMENT, COURSES_JSON


def extract_course_codes_from_majors(majors_file):
    """
    Extract all unique course codes from the majors JSON file
    
    Args:
        majors_file: Path to the bachelors_majors_web.json file
    
    Returns:
        set: Set of all unique course codes (e.g., 'ACCT 201', 'COMM 100')
    """
    course_codes = set()
    
    with open(majors_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for program_key, program_data in data.get('programs', {}).items():
        required_courses = program_data.get('required_courses', [])
        
        for item in required_courses:
            if isinstance(item, str):
                # Handle regular course codes and OR relationships
                if item.startswith('[Elective:'):
                    continue
                
                # Split by 'or' to handle OR relationships
                parts = item.split(' or ')
                for part in parts:
                    part = part.strip()
                    # Match course codes like "ACCT 201" or "MATH 110"
                    match = re.match(r'^([A-Z]{2,5})\s+(\d{3}[A-Z]?)$', part)
                    if match:
                        course_codes.add(part)
            elif isinstance(item, dict) and 'options' in item:
                # Handle options within electives (select any courses)
                for option in item['options']:
                    # Split by 'or' to handle OR relationships
                    parts = option.split(' or ')
                    for part in parts:
                        part = part.strip()
                        match = re.match(r'^([A-Z]{2,5})\s+(\d{3}[A-Z]?)$', part)
                        if match:
                            course_codes.add(part)
    
    return course_codes

def extract_course_codes_from_enrollment(enrollment_file):
    """
    Extract all unique course codes from the enrollment TSV file
    
    Args:
        enrollment_file: Path to the merged_student_enrollment.tsv file
    
    Returns:
        set: Set of all unique course codes found in enrollment data
    """
    course_codes = set()
    
    try:
        with open(enrollment_file, 'r', encoding='utf-8') as f:
            # Read TSV file
            lines = f.readlines()
            
            # Skip header if present
            for line in lines[1:]:
                # Split by tab
                fields = line.strip().split('\t')
                
                # Check each field for course codes
                for field in fields:
                    # Look for patterns like "ACCT 201", "MATH 110", etc.
                    matches = re.findall(r'\b([A-Z]{2,5})\s+(\d{3}[A-Z]?)\b', field)
                    for dept, num in matches:
                        course_codes.add(f"{dept} {num}")
        
        return course_codes
    
    except FileNotFoundError:
        print(f"  Warning: Enrollment file not found: {enrollment_file}")
        return set()
    except Exception as e:
        print(f"  Warning: Error reading enrollment file: {str(e)[:50]}")
        return set()

def get_course_departments(course_codes):
    """
    Extract unique department codes from course codes
    
    Args:
        course_codes: Set of course codes
    
    Returns:
        set: Set of department codes (e.g., 'ACCT', 'COMM', 'MATH')
    """
    departments = set()
    
    for code in course_codes:
        match = re.match(r'^([A-Z]{2,5})\s+(\d{3}[A-Z]?)$', code)
        if match:
            departments.add(match.group(1))
    
    return departments

def scrape_course_details(course_code):
    """
    Scrape course details from the Loyola catalog
    
    Args:
        course_code: Course code like "ACCT 201"
    
    Returns:
        dict: Course details including title, description, credits, prerequisites
    """
    # Construct the search URL
    search_url = f"https://catalog.luc.edu/search/?P={course_code.replace(' ', '%20')}"
    
    course_data = {
        "course_code": course_code,
        "course_url": search_url,
        "course_title": None,
        "course_description": None,
        "credit_hours": None,
        "prerequisites": [],
        "corequisites": [],
        "course_equivalencies": []
    }
    
    try:
        time.sleep(0.3)  # Be polite to the server
        
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the course block - it's an article with class 'search-courseresult'
        course_block = soup.find('article', class_='search-courseresult')
        
        if not course_block:
            return None
        
        # Get course title from span.detail-title
        title_elem = course_block.find('span', class_='detail-title')
        if title_elem:
            course_data['course_title'] = title_elem.get_text(strip=True)
        
        # Get credit hours from span.detail-hours_html
        hours_elem = course_block.find('span', class_='detail-hours_html')
        if hours_elem:
            hours_text = hours_elem.get_text(strip=True)
            # Extract number from "(3 Credit Hours)"
            match = re.search(r'\((\d+(?:\.\d+)?)\s*Credit Hours?\)', hours_text)
            if match:
                course_data['credit_hours'] = match.group(1).strip()
        
        # Get course description from div.courseblockextra
        desc_elem = course_block.find('div', class_='courseblockextra')
        if desc_elem:
            course_data['course_description'] = desc_elem.get_text(strip=True)
        
        # Get prerequisites from span.detail-prereqs
        prereq_elem = course_block.find('span', class_='detail-prereqs')
        if prereq_elem:
            prereq_text = prereq_elem.get_text(strip=True)
            # Remove the "Pre-requisites:" label
            prereq_text = re.sub(r'^Pre-requisites?:\s*', '', prereq_text, flags=re.IGNORECASE)
            if prereq_text:
                course_data['prerequisites'] = extract_prerequisite_courses(prereq_text)
        
        # Get corequisites from span.detail-coreqs (if exists)
        coreq_elem = course_block.find('span', class_='detail-coreqs')
        if coreq_elem:
            coreq_text = coreq_elem.get_text(strip=True)
            coreq_text = re.sub(r'^Co-requisites?:\s*', '', coreq_text, flags=re.IGNORECASE)
            if coreq_text:
                course_data['corequisites'] = extract_prerequisite_courses(coreq_text)
        
        # Get course equivalencies from span.detail-equiv
        equiv_elem = course_block.find('span', class_='detail-equiv')
        if equiv_elem:
            equiv_text = equiv_elem.get_text(strip=True)
            # Remove the "Course equivalencies:" label
            equiv_text = re.sub(r'^Course equivalenc(?:ies|y):\s*', '', equiv_text, flags=re.IGNORECASE)
            if equiv_text:
                # Split by multiple delimiters: /, comma, semicolon, 'and', 'or'
                equiv_courses = re.split(r'[/,;]|\s+and\s+|\s+or\s+', equiv_text)
                course_data['course_equivalencies'] = [c.strip() for c in equiv_courses if c.strip()]
        
        return course_data
        
    except requests.Timeout:
        print(f"    Timeout for {course_code}")
        return None
    except requests.RequestException as e:
        print(f"    Network error for {course_code}: {str(e)[:50]}")
        return None
    except Exception as e:
        print(f"    Error scraping {course_code}: {str(e)[:50]}")
        return None

def extract_prerequisite_courses(prereq_text):
    """
    Extract course codes from prerequisite text, removing grade/standing requirements
    
    Args:
        prereq_text: Text describing prerequisites
    
    Returns:
        list: List of prerequisite course codes or simple conditions
    """
    prerequisites = []
    
    # Find all course codes in the text
    # Match patterns like "ACCT 201", "MATH 110", etc.
    course_matches = re.findall(r'\b([A-Z]{2,5})\s+(\d{3}[A-Z]?)\b', prereq_text)
    
    if course_matches:
        # Extract just the course codes, removing duplicates while preserving order
        seen = set()
        for dept, num in course_matches:
            course_code = f"{dept} {num}"
            if course_code not in seen:
                prerequisites.append(course_code)
                seen.add(course_code)
    
    # If no specific courses found but there's meaningful text, store simplified version
    if not prerequisites and prereq_text:
        # Clean up common prerequisite text patterns
        cleaned = prereq_text
        
        # Remove grade requirements
        cleaned = re.sub(r'(?:with\s+)?(?:a\s+)?(?:minimum\s+)?grade\s+of\s+["\']?[A-Z][+-]?["\']?\s*(?:or\s+(?:higher|better))?\s*(?:in|for)?\s*', '', cleaned, flags=re.IGNORECASE)
        
        # Remove standing requirements if they're the only thing left
        if re.match(r'^(?:Freshman|Sophomore|Junior|Senior)\s+standing\s*(?:or\s+above)?\s*;?\s*$', cleaned, flags=re.IGNORECASE):
            return []  # Don't include just standing requirements
        
        # Keep meaningful requirements like "Minimum X earned hours" or "Permission of instructor"
        if cleaned.strip() and len(cleaned.strip()) > 5:
            prerequisites.append(cleaned.strip())
    
    return prerequisites

def main():
    """
    Main function to scrape all course details and save to JSON.
    """
    majors_file = MAJORS_JSON
    enrollment_file = MERGED_ENROLLMENT
    output_file = COURSES_JSON
    
    print("="*80)
    print("SCRAPING COURSE DETAILS FROM LOYOLA CATALOG")
    print("="*80)
    
    # Step 1: Extract all course codes from majors
    print("\nStep 1: Extracting course codes from majors data...")
    course_codes_from_majors = extract_course_codes_from_majors(majors_file)
    print(f"  Found {len(course_codes_from_majors)} unique course codes in majors")
    print(f"  (Including all OR options and elective selections)")
    
    # Step 2: Extract course codes from enrollment data
    print("\nStep 2: Extracting course codes from enrollment data...")
    course_codes_from_enrollment = extract_course_codes_from_enrollment(enrollment_file)
    print(f"  Found {len(course_codes_from_enrollment)} unique course codes in enrollment data")
    
    # Combine both sources
    all_course_codes = course_codes_from_majors | course_codes_from_enrollment
    print(f"\nCombined total: {len(all_course_codes)} unique courses to scrape")
    
    # Step 3: Extract department codes
    print("\nStep 3: Identifying course departments...")
    departments = get_course_departments(all_course_codes)
    print(f"  Found {len(departments)} unique departments: {', '.join(sorted(departments))}")
    
    # Step 4: Use combined course list
    print("\nStep 4: Preparing course list...")
    all_courses_to_check = all_course_codes
    
    print(f"  Total courses to check: {len(all_courses_to_check)}")
    print(f"  (From majors requirements + enrollment records)")
    
    # Step 5: Scrape course details
    print("\nStep 5: Scraping course details...")
    courses_data = {}
    found_count = 0
    not_found_count = 0
    
    # Sort courses for organized output
    sorted_courses = sorted(all_courses_to_check)
    total = len(sorted_courses)
    
    for idx, course_code in enumerate(sorted_courses, 1):
        if idx % 50 == 0 or idx == 1:
            print(f"\n  Progress: {idx}/{total} courses processed ({found_count} found, {not_found_count} not found)")
        
        course_data = scrape_course_details(course_code)
        
        if course_data and course_data.get('course_title'):
            courses_data[course_code] = course_data
            found_count += 1
            if idx % 50 == 1 or idx <= 5:  # Show first few and every 50th
                print(f"  {course_code}: {course_data['course_title']}")
        else:
            not_found_count += 1
    
    print(f"\n  Final count: {found_count} courses found, {not_found_count} not found")
    
    # Step 6: Save to JSON
    print("\nStep 6: Saving course data to JSON...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(courses_data, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved to: {output_file}")
    
    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total courses checked: {total}")
    print(f"Courses found: {found_count}")
    print(f"Courses not found: {not_found_count}")
    print(f"Success rate: {(found_count/total*100):.1f}%")
    
    # Count courses by department
    dept_counts = defaultdict(int)
    for course_code in courses_data.keys():
        match = re.match(r'^([A-Z]{2,5})\s+(\d{3}[A-Z]?)$', course_code)
        if match:
            dept_counts[match.group(1)] += 1
    
    print(f"\nCourses found by department:")
    for dept in sorted(dept_counts.keys()):
        print(f"  {dept}: {dept_counts[dept]} courses")
    
    # Count courses with prerequisites
    with_prereqs = sum(1 for c in courses_data.values() if c.get('prerequisites'))
    print(f"\nCourses with prerequisites: {with_prereqs} ({with_prereqs/found_count*100:.1f}%)")
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
