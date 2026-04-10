import pytest
from app.web.app import create_app

@pytest.fixture
def app():
    return create_app({'TESTING': True})

@pytest.fixture
def client(app):
    return app.test_client()

def test_health_live(client):
    resp=client.get('/health/live'); assert resp.status_code==200; data=resp.get_json(); assert data['status']=='ok'

def test_api_test(client):
    resp=client.get('/api/test'); assert resp.status_code==200; data=resp.get_json(); assert data['success'] is True

def test_engine_status(client):
    resp=client.get('/api/engine-status'); assert resp.status_code==200; assert 'engines' in resp.get_json()

def test_stats_endpoint(client):
    resp=client.get('/api/stats'); assert resp.status_code==200

def test_supported_endpoint(client):
    resp=client.get('/api/supported?sport=football'); assert resp.status_code==200; data=resp.get_json(); assert data['success'] is True; assert 'supported_competitions' in data

def test_matches_endpoint(client, monkeypatch):
    from app.web import app as webapp
    monkeypatch.setattr(webapp, 'get_sofascore_client', lambda: type('C', (), {'get_scheduled_events_for_date': lambda self, sport, date: [{'id': 1, 'tournament': {'slug': 'epl'}, 'homeTeam': {'name': 'Arsenal', 'id': 10}, 'awayTeam': {'name': 'Chelsea', 'id': 11}, 'startTimestamp': 123, 'status': {'type': 'notstarted'}}]})())
    test_client=create_app({'TESTING': True}).test_client()
    resp=test_client.get('/api/matches?sport=football&date=2026-04-08'); assert resp.status_code==200; data=resp.get_json(); assert data['count'] == 1

def test_accuracy_report_endpoint(client):
    resp=client.get('/api/accuracy-report'); assert resp.status_code==200; data=resp.get_json(); assert data['success'] is True; assert 'report' in data

def test_request_id_header_present(client):
    resp=client.get('/api/test'); assert 'X-Request-ID' in resp.headers
