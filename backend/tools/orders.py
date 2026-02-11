"""Order CRUD + tracking simulation tools."""
import json
from pathlib import Path
from datetime import datetime

_DATA_PATH = Path(__file__).parent.parent / "mock_data" / "orders.json"
_orders: list[dict] | None = None


def _load_orders() -> list[dict]:
    global _orders
    if _orders is None:
        with open(_DATA_PATH) as f:
            _orders = json.load(f)
    return _orders


class OrderTools:
    @staticmethod
    def get_order_status(order_id: str) -> dict:
        """Get order details and tracking info."""
        orders = _load_orders()
        for order in orders:
            if order["order_id"] == order_id:
                result = {
                    "order_id": order["order_id"],
                    "status": order["status"],
                    "items": order["items"],
                    "total": order["total"],
                    "currency": order.get("currency", "EUR"),
                    "placed_at": order["placed_at"],
                }
                if order.get("carrier"):
                    result["carrier"] = order["carrier"]
                    result["tracking_number"] = order.get("tracking_number")
                    result["current_location"] = order.get("current_location")
                if order.get("estimated_delivery"):
                    result["estimated_delivery"] = order["estimated_delivery"]
                if order.get("delivered_at"):
                    result["delivered_at"] = order["delivered_at"]
                if order.get("note"):
                    result["note"] = order["note"]
                if order.get("seller"):
                    result["seller"] = order["seller"]
                return result
        return {"error": f"Order {order_id} not found"}

    @staticmethod
    def get_customer_orders(customer_id: str) -> dict:
        """List recent orders for a customer."""
        orders = _load_orders()
        customer_orders = [
            {
                "order_id": o["order_id"],
                "status": o["status"],
                "total": o["total"],
                "currency": o.get("currency", "EUR"),
                "items_summary": ", ".join(item["name"] for item in o["items"]),
                "placed_at": o["placed_at"],
            }
            for o in orders
            if o["customer_id"] == customer_id
        ]
        if not customer_orders:
            return {"error": f"No orders found for customer {customer_id}"}
        return {"customer_id": customer_id, "orders": customer_orders, "count": len(customer_orders)}

    @staticmethod
    def get_carrier_tracking(tracking_number: str) -> dict:
        """Get detailed courier tracking timeline."""
        orders = _load_orders()
        for order in orders:
            if order.get("tracking_number") == tracking_number:
                # Simulate a tracking timeline
                timeline = []
                placed = order["placed_at"]
                timeline.append({"timestamp": placed, "status": "Order placed", "location": "Online"})

                if order["status"] in ("shipped", "in_transit", "delivered"):
                    timeline.append({
                        "timestamp": placed.replace("T", "T").replace(placed.split("T")[1], "23:00:00Z"),
                        "status": "Picked up by carrier",
                        "location": f"{order.get('carrier', 'Carrier')} Warehouse"
                    })

                if order["status"] in ("in_transit", "delivered"):
                    timeline.append({
                        "timestamp": order.get("estimated_delivery", placed),
                        "status": "In transit",
                        "location": order.get("current_location", "In transit")
                    })

                if order["status"] == "delivered":
                    timeline.append({
                        "timestamp": order.get("delivered_at", ""),
                        "status": "Delivered",
                        "location": order.get("delivery_address", "")
                    })

                return {
                    "tracking_number": tracking_number,
                    "carrier": order.get("carrier"),
                    "status": order["status"],
                    "timeline": timeline,
                    "estimated_delivery": order.get("estimated_delivery"),
                }
        return {"error": f"Tracking number {tracking_number} not found"}
