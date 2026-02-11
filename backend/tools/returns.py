"""Return processing + refund logic tools."""
import json
import uuid
from pathlib import Path
from datetime import datetime, timedelta

_DATA_PATH = Path(__file__).parent.parent / "mock_data" / "orders.json"
_orders: list[dict] | None = None


def _load_orders() -> list[dict]:
    global _orders
    if _orders is None:
        with open(_DATA_PATH) as f:
            _orders = json.load(f)
    return _orders


class ReturnTools:
    @staticmethod
    def get_order_details(order_id: str) -> dict:
        """Full order with items and prices."""
        orders = _load_orders()
        for order in orders:
            if order["order_id"] == order_id:
                return order
        return {"error": f"Order {order_id} not found"}

    @staticmethod
    def check_return_eligibility(order_id: str, sku: str) -> dict:
        """Check return window + restrictions."""
        orders = _load_orders()
        for order in orders:
            if order["order_id"] == order_id:
                # Find the item
                item = None
                for i in order["items"]:
                    if i["sku"] == sku:
                        item = i
                        break
                if not item:
                    return {"error": f"SKU {sku} not found in order {order_id}"}

                delivered_at = order.get("delivered_at")
                if not delivered_at and order["status"] != "delivered":
                    return {
                        "eligible": False,
                        "reason": f"Order status is '{order['status']}' — item has not been delivered yet",
                        "order_id": order_id,
                        "sku": sku,
                    }

                # Check return window
                seller = order.get("seller", "platform")
                is_marketplace = seller != "platform" and seller.startswith("marketplace_")
                return_window_days = 14 if is_marketplace else 30

                if delivered_at:
                    delivery_date = datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
                    now = datetime.now(delivery_date.tzinfo)
                    days_since = (now - delivery_date).days
                    within_window = days_since <= return_window_days
                else:
                    days_since = 0
                    within_window = True

                # Check for non-returnable categories
                non_returnable = sku.startswith("SVC-")  # Services
                if order.get("return_reason") and "defective" in order.get("return_reason", "").lower():
                    # Defective items are always eligible
                    return {
                        "eligible": True,
                        "reason": "Defective item — warranty claim, free return regardless of timeframe",
                        "order_id": order_id,
                        "sku": sku,
                        "item_name": item["name"],
                        "item_price": item["price"],
                        "return_type": "warranty_claim",
                        "free_pickup": True,
                        "restocking_fee": 0,
                    }

                return {
                    "eligible": within_window and not non_returnable,
                    "reason": (
                        f"Within {return_window_days}-day return window ({days_since} days since delivery)"
                        if within_window
                        else f"Return window expired ({days_since}/{return_window_days} days)"
                    ),
                    "order_id": order_id,
                    "sku": sku,
                    "item_name": item["name"],
                    "item_price": item["price"],
                    "seller": seller,
                    "is_marketplace": is_marketplace,
                    "return_window_days": return_window_days,
                    "days_since_delivery": days_since,
                    "free_pickup": not is_marketplace,
                    "restocking_fee": item["price"] * 0.1 if is_marketplace else 0,
                }
        return {"error": f"Order {order_id} not found"}

    @staticmethod
    def initiate_return(order_id: str, sku: str, reason: str) -> dict:
        """Start return, generate label."""
        return_id = f"RET-{uuid.uuid4().hex[:8].upper()}"
        return {
            "return_id": return_id,
            "order_id": order_id,
            "sku": sku,
            "reason": reason,
            "status": "initiated",
            "return_label": f"https://returns.example.com/label/{return_id}",
            "instructions": "Please pack the item securely in original packaging if available. Attach the return label to the outside of the package.",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def process_refund(order_id: str, amount: float, method: str) -> dict:
        """Issue refund."""
        refund_id = f"REF-{uuid.uuid4().hex[:8].upper()}"
        return {
            "refund_id": refund_id,
            "order_id": order_id,
            "amount": amount,
            "currency": "EUR",
            "method": method,
            "status": "processing",
            "estimated_completion": "3-5 business days",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def schedule_pickup(return_id: str, date: str, address: str) -> dict:
        """Schedule courier pickup."""
        return {
            "return_id": return_id,
            "pickup_date": date,
            "pickup_address": address,
            "carrier": "DPD",
            "time_window": "09:00 - 18:00",
            "status": "scheduled",
            "confirmation_code": f"PU-{uuid.uuid4().hex[:6].upper()}",
        }
