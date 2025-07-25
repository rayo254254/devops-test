# ***********************************************************************************************
# THIS FLOW CREATES A TIMESHEET BASED ON KEYS PROVIDED IN THE URL
#
# params:
#   Action = SISU_TS_NON_SAMSUNG or SISU_TS_SAMSUNG or SISU_TS_CONSULTANT
#   TS_ID = (eg.)202506ARISTA03572
#   Thisuseremail= (eg.)wim@coffeewriter.be
#
# creteated by: Marc De Krock
# date: 20250709
# ***********************************************************************************************

import io
import pymysql
from flask import jsonify  # Needed for HTTP responses in Cloud Functions
from email_utils import send_email
import functions_framework  # Google Cloud Functions framework
from datetime import datetime, date
from decimal import Decimal
import json
import base64
import urllib.parse
import requests

# --- Database Connection Details from Environment Variables ---

# These will be set during Cloud Function deployment
"""DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")  # Default for local testing if not set
DB_PORT = int(os.environ.get("DB_PORT", 3306))
DB_USER = os.environ.get("DB_USER", "default_user")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "default_password")
DB_NAME = os.environ.get("DB_NAME", "default_db")  # This should be TEST_MYSQL_WW1"""

# NEEDS TO BE MOVED TO SECRET MANAGER
DB_HOST = "34.78.96.222"
DB_PORT = 3306
DB_USER = "GCR_WW"
# DB_PASSWORD = ")PJ3B|6NH&eJcF_M"
# DB_PASSWORD = "Ym~N\q$0i.Ee&k=g"
DB_PASSWORD = "9a`Z:)p/5[q{CC<&"
DB_NAME = "ProductionSisu_Sync_V2"

print("flow is starting...")


def transform_row1(row):
    transformed = {}
    for key, value in row.items():
        new_key = key.replace(" ", "_")
        if isinstance(value, (datetime, date)):
            transformed[new_key] = value.isoformat()
        elif isinstance(value, Decimal):
            transformed[new_key] = float(value)
        else:
            transformed[new_key] = value
    return transformed


def transform_row(row):
    transformed = {}
    for key, value in row.items():
        new_key = key.replace(" ", "_")

        if isinstance(value, (datetime, date)):
            transformed[new_key] = value.isoformat()
        elif isinstance(value, Decimal):
            transformed[new_key] = float(value)
        elif isinstance(value, bytes):
            # If you know it's just binary flags (like b'\x01'), convert to int
            transformed[new_key] = int.from_bytes(value, byteorder="little")
            # Alternatively, if it's more complex data, use this instead:
            # transformed[new_key] = base64.b64encode(value).decode('utf-8')
        else:
            transformed[new_key] = value
    return transformed


# --- Database Connection Function (reused) ---
def get_db_connection():
    """
    Establishes and returns a database connection.
    """
    try:
        connection = pymysql.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,  # Returns results as dictionaries
        )
        print("Successfully connected to the database!")
        return connection
    except Exception as e:  # Catch broader Exception for Cloud Functions logging
        print(f"Error connecting to MySQL database: {e}")
        return None


# ********************************************************************
# FUNCTIONS TO GET DATA FROM MYSQL TABLES
# Tables: Project TS List, Project TS Calendar, Exception Time
# *********************************************************************
# --- New function to fetch from 'Project TS List' ---
def fetch_project_ts_list(connection, ts_id):
    """
    Fetches records from 'Project TS List' based on TS_ID.
    """
    if not connection:
        return []

    try:
        with connection.cursor() as cursor:
            # IMPORTANT: Table name 'Project TS List' and column 'TS-ID' have spaces/hyphens,
            # so they MUST be delimited with backticks (`).
            sql = """
            SELECT *
            FROM `Project TS List`
            WHERE `TS-ID` = %s
            """
            cursor.execute(sql, (ts_id,))
            result = cursor.fetchall()
            return result
    except Exception as e:
        print(f"Error fetching data from 'Project TS List': {e}")
        return []


# --- NEW FUNCTION: Fetch Project TS Calendar Data ---
def fetch_project_ts_calendar(connection, ts_id):
    """
    Retrieves data from the 'Project TS Calendar' table filtered by 'Project TS ID'
    and ordered by 'Date'.
    """
    if not connection:
        print("No database connection available.")
        return []

    try:
        with connection.cursor() as cursor:
            # SQL query with backticks for column/table names with spaces
            # and a placeholder (%s) for the TS_ID parameter.
            # Using schema_name.table_name for full qualification.
            sql = """
            SELECT *
            FROM `Project TS Calendar`
            WHERE `Project TS ID` = %s
            ORDER BY `Date`
            """
            cursor.execute(sql, (ts_id,))
            result = cursor.fetchall()
            return result
    except pymysql.Error as e:
        print(f"Error fetching data from Project TS Calendar for TS_ID '{ts_id}': {e}")
        return []


# --- NEW FUNCTION: Fetch Exception Time Data ---
def fetch_exception_time(connection, ts_id):
    """
    Retrieves data from the 'Project TS Calendar' table filtered by 'Project TS ID'
    and ordered by 'Date'.
    """
    if not connection:
        print("No database connection available.")
        return []

    try:
        with connection.cursor() as cursor:
            # SQL query with backticks for column/table names with spaces
            # and a placeholder (%s) for the TS_ID parameter.
            # Using schema_name.table_name for full qualification.
            sql = """
            SELECT *
            FROM `Exception time`
            WHERE `TS ID` = %s
            """
            cursor.execute(sql, (ts_id,))
            result = cursor.fetchall()
            return result
    except pymysql.Error as e:
        print(f"Error fetching data from Exception time for TS_ID '{ts_id}': {e}")
        return []


def fetch_project_exception_time(connection, pr_ex_time_id):
    """
    Retrieves data from the 'Project TS Calendar' table filtered by 'Project TS ID'
    and ordered by 'Date'.
    """
    if not connection:
        print("No database connection available.")
        return []

    try:
        with connection.cursor() as cursor:
            # SQL query with backticks for column/table names with spaces
            # and a placeholder (%s) for the TS_ID parameter.
            # Using schema_name.table_name for full qualification.
            sql = """
            SELECT *
            FROM `Project exception time`
            WHERE `Project exception time ID` = %s
            """
            cursor.execute(sql, (pr_ex_time_id,))
            result = cursor.fetchall()
            return result
    except pymysql.Error as e:
        print(
            f"Error fetching data from Exception time for TS_ID '{pr_ex_time_id}': {e}"
        )
        return []


def fetch_project_exception_times(connection, project_exception_time_ids):
    """
    Fetches all 'Project exception time' records matching any of the given IDs.

    Parameters:
    - connection: Active MySQL connection
    - project_exception_time_ids: list of unique IDs (strings)

    Returns:
    - List of matching project exception time records
    """
    if not connection:
        print("No database connection available.")
        return []

    if not project_exception_time_ids:
        print("No project exception time IDs provided.")
        return []

    try:
        with connection.cursor() as cursor:
            placeholders = ", ".join(["%s"] * len(project_exception_time_ids))
            sql = f"""
            SELECT *
            FROM `Project exception time`
            WHERE `Project exception time ID` IN ({placeholders})
            """
            cursor.execute(sql, project_exception_time_ids)
            return cursor.fetchall()
    except pymysql.Error as e:
        print(f"Error fetching project exception times: {e}")
        return []


def enrich_exception_time_data(exception_time_data, project_exception_time_data):
    # Build a lookup dictionary from project_exception_time_data
    pet_lookup = {
        item["Project exception time ID"]: item for item in project_exception_time_data
    }

    # Create the enriched list
    enriched = []
    for item in exception_time_data:
        project_id = item.get("Project exception time id")
        matching_pet = pet_lookup.get(project_id, {})

        enriched_item = {
            "Exception_time_id": item.get("Exception time id"),
            "TS_ID": item.get("TS ID"),
            "Project_exception_time_id": project_id,
            "Quantity": item.get("Quantity"),
            "Units": matching_pet.get("Units"),  # from related table
            "Description": matching_pet.get(
                "Exception time description"
            ),  # from related table
            "Note": item.get("Note"),
            "Update": item.get("Update"),
            "last_change": item.get("last change"),
            "changed_by": item.get("changed by"),
        }

        enriched.append(enriched_item)

    return enriched


# ************************************************
# --- Google Cloud Function Entry Point ---
# ************************************************
secret_value = (
    "^Yfz1R6BsD#KjmWp9@uCV83+OQtwcEbZPiFHaUL!M5xAqJhNX*GTo72v$lnRydk0gzseY#bKP4Q^mwdnMT"
)


@functions_framework.http
def main(request):
    print("Function triggered.")
    # *******************************
    # 1. Parse URL query parameters
    # *******************************
    action = request.args.get("Action")
    ts_id = request.args.get("TS_ID")
    incoming_key = request.headers.get("TS_AppKey")
    # security check
    if incoming_key != secret_value:
        print("Invalid key")
        return jsonify({"error": "Invalid key"}), 403
    else:
        print("Valid key")
    # end security check
    # 2. Input Validation (Basic)
    if not ts_id:
        return jsonify({"error": "TS_ID parameter is required."}), 400
    if not action:
        return jsonify({"error": "Action parameter is required."}), 400

    print(f"Received Action: {action}, TS_ID: {ts_id}")
    # ********************
    # GET THE JSON BODY
    # ********************
    if request.method != "POST":
        return jsonify({"error": "Only POST requests are allowed, you stupid 😁"}), 405
    try:
        json_body_from_sender = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    parsed = json_body_from_sender

    # Extract only the "Data" object
    data_from_sender = parsed["Data"]

    # Normalize numbers (convert comma to dot, cast to float)
    def normalize_numbers(d):
        for key, value in d.items():
            if isinstance(value, str) and "," in value:
                try:
                    d[key] = float(value.replace(",", "."))
                except ValueError:
                    pass  # Ignore if not a real number string
        return d

    normalized_json_from_sender = normalize_numbers(data_from_sender)

    # Example result
    print(
        "NORMALIZED DATA FROM SENDER = ",
        json.dumps(normalized_json_from_sender, indent=2),
    )

    db_connection = None
    try:
        db_connection = get_db_connection()
        if db_connection:
            # 3. Execute the specific query
            # Assuming 'Action' is for future branching or logging,
            # we're focusing on the TS_ID filter as per your request.
            # *******************************************************
            # * STEP 1:  GET PROJECT TS DATA
            # *******************************************************
            print("*******************************************************")
            print("* STEP 1:  GET PROJECT TS DATA ")
            print("*******************************************************")
            p_ts_data = fetch_project_ts_list(db_connection, ts_id)
            print(f"Data fetched: {p_ts_data}")
            if p_ts_data:
                # print(
                #    f"Found {len(p_ts_data)} Project TS List records for TS_ID: {ts_id}"
                # )
                for record in p_ts_data:
                    print(record)
                try:
                    # Process all rows
                    p_ts_processed_rows = [transform_row(row) for row in p_ts_data]
                    # Print as nicely formatted JSON
                    # print(">>>>> ", json.dumps(p_ts_processed_rows, indent=2))
                except Exception as e:
                    print(f"Error processing rows: {e}")
                    return (
                        jsonify({"error": "Error processing Project TS List data."}),
                        500,
                    )

            else:
                print(f"No records found for TS_ID: {ts_id}")
                return (
                    jsonify({"message": f"No data found for TS_ID: {ts_id}"}),
                    404,
                )  # 404 Not Found
            target_ts_id = ts_id  # Use the TS_ID from the request
            print("target_ts_id: ", target_ts_id)
            # *******************************************************
            # * STEP 2:  GET TS CALENDAR DATA
            # *******************************************************
            print("*******************************************************")
            print("* STEP 2:  GET TS CALENDAR DATA ")
            print("*******************************************************")
            calendar_data = fetch_project_ts_calendar(db_connection, target_ts_id)
            if calendar_data:
                print(f"Found {len(calendar_data)} records for '{target_ts_id}':")
                # for record in calendar_data:
                #    print(record)
                # Process all rows
                processed_c_rows = [transform_row(row) for row in calendar_data]
                # Print as nicely formatted JSON
                print(json.dumps(processed_c_rows, indent=2))

                def enrich_calendar_data(c_data):
                    for entry in c_data:
                        normal = entry.get("Nr_hours_normal") or 0
                        ot1 = entry.get("Nr_hours_OT1") or 0
                        ot2 = entry.get("Nr_hours_OT2") or 0

                        total_hours = normal + ot1 + ot2
                        total_days = round(total_hours / 8.0, 2)

                        entry["Nr_hours_total"] = total_hours
                        entry["Nr_days_total"] = total_days

                    return c_data

                processed_c_rows = enrich_calendar_data(processed_c_rows)
                print("Final c rows:", json.dumps(processed_c_rows, indent=2))
            else:
                print(
                    f"No records found for TS_ID '{target_ts_id}' in Project TS Calendar."
                )
                return (
                    jsonify({"message": f"No Calendar data found for TS_ID: {ts_id}"}),
                    404,
                )  # 404 Not Found

            # *******************************************************
            # * STEP 3:  GET EXCEPTION TIME DATA
            # *******************************************************
            print("*******************************************************")
            print("* STEP 3a:  GET EXCEPTION TIME DATA ")
            print("*******************************************************")
            exception_time_data = fetch_exception_time(db_connection, target_ts_id)
            if exception_time_data:
                print(f"Found {len(exception_time_data)} records for '{target_ts_id}':")
                processed_et_rows = [transform_row(row) for row in exception_time_data]
                # Print as nicely formatted JSON
                print(json.dumps(processed_et_rows, indent=2))
                for record in exception_time_data:
                    print(record)
            else:
                print(f"No records found for TS_ID '{target_ts_id}' in Exception time.")
                # return (
                #    jsonify({"message": f"No Exception time data found for TS_ID: {ts_id}"}),
                #    404,
                # )  # 404 Not Found
            print("*******************************************************")
            print("* STEP 3b:  GET PROJECT EXCEPTION TIME DATA ")
            print("*******************************************************")
            # first_et_object = processed_et_rows[0]
            # print(first_et_object)
            # target_pr_ex_time_id = first_et_object.get("Project_exception_time_id", "")
            # print("target_pr_ex_time_id: ", target_pr_ex_time_id)
            # project_exception_time_data = fetch_project_exception_time(
            #    db_connection, target_pr_ex_time_id
            # )
            """if project_exception_time_data:
                print(
                    f"Found {len(project_exception_time_data)} records for '{target_pr_ex_time_id}':"
                )
                processed_pr_et_rows = [
                    transform_row(row) for row in project_exception_time_data
                ]
                # Print as nicely formatted JSON
                print(json.dumps(processed_pr_et_rows, indent=2))
                for record in project_exception_time_data:
                    print(record)
            else:
                print(
                    f"No records found for TS_ID '{target_pr_ex_time_id}' in Exception time."
                )"""
            """first_pr_et_object = processed_pr_et_rows[0]
            print(first_pr_et_object)
            processed_et_rows["Units"] = first_pr_et_object.get("Units", "")
            processed_et_rows["Exception_time_description"] = first_pr_et_object.get(
                "Exception time description", ""
            )"""

            # 1. First, fetch exception time records
            exception_time_data = fetch_exception_time(db_connection, ts_id)
            print(f"11111111 Found {len(exception_time_data)} records for '{ts_id}':")
            for record in exception_time_data:
                print(record)
            # 2. Extract unique Project_exception_time_id values
            unique_ids = list(
                {
                    item.get("Project exception time id")
                    for item in exception_time_data
                    if item.get("Project exception time id")
                }
            )
            print("QQQQQQQ unique ids", json.dumps(unique_ids))
            # 3. Fetch related project exception time details in one go
            project_exception_time_data = fetch_project_exception_times(
                db_connection, unique_ids
            )
            print(
                f"2222222 Found {len(project_exception_time_data)} project exception time records:"
            )
            for record in project_exception_time_data:
                print(record)
            # 4. Enrich the exception time data with additional info
            final_array = enrich_exception_time_data(
                exception_time_data, project_exception_time_data
            )
            final_exception_time_data = [transform_row(row) for row in final_array]
            print(
                "@@@@@@@@@@@@@@@final array = ",
                json.dumps(final_exception_time_data, indent=2),
            )
            # NOW PROCESS THE DATA TO GET TO A CORRECT CARBONE FILE
            # Mapping from source key → target key

            # Add the mapped key-value to the target
            # **************************************************************
            # * STEP 4:  MAP THE FETCHED DATA TO ASSEMBLE THE CARBONE JSON
            # **************************************************************
            print("***************************************************************")
            print("* STEP 4:  MAP THE FETCHED DATA TO ASSEMBLE THE CARBONE JSON ")
            print("***************************************************************")
            print("NOW DO THE MAPPING...")
            try:
                print(f"Type of p_ts_processed_rows: {type(p_ts_processed_rows)}")
                if p_ts_processed_rows:  # Check if list is not empty
                    print(
                        f"Type of p_ts_processed_rows[0]: {type(p_ts_processed_rows[0])}"
                    )
                    print(
                        f"Content of p_ts_processed_rows[0]: {p_ts_processed_rows[0]}"
                    )

                entry = normalized_json_from_sender  # its not an array but a dict
                raw_path = entry.get("BU Header Logo", "")
                # logo_filename = raw_path.rsplit("/", 1)[-1] if raw_path else None
                # url_friendly_filename = urllib.parse.quote(logo_filename)
                # print(url_friendly_filename)
                # base_url = "https://www.appsheet.com/image/getimageurl?appName=SISUSYNCv1-testcopy-53434990&tableName=BU%20Logos&fileName=BU%20Logos_Images%2F"
                # Extract filename and URL-encode it
                # filename = raw_path.rsplit("/", 1)[-1]
                # encoded_filename = urllib.parse.quote(filename)

                # Ensure proper concatenation with trailing slash
                # final_url = f"{base_url.rstrip('/')}/{encoded_filename}"
                final_url = raw_path
                print(final_url)
                new_json_object = {
                    "TS-ID": ts_id,
                    "BU_Header_Logo": final_url,
                    "Business_Unit": entry.get("Business Unit", ""),
                    "Consultant": entry.get("Consultant", ""),
                    "Reporting_month_new": entry.get("Reporting month new", ""),
                    "Customer_name": entry.get("Customer Name", ""),
                    "Total_nr_hours_this_period": entry.get(
                        "Total nr hours this period", 0
                    ),
                    "Total_nr_days_this_period": entry.get(
                        "Total nr days this period", 0
                    ),
                    "Nr_days_normal_this_period": entry.get(
                        "Nr days normal this period", 0
                    ),
                    "Nr_days_OT1_this_period": entry.get("Nr days OT1 this period", 0),
                    "Nr_days_OT2_this_period": entry.get("Nr days OT2 this period", 0),
                    "Cost_NMT_Act": entry.get("Cost NMT Act", 0),
                    "Related_Project_TS_Calendars": processed_c_rows,
                    "Related_exception_times": processed_et_rows,
                }
                print("xxxxxxxxxxxxxxx final object =", new_json_object)
                print(
                    ">>>>>>>>>>>>>>Final assembled object:",
                    json.dumps(new_json_object, indent=2),
                )
                print("***************************************************************")
                print("* END RESULT CARBONE PAYLOAD ")
                print("***************************************************************")
                # print(json.dumps(new_json_object, indent=2))

                carbone_payload = {
                    "data": new_json_object,  # 👈 insert your generated data here
                    "convertTo": "pdf",
                    "timezone": "Europe/Paris",
                    "lang": "en",
                    "complement": {},
                    "variableStr": "",
                    "reportName": "document",
                    "enum": {},
                    "translations": {},
                    "currencySource": "",
                    "currencyTarget": "",
                    "currencyRates": {},
                    "hardRefresh": "",
                }
                print(
                    ">>>>>>>>>>>>>>Final assembled object:",
                    json.dumps(carbone_payload, indent=2),
                )
                print("***************************************************************")
                print("* END OF PROCESSING CARBONE PAYLOAD, NOW CALL CARBONE HANDLER ")
                print("***************************************************************")

            except Exception as e:
                # Catch any unexpected errors during database operations or other logic
                print(f"An unexpected error occurred: {e}")
                return jsonify({"error": f"cannot map: {str(e)}"}), 500

            try:

                headers = {
                    "Content-Type": "application/json",
                    "AppKey": "7e9f8b3d5a1c4297fa6b0de4392ed10f8ab7e12466f52a8d5cfe90b6432d901fa57c3de8196a54be1f9a84cb29c07915320c6de5f13e98b94298c83ae374bcbb6",
                }
                params = {"mode": "test", "filename": "generate", "sender": "raw"}
                cloud_run_url = "https://europe-west1-my-project-trial-1-441910.cloudfunctions.net/project-4-carbone-doc-handler-new"
                response = requests.post(
                    url=cloud_run_url,
                    params=params,
                    json=carbone_payload,
                    headers=headers,
                )
                if response.status_code == 200:
                    print("✅ Webhook call successful.")
                    # print("Response:", response.json())
                else:
                    print(f"❌ Failed with status code {response.status_code}")
                    print("Response content:", response.text)

                # print(json.dumps(carbone_payload, indent=2))
                # return jsonify(carbone_payload), 200

            except Exception as e:
                # Catch any unexpected errors during database operations or other logic
                print(f"An unexpected error occurred: {e}")
                return (
                    jsonify({"error": f"call to carbone handler failed: {str(e)}"}),
                    500,
                )
            try:
                if response.status_code == 200:
                    response_json = response.json()  # ✅ convert to dict
                    content_base64 = response_json["content_base64"]
                    pdf_bytes = base64.b64decode(content_base64)
                else:
                    print(f"Error: {response.status_code} - {response.text}")
                # Keep it in memory
                project_id = entry.get("Project ID", "")
                consultant = entry.get("Consultant", "")
                reporting_month_year = entry.get("Reporting Month Year", "")
                firstname = entry.get("consultant first name", "")
                reporting_month_new = entry.get("Reporting month new", "")
                consultant_email = entry.get("Consultant email", "")
                ts_id_clean = entry.get("TS ID Clean", "")
                reporting_yyyymm = entry.get("Reporting yyyymm", "")

                print("project id: ", project_id)
                print("consultant: ", consultant)
                print("reporting_month_year: ", reporting_month_year)
                print("firstname: ", firstname)
                print("reporting_month_new: ", reporting_month_new)
                print("consultant_email: ", consultant_email)
                print("ts_id_clean: ", ts_id_clean)
                print("reporting_yyyymm: ", reporting_yyyymm)
                print("action: ", action)

                sender_email = "master@sisusync.app"
                sender_password = "rnyo nbku sion plwk"
                attachment_bytes = pdf_bytes
                attachment_filename = (
                    f"{ts_id_clean}_Timesheet_{consultant}_{reporting_yyyymm}.pdf"
                )
                # attachment_filename = "testfile.pdf"
                if action == "SISU_TS_SAMSUNG":
                    sender_name = "sync@sisu.be"
                    recipient_email = ["invoicing_belgium@ariadgroup.com"]
                    recipient_cc = None
                    recipient_bcc = ["nico.marien@sisusync.app", "sync@sisu.be"]
                    reply_to = "sync@sisu.be"
                    body = f"Please find attached the timesheet in pdf format for the fixed price project with project ID {project_id}. \n\nThis pdf will not be sent to the consultant."
                    subject = f"Timesheet for {consultant} {reporting_month_year}"
                # nico.marien@sisusync.app, sync@sisu.be
                # invoicing_belgium@ariadgroup.com
                elif action == "SISU_TS_NON_SAMSUNG":
                    sender_name = "sync@sisu.be"
                    recipient_email = [consultant_email]
                    recipient_cc = None
                    recipient_bcc = [
                        "nico.marien@sisusync.app",
                        "sync@sisu.be",
                        "adam@ariadgroup.com",
                        "invoicing_belgium@ariadgroup.com",
                    ]
                    reply_to = "sync@sisu.be"
                    body = f"Dear {firstname} ,\n\nThanks for submitting your timesheet for this month. Please find attached your timesheet in pdf format.\n\nbest regards, \nthe SISU Team"
                    subject = f"Timesheet for {consultant} {reporting_month_year}"
                # nico.marien@sisusync.app, sync@sisu.be, adam@ariadgroup.com, invoicing_belgium@ariadgroup.com
                # Consultant email

                elif action == "SISU_TS_CONSULTANT":
                    sender_name = "sync@sisu.be"
                    recipient_email = [consultant_email]
                    recipient_cc = None
                    recipient_bcc = [
                        "nico.marien@sisusync.app",
                        "sync@sisu.be",
                        "adam@ariadgroup.com",
                        "invoicing_belgium@ariadgroup.com",
                    ]
                    reply_to = "sync@sisu.be"
                    body = f"Dear {firstname}, \n\nPlease find attached you timesheet for {reporting_month_new} in pdf format.\n\nbest regards, \nthe SISU Team"
                    subject = f"Timesheet for {consultant} {reporting_month_year}"
                # nico.marien@sisusync.app, sync@sisu.be, adam@ariadgroup.com, invoicing_belgium@ariadgroup.com
                # Consultant email
                else:  # no action parameter given (for testing)
                    sender_name = "WISEWORKS"
                    recipient_email = "mdk3@telenet.be"
                    recipient_cc = "marc.dekrock@wiseworks.be"
                    recipient_bcc = "support@wiseworks.be"
                    reply_to = "mdk3@telenet.be"
                    reason = "test"
                    subject = f"Subject: This is a testmail for Sisu TS creation flow"
                    body = f"Hello,\n\nThis is to notify you of the following event:\n\n{reason}\n\nRegards,\n{sender_name}"

                success = send_email(
                    subject,
                    body,
                    sender_email,
                    sender_name,
                    sender_password,
                    recipient_email,
                    recipient_cc,
                    recipient_bcc,
                    reply_to,
                    attachment_bytes,
                    attachment_filename,
                )

                if not success:
                    print("⚠️ Failed to send email.")
                    return (
                        jsonify({"error": "failed to send email"}),
                        500,
                    )
                else:
                    print("✅ Email function executed successfully.")
                    return (
                        jsonify({"ok": "successfully sent email!"}),
                        200,
                    )

                # select sertain keys

            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                return (
                    jsonify(
                        {
                            "error": f"call to carbone handler failed or getting data from json failed : {str(e)}"
                        }
                    ),
                    500,
                )
        else:
            print("Failed to connect to the database.")
            return jsonify({"error": "Database connection failed."}), 500

    except pymysql.MySQLError as e:
        # Handle MySQL errors specifically
        print(f"MySQL error occurred: {e}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500

    finally:
        if db_connection:
            db_connection.close()
            print("Database connection closed.")
    # return jsonify({"error": "Unexpected termination of function."}), 500
