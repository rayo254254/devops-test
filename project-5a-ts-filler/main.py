
# MAIN.PY
#************************************************************************************************
# THIS FLOW HANDLES TIMSHEET PREFILLING                                                               *
#                                                                                               *
# params: no params                                                                             *
#                                                                                               *
# creteated by: Marc De Krock                                                                   *
# date: 20250516                                                                                *
#************************************************************************************************

import os
from datetime import datetime, timezone
from webhook_utils_1 import post_data_to_appsheet_whc_v2
import uuid
import functions_framework
from flask import jsonify
from pathlib import Path
import json
import xml.etree.ElementTree as ET
from urllib.parse import quote
import google.auth



# Constants
WHC_app_id = "397f3d50-89dc-46bb-b912-e52499e9b2f1"
WHC_app_access_key = "V2-ggEMV-znIzP-zanfl-m6Sxr-zre0X-55Mkm-oOMQM-qfaZ6"
app_name = "WiseHubCore-346984636"
secret_value="7e9f8b3d5a1c4297fa6b0de4392ed10f8ab7e12466f52a8d5cfe90b6432d901fa57c3de8196a54be1f9a84cb29c07915320c6de5f13e98b94298c83e374bcbb6a"
# ************** HERE IT STARTS ***********************
#**SECRETS**
_, project_id = google.auth.default()
print("Project ID: ", project_id)


@functions_framework.http
def main(request):
    #TESTRUN
    test_run=request.args.get('test')
    if test_run:
        print("Test run, skipping security checks and processing")
        return jsonify({"message": "Test run, no processing done"}), 200
    # SECURITY CHECK
    #load_dotenv()  # Load from .env
    incoming_key = request.headers.get("AppKey")
    print("***Incoming key: ", incoming_key)
    print("***Secret value: ", secret_value)
    if incoming_key != secret_value:
        print("Invalid key")
        return jsonify({"error": "Invalid key"}), 403
    print("Valid key")
    # END SECURITY CHECK

    base_path = Path(os.getcwd())
    print("Working directory:", os.getcwd())

    #base_path = Path(__file__).parent

    # GET THE JSON BODY
    if request.method != "POST":
        return jsonify({"error": "Only POST requests are allowed, you stupid 😁"}), 405
    try:
        data = request.get_json(force=True)
        print("_________________________________________________")
        print("data = ", json.dumps(data, indent=2))
        print("data =", data)
        print("type of data =", type(data))
        print("keys in data:", list(data.keys()))
        print("_________________________________________________")
    except Exception:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
        
    # Normalize JSON (flatten nested dicts/lists)
    try:
        entry_timestamp = datetime.now(timezone.utc).isoformat()
        random_uuid = str(uuid.uuid4())
        print("data 1", json.dumps(data, indent=2))
        print("______________________________________________")
        # SHOW timestamp and UUID, add later to the XML
        print("timestamp: ", entry_timestamp)
        print("random_uuid: ", random_uuid)
        print("______________________________________________")
        #**************************************************
        
        print("**** START COLLECTING DATA FOR VAT CALCULATION AND ADDING THEM TO THE JSON ****")
        # `data` is your original JSON dictionary
        le_group = data["THISUSER LE group"]
        ou_id = data["Ou_id"]
        person_id = data["person_id"]
        project_team_assignment_id = data["project_team_assignment_id"]
        zenphi_dates = data["New dates to include Zenphi"].split(" , ")
        formatted_dates = data["New dates to include"].split(" , ")
        print("LE Group:", le_group)
        print("OU ID:", ou_id)
        print("Person ID:", person_id)
        print("Project Assignment ID:", project_team_assignment_id)
        print("Zenphi Dates:", zenphi_dates)
        print("Formatted Dates:", formatted_dates)
    except Exception as e:
        return jsonify({"error": f"Failed to normalize JSON: {str(e)}"}), 500
    #****************************************************************

    #NOW GET THE FEE TYPES FROM THE APPSHEET TABLE
    #****************************************************************
    #table to address
    # Headers
    #none
    #JSON payload
    #`Add`: Adds a new row to the table.
    #`Delete`: Deletes existing rows from the table.
    #`Edit`: Updates existing rows in the table.
    #`Find`: Reads an existing row of the table.
    selector = f'TOP(Filter(fee_types, And([ou_id]={ou_id} , [fee_type]=Normal)),1)'
    #*********************************************************
    try:
        response= post_data_to_appsheet_whc_v2(table="fee_types", rows=[],action="Find", selector=selector)   
        print("Status Code from find line in: fee_types: ", response.status_code)
        response_data=response.json()
        #print("data", json.dumps(data, indent=2))
        fee_type_id = response_data[0]["fee_type_id"]
        print("FEE TYPE ID=" ,fee_type_id)
    except Exception as e:
        print("Error while fetching fee type:", str(e))
        return jsonify({"error": "Failed to fetch fee type"}), 500
    
    
    
        # Split and clean dates
    # Extract and clean the date list
    date_list = [d.strip() for d in data["New dates to include"].split(",")]

    # Sort the dates (DDMMYYYY format)
    sorted_dates = sorted(date_list, key=lambda d: (d[4:], d[2:4], d[:2]))

    # Build the rows array for AppSheet
    rows = [
        {
         "date": date, 
         "fee_type": fee_type_id,
         "person_id": person_id,
         "project_team_assignment_id": project_team_assignment_id,
         } 
        for date in sorted_dates
        ]
    print("Sorted dates with fee type ID:", json.dumps(rows, indent=2))
    #** NOW ADD ALL RECORDS IN ONE CALL TO APPSHEET  **
    #****************************************************************
    #table to address
    # Headers
    #none
    #JSON payload
    #`Add`: Adds a new row to the table.
    #`Delete`: Deletes existing rows from the table.
    #`Edit`: Updates existing rows in the table.
    #`Find`: Reads an existing row of the table.
    #selector = f'Filter(SB invoices,[Customer]= SB20250003)'
    #*********************************************************
    try:
        #response = post_data_to_appsheet_whc(table, appsheet_data)
        response= post_data_to_appsheet_whc_v2(table="actuals", rows=rows, action="Add", selector=None)   
    #*********************************************************
        print("Status Code from add lines to actuals: ", response.status_code)
        data=response.json()
        print("data", json.dumps(data, indent=2))
        print("Posting data to AppSheet...")
    except Exception as e:
        print("Error while posting data to AppSheet:", str(e))
        return jsonify({"error": "Failed to post data to AppSheet"}), 500
    #*********************************************************
    
    #Send push notification"""
    
    return jsonify({"project_id":project_id,"message": "TS were successfully processed"}), 200