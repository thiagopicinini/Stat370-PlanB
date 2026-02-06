"""
Test script to save sample course HTML pages from Loyola catalog.

This script fetches the HTML for specific course pages to help understand
the structure and develop scraping logic.
"""
import requests
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import TEST_OUTPUT_DIR


def save_course_html(course_code):
    """
    Save the HTML for a course page to inspect its structure.
    
    Args:
        course_code: Course code like "ACCT 201"
    
    Returns:
        Path: Path to the saved HTML file, or None if error
    """
    # Construct the search URL
    search_url = f"https://catalog.luc.edu/search/?P={course_code.replace(' ', '%20')}"
    
    print(f"Fetching: {course_code}")
    print(f"URL: {search_url}")
    
    try:
        response = requests.get(search_url, timeout=10)
        response.raise_for_status()
        
        # Save to file
        output_file = TEST_OUTPUT_DIR / f'sample_course_{course_code.replace(" ", "_")}.html'
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"Saved to: {output_file}")
        print(f"File size: {len(response.text)} characters")
        
        return output_file
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

if __name__ == "__main__":
    # Save HTML for ACCT 201 to inspect structure
    course_code = "COMP 330"
    save_course_html(course_code)
