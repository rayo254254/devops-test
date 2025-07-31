from authentication_utils import save_token
import uuid
import requests
from flask import request, Response, jsonify

def call_tickstar_api(token, xml_payload):
    print("Starting call_tickstar_api function...")
    if token:
        print("Using cached token:", token)
        access_token=token
    else:
        print("Fetching new token...")
        client_id = "trial+021@tickstar.com"
        client_secret = "mXb94ubjsoyCXoLWyKNVRU9aTv"
        #client_id = get_secret("Tickstar_user_name_for_test", project_id)
        #client_secret = get_secret("Tickstar_password_for_test", project_id)
        myuuid = uuid.uuid4()
        print("UUID: ", myuuid)
        # Tickstar OAuth2 details
        token_url = "https://auth.test.galaxygw.com/oauth2/token"  # replace with the actual URL

        # Step 1: Request access token
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "transaction-api"}

        try:
            print("Fetching new token...")
            response = requests.post(token_url, data=payload)
            response.raise_for_status()  # throws an error if the request failed
            access_token = response.json().get("access_token")
            print("*********TOKEN: ",access_token, "RESPONSE STATUS CODE: ", response.status_code)
            token = access_token
            save_token(token, 3600)  # 1 hour lifetime
        except requests.exceptions.HTTPError as http_err:
            if response.status_code == 401:
                # Token is likely expired or invalid
                return jsonify({"error": "Unauthorized: token invalid or expired"}), 401
            elif response.status_code == 403:
                # Token is valid but user is forbidden (wrong scopes, etc.)
                return jsonify({"error": "Forbidden: access denied"}), 403
            else:
                return jsonify({"error": f"HTTP error: {http_err}"}), 500

        except requests.exceptions.RequestException as req_err:
                return jsonify({"error": f"Request failed: {req_err}"}), 500

        except Exception as e:
                return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
    # Step 2: Use the access token in API requests
    headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json",
    "Accept": "application/json"
    }
    try:
        print("######################################################################")
        print("HEADERS: ",headers)
        api_url_ping = "https://api.test.galaxygw.com/transaction-api/1.0/secure-ping"  # example API endpoint
        response1 = requests.get(api_url_ping, headers=headers)
        response1.raise_for_status()  # throws an error if the request failed
        print("######################################################################")   
        print("RESPONS FROM SECURe PING",response1.status_code)
    except requests.exceptions.HTTPError as http_err:
        if response1.status_code == 401:
            # Token is likely expired or invalid
            return jsonify({"error": "Unauthorized: token invalid or expired"}), 401
        elif response1.status_code == 403:
            # Token is valid but user is forbidden (wrong scopes, etc.)
            return jsonify({"error": "Forbidden: access denied"}), 403
        else:
            return jsonify({"error": f"HTTP error: {http_err}"}), 500

    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": f"Request failed: {req_err}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    try:
        api_url_webhooks = "https://api.test.galaxygw.com/transaction-api/1.0/transactions/webhooks"  # example API endpoint
        response2 = requests.get(api_url_webhooks, headers=headers)
        response2.raise_for_status()  # throws an error if the request failed
        print("######################################################################")
        print("RESPONS TRANSACTION WEBHOOKS",response2.json())
    except requests.exceptions.HTTPError as http_err:
        if response2.status_code == 401:
            # Token is likely expired or invalid
            return jsonify({"error": "Unauthorized: token invalid or expired"}), 401
        elif response2.status_code == 403:
            # Token is valid but user is forbidden (wrong scopes, etc.)
            return jsonify({"error": "Forbidden: access denied"}), 403
        else:
            return jsonify({"error": f"HTTP error: {http_err}"}), 500

    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": f"Request failed: {req_err}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

    try: 
        api_url_transactions_peppol = "https://api.test.galaxygw.com/transaction-api/1.0/transactions?networkType=PEPPOL"  # example API endpoint
        response_transactions = requests.post(api_url_transactions_peppol, data=xml_payload, headers=headers)

        response_transactions.raise_for_status()  # throws an error if the request failed
        print("######################################################################")
        print("RESPONS TRANSACTION SUBMIT XML",response_transactions.json())
    except requests.exceptions.HTTPError as http_err:
        if response_transactions.status_code == 401:
            # Token is likely expired or invalid
            return jsonify({"error": "Unauthorized: token invalid or expired"}), 401
        elif response_transactions.status_code == 403:
            # Token is valid but user is forbidden (wrong scopes, etc.)
            return jsonify({"error": "Forbidden: access denied"}), 403
        else:
            return jsonify({"error": f"HTTP error: {http_err}"}), 500

    except requests.exceptions.RequestException as req_err:
        return jsonify({"error": f"Request failed: {req_err}"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

        
    return response_transactions