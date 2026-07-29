import pytest
from app import app, db

@pytest.fixture
def client():
    # Configure the app for testing using an in-memory database
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_login_page_loads(client):
    """Test that the login page successfully renders"""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Login" in response.data
