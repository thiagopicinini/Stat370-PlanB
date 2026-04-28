"""
Edited scraper for Loyola University Chicago undergraduate catalog, requires manual fixes to handle some edge cases in the curriculum tables.
Current information is not from the scraper but from a manually fixed version of the output JSON. This script is kept for reference and potential future use if the catalog structure changes again.
"""

import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, NavigableString, Tag


# ── helpers ────────────────────────────────────────────────────────────────────

def get_row_description_text(row):
    """
    Return the text of a description/header row WITHOUT leaking the hourscol value.
    Original bug: row.get_text() included the credit number cell.
    """
    parts = []
    for td in row.find_all('td'):
        if 'hourscol' in (td.get('class') or []):
            continue
        t = td.get_text(strip=True)
        if t:
            parts.append(t)
    return ' '.join(parts).strip()


def parse_credits_from_cell(credits_cell):
    if not credits_cell:
        return None
    text = credits_cell.get_text(strip=True)
    m = re.search(r'(\d+(?:-\d+)?)', text)
    return m.group(1) if m else None


def extract_required_credits_from_selection(text):
    """Pull credit value from a selection header, e.g. 'Select two (6 credits)'."""
    m = re.search(r'\((\d+(?:-\d+)?)\s*(?:credits?|hours?)?\)', text, re.I)
    return m.group(1) if m else None


def is_selection_description(text):
    if not text:
        return False
    tl = text.lower()
    return any(p in tl for p in [
        'select', 'choose', 'of the following', 'complete', 'take', 'from the following'
    ])


def parse_selection_rule(text):
    """Return (rule_string, n_choices) from a description line."""
    if not text:
        return 'exactly_one', 1
    tl = text.lower()
    if 'at least one' in tl:
        return 'at_least_one', 1
    if 'at most one' in tl or 'no more than one' in tl:
        return 'at_most_one', 1
    m = re.search(r'(?:choose|select|take)\s+(\w+)\s+(?:courses?|of the following)', tl)
    if m:
        num_word = m.group(1)
        w2n = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
               'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10}
        if num_word in w2n:
            n = w2n[num_word]
            return f'choose_{num_word}', n
    digit_m = re.search(r'(?:choose|select|take)\s+(\d+)', tl)
    if digit_m:
        n = int(digit_m.group(1))
        words = ['zero','one','two','three','four','five','six','seven','eight','nine','ten']
        label = words[n] if n < len(words) else str(n)
        return f'choose_{label}', n
    if 'one of the following' in tl:
        return 'exactly_one', 1
    if 'two of the following' in tl:
        return 'choose_two', 2
    if 'three of the following' in tl:
        return 'choose_three', 3
    if 'four of the following' in tl:
        return 'choose_four', 4
    return 'exactly_one', 1


def compute_group_credits(group):
    total = 0
    for course in group.get('courses', []):
        cred = course.get('credits', '3')
        try:
            total += int(str(cred).split('-')[0])
        except (ValueError, TypeError):
            pass
    for sub in group.get('subgroups', []):
        rc = sub.get('required_credits')
        if rc:
            try:
                total += int(str(rc).split('-')[0])
                continue
            except (ValueError, TypeError):
                pass
        rule = sub.get('selectionRule', 'exactly_one')
        courses = sub.get('courses', [])
        # recurse into sub-subgroups
        if not courses and sub.get('subgroups'):
            total += compute_group_credits(sub)
            continue
        if not courses:
            continue
        sample = courses[0].get('credits', '3')
        try:
            unit = int(str(sample).split('-')[0])
        except (ValueError, TypeError):
            unit = 3
        multiplier = {
            'exactly_one': 1, 'at_least_one': 1, 'at_most_one': 1,
            'choose_two': 2, 'choose_three': 3, 'choose_four': 4,
            'choose_five': 5, 'choose_six': 6, 'choose_seven': 7,
            'choose_eight': 8, 'choose_nine': 9, 'choose_ten': 10,
        }.get(rule, 1)
        total += multiplier * unit
    return total


def get_university_core_requirements():
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
            "Engaged Learning - 3 credit hours minimum",
        ],
        "total_credit_hours": "Approximately 34-37 credit hours",
    }


# ── main curriculum table parser ───────────────────────────────────────────────

def parse_curriculum_tables(container):
    """
    Parse all sc_courselist tables inside container.
    Returns a list of requirement group dicts.
    """
    groups = []
    tables = container.find_all('table', class_='sc_courselist')
    if not tables:
        return groups

    for table in tables:
        # --- Derive table name from immediately-preceding heading/paragraph ---
        prev = table.find_previous_sibling(['h2', 'h3', 'h4', 'p', 'strong'])
        if prev is None:
            prev = table.find_previous(['h2', 'h3', 'h4'])
        table_name = prev.get_text(strip=True) if prev else 'Requirements'

        current_group = None

        # Selection state (simple: one list of options)
        in_selection = False
        selection_text = None
        selection_rule = 'exactly_one'
        selection_req_credits = None
        selection_courses = []

        # Multi-part selection state (one-from-each-area style)
        parent_selection = None
        current_sub_name = None
        current_sub_courses = []

        # Track last required course so orclass rows can merge with it (BUG 1 FIX)
        last_required_course = None  # dict {"code": ..., "credits": ...}

        def flush_selection():
            """Commit the in-progress simple selection as a subgroup."""
            nonlocal in_selection, selection_text, selection_rule
            nonlocal selection_req_credits, selection_courses
            if in_selection and selection_courses:
                sub = {
                    'name': selection_text or 'Select from the following',
                    'selectionRule': selection_rule,
                    'courses': selection_courses[:],
                }
                if selection_req_credits:
                    sub['required_credits'] = selection_req_credits
                current_group.setdefault('subgroups', []).append(sub)
            in_selection = False
            selection_text = None
            selection_rule = 'exactly_one'
            selection_req_credits = None
            selection_courses = []

        def flush_sub():
            """Commit current subsection of a parent multi-part selection."""
            nonlocal current_sub_name, current_sub_courses
            if current_sub_name and current_sub_courses:
                parent_selection['subgroups'].append({
                    'name': current_sub_name,
                    'selectionRule': 'exactly_one',
                    'courses': current_sub_courses[:],
                })
            current_sub_name = None
            current_sub_courses = []

        for row in table.find_all('tr'):
            row_classes = row.get('class', [])

            # ── Area header: start a new requirement group ──────────────────
            if 'areaheader' in row_classes:
                flush_selection()
                if parent_selection:
                    flush_sub()
                    parent_selection = None

                if current_group and (current_group.get('courses') or current_group.get('subgroups')):
                    if current_group.get('credits') is None:
                        current_group['credits'] = compute_group_credits(current_group) or None
                    groups.append(current_group)

                header_text = row.get_text(strip=True)
                credit_m = re.search(r'\((\d+(?:-\d+)?)\s*(?:credits?|hours?)?\)', header_text)
                header_credits = credit_m.group(1) if credit_m else None

                current_group = {
                    'id': re.sub(r'[^a-z0-9]+', '_', header_text[:50].lower()).strip('_'),
                    'name': header_text,
                    'selectionRule': 'all',
                    'credits': header_credits,
                    'courses': [],
                    'subgroups': [],
                }
                last_required_course = None
                continue

            # Ensure we always have a current group
            if current_group is None:
                current_group = {
                    'id': re.sub(r'[^a-z0-9]+', '_', table_name[:50].lower()).strip('_'),
                    'name': table_name,
                    'selectionRule': 'all',
                    'credits': None,
                    'courses': [],
                    'subgroups': [],
                }

            # Skip header rows (th)
            if row.find('th'):
                continue

            # ── OR / orclass row (BUG 1 FIX) ──────────────────────────────
            if 'orclass' in row_classes:
                codecol = row.find('td', class_='codecol')
                if not codecol:
                    continue
                links = codecol.find_all('a', class_='bubblelink')
                if not links:
                    continue
                or_course_code = links[0].get_text(strip=True)
                hours_cell = row.find('td', class_='hourscol')
                or_credits = parse_credits_from_cell(hours_cell) or '3'
                or_course = {'code': or_course_code, 'credits': or_credits}

                # Merge with previous course into a proper OR subgroup
                if last_required_course:
                    # Remove the last required course from its list
                    if in_selection and selection_courses and selection_courses[-1] == last_required_course:
                        selection_courses.pop()
                    elif current_group['courses'] and current_group['courses'][-1] == last_required_course:
                        current_group['courses'].pop()
                    elif parent_selection and current_sub_courses and current_sub_courses[-1] == last_required_course:
                        current_sub_courses.pop()
                    else:
                        last_required_course = None  # can't find it, just append normally

                if last_required_course:
                    or_subgroup = {
                        'name': 'Select one of the following:',
                        'selectionRule': 'exactly_one',
                        'courses': [last_required_course, or_course],
                    }
                    # Put it in the right place
                    if in_selection:
                        selection_courses.append(or_subgroup)  # nested — rare
                    elif parent_selection and current_sub_name:
                        current_sub_courses.append(or_subgroup)
                    else:
                        current_group.setdefault('subgroups', []).append(or_subgroup)
                    last_required_course = None
                else:
                    # Fallback: just add as a regular course
                    _add_course(or_course, current_group, in_selection, selection_courses,
                                parent_selection, current_sub_courses)
                    last_required_course = or_course
                continue

            # ── Selection description row (no codecol) ─────────────────────
            codecol_check = row.find('td', class_='codecol')
            row_desc_text = get_row_description_text(row)   # BUG 2 FIX: no hourscol leak

            if not codecol_check and is_selection_description(row_desc_text):
                # Multi-part: one from each area
                if re.search(r'one from each|each of the following|from each', row_desc_text, re.I):
                    flush_selection()
                    if parent_selection:
                        flush_sub()
                    rule, _ = parse_selection_rule(row_desc_text)
                    rc = extract_required_credits_from_selection(row_desc_text)
                    parent_selection = {
                        'name': row_desc_text,
                        'selectionRule': rule,
                        'courses': [],
                        'subgroups': [],
                    }
                    if rc:
                        parent_selection['required_credits'] = rc
                    current_group.setdefault('subgroups', []).append(parent_selection)
                    current_sub_name = None
                    current_sub_courses = []
                else:
                    # Standard selection list
                    flush_selection()
                    selection_text = row_desc_text
                    selection_rule, _ = parse_selection_rule(row_desc_text)
                    selection_req_credits = extract_required_credits_from_selection(row_desc_text)
                    in_selection = True
                continue

            # ── Subsection bold header within a parent selection ───────────
            if parent_selection is not None and not codecol_check:
                bold = row.find(['strong', 'b'])
                if bold:
                    flush_sub()
                    current_sub_name = bold.get_text(strip=True)
                    continue

            # ── Course row ─────────────────────────────────────────────────
            codecol = row.find('td', class_='codecol')
            if not codecol:
                continue
            link = codecol.find('a', class_='bubblelink')
            if not link:
                continue
            code = link.get_text(strip=True)
            if code in {'UNIV 101', 'UCWR 110'}:
                continue
            hours_cell = row.find('td', class_='hourscol')
            credits = parse_credits_from_cell(hours_cell) or '3'

            course_obj = {'code': code, 'credits': credits}

            if parent_selection is not None:
                if current_sub_name:
                    current_sub_courses.append(course_obj)
                else:
                    parent_selection.setdefault('courses', []).append(course_obj)
                last_required_course = course_obj
            elif in_selection:
                selection_courses.append(course_obj)
                last_required_course = course_obj
            else:
                current_group.setdefault('courses', []).append(course_obj)
                last_required_course = course_obj

        # ── End of table: flush open structures ────────────────────────────
        if parent_selection:
            flush_sub()
            parent_selection = None
        flush_selection()

        if current_group and (current_group.get('courses') or current_group.get('subgroups')):
            if current_group.get('credits') is None:
                current_group['credits'] = compute_group_credits(current_group) or None
            groups.append(current_group)

    return groups


def _add_course(course_obj, current_group, in_selection, selection_courses,
                parent_selection, current_sub_courses):
    """Helper to add a course to the right bucket."""
    if parent_selection is not None and current_sub_courses is not None:
        current_sub_courses.append(course_obj)
    elif in_selection:
        selection_courses.append(course_obj)
    else:
        current_group.setdefault('courses', []).append(course_obj)


def extract_total_credits_from_page(soup):
    patterns = [
        r'Total\s*(?:Credit\s*Hours?|Credits?)?\s*[:]\s*(\d+(?:-\d+)?)',
        r'(\d+(?:-\d+)?)\s*credit hours?\s*(?:are required for the major|total)',
        r'a total of\s+.*?\(?(\d+(?:-\d+)?)\s*(?:credit|hour)',
        r'requires\s+(\d+(?:-\d+)?)\s*(?:credit|hour)',
    ]
    for cont in soup.find_all(['div', 'p', 'span', 'strong']):
        txt = cont.get_text(strip=True)
        if not re.search(r'Total|credit', txt, re.I):
            continue
        for pat in patterns:
            m = re.search(pat, txt, re.I)
            if m:
                return m.group(1)
    return None


# ── page fetcher / parser ──────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/124.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

STOP_HEADINGS = re.compile(
    r'suggested|sequence|transfer|study abroad|graduation|additional|important|details',
    re.IGNORECASE,
)


def parse_curriculum_page(url):
    try:
        time.sleep(0.5)
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        container = soup.find('div', id='curriculumtextcontainer')
        if not container:
            container = soup.find('div', class_='page_content tab_content')
        if not container:
            return {'requirements': [], 'total_credits': None}

        # Clip container at non-curriculum headings
        curriculum_start = None
        for elem in container.children:
            if isinstance(elem, Tag) and elem.name in ('h2', 'h3', 'h4'):
                text = elem.get_text(strip=True).lower()
                if any(kw in text for kw in [
                    'curriculum', 'major requirements', 'program requirements', 'requirements'
                ]):
                    curriculum_start = elem
                    break
        if curriculum_start is None:
            curriculum_start = next(
                (c for c in container.children if isinstance(c, Tag)), None
            )

        relevant = []
        elem = curriculum_start
        while elem:
            if isinstance(elem, Tag) and elem.name in ('h2', 'h3', 'h4'):
                if STOP_HEADINGS.search(elem.get_text(strip=True)):
                    break
            relevant.append(elem)
            elem = elem.next_sibling

        temp = BeautifulSoup('', 'html.parser').new_tag('div')
        for e in relevant:
            temp.append(e)

        declared_total = (
            extract_total_credits_from_page(container)
            or extract_total_credits_from_page(soup)
        )

        groups = parse_curriculum_tables(temp)

        computed_total = None
        if not declared_total:
            t = sum(compute_group_credits(g) for g in groups)
            if t > 0:
                computed_total = str(t)

        final_total = declared_total or computed_total

        for g in groups:
            if g.get('credits') is None:
                g['credits'] = compute_group_credits(g) or None

        return {'requirements': groups, 'total_credits': final_total}

    except Exception as e:
        print(f'    Error parsing {url}: {str(e)[:100]}')
        return {'requirements': [], 'total_credits': None}


# ── school / program discovery ─────────────────────────────────────────────────

def scrape_school_programs(school_url, school_name):
    programs = {}
    try:
        print(f'\nScraping {school_name}...')
        resp = SESSION.get(school_url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, 'html.parser')

        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            href = link['href']

            m = re.search(r'^(.+?)\s*\((B[A-Z]{1,4})\)$', link_text)
            if m and href:
                major_name = m.group(1).strip()
                degree_type = m.group(2).strip()
                program_url = urljoin(school_url, href)
                key = f'{major_name} ({degree_type})'
                if key not in programs:
                    programs[key] = {
                        'major_name': major_name,
                        'degree_type': degree_type,
                        'school_college': school_name,
                        'program_url': program_url,
                        'requirements': [],
                        'total_credits': None,
                    }
                    print(f'  Found: {key}')

            elif school_name == 'School of Education' and href and '/education/' in href:
                if any(kw in link_text.lower() for kw in [
                    'education', 'bilingual', 'early childhood',
                    'elementary', 'secondary', 'special education',
                ]):
                    major_name = link_text.strip()
                    degree_type = 'BSEd'
                    program_url = urljoin(school_url, href)
                    key = f'{major_name} ({degree_type})'
                    if key not in programs:
                        programs[key] = {
                            'major_name': major_name,
                            'degree_type': degree_type,
                            'school_college': school_name,
                            'program_url': program_url,
                            'requirements': [],
                            'total_credits': None,
                        }
                        print(f'  Found (education): {key}')

        print(f'  Total programs: {len(programs)}')
    except Exception as e:
        print(f'  Error scraping {school_name}: {e}')
    return programs


def scrape_all_schools():
    schools = [
        {'name': 'College of Arts and Sciences',
         'url': 'https://catalog.luc.edu/undergraduate/arts-sciences/#academicstext'},
        {'name': 'Quinlan School of Business',
         'url': 'https://catalog.luc.edu/undergraduate/business/#academicstext'},
        {'name': 'School of Communication',
         'url': 'https://catalog.luc.edu/undergraduate/communication/#academicstext'},
        {'name': 'School of Education',
         'url': 'https://catalog.luc.edu/undergraduate/education/#academicstext'},
        {'name': 'School of Environmental Sustainability',
         'url': 'https://catalog.luc.edu/undergraduate/environmental-sustainability/#academicstext'},
        {'name': 'Parkinson School of Health Sciences and Public Health',
         'url': 'https://catalog.luc.edu/undergraduate/health-sciences-public-health/#academicstext'},
        {'name': 'Marcella Niehoff School of Nursing',
         'url': 'https://catalog.luc.edu/undergraduate/nursing/#academicstext'},
        {'name': 'School of Social Work',
         'url': 'https://catalog.luc.edu/undergraduate/social-work/#academicstext'},
        {'name': 'School of Continuing and Professional Studies',
         'url': 'https://catalog.luc.edu/undergraduate/continuing-professional-studies/#academicstext'},
    ]
    all_programs = {}
    for school in schools:
        progs = scrape_school_programs(school['url'], school['name'])
        all_programs.update(progs)
        time.sleep(1)
    return all_programs


def populate_all_requirements(programs):
    total = len(programs)
    print(f'\nPopulating requirements for {total} programs...')
    for idx, (key, prog) in enumerate(programs.items(), 1):
        url = prog.get('program_url')
        if not url:
            continue
        curriculum_url = f'{url}#curriculumtext'
        print(f'[{idx}/{total}] {key}')
        result = parse_curriculum_page(curriculum_url)
        prog['requirements'] = result['requirements']
        prog['total_credits'] = result['total_credits']
        if result['requirements']:
            print(f'  {len(result["requirements"])} groups, {result["total_credits"]} credits')
        else:
            print('  No requirements found.')
    return programs


def main():
    import os
    output_file = 'majors_structured_fixed.json'

    print('=' * 70)
    print('SCRAPING LOYOLA CHICAGO BACHELOR PROGRAMS (FIXED)')
    print('=' * 70)

    print('\nStep 1: Discovering programs...')
    all_programs = scrape_all_schools()
    print(f'\nTotal programs found: {len(all_programs)}')

    print('\nStep 2: Extracting requirements...')
    all_programs = populate_all_requirements(all_programs)

    sorted_programs = dict(sorted(all_programs.items()))
    output_data = {
        'university_core': get_university_core_requirements(),
        'programs': sorted_programs,
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f'\nSaved to {output_file}')
    with_reqs = sum(1 for p in sorted_programs.values() if p['requirements'])
    with_credits = sum(1 for p in sorted_programs.values() if p.get('total_credits'))
    print(f'Programs with requirements : {with_reqs}')
    print(f'Programs with credit totals: {with_credits}')
    print('Done.')


if __name__ == '__main__':
    main()