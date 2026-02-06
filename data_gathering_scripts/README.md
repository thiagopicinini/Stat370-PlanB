# Data Gathering Scripts

This directory contains scripts for collecting and preparing data from various sources.

## Scripts Overview

### dataprep.py

**Purpose**: Data preparation and cleaning utilities.

**Functions:**

1. `filter_ugrd_students(input_file, output_file)`
   - Filters enrollment data to keep only undergraduate (UGRD) students
   - Removes graduate and other non-undergraduate records
   - Essential preprocessing step for accurate recommendations

2. `extract_text_from_pdf(pdf_file, output_file)`
   - Extracts text from PDF course catalogs
   - Uses PyPDF2 library
   - Useful for analyzing catalog content

3. `batch_extract_pdfs(pdf_directory, output_directory)`
   - Batch processes multiple PDF files
   - Extracts text from all PDFs in a directory

4. `process_all_enrollment_files()`
   - Processes all enrollment TSV files from original_data/
   - Filters for UGRD students
   - Saves to filtered_data/

**Usage:**
```bash
python dataprep.py
```

**Requirements:**
- pandas
- PyPDF2

---

### scrape_majors_from_web.py

**Purpose**: Scrape bachelor's degree program requirements from Loyola University course catalog.

**What It Scrapes:**
- All bachelor's degree programs across 9 schools/colleges
- Required courses for each major
- Elective requirements with options
- OR conditions between courses
- Selective requirements (e.g., "Select 2 of the following")

**Output:**
- `filtered_data/bachelors_majors_web.json`

**Data Structure:**
```json
{
  "university_core": {...},
  "programs": {
    "Major Name (Degree)": {
      "major_name": "...",
      "degree_type": "BS/BA/BBA/etc",
      "school_college": "...",
      "program_url": "...",
      "required_courses": [
        "SUBJ 101",
        "SUBJ 201 or SUBJ 202",
        {"options": ["SUBJ 301", "SUBJ 302"]},
        "[Elective: Select 2 from list]"
      ],
      "total_major_courses": 45
    }
  }
}
```

**Schools Scraped:**
- College of Arts and Sciences
- Quinlan School of Business
- School of Communication
- School of Education
- School of Environmental Sustainability
- Parkinson School of Health Sciences and Public Health
- Marcella Niehoff School of Nursing
- School of Social Work
- School of Continuing and Professional Studies

**Usage:**
```bash
python scrape_majors_from_web.py
```

**Features:**
- Handles OR relationships (e.g., "MATH 161 or MATH 165")
- Identifies elective blocks
- Excludes university core courses from major requirements
- Respects server with built-in delays

**Requirements:**
- requests
- beautifulsoup4

---

### scrape_course_details.py

**Purpose**: Scrape detailed course information from Loyola University catalog.

**What It Scrapes:**
- Course titles
- Course descriptions
- Credit hours
- Prerequisites
- Corequisites
- Course equivalencies

**Sources:**
- Courses from major requirements
- Courses from enrollment data
- Combines both sources for complete coverage

**Output:**
- `filtered_data/courses.json`

**Data Structure:**
```json
{
  "SUBJ 101": {
    "course_code": "SUBJ 101",
    "course_url": "...",
    "course_title": "Introduction to Subject",
    "course_description": "...",
    "credit_hours": "3",
    "prerequisites": ["SUBJ 100"],
    "corequisites": [],
    "course_equivalencies": []
  }
}
```

**Usage:**
```bash
python scrape_course_details.py
```

**Features:**
- Extracts prerequisites from complex text descriptions
- Handles multiple prerequisite formats
- Removes grade requirements to get just course codes
- Provides progress updates during scraping
- Graceful error handling for missing courses

**Requirements:**
- requests
- beautifulsoup4

**Performance:**
- Scrapes 500+ courses
- Includes 0.3s delay between requests
- Takes approximately 3-5 minutes for full run

---

## Data Pipeline

Recommended execution order:

1. **Prepare Enrollment Data**
```bash
python dataprep.py
```
Filters original enrollment files to UGRD only.

2. **Scrape Major Requirements**
```bash
python scrape_majors_from_web.py
```
Collects all bachelor's program requirements.

3. **Scrape Course Details**
```bash
python scrape_course_details.py
```
Gets detailed information for all referenced courses.

---

## Output Files

All output files are saved to `filtered_data/`:

- `deident_student_enrollment_*.tsv` - Filtered enrollment data
- `merged_student_enrollment.tsv` - Combined all semesters
- `bachelors_majors_web.json` - Major requirements
- `courses.json` - Course details

---

## Web Scraping Notes

**Ethical Considerations:**
- Respects robots.txt
- Includes delays between requests
- Only scrapes public catalog information
- No user data or private information

**Rate Limiting:**
- 0.3-1 second delays between requests
- Batch processing with progress updates
- Timeout handling for slow connections

**Error Handling:**
- Graceful handling of missing pages
- Retry logic for network errors
- Continues on individual failures
- Detailed logging of issues

---

## Troubleshooting

**Import Errors:**
```bash
pip install pandas beautifulsoup4 requests PyPDF2
```

**Scraping Fails:**
- Check internet connection
- Verify catalog URLs haven't changed
- Check for robots.txt restrictions
- Increase timeout values if needed

**Empty Results:**
- Verify catalog structure hasn't changed
- Check HTML class names in scraper
- Run test scripts first to validate

**Path Errors:**
- Scripts use centralized paths from `utils/paths.py`
- Run from project root or scripts directory
- Check that data directories exist

---

## Data Quality

**Validation:**
- Check for empty major requirements
- Verify course code formats
- Compare enrollment data counts
- Review scraping success rates

**Known Issues:**
- Some majors may have incomplete requirements
- Elective descriptions vary in format
- Prerequisites may include non-course requirements
- Course equivalencies may be partial

---

## Maintenance

**Regular Updates:**
- Re-run scrapers when catalog updates
- Verify data structure compatibility
- Update selectors if HTML changes
- Check for new schools/programs

**Data Freshness:**
- Enrollment data: Academic years covered
- Major requirements: Catalog year
- Course details: Current catalog
