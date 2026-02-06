# Test Scripts

This directory contains testing and validation scripts for the data gathering pipeline.

## Purpose

These scripts help develop and validate the web scraping logic before running the full data collection process. They save sample HTML files and test parsing logic on small datasets.

---

## Scripts Overview

### save_sample_course_html.py

**Purpose**: Save sample course detail pages for analysis.

**What It Does:**
- Fetches HTML for a specific course from Loyola catalog
- Saves raw HTML to `test_output/` directory
- Helps understand page structure for scraper development

**Usage:**
```bash
python save_sample_course_html.py
```

**Modify the course to test:**
```python
if __name__ == "__main__":
    course_code = "COMP 330"  # Change this
    save_course_html(course_code)
```

**Output:**
- `test_output/sample_course_COMP_330.html`

**Use Cases:**
- Inspecting HTML structure
- Identifying CSS selectors
- Testing parsing logic
- Debugging scraper issues

---

### save_sample_curriculum_html.py

**Purpose**: Save sample curriculum/major requirement pages for analysis.

**What It Does:**
- Selects a random bachelor's program
- Fetches the curriculum page HTML
- Saves raw HTML and extracts sample courses
- Shows preview of course extraction

**Usage:**
```bash
python save_sample_curriculum_html.py
```

**Output:**
- `test_output/sample_curriculum_[ProgramName]_[Degree].html`
- Console output showing extracted courses

**Features:**
- Random program selection across all schools
- Preview of parsed required courses
- Validation of course extraction logic

---

### test_course_scraper.py

**Purpose**: Test course detail scraping on sample courses.

**What It Does:**
- Tests scraper on 8 sample courses from different departments
- Validates data extraction for:
  - Course titles
  - Credit hours
  - Descriptions
  - Prerequisites
  - Corequisites
  - Equivalencies
- Displays detailed parsing output

**Sample Courses:**
- ACCT 201 (Accounting)
- MATH 161 (Calculus)
- COMM 100 (Communication)
- COMP 271 (Computer Science)
- BIOL 101 (Biology)
- PHYS 121 (Physics)
- CHEM 111 (Chemistry)
- PSYC 101 (Psychology)

**Usage:**
```bash
python test_course_scraper.py
```

**Output:**
- Detailed extraction results for each course
- JSON summary of all scraped data
- Success/failure statistics

**Modify test courses:**
```python
test_courses = [
    "YOUR 101",
    "COURSE 202",
    # Add more...
]
```

---

### test_scrape_preview.py

**Purpose**: Preview major scraping across all schools before full run.

**What It Does:**
- Fetches program lists from all 9 schools
- Displays program names and URLs
- Tests curriculum extraction on random samples
- Shows course extraction preview

**Usage:**
```bash
python test_scrape_preview.py
```

**Output:**
- List of programs found in each school
- Curriculum URLs for each program
- Sample curriculum extraction for random programs
- Course counts and formats

**Benefits:**
- Validates scraper before full run
- Identifies issues early
- Shows expected data volume
- Tests across different program formats

---

## Workflow

### 1. Validate Course Scraping

```bash
# Save a sample course page
python save_sample_course_html.py

# Inspect the HTML structure
open test_output/sample_course_*.html

# Test the scraper
python test_course_scraper.py
```

### 2. Validate Major Scraping

```bash
# Save a sample curriculum page
python save_sample_curriculum_html.py

# Inspect the HTML
open test_output/sample_curriculum_*.html

# Preview all schools
python test_scrape_preview.py
```

### 3. Run Full Data Collection

```bash
# After validation passes
cd ../data_gathering_scripts
python scrape_majors_from_web.py
python scrape_course_details.py
```

---

## Output Directory

All test outputs are saved to `test_output/`:

```
test_output/
├── sample_course_COMP_330.html
├── sample_course_MATH_161.html
├── sample_curriculum_Computer_Science_BS.html
└── sample_curriculum_Biology_BS.html
```

This directory is created automatically by the scripts.

---

## Development Tips

**Testing New Selectors:**
1. Save sample HTML with save scripts
2. Open HTML in browser
3. Inspect elements to find CSS selectors
4. Update scraper logic
5. Test with test scripts
6. Validate output

**Debugging Scraping Issues:**
1. Save problematic page with save scripts
2. Check HTML structure manually
3. Verify CSS class names
4. Test regex patterns
5. Check for dynamic content
6. Validate encoding issues

**Adding New Test Cases:**
```python
# In test_course_scraper.py
test_courses = [
    "EXISTING 101",
    "NEW 202",  # Add your test course
]
```

---

## Common Issues

**No HTML Saved:**
- Check internet connection
- Verify course code format
- Check catalog URL is accessible
- Look for timeout errors

**Extraction Returns Empty:**
- HTML structure may have changed
- CSS selectors need updating
- Course may not exist in catalog
- Check for JavaScript-rendered content

**Import Errors:**
```bash
pip install requests beautifulsoup4
```

**Path Errors:**
- Scripts create `test_output/` automatically
- Run from project root or test_scripts/
- Check `utils/paths.py` is accessible

---

## Validation Checklist

Before running full data collection:

- [ ] Course scraper extracts all fields correctly
- [ ] Prerequisites are parsed properly
- [ ] Credit hours are captured
- [ ] Major scraper finds all programs
- [ ] Required courses are extracted
- [ ] OR conditions are handled
- [ ] Electives are identified
- [ ] No major errors in test runs
- [ ] Output formats are correct
- [ ] Sample data looks valid

---

## Best Practices

**Regular Testing:**
- Test scrapers before each full run
- Validate after catalog updates
- Check sample outputs manually
- Compare with previous results

**Error Handling:**
- Scripts continue on individual failures
- Log errors for review
- Validate output completeness
- Check for pattern changes

**Performance:**
- Test scripts use same delays as production
- Small sample sizes for quick validation
- Full runs after successful tests
- Monitor server response times

---

## Next Steps

After successful testing:

1. Review test outputs for accuracy
2. Fix any issues found
3. Run full data gathering scripts
4. Validate complete datasets
5. Update scrapers if catalog changes
