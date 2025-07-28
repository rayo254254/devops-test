import base64
import json
import logging
import os
import io
from datetime import datetime
import requests
import mimetypes  # To infer filename extension if needed and for better MIME handling

import google.auth  # This is the standard way to get default credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

import functions_framework

from dotenv import load_dotenv  # For local development
from gdrive_utils import upload_doc_from_memory
from webhook_utils_2 import post_data_to_appsheet
from xml_to_appsheet import (
    process_peppol_xml,
)  # Assuming this is your XML processing function

# Load environment variables from .env file if it exists (for local development)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# --- Configuration (Set these as Cloud Function Environment Variables!) ---
# Billit API Configuration
BILLIT_BASE_URL = os.environ.get("BILLIT_BASE_URL")  # e.g., "https://api.billit.be"
BILLIT_API_KEY = os.environ.get("BILLIT_API_KEY")  # Your Billit API Key

# AppSheet Configuration
APPSHEET_APP_ID = os.environ.get("APPSHEET_APP_ID")
APPSHEET_TABLE_NAME = os.environ.get("APPSHEET_TABLE_NAME")
APPSHEET_API_KEY = os.environ.get("APPSHEET_API_KEY")


# Google Drive Configuration
GDRIVE_ROOT_FOLDER_NAME = os.environ.get(
    "GDRIVE_ROOT_FOLDER_NAME_INCOMING", "AppSheet Billit Invoices"
)
GDRIVE_TARGET_PARENT_ID = os.environ.get(
    "GDRIVE_TARGET_FOLDER_ID_INCOMING"
)  # NEW: ID of your Shared Drive or a specific human user's folder
GDRIVE_API_SCOPES = ["https://www.googleapis.com/auth/drive.file"]  # Simplified scope


# --- Helper functions for Billit API ---
def _billit_api_call(method, endpoint, params=None, data=None):
    """
    Helper to make authenticated calls to the Billit API.
    """
    if not BILLIT_BASE_URL or not BILLIT_API_KEY:
        raise ValueError("Billit API base URL or API Key not configured.")

    url = f"{BILLIT_BASE_URL}{endpoint}"
    headers = {"ApiKey": BILLIT_API_KEY, "Accept": "application/json"}
    if data:  # For POST/PUT if Billit ever requires them
        headers["Content-Type"] = "application/json"

    try:
        response = requests.request(
            method, url, headers=headers, params=params, json=data
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Billit API call failed: {method} {url} - {e}")
        if hasattr(e, "response") and e.response is not None:
            logging.error(f"Billit API Error Response: {e.response.text}")
        raise


def get_billit_order_details(order_id):
    """Fetches full order details from Billit API."""
    logging.info(f"Fetching order details for ID: {order_id}")
    return _billit_api_call("GET", f"/v1/orders/{order_id}")


def get_billit_file_content(file_id):
    """Fetches file content (base64) from Billit API."""
    logging.info(f"Fetching file content for FileID: {file_id}")
    return _billit_api_call("GET", f"/v1/files/{file_id}")


# --- Helper function for Google Drive ---
def get_drive_service():
    """Initializes and returns a Google Drive API service."""
    # When deployed to Cloud Functions, the default service account credentials
    # are automatically picked up by google.auth.default().
    # Ensure this service account has appropriate Google Drive permissions.
    try:
        credentials, project = google.auth.default()
        logging.info(f"Using Google Cloud project: {project}")
        return build("drive", "v3", credentials=credentials)
    except Exception as e:
        logging.error(f"Failed to initialize Drive service: {e}")
        raise


def get_or_create_drive_folder(drive_service, folder_name, parent_id=None):
    """
    Checks if a folder exists in Google Drive and returns its ID. If not, creates it.
    Can create it within a specified parent folder/Shared Drive.
    """
    query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = (
        drive_service.files().list(q=query, fields="files(id, name, parents)").execute()
    )
    items = results.get("files", [])

    if items:
        logging.info(
            f"Found existing Google Drive folder: '{folder_name}' with ID: {items[0]['id']}"
        )
        return items[0]["id"]
    else:
        # Create the folder
        file_metadata = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            file_metadata["parents"] = [parent_id]

        folder = drive_service.files().create(body=file_metadata, fields="id").execute()
        logging.info(
            f"Created new Google Drive folder: '{folder_name}' with ID: {folder.get('id')}"
        )
        return folder.get("id")


def upload_file_to_drive(
    drive_service, folder_id, filename, file_content_bytes, mime_type
):
    """
    Uploads a file to a specific folder in Google Drive.
    Returns the file ID of the uploaded file.
    """
    file_metadata = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(
        io.BytesIO(file_content_bytes), mimetype=mime_type, resumable=True
    )

    file = (
        drive_service.files()
        .create(body=file_metadata, media_body=media, fields="id, webViewLink")
        .execute()
    )
    logging.info(
        f"Uploaded file '{filename}' to Google Drive. File ID: {file.get('id')}"
    )
    return file.get("id")


# --- AppSheet Interaction ---
def update_appsheet_table(invoice_data, drive_file_id):
    """
    Adds a new row to the AppSheet table with comprehensive invoice details.
    """
    appsheet_api_url = f"https://api.appsheet.com/api/v2/apps/{APPSHEET_APP_ID}/tables/{APPSHEET_TABLE_NAME}/Action"

    # Construct the AppSheet-friendly Google Drive URL
    # For an AppSheet 'File' type column mapped to a Drive folder, you often provide just the filename.
    # If the column is 'URL' or 'Text', the webViewLink/public link is better.
    # Let's provide the standard Google Drive view link, which is generally flexible.
    google_drive_file_url = (
        f"https://drive.google.com/file/d/{drive_file_id}/view?usp=drivesdk"
    )

    # Extract relevant data from invoice_data dictionary
    billit_id = invoice_data.get("OrderID")
    order_number = invoice_data.get("OrderNumber")
    customer_name = invoice_data.get("Customer", {}).get("DisplayName")
    supplier_name = invoice_data.get("Supplier", {}).get("DisplayName")
    invoice_date_str = invoice_data.get("OrderDate")
    total_excl = invoice_data.get("TotalExcl")
    total_incl = invoice_data.get("TotalIncl")
    total_vat = invoice_data.get("TotalVAT")
    currency = invoice_data.get("Currency")
    file_name = invoice_data.get("FileName")  # The original filename from Billit

    # Convert date for AppSheet if necessary (AppSheet usually handles ISO format)
    # invoice_date_formatted = datetime.fromisoformat(invoice_date_str).strftime('%Y-%m-%d') if invoice_date_str else None

    row_data = {
        "BillitOrderID": str(
            billit_id
        ),  # Ensure it's a string if AppSheet column is Text
        "BillitOrderNumber": order_number,
        "CustomerName": customer_name,
        "SupplierName": supplier_name,
        "InvoiceDate": invoice_date_str,  # Send as is, AppSheet often handles ISO 8601
        "TotalExcl": total_excl,
        "TotalIncl": total_incl,
        "TotalVAT": total_vat,
        "Currency": currency,
        "OriginalFileName": file_name,  # Store the original Billit filename for reference
        "InvoiceFile": google_drive_file_url,  # Or just file_name if AppSheet column is type File and folder linked
        "Status": "Processed",
        "ReceivedTimestamp": datetime.utcnow().isoformat(),
    }

    # Remove None values before sending to AppSheet to avoid schema issues if a field is optional
    row_data = {k: v for k, v in row_data.items() if v is not None}

    payload = {
        "Action": "Add",
        "Properties": {
            "Locale": "en-US",
            "Timezone": "Europe/Brussels",  # Adjust to your local timezone for AppSheet date/time
        },
        "Rows": [row_data],
    }

    headers = {
        "Content-Type": "application/json",
        "ApplicationAccessKey": APPSHEET_API_KEY,
    }

    logging.info(f"Sending data to AppSheet: {json.dumps(payload)}")
    response = requests.post(
        appsheet_api_url, headers=headers, data=json.dumps(payload)
    )

    if response.status_code == 200:
        logging.info("Successfully updated AppSheet table.")
        logging.info(f"AppSheet Response: {response.text}")
    else:
        logging.error(
            f"Failed to update AppSheet table. Status: {response.status_code}, Response: {response.text}"
        )
        response.raise_for_status()


print("STARTING Cloud Function for Billit Webhooks...")


# --- Main Cloud Function Entry Point ---
@functions_framework.http
def main(request):
    """
    Receives a webhook from Billit, fetches order/file details,
    saves the file to Google Drive, and updates an AppSheet table.
    """
    print("Billit_api_key = ", BILLIT_API_KEY)
    print("Received request:", request)
    logging.info("Received request: %s", request)
    if request.method != "POST":
        logging.warning(f"Received non-POST request: {request.method}")
        return ("Only POST requests are accepted", 405)

    try:
        request_json = request.get_json(silent=True)
        if not request_json:
            raise ValueError("No JSON payload received or invalid JSON.")

        billit_order_id = request_json.get("UpdatedEntityID")
        updated_entity_type = request_json.get("UpdatedEntityType")
        webhook_update_type = request_json.get("WebhookUpdateTypeTC")

        if not billit_order_id:
            raise ValueError("Missing 'UpdatedEntityID' in webhook payload.")

        if updated_entity_type != "Order" or webhook_update_type != "I":
            logging.info(
                f"Ignoring webhook for EntityType: {updated_entity_type}, UpdateType: {webhook_update_type}. Expected 'Order' and 'I'."
            )
            return ("Webhook received but not processed (ignored type/status)", 200)

        logging.info(f"Received Billit webhook for Order ID: {billit_order_id}")

        # 1. Fetch Order Details from Billit API
        order_details = get_billit_order_details(billit_order_id)
        logging.info(f"Fetched Billit order details for ID {billit_order_id}.")

        # 2. Identify the target file (XML attachment)
        target_file_id = None
        target_file_name = None
        target_mime_type = None

        # Prioritize XML attachments for e-invoices
        attachments = order_details.get("Attachments", [])
        for attachment in attachments:
            if attachment.get("FileName", "").lower().endswith(".xml"):
                target_file_id = attachment.get("FileID")
                target_file_name = attachment.get("FileName")
                # We'll get the actual MIME type from the file content endpoint later
                break  # Found our XML, break the loop

        # If no XML attachment, maybe fall back to OrderPDF? (Optional, adjust as needed)
        if not target_file_id and order_details.get("OrderPDF"):
            logging.warning(
                f"No XML attachment found for order {billit_order_id}. Attempting to process OrderPDF."
            )
            target_file_id = order_details["OrderPDF"].get("FileID")
            target_file_name = order_details["OrderPDF"].get("FileName")
            # Note: MimeType for PDF is application/pdf, but get_billit_file_content will confirm

        if not target_file_id:
            raise ValueError(
                f"No suitable XML attachment or OrderPDF found for Order ID: {billit_order_id}."
            )

        # 3. Fetch File Content from Billit API
        file_data = get_billit_file_content(target_file_id)

        base64_file_content = file_data.get("FileContent")
        original_billit_filename = file_data.get(
            "FileName", target_file_name
        )  # Prefer filename from file_data, fallback to target
        file_mime_type = file_data.get("MimeType")

        if not base64_file_content:
            raise ValueError(
                f"No file content received from Billit API for File ID: {target_file_id}."
            )

        # Decode the Base64 file content
        try:
            decoded_file_bytes = base64.b64decode(base64_file_content)
            logging.info("File content decoded successfully.")
        except Exception as e:
            logging.error(
                f"Error decoding base64 file content for File ID {target_file_id}: {e}"
            )
            return (f"Invalid base64 file content: {e}", 400)

        # Ensure filename has an appropriate extension if missing from Billit's response
        if not original_billit_filename or "." not in original_billit_filename:
            # Try to infer extension from MIME type
            ext = mimetypes.guess_extension(file_mime_type, strict=False)
            if ext:
                original_billit_filename = f"billit_file_{target_file_id}{ext}"
            else:
                original_billit_filename = (
                    f"billit_file_{target_file_id}.unknown"  # Last resort
                )

        # 4. Save to Google Drive
        """drive_service = get_drive_service()
        if not drive_service:
            raise RuntimeError("Failed to get Google Drive service.")
        target_folder_id = get_or_create_drive_folder(
            drive_service, GDRIVE_ROOT_FOLDER_NAME, GDRIVE_TARGET_PARENT_ID
        )
        if not target_folder_id:
            raise RuntimeError(
                f"Could not find or create Google Drive folder: {GDRIVE_ROOT_FOLDER_NAME}"
            )

        drive_file_id = upload_file_to_drive(
            drive_service,
            target_folder_id,
            original_billit_filename,
            decoded_file_bytes,
            file_mime_type,
        )
        if not drive_file_id:
            raise RuntimeError("Failed to upload file to Google Drive.")

        # 5. Update AppSheet table
        if not all([APPSHEET_APP_ID, APPSHEET_TABLE_NAME, APPSHEET_API_KEY]):
            logging.warning(
                "AppSheet configuration incomplete. Skipping AppSheet update."
            )
            return (
                "File processed, but AppSheet not updated due to missing config.",
                200,
            )"""
        folder_id = GDRIVE_TARGET_PARENT_ID
        filename = original_billit_filename
        file_bytes = decoded_file_bytes
        mime_type = file_mime_type

        # Save rendered document to Google Drive
        print("Uploading document to Google Drive..., folder_id: ", folder_id)
        upload_doc_from_memory(
            file_content=file_bytes,
            filename=filename,
            mime_type=mime_type,
            folder_id=folder_id,
        )
        # XML is uploaded to Google Drive, now we can send it to the Tickstar API
        print("End uploading DOCUMENT to Google Drive...")

        # 6. Process XML and update AppSheet (
        # A. map xml to AppSheet,
        # B. update Appsheet records,
        # C. save file to Google Drive)
        processed_peppol_XML = io.BytesIO(decoded_file_bytes)
        response_from_xml = process_peppol_xml(processed_peppol_XML)
        print("response_from_xml = ", response_from_xml)

        logging.info(
            f"Successfully processed webhook for Order ID: {billit_order_id}. "
            f"File '{original_billit_filename}' saved and AppSheet updated."
        )
        return ("Successfully processed Billit webhook", 200)

    except ValueError as ve:
        logging.error(f"Bad Request or Missing Configuration: {ve}")
        return (str(ve), 400)
    except requests.exceptions.RequestException as re:
        logging.error(f"External API error (Billit or AppSheet): {re}")
        return (f"Error communicating with external service: {re}", 500)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return (f"Internal Server Error: {e}", 500)
