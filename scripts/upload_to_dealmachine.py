import csv
import requests
import os
import time
import re

# Configuration
API_KEY = os.getenv('DEALMACHINE_API_KEY')
CSV_FILE = 'data/leads_ghl_export.csv' 
URL = "https://api.dealmachine.com/public/v1/leads/"
LIST_ID = 1254885 

def is_valid_address(addr):
    """
    Returns True only if the string looks like a real street address.
    """
    if not addr or len(addr) < 5:
        return False
    
    # 1. Ignore if it's a legal block (starts with common legal phrases)
    junk_phrases = ['ANY HEIRS', 'SUMMONS', 'NOTICE', 'ESTATE OF', 'ORDER', 'THE PERSONAL', 'COMMONWEALTH']
    if any(addr.upper().startswith(phrase) for phrase in junk_phrases):
        return False

    # 2. Ignore known non-residential building/attorney debris
    if any(x in addr.upper() for x in ['PO BOX', 'POST OFFICE', 'LAW FIRM', 'COURTROOM', 'SUITE']):
        return False

    # 3. Logic Check: Real addresses in Richland SC usually start with a digit
    # This catches things like "Any heirs-at-law..." that passed rule #1
    if not addr[0].isdigit():
        return False

    return True

def clean_address(addr):
    """Cleans parentheses and extra spaces from verified addresses."""
    # Remove anything in parentheses like (29204)
    addr = re.sub(r'\(.*?\)', '', addr)
    # Remove extra commas and whitespace
    return addr.strip().strip(',')

def upload_leads():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return

    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        uploaded_count = 0
        skipped_count = 0
        
        for row in reader:
            raw_addr = row.get('Property Address', '').strip()
            
            # Step 1: Validate
            if not is_valid_address(raw_addr):
                skipped_count += 1
                continue

            # Step 2: Clean
            addr = clean_address(raw_addr)
            city = row.get('Property City', 'Columbia').strip()
            state = row.get('Property State', 'SC').strip()
            zip_code = row.get('Property Zip', '').strip()
            
            payload = {
                "address": addr,
                "city": city,
                "state": state,
                "zip": zip_code,
                "skip_trace": True,
                "list_id": LIST_ID
            }
            
            headers = {
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(URL, json=payload, headers=headers)
                res_data = response.json()
                
                error_msg = res_data.get('error', {}).get('message', '') if isinstance(res_data.get('error'), dict) else ''
                
                if response.status_code in [200, 201]:
                    print(f"✅ Added: {addr}")
                    uploaded_count += 1
                elif "already added" in error_msg:
                    print(f"➖ Skipped: {addr} (Already in DM)")
                    skipped_count += 1
                else:
                    print(f"❌ Failed: {addr} | {error_msg}")
            
            except Exception as e:
                print(f"⚠️ Error processing {addr}: {str(e)}")

            time.sleep(0.4) # Slightly faster but safe

    print(f"\n--- SYNC COMPLETE ---")
    print(f"Total Uploaded: {uploaded_count}")
    print(f"Total Filtered/Already There: {skipped_count}")

if __name__ == "__main__":
    upload_leads()
