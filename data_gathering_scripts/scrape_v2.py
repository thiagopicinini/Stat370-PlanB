"""
Scrape bachelor's degree program requirements from Loyola catalog into structured JSON format.

This script extracts all bachelor's degree programs from the Loyola University
catalog and formats them with proper selection rules (exactly_one, at_least_one,
at_most_one, nested_group, etc.) and dynamic course filtering.
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

from bs4 import BeautifulSoup
import requests


def extract_department(program_url):
    """Extract department name from URL"""
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


def get_university_core_requirements():
    """Get University Core requirements"""
    return {
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


def extract_credits_from_text(text):
    """
    Extract credit hours from text.
    Returns string like "3", "3-4", or None if not found.
    """
    if not text:
        return None
    
    # Look for patterns like "3 hours", "3 credit hours", or just "3"
    patterns = [
        r'(\d+(?:-\d+)?)\s*(?:credit|hours?|credits?)',
        r'^(\d+(?:-\d+)?)$',
        r'\(\s*(\d+(?:-\d+)?)\s*(?:credit|hours?|credits?)?\s*\)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return None


def parse_credits_from_cell(credits_cell):
    """
    Parse credits from a credits column cell.
    Returns credits as string (e.g., "3", "3-4") or None.
    """
    if not credits_cell:
        return None
    
    credits_text = credits_cell.get_text(strip=True)
    return extract_credits_from_text(credits_text)


def scrape_school_programs(school_url, school_name):
    """
    Scrape all bachelor's programs from a school's page
    
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
        links = soup.find_all('a', href=True)
        
        program_links = set()
        
        for link in links:
            link_text = link.get_text(strip=True)
            href = link['href']
            
            # Pattern 1: Standard format with degree type in parentheses
            match = re.search(r'^(.+?)\s*\((B[A-Z]{1,4})\)$', link_text)
            
            # Pattern 2: Education programs that might not have degree type in link text
            # Look for links to education program pages
            is_education_program = (
                school_name == "School of Education" and 
                href and 
                '/education/' in href and
                any(keyword in link_text.lower() for keyword in 
                    ['education', 'bilingual', 'early childhood', 'elementary', 
                     'secondary', 'special education'])
            )
            
            if match and href:
                major_name = match.group(1).strip()
                degree_type = match.group(2).strip()
                
                # Build absolute URL
                if href.startswith('/'):
                    program_url = f"https://catalog.luc.edu{href}"
                elif href.startswith('http'):
                    program_url = href
                else:
                    base_path = urlparse(school_url).path
                    if base_path.endswith('/'):
                        program_url = urljoin(school_url, href)
                    else:
                        program_url = urljoin(school_url + '/', href)
                
                key = f"{major_name} ({degree_type})"
                department_name = extract_department(program_url)
                
                if key not in programs:
                    programs[key] = {
                        "major_name": major_name,
                        "degree_type": degree_type,
                        "school_college": school_name,
                        "department": department_name,
                        "program_url": program_url,
                        "requirements": [],
                        "total_credits": 0
                    }
                    print(f"  Found: {key}")
            
            # Special handling for School of Education programs
            elif is_education_program and href:
                # Try to extract program name from the link text or URL
                major_name = link_text.strip()
                if not major_name or len(major_name) < 3:
                    # Extract from URL
                    url_path = href.split('/')
                    for part in url_path:
                        if 'education' in part.lower() and part.lower() != 'education':
                            major_name = part.replace('-', ' ').title()
                            break
                
                degree_type = "BSEd" if "bilingual" in major_name.lower() or "education" in major_name.lower() else "BS"
                
                if href.startswith('/'):
                    program_url = f"https://catalog.luc.edu{href}"
                else:
                    program_url = href
                
                key = f"{major_name} ({degree_type})"
                department_name = "Education"
                
                if key not in programs:
                    programs[key] = {
                        "major_name": major_name,
                        "degree_type": degree_type,
                        "school_college": school_name,
                        "department": department_name,
                        "program_url": program_url,
                        "requirements": [],
                        "total_credits": 0
                    }
                    print(f"  Found (education): {key}")
        
        print(f"  Total programs found: {len(programs)}")
        
    except Exception as e:
        print(f"  Error scraping {school_name}: {str(e)}")
    
    return programs


def parse_standard_curriculum_table(soup, curriculum_section):
    """
    Parse the standard curriculum table and return structured requirements
    
    Returns:
        list: Structured requirement groups
    """
    requirements = []
    course_table = curriculum_section.find('table', class_='sc_courselist')
    
    if not course_table:
        return requirements
    
    rows = course_table.find_all('tr')
    
    current_group = None
    current_subgroup = None
    option_courses = []
    collecting_options = False
    current_selection_rule = None
    group_total_credits = 0
    
    for row in rows:
        # Skip header rows
        if row.find('th'):
            continue
        
        # Check for section header
        if 'areaheader' in row.get('class', []):
            # Save previous group if it exists
            if current_group and (current_group.get("courses") or current_group.get("subgroups")):
                current_group["credits"] = group_total_credits if group_total_credits > 0 else None
                requirements.append(current_group)
            
            # Start new group
            header_text = row.get_text(strip=True)
            
            # Extract credits from header if present
            credits_match = re.search(r'(\d+(?:-\d+)?)\s*(?:credits?|hours?)?$', header_text)
            group_credits = credits_match.group(1) if credits_match else None
            
            current_group = {
                "id": re.sub(r'[^a-z0-9]+', '_', header_text[:50].lower()),
                "name": header_text,
                "selectionRule": "all",
                "credits": group_credits,
                "courses": [],
                "subgroups": []
            }
            group_total_credits = 0
            current_subgroup = None
            collecting_options = False
            option_courses = []
            continue
        
        # Check for selective requirement text
        cell_text = row.get_text(strip=True)
        if 'select' in cell_text.lower() or 'choose' in cell_text.lower():
            # Save any pending options
            if collecting_options and option_courses and current_group:
                if current_subgroup:
                    current_subgroup["courses"] = option_courses
                    if current_subgroup not in current_group["subgroups"]:
                        current_group["subgroups"].append(current_subgroup)
                else:
                    current_group["courses"].append({
                        "type": "selective",
                        "selectionRule": current_selection_rule or "exactly_one",
                        "options": option_courses
                    })
                option_courses = []
            
            # Parse selection rule
            if 'at least one' in cell_text.lower() or 'choose at least one' in cell_text.lower():
                current_selection_rule = "at_least_one"
            elif 'no more than one' in cell_text.lower() or 'at most one' in cell_text.lower():
                current_selection_rule = "at_most_one"
            elif 'choose two' in cell_text.lower():
                current_selection_rule = "choose_two"
            else:
                current_selection_rule = "exactly_one"
            
            # Check if this starts a subgroup
            if 'of the following' in cell_text.lower():
                current_subgroup = {
                    "name": cell_text,
                    "selectionRule": current_selection_rule,
                    "courses": []
                }
                collecting_options = True
            continue
        
        # Look for course codes
        codecol = row.find('td', class_='codecol')
        if codecol and current_group:
            # Check for OR relationships
            if 'orclass' in row.get('class', []):
                continue
            
            # Find credits column
            credits_cell = row.find('td', class_='hourscol')
            credits = parse_credits_from_cell(credits_cell)
            
            # Get course code
            course_link = codecol.find('a', class_='bubblelink')
            if not course_link:
                continue
            
            course_code = course_link.get_text(strip=True)
            
            # Skip university core courses
            if course_code in {'UNIV 101', 'UCWR 110'}:
                continue
            
            # Check if indented (part of a selection group)
            if codecol.find('div', class_='blockindent') or codecol.find('p', class_='indent'):
                if collecting_options:
                    option_courses.append({"code": course_code, "credits": credits or "3"})
                continue
            
            # If we were collecting options, save them
            if collecting_options and option_courses:
                if current_subgroup:
                    current_subgroup["courses"] = option_courses
                    if current_subgroup not in current_group["subgroups"]:
                        current_group["subgroups"].append(current_subgroup)
                else:
                    current_group["courses"].append({
                        "type": "selective",
                        "selectionRule": current_selection_rule or "exactly_one",
                        "options": option_courses
                    })
                option_courses = []
                collecting_options = False
                current_subgroup = None
            
            # Regular required course
            current_group["courses"].append({
                "code": course_code,
                "credits": credits or "3"
            })
            
            # Add to total credits if numeric
            if credits and '-' not in credits:
                try:
                    group_total_credits += int(credits)
                except ValueError:
                    pass
    
    # Save the last group
    if current_group and (current_group.get("courses") or current_group.get("subgroups")):
        current_group["credits"] = group_total_credits if group_total_credits > 0 else None
        requirements.append(current_group)
    
    return requirements


def parse_education_curriculum(soup, curriculum_section):
    """
    Special handling for School of Education curriculum which has a different structure.
    Handles multiple tables, section headers, and module-based sequences.
    """
    requirements = []
    
    # Find all course listing tables
    tables = curriculum_section.find_all('table', class_='sc_courselist')
    
    # Also look for sections with TLSC modules that might be in divs
    phase_sections = curriculum_section.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Phase|Sequence|Concentration|Specialization', re.IGNORECASE))
    
    if phase_sections:
        # Handle phase-based structure (like TLSC modules)
        for phase in phase_sections:
            phase_name = phase.get_text(strip=True)
            phase_group = {
                "id": re.sub(r'[^a-z0-9]+', '_', phase_name[:50].lower()),
                "name": phase_name,
                "selectionRule": "all",
                "credits": None,
                "courses": [],
                "subgroups": []
            }
            
            # Find tables after this header until the next header
            phase_total = 0
            next_elem = phase.find_next_sibling()
            
            while next_elem and next_elem.name not in ['h2', 'h3', 'h4']:
                if next_elem.name == 'table' and 'sc_courselist' in next_elem.get('class', []):
                    rows = next_elem.find_all('tr')
                    for row in rows:
                        codecol = row.find('td', class_='codecol')
                        if codecol:
                            course_link = codecol.find('a', class_='bubblelink')
                            if course_link:
                                course_code = course_link.get_text(strip=True)
                                if course_code in {'UNIV 101', 'UCWR 110'}:
                                    continue
                                
                                credits_cell = row.find('td', class_='hourscol')
                                credits = parse_credits_from_cell(credits_cell)
                                
                                phase_group["courses"].append({
                                    "code": course_code,
                                    "credits": credits or "3"
                                })
                                
                                if credits and '-' not in credits:
                                    try:
                                        phase_total += int(credits)
                                    except ValueError:
                                        pass
                next_elem = next_elem.find_next_sibling()
            
            if phase_group["courses"]:
                phase_group["credits"] = phase_total if phase_total > 0 else None
                requirements.append(phase_group)
    
    # Also handle standard course tables
    for table in tables:
        # Look for section headers before the table
        prev_sibling = table.find_previous_sibling()
        section_name = "Education Courses"
        
        # Check for heading tags
        if prev_sibling and prev_sibling.name in ['h2', 'h3', 'h4']:
            section_name = prev_sibling.get_text(strip=True)
        # Check for bold text or strong tags
        elif prev_sibling and prev_sibling.name == 'p':
            strong = prev_sibling.find('strong')
            if strong:
                section_name = strong.get_text(strip=True)
        
        current_group = {
            "id": re.sub(r'[^a-z0-9]+', '_', section_name[:50].lower()),
            "name": section_name,
            "selectionRule": "all",
            "credits": None,
            "courses": [],
            "subgroups": []
        }
        
        rows = table.find_all('tr')
        group_total = 0
        
        for row in rows:
            if row.find('th'):
                continue
            
            codecol = row.find('td', class_='codecol')
            if codecol:
                course_link = codecol.find('a', class_='bubblelink')
                if course_link:
                    course_code = course_link.get_text(strip=True)
                    
                    # Skip if already in core
                    if course_code in {'UNIV 101', 'UCWR 110'}:
                        continue
                    
                    # Get credits
                    credits_cell = row.find('td', class_='hourscol')
                    credits = parse_credits_from_cell(credits_cell)
                    
                    current_group["courses"].append({
                        "code": course_code,
                        "credits": credits or "3"
                    })
                    
                    if credits and '-' not in credits:
                        try:
                            group_total += int(credits)
                        except ValueError:
                            pass
        
        if current_group["courses"]:
            current_group["credits"] = group_total if group_total > 0 else None
            # Avoid duplicate groups
            if not any(req.get("name") == section_name for req in requirements):
                requirements.append(current_group)
    
    return requirements


def extract_courses_from_curriculum(curriculum_url):
    """
    Extract structured requirements from a program's curriculum page
    
    Returns:
        list: Structured requirements with selection rules
    """
    try:
        time.sleep(0.5)
        
        response = requests.get(curriculum_url, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the curriculum section
        curriculum_section = soup.find('div', id='curriculumtextcontainer')
        if not curriculum_section:
            curriculum_section = soup.find('div', class_='page_content tab_content')
        
        if not curriculum_section:
            return []
        
        # Special handling for Education programs
        if 'education' in curriculum_url.lower():
            return parse_education_curriculum(soup, curriculum_section)
        
        return parse_standard_curriculum_table(soup, curriculum_section)
        
    except requests.Timeout:
        print(f"    Timeout - skipping this program")
    except requests.RequestException as e:
        print(f"    Network error: {str(e)[:50]}")
    except Exception as e:
        print(f"    Error extracting courses: {str(e)[:50]}")
    
    return []


def scrape_all_schools():
    """Scrape programs from all schools/colleges"""
    all_programs = {}
    
    schools = [
        {"name": "College of Arts and Sciences", "url": "https://catalog.luc.edu/undergraduate/arts-sciences/#academicstext"},
        {"name": "Quinlan School of Business", "url": "https://catalog.luc.edu/undergraduate/business/#academicstext"},
        {"name": "School of Communication", "url": "https://catalog.luc.edu/undergraduate/communication/#academicstext"},
        {"name": "School of Education", "url": "https://catalog.luc.edu/undergraduate/education/#academicstext"},
        {"name": "School of Environmental Sustainability", "url": "https://catalog.luc.edu/undergraduate/environmental-sustainability/#academicstext"},
        {"name": "Parkinson School of Health Sciences and Public Health", "url": "https://catalog.luc.edu/undergraduate/health-sciences-public-health/#academicstext"},
        {"name": "Marcella Niehoff School of Nursing", "url": "https://catalog.luc.edu/undergraduate/nursing/#academicstext"},
        {"name": "School of Social Work", "url": "https://catalog.luc.edu/undergraduate/social-work/#academicstext"},
        {"name": "School of Continuing and Professional Studies", "url": "https://catalog.luc.edu/undergraduate/continuing-professional-studies/#academicstext"}
    ]
    
    for school in schools:
        school_programs = scrape_school_programs(school['url'], school['name'])
        all_programs.update(school_programs)
        time.sleep(1)
    
    return all_programs


def populate_requirements(programs):
    """Populate structured requirements for each program"""
    total = len(programs)
    
    print(f"\nPopulating requirements for {total} programs...")
    
    for idx, (key, program) in enumerate(programs.items(), 1):
        print(f"\n[{idx}/{total}] Processing: {key}")
        
        program_url = program.get('program_url', '')
        
        if program_url:
            curriculum_url = f"{program_url}#curriculumtext"
            print(f"  Fetching from: {curriculum_url}")
            
            requirements = extract_courses_from_curriculum(curriculum_url)
            
            program['requirements'] = requirements
            
            # Calculate total credits from all requirement groups
            total_credits = 0
            for req in requirements:
                credits = req.get('credits')
                if credits:
                    try:
                        # Handle ranges like "3-4" by taking the max
                        if '-' in str(credits):
                            total_credits += int(str(credits).split('-')[1])
                        else:
                            total_credits += int(credits)
                    except (ValueError, TypeError):
                        pass
            
            program['total_credits'] = total_credits if total_credits > 0 else None
            
            if requirements:
                print(f"  Found {len(requirements)} requirement groups, total credits: {total_credits}")
            else:
                print(f"  - No requirements found")
        else:
            print(f"  - No program URL available")
    
    return programs


def main():
    """Main function to scrape all programs and save to JSON"""
    output_file = "filtered_data/majors_structured.json"
    
    print("=" * 80)
    print("SCRAPING BACHELOR'S DEGREE PROGRAMS FROM LOYOLA CATALOG")
    print("(Structured format with selection rules)")
    print("=" * 80)
    
    print("\nStep 1: Scraping all schools for bachelor's programs...")
    all_programs = scrape_all_schools()
    
    print(f"\n{'=' * 80}")
    print(f"Total programs found: {len(all_programs)}")
    print(f"{'=' * 80}")
    
    print("\nStep 2: Extracting structured requirements for each program...")
    all_programs = populate_requirements(all_programs)
    
    print(f"\n{'=' * 80}")
    print("Step 3: Saving results to JSON...")
    
    # Sort programs alphabetically
    sorted_programs = dict(sorted(all_programs.items()))
    
    # Create final output with university core
    output_data = {
        "university_core": get_university_core_requirements(),
        "programs": sorted_programs
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"  Saved to: {output_file}")
    
    # Summary statistics
    programs_with_reqs = sum(1 for p in sorted_programs.values() if p['requirements'])
    programs_with_credits = sum(1 for p in sorted_programs.values() if p.get('total_credits'))
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total programs: {len(sorted_programs)}")
    print(f"Programs with requirements: {programs_with_reqs}")
    print(f"Programs with credit totals: {programs_with_credits}")
    print(f"Programs without requirements: {len(sorted_programs) - programs_with_reqs}")
    
    # Summary by school
    school_counts = {}
    for program in sorted_programs.values():
        school = program.get('school_college', 'Unknown')
        school_counts[school] = school_counts.get(school, 0) + 1
    
    print(f"\nPrograms by school:")
    for school in sorted(school_counts.keys()):
        print(f"  {school}: {school_counts[school]} programs")
    
    # Sample output for verification
    if sorted_programs:
        sample_key = list(sorted_programs.keys())[0]
        print(f"\nSample program: {sample_key}")
        print(f"  Total credits: {sorted_programs[sample_key].get('total_credits')}")
        print(f"  Requirement groups: {len(sorted_programs[sample_key].get('requirements', []))}")
    
    print(f"\n{'=' * 80}")
    print("COMPLETE!")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()