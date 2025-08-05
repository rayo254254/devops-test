
import re
from datetime import datetime

#*****************************************************
def capitalize_keys(data):
    if isinstance(data, dict):
        return {
            key[0].upper() + key[1:] if key else key: capitalize_keys(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [capitalize_keys(item) for item in data]
    else:
        return data
#*****************************************************
def replace_empty_values(data):
    if isinstance(data, dict):
        return {
            key: replace_empty_values(value) if isinstance(value, (dict, list)) else ("-" if value in ("", None) else value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [replace_empty_values(item) for item in data]
    else:
        return "-" if data in ("", None) else data
#*****************************************************
def clean_money_in_json(data):
    if isinstance(data, dict):
        return {k: clean_money_in_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_money_in_json(item) for item in data]
    elif isinstance(data, str):
        # Match and clean Euro-formatted money strings like "€1,752.66"
        match = re.match(r"^€?\s*[\d,]+\.\d{2}$", data.strip())
        if match:
            clean = data.replace("€", "").replace(",", "").strip()
            return clean
        return data
    else:
        return data
#*****************************************************
def extract_vat_percentage(vat_string):
    try:
        return int(float(vat_string.strip().replace("%", "")))
    except Exception:
        return None  # or fallback value like 0
#*****************************************************    
def clean_vat_in_json(data):
    if isinstance(data, dict):
        return {k: clean_vat_in_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_vat_in_json(item) for item in data]
    elif isinstance(data, str):
        match = re.match(r"^\d+(\.\d+)?%$", data.strip())
        if match:
            return int(float(data.strip().replace("%", "")))
        return data
    else:
        return data
#*****************************************************
def split_supplier_address_for_template(address):
    try:
        parts = [part.strip() for part in address.split(",")]

        if len(parts) == 3:
            street_and_nr, postal_city, country = parts
        elif len(parts) == 2:
            street_and_nr, postal_city = parts
            country = ""  # fallback if country is missing
        else:
            raise ValueError("Unexpected address format")

        postal_parts = postal_city.strip().split(" ", 1)
        postalcode = postal_parts[0]
        city = postal_parts[1] if len(postal_parts) > 1 else ""

        return {
            "P_supplier_address_streetname": street_and_nr,
            "P_supplier_address_postalzone": postalcode,
            "P_supplier_address_city": city,
            "P_supplier_address_country": country
        }


    except Exception as e:
        return {
            "P_supplier_address_streetname": "",
            "P_supplier_address_postalzone": "",
            "P_supplier_address_city": "",
            "P_supplier_address_country": "",
            "error": f"Could not parse address: {str(e)}"
        }
#*****************************************************
def split_customer_address_for_template(address):
    try:
        parts = [part.strip() for part in address.split(",")]

        if len(parts) == 3:
            street_and_nr, postal_city, country = parts
        elif len(parts) == 2:
            street_and_nr, postal_city = parts
            country = ""  # fallback if country is missing
        else:
            raise ValueError("Unexpected address format")

        postal_parts = postal_city.strip().split(" ", 1)
        postalcode = postal_parts[0]
        city = postal_parts[1] if len(postal_parts) > 1 else ""
        return {
            "P_customer_address_streetname": street_and_nr,
            "P_customer_address_postalzone": postalcode,
            "P_customer_address_city": city,
            "P_customer_address_country": country
        }

    except Exception as e:
        return {
            "P_customer_address_streetname": "",
            "P_customer_address_postalzone": "",
            "P_customer_address_city": "",
            "P_customer_address_country": "",
            "error": f"Could not parse address: {str(e)}"
        }
#*****************************************************
def normalize_keys(data):
    if isinstance(data, dict):
        return {
            key.replace(" ", "_"): normalize_keys(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [normalize_keys(item) for item in data]
    else:
        return data
#*****************************************************
#** FUNCTION to make the dates in the JSON normalized **
def reformat_dates_in_json(data, input_format="%m/%d/%Y", output_format="%d/%m/%Y"):
    """
    Recursively reformats date strings in a nested JSON-like structure.
    
    :param data: The JSON-like structure (dict/list)
    :param input_format: The expected format of the input date strings
    :param output_format: The desired format of the output date strings
    :return: A new structure with reformatted date strings
    """
    if isinstance(data, dict):
        return {
            key: reformat_dates_in_json(value, input_format, output_format)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [
            reformat_dates_in_json(item, input_format, output_format)
            for item in data
        ]
    elif isinstance(data, str):
        try:
            dt = datetime.strptime(data, input_format)
            return dt.strftime(output_format)
        except ValueError:
            return data  # Not a date string, return as-is
    else:
        return data  # Return all non-string values unchanged
#*****************************************************
def clean_json_data_for_carbone(data):
    """
    Cleans the JSON data by capitalizing keys, replacing empty values, and normalizing keys and reformatting the dates to Peppol requirements.
    
    :param data: The JSON data to clean
    :return: The cleaned JSON data
    """
    data = capitalize_keys(data)
    #print("data after capitalize_keys",data)
    data = replace_empty_values(data)
    #print("data after replace_empty_values",data)
    data = clean_money_in_json(data)
    #print("data after clean_money_in_json",data)
    data = clean_vat_in_json(data)
    #print("data after clean_vat_in_json",data)
    #data = split_supplier_address_for_template(data.get("supplier_address", ""))
    #print("data after split_supplier_address_for_template",data)
    data = normalize_keys(data)
    #print("data after normalize_keys",data)
    data = reformat_dates_in_json(data, "%m/%d/%Y", "%Y-%m-%d")
    #print("data after reformat_dates_in_json",data)
    return data
#*****************************************************
def format_number_eu(value):
    """Convert float to EU formatted string: 11560.00 → '11.560,00'"""
    s = f"{value:,.2f}"              # '11,560.00'
    s = s.replace(",", "X").replace(".", ",").replace("X", " ")
    return s

def try_convert_string_number(value):
    """Try to convert a string to a number, format if successful."""
    try:
        # Try to parse as float
        num = float(value)
        return format_number_eu(num)
    except (ValueError, TypeError):
        return value  # Leave non-numeric strings untouched

def convert_string_numbers_in_json(data):
    """Recursively convert numeric strings in JSON-like structure to EU format."""
    if isinstance(data, dict):
        return {k: convert_string_numbers_in_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_string_numbers_in_json(item) for item in data]
    elif isinstance(data, str):
        return try_convert_string_number(value=data)
    else:
        return data  # Leave other types untouched (e.g., bool, None)
#*****************************************************
