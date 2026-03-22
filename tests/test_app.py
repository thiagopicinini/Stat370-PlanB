"""
test_app.py — Tests for the Flask web application endpoints (planb.py).

WHAT ARE WE TESTING?
    The web app has 4 routes (URL endpoints):
        GET  /                → shows the login page
        POST /login           → handles form submission (student_id + password)
        GET  /recommendations → shows major recommendations (must be logged in)
        GET  /logout          → clears the session and redirects to login

    We test each route to make sure it:
    - Returns the right HTTP status code (200 = OK, 302 = redirect, 405 = not allowed)
    - Shows the right content (error messages, student info, etc.)
    - Handles sessions correctly (login sets session, logout clears it)
    - Doesn't crash on bad input (missing fields, garbage filter values)

HOW DOES THE TEST CLIENT WORK?
    Flask provides a "test client" that simulates a browser. Instead of
    actually opening Chrome and clicking around, we call:
        client.get("/")                                    # visit a page
        client.post("/login", data={"student_id": "S001"}) # submit a form
    The response has .status_code (200, 302, etc.) and .data (the HTML bytes).

WHERE DOES "client" COME FROM?
    It's a fixture defined in conftest.py. pytest sees "client" as a
    parameter name and automatically injects it. The fixture creates a
    test client backed by our fake student data (S001-S030).
"""
import pytest


class TestIndexPage:
    """GET / — the login page that users see first."""

    def test_returns_200(self, client):
        """Visiting the homepage should return HTTP 200 (OK)."""
        resp = client.get("/")
        assert resp.status_code == 200

    def test_contains_login_form(self, client):
        """The page should have a login form (mentions student_id or login)."""
        resp = client.get("/")
        html = resp.data.decode()  # convert bytes to string so we can search
        assert "student_id" in html.lower() or "Student ID" in html or "login" in html.lower()

    def test_no_session_by_default(self, client):
        """Just visiting / shouldn't log you in (no session set)."""
        with client.session_transaction() as sess:
            # session_transaction() lets us peek at Flask's session cookie
            assert "student_id" not in sess


class TestLogin:
    """POST /login — authentication and session creation."""

    def test_valid_login_redirects(self, client):
        """Correct credentials → redirect (302) to /recommendations."""
        resp = client.post("/login", data={"student_id": "S001", "password": "1234"})
        # 302 = "Found" redirect, 303 = "See Other" redirect — both are correct
        assert resp.status_code in (302, 303)
        assert "/recommendations" in resp.headers.get("Location", "")

    def test_valid_login_sets_session(self, client):
        """After logging in, the session should contain the student_id."""
        client.post("/login", data={"student_id": "S001", "password": "1234"})
        with client.session_transaction() as sess:
            assert sess.get("student_id") == "S001"

    def test_wrong_password_shows_error(self, client):
        """Wrong password → stay on login page (200) with an error message."""
        resp = client.post("/login", data={"student_id": "S001", "password": "wrong"})
        assert resp.status_code == 200  # stays on login page, doesn't redirect
        assert b"Invalid" in resp.data or b"invalid" in resp.data

    def test_empty_fields_shows_error(self, client):
        """Both fields empty → error message telling user to fill them in."""
        resp = client.post("/login", data={"student_id": "", "password": ""})
        assert resp.status_code == 200
        assert b"Please enter" in resp.data or b"error" in resp.data.lower()

    def test_missing_student_id_field(self, client):
        """Form submitted without a student_id field at all."""
        resp = client.post("/login", data={"password": "1234"})
        assert resp.status_code == 200  # shows login page with error

    def test_missing_password_field(self, client):
        """Form submitted without a password field at all."""
        resp = client.post("/login", data={"student_id": "S001"})
        assert resp.status_code == 200

    def test_nonexistent_student_correct_pw(self, client):
        """Password is right but the student doesn't exist in our data.
        The app authenticates first (password OK), then looks up the student
        and shows 'not found' when the ID isn't in the enrollment data."""
        resp = client.post("/login", data={"student_id": "DOESNOTEXIST", "password": "1234"})
        assert resp.status_code == 200
        assert b"not found" in resp.data.lower() or b"error" in resp.data.lower()

    def test_login_strips_whitespace(self, client):
        """'  S001  ' with spaces should be trimmed to 'S001' and work."""
        resp = client.post("/login", data={"student_id": "  S001  ", "password": "1234"})
        assert resp.status_code in (302, 303)  # successful redirect


class TestRecommendations:
    """GET /recommendations — requires an active login session."""

    def _login(self, client, sid="S001"):
        """Helper: log in as a given student so we can test /recommendations."""
        client.post("/login", data={"student_id": sid, "password": "1234"})

    def test_redirects_when_not_logged_in(self, client):
        """If you're not logged in, /recommendations should kick you back to /."""
        resp = client.get("/recommendations")
        assert resp.status_code in (302, 303)
        assert "/" in resp.headers.get("Location", "")

    def test_returns_200_when_logged_in(self, client):
        """Logged-in user should see the recommendations page (200 OK)."""
        self._login(client)
        resp = client.get("/recommendations")
        assert resp.status_code == 200

    def test_contains_student_info(self, client):
        """The page should mention the student's ID or name somewhere."""
        self._login(client, "S001")
        resp = client.get("/recommendations")
        html = resp.data.decode()
        assert "S001" in html or "Alice" in html

    def test_contains_major_recommendations(self, client):
        """S001 is a CS major who took lots of Stats courses, so
        'Statistics' should appear somewhere in the recommendations page."""
        self._login(client, "S001")
        resp = client.get("/recommendations")
        html = resp.data.decode()
        assert "Statistics" in html or "credits" in html.lower()

    # ── Filter parameter tests ───────────────────────────────────────
    # The recommendations page accepts URL query parameters to filter results:
    #   ?four_year=yes        → only show majors completable in 4 years
    #   ?outside_dept=yes     → exclude majors in the same department
    #   ?outside_school=yes   → exclude majors in the same school/college
    # These tests verify the page doesn't crash with various filter combos.

    def test_filter_four_year_yes(self, client):
        self._login(client, "S001")
        resp = client.get("/recommendations?four_year=yes")
        assert resp.status_code == 200

    def test_filter_four_year_no(self, client):
        self._login(client, "S001")
        resp = client.get("/recommendations?four_year=no")
        assert resp.status_code == 200

    def test_filter_outside_dept_yes(self, client):
        self._login(client, "S001")
        resp = client.get("/recommendations?outside_dept=yes")
        assert resp.status_code == 200

    def test_filter_outside_school_yes(self, client):
        self._login(client, "S001")
        resp = client.get("/recommendations?outside_school=yes")
        assert resp.status_code == 200

    def test_multiple_filters(self, client):
        """All three filters at once — should not crash."""
        self._login(client, "S001")
        resp = client.get("/recommendations?four_year=yes&outside_dept=yes&outside_school=no")
        assert resp.status_code == 200

    def test_invalid_filter_value_does_not_crash(self, client):
        """Garbage filter values like 'garbage' and '42' — app should
        ignore them gracefully and still return 200."""
        self._login(client, "S001")
        resp = client.get("/recommendations?four_year=garbage&outside_dept=42")
        assert resp.status_code == 200


class TestLogout:
    """GET /logout — clears the session and redirects to login."""

    def test_logout_redirects_to_index(self, client):
        """After logout, user should be redirected back to /."""
        client.post("/login", data={"student_id": "S001", "password": "1234"})
        resp = client.get("/logout")
        assert resp.status_code in (302, 303)

    def test_logout_clears_session(self, client):
        """After logout, the session should no longer contain student_id."""
        client.post("/login", data={"student_id": "S001", "password": "1234"})
        client.get("/logout")
        with client.session_transaction() as sess:
            assert "student_id" not in sess

    def test_recommendations_after_logout_redirects(self, client):
        """If you log out and then try to visit /recommendations,
        you should be redirected back to the login page."""
        client.post("/login", data={"student_id": "S001", "password": "1234"})
        client.get("/logout")
        resp = client.get("/recommendations")
        assert resp.status_code in (302, 303)


class TestSessionManagement:
    """Cross-cutting tests about how sessions behave."""

    def test_login_then_switch_student(self, client):
        """Logging in as a second student should overwrite the first session."""
        client.post("/login", data={"student_id": "S001", "password": "1234"})
        client.post("/login", data={"student_id": "S002", "password": "1234"})
        with client.session_transaction() as sess:
            assert sess["student_id"] == "S002"  # second login wins

    def test_get_login_not_allowed(self, client):
        """GET /login should return 405 (Method Not Allowed).
        The /login route only accepts POST (form submissions),
        not GET (typing the URL in the browser)."""
        resp = client.get("/login")
        assert resp.status_code == 405
