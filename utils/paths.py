"""
Centralized path management for the Stat370-PlanB project.

This module provides consistent path handling across all scripts,
avoiding relative path issues and ensuring portability.
"""
from pathlib import Path

# Project root directory (parent of utils/)
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
ORIGINAL_DATA_DIR = PROJECT_ROOT / 'original_data'
FILTERED_DATA_DIR = PROJECT_ROOT / 'filtered_data'
DATA_ANALYSIS_DIR = PROJECT_ROOT / 'data_analysis'

# Output directories
TEST_OUTPUT_DIR = PROJECT_ROOT / 'test_output'

# Specific data files
MERGED_ENROLLMENT = FILTERED_DATA_DIR / 'merged_student_enrollment.tsv'
MAJORS_JSON = FILTERED_DATA_DIR / 'bachelors_majors_web.json'
COURSES_JSON = FILTERED_DATA_DIR / 'courses.json'
SEMESTER_STATS = DATA_ANALYSIS_DIR / 'semester_statistics.csv'

# Ensure output directories exist
TEST_OUTPUT_DIR.mkdir(exist_ok=True)
FILTERED_DATA_DIR.mkdir(exist_ok=True)


def get_enrollment_files():
    """
    Get all enrollment TSV files from the original_data directory.
    
    Returns:
        list: List of Path objects for enrollment files
    """
    return sorted(ORIGINAL_DATA_DIR.glob('deident_student_enrollment_*.tsv'))


def get_filtered_enrollment_files():
    """
    Get all filtered enrollment TSV files from the filtered_data directory.
    
    Returns:
        list: List of Path objects for filtered enrollment files
    """
    return sorted(FILTERED_DATA_DIR.glob('deident_student_enrollment_*.tsv'))
