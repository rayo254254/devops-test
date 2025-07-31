import json
import re

def clean_currency_string(value):
    """
    Cleans a string representation of a price, removing currency symbols,
    handling EU/US number formats (prioritizing EU interpretation as per request),
    and converting it to a float.

    Args:
        value (str): The input string that might represent a currency amount.

    Returns:
        float: The cleaned numerical value as a float if successfully parsed.
        str: The original string if it cannot be parsed as a currency amount.
        Any: The original value if it's not a string.
    """
    if not isinstance(value, str):
        return value # Return original value if it's not a string (e.g., int, float, bool, None)

    # --- Initial Check & Simple Number Handling ---
    # Define common currency symbols for detection
    currency_symbols_patterns = r'[€$£¥₹₽₴฿]' # Expanded for more common symbols

    # If the string does not contain digits and no obvious currency symbol,
    # it's unlikely to be a price we need to parse with complex logic.
    # However, it might be a simple number like "50" or "100.25".
    if not re.search(r'\d', value) and not re.search(currency_symbols_patterns, value):
        try:
            # Attempt to convert to float directly for simple cases (e.g., "50", "100.25", "1,234" treated as 1.234)
            # For "1,234" this might result in 1.0 depending on locale, which isn't what we want for prices.
            # So, we'll let the more robust logic below handle numeric parsing, even for plain numbers.
            # This makes the parsing consistent for all potential numbers.
            pass 
        except ValueError:
            return value # Not a recognized number or price string, return original

    # --- Cleaning: Remove Currency Symbols and Normalize Spaces ---
    # Remove common currency symbols and strip leading/trailing whitespace
    cleaned_value = re.sub(currency_symbols_patterns, '', value).strip()
    # Remove spaces used as thousands separators (e.g., "2 600,23")
    cleaned_value = cleaned_value.replace(' ', '') 

    # Flag to remember if the original string contained a currency symbol.
    # This helps in ambiguous cases like "2.600".
    was_currency_string = bool(re.search(currency_symbols_patterns, value))

    # --- Format Detection and Conversion Logic ---
    # Determine number format based on separator presence and position
    last_comma_idx = cleaned_value.rfind(',')
    last_dot_idx = cleaned_value.rfind('.')
    
    # Case 1: Contains both '.' and ',' (e.g., '1.234,56' or '1,234.56')
    if last_comma_idx != -1 and last_dot_idx != -1:
        if last_comma_idx > last_dot_idx:
            # EU format: comma is decimal, dot is thousands (e.g., '1.234,56')
            cleaned_value = cleaned_value.replace('.', '')  # Remove thousands separators
            cleaned_value = cleaned_value.replace(',', '.')  # Replace decimal separator
        else:
            # US format: dot is decimal, comma is thousands (e.g., '1,234.56')
            cleaned_value = cleaned_value.replace(',', '')  # Remove thousands separators
            # Dot is already the standard decimal for float conversion
    
    # Case 2: Contains only ',' (e.g., '123,45')
    elif last_comma_idx != -1:
        # EU decimal format: comma is decimal
        cleaned_value = cleaned_value.replace(',', '.')

    # Case 3: Contains only '.' (most ambiguous case: '123.45' vs '1.234')
    elif last_dot_idx != -1:
        # Per the prompt's strong EU bias ("2600,23, not 2.600,23"),
        # if the original string had a currency symbol OR it looks like a common EU thousands pattern,
        # we treat the dot as a thousands separator and remove it.
        # This regex ensures we only remove dots if they are clearly structured as thousands separators (xxx.xxx).
        # We also check if it's not a standard decimal (i.e., not a single dot followed by 1-2 digits, for example).
        if re.fullmatch(r'\d{1,3}(?:\.\d{3})+', cleaned_value) and not re.fullmatch(r'\d+\.\d{1,2}', cleaned_value):
            cleaned_value = cleaned_value.replace('.', '')
        # Otherwise (e.g., "123.45", "1.23", or just a number like "1.23" without currency), 
        # assume it's a US decimal and the dot should remain. No action needed here.
    
    # Handle cases where value might be like "50" or "100.25" without currency symbols
    # If after all cleaning, it's just a number string without currency info, try to convert.
    # The previous `if not re.search(...)` block was a bit too aggressive; a plain number needs to go through parsing too.

    # --- Final Conversion ---
    try:
        return float(cleaned_value)
    except ValueError:
        # If, after all cleaning, it still cannot be converted to a float,
        # return the original string to avoid data loss.
        return value 

def process_json_recursively(data):
    """
    Recursively processes a JSON-like structure (dict or list).
    Applies the `clean_currency_string` function to all string values found.

    Args:
        data (dict | list | any): The JSON data to process.

    Returns:
        dict | list | any: The processed JSON data with currency strings converted to floats.
    """
    if isinstance(data, dict):
        # If it's a dictionary, recursively process each value
        return {key: process_json_recursively(value) for key, value in data.items()}
    elif isinstance(data, list):
        # If it's a list, recursively process each element
        return [process_json_recursively(element) for element in data]
    elif isinstance(data, str):
        # If it's a string, attempt to clean and convert it
        return clean_currency_string(data)
    else:
        # For other types (int, float, bool, None), return as-is
        return data

# --- Example Usage ---
json_data = {
    "Invoice ID": "INV-2025-00123",
    "Customer ID": "CUST-00987",
    "Invoice Date": "2025-06-20",
    "Due Date": "2025-07-20",
    "Currency": "EUR",
    "Total invoice lines ex VAT": "€ 2.170,00", # EU format with thousands dot and comma decimal
    "Total invoice lines VAT": "€ 409,50",   # EU format with comma decimal
    "Total invoice lines incl VAT": "€ 2.579,50", # EU format
    "P_invoice_typecode": "380",
    "TaxExemptionReasonCode": "",
    "Invoice lines": [
        {
            "Invoice Line ID": "30ef4208",
            "Invoice Line Description": "Nieuwe banden",
            "Note": "Special price",
            "Units": "stuks",
            "Quantity": "2",                 # Plain integer string
            "Unit fee": "€ 475,00",          # EU format
            "Total ex VAT": "€ 950,00"       # EU format
        },
        {
            "Invoice Line ID": "45g34h2k",
            "Description": "Service fee",
            "Amount": "$ 1,000.55",          # US format (comma thousands, dot decimal)
            "Another Fee": "$ 123.45"        # US format (dot decimal only)
        },
        {
            "Invoice Line ID": "test_cases",
            "Price (EU thousands)": "£ 2.600",   # Ambiguous, should be 2600.0 per prompt's bias
            "Cost": "100.25",                # Simple US decimal, no currency
            "Flat Fee": "50",                # Plain integer string
            "Zero Amount": "€ 0,00",         # Zero EU format
            "Big Number": "€ 12.345.678,90", # Complex EU format
            "Large US Number": "$ 9,876,543.21", # Complex US format
            "Invalid Price": "ABC € 100",    # Remains string as invalid number
            "Another Invalid": "No Price",   # Remains string
            "Empty String": "",              # Remains empty string
            "Negative Price": "-€ 15,50",    # Handles negative values (after stripping symbol)
            "No Space Thousands (EU)": "€ 2500,00", # EU standard
            "Space Thousands (EU)": "€ 2 500,00",  # EU with space thousands
            "Dot Thousands, no decimal (EU)": "€ 2.500", # Dot thousands without decimal (should be 2500.0)
            "Plain number EUR": "2.500,00",  # Plain numbers matching EU format
            "Plain number US": "2,500.00"    # Plain numbers matching US format
        }
    ],
    "Nested Info": {
        "Subtotal": "€ 2.000,00",
        "Discount Applied": "$ 50.75",
        "Admin Fee": "15.00" # Plain number, should still convert to float
    }
}

# Process the JSON data
processed_json_data = process_json_recursively(json_data)

# Pretty print the result
print(json.dumps(processed_json_data, indent=2))
