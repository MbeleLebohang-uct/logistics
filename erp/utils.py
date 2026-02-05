from datetime import datetime
import json
import os
from dateutil.tz import tzutc
from dateutil import parser
from typing import Union

DB_FILE = os.path.join(os.path.dirname(__file__), "db.json")


def read_db():
    if not os.path.exists(DB_FILE):
        return {"orders": []}
    with open(DB_FILE, "r") as f:
        return json.load(f)


def write_db(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)


def parse(value: Union[datetime, str]) -> datetime:
    if not isinstance(value, (str, datetime)):
        raise TypeError('parse_date() first argument must be either type str or datetime')
    if isinstance(value, str):
        value = parser.parse(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=tzutc())
    return value
