"""
test_auth.py — Tests for the authenticate_student() function.

WHAT ARE WE TESTING?
    In major_recommender.py there's a simple function:

        def authenticate_student(student_id, password):
            return password == "1234"

    It's a proof-of-concept (POC) — every student uses the same password.
    These tests verify it behaves correctly for all kinds of inputs:
    right password, wrong password, empty strings, None values, etc.

HOW DOES PYTEST WORK?
    - Any function starting with "test_" is automatically discovered and run.
    - "assert" checks if something is True. If it's False, the test FAILS.
    - Example: assert 1 + 1 == 2   → passes
               assert 1 + 1 == 3   → FAILS, pytest reports the error
"""
import sys
from pathlib import Path

# Make dev_scripts/ importable so we can use authenticate_student
sys.path.insert(0, str(Path(__file__).parent.parent / "dev_scripts"))
from major_recommender import authenticate_student


class TestAuthenticateStudent:
    """All tests for authenticate_student(student_id, password).

    We group related tests in a class for organization. pytest discovers
    them automatically — you don't need to call them yourself.
    """

    # ── Correct password tests ───────────────────────────────────────
    # These should ALL return True because the password is "1234"

    def test_correct_password_valid_id(self):
        """Normal case: valid student ID + correct password."""
        assert authenticate_student("S001", "1234") is True

    def test_correct_password_numeric_id(self):
        """Student ID is purely numeric — should still work."""
        assert authenticate_student("12345", "1234") is True

    def test_correct_password_long_id(self):
        """Very long student ID — auth doesn't care about ID format."""
        assert authenticate_student("STUDENT_00000001", "1234") is True

    # ── Incorrect password tests ─────────────────────────────────────
    # These should ALL return False

    def test_wrong_password(self):
        """Completely wrong password."""
        assert authenticate_student("S001", "wrong") is False

    def test_empty_password(self):
        """Empty string is not '1234'."""
        assert authenticate_student("S001", "") is False

    def test_password_with_spaces(self):
        """' 1234 ' (with spaces) is NOT the same as '1234'."""
        assert authenticate_student("S001", " 1234 ") is False

    def test_password_similar(self):
        """'12345' has an extra digit — should fail."""
        assert authenticate_student("S001", "12345") is False

    def test_password_partial(self):
        """'123' is missing the last digit."""
        assert authenticate_student("S001", "123") is False

    def test_password_none_type(self):
        """Passing None instead of a string shouldn't crash.
        None == '1234' is False in Python, so this returns False."""
        assert authenticate_student("S001", None) is False

    # ── Various student ID edge cases ────────────────────────────────
    # The function only checks the password, not the ID, so even weird
    # IDs should work as long as the password is correct.

    def test_empty_student_id_correct_pw(self):
        """Empty ID + correct password → True (auth only checks password)."""
        assert authenticate_student("", "1234") is True

    def test_none_student_id_correct_pw(self):
        """None ID + correct password → True."""
        assert authenticate_student(None, "1234") is True

    def test_numeric_student_id(self):
        """Numeric-looking string ID."""
        assert authenticate_student("999", "1234") is True

    def test_special_chars_in_id(self):
        """Special characters in ID — auth doesn't validate IDs."""
        assert authenticate_student("!@#$%", "1234") is True

    # ── Type edge cases ──────────────────────────────────────────────

    def test_integer_password(self):
        """If someone accidentally passes the integer 1234 instead of
        the string '1234', it should return False because:
            1234 == '1234'  →  False in Python (different types)
        """
        assert authenticate_student("S001", 1234) is False

    def test_both_empty(self):
        """Both fields empty — password '' != '1234' → False."""
        assert authenticate_student("", "") is False
