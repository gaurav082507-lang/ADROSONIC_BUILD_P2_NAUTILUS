import pytest
import httpx
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_end_to_end_claim_flow():
    # 1. Claimant Login
    r = client.post('/api/v1/auth/login', json={'email': 'claimant@example.com', 'password': 'Password123!'})
    assert r.status_code == 200
    c_token = r.json().get('token')
    c_headers = {'Authorization': f'Bearer {c_token}'}

    # 2. Submit Claim
    with open('web/public/samples/ai_car.jpg', 'rb') as ai_car:
        files = {
            'evidence': ('ai_car.jpg', ai_car, 'image/jpeg')
        }
        data = {
            'policy_id': 'POL-MOT-1001',
            'claim_type': 'motor',
            'peril': 'accident',
            'incident_date': '2026-10-01',
            'incident_time': '12:00',
            'location': '{"lat": 12.9716, "lng": 77.5946, "text": "Bangalore"}',
            'claimed_amount': '50000',
            'damaged_items': 'bumper, fender',
            'description_text': 'I had an accident',
            'description_lang': 'en',
            'consent': 'true',
            'evidence_slot': 'damage',
            'evidence_capture_source': 'upload'
        }
        r = client.post('/api/v1/claims', data=data, files=files, headers=c_headers)
        assert r.status_code == 202
        claim_id = r.json()['id']
    
    # We can't easily wait for background job in test client without mocking it, 
    # but we can check if it exists in the database
    st = client.get(f'/api/v1/claims/{claim_id}/status', headers=c_headers).json()
    assert st['status'] in ('submitted', 'analysing', 'under_review', 'resubmitted')
    
    # 3. Investigator Login
    r = client.post('/api/v1/auth/login', json={'email': 'investigator@lucen.ai', 'password': 'Password123!'})
    assert r.status_code == 200
    i_token = r.json().get('token')
    i_headers = {'Authorization': f'Bearer {i_token}'}

    # 4. Check Queue
    q_res = client.get('/api/v1/queue?sort=newest', headers=i_headers).json()
    items = q_res.get('items', [])
    assert any(x.get('claim_id') == claim_id for x in items), "Claim should be visible in queue"
