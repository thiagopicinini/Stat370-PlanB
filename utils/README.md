# Utils Module

This directory contains utility modules used across the Stat370-PlanB project.

## paths.py

Centralized path management to ensure consistent file access across all scripts.

### Usage Example

```python
from utils.paths import MAJORS_JSON, MERGED_ENROLLMENT, TEST_OUTPUT_DIR

# Read data files
with open(MAJORS_JSON, 'r') as f:
    data = json.load(f)

# Save test output
output_file = TEST_OUTPUT_DIR / 'my_test_output.html'
with open(output_file, 'w') as f:
    f.write(content)
```

### Available Paths

**Directories:**
- `PROJECT_ROOT`: Root directory of the project
- `ORIGINAL_DATA_DIR`: Original data files (read-only)
- `FILTERED_DATA_DIR`: Processed/filtered data files
- `DATA_ANALYSIS_DIR`: Analysis outputs and notebooks
- `TEST_OUTPUT_DIR`: Test script outputs

**Data Files:**
- `MERGED_ENROLLMENT`: Merged student enrollment TSV
- `MAJORS_JSON`: Bachelor's degree programs JSON
- `COURSES_JSON`: Course details JSON
- `SEMESTER_STATS`: Semester statistics CSV

**Helper Functions:**
- `get_enrollment_files()`: Returns list of original enrollment files
- `get_filtered_enrollment_files()`: Returns list of filtered enrollment files

### Benefits

1. **No hardcoded paths**: All paths relative to project root
2. **Portable**: Works regardless of where project is cloned
3. **Consistent**: Single source of truth for file locations
4. **Maintainable**: Change paths in one place
