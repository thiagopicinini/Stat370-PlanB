"""
conftest.py — Shared pytest fixtures for the Plan B test suite.

WHAT IS THIS FILE?
    pytest automatically looks for a file called "conftest.py" before
    running any tests. Anything defined here (especially "fixtures")
    becomes available to ALL test files in this folder without needing
    to import it. Think of it as the "setup" file for the whole test suite.

WHAT IS A FIXTURE?
    A fixture is a reusable piece of setup code. For example, instead of
    every single test creating its own MajorRecommender from scratch,
    we create ONE recommender here and share it across all tests.
    Tests request a fixture simply by naming it as a parameter:

        def test_something(self, recommender):   # <-- pytest injects it
            result = recommender.recommend_majors("S001")

WHY SYNTHETIC DATA?
    The real enrollment data (TSV files) contains de-identified student
    records and lives in filtered_data/. It's gitignored and not available
    in CI. So we created 30 fake students (S001-S030) with known courses
    and known expected outcomes. This lets us assert things like "S001
    should get Statistics as a top recommendation" because we designed
    S001's transcript to make that true.
"""

import sys
from pathlib import Path
import pytest

# ── Make our project importable ──────────────────────────────────────
# Python needs to know where to find our code. These two lines tell it:
#   1) The project root (so `from utils.paths import ...` works)
#   2) The dev_scripts folder (so `from major_recommender import ...` works)
PROJECT_ROOT = Path(__file__).parent.parent            # Stat370-PlanB/
sys.path.insert(0, str(PROJECT_ROOT))                  # add project root
sys.path.insert(0, str(PROJECT_ROOT / "dev_scripts"))  # add dev_scripts/

# Where our fake test data lives (the JSON + TSV files we generated)
TEST_DATA_DIR = Path(__file__).parent / "test_data"

# Now we can import our actual project code
from major_recommender import MajorRecommender, authenticate_student  # noqa: E402


@pytest.fixture(scope="session")
def test_data_dir():
    """Returns the path to tests/test_data/ so tests can find fixture files.

    scope="session" means this runs ONCE for the entire test session,
    not once per test. (It's just a path, so no reason to recreate it.)
    """
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def recommender():
    """Creates a MajorRecommender loaded with our FAKE test data.

    This is the same MajorRecommender class the real app uses, but
    instead of loading real student files from filtered_data/, it loads
    our 30 synthetic students (S001-S030) from tests/test_data/.

    scope="session" = shared across ALL tests (faster than recreating).
    """
    majors = str(TEST_DATA_DIR / "test_majors.json")        # 6 fake majors
    courses = str(TEST_DATA_DIR / "test_courses.json")       # ~50 fake courses
    enrollment = sorted(TEST_DATA_DIR.glob("deident_student_enrollment_*.tsv"))
    return MajorRecommender(majors, courses, [str(f) for f in enrollment])


@pytest.fixture()
def client(monkeypatch):
    """Creates a Flask test client for testing the web app endpoints.

    THE PROBLEM:
        planb.py loads data from filtered_data/ at startup, but we don't
        have real data in tests — only our fake data in tests/test_data/.

    THE SOLUTION:
        monkeypatch temporarily swaps the file paths planb.py reads,
        so it loads fake data instead. After the test, paths are restored.

    WHAT IS A TEST CLIENT?
        Flask's test client simulates HTTP requests (GET, POST) without
        starting a real web server. Instead of opening a browser to
        http://localhost:5001, you do:
            resp = client.get("/")           # simulates visiting the homepage
            resp = client.post("/login", data={...})  # simulates form submit
    """
    import importlib
    import utils.paths as paths_mod

    # Swap the real data paths with our test data paths
    monkeypatch.setattr(paths_mod, "MAJORS_JSON", str(TEST_DATA_DIR / "test_majors.json"))
    monkeypatch.setattr(paths_mod, "COURSES_JSON", str(TEST_DATA_DIR / "test_courses.json"))
    monkeypatch.setattr(
        paths_mod,
        "get_filtered_enrollment_files",
        lambda: sorted(TEST_DATA_DIR.glob("deident_student_enrollment_*.tsv")),
    )

    # Force Python to re-import planb so it picks up the swapped paths
    if "planb" in sys.modules:
        del sys.modules["planb"]

    import planb

    planb.app.config["TESTING"] = True           # shows real errors in tests
    planb.app.config["SECRET_KEY"] = "test-secret"

    # yield = "give this to the test, wait for it to finish, then clean up"
    with planb.app.test_client() as c:
        yield c
