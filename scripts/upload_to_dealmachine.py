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
    # Remove (Zip) and handle "Unit" -> "#"
    addr = re.sub(r'\(.*?\)', '', addr)
    addr = re.sub(r'\bUNIT\b', '#', addr, flags=re.IGNORECASE)
    return addr.strip().strip(',')

def upload_leads():
    if not API_KEY:
        print("❌ API Key missing")
        return

    headers = {
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
                # 1. ATTEMPT TO CREATE (POST)
                response = requests.post(f"{BASE_URL}/", json=payload, headers=headers)
                res_json = response.json()
                
                # --- ROBUST DATA EXTRACTION ---
                # Handle cases where API returns a list or a dict
                lead_data = {}
                if isinstance(res_json, list) and len(res_json) > 0:
                    lead_data = res_json[0]
                elif isinstance(res_json, dict):
                    lead_data = res_json.get('data', {})
                    if isinstance(lead_data, list) and len(lead_data) > 0:
                        lead_data = lead_data[0]
                
                error_info = res_json.get('error', {}) if isinstance(res_json, dict) else {}
                error_msg = error_info.get('message', '') if isinstance(error_info, dict) else str(error_info)
                
                lead_id = lead_data.get('id') if isinstance(lead_data, dict) else None

                # 2. EVALUATE OUTCOME
                if response.status_code in [200, 201] and lead_id:
                    print(f"✅ Added: {addr}")
                
                elif ("already added" in error_msg.lower() or lead_id) and lead_id:
                    # 3. IF ALREADY EXISTS, FORCE TO LIST (FORM DATA)
                    # Documentation: /public/v1/leads/:lead_id/add-to-list
                    add_url = f"{BASE_URL}/{lead_id}/add-to-list"
                    form_payload = {"list_ids": LIST_ID}
                    
                    # Note: We use data= (Form Data) here to match DM docs
                    update_res = requests.post(add_url, data=form_payload, headers=headers)
                    
                    if update_res.status_code == 200:
                        print(f"🔄 Synced: {addr} -> Richland_Intel")
                    else:
                        print(f"⚠️ Found {addr}, but List Sync failed.")
                
                else:
                    print(f"❌ Failed: {addr} | {error_msg}")
            
            except Exception as e:
                print(f"⚠️ System Error: {addr} | {str(e)}")

            time.sleep(0.4)

if __name__ == "__main__":
    upload_leads()
