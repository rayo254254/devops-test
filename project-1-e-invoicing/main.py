# MAIN.PY
# ****************************************************************************
# THIS FLOW IS HANDLING AN E-INVOiCE USING TICKSTAR LAYER     xfgbryan omondi marc de krock *
# IT HANDLES: INVOICES, CREDIT NOTES AND SB INVOICES                        *
#                                                                           *
# IT CREATES A PEPPOL COMPLIANT XML FILE USING JINJA2                       *
# IT UPLOADS THE XML FILE TO GOOGLE DRIVE                                   *
# IT SENDS THE XML FILE TO TICKSTAR API                                     *
# IT CREATES A RECORD IN THE APPSHEET TABLE "peppol_transactions"           *
#                                                                           *
# added 20250519: support for Petrol Cave                                   *
# - parameters: sender=petrolcave
#                                                                           *
# creteated by: Marc De Krock                                               *
# date: 20250516                                                            *
# ****************************************************************************
# FROM OWN LIBS
from data_processing_utils import (
    split_supplier_address_for_template,
    split_customer_address_for_template,
    clean_json_for_peppol,
    build_invoice_lines,
)
from authentication_utils import (
    authenticate_drive,
    upload_xml_memory,
    save_token,
    load_token,
)
from tickstar_utils import call_tickstar_api
from webhook_utils_1 import (
    send_push_notification,
    post_data_to_appsheet_whc,
    post_data_to_appsheet_pc,
)

# IMPORTS
import uuid
import functions_framework
import os
import re
import pandas as pd
import json
import xml.etree.ElementTree as ET
import google.auth

# FROM OTHER LIBS
from datetime import datetime, timezone
from flask import request, Response, jsonify
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path
from collections import defaultdict
from urllib.parse import quote


# Constants definition
TOKEN_FILE = Path("token_cache.json")
Instance_id_invoice = "Invoice-2::Invoice"
Instance_id_creditnote = "CreditNote-2::CreditNote"
Instance_id_Selfbilling = "Invoice-2::Invoice"
Process_nr_invoice = "01:1.0"
Process_nr_creditnote = "01:1.0"
Process_nr_Selfbilling = "06:1.0"


# ************** HERE THE FLOW STARTS ***********************
# **SECRETS SECTION**
_, project_id = google.auth.default()
print("Project ID: ", project_id)

project_id = os.getenv("PROJECT_ID", None)
print("Project ID:", project_id)
"""PROJECT_ID = project_id
SECRET_ID = "Appkey_A1"

secret_value = get_secret(SECRET_ID, PROJECT_ID)

print("****************My secret value:", secret_value)"""
secret_value = (
    "^Yfz1R6BsD#KjmWp9@uCV83+OQtwcEbZPiFHaUL!M5xAqJhNX*GTo72v$lnRydk0gzseY#bKP4Q^mwdnMT"
)


# ** URL ENTRY POINT FOR THE CLOUD FUNCTION **
@functions_framework.http
def main(request):
    # **********************************************************
    # * SEE IF ITS A TESTCALL OTHERWISE GET PARAMS AND HEADERS *
    # **********************************************************
    test_run = request.args.get("test")
    if test_run:
        print("Test run, skipping security checks and processing")
        return jsonify({"message": "Test run, no processing done"}), 200
    incoming_key = request.headers.get("TS-AppKey")
    sender = request.args.get("sender")
    table_arg = request.args.get("table")
    print("Incoming key: ", incoming_key)
    print("Secret value: ", secret_value)
    print("sender: ", sender)
    print("table_arg: ", table_arg)

    # security check
    if incoming_key != secret_value:
        print("Invalid key")
        return jsonify({"error": "Invalid key"}), 403
    else:
        print("Valid key")
    # end security check
    # **GET BASEPATH
    base_path = Path(os.getcwd())
    print("Working directory:", os.getcwd())
    # base_path = Path(__file__).parent
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(base_path / "templates"),
        autoescape=select_autoescape(["xml"]),
    )

    # ***************************************************
    # * GET THE JSON BODY FROM THE INCOMING CALL.       *
    # ***************************************************
    if request.method != "POST":
        return jsonify({"error": "Only POST requests are allowed, you stupid"}), 405
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    # Normalize JSON (flatten nested dicts/lists)
    try:
        entry_timestamp = datetime.now(timezone.utc).isoformat()
        random_uuid = str(uuid.uuid4())
        print("data", json.dumps(data, indent=2))
        print("______________________________________________")
        # SHOW timestamp and UUID, add later to the XML
        print("timestamp: ", entry_timestamp)
        print("random_uuid: ", random_uuid)
        print("______________________________________________")
        # **************************************************

        # ***************************************************
        # * GET TEMPLATE BASED ON SENDER AND TABLE ARGUMENT *
        # ***************************************************
        # Default template = WHC
        template = env.get_template(
            "peppol_compliant_invoice_with_jinja_placeholders_1.xml"
        )
        peppol_xml_files = (
            "14cSev_C8w7fuYgU56__ijGoMuLMb3Rqh"  # folder under WisehubCore
        )
        if sender == "petrolcave":
            print("sender is petrolcave!!!!!!")
            peppol_xml_files = (
                "1vUKgQMKLPQMb3nACFRyT5mYg4-WV6lp8"  # folder in root drive Petrol Cave
            )
            if table_arg == "proforma":
                print("table_arg is proforma")
                template = env.get_template(
                    "peppol_compliant_invoice_with_jinja_placeholders_petrol_cave_1.xml"
                )
            elif table_arg == "ad_hoc_invoice":
                print("table_arg is ad_hoc_invoice")
                template = env.get_template(
                    "peppol_compliant_invoice_with_jinja_placeholders_petrol_cave_ad_hoc_invoice.xml"
                )
            elif table_arg == "proforma_com":
                print("table_arg is proforma_com")
                template = env.get_template(
                    "peppol_compliant_invoice_with_jinja_placeholders_petrol_cave_proforma_com.xml"
                )
        print("Template FOUND: ", template)
        # END DETERMINE THE FOLDER ID

        # ********************************************************
        # * CREATE THE JSON INVOICE LINES FOR THE PROFORMA COM   *
        # * PROFORMA COM HAS NO INVOICE LINES, SO WE BUILD THEM  *
        # * BEFORE THE JSON IS CLEANED FOR PEPPOL                *
        # ********************************************************
        if sender == "petrolcave":
            if table_arg == "proforma_com":
                print("table_arg is proforma_com")
                # build invoice lines for proforma_com
                pfc_vat_cat_id = data.get("TaxCategory_ID", "S")
                pfc_vat_percent = (
                    data.get("TaxCategory_Percent", "0.00%").replace("%", "").strip()
                )
                pfc_vat_exemption_reason_code = data.get(
                    "TaxExemptionReasonCode", "no code given"
                )
                pfc_vat_exemption_reason = data.get(
                    "TaxExemptionReason", "no reason given"
                )
                invoice_lines = build_invoice_lines(
                    data,
                    vat_category=pfc_vat_cat_id,
                    vat_percentage=pfc_vat_percent,
                    unit_code="C62",
                    vat_exemption_reason_code=pfc_vat_exemption_reason_code,
                    vat_exemption_reason=pfc_vat_exemption_reason,
                )
                # print("invoice lines from proforma_com: ", json.dumps(invoice_lines, indent=2))
                data["Invoice lines"] = invoice_lines["Invoice_lines"]
                print("data after building invoice lines: ", json.dumps(data, indent=2))
            elif table_arg == "ad_hoc_invoice":
                print("table_arg is ad_hoc_invoice")

        # ****************************************************************
        # * THE JSON IS NOW COMPLETED, NOW CLEAN IT                      *
        # * SO IT MATCHES THE PEPPOL REQUIREMENTS                        *
        # * (eg. no currency symbols, dates in correct format, etc...)   *
        # ****************************************************************
        print("HOW DOES DATA LOOK LIKE BEFORE CLEANING: ", json.dumps(data, indent=2))
        cleaned_invoice_data = clean_json_for_peppol(data)
        print("CLEANED JSON: ", json.dumps(cleaned_invoice_data, indent=2))

        print(
            "**** START COLLECTING DATA FOR VAT CALCULATION AND ADDING THEM TO THE JSON ****"
        )
        # `data` is your original JSON dictionary
        invoice_lines = cleaned_invoice_data.get("Invoice_lines", [])

        # def parse_currency(value):
        #   return float(re.sub(r"[^\d.,]", "", value).replace(",", "").strip())

        # *************************************************************************
        # * COLLECT INVOICE LINES AND MAKE TOTALS PER TAX RATE (eg. TAXSUBTOTALS) *
        # *************************************************************************
        # def parse_currency(value):
        #    # Remove € and spaces, convert comma to dot, remove thousands separator
        #    cleaned = re.sub(r"[^\d,\.]", "", value).replace(".", "").replace(",", ".")
        #    return float(cleaned)

        if (
            sender != "do_not_process_subtotals"
        ):  # This is a placeholder to skip this section for testing, so now do it for all senders except "do_not_process_subtotals"
            # Use a dict to group subtotals by VAT rate and category ID
            totals_by_tax_category = defaultdict(
                lambda: {
                    "TaxableAmount": 0.0,
                    "TaxAmount": 0.0,
                    "TaxCategory_ID": "",
                    "TaxCategory_Percent": "",
                    "TaxExemptionReasonCode": "",
                    "TaxExemptionReason": "",
                    "TaxScheme_ID": "VAT",  # Fixed as you specified
                }
            )

            for line in invoice_lines:
                vat_percent = line.get("P_vat_percentage", 1.11)
                tax_cat_id = line.get("P_vat_category", "S")  # Default if missing
                ex_vat = line.get("Total_ex_VAT", 0)
                vat = line.get("Total_VAT", 0)
                print("vat and ex_vat", vat, "   ", ex_vat)
                tax_exemption_reason = line.get("vat_exemption_reason_code", "")

                key = (vat_percent, tax_cat_id)
                subtotal = totals_by_tax_category[key]
                subtotal["TaxableAmount"] += ex_vat
                subtotal["TaxAmount"] += vat
                subtotal["TaxCategory_ID"] = tax_cat_id
                subtotal["TaxCategory_Percent"] = vat_percent
                subtotal["TaxExemptionReason"] = tax_exemption_reason
            # Convert grouped data to a list
            cleaned_invoice_data["TaxSubtotal"] = [
                {
                    "TaxableAmount": f"{totals['TaxableAmount']:.2f}",
                    "TaxAmount": f"{totals['TaxAmount']:.2f}",
                    "TaxCategory_ID": totals["TaxCategory_ID"],
                    "TaxCategory_Percent": totals["TaxCategory_Percent"],
                    "TaxScheme_ID": totals["TaxScheme_ID"],
                    "TaxExemptionReason": totals["TaxExemptionReason"],
                }
                for totals in totals_by_tax_category.values()
            ]

        print(
            "**** END COLLECTING DATA FOR VAT CALCULATION AND ADDING THEM TO THE JSON ****"
        )

    except Exception as e:
        return jsonify({"error": f"Failed to normalize JSON: {str(e)}"}), 500

    # ***************************************************
    # * DECOMPOSE THE SUPPLIER AND CUSTOMER ADDRESSES   *
    # ***************************************************
    supplier_address_parts = split_supplier_address_for_template(
        cleaned_invoice_data["P_supplier_address"]
    )
    print("supplier_address_parts", json.dumps(supplier_address_parts, indent=2))
    print("______________________________________________")
    customer_address_parts = split_customer_address_for_template(
        cleaned_invoice_data["P_customer_address"]
    )
    print("customer_address_parts", json.dumps(customer_address_parts, indent=2))
    print("______________________________________________")

    # ******************************************************
    # * PEPPOL PROCESS MAPPING BASED ON INVOICE TYPECODE   *
    # ******************************************************
    # Determine the instance ID and process number based on the invoice type code
    if (
        cleaned_invoice_data["P_invoice_typecode"] == 380
    ):  # 380 = peppol commercial invoice
        instance_id = Instance_id_invoice
        process_nr = Process_nr_invoice
    elif cleaned_invoice_data["P_invoice_typecode"] == 381:  # 381 = peppol credit note
        instance_id = Instance_id_creditnote
        process_nr = Process_nr_creditnote
    elif (
        cleaned_invoice_data["P_invoice_typecode"] == 389
    ):  # 389 = peppol self billed invoice
        instance_id = Instance_id_Selfbilling
        process_nr = Process_nr_Selfbilling
    else:
        return jsonify({"error": "Unknown invoice type"}), 400

    print("data = ", json.dumps(data, indent=2))
    print("cleaned_invoice_data = ", json.dumps(cleaned_invoice_data, indent=2))

    # ********************************************************************
    # * NOW ASSEMBLE EVERYTHING IN THE JSON TO XML RENDERING             *
    # * based on the template and the invoice data and some other stuff  *
    # ********************************************************************
    xml_output = template.render(
        invoice=cleaned_invoice_data,
        paymentmeans_code="30",
        randomUUID=random_uuid,
        isoTimestamp=entry_timestamp,
        trial_participant_id="0007:9999004021",
        TEST_supplier_endpoint="9482348239847239874",
        TEST_customer_endpoint="FR23342",
        **supplier_address_parts,
        **customer_address_parts,
        doc_instance_id=instance_id,
        doc_process_nr=process_nr,
    )
    # **customer_address_parts means unpacking the dictionary into keyword arguments, is much quicker
    xml_output = xml_output.replace(
        "<cbc:TaxExemptionReason>-</cbc:TaxExemptionReason>", ""
    )
    xml_payload = xml_output.encode("utf-8")
    # print("xml_payload", xml_payload)
    print("______________________________________________")
    # return(xml_payload, 200, {'Content-Type': 'application/xml'})

    # ********************************************************************
    # * NOW UPLOAD THE FILE TO THE SELECTED FOLDER IN GOOGLE DRIVE       *
    # ********************************************************************
    print("Uploading XML to Google Drive...")

    folder_id = peppol_xml_files
    now = datetime.now(timezone.utc)
    file_timestamp = now.strftime("%Y%m%dT%H%M%S")
    file_timestamp_iso = now.isoformat()

    if sender == "petrolcave":
        print("sender is petrolcave!!!!!!")
        proforma_id = cleaned_invoice_data.get("Pro_Forma_out_ID", "")
        if proforma_id == "-" or not proforma_id:
            proforma_id = ""
        proforma_com_id = cleaned_invoice_data.get("Pro_Forma_Commissie_ID", "")
        if proforma_com_id == "-" or not proforma_com_id:
            proforma_com_id = ""
        ad_hoc_invoice_id = cleaned_invoice_data.get("Invoice_ID", "")
        if ad_hoc_invoice_id == "-" or not ad_hoc_invoice_id:
            ad_hoc_invoice_id = ""
        if proforma_id:
            filename = f"XML_PEPPOL_PROFORMA_{file_timestamp}_{proforma_id}.xml"
        elif proforma_com_id:
            filename = f"XML_PEPPOL_PROFORMA_COM_{file_timestamp}_{proforma_com_id}.xml"
        elif ad_hoc_invoice_id:
            filename = f"XML_PEPPOL_AD_HOC_{file_timestamp}_{ad_hoc_invoice_id}.xml"
        else:
            filename = f"XML_PEPPOL_NULL_{file_timestamp}_NO_ID.xml"
    else:
        print("sender is not petrolcave, using default = WHC")
        sb_invoice_id = cleaned_invoice_data.get("Sb_invoice_ID", "")
        invoice_id = cleaned_invoice_data.get("Invoice_ID", "")
        if invoice_id:
            filename = f"XML_PEPPOL_INV_{file_timestamp}_{invoice_id}.xml"
        elif sb_invoice_id:
            filename = f"XML_PEPPOL_SB_{file_timestamp}_{sb_invoice_id}.xml"
        else:
            filename = f"XML_PEPPOL_NULL_{file_timestamp}_NO_ID.xml"

    xml_content = xml_output
    # xml_content = '<root><message>Hello from memory!</message></root>'
    print("Uploading XML to Google Drive..., folder_id: ", folder_id)
    drive_service = authenticate_drive()
    upload_xml_memory(drive_service, filename, xml_content, folder_id)
    # XML is uploaded to Google Drive, now we can send it to the Tickstar API
    print("End uploading XML to Google Drive...for file:", filename)

    # ************************************************************
    # * NOW DO THE TICKSTAR STUFF                                *
    # ************************************************************
    print("Preparing to call Tickstar API...")
    print("XML payload to send to Tickstar API: ", xml_payload)
    token = load_token()
    response = call_tickstar_api(token, xml_payload)
    response_data = response.json()
    print("response_data", json.dumps(response_data, indent=2))
    tickstar_timestamp = now.isoformat()

    transaction_status_code = response.status_code
    transaction_id = response_data.get("transactionId", "")
    transaction_error_title = response_data.get("type", "")
    transaction_error_type = response_data.get("type", "")
    transaction_error_detail = response_data.get("detail", "")
    print("transaction_id: ", transaction_id)
    print("transaction_status: ", transaction_status_code)
    print("transaction_error_title: ", transaction_error_title)
    print("transaction_error_type: ", transaction_error_type)
    print("transaction_error_detail: ", transaction_error_detail)

    # *****************************************************************
    # * FINALLY UPDATE THE TICKSTAR RESPONS IN THE TRANSACTIONS TABLE *
    # *****************************************************************
    if sender == None:
        # *** DEFAULT = WHC SECTION ***
        # ** PREPARE DATA FOR APPSHEET CALL TO CREATE RECORD **
        invoice_id = cleaned_invoice_data.get("Invoice_ID", "")
        sb_invoice_id = cleaned_invoice_data.get("Sb_invoice_id", "")
        table = "peppol_transactions"
        folder_table = "peppol_xml_files"
        html_name_for_file = filename

        # ** prepare the url for the file saved in Google Drive **
        # Sample values (replace these with your actual values)
        app_name = "WiseHubCore-346984636"
        table_name = folder_table
        file_name = filename
        xml_url = (
            "https://www.appsheet.com/template/gettablefileurl"
            + "?appName="
            + quote(app_name)
            + "&tableName="
            + quote(table_name)
            + "&fileName="
            + quote(file_name)
        )
        xml_url_html = f'<a href="{xml_url}" target="_blank">{html_name_for_file}</a>'
        # ** NOW STORE THE TICKSTAR RESPONSE IN THE APPSHEET TABLE  **
        # ****************************************************************
        # table to address
        # table = "peppol_transactions"
        # Headers
        # none
        # JSON payload
        # `Add`: Adds a new row to the table.
        # `Delete`: Deletes existing rows from the table.
        # `Edit`: Updates existing rows in the table.
        # `Find`: Reads an existing row of the table.
        data = {
            "Action": "Add",
            "Properties": {
                "Locale": "en-US",
                "Location": "51.159133, 4.806236",
                "Timezone": "Central European Standard Time",
                #  "Selector": "Filter(SB invoices,[Customer]= SB20250003)",
                "UserSettings": {"User role": "Super Administrator"},
            },
            "Rows": [
                {
                    "invoice_id": str(invoice_id or ""),
                    "sb_invoice_id": str(sb_invoice_id or ""),
                    "p_transaction_status_code": str(transaction_status_code or ""),
                    "p_transaction_id": str(transaction_id or ""),
                    "p_transaction_error_title": str(transaction_error_title or ""),
                    "p_transaction_error_type": str(transaction_error_type or ""),
                    "p_transaction_error_detail": str(transaction_error_detail or ""),
                    "transaction_timestamp": str(tickstar_timestamp or ""),
                    "xml_file_creation_timestamp": str(file_timestamp_iso or ""),
                    "xml_url": str(xml_url or ""),
                    "xml_url_html": str(xml_url_html or ""),
                }
            ],
        }
        print("JSON FOR APPSHEET: ", json.dumps(data, indent=2))
        # *********************************************************
        response = post_data_to_appsheet_whc(table, data)
        # *********************************************************
        print("Status Code from add line to ", table, ":", response.status_code)
        if response.status_code != 200:
            print("Error: ", response.status_code)
            return jsonify({"error": "Failed to update AppSheet table"}), 500
        elif response.json() == "":
            print("Error: not able to Add row, please check keys", response.status_code)
            return jsonify({"Error: not able to Add row, please check keys"}), 200
        else:
            print("Success: ", response.status_code)
            data = response.json()
            print("JSON data", json.dumps(data, indent=2))

        # select sertain keys
        """if data:
            selected = {
                "invoice_nr": data[0]["invoice_nr"],
                "project_id": data[0]["project_id"],
                "sb_invoice_id": data[0]["sb_invoice_id"]
            }
            print(json.dumps(selected, indent=2))
        else:
            print("No data returned in response.")"""
    elif sender == "petrolcave":
        if table_arg == None:
            print("table_arg is empty")
        else:
            # *** PETROL CAVE SECTION ***
            # ** PREPARE DATA FOR APPSHEET CALL TO CREATE RECORD **
            proforma_id = cleaned_invoice_data.get("Pro_forma_out_ID", "")
            proforma_com_id = cleaned_invoice_data.get("Pro_forma_commissie_ID", "")
            ad_hoc_invoice_id = cleaned_invoice_data.get("Invoice_ID", "")
            print("ad_hoc_invoice_id: ", ad_hoc_invoice_id)
            print("proforma_id: ", proforma_id)
            print("proforma_com_id: ", proforma_com_id)
            table = "peppol_transactions"
            folder_table = "peppol_xml_files"
            html_name_for_file = filename

            # ** prepare the url for the file saved in Google Drive **
            # Sample values (replace these with your actual values)
            app_name = "PetrolCaveAutohandel-346984636"
            table_name = folder_table
            file_name = filename
            xml_url = (
                "https://www.appsheet.com/template/gettablefileurl"
                + "?appName="
                + quote(app_name)
                + "&tableName="
                + quote(table_name)
                + "&fileName="
                + quote(file_name)
            )
            xml_url_html = (
                f'<a href="{xml_url}" target="_blank">{html_name_for_file}</a>'
            )
            # ** NOW STORE THE TICKSTAR RESPONSE IN THE APPSHEET TABLE  **
            # ****************************************************************
            # table to address
            # table = "peppol_transactions"
            # Headers
            # none
            # JSON payload
            # `Add`: Adds a new row to the table.
            # `Delete`: Deletes existing rows from the table.
            # `Edit`: Updates existing rows in the table.
            # `Find`: Reads an existing row of the table.
            data = {
                "Action": "Add",
                "Properties": {
                    "Locale": "en-US",
                    "Location": "51.159133, 4.806236",
                    "Timezone": "Central European Standard Time",
                    # "Selector": "Filter(SB invoices,[Customer]= SB20250003)",
                    # "UserSettings": {  "User role":"Super Administrator" }
                },
                "Rows": [
                    {
                        "proforma_id": str(proforma_id or ""),
                        "proforma_com_id": str(proforma_com_id or ""),
                        "ad_hoc_invoice_id": str(ad_hoc_invoice_id or ""),
                        "p_transaction_status_code": str(transaction_status_code or ""),
                        "p_transaction_id": str(transaction_id or ""),
                        "p_transaction_error_title": str(transaction_error_title or ""),
                        "p_transaction_error_type": str(transaction_error_type or ""),
                        "p_transaction_error_detail": str(
                            transaction_error_detail or ""
                        ),
                        "transaction_timestamp": str(tickstar_timestamp or ""),
                        "xml_file_creation_timestamp": str(file_timestamp_iso or ""),
                        "xml_url": str(xml_url or ""),
                        "xml_url_html": str(xml_url_html or ""),
                    }
                ],
            }
            print("JSON FOR APPSHEET: ", json.dumps(data, indent=2))
            # *********************************************************
            response = post_data_to_appsheet_pc(table, data)
            # *********************************************************
            print("Status Code from add line to ", table, ":", response.status_code)
            if response.status_code != 200:
                print("Error: ", response.status_code)
                return jsonify({"error": "Failed to update AppSheet table"}), 500
            elif response.json() == "":
                print(
                    "Error: not able to Add row, please check keys",
                    response.status_code,
                )
                return jsonify({"Error: not able to Add row, please check keys"}), 200
            else:
                print("Success: ", response.status_code)
                data = response.json()
                print("JSON data", json.dumps(data, indent=2))

            # select sertain keys
            """if data:
                selected = {
                    "invoice_nr": data[0]["invoice_nr"],
                    "project_id": data[0]["project_id"],
                    "sb_invoice_id": data[0]["sb_invoice_id"]
                }
                print(json.dumps(selected, indent=2))
            else:
                print("No data returned in response.")"""
    elif sender == "WBC":
        print("sender is WBC")
    else:
        print("sender is unknown")
    # Send push notification

    return (
        jsonify(
            {
                "project_id": project_id,
                "message": "XML sent successfully",
                "response": response.json(),
            }
        ),
        200,
    )
