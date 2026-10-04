import httpx
import json
import time

def run():
    base_url = 'http://localhost:8000/api/v1'
    print("--- 1. Claimant Login ---")
    r = httpx.post(f'{base_url}/auth/login', json={'email': 'claimant@example.com', 'password': 'Password123!'})
    c_token = r.json().get('token')
    c_client = httpx.Client(headers={'Authorization': f'Bearer {c_token}'})
    
    print("--- 2. Submitting Claim ---")
    files = {
        'evidence': ('genuine_car.jpg', open('web/public/samples/genuine_car.jpg', 'rb'), 'image/jpeg'),
        'document': ('clean_invoice.pdf', open('web/public/samples/clean_invoice.pdf', 'rb'), 'application/pdf'),
    }
    data = {
        'policy_id': 'POL-MOT-1001',
        'claim_type': 'motor',
        'peril': 'collision',
        'incident_date': '2026-10-04',
        'incident_time': '12:00',
        'location': json.dumps({'lat': 12.9716, 'lng': 77.5946, 'text': ''}),
        'claimed_amount': '15000',
        'damaged_items': '',
        'description_text': 'Live check claim',
        'consent': 'true'
    }
    r = c_client.post(f'{base_url}/claims', data=data, files=files)
    if r.status_code != 202:
        print(f"Failed to submit: {r.status_code} {r.text}")
        return
    
    claim_id = r.json()['id']
    print(f'Claim submitted: {claim_id}')
    
    print("--- 3. Polling Status ---")
    start = time.time()
    while time.time() - start < 120:
        st = c_client.get(f'{base_url}/claims/{claim_id}/status').json()
        print(f"Status: {st.get('status')} - Jobs: {len(st.get('timeline', []))}")
        if st.get('status') not in ('submitted', 'analysing', 'resubmitted'):
            break
        time.sleep(2)
    
    print("--- 4. Investigator Login & Queue Check ---")
    r = httpx.post(f'{base_url}/auth/login', json={'email': 'investigator@lucen.ai', 'password': 'Password123!'})
    i_client = httpx.Client(headers={'Authorization': f'Bearer {r.json().get("token")}'})
    
    q1 = i_client.get(f'{base_url}/queue?sort=newest&limit=50').json()
    items1 = q1.get('items', [])
    found_in_page_1 = next((x for x in items1 if x.get('claim_id') == claim_id), None)
    print(f"Found in newest page 1? {found_in_page_1 is not None}")
    if found_in_page_1:
        print(f"  Status: {found_in_page_1.get('status')}, Band: {found_in_page_1.get('band')}, Result: {found_in_page_1.get('result_id')}")
        
    q2 = i_client.get(f'{base_url}/queue?q={claim_id}').json()
    items2 = q2.get('items', [])
    found_in_search = next((x for x in items2 if x.get('claim_id') == claim_id), None)
    print(f"Found via search? {found_in_search is not None}")
    if found_in_search:
        print(f"  Status: {found_in_search.get('status')}, Band: {found_in_search.get('band')}, Result: {found_in_search.get('result_id')}")
    
    print("\n--- SQL Details ---")
    print("The queue SQL runs: SELECT c.*, r.overall_band, r.overall_risk, r.id as result_id FROM claims c LEFT JOIN results r ON c.result_id = r.id WHERE (c.data_source IS NULL OR c.data_source != 'synthetic_history')")

if __name__ == '__main__':
    run()
