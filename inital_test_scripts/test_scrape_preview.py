"""
Test script to preview program scraping across all schools.

This script previews bachelor's programs from all Loyola schools
and tests curriculum extraction to validate scraping logic before
running the full data gathering process.
"""
import re
import random
from bs4 import BeautifulSoup
import requests
import time


def extract_sample_curriculum(program_url):
    """
    Extract curriculum from a single program page
    Handles OR conditions, electives, and selective requirements
    
    Args:
        program_url: URL to the program page
    
    Returns:
        list: List of course codes and elective descriptions
    """
    required_courses = []
    
    try:
        time.sleep(1)  # Be polite to the server
        
        curriculum_url = f"{program_url}#curriculumtext"
        response = requests.get(curriculum_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the curriculum section
        curriculum_section = soup.find('div', id='curriculumtextcontainer')
        
        if not curriculum_section:
            curriculum_section = soup.find('div', class_='page_content tab_content')
        
        if curriculum_section:
            # Find the main course table
            course_table = curriculum_section.find('table', class_='sc_courselist')
            
            if course_table:
                rows = course_table.find_all('tr')
                i = 0
                while i < len(rows):
                    row = rows[i]
                    
                    # Skip header rows
                    if row.find('th'):
                        i += 1
                        continue
                    
                    # Check if this is a section header
                    if 'areaheader' in row.get('class', []):
                        section_name = row.get_text(strip=True)
                        # Skip elective sections
                        if 'elective' in section_name.lower():
                            while i < len(rows) and 'areaheader' not in rows[i].get('class', []):
                                i += 1
                            continue
                        i += 1
                        continue
                    
                    # Check for selective requirements
                    cell_text = row.get_text(strip=True)
                    if 'select' in cell_text.lower() or 'choose' in cell_text.lower():
                        if 'one of the following' in cell_text.lower():
                            required_courses.append(f"[Elective: {cell_text}]")
                        i += 1
                        continue
                    
                    # Look for course codes
                    codecol = row.find('td', class_='codecol')
                    if codecol:
                        # Check for "or" relationship
                        if 'orclass' in row.get('class', []):
                            course_link = codecol.find('a', class_='bubblelink')
                            if course_link and required_courses:
                                course_code = course_link.get_text(strip=True)
                                if not required_courses[-1].startswith('[Elective:'):
                                    required_courses[-1] = f"{required_courses[-1]} or {course_code}"
                            i += 1
                            continue
                        
                        # Regular course
                        course_link = codecol.find('a', class_='bubblelink')
                        if course_link:
                            course_code = course_link.get_text(strip=True)
                            # Skip indented blocks (choice options)
                            if codecol.find('div', class_='blockindent'):
                                i += 1
                                continue
                            
                            required_courses.append(course_code)
                    
                    i += 1
        
    except Exception as e:
        return []
    
    return required_courses

def preview_school_programs(school_url, school_name):
    """
    Preview bachelor's programs from a school's page
    
    Args:
        school_url: URL of the school's academics page
        school_name: Name of the school/college
    """
    print(f"\n{'='*80}")
    print(f"{school_name}")
    print(f"{'='*80}")
    print(f"URL: {school_url}\n")
    
    try:
        response = requests.get(school_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links that might be program pages
        links = soup.find_all('a', href=True)
        
        programs_found = []
        
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
                
                programs_found.append({
                    'name': major_name,
                    'degree': degree_type,
                    'url': program_url
                })
        
        if programs_found:
            print(f"Found {len(programs_found)} bachelor's programs:\n")
            for i, prog in enumerate(programs_found, 1):
                print(f"{i:2d}. {prog['name']} ({prog['degree']})")
                print(f"    URL: {prog['url']}")
                print(f"    Curriculum: {prog['url']}#curriculumtext")
                print()
            
            # Test curriculum extraction on one random program
            if programs_found:
                sample_prog = random.choice(programs_found)
                print(f"\n{'-'*80}")
                print(f"SAMPLE CURRICULUM TEST: {sample_prog['name']} ({sample_prog['degree']})")
                print(f"{'-'*80}")
                print(f"Fetching curriculum from: {sample_prog['url']}#curriculumtext")
                
                courses = extract_sample_curriculum(sample_prog['url'])
                
                if courses:
                    print(f"\nFound {len(courses)} required courses:")
                    # Display first 20 courses
                    for i, course in enumerate(courses[:20], 1):
                        print(f"  {i:2d}. {course}")
                    if len(courses) > 20:
                        print(f"  ... and {len(courses) - 20} more courses")
                else:
                    print("\n✗ No courses found in curriculum section")
                
                print()
        else:
            print("No bachelor's programs found.\n")
    
    except Exception as e:
        print(f"ERROR: {str(e)}\n")

def main():
    print("="*80)
    print("PREVIEW: SCRAPING BACHELOR'S DEGREE PROGRAMS")
    print("="*80)
    
    # Define schools and their URLs
    schools = [
        {
            "name": "College of Arts and Sciences",
            "url": "https://catalog.luc.edu/undergraduate/arts-sciences/#academicstext"
        },
        {
            "name": "Quinlan School of Business",
            "url": "https://catalog.luc.edu/undergraduate/business/#academicstext"
        },
        {
            "name": "School of Communication",
            "url": "https://catalog.luc.edu/undergraduate/communication/#academicstext"
        },
        {
            "name": "School of Education",
            "url": "https://catalog.luc.edu/undergraduate/education/#academicstext"
        },
        {
            "name": "School of Environmental Sustainability",
            "url": "https://catalog.luc.edu/undergraduate/environmental-sustainability/#academicstext"
        },
        {
            "name": "Parkinson School of Health Sciences and Public Health",
            "url": "https://catalog.luc.edu/undergraduate/parkinson-school-health-sciences-public-health/#academicstext"
        },
        {
            "name": "Marcella Niehoff School of Nursing",
            "url": "https://catalog.luc.edu/undergraduate/nursing/#academicstext"
        },
        {
            "name": "School of Social Work",
            "url": "https://catalog.luc.edu/undergraduate/social-work/#academicstext"
        },
        {
            "name": "School of Continuing and Professional Studies",
            "url": "https://catalog.luc.edu/undergraduate/continuing-professional-studies/#academicstext"
        }
    ]
    
    total_programs = 0
    
    for school in schools:
        preview_school_programs(school['url'], school['name'])
    
    print("="*80)
    print("PREVIEW COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
