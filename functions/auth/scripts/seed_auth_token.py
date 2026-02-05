import json
import os
from google.cloud import firestore_v1
from cryptography.fernet import Fernet


SECRET_KEY = os.environ.get("SECRET_KEY")
SAMPLE_AUTH_TOKEN = {
    "realmId": "123189227149329",
    "id_token": "",
    "createdAt": 1770323175692,
    "expires_in": 3600,
    "token_type": "bearer",
    "access_token": "eyJhbGciOiJkaXIiLCJlbmMiOiJBMTI4Q0JDLUhTMjU2IiwieC5vcmciOiABCDJ9..656ABf59befbbf030f9cdd.\
        omMyLhBDFtK948nmDu9ksHChYbPncTv0OAjQgxQUcFcsejRtyMpFLr0WHB2OZWn8GGDnnyIuHDE9XTR_S5x8VVpIkssWjfAVnmnjpgP\
        -JAs2gfL13zA3rJLkmkmYKxsSaHmYmaFSE56jLQFoAwQST4WyGsasJw7ZjvrnV6szypMKqsVaSb2AwEv4R3ugmTuafI_\
        7Mtn6ID83I3bvyle1wNVvCcwbAjt922LaeeHyI1P3u12eYG7JnWZS-n3tGgjSdJ7J3Yc60fNnD3jjdgd4gWvzFya0Cg3W\
        rbg9rCTP3B5OKrwaNMxQLOnFpOeu4kN9y1IBzCiI5VlWNtTwSSl_oYT1XtKD9fJOSHGhqCGBqj8o5LuiFIp_sb312OMpsX\
        6YltdAW0C-slZrTnUAlMoiW_s0EdY3up2B1ml8v8UO7qkkKkpliVmbfFzhPwCZrvIbLITfO7e9hnyxuIrFWwSCFq5K4itN1\
        Odh8vIGFxgKHhBZAQYsSORDOh19XDQwhOdSAsFgIxruhPrJofp_JxlEr3ihjhXbQHKhAGvOXPPawNjYpWaS8Y1eZiSllqwgk\
        uvk.gqWTaFP-WRF8Q_KGBIsngw",
    "refresh_token": "RT1-206-H0-1770282300mebf8x2oafhqqigp08r9",
    "x_refresh_token_expires_in": 8643837,
}


def encrypt_auth_token(token, key):
    """Encrypts the auth token dictionary using Fernet."""
    f = Fernet(key)
    token_json = json.dumps(token)
    return f.encrypt(token_json.encode())


def seed_auth_token():
    """Seeds the encrypted auth token to Firestore."""
    encrypted_data = encrypt_auth_token(SAMPLE_AUTH_TOKEN, SECRET_KEY.encode())

    db = firestore_v1.Client()
    doc_ref = db.collection("auth_tokens").document(SAMPLE_AUTH_TOKEN["realmId"])

    doc_ref.set(
        {
            "token": encrypted_data.decode("utf-8"),
            "created_at": SAMPLE_AUTH_TOKEN["createdAt"],
            "expires_in": SAMPLE_AUTH_TOKEN["expires_in"],
            "x_refresh_token_expires_in": SAMPLE_AUTH_TOKEN["x_refresh_token_expires_in"],
        }
    )
    print(
        f"Successfully seeded encrypted auth token for realm {SAMPLE_AUTH_TOKEN['realmId']}"
    )


if __name__ == "__main__":
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "yoco-logistics-intergration"

    seed_auth_token()
