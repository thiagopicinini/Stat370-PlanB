"""
Extract all unique major/program names from deident_student_enrollment files.

This script reads through all deident_student_enrollment TSV files and pulls out
all unique major names from the Program and Active_Plan_List columns.
"""

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.paths import get_filtered_enrollment_files


def extract_major_names_from_enrollment_files():
    """
    Extract all unique major/program names from enrollment files.
    
    Returns:
        dict: Dictionary with statistics and lists of majors found
    """
    enrollment_files = get_filtered_enrollment_files()
    
    major_names = set()
    major_counts = defaultdict(int)
    file_sources = defaultdict(set)
    
    print("Reading enrollment files...")
    print("=" * 80)
    
    for file_path in sorted(enrollment_files):
        print(f"\nProcessing: {Path(file_path).name}")
        
        try:
            df = pd.read_csv(file_path, sep='\t')
            print(f"  Rows: {len(df)}")
            
            # Extract from Program column
            if 'Program' in df.columns:
                programs = df['Program'].dropna().unique()
                for prog in programs:
                    prog_str = str(prog).strip()
                    if prog_str and prog_str.lower() not in ['nan', 'none', '']:
                        major_names.add(prog_str)
                        major_counts[prog_str] += len(df[df['Program'] == prog_str])
                        file_sources[prog_str].add(Path(file_path).stem)
                print(f"  Programs found: {len(programs)}")
            
            # Extract from Active_Plan_List column
            if 'Active_Plan_List' in df.columns:
                active_plans = df['Active_Plan_List'].dropna().unique()
                for plan in active_plans:
                    plan_str = str(plan).strip()
                    if plan_str and plan_str.lower() not in ['nan', 'none', '']:
                        major_names.add(plan_str)
                        major_counts[plan_str] += len(df[df['Active_Plan_List'] == plan_str])
                        file_sources[plan_str].add(Path(file_path).stem)
                print(f"  Active plans found: {len(active_plans)}")
            
            # Extract from AcademicGroup column (alternative major grouping)
            if 'AcademicGroup' in df.columns:
                academic_groups = df['AcademicGroup'].dropna().unique()
                for group in academic_groups:
                    group_str = str(group).strip()
                    if group_str and group_str.lower() not in ['nan', 'none', '']:
                        major_names.add(f"[AcademicGroup] {group_str}")
                        major_counts[f"[AcademicGroup] {group_str}"] += len(df[df['AcademicGroup'] == group_str])
                        file_sources[f"[AcademicGroup] {group_str}"].add(Path(file_path).stem)
                print(f"  Academic groups found: {len(academic_groups)}")
        
        except Exception as e:
            print(f"  ERROR reading file: {str(e)}")
            continue
    
    # Sort by frequency
    sorted_majors = sorted(major_counts.items(), key=lambda x: x[1], reverse=True)
    
    print("\n" + "=" * 80)
    print(f"\nTOTAL UNIQUE MAJORS FOUND: {len(major_names)}")
    print("=" * 80)
    
    # Display results
    print("\nMajors by frequency (student-semester records):")
    print("-" * 80)
    for major, count in sorted_majors:
        sources = ", ".join(sorted(file_sources[major]))
        print(f"{count:5d}  {major[:60]:<60}")
        if len(major) > 60:
            print(f"        {major[60:]}")
    
    # Save to file for reference
    output_file = Path(__file__).parent.parent / "filtered_data" / "major_names_from_enrollment.json"
    output_data = {
        "total_unique_majors": len(major_names),
        "majors_by_frequency": [
            {
                "major_name": major,
                "student_records_count": count,
                "found_in_files": sorted(list(file_sources[major]))
            }
            for major, count in sorted_majors
        ],
        "all_majors_sorted": sorted(list(major_names))
    }
    
    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\n✓ Results saved to: {output_file}")
    
    return output_data


def main():
    """Main entry point."""
    data = extract_major_names_from_enrollment_files()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total unique majors: {data['total_unique_majors']}")
    print(f"Total major-frequency records: {len(data['majors_by_frequency'])}")
    
    # Show top 10
    print("\nTop 10 majors:")
    for i, entry in enumerate(data['majors_by_frequency'][:10], 1):
        print(f"  {i}. {entry['major_name']} ({entry['student_records_count']} records)")


if __name__ == '__main__':
    main()
