from datetime import datetime
from enum import Enum
from dateutil import parser
from dateutil.tz import tzutc
import requests

from firebase_functions import pubsub_fn
from firebase_functions.options import set_global_options
from firebase_admin import initialize_app
from google.cloud import firestore_v1
from firebase_functions.params import StringParam

set_global_options(region="europe-west3", max_instances=10)

initialize_app()

API_KEY = "dummy-api-key"
ERP_API_BASE_URL = StringParam("ERP_API_BASE_URL").value
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


class ProcessingStatus(Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


def parse_date(value) -> datetime:
    if not isinstance(value, (str, datetime)):
        raise TypeError('parse_date() first argument must be either type str or datetime')
    if isinstance(value, str):
        value = parser.parse(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tzutc())
    return value


def get_event_message_payload(event: pubsub_fn.CloudEvent[pubsub_fn.MessagePublishedData]) -> dict | None:
    try:
        message = event.data.message.json
        print(f"Message: {message}")
        return message
    except Exception as e:
        print(f"Error decoding message: {e}")
        return None


@firestore_v1.transactional
def acquire_lock(transaction, doc_ref, shipment_id, updated_at_raw):
    snapshot = doc_ref.get(transaction=transaction)
    if snapshot.exists:
        data = snapshot.to_dict()
        status = data.get("status")

        if status != ProcessingStatus.FAILED.value:
            return False

    transaction.set(
        doc_ref,
        {
            "status": ProcessingStatus.PROCESSING.value,
            "created_at": firestore_v1.SERVER_TIMESTAMP,
            "shipment_id": shipment_id,
            "updated_at": updated_at_raw,
            "retry_count": firestore_v1.Increment(1),
        },
        merge=True,
    )
    return True


@pubsub_fn.on_message_published(topic="erp-order-status-update-queue")
def order_status_update_consumer(
    event: pubsub_fn.CloudEvent[pubsub_fn.MessagePublishedData],
) -> None:
    """
    Triggered by a Pub/Sub message. Pushes the update to the ERP system
    idempotently using a locking mechanism.
    """
    print(f"Consumer triggered by Pub/Sub message: {event.id}")

    shipment = get_event_message_payload(event)
    if shipment is None:
        return

    shipment_id = shipment.get("id")
    last_updated = parse_date(shipment.get("last_updated"))

    db = firestore_v1.Client()
    event_key = f"{shipment_id}-{round(last_updated.timestamp() * 1000)}"
    processed_ref = db.collection("order-status-updates").document(event_key)

    transaction = db.transaction()
    if not acquire_lock(transaction, processed_ref, shipment_id, last_updated):
        print(f"Event {event_key} already processed or in progress. Skipping.")
        return

    print(f"Processing shipment {shipment_id} last_updated {last_updated}")
    try:
        response = requests.post(ERP_API_BASE_URL, json=shipment, headers=HEADERS, timeout=30)
        response.raise_for_status()
        print(f"Successfully pushed to ERP: {response.status_code}")

        processed_ref.update({"status": "COMPLETED", "processed_at": firestore_v1.SERVER_TIMESTAMP})
    except Exception as e:
        print(f"Failed to push to ERP: {e}")
        processed_ref.update(
            {"status": ProcessingStatus.FAILED.value, "error": str(e), "processed_at": firestore_v1.SERVER_TIMESTAMP}
        )
        raise e
