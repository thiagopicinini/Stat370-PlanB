# Dev Scripts - Major Recommender System

This directory contains the core major recommendation system and web application.

## Files

### major_recommender.py

**Purpose**: Core recommendation engine that analyzes student transcripts and matches courses to major requirements.

**Key Classes:**
- `MajorRecommender`: Main class for recommendation logic

**Key Methods:**
- `get_student_info(student_id)`: Retrieve student information
- `get_student_courses(student_id)`: Get all passed courses for a student
- `calculate_major_match(student_courses, major_name)`: Calculate credits earned toward a major
- `recommend_majors(student_id, top_n)`: Generate top N major recommendations

**Usage:**
```python
from major_recommender import MajorRecommender
from utils.paths import MAJORS_JSON, COURSES_JSON, get_filtered_enrollment_files

enrollment_files = [str(f) for f in get_filtered_enrollment_files()]
recommender = MajorRecommender(MAJORS_JSON, COURSES_JSON, enrollment_files)

results = recommender.recommend_majors('student_id', top_n=5)
```

**Test Mode:**
```bash
python major_recommender.py
```
This runs the system on 10 random students for validation.

---

### planb.py

**Purpose**: Flask web application providing user interface for the major recommender.

**Routes:**
- `/` - Login page
- `/login` - Handle authentication
- `/recommendations` - Display recommendations
- `/logout` - Clear session

**Running the App:**
```bash
python planb.py
```
Then open `http://localhost:5001` in your browser.

**Authentication:**
- Student ID: Any valid student ID from enrollment data
- Password: `1234` (demo password for all students)

**Features:**
- Student authentication
- Personalized recommendations
- Visual progress indicators
- Course matching details

---

### debug_recommender.py

**Purpose**: Diagnostic tool to troubleshoot recommendation issues.

**What It Checks:**
- Student enrollment data loading
- Major requirements data structure
- Course code matching
- Match calculation logic
- Common issues (empty requirements, format mismatches)

**Usage:**
```bash
python debug_recommender.py
```

**Output:**
- Student course history
- Major requirements analysis
- Match detection results
- Diagnostic messages

---

### templates/

Flask HTML templates for the web interface.

**login.html**: Student authentication page
**recommendations.html**: Results display with ranked majors

---

## How the System Works

1. **Data Loading**
   - Loads student enrollment data from TSV files
   - Loads major requirements from JSON (scraped catalog data)
   - Filters for undergraduate (UGRD) students only

2. **Course Matching**
   - Identifies all courses student has passed (A-C or P grades)
   - Compares against required courses for each major
   - Handles OR conditions and elective requirements

3. **Recommendation Ranking**
   - Calculates total credits earned toward each major
   - Counts number of matching courses
   - Computes completion percentage
   - Ranks by credits earned (descending)

4. **Output**
   - Top 5 alternative majors (excludes current major)
   - Credits earned toward each
   - Completion percentage
   - List of matched courses

---

## Data Requirements

**Input Files:**
- `filtered_data/merged_student_enrollment.tsv` - Combined enrollment data
- `filtered_data/bachelors_majors_web.json` - Major requirements
- `filtered_data/courses.json` - Course details (optional)

**Data Format:**

Enrollment TSV must include:
- `LID`: Student ID
- `Subject`: Course subject (e.g., "COMP")
- `CatalogNumber`: Course number (e.g., "271")
- `FinalGrade`: Letter grade
- `Units_Earned`: Credits
- `Term`: Semester code
- `Career`: Student level (UGRD/GRAD)
- `Active_Plan_List`: Current major

Majors JSON structure:
```json
{
  "programs": {
    "Major Name (BS)": {
      "major_name": "Major Name",
      "degree_type": "BS",
      "school_college": "College Name",
      "required_courses": ["SUBJ 101", "SUBJ 202", ...],
      "total_major_courses": 45
    }
  }
}
```

---

## Troubleshooting

**No recommendations returned:**
- Run `debug_recommender.py` to diagnose
- Check that major requirements are populated
- Verify course codes match between enrollment and requirements
- Ensure student has passed some courses

**Import errors:**
- Ensure you're running from project root or scripts directory
- Check that `utils/paths.py` exists
- Verify all required packages are installed

**Flask errors:**
- Check that filtered data files exist
- Verify port 5001 is not in use
- Ensure templates/ directory contains HTML files

---

## Future Enhancements

- Support for minor recommendations
- GPA-weighted recommendations
- Time-to-degree estimates
- Course scheduling suggestions
- Prerequisite path planning
