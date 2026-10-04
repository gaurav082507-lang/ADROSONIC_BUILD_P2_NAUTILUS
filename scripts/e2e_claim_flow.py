import httpx
import json
import time

base_url = 'http://localhost:8000/api/v1'
r = httpx.post(f'{base_url}/auth/login', json={'email': 'claimant@example.com', 'password': 'Password123!'})
c_token = r.json().get('token')
c_client = httpx.Client(headers={'Authorization': f'Bearer {c_token}'})

files = {
    'evidence': ('ai_car.jpg', open('web/public/samples/ai_car.jpg', 'rb'), 'image/jpeg'),
    'document': ('tampered_invoice.pdf', open('web/public/samples/tampered_invoice.pdf', 'rb'), 'application/pdf'),
    'id_photo': ('id_card.png', open('web/public/samples/id_card.png', 'rb'), 'image/png'),
    'selfie': ('selfie.jpg', open('web/public/samples/selfie.jpg', 'rb'), 'image/jpeg'),
}
data = {
    'policy_id': 'POL-MOT-1001',
    'claim_type': 'motor',
    'peril': 'accident',
    'incident_date': '2026-10-01',
    'incident_time': '12:00',
    'location': json.dumps({'lat': 12.9716, 'lng': 77.5946, 'text': 'Bangalore'}),
    'claimed_amount': '50000',
    'damaged_items': 'bumper, fender',
    'description_text': 'I had an accident',
    'description_lang': 'en',
    'consent': 'true',
    'evidence_slot': 'damage',
    'evidence_capture_source': 'upload'
}
r = c_client.post(f'{base_url}/claims', data=data, files=files)
claim_id = r.json()['id']
print(f'Claim submitted: {claim_id}')

while True:
    st = c_client.get(f'{base_url}/claims/{claim_id}/status').json()
    if st['status'] not in ('submitted', 'analysing', 'resubmitted'): break
    time.sleep(1)
print(f'Claim status is now: {st["status"]}')

i_client = httpx.Client(headers={'Authorization': f'Bearer ' + httpx.post(f'{base_url}/auth/login', json={'email': 'investigator@lucen.ai', 'password': 'Password123!'}).json().get('token')})

q_res = i_client.get(f'{base_url}/queue').json()
items = q_res.get('items', [])
total = q_res.get('total', 0)

found_in_page_1 = any(x.get('claim_id') == claim_id for x in items)
print(f'Queue page 1 returned {len(items)} items out of {total} total.')
print(f'Claim {claim_id} found in page 1:', found_in_page_1)

q_search = i_client.get(f'{base_url}/queue?q={claim_id}').json().get('items', [])
print(f'Claim found via search (?q=):', len(q_search) > 0)

if q_search:
    print(f"Claim is present in DB, but pushed off page 1 because default sort is by risk descending and there are {total} synthetic/seed claims clogging the queue.")
    print("ROOT CAUSE 1: synthetic_history claims are returned in GET /queue.")
    print("ROOT CAUSE 2: default sort is by risk, so new claims (which might be still 'analysing' with no score, or just lower score) are pushed off page 1.")
