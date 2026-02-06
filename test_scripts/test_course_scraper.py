"""
Test script for course scraping functionality.

This script tests the course detail scraper on a sample set of courses
from different departments to validate the scraping logic.
"""
import json
import re
from bs4 import BeautifulSoup
import requests
import time


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
        "course_title": None,
        "course_description": None,
        "credit_hours": None,
        "prerequisites": [],
        "corequisites": [],
        "course_equivalencies": []
    }
    
    try:
        print(f"\n{'='*80}")
        print(f"Testing: {course_code}")
        print(f"URL: {search_url}")
        print(f"{'='*80}")
        
        time.sleep(0.5)  # Be polite to the server
        
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the course block - it's an article with class 'search-courseresult'
        course_block = soup.find('article', class_='search-courseresult')
        
        if not course_block:
            print("No course block found")
            return None
        
        print("Found course block")
        
        # Get course title from span.detail-title
        title_elem = course_block.find('span', class_='detail-title')
        if title_elem:
            course_data['course_title'] = title_elem.get_text(strip=True)
            print(f"  Title: {course_data['course_title']}")
        
        # Get credit hours from span.detail-hours_html
        hours_elem = course_block.find('span', class_='detail-hours_html')
        if hours_elem:
            hours_text = hours_elem.get_text(strip=True)
            print(f"  Raw hours: {hours_text}")
            # Extract number from "(3 Credit Hours)"
            match = re.search(r'\((\d+(?:\.\d+)?)\s*Credit Hours?\)', hours_text)
            if match:
                course_data['credit_hours'] = match.group(1).strip()
                print(f"  Credits: {course_data['credit_hours']}")
        
        # Get course description from div.courseblockextra
        desc_elem = course_block.find('div', class_='courseblockextra')
        if desc_elem:
            course_data['course_description'] = desc_elem.get_text(strip=True)
            print(f"  Description: {course_data['course_description'][:100]}...")
        
        # Get prerequisites from span.detail-prereqs
        prereq_elem = course_block.find('span', class_='detail-prereqs')
        if prereq_elem:
            prereq_text = prereq_elem.get_text(strip=True)
            print(f"  Raw prereqs: {prereq_text}")
            # Remove the "Pre-requisites:" label
            prereq_text = re.sub(r'^Pre-requisites?:\s*', '', prereq_text, flags=re.IGNORECASE)
            if prereq_text:
                course_data['prerequisites'] = extract_prerequisite_courses(prereq_text)
                print(f"    Prerequisites: {course_data['prerequisites']}")
        
        # Get corequisites from span.detail-coreqs (if exists)
        coreq_elem = course_block.find('span', class_='detail-coreqs')
        if coreq_elem:
            coreq_text = coreq_elem.get_text(strip=True)
            print(f"  Raw coreqs: {coreq_text}")
            coreq_text = re.sub(r'^Co-requisites?:\s*', '', coreq_text, flags=re.IGNORECASE)
            if coreq_text:
                course_data['corequisites'] = extract_prerequisite_courses(coreq_text)
                print(f"    Corequisites: {course_data['corequisites']}")
        
        # Get course equivalencies from span.detail-equiv
        equiv_elem = course_block.find('span', class_='detail-equiv')
        if equiv_elem:
            equiv_text = equiv_elem.get_text(strip=True)
            print(f"  Raw equivalencies: {equiv_text}")
            # Remove the "Course equivalencies:" label
            equiv_text = re.sub(r'^Course equivalenc(?:ies|y):\s*', '', equiv_text, flags=re.IGNORECASE)
            if equiv_text:
                # Split by / or comma for multiple equivalencies
                equiv_courses = re.split(r'[/,]', equiv_text)
                course_data['course_equivalencies'] = [c.strip() for c in equiv_courses if c.strip()]
                print(f"    Equivalencies: {course_data['course_equivalencies']}")
        
        return course_data
        
    except requests.Timeout:
        print(f"Timeout for {course_code}")
        return None
    except requests.RequestException as e:
        print(f"Network error for {course_code}: {str(e)}")
        return None
    except Exception as e:
        print(f"Error scraping {course_code}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def extract_prerequisite_courses(prereq_text):
    """
    Extract course codes from prerequisite text
    
    Args:
        prereq_text: Text describing prerequisites
    
    Returns:
        list: List of prerequisite course codes or conditions
    """
    prerequisites = []
    
    # Find all course codes in the text
    # Match patterns like "ACCT 201", "MATH 110", etc.
    course_matches = re.findall(r'\b([A-Z]{2,5})\s+(\d{3}[A-Z]?)\b', prereq_text)
    
    if course_matches:
        # Store the full prerequisite text as well for context
        for dept, num in course_matches:
            prerequisites.append(f"{dept} {num}")
    
    # If no specific courses found but there's text, store the text
    if not prerequisites and prereq_text:
        # Store complex prerequisite descriptions
        prerequisites.append(prereq_text)
    
    return prerequisites

def main():
    # Sample courses to test - mix of different departments and complexity
    test_courses = [
        "ACCT 201",  # Basic accounting - likely has prerequisites
        "MATH 161",  # Calculus - likely has prerequisites
        "COMM 100",  # Intro course - may have no prerequisites
        "COMP 271",  # Computer science - likely complex prerequisites
        "BIOL 101",  # Biology - standard science course
        "PHYS 121",  # Physics - likely prerequisites
        "CHEM 111",  # Chemistry - likely prerequisites
        "PSYC 101",  # Psychology intro - baseline
    ]
    
    print("="*80)
    print("TESTING COURSE SCRAPER - SAMPLE OUTPUT")
    print("="*80)
    print(f"\nTesting {len(test_courses)} sample courses...")
    
    results = {}
    
    for course_code in test_courses:
        course_data = scrape_course_details(course_code)
        if course_data and course_data.get('course_title'):
            results[course_code] = course_data
    
    # Display results in a nice format
    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    
    for course_code, data in results.items():
        print(f"\n{course_code} - {data['course_title']} ({data['credit_hours']} credits)")
        if data['prerequisites']:
            print(f"  Prerequisites: {', '.join(data['prerequisites'])}")
        if data['corequisites']:
            print(f"  Corequisites: {', '.join(data['corequisites'])}")
        if data['course_equivalencies']:
            print(f"  Equivalencies: {', '.join(data['course_equivalencies'])}")
    
    # Save sample JSON output
    print("\n" + "="*80)
    print("JSON OUTPUT")
    print("="*80)
    print(json.dumps(results, indent=2))
    
    print("\n" + "="*80)
    print(f"Successfully scraped {len(results)} out of {len(test_courses)} test courses")
    print("="*80)

if __name__ == "__main__":
    main()
