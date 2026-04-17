#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/osanchezhuezca/Documents/GitHub/Stat370-PlanB/dev_scripts')
from major_recommender import MajorRecommender
import glob

enrollment_files = sorted(glob.glob('/Users/osanchezhuezca/Documents/GitHub/Stat370-PlanB/filtered_data/deident_student_enrollment_*.tsv'))
recommender = MajorRecommender(
    majors_file='/Users/osanchezhuezca/Documents/GitHub/Stat370-PlanB/filtered_data/majors_structured.json',
    courses_file='/Users/osanchezhuezca/Documents/GitHub/Stat370-PlanB/filtered_data/courses.json',
    enrollment_files=enrollment_files
)

# Find a student with recommendations
count = 0
for sem_key, df in list(recommender.student_data_by_semester.items())[:1]:
    for idx, row in df.head(500).iterrows():
        student_id = str(int(row['LID']))
        result = recommender.recommend_majors(student_id)
        if result and result.get('recommended_majors') and len(result['recommended_majors']) > 0:
            print(f'Found student {student_id} with {len(result["recommended_majors"])} recommendations')
            print(f'  Total courses passed: {result.get("total_courses_passed", 0)}')
            print(f'  Total credits: {result.get("total_credits_earned", 0)}')
            count += 1
            if count >= 3:
                break
    if count >= 3:
        break
