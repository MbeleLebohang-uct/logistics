from flask import Flask, request, jsonify
from external.utils import parse, read_db


app = Flask(__name__)


@app.route("/api/v1/shipments/", methods=["GET"])
def get_shipments():
    last_updated_param = request.args.get("last_updated", None)

    if not last_updated_param:
        return jsonify({"data": []})

    data = read_db()
    shipments = data.get("shipments", [])
    try:
        last_updated = parse(last_updated_param)
        shipments = [shipment for shipment in shipments if parse(shipment.get("last_updated")) >= last_updated]
    except ValueError:
        return (jsonify({"error": "Invalid date format. Use ISO 8601 (e.g., 2024-01-01T00:00:00Z)"}), 400)

    return jsonify({"data": shipments})
