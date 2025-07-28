import requests
import urllib.parse
import json


#*
def send_push_notification(message):
    url = "https://www.pushsafer.com/api?k=AYIor8gFjJ5zb1k0Y7Pv&d=17595&m=ryan_test"
    response = requests.get(url)

    if response.status_code == 200:
        return "Notification sent successfully!"
    else:
        return f"Failed to send notification. Status code: {response.status_code}, Response: {response.text}"
#**********************************************************
def get_url(table, app_id=None, app_access_key=None):
    encoded_table = urllib.parse.quote(table)
    appsheet_url = f"https://api.appsheet.com/api/v2/apps/{app_id}/tables/{encoded_table}/Action?applicationAccessKey={app_access_key}"
    return appsheet_url

#**********************************************************
def post_data_to_appsheet(table, rows=None, action=None, selector=None, app_name=None, app_id=None, app_access_key=None, user_settings=None):
    print("post_data_to_appsheet called with parameters:")
    #if not app_name or not app_id or not app_access_key or not table or not action or not rows:
    #   print("parameter missing, please check the parameters")
    print("OK, lets do the call to AppSheet")
    print("App Name:", app_name)
    if rows is None:
        rows = []  # make sure it's an empty list, not [None]
    url_appsheet_app = get_url(table, app_id, app_access_key)
    print("URL:", url_appsheet_app)
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
    "Timezone": "Central European Standard Time"
    },
    "Rows": rows
    }
    if selector:
        payload["Properties"]["Selector"] = selector
    if user_settings:
        payload["Properties"]["UserSettings"] = user_settings
    print("JSON FOR APPSHEET in V2: ", json.dumps(payload, indent=2))
    response = requests.post(url_appsheet_app, json=payload)
    return response
#**********************************************************