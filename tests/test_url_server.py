import pytest
from url_server import app
import os

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check_structure(client):
    """Test that health check returns the correct structure"""
    response = client.get('/health')
    data = response.get_json()
    
    # Check basic structure
    assert 'status' in data
    assert 'timestamp' in data
    assert 'checks' in data
    assert 'redis' in data['checks']
    assert 'r2_storage' in data['checks']

def test_index_route(client):
    """Test that index route returns 200"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'YouTube Song Downloader' in response.data
