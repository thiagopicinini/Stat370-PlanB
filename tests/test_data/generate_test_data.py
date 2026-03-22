"""
generate_test_data.py — Creates synthetic test data for the Plan B test suite.

WHY DO WE NEED FAKE DATA?
    The real student enrollment data (TSV files in filtered_data/) is:
    1. Too large for fast testing
    2. Contains de-identified but real student info (privacy concern)
    3. Not available in GitHub Actions CI (it's gitignored)

    So we create 30 fake students (S001-S030), each hand-crafted to produce
    a KNOWN expected outcome. This lets us write assertions like:
        "S001 should get Statistics as a recommendation"
    because we specifically gave S001 lots of Statistics courses.

WHAT FILES DOES THIS SCRIPT CREATE?
    tests/test_data/
    ├── test_majors.json                         ← 6 fake majors
    ├── test_courses.json                        ← ~50 fake course definitions
    ├── deident_student_enrollment_Fall2019.tsv   ← fall semester rows
    ├── deident_student_enrollment_Spring2020.tsv ← spring semester rows
    └── deident_student_enrollment_Fall2020.tsv   ← combined (all rows)

HOW TO RUN:
    python tests/test_data/generate_test_data.py
"""
import json
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent

# ── 1. Fake majors (mirrors bachelors_majors_web.json structure) ─────

MAJORS_JSON = {
    "university_core": {
        "category": "University Core Curriculum",
        "description": "Required foundation courses.",
        "areas": [],
        "total_credit_hours": "Approximately 34-37 credit hours"
    },
    "programs": {
        "Computer Science (BS)": {
            "major_name": "Computer Science", "degree_type": "BS",
            "school_college": "College of Arts and Sciences",
            "department": "Computer Science",
            "program_url": "https://example.com/cs",
            "required_courses": [
                "MATH 161", "MATH 162", "COMP 141", "COMP 170",
                "COMP 264", "COMP 271", "COMP 272", "COMP 310",
                "COMP 317", "COMP 363", "COMP 371", "STAT 203"
            ]
        },
        "Statistics (BS)": {
            "major_name": "Statistics", "degree_type": "BS",
            "school_college": "College of Arts and Sciences",
            "department": "Mathematics Statistics",
            "program_url": "https://example.com/stat",
            "required_courses": [
                "MATH 161", "MATH 162", "MATH 212", "MATH 263",
                "STAT 203 or STAT 335",
                "STAT 303", "STAT 304", "STAT 305", "STAT 307", "STAT 308"
            ]
        },
        "Mathematics (BS)": {
            "major_name": "Mathematics", "degree_type": "BS",
            "school_college": "College of Arts and Sciences",
            "department": "Mathematics Statistics",
            "program_url": "https://example.com/math",
            "required_courses": [
                "MATH 161", "MATH 162", "MATH 201", "MATH 212",
                "MATH 263", "MATH 264", "STAT 203", "MATH 313", "MATH 351"
            ]
        },
        "Accounting (BBA)": {
            "major_name": "Accounting", "degree_type": "BBA",
            "school_college": "Quinlan School of Business",
            "department": "Accounting Bba",
            "program_url": "https://example.com/acct",
            "required_courses": [
                "ACCT 201", "ACCT 202", "ECON 201", "ECON 202",
                "MGMT 201", "MGMT 304", "MARK 201",
                "ACCT 303", "ACCT 304", "ACCT 311"
            ]
        },
        "Psychology (BS)": {
            "major_name": "Psychology", "degree_type": "BS",
            "school_college": "College of Arts and Sciences",
            "department": "Psychology",
            "program_url": "https://example.com/psych",
            "required_courses": [
                "PSYC 101", "PSYC 200", "PSYC 201", "PSYC 202",
                "PSYC 301", "PSYC 302", "PSYC 304", "STAT 203"
            ]
        },
        "Biology (BS)": {
            "major_name": "Biology", "degree_type": "BS",
            "school_college": "College of Arts and Sciences",
            "department": "Biology",
            "program_url": "https://example.com/bio",
            "required_courses": [
                "BIOL 101", "BIOL 111", "BIOL 102", "BIOL 112",
                "CHEM 101", "CHEM 102", "PHYS 121", "PHYS 122",
                "MATH 131 or MATH 161", "STAT 203"
            ]
        }
    }
}

# ── 2. Fake courses (mirrors courses.json structure) ─────────────────

def _ce(code, title):
    return {"course_code": code, "course_url": f"https://example.com/{code.replace(' ','')}",
            "course_title": title, "course_description": f"Description for {title}."}

COURSES_JSON = {c: _ce(c,t) for c,t in [
    ("MATH 161","Calculus I"),("MATH 162","Calculus II"),("MATH 131","Applied Calculus I"),
    ("MATH 201","Discrete Math"),("MATH 212","Linear Algebra"),("MATH 263","Multivariable Calc"),
    ("MATH 264","ODE"),("MATH 313","Abstract Algebra"),("MATH 351","Real Analysis"),
    ("COMP 141","Intro Computing"),("COMP 170","Intro CS"),("COMP 264","Systems"),
    ("COMP 271","Data Structures"),("COMP 272","Software Eng"),("COMP 310","Algorithms"),
    ("COMP 317","Social Computing"),("COMP 363","Theory"),("COMP 371","Programming Languages"),
    ("STAT 203","Intro Stats"),("STAT 303","Probability"),("STAT 304","Math Stats"),
    ("STAT 305","Regression"),("STAT 307","Statistical Design"),("STAT 308","Applied Stats"),
    ("STAT 335","Intro Biostat"),
    ("ACCT 201","Intro Acct I"),("ACCT 202","Intro Acct II"),("ACCT 303","Intermed Acct I"),
    ("ACCT 304","Intermed Acct II"),("ACCT 311","Cost Accounting"),
    ("ECON 201","Microecon"),("ECON 202","Macroecon"),
    ("MGMT 201","Principles of Mgmt"),("MGMT 304","Strategic Mgmt"),("MARK 201","Marketing"),
    ("PSYC 101","Intro Psych"),("PSYC 200","Research Methods"),("PSYC 201","Brain & Behavior"),
    ("PSYC 202","Developmental"),("PSYC 301","Personality"),("PSYC 302","Social Psych"),
    ("PSYC 304","Abnormal Psych"),
    ("BIOL 101","Intro Bio I"),("BIOL 102","Intro Bio II"),("BIOL 111","Bio Lab I"),
    ("BIOL 112","Bio Lab II"),("CHEM 101","Gen Chem I"),("CHEM 102","Gen Chem II"),
    ("PHYS 121","Intro Physics I"),("PHYS 122","Intro Physics II"),
    ("ENGL 100","Freshman Writing"),("HIST 101","Western Civ"),("PHIL 101","Intro Philosophy"),
]}

# ── 3. Fake enrollment rows (30 students) ────────────────────────────

HEADER = "LID\tName\tTerm\tCareer\tSubject\tCatalogNumber\tFinalGrade\tUnits_Earned\tAcademic_Level\tActive_Plan_List"

def row(lid, name, term, subject, cat, grade, units, level, plan):
    return f"{lid}\t{name}\t{term}\tUGRD\t{subject}\t{cat}\t{grade}\t{units}\t{level}\t{plan}"

STUDENTS = []

# S001: CS major, took Stats courses → expect Stats rec
for c in [("MATH","161","A"),("MATH","162","A-"),("STAT","203","B+"),("STAT","303","B"),("STAT","304","A"),("STAT","305","B+"),("COMP","170","A"),("COMP","141","A")]:
    STUDENTS.append(row("S001","Alice Test","2196",c[0],c[1],c[2],3,"Senior","Computer Science (BS)"))

# S002: Stats major, took CS courses → expect CS rec
for c in [("MATH","161","A"),("MATH","162","B+"),("COMP","141","A"),("COMP","170","A"),("COMP","264","B"),("COMP","271","B+"),("COMP","272","A-"),("STAT","203","A"),("COMP","310","B")]:
    STUDENTS.append(row("S002","Bob Test","2196",c[0],c[1],c[2],3,"Senior","Statistics (BS)"))

# S003: Math major, mixed → expect Stats or CS
for c in [("MATH","161","A"),("MATH","162","A"),("MATH","212","B+"),("MATH","263","B"),("STAT","203","A"),("STAT","303","B+"),("COMP","170","B"),("MATH","264","A")]:
    STUDENTS.append(row("S003","Charlie Test","2196",c[0],c[1],c[2],3,"Junior","Mathematics (BS)"))

# S004: Psych major, only STAT 203 overlaps STEM
for c in [("PSYC","101","A"),("PSYC","200","B+"),("PSYC","201","B"),("PSYC","202","A"),("STAT","203","B"),("ENGL","100","A")]:
    STUDENTS.append(row("S004","Diana Test","2196",c[0],c[1],c[2],3,"Junior","Psychology (BS)"))

# S005: Accounting, zero STEM overlap
for c in [("ACCT","201","B+"),("ACCT","202","B"),("ECON","201","A"),("ECON","202","B+"),("MGMT","201","A"),("MGMT","304","B")]:
    STUDENTS.append(row("S005","Eva Test","2196",c[0],c[1],c[2],3,"Senior","Accounting (BBA)"))

# S006: Bio major, full bio + some STEM overlap
for c in [("BIOL","101","A"),("BIOL","111","A"),("BIOL","102","B+"),("BIOL","112","B"),("CHEM","101","A"),("CHEM","102","B"),("PHYS","121","B+"),("PHYS","122","B"),("MATH","161","A"),("STAT","203","B+")]:
    STUDENTS.append(row("S006","Frank Test","2196",c[0],c[1],c[2],3,"Senior","Biology (BS)"))

# S007: CS freshman, only 2 courses
for c in [("MATH","161","B+"),("COMP","141","A")]:
    STUDENTS.append(row("S007","Grace Test","2196",c[0],c[1],c[2],3,"Freshman","Computer Science (BS)"))

# S008: Undeclared, wide mix
for c in [("MATH","161","A"),("MATH","162","B"),("STAT","203","A"),("COMP","141","B+"),("PSYC","101","A"),("ECON","201","B")]:
    STUDENTS.append(row("S008","Hank Test","2196",c[0],c[1],c[2],3,"Sophomore","Undeclared"))

# S009: Stats major, ALL stats reqs done → stats excluded, math top rec
for c in [("MATH","161","A"),("MATH","162","A"),("MATH","212","A"),("MATH","263","A"),("STAT","203","A"),("STAT","303","A"),("STAT","304","A"),("STAT","305","A"),("STAT","307","A"),("STAT","308","A")]:
    STUDENTS.append(row("S009","Iris Test","2196",c[0],c[1],c[2],3,"Senior","Statistics (BS)"))

# S010: All failing grades → zero recs
for c in [("MATH","161","F"),("COMP","141","F"),("COMP","170","D")]:
    STUDENTS.append(row("S010","Jake Test","2196",c[0],c[1],c[2],3,"Freshman","Computer Science (BS)"))

# S011: Accounting + some CS courses
for c in [("ACCT","201","A"),("ACCT","202","B"),("COMP","141","B+"),("COMP","170","A"),("MATH","161","B"),("ECON","201","A"),("MGMT","201","B+")]:
    STUDENTS.append(row("S011","Kelly Test","2196",c[0],c[1],c[2],3,"Junior","Accounting (BBA)"))

# S012: Bio + lots of math
for c in [("BIOL","101","A"),("MATH","161","A"),("MATH","162","A"),("MATH","212","B+"),("MATH","263","B"),("STAT","203","A"),("CHEM","101","B+")]:
    STUDENTS.append(row("S012","Leo Test","2196",c[0],c[1],c[2],3,"Junior","Biology (BS)"))

# S013: CS across 4 semesters
for t,courses in [("2186",[("MATH","161","A"),("COMP","141","B+"),("ENGL","100","A")]),("2191",[("MATH","162","A"),("COMP","170","A")]),("2196",[("COMP","264","B"),("COMP","271","B+"),("STAT","203","A")]),("2201",[("COMP","310","B"),("COMP","363","A")])]:
    for c in courses:
        STUDENTS.append(row("S013","Mike Test",t,c[0],c[1],c[2],3,"Senior","Computer Science (BS)"))

# S014: Stats across 4 semesters
for t,courses in [("2186",[("MATH","161","A"),("MATH","162","B+")]),("2191",[("MATH","212","A"),("MATH","263","B+"),("STAT","203","A")]),("2196",[("STAT","303","A"),("STAT","304","B+")]),("2201",[("STAT","305","A"),("STAT","307","B"),("STAT","308","A")])]:
    for c in courses:
        STUDENTS.append(row("S014","Nancy Test",t,c[0],c[1],c[2],3,"Senior","Statistics (BS)"))

# S015: Switched Undeclared → CS
for t,plan,courses in [("2196","Undeclared",[("MATH","161","A"),("COMP","141","B")]),("2201","Computer Science (BS)",[("COMP","170","A"),("MATH","162","B+")])]:
    for c in courses:
        STUDENTS.append(row("S015","Oscar Test",t,c[0],c[1],c[2],3,"Sophomore",plan))

# S016: P grades (should count)
for c in [("MATH","161","P"),("MATH","162","P"),("STAT","203","P")]:
    STUDENTS.append(row("S016","Pat Test","2196",c[0],c[1],c[2],3,"Junior","Mathematics (BS)"))

# S017: Mix passing/failing
for c in [("MATH","161","A"),("MATH","162","F"),("COMP","141","A"),("COMP","170","D"),("STAT","203","C")]:
    STUDENTS.append(row("S017","Quinn Test","2196",c[0],c[1],c[2],3,"Sophomore","Computer Science (BS)"))

# S018: GRAD row should be filtered out
STUDENTS.append(f"S018\tRay Test\t2196\tGRAD\tSTAT\t303\tA\t3\tGraduate\tStatistics (BS)")
STUDENTS.append(row("S018","Ray Test","2196","STAT","203","B+",3,"Senior","Statistics (BS)"))
STUDENTS.append(row("S018","Ray Test","2196","MATH","161","A",3,"Senior","Statistics (BS)"))

# S019: Retook MATH 161 (F → B+)
STUDENTS.append(row("S019","Sam Test","2186","MATH","161","F",3,"Freshman","Mathematics (BS)"))
STUDENTS.append(row("S019","Sam Test","2196","MATH","161","B+",3,"Sophomore","Mathematics (BS)"))
STUDENTS.append(row("S019","Sam Test","2196","MATH","162","A",3,"Sophomore","Mathematics (BS)"))

# S020: Psych + Accounting courses → Accounting rec
STUDENTS.append(row("S020","Tina Test","2196","ACCT","201","A",3,"Senior","Psychology (BS)"))
STUDENTS.append(row("S020","Tina Test","2196","ACCT","202","B+",3,"Senior","Psychology (BS)"))
STUDENTS.append(row("S020","Tina Test","2196","PSYC","101","A",3,"Senior","Psychology (BS)"))

# S021: Early student (1 sem) → can complete in 4 years
for c in [("MATH","161","A"),("COMP","141","A"),("STAT","203","B+")]:
    STUDENTS.append(row("S021","Uma Test","2196",c[0],c[1],c[2],3,"Freshman","Computer Science (BS)"))

# S022: Late student (7 semesters) → hard to complete
for t in ["2166","2171","2176","2181","2186","2191","2196"]:
    STUDENTS.append(row("S022","Vic Test",t,"ENGL","100","A",3,"Senior","Computer Science (BS)"))

# S023-S025: Filter testing students
for c in [("MATH","161","A"),("MATH","162","A"),("STAT","203","B"),("COMP","141","B+"),("COMP","170","A")]:
    STUDENTS.append(row("S023","Wendy Test","2196",c[0],c[1],c[2],3,"Junior","Computer Science (BS)"))

for c in [("ACCT","201","A"),("ECON","201","A"),("MATH","161","B+"),("STAT","203","B"),("COMP","141","A")]:
    STUDENTS.append(row("S024","Xavier Test","2196",c[0],c[1],c[2],3,"Junior","Accounting (BBA)"))

for c in [("MATH","161","A"),("STAT","203","B+"),("ACCT","201","B"),("COMP","141","A")]:
    STUDENTS.append(row("S025","Yara Test","2196",c[0],c[1],c[2],3,"Junior","Mathematics (BS)"))

# S026: Single course match
STUDENTS.append(row("S026","Zach Test","2196","STAT","203","A",3,"Freshman","Computer Science (BS)"))

# S027: All Math reqs done → 100% completion
for c in [("MATH","161","A"),("MATH","162","A"),("MATH","212","A"),("MATH","263","A"),("MATH","264","A"),("STAT","203","A"),("MATH","313","A"),("MATH","351","A"),("MATH","201","A")]:
    STUDENTS.append(row("S027","Adam Test","2196",c[0],c[1],c[2],3,"Senior","Computer Science (BS)"))

# S028: All C- grades (minimum passing)
for c in [("MATH","161","C-"),("MATH","162","C-"),("STAT","203","C-"),("COMP","141","C-")]:
    STUDENTS.append(row("S028","Beth Test","2196",c[0],c[1],c[2],3,"Sophomore","Psychology (BS)"))

# S029: Took STAT 335 (satisfies "STAT 203 or STAT 335")
for c in [("MATH","161","A"),("MATH","162","B+"),("MATH","212","B"),("MATH","263","A"),("STAT","335","B+")]:
    STUDENTS.append(row("S029","Carl Test","2196",c[0],c[1],c[2],3,"Junior","Biology (BS)"))

# S030: Units_Earned=0 → defaults to 3
STUDENTS.append(f"S030\tDawn Test\t2196\tUGRD\tMATH\t161\tA\t0\tFreshman\tStatistics (BS)")
STUDENTS.append(f"S030\tDawn Test\t2196\tUGRD\tSTAT\t203\tB\t0\tFreshman\tStatistics (BS)")


def main():
    with open(TEST_DATA_DIR / "test_majors.json", "w") as f:
        json.dump(MAJORS_JSON, f, indent=2)
    with open(TEST_DATA_DIR / "test_courses.json", "w") as f:
        json.dump(COURSES_JSON, f, indent=2)

    fall_rows = [r for r in STUDENTS if any(f"\t{t}\t" in r for t in ["2196","2186","2176","2166"])]
    spring_rows = [r for r in STUDENTS if any(f"\t{t}\t" in r for t in ["2191","2201","2181","2171"])]

    for fname, rows in [("Fall2019", fall_rows), ("Spring2020", spring_rows), ("Fall2020", STUDENTS)]:
        with open(TEST_DATA_DIR / f"deident_student_enrollment_{fname}.tsv", "w") as f:
            f.write(HEADER + "\n")
            for r in rows:
                f.write(r + "\n")

    print(f"Generated {len(STUDENTS)} rows across 30 students → {TEST_DATA_DIR}")

if __name__ == "__main__":
    main()
