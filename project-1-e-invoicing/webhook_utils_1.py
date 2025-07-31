import requests
import urllib.parse

WHC_app_id = "397f3d50-89dc-46bb-b912-e52499e9b2f1"
WHC_app_access_key = "V2-ggEMV-znIzP-zanfl-m6Sxr-zre0X-55Mkm-oOMQM-qfaZ6"
PC_app_id = "aa5cdeac-1127-4194-b629-1393b8186d6d"
PC_app_access_key= "V2-h4VdX-fPQ53-EW8s0-JWxNk-U8v6K-ctajU-nVhiP-wJ64M"
carbone_authorisation_key = 'test_eyJhbGciOiJFUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIxMDMyNTAyMzM5Mjg3MTIwNzQxIiwiYXVkIjoiY2FyYm9uZSIsImV4cCI6MjM5NDc5OTA3MCwiZGF0YSI6eyJ0eXBlIjoidGVzdCJ9fQ.AeNwsovwdLdyPAqJ16IjPSOjImuv5Yj0y8mdKJDApZlP0j3XD1T90x1wQSL5AkWU42d6iC3dWOLAjdn9zCUBHQWeAMkP46CN_pMj2NT3acUU7TSIGI1U6a5dRcNXeE4t_WLguijWVCm33Nkus1-ap_bp7GL84eMnpvCHXJ8VVUrqt2tS'
#*
def send_push_notification(message):
    url = "https://www.pushsafer.com/api?k=AYIor8gFjJ5zb1k0Y7Pv&d=17595&m=ryan_test"
    response = requests.get(url)

    if response.status_code == 200:
        return "Notification sent successfully!"
    else:
        return f"Failed to send notification. Status code: {response.status_code}, Response: {response.text}"
#**********************************************************
def get_url_whc(table):
    encoded_table = urllib.parse.quote(table)
    url = f"https://api.appsheet.com/api/v2/apps/{WHC_app_id}/tables/{encoded_table}/Action?applicationAccessKey={WHC_app_access_key}"
    return url

#**********************************************************
def get_url_pc(table):
    encoded_table = urllib.parse.quote(table)
    url = f"https://api.appsheet.com/api/v2/apps/{PC_app_id}/tables/{encoded_table}/Action?applicationAccessKey={PC_app_access_key}"
    return url


#*** WISEHUB CORE *******************************************************
def post_data_to_appsheet_whc(table, data):
    url_WHC = get_url_whc(table)
    print("URL:", url_WHC)
    response = requests.post(url_WHC, json=data)
    return response

#***PETROl CAVE *******************************************************
def post_data_to_appsheet_pc(table, data):
    url_PC = get_url_pc(table)
    print("URL:", url_PC)
    response = requests.post(url_PC, json=data)
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