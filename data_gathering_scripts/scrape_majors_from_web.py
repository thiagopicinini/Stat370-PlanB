"""
Scrape bachelor's degree program requirements from Loyola catalog.

This script extracts all bachelor's degree programs from the Loyola University
catalog, including their required courses, by scraping curriculum pages from
each school/college.
"""
import json
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup
import requests
import time

from urllib.parse import urlparse

def extract_department(program_url):
    try:
        path = urlparse(program_url).path.lower()
        parts = path.split("/")

        if "undergraduate" in parts:
            idx = parts.index("undergraduate")
            if len(parts) > idx + 2:
                department_slug = parts[idx + 2]
                return department_slug.replace("-", " ").title()
    except:
        pass

    return "Unknown"

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import MAJORS_JSON


def get_university_core_requirements():
    """
    Get University Core requirements
    
    Returns:
        dict: Dictionary with core requirement categories and descriptions
    """
    core_requirements = {
        "category": "University Core",
        "description": "All undergraduate students must complete the University Core curriculum",
        "areas": [
            "Writing Responsibly (UCWR 110) - 3 credit hours",
            "First Year Seminar (UNIV 101) - 1 credit hour",
            "Philosophical Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Theological & Religious Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Artistic Knowledge and Inquiry - 3 credit hours",
            "Literary Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Historical Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Scientific Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Societal and Cultural Knowledge and Inquiry Tier 1 - 3 credit hours",
            "Quantitative Knowledge and Inquiry - 3 credit hours",
            "Ethical Knowledge and Inquiry - 3 credit hours",
            "Engaged Learning - 3 credit hours minimum"
        ],
        "total_credit_hours": "Approximately 34-37 credit hours"
    }
    
    return core_requirements

def scrape_school_programs(school_url, school_name):
    """
    Scrape all bachelor's programs from a school's page
    
    Args:
        school_url: URL of the school's academics page
        school_name: Name of the school/college
    
    Returns:
        dict: Dictionary of programs found
    """
    programs = {}
    
    try:
        print(f"\nScraping {school_name}...")
        print(f"  URL: {school_url}")
        
        response = requests.get(school_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all links that might be program pages
        # Look for links with degree types in parentheses
        links = soup.find_all('a', href=True)
        
        for link in links:
            link_text = link.get_text(strip=True)
            href = link['href']
            
            # Check if this looks like a bachelor's degree program
            # Pattern: "Program Name (BA)", "Program Name (BS)", etc.
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
                
                key = f"{major_name} ({degree_type})"
                
                department_name = extract_department(program_url)

                programs[key] = {
                  "major_name": major_name,
                  "degree_type": degree_type,
                  "school_college": school_name,
                  "department": department_name,
                  "program_url": program_url,
                  "required_courses": [],
                  "total_major_courses": 0
                }
                
                print(f"  Found: {key}")
        
        print(f"  Total programs found: {len(programs)}")
        
    except Exception as e:
        print(f"  Error scraping {school_name}: {str(e)}")
    
    return programs

def extract_courses_from_curriculum(curriculum_url):
    """
    Extract required courses from a program's curriculum page
    Handles OR conditions, electives, and selective requirements
    Returns all courses in a single list
    
    Args:
        curriculum_url: URL to the program's curriculum section
    
    Returns:
        list: List of all required courses with options preserved for electives
    """
    all_courses = []
    
    # Core courses to exclude from major requirements
    core_courses = {'UNIV 101', 'UCWR 110'}
    
    try:
        time.sleep(0.5)  # Be polite to the server
        
        response = requests.get(curriculum_url, timeout=10)
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
                in_elective_section = False
                
                collecting_options = False
                option_courses = []
                
                for row in rows:
                    # Skip header rows
                    if row.find('th'):
                        continue
                    
                    # Check if this is a section header (like "Required Courses", "Electives")
                    if 'areaheader' in row.get('class', []):
                        # Save any collected options
                        if collecting_options and option_courses:
                            all_courses.append({"options": option_courses})
                            collecting_options = False
                            option_courses = []
                        
                        # Track if we're in an elective section
                        section_name = row.get_text(strip=True)
                        in_elective_section = 'elective' in section_name.lower()
                        continue
                    
                    # Skip rows if we're in an elective section
                    if in_elective_section:
                        continue
                    
                    # Check for "Select one of the following" or similar
                    cell_text = row.get_text(strip=True)
                    if 'select' in cell_text.lower() or 'choose' in cell_text.lower():
                        # Save any previously collected options
                        if collecting_options and option_courses:
                            all_courses.append({"options": option_courses})
                            option_courses = []
                        
                        # This is a selective requirement - add as description
                        if 'of the following' in cell_text.lower():
                            all_courses.append(f"[Elective: {cell_text}]")
                            collecting_options = True
                        continue
                    
                    # Look for course codes in regular course rows
                    codecol = row.find('td', class_='codecol')
                    if codecol:
                        # Check for "or" relationship
                        if 'orclass' in row.get('class', []):
                            # This is an OR option, combine with previous
                            course_link = codecol.find('a', class_='bubblelink')
                            if course_link:
                                course_code = course_link.get_text(strip=True)
                                # If we're collecting options, add to option list
                                if collecting_options and option_courses:
                                    option_courses[-1] = f"{option_courses[-1]} or {course_code}"
                                elif all_courses and not all_courses[-1].startswith('[Elective:'):
                                    all_courses[-1] = f"{all_courses[-1]} or {course_code}"
                            continue
                        
                        # Regular course
                        course_link = codecol.find('a', class_='bubblelink')
                        if course_link:
                            course_code = course_link.get_text(strip=True)
                            
                            # Skip university core courses
                            if course_code in core_courses:
                                continue
                            
                            # Check if it's in an indented block (part of a choice)
                            if codecol.find('div', class_='blockindent'):
                                # These are options within a "select one" - add to options
                                if collecting_options:
                                    option_courses.append(course_code)
                                continue
                            
                            # Regular required course
                            all_courses.append(course_code)
                
                # Save any remaining collected options
                if collecting_options and option_courses:
                    all_courses.append({"options": option_courses})
        
    except requests.Timeout:
        print(f"    Timeout - skipping this program")
    except requests.RequestException as e:
        print(f"    Network error: {str(e)[:50]}")
    except Exception as e:
        print(f"    Error extracting courses: {str(e)[:50]}")
    
    return all_courses

def scrape_all_schools():
    """
    Scrape programs from all schools/colleges
    
    Returns:
        dict: All bachelor's programs from all schools
    """
    all_programs = {}
    
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
            "url": "https://catalog.luc.edu/undergraduate/health-sciences-public-health/#academicstext"
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
    
    for school in schools:
        school_programs = scrape_school_programs(school['url'], school['name'])
        all_programs.update(school_programs)
        time.sleep(1)  # Be polite between school pages
    
    return all_programs

def populate_required_courses(programs):
    """
    Populate required courses for each program by scraping curriculum pages
    
    Args:
        programs: Dictionary of programs
    
    Returns:
        Updated programs dictionary
    """
    total = len(programs)
    
    print(f"\nPopulating required courses for {total} programs...")
    
    for idx, (key, program) in enumerate(programs.items(), 1):
        print(f"\n[{idx}/{total}] Processing: {key}")
        
        program_url = program.get('program_url', '')
        
        if program_url:
            # Add #curriculumtext to the URL
            curriculum_url = f"{program_url}#curriculumtext"
            
            print(f"  Fetching curriculum from: {curriculum_url}")
            
            required_courses = extract_courses_from_curriculum(curriculum_url)
            
            program['required_courses'] = required_courses
            program['total_major_courses'] = len(required_courses)
            
            if required_courses:
                print(f"  Found {len(required_courses)} total items")
            else:
                print(f"  - No courses found")
        else:
            print(f"  - No program URL available")
    
    return programs

def main():
    """
    Main function to scrape all programs and save to JSON.
    """
    output_file = MAJORS_JSON
    
    print("="*80)
    print("SCRAPING BACHELOR'S DEGREE PROGRAMS FROM LOYOLA CATALOG")
    print("="*80)
    
    print("\nStep 1: Scraping all schools for bachelor's programs...")
    all_programs = scrape_all_schools()
    
    print(f"\n{'='*80}")
    print(f"Total programs found: {len(all_programs)}")
    print(f"{'='*80}")
    
    print("\nStep 2: Extracting required courses for each program...")
    all_programs = populate_required_courses(all_programs)
    
    print(f"\n{'='*80}")
    print("Step 3: Saving results to JSON...")
    
    # Sort programs alphabetically
    sorted_programs = dict(sorted(all_programs.items()))
    
    # Create final output with university core as separate entry
    output_data = {
        "university_core": get_university_core_requirements(),
        "programs": sorted_programs
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved to: {output_file}")
    
    # Summary statistics
    programs_with_courses = sum(1 for p in sorted_programs.values() if p['total_major_courses'] > 0)
    avg_courses = sum(p['total_major_courses'] for p in sorted_programs.values()) / len(sorted_programs) if sorted_programs else 0
    
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total programs: {len(sorted_programs)}")
    print(f"Programs with required courses: {programs_with_courses}")
    print(f"Programs without courses: {len(sorted_programs) - programs_with_courses}")
    print(f"Average courses per major: {avg_courses:.1f}")
    
    # Summary by school
    school_counts = {}
    for program in sorted_programs.values():
        school = program.get('school_college', 'Unknown')
        school_counts[school] = school_counts.get(school, 0) + 1
    
    print(f"\nPrograms by school:")
    for school in sorted(school_counts.keys()):
        print(f"  {school}: {school_counts[school]} programs")
    
    # Summary by degree type
    degree_counts = {}
    for program in sorted_programs.values():
        degree_type = program.get('degree_type', 'Unknown')
        degree_counts[degree_type] = degree_counts.get(degree_type, 0) + 1
    
    print(f"\nPrograms by degree type:")
    for degree_type in sorted(degree_counts.keys()):
        print(f"  {degree_type}: {degree_counts[degree_type]} programs")
    
    print(f"\n{'='*80}")
    print("COMPLETE!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
