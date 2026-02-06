import json
import os
from google.cloud import firestore_v1


def seed_orders():
    db_file_path = os.path.join(os.path.dirname(__file__), "db.json")

    print(f"Reading data from {db_file_path}")

    if not os.path.exists(db_file_path):
        print(f"Error: {db_file_path} does not exist.")
        return

    with open(db_file_path, "r") as f:
        data = json.load(f)

    orders = data.get("orders", [])

    if not orders:
        print("No orders found in db.json")
        return

    db = firestore_v1.Client()

    collection_name = "orders"
    batch = db.batch()

    print(f"Seeding {len(orders)} orders to Firestore collection '{collection_name}'...")

    count = 0
    for order in orders:
        doc_id = order.get("id")
        if not doc_id:
            continue

        doc_ref = db.collection(collection_name).document(doc_id)
        batch.set(doc_ref, order)
        count += 1

        # Commit in batches of 500 (limit is 500)
        if count % 500 == 0:
            batch.commit()
            batch = db.batch()
            print(f"Committed {count} records...")

    if count % 500 != 0:
        batch.commit()

    print(f"Successfully seeded {count} orders.")


if __name__ == "__main__":
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        os.environ["GOOGLE_CLOUD_PROJECT"] = "yoco-logistics-intergration"

    seed_orders()
