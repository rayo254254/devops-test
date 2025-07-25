# main.py

import os
import requests
from flask import (Flask, render_template, request, redirect, url_for, flash)

# --- Configuration ---
# Initialize the Flask App
app = Flask(__name__)

# A secret key is required for flash messages. Set as an environment variable in production.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-strong-default-secret-key-for-dev")

# Get Tickstar credentials from environment variables for security.
TICKSTAR_API_BASE_URL = os.environ.get("TICKSTAR_API_BASE_URL", "https://api.test.galaxygw.com/transaction-api/1.0")
TICKSTAR_API_KEY = os.environ.get("TICKSTAR_API_KEY")

# to get the latest TICKTAR_API_KEY please execute this Zenphi flow: 
# https://webhook.eu1.zenphi.io/http/e1379fe8651542359f58fa862638c3d4/1a96d4b20f0c488884b1b2ad23d27318?x-zenphi-httptriggertoken=NDU4YjgxOWYtYmM5ZS00NDdmLThiYmQtNjJlN2FkODgzZTBm&action=WEBHOOK
# next go to this flow: PEPPOL TICKSTAR in the E-INVOICING space on Zenphi Wiseworks
# next pick the acces token from the run log of the last run
#eg. 
# JTO Tokens
# ACCESS TOKEN: eyJraWQiOiJrRnJGRFZxSXE4NE1kZElaSTF2V0FyMEFTSmVSMGJsUk
# copy the key and in a terminal execute the following: 
# import TICKSTAR_API_KEY="PASTE HERE YOUR KEY"
# check if the key was captured by executing this in the terminal:
# echo $TICKSTAR_API_KEY
# you are now set to go
# execute the code with following command in the terminal: 
# python main.py
# this will result in something like this: 
#  * Serving Flask app 'main'
# * Debug mode: on
# WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
# * Running on all addresses (0.0.0.0)
# * Running on http://127.0.0.1:8081
# * Running on http://192.168.1.35:8081
# Press CTRL+C to quit
# * Restarting with watchdog (fsevents)
# * Debugger is active!
# * Debugger PIN: 113-593-403
# the service is now running. 
# goto a browser and execute following address: 
# http://localhost:8081/
# voila, now you can see the webhooks, delete webhooks and install new webhooks
# please note the code below has a Tickstar url for testing. For production you need to uase another url



# The specific event type we are interested in.
EVENT_TYPE_PEPPOL_INCOMING = "peppol-transaction-incoming"


# --- Tickstar API Helper Functions ---

# Define the correct endpoint path as a constant for consistency
WEBHOOKS_ENDPOINT = f"{TICKSTAR_API_BASE_URL}/transactions/webhooks"

# --- Tickstar API Helper Functions (REPLACE ALL THREE) ---

def get_tickstar_headers():
    """Returns the authorization headers for Tickstar API calls."""
    if not TICKSTAR_API_KEY:
        raise ValueError("TICKSTAR_API_KEY environment variable not set.")
    return {
        "Authorization": f"Bearer {TICKSTAR_API_KEY}",
        "Content-Type": "application/json"
    }

def list_webhooks():
    """Fetches all webhooks from Tickstar using the correct endpoint."""
    try:
        # USE THE CORRECT ENDPOINT
        response = requests.get(WEBHOOKS_ENDPOINT, headers=get_tickstar_headers(), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing webhooks: {e}")
        return None

def create_webhook(url):
    """Creates a new INBOUND webhook in Tickstar using the correct payload format."""
    # BUILD THE CORRECT PAYLOAD based on user's provided JSON
    payload = {
        "version": "1.0",
        "direction": "INBOUND",
        "callbackUrl": url,
        "artefacts": [],
        "maxCallbackSize": 51200,
        "autoAcknowledge": False,
        "forceMultipart": False
    }
    try:
        # POST TO THE CORRECT ENDPOINT with the new payload
        response = requests.post(WEBHOOKS_ENDPOINT, headers=get_tickstar_headers(), json=payload, timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        # Add more detailed error logging
        print(f"Error creating webhook: {e}")
        if e.response is not None:
            print(f"API Response Status Code: {e.response.status_code}")
            print(f"API Response Text: {e.response.text}")
        return False

def delete_webhook(webhook_id):
    """Deletes a specific webhook from Tickstar using the correct endpoint."""
    try:
        # DELETE FROM THE CORRECT ENDPOINT using the specific webhook ID
        response = requests.delete(f"{WEBHOOKS_ENDPOINT}/{webhook_id}", headers=get_tickstar_headers(), timeout=10)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error deleting webhook: {e}")
        return False


# --- Flask Web Routes ---

@app.route('/', methods=['GET'])
def index():
    """Main page to view and manage webhooks."""
    if not TICKSTAR_API_KEY:
        flash("Server-side error: TICKSTAR_API_KEY is not configured.", "danger")
        return render_template('index.html', webhooks=[])

    response_data = list_webhooks()
    webhooks_list = [] # Default to an empty list

    print("--- DEBUG: Full API Response Data ---")
    print(response_data) # Keep this for now, it's useful!

    if response_data and isinstance(response_data, dict):
        # *** THIS IS THE KEY FIX ***
        # The API response contains the list under the "items" key.
        webhooks_list = response_data.get('items', [])
    elif response_data is None:
        flash("Error: Could not fetch webhooks from Tickstar. Check API key and logs.", "danger")
    else:
        flash("API returned an unexpected data format.", "warning")

    # Pass the correctly extracted list to the template
    return render_template('index.html', webhooks=webhooks_list)

@app.route('/install', methods=['POST'])
def install_webhook():
    """Handles the form submission to install a new webhook."""
    webhook_url = request.form.get('webhook_url')

    if not webhook_url:
        flash("Webhook URL cannot be empty.", "warning")
        return redirect(url_for('index'))

    # *** THIS IS THE KEY FIX ***
    # Call the new create_webhook function which only needs the URL
    success = create_webhook(webhook_url)

    if success:
        flash(f"Webhook for '{webhook_url}' installed successfully!", "success")
    else:
        # The error log will now show the detailed API response on failure
        flash(f"Failed to install webhook for '{webhook_url}'. Check logs for details.", "danger")

    return redirect(url_for('index'))

@app.route('/delete/<webhook_id>', methods=['POST'])
def remove_webhook(webhook_id):
    """Handles the request to delete a webhook."""
    success = delete_webhook(webhook_id)

    if success:
        flash(f"Webhook ID '{webhook_id}' was deleted successfully.", "success")
    else:
        flash(f"Failed to delete webhook ID '{webhook_id}'. Check logs for details.", "danger")

    return redirect(url_for('index'))

# --- Local Development Runner ---
# This block is ignored by Gunicorn on Cloud Run but allows local testing
if __name__ == "__main__":
    # Ensure a default port is set if running locally without PORT env var
    port = int(os.environ.get("PORT", 8081))
    app.run(debug=True, host="0.0.0.0", port=port)