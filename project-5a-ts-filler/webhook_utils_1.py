import requests
import urllib.parse
import json

WHC_app_id = "397f3d50-89dc-46bb-b912-e52499e9b2f1"
WHC_app_access_key = "V2-ggEMV-znIzP-zanfl-m6Sxr-zre0X-55Mkm-oOMQM-qfaZ6"
#*
def send_push_notification(message):
    url = "https://www.pushsafer.com/api?k=AYIor8gFjJ5zb1k0Y7Pv&d=17595&m=ryan_test"
    response = requests.get(url)

    if response.status_code == 200:
        return "Notification sent successfully!"
    else:
        return f"Failed to send notification. Status code: {response.status_code}, Response: {response.text}"
#**********************************************************
def get_url(table):
    encoded_table = urllib.parse.quote(table)
    url_WHC = f"https://api.appsheet.com/api/v2/apps/{WHC_app_id}/tables/{encoded_table}/Action?applicationAccessKey={WHC_app_access_key}"
    return url_WHC

#**********************************************************
def post_data_to_appsheet_whc(table, data):
    url_WHC = get_url(table)
    print("URL:", url_WHC)
    response = requests.post(url_WHC, json=data)
    return response

# #****************************************************************
def post_docdata_to_carbone(template_id, data):
    url_carbone = f"https://api.carbone.io/render/{template_id}"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": carbone_authorisation_key
    }
    response = requests.post(url_carbone, json=data, headers=headers)
    return response
# #****************************************************************
def get_doc_from_carbone(render_id):
    url_carbone = f"https://api.carbone.io/render/{render_id}"
    headers = {
        "Accept": "application/json",
        "Authorization": carbone_authorisation_key
    }
    response = requests.get(url_carbone, headers=headers)
    return response

#**********************************************************
def post_data_to_appsheet_whc_v2(table, rows=None, action="find", selector=None):
    url_WHC = get_url(table)
    print("URL:", url_WHC)
     #table to address
    # Headers
    #none
    #JSON payload
    #`Add`: Adds a new row to the table.
    #`Delete`: Deletes existing rows from the table.
    #`Edit`: Updates existing rows in the table.
    #`Find`: Reads an existing row of the table.
    payload = {
    "Action": action,
    "Properties": {
    "Locale": "en-US", 
    "Location": "51.159133, 4.806236", 
    "Timezone": "Central European Standard Time",
    "UserSettings": {  "User role":"Super Administrator" }
    },
    "Rows": rows
    }
    if selector:
        payload["Properties"]["Selector"] = selector
    print("JSON FOR APPSHEET in V2: ", json.dumps(payload, indent=2))
    response = requests.post(url_WHC, json=payload)
    return response