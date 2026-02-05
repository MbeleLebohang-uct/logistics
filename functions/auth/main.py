import json
import time
from cryptography.fernet import Fernet
from firebase_admin import initialize_app
from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from firebase_functions.params import StringParam
from google.cloud import firestore_v1

set_global_options(region="africa-south1")

initialize_app()


SECRET_KEY = StringParam("SECRET_KEY").value
REALM_ID = StringParam("REALM_ID").value


def encrypt_auth_token(token, key):
    """Encrypts the auth token dictionary using Fernet."""
    f = Fernet(key)
    return f.encrypt(json.dumps(token).encode())


def decrypt_auth_token(token, key):
    """Decrypts the auth token dictionary using Fernet."""
    f = Fernet(key)
    return json.loads(f.decrypt(token.encode()).decode())


def get_auth_token(realm_id: str) -> dict:
    """Gets the auth token for a given realm ID."""
    db = firestore_v1.Client()
    doc_ref = db.collection("auth_tokens").document(realm_id)
    doc = doc_ref.get()
    return doc.to_dict()


def is_token_expired(token: dict) -> bool:
    """Checks if the auth token is expired."""
    epoch_now = round(time.time() * 1000)
    expires_at = token.get("expires_in") + token.get("createdAt")
    return expires_at < epoch_now


def refresh_auth_token(token: dict) -> dict:
    """Simulates the refresh of the auth token."""

    token['createdAt'] = round(time.time() * 1000)

    db = firestore_v1.Client()
    doc_ref = db.collection("auth_tokens").document(REALM_ID)

    encrypted_data = encrypt_auth_token(token, SECRET_KEY.encode())
    doc_ref.set(
        {
            "token": encrypted_data.decode("utf-8"),
            "created_at": token["createdAt"],
            "expires_in": token["expires_in"],
            "x_refresh_token_expires_in": token["x_refresh_token_expires_in"],
        }
    )
    return token


@https_fn.on_request(max_instances=10)
def authenticate(request: https_fn.Request) -> https_fn.Response:
    print(f"Authenticating for realm {REALM_ID}")
    data = get_auth_token(REALM_ID)

    encrypted_token = data.get("token")

    print(f"Token: {encrypted_token[:8]}...{encrypted_token[-8:]}")

    token = decrypt_auth_token(encrypted_token, SECRET_KEY.encode())

    if is_token_expired(token):
        print(f"Token expired for realm {REALM_ID}")
        token = refresh_auth_token(token)

    return https_fn.Response(status=200, response=json.dumps({"token": token}), content_type="application/json")
