from google.cloud import secretmanager

def get_secret(secret_id, project_id):
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Return the decoded payload.
    return response.payload.data.decode("UTF-8")


PROJECT_ID = "764652156242"
SECRET_ID = "Appkey_A1"

secret_value = get_secret(SECRET_ID, PROJECT_ID)
print("My secret value:", secret_value)