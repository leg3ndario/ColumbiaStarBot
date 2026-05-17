import csv
import requests
import os
import time
import re

# Configuration
API_KEY = os.getenv('DEALMACHINE_API_KEY')
CSV_FILE = 'data/leads_ghl_export.csv' 
BASE_URL = "https://api.dealmachine.com/public/v1/leads"
LIST_ID = "1254885" 

def clean_address(addr):
    addr = re.sub(r'\(.*?\)', '', addr)
    addr = re.sub(r'\bUNIT\b', '#', addr, flags=re.IGNORECASE)
    return addr.strip().strip(',')

def get_lead_id_by_address(address, headers):
    """Searches for an existing lead ID by street address."""
    search_url = f"{BASE_URL}/"
    # Try searching the specific street address
    params = {"search": address, "per_page": 1}
    try:
        res = requests.get(search_url, params=params, headers=headers)
        res_data = res.json()
        data = res_data.get('data', [])
        if isinstance(data, list) and len(data) > 0:
            return data[0].get('id')
    except:
        return None
    return None

def upload_leads():
    if not API_KEY:
        print("❌ API Key missing")
        return

    # Base headers for JSON calls
    json_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Headers for Form Data calls (Let requests handle Content-Type for boundaries)
    form_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": "application/json"
    }

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            raw_addr = row.get('Property Address', '').strip()
            if not raw_addr or not raw_addr[0].isdigit() or len(raw_addr) > 120:
                continue

            addr = clean_address(raw_addr)
            city = row.get('Property City', 'Columbia').strip()
            zip_code = row.get('Property Zip', '').strip()
            
            # Initial Creation Payload (JSON)
            payload = {
                "address": addr,
                "city": city,
                "state": "SC",
                "zip": zip_code,
                "skip_trace": True,
                "lists": [int(LIST_ID)]
            }

            try:
                # 1. ATTEMPT TO CREATE
                response = requests.post(f"{BASE_URL}/", json=payload, headers=json_headers)
                res_json = response.json()
                
                # Check for existing ID or newly created ID
                lead_data = res_json.get('data', {})
                if isinstance(lead_data, list) and len(lead_data) > 0:
                    lead_data = lead_data[0]
                
                lead_id = lead_data.get('id') if isinstance(lead_data, dict) else None
                error_info = res_json.get('error', {}) if isinstance(res_json, dict) else {}
                error_msg = str(error_info.get('message', '')) if isinstance(error_info, dict) else str(error_info)

                # 2. EVALUATE: IF SUCCESSFUL ADD
                if response.status_code in [200, 201] and lead_id:
                    # Note: Sometimes 200 Success still doesn't add to list if lead exists
                    # So we fall through to the sync logic to be absolutely sure
                    pass 

                # 3. IF ALREADY EXISTS OR WE HAVE AN ID, FORCE TO LIST
                # Get the ID if we don't have it yet
                target_id = lead_id if lead_id else get_lead_id_by_address(addr, json_headers)

                if target_id:
                    # Endpoint: /public/v1/leads/:lead_id/add-to-list
                    add_url = f"{BASE_URL}/{target_id}/add-to-list"
                    
                    # MATCHING DOCUMENTATION EXACTLY:
                    # Key is 'list_ids' (plural) and value is the ID string
                    form_payload = {"list_ids": str(LIST_ID)}
                    
                    # POST with data= sends as multipart/form-data
                    update_res = requests.post(add_url, data=form_payload, headers=form_headers)
                    
                    if update_res.status_code == 200:
                        print(f"🔄 Synced: {addr} -> Richland_Intel")
                    else:
                        print(f"✅ Exists: {addr} | List Update Status: {update_res.status_code}")
                else:
                    if "not found" in error_msg.lower():
                        print(f"❌ Failed: {addr} (Property not found)")
                    else:
                        print(f"➖ Skipped: {addr} (ID not found)")
            
            except Exception as e:
                print(f"⚠️ System Error: {addr} | {str(e)}")

            time.sleep(0.5)

if __name__ == "__main__":
    upload_leads()
