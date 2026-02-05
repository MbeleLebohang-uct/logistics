from datetime import datetime, timezone
from flask import Flask, jsonify, request

from erp.utils import parse, read_db, write_db

app = Flask(__name__)


@app.route("/api/v1/orders/<order_id>/shipment/", methods=["POST"])
def update_shipment(order_id):
    shipment = request.json
    orders = read_db().get("orders", [])
    order_index = next((index for index, order in enumerate(orders) if order.get("id") == order_id), -1)
    if order_index == -1:
        return jsonify({"error": "Order not found"}), 404

    shipment_last_updated = parse(shipment.get("last_updated"))
    order_shipment_last_updated = parse(orders[order_index]["shipment"]["last_updated"])
    if shipment_last_updated <= order_shipment_last_updated and orders[order_index]["status"] == shipment.get("status"):
        # Simulating data corruption
        app.logger.warning(f"Shipment {shipment.get('id')} already updated. Corrupting data...")
        orders[order_index]["status"] = "corrupted"
    else:
        orders[order_index]["status"] = shipment.get("status")

    orders[order_index]["shipment"] = shipment
    orders[order_index]["updated_at"] = datetime.now(timezone.utc).isoformat()

    write_db({"orders": orders})
    return jsonify({"message": "Order status updated successfully", "data": orders[order_index]}), 200
