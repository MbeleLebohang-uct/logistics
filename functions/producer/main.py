import os
import json
from typing import Any
import requests

from datetime import datetime, timezone
from dateutil import parser
from dateutil.tz import tzutc

from firebase_admin import initialize_app
from firebase_functions import scheduler_fn
from firebase_functions.options import set_global_options
from firebase_functions.params import StringParam

from google.cloud import pubsub_v1, firestore_v1
from google.api_core.exceptions import NotFound

set_global_options(region="europe-west3", max_instances=1)

initialize_app()

API_KEY = "dummy-api-key"
LOGISTICS_API_BASE_URL = StringParam("LOGISTICS_API_BASE_URL").value
LOGISTICS_AUTH_API_URL = StringParam("LOGISTICS_AUTH_API_URL").value
PROJECT_ID = os.environ.get("GCLOUD_PROJECT", "yoco-logistics-intergration")
TOPIC_ID = "erp-order-status-update-queue"


def parse_date(value) -> datetime:
    if not isinstance(value, (str, datetime)):
        raise TypeError('parse_date() first argument must be either type str or datetime')
    if isinstance(value, str):
        value = parser.parse(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tzutc())
    return value


def get_auth_token(auth_api_url: str) -> str:
    response = requests.post(auth_api_url, headers={"Content-Type": "application/json"}, timeout=30)
    response.raise_for_status()
    return response.json().get("token")


def get_last_updated(state_ref: firestore_v1.DocumentReference) -> str:
    last_updated = parse_date("2026-02-06T10:00:00Z")
    try:
        state_doc = state_ref.get()
        return (
            parse_date(state_doc.get("last_updated")) if state_doc.exists else last_updated
        )
    except Exception as e:
        print(f"Error reading state: {e}")
        return last_updated


def ensure_topic_exists(
    publisher: pubsub_v1.PublisherClient, project_id: str, topic_id: str
) -> None:
    topic_path = publisher.topic_path(project_id, topic_id)
    try:
        publisher.get_topic(request={"topic": topic_path})
    except NotFound:
        print(f"Topic {topic_path} not found. Creating it.")
        try:
            publisher.create_topic(request={"name": topic_path})
            print(f"Topic {topic_path} created.")
        except Exception as e:
            print(f"Error creating topic: {e}")
    except Exception as e:
        print(f"Error checking topic: {e}")


def generate_shipment_messages(
    publisher: pubsub_v1.PublisherClient, shipments: list[dict], last_updated: datetime
) -> tuple[list[Any], datetime]:
    messages = []
    topic = publisher.topic_path(PROJECT_ID, TOPIC_ID)
    max_timestamp_seen = last_updated

    for shipment in shipments:
        shipment_id = shipment.get("id")
        last_updated = parse_date(shipment.get("last_updated"))

        if not shipment_id or not last_updated:
            print(f"Skipping invalid shipment data: {shipment}")
            continue

        data = json.dumps(shipment).encode("utf-8")
        updated_at = datetime.now(timezone.utc).isoformat()
        message = publisher.publish(
            topic, data, shipment_id=shipment_id, updated_at=updated_at
        )
        messages.append(message)

        if last_updated > max_timestamp_seen:
            max_timestamp_seen = last_updated

    return messages, max_timestamp_seen


def poll_shipment_updates_api(last_updated: datetime) -> list[dict]:
    try:
        params = {"last_updated": last_updated.isoformat()}
        token = get_auth_token(LOGISTICS_AUTH_API_URL)
        response = requests.get(
            LOGISTICS_API_BASE_URL,
            params=params,
            headers={
                "Authorization": f"{token['token_type'].capitalize} {token['access_token']}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        response.raise_for_status()
        shipments = response.json()
        return shipments.get("data", [])
    except requests.exceptions.RequestException as e:
        print(f"API Request failed: {e}")
        return []


@scheduler_fn.on_schedule(schedule="*/3 * * * *", max_instances=1)
def order_status_update_producer(event: scheduler_fn.ScheduledEvent) -> None:
    """
    Polls the Logistics API for shipment updates and publishes them to Pub/Sub.
    """
    print(f"Producer triggered by cron: {event}")

    db = firestore_v1.Client()
    state_ref = db.collection("system-state").document("erp-order-status-sync")
    last_updated = get_last_updated(state_ref)

    print(f"Polling API for updates since: {last_updated}")
    shipments = poll_shipment_updates_api(last_updated)
    if not shipments:
        print("No new shipments found.")
        return

    print(f"Found {len(shipments)} updates.")
    publisher = pubsub_v1.PublisherClient()
    ensure_topic_exists(publisher, PROJECT_ID, TOPIC_ID)
    messages, max_timestamp_seen = generate_shipment_messages(
        publisher, shipments, last_updated
    )

    try:
        for message in messages:
            message.result()
        print(f"Successfully published {len(messages)} messages.")
    except Exception as e:
        print(f"Error publishing to Pub/Sub: {e}")
        return

    if max_timestamp_seen > last_updated:
        state_ref.set({"last_updated": max_timestamp_seen}, merge=True)
        print(f"Checkpoint updated to: {max_timestamp_seen}")

    print("Producer run completed.")
