from datetime import datetime
from dateutil import parser
from dateutil.tz import tzutc
from firebase_admin import initialize_app
from firebase_functions import https_fn
from firebase_functions.options import set_global_options
from google.cloud import firestore_v1
import logging
import json

set_global_options(region="africa-south1")

initialize_app()


def parse_date(value) -> datetime:
    if not isinstance(value, (str, datetime)):
        raise TypeError('parse_date() first argument must be either type str or datetime')
    if isinstance(value, str):
        value = parser.parse(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tzutc())
    return value


@https_fn.on_request(max_instances=10)
def get_shipments(request: https_fn.Request) -> https_fn.Response:
    """
    Mock and external endpoint for retrieving shipment status updates.
    """
    last_updated_param = request.args.get("last_updated", None)

    if not last_updated_param:
        return https_fn.Response(status=200, response=json.dumps({"data": []}), content_type="application/json")

    try:
        last_updated = parse_date(last_updated_param)
    except (ValueError, TypeError):
        message = "Invalid date format. Use ISO 8601 (e.g., 2024-01-01T00:00:00Z)"
        return https_fn.Response(status=400, response=json.dumps({"error": message}), content_type="application/json")

    try:
        db = firestore_v1.Client()
        docs = db.collection("shipments").stream()

        shipments = [doc.to_dict() for doc in docs if parse_date(doc.to_dict().get("last_updated")) >= last_updated]

        return https_fn.Response(status=200, response=json.dumps({"data": shipments}), content_type="application/json")
    except Exception as e:
        logging.error(f"Error getting shipments: {e}")
        return https_fn.Response(f"Internal Server Error: {str(e)}", status=500)
