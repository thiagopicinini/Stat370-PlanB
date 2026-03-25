"""
Test script to save sample curriculum HTML pages from Loyola catalog.

This script fetches curriculum pages for random bachelor's programs
to help understand the structure and develop scraping logic.
"""
import re
import random
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import TEST_OUTPUT_DIR


def get_random_program():
    """
    Get a random bachelor's program from Loyola catalog
    
    Returns:
        dict: Program information with name, degree, and URL
    """
    schools = [
        "https://catalog.luc.edu/undergraduate/arts-sciences/#academicstext",
        "https://catalog.luc.edu/undergraduate/business/#academicstext",
        "https://catalog.luc.edu/undergraduate/communication/#academicstext",
        "https://catalog.luc.edu/undergraduate/education/#academicstext",
        "https://catalog.luc.edu/undergraduate/environmental-sustainability/#academicstext",
        "https://catalog.luc.edu/undergraduate/parkinson-school-health-sciences-public-health/#academicstext",
        "https://catalog.luc.edu/undergraduate/nursing/#academicstext",
        "https://catalog.luc.edu/undergraduate/social-work/#academicstext",
        "https://catalog.luc.edu/undergraduate/continuing-professional-studies/#academicstext"
    ]
    
    # Pick a random school
    school_url = random.choice(schools)
    
    print(f"Fetching programs from: {school_url}")
    
    try:
        response = requests.get(school_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        links = soup.find_all('a', href=True)
        
        programs = []
        
        for link in links:
            link_text = link.get_text(strip=True)
            href = link['href']
            
            # Check if this looks like a bachelor's degree program
            match = re.search(r'^(.+?)\s*\((B[A-Z]{1,4})\)$', link_text)
            
            if match and href:
                major_name = match.group(1).strip()
                degree_type = match.group(2).strip()
                
                # Convert relative URLs to absolute
                if href.startswith('/'):
                    program_url = f"https://catalog.luc.edu{href}"
                elif href.startswith('http'):
                    program_url = href
                else:
                    program_url = f"https://catalog.luc.edu/undergraduate/arts-sciences/{href}"
                
                programs.append({
                    'name': major_name,
                    'degree': degree_type,
                    'url': program_url
                })
        
        if programs:
            return random.choice(programs)
    
    except Exception as e:
        print(f"Error: {str(e)}")
    
    return None

def save_curriculum_html(program):
    """
    Fetch and save curriculum HTML for a program
    
    Args:
        program: Dictionary with program info
    """
    if not program:
        print("No program provided")
        return
    
    curriculum_url = f"{program['url']}#curriculumtext"
    
    print(f"\nProgram: {program['name']} ({program['degree']})")
    print(f"URL: {curriculum_url}")
    
    try:
        time.sleep(1)
        response = requests.get(curriculum_url, timeout=15)
        response.raise_for_status()
        
        # Save the raw HTML to test output directory
        TEST_OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Create a clean filename
        clean_name = re.sub(r'[^\w\s-]', '', program['name'])
        clean_name = re.sub(r'\s+', '_', clean_name)
        filename = f"sample_curriculum_{clean_name}_{program['degree']}.html"
        
        output_file = TEST_OUTPUT_DIR / filename
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        print(f"\nSaved HTML to: {output_file}")
        
        # Also extract and show some info
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for the curriculum section
        curriculum_section = soup.find('div', id='curriculumtextcontainer')
        
        if not curriculum_section:
            # Try alternative selector
            curriculum_section = soup.find('div', class_='page_content tab_content')
        
        if curriculum_section:
            # Parse courses smartly
            required_courses = []
            course_table = curriculum_section.find('table', class_='sc_courselist')
            
            if course_table:
                rows = course_table.find_all('tr')
                i = 0
                while i < len(rows):
                    row = rows[i]
                    
                    if row.find('th'):
                        i += 1
                        continue
                    
                    if 'areaheader' in row.get('class', []):
                        section_name = row.get_text(strip=True)
                        if 'elective' in section_name.lower():
                            while i < len(rows) and 'areaheader' not in rows[i].get('class', []):
                                i += 1
                            continue
                        i += 1
                        continue
                    
                    cell_text = row.get_text(strip=True)
                    if 'select' in cell_text.lower() or 'choose' in cell_text.lower():
                        if 'one of the following' in cell_text.lower():
                            required_courses.append(f"[Elective: {cell_text}]")
                        i += 1
                        continue
                    
                    codecol = row.find('td', class_='codecol')
                    if codecol:
                        if 'orclass' in row.get('class', []):
                            course_link = codecol.find('a', class_='bubblelink')
                            if course_link and required_courses:
                                course_code = course_link.get_text(strip=True)
                                if not required_courses[-1].startswith('[Elective:'):
                                    required_courses[-1] = f"{required_courses[-1]} or {course_code}"
                            i += 1
                            continue
                        
                        course_link = codecol.find('a', class_='bubblelink')
                        if course_link:
                            course_code = course_link.get_text(strip=True)
                            if codecol.find('div', class_='blockindent'):
                                i += 1
                                continue
                            required_courses.append(course_code)
                    
                    i += 1
            
            print(f"\nFound {len(required_courses)} required courses/requirements:")
            for i, course in enumerate(required_courses[:20], 1):
                print(f"  {i:2d}. {course}")
            if len(required_courses) > 20:
                print(f"  ... and {len(required_courses) - 20} more")
        else:
            print("\n- No curriculum section found with id='curriculumtextcontainer'")
        
    except Exception as e:
        print(f"\nError fetching curriculum: {str(e)}")

def main():
    print("="*80)
    print("SAVE SAMPLE CURRICULUM HTML")
    print("="*80)
    
    program = get_random_program()
    
    if program:
        save_curriculum_html(program)
    else:
        print("\nFailed to find a random program")
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)

if __name__ == "__main__":
    main()
