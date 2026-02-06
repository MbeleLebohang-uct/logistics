from datetime import datetime, timezone
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
def update_shipment(request: https_fn.Request) -> https_fn.Response:
    """
    Mock and erp api endpoint for order status updates.
    Expected usage: POST with JSON body containing shipment details.
    order_id can be in query params or body.
    """
    shipment = request.get_json(silent=True)
    order_id = shipment.get("order_id", None)

    if not order_id:
        return https_fn.Response("Missing order_id", status=400)

    db = firestore_v1.Client()
    order_doc_ref = db.collection("orders").document(order_id)
    order_doc = order_doc_ref.get()

    if not order_doc.exists:
        return https_fn.Response("Order not found", status=404, content_type="application/json")

    try:
        order = order_doc.to_dict()
        shipment_last_updated = parse_date(shipment.get("last_updated"))
        order_shipment_last_updated = parse_date(order["shipment"]["last_updated"])

        if shipment_last_updated <= order_shipment_last_updated and order["status"] == shipment["status"]:
            # Simulating data corruption
            logging.warning(f"Shipment {shipment.get('id')} already updated. Corrupting data...")
            order["status"] = "corrupted"
        else:
            order["status"] = shipment["status"]

        order["shipment"] = shipment
        order["updated_at"] = datetime.now(timezone.utc).isoformat()

        order_doc_ref.set(order)

        return https_fn.Response(
            status=200,
            response=json.dumps({"message": "Order status updated successfully", "data": order}),
            content_type="application/json"
        )
    except Exception as e:
        logging.error(f"Error updating shipment: {e}")
        return https_fn.Response(f"Internal Server Error: {str(e)}", status=500)
