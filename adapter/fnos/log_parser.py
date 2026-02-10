from datetime import date
from typing import List, Dict, Any
from urllib.parse import urlencode
from .api_client import APIClient


def parse_login_events(d: date) -> List[Dict[str, Any]]:
    client = APIClient()
    q = f"/api/v1/logs?{urlencode({'date': d.isoformat(), 'type': 'login'})}"
    data = client.get(q) or {}
    items = data.get("items") if isinstance(data, dict) else None
    if not items or not isinstance(items, list):
        return []
    return items


def parse_user_actions(d: date) -> List[Dict[str, Any]]:
    client = APIClient()
    q = f"/api/v1/logs?{urlencode({'date': d.isoformat(), 'type': 'action'})}"
    data = client.get(q) or {}
    items = data.get("items") if isinstance(data, dict) else None
    if not items or not isinstance(items, list):
        return []
    return items
