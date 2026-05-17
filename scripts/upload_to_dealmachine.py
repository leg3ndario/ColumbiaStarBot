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
    search_url = f"{BASE_URL}/"
    params = {"search": address, "per_page": 1}
    try:
        res = requests.get(search_url, params=params, headers=headers)
        data = res.json().get('data', [])
        if isinstance(data, list) and len(data) > 0:
            return data[0].get('id')
    except:
        return None
    return None

def upload_leads():
    if not API_KEY:
        print("❌ API Key missing")
        return

    # Standard JSON headers
    json_headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Strictly for the form-data call - NO Content-Type header
    # Let the requests library generate the multipart boundary automatically
    auth_header = {
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
                
                # Check for existing ID
                lead_data = res_json.get('data', {})
                if isinstance(lead_data, list) and len(lead_data) > 0:
                    lead_data = lead_data[0]
                
                lead_id = lead_data.get('id') if isinstance(lead_data, dict) else None
                
                # 2. FORCE SYNC REGARDLESS OF POST OUTCOME
                target_id = lead_id if lead_id else get_lead_id_by_address(addr, json_headers)

                if target_id:
                    add_url = f"{BASE_URL}/{target_id}/add-to-list"
                    
                    # QUIRK FIX: We wrap the ID in quotes inside the string to match the 
                    # --form 'list_ids="817332"' documentation exactly.
                    # We also use a list of tuples for files/data to ensure multipart format.
                    form_data = [('list_ids', f'"{LIST_ID}"')]
                    
                    # POST using files= or data= without a Content-Type header 
                    # forces the 'multipart/form-data' boundary DM wants.
                    update_res = requests.post(add_url, files=form_data, headers=auth_header)
                    
                    if update_res.status_code == 200:
                        print(f"🔄 Forced Sync: {addr}")
                    else:
                        print(f"✅ Exists: {addr} | Manual check needed.")
                else:
                    print(f"❌ Not Found: {addr}")
            
            except Exception as e:
                print(f"⚠️ Error: {addr} | {str(e)}")

            time.sleep(0.5)

if __name__ == "__main__":
    upload_leads()
