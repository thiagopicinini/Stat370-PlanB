"""
test_integration.py — Integration tests for the Major Recommender System.

WHAT ARE INTEGRATION TESTS?
    Unlike test_auth.py (which tests ONE function in isolation), these
    tests exercise the FULL pipeline: loading data -> finding a student ->
    calculating course matches -> producing ranked recommendations.

HOW DO THE 30 CONTROL STUDENTS WORK?
    In tests/test_data/generate_test_data.py, we created 30 fake students
    (S001-S030), each with a carefully designed transcript. For example:

        S001: CS major who took 6 Statistics-area courses
              -> Expected result: Statistics (BS) should be recommended

        S010: Only F and D grades
              -> Expected result: zero recommendations (no passed courses)

    Because WE designed the students, we KNOW what the correct output
    should be. If the recommender gives a different answer, the test fails
    and we know something is broken.

WHAT IS THE "recommender" PARAMETER?
    It's a fixture defined in conftest.py -- a MajorRecommender instance
    loaded with our fake test data. pytest automatically injects it
    when a test method includes it as a parameter.
"""

import pytest


# =====================================================================
# Helper functions (used by multiple tests below)
# =====================================================================

def top_major_names(results, n=5):
    """Extract just the major names from the top N recommendations.
    
    Example:
        results = recommender.recommend_majors("S001")
        top_major_names(results)  ->  ["Statistics (BS)", "Mathematics (BS)", ...]
    """
    if not results or not results.get("recommended_majors"):
        return []
    return [m["major_name"] for m in results["recommended_majors"][:n]]


def rec_by_name(results, name):
    """Find a specific major in the recommendations list.
    
    Example:
        math_rec = rec_by_name(results, "Mathematics (BS)")
        if math_rec:
            print(math_rec["completion_percentage"])  # e.g., 100.0
    """
    for m in results.get("recommended_majors", []):
        if m["major_name"] == name:
            return m
    return None


# =====================================================================
# 1. Core recommendation correctness (Students S001-S012)
# =====================================================================

class TestCoreRecommendations:

    def test_s001_cs_major_gets_stats_rec(self, recommender):
        """S001 is a CS major who took MATH 161, MATH 162, STAT 203,
        STAT 303, STAT 304, STAT 305. Statistics should be recommended."""
        r = recommender.recommend_majors("S001")
        names = top_major_names(r)
        assert "Statistics (BS)" in names, f"Expected Statistics in {names}"

    def test_s001_current_major_excluded(self, recommender):
        """S001 is CS, so Computer Science (BS) should be excluded."""
        r = recommender.recommend_majors("S001")
        names = top_major_names(r, n=20)
        assert "Computer Science (BS)" not in names

    def test_s002_stats_major_gets_cs_rec(self, recommender):
        """S002 is Stats, took 7 CS courses. CS should be top rec."""
        r = recommender.recommend_majors("S002")
        names = top_major_names(r)
        assert "Computer Science (BS)" in names, f"Expected CS in {names}"

    def test_s002_current_major_excluded(self, recommender):
        r = recommender.recommend_majors("S002")
        names = top_major_names(r, n=20)
        assert "Statistics (BS)" not in names

    def test_s003_math_major_gets_stats_or_cs(self, recommender):
        """S003 is Math with mixed courses. Stats or CS should appear."""
        r = recommender.recommend_majors("S003")
        names = top_major_names(r)
        assert any(n in names for n in ["Statistics (BS)", "Computer Science (BS)"]), \
            f"Expected Stats or CS in {names}"

    def test_s003_current_major_excluded(self, recommender):
        r = recommender.recommend_majors("S003")
        names = top_major_names(r, n=20)
        assert "Mathematics (BS)" not in names

    def test_s004_psych_only_overlap_is_stat203(self, recommender):
        """S004 is Psych, only STAT 203 overlaps STEM. Low credits."""
        r = recommender.recommend_majors("S004")
        assert r is not None
        if r["recommended_majors"]:
            top = r["recommended_majors"][0]
            assert top["credits_earned"] <= 6

    def test_s004_current_major_excluded(self, recommender):
        r = recommender.recommend_majors("S004")
        names = top_major_names(r, n=20)
        assert "Psychology (BS)" not in names

    def test_s005_accounting_no_stem_recs(self, recommender):
        """S005 only took business courses. No STEM recs."""
        r = recommender.recommend_majors("S005")
        names = top_major_names(r)
        for stem in ["Computer Science (BS)", "Statistics (BS)", "Mathematics (BS)", "Biology (BS)"]:
            assert stem not in names

    def test_s006_bio_major_some_overlap(self, recommender):
        """S006 is Bio. Bio excluded, but MATH/STAT overlap exists."""
        r = recommender.recommend_majors("S006")
        assert r is not None
        names = top_major_names(r)
        assert "Biology (BS)" not in names

    def test_s007_freshman_minimal_recs(self, recommender):
        """S007 is CS freshman with only 2 courses. Minimal recs."""
        r = recommender.recommend_majors("S007")
        assert r is not None
        if r["recommended_majors"]:
            top = r["recommended_majors"][0]
            assert top["courses_matched"] <= 3

    def test_s008_undeclared_gets_recs(self, recommender):
        """S008 is Undeclared with mixed courses. Should see recs."""
        r = recommender.recommend_majors("S008")
        assert r is not None
        assert len(r["recommended_majors"]) >= 1

    def test_s009_current_major_excluded_even_if_perfect(self, recommender):
        """S009 completed ALL Stats reqs. Stats MUST be excluded."""
        r = recommender.recommend_majors("S009")
        names = top_major_names(r, n=20)
        assert "Statistics (BS)" not in names

    def test_s009_math_highly_ranked(self, recommender):
        """S009 has MATH 161, 162, 212, 263. Math should rank well."""
        r = recommender.recommend_majors("S009")
        names = top_major_names(r)
        assert "Mathematics (BS)" in names

    def test_s010_no_passed_courses_empty_recs(self, recommender):
        """S010 has only F and D grades. Zero recs."""
        r = recommender.recommend_majors("S010")
        assert r is not None
        assert len(r["recommended_majors"]) == 0

    def test_s011_accounting_with_cs_courses(self, recommender):
        """S011 is Accounting but took CS courses. CS should appear."""
        r = recommender.recommend_majors("S011")
        names = top_major_names(r)
        assert any(n in names for n in ["Computer Science (BS)", "Mathematics (BS)"])

    def test_s012_bio_with_math_courses(self, recommender):
        """S012 is Bio but took lots of math. Math or Stats should appear."""
        r = recommender.recommend_majors("S012")
        names = top_major_names(r)
        assert any(n in names for n in ["Statistics (BS)", "Mathematics (BS)"])


# =====================================================================
# 2. Multi-semester students (Students S013-S015)
# =====================================================================

class TestMultiSemester:

    def test_s013_four_semesters_aggregated(self, recommender):
        """S013 has courses across 4 semesters. All should be aggregated."""
        info = recommender.get_student_info("S013")
        assert info is not None
        courses = recommender.get_student_courses("S013")
        terms = set(c["term"] for c in courses)
        assert len(terms) >= 3, f"Expected >= 3 distinct terms, got {terms}"

    def test_s013_semesters_enrolled_count(self, recommender):
        info = recommender.get_student_info("S013")
        assert info["semesters_enrolled"] >= 3

    def test_s014_all_stat_courses_aggregated(self, recommender):
        """S014 completed Stats across 4 semesters. Math should be top rec."""
        r = recommender.recommend_majors("S014")
        names = top_major_names(r)
        assert "Mathematics (BS)" in names

    def test_s015_plan_switch_uses_latest(self, recommender):
        """S015 was Undeclared then CS. Current major should be CS."""
        info = recommender.get_student_info("S015")
        assert "Computer Science" in str(info["current_major"])


# =====================================================================
# 3. Edge cases (Students S016-S030)
# =====================================================================

class TestEdgeCases:

    def test_s016_pass_grades_count(self, recommender):
        """S016 has only P grades. They should still count."""
        courses = recommender.get_student_courses("S016")
        codes = [c["course"] for c in courses]
        assert "MATH 161" in codes
        assert "STAT 203" in codes

    def test_s017_failing_grades_excluded(self, recommender):
        """S017: A, F, A, D, C. Only A and C should count."""
        courses = recommender.get_student_courses("S017")
        codes = [c["course"] for c in courses]
        assert "MATH 161" in codes
        assert "COMP 141" in codes
        assert "STAT 203" in codes
        assert "MATH 162" not in codes
        assert "COMP 170" not in codes

    def test_s018_grad_rows_filtered_out(self, recommender):
        """S018 has a GRAD row for STAT 303. Only UGRD rows should load."""
        courses = recommender.get_student_courses("S018")
        codes = [c["course"] for c in courses]
        assert "STAT 303" not in codes
        assert "STAT 203" in codes
        assert "MATH 161" in codes

    def test_s019_retake_counts_once(self, recommender):
        """S019 took MATH 161 twice (F then B+). Should count the pass."""
        courses = recommender.get_student_courses("S019")
        math161 = [c for c in courses if c["course"] == "MATH 161"]
        assert len(math161) >= 1
        assert all(c["grade"] != "F" for c in math161)

    def test_s020_cross_major_overlap(self, recommender):
        """S020 is Psych but took ACCT 201/202. Accounting should appear."""
        r = recommender.recommend_majors("S020")
        names = top_major_names(r)
        assert "Accounting (BBA)" in names

    def test_s026_single_course_match(self, recommender):
        """S026 has only STAT 203. Very low match."""
        r = recommender.recommend_majors("S026")
        assert r is not None
        if r["recommended_majors"]:
            top = r["recommended_majors"][0]
            assert top["courses_matched"] == 1
            assert top["credits_earned"] == 3

    def test_s027_all_math_reqs_done(self, recommender):
        """S027 completed ALL Math(BS) requirements. Math should be top rec."""
        r = recommender.recommend_majors("S027")
        names = top_major_names(r)
        assert "Mathematics (BS)" in names

    def test_s027_high_completion_pct(self, recommender):
        """S027 matched 9/9 Math courses. 100% completion."""
        r = recommender.recommend_majors("S027")
        math_rec = rec_by_name(r, "Mathematics (BS)")
        assert math_rec is not None
        assert math_rec["completion_percentage"] == 100.0

    def test_s028_c_minus_grades_count(self, recommender):
        """S028 has all C- grades. C- is passing."""
        courses = recommender.get_student_courses("S028")
        assert len(courses) == 4
        assert all(c["grade"] == "C-" for c in courses)

    def test_s029_or_course_match(self, recommender):
        """S029 took STAT 335 which satisfies 'STAT 203 or STAT 335'."""
        r = recommender.recommend_majors("S029")
        stat_rec = rec_by_name(r, "Statistics (BS)")
        if stat_rec:
            matched_codes = [c["course"] for c in stat_rec["matched_courses"]]
            assert "STAT 335" in matched_codes

    def test_s030_zero_units_defaults_to_3(self, recommender):
        """S030 has Units_Earned=0. Should default to 3."""
        courses = recommender.get_student_courses("S030")
        for c in courses:
            assert c["credits"] == 3

    def test_nonexistent_student_returns_none(self, recommender):
        """Non-existent student should return None."""
        r = recommender.recommend_majors("DOESNOTEXIST")
        assert r is None


# =====================================================================
# 4. Filter tests (Students S021-S025)
# =====================================================================

class TestFilters:

    def test_s021_early_student_can_complete(self, recommender):
        """S021 has 1 semester. four_year=yes should return recs."""
        r = recommender.recommend_majors("S021", filter_four_year="yes")
        assert r is not None
        assert len(r["recommended_majors"]) >= 1

    def test_s022_late_student_four_year_filter(self, recommender):
        """S022 has 7 semesters. Very little capacity left."""
        r_yes = recommender.recommend_majors("S022", filter_four_year="yes")
        r_no = recommender.recommend_majors("S022", filter_four_year="no")
        assert r_yes is not None and r_no is not None

    def test_four_year_yes_and_no_are_disjoint(self, recommender):
        """yes and no results should not overlap."""
        r_yes = recommender.recommend_majors("S001", filter_four_year="yes")
        r_no = recommender.recommend_majors("S001", filter_four_year="no")
        yes_names = set(top_major_names(r_yes, n=50))
        no_names = set(top_major_names(r_no, n=50))
        assert yes_names.isdisjoint(no_names), f"Overlap: {yes_names & no_names}"

    def test_four_year_none_is_superset(self, recommender):
        """No filter should be a superset of yes and no."""
        r_all = recommender.recommend_majors("S001", top_n=50)
        r_yes = recommender.recommend_majors("S001", top_n=50, filter_four_year="yes")
        r_no = recommender.recommend_majors("S001", top_n=50, filter_four_year="no")
        all_names = set(top_major_names(r_all, n=50))
        yes_names = set(top_major_names(r_yes, n=50))
        no_names = set(top_major_names(r_no, n=50))
        assert yes_names.issubset(all_names)
        assert no_names.issubset(all_names)

    def test_s023_outside_dept_yes_excludes_cs(self, recommender):
        """S023 is CS dept. outside_dept=yes excludes CS dept majors."""
        r = recommender.recommend_majors("S023", filter_outside_dept="yes")
        for m in r.get("recommended_majors", []):
            assert m["department"].lower() != "computer science"

    def test_s023_outside_dept_no_keeps_same_dept(self, recommender):
        """outside_dept=no keeps ONLY same-department majors."""
        r = recommender.recommend_majors("S023", filter_outside_dept="no")
        info = recommender.get_student_info("S023")
        for m in r.get("recommended_majors", []):
            assert m["department"].lower() == info["current_department"].lower()

    def test_s024_outside_school_yes_excludes_quinlan(self, recommender):
        """S024 is Quinlan Business. outside_school=yes excludes Quinlan."""
        r = recommender.recommend_majors("S024", filter_outside_school="yes")
        for m in r.get("recommended_majors", []):
            assert "quinlan" not in m["school"].lower()

    def test_s025_outside_school_no_keeps_arts_sciences(self, recommender):
        """S025 is Arts & Sciences. outside_school=no keeps same school."""
        r = recommender.recommend_majors("S025", filter_outside_school="no")
        for m in r.get("recommended_majors", []):
            assert "arts and sciences" in m["school"].lower()

    def test_combined_filters_narrow_results(self, recommender):
        """More filters = fewer or equal results."""
        r_all = recommender.recommend_majors("S001", top_n=50)
        r_filtered = recommender.recommend_majors(
            "S001", top_n=50, filter_four_year="yes", filter_outside_dept="yes"
        )
        assert len(r_filtered["recommended_majors"]) <= len(r_all["recommended_majors"])


# =====================================================================
# 5. Student info and course retrieval
# =====================================================================

class TestStudentInfo:

    def test_get_student_info_valid(self, recommender):
        info = recommender.get_student_info("S001")
        assert info is not None
        assert info["student_id"] == "S001"
        assert "current_major" in info

    def test_get_student_info_invalid(self, recommender):
        assert recommender.get_student_info("ZZZZ") is None

    def test_student_courses_returns_list(self, recommender):
        courses = recommender.get_student_courses("S001")
        assert isinstance(courses, list)
        assert len(courses) > 0

    def test_student_courses_invalid_id(self, recommender):
        courses = recommender.get_student_courses("ZZZZ")
        assert courses == []

    def test_course_dict_has_required_keys(self, recommender):
        courses = recommender.get_student_courses("S001")
        for c in courses:
            assert "course" in c
            assert "credits" in c
            assert "grade" in c
            assert "term" in c


# =====================================================================
# 6. calculate_major_match unit-level checks
# =====================================================================

class TestCalculateMajorMatch:

    def test_no_overlap(self, recommender):
        fake_courses = [{"course": "ZZZZ 999", "credits": 3, "grade": "A", "term": "2196"}]
        result = recommender.calculate_major_match(fake_courses, "Computer Science (BS)")
        assert result["total_credits"] == 0
        assert result["course_count"] == 0

    def test_full_overlap(self, recommender):
        cs_reqs = ["MATH 161", "MATH 162", "COMP 141", "COMP 170", "COMP 264",
                    "COMP 271", "COMP 272", "COMP 310", "COMP 317", "COMP 363",
                    "COMP 371", "STAT 203"]
        fake_courses = [{"course": c, "credits": 3, "grade": "A", "term": "2196"} for c in cs_reqs]
        result = recommender.calculate_major_match(fake_courses, "Computer Science (BS)")
        assert result["course_count"] == len(cs_reqs)
        assert result["total_credits"] == 3 * len(cs_reqs)

    def test_nonexistent_major(self, recommender):
        fake_courses = [{"course": "MATH 161", "credits": 3, "grade": "A", "term": "2196"}]
        result = recommender.calculate_major_match(fake_courses, "Underwater Basket Weaving (BA)")
        assert result["total_credits"] == 0

    def test_or_requirement_match(self, recommender):
        fake_courses = [{"course": "STAT 335", "credits": 3, "grade": "A", "term": "2196"}]
        result = recommender.calculate_major_match(fake_courses, "Statistics (BS)")
        matched_codes = [c["course"] for c in result["matched_courses"]]
        assert "STAT 335" in matched_codes

    def test_or_requirement_no_double_count(self, recommender):
        fake_courses = [
            {"course": "STAT 203", "credits": 3, "grade": "A", "term": "2196"},
            {"course": "STAT 335", "credits": 3, "grade": "A", "term": "2196"},
        ]
        result = recommender.calculate_major_match(fake_courses, "Statistics (BS)")
        matched_codes = [c["course"] for c in result["matched_courses"]]
        stat_matches = [c for c in matched_codes if c in ("STAT 203", "STAT 335")]
        assert len(stat_matches) == 1


# =====================================================================
# 7. Error handling
# =====================================================================

class TestErrorHandling:

    def test_empty_student_id(self, recommender):
        assert recommender.recommend_majors("") is None

    def test_numeric_student_id(self, recommender):
        r = recommender.recommend_majors("12345")
        assert r is None or isinstance(r, dict)

    def test_recommend_with_top_n_zero(self, recommender):
        r = recommender.recommend_majors("S001", top_n=0)
        assert r is not None
        assert len(r["recommended_majors"]) == 0

    def test_recommend_with_top_n_one(self, recommender):
        r = recommender.recommend_majors("S001", top_n=1)
        assert len(r["recommended_majors"]) <= 1

    def test_recommend_with_large_top_n(self, recommender):
        r = recommender.recommend_majors("S001", top_n=1000)
        assert r is not None
        assert len(r["recommended_majors"]) <= 1000
