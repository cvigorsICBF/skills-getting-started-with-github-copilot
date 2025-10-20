"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities data before each test"""
    # Store original activities
    original_activities = activities.copy()
    
    # Reset to known state for testing
    activities.clear()
    activities.update({
        "Chess Club": {
            "description": "Learn strategies and compete in chess tournaments",
            "schedule": "Fridays, 3:30 PM - 5:00 PM",
            "max_participants": 12,
            "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
        },
        "Programming Class": {
            "description": "Learn programming fundamentals and build software projects",
            "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
            "max_participants": 20,
            "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
        }
    })
    
    yield
    
    # Restore original activities after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static_index(self, client):
        """Test that root endpoint redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Tests for the activities endpoint"""
    
    def test_get_activities_success(self, client, reset_activities):
        """Test successful retrieval of activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert "Chess Club" in data
        assert "Programming Class" in data
        
        # Check structure of activities
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that all activities are returned"""
        response = client.get("/activities")
        data = response.json()
        
        assert len(data) == 2
        assert data["Chess Club"]["max_participants"] == 12
        assert data["Programming Class"]["max_participants"] == 20


class TestSignupEndpoint:
    """Tests for the signup endpoint"""
    
    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Signed up test@mergington.edu for Chess Club"
        
        # Verify participant was added
        assert "test@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_signup_duplicate_participant(self, client, reset_activities):
        """Test signup when participant is already registered"""
        # Try to sign up someone who's already registered
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"
    
    def test_signup_with_spaces_in_activity_name(self, client, reset_activities):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Programming%20Class/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Signed up newstudent@mergington.edu for Programming Class"
    
    def test_signup_multiple_students_same_activity(self, client, reset_activities):
        """Test multiple students can sign up for the same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Chess Club/signup?email={email}")
            assert response.status_code == 200
        
        # Check all students are registered
        chess_participants = activities["Chess Club"]["participants"]
        for email in emails:
            assert email in chess_participants


class TestUnregisterEndpoint:
    """Tests for the unregister/delete participant endpoint"""
    
    def test_unregister_success(self, client, reset_activities):
        """Test successful participant removal"""
        # Verify participant exists first
        assert "michael@mergington.edu" in activities["Chess Club"]["participants"]
        
        response = client.delete("/activities/Chess Club/participants/michael@mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Unregistered michael@mergington.edu from Chess Club"
        
        # Verify participant was removed
        assert "michael@mergington.edu" not in activities["Chess Club"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregister from non-existent activity"""
        response = client.delete("/activities/Nonexistent Activity/participants/test@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"
    
    def test_unregister_nonexistent_participant(self, client, reset_activities):
        """Test unregister participant who isn't registered"""
        response = client.delete("/activities/Chess Club/participants/notregistered@mergington.edu")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Participant not found in this activity"
    
    def test_unregister_with_url_encoding(self, client, reset_activities):
        """Test unregister with URL-encoded parameters"""
        response = client.delete("/activities/Programming%20Class/participants/emma%40mergington.edu")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Unregistered emma@mergington.edu from Programming Class"


class TestIntegrationScenarios:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client, reset_activities):
        """Test complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Chess Club"
        
        # Step 1: Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        assert email in activities[activity]["participants"]
        
        # Step 2: Verify in activities list
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Step 3: Unregister
        response = client.delete(f"/activities/{activity}/participants/{email}")
        assert response.status_code == 200
        assert email not in activities[activity]["participants"]
        
        # Step 4: Verify removal in activities list
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert email not in data[activity]["participants"]
    
    def test_activity_capacity_tracking(self, client, reset_activities):
        """Test that activity capacity is properly tracked"""
        # Get initial state
        response = client.get("/activities")
        initial_data = response.json()
        initial_count = len(initial_data["Chess Club"]["participants"])
        max_participants = initial_data["Chess Club"]["max_participants"]
        
        # Sign up a new student
        client.post("/activities/Chess Club/signup?email=newstudent@mergington.edu")
        
        # Check updated state
        response = client.get("/activities")
        updated_data = response.json()
        new_count = len(updated_data["Chess Club"]["participants"])
        
        assert new_count == initial_count + 1
        assert new_count <= max_participants
    
    def test_multiple_activities_independence(self, client, reset_activities):
        """Test that operations on one activity don't affect others"""
        email = "independent@mergington.edu"
        
        # Sign up for Chess Club
        client.post(f"/activities/Chess Club/signup?email={email}")
        
        # Check Programming Class is unaffected
        response = client.get("/activities")
        data = response.json()
        
        assert email in data["Chess Club"]["participants"]
        assert email not in data["Programming Class"]["participants"]
        
        # Original participants still there
        assert "emma@mergington.edu" in data["Programming Class"]["participants"]
        assert "sophia@mergington.edu" in data["Programming Class"]["participants"]


class TestErrorHandling:
    """Tests for error handling scenarios"""
    
    def test_malformed_email_in_signup(self, client, reset_activities):
        """Test signup with malformed email parameter"""
        # FastAPI will still accept it, but we can test the functionality
        response = client.post("/activities/Chess Club/signup?email=not-an-email")
        assert response.status_code == 200  # Our API doesn't validate email format
    
    def test_empty_email_parameter(self, client, reset_activities):
        """Test signup with empty email"""
        response = client.post("/activities/Chess Club/signup?email=")
        assert response.status_code == 200
        
        # Empty string should be added as participant
        assert "" in activities["Chess Club"]["participants"]
    
    def test_missing_email_parameter(self, client, reset_activities):
        """Test signup without email parameter"""
        response = client.post("/activities/Chess Club/signup")
        assert response.status_code == 422  # FastAPI validation error


if __name__ == "__main__":
    pytest.main([__file__])