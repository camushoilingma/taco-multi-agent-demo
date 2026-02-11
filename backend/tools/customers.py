"""Customer profiles + history tools."""
import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "mock_data" / "customers.json"
_customers: list[dict] | None = None


def _load_customers() -> list[dict]:
    global _customers
    if _customers is None:
        with open(_DATA_PATH) as f:
            _customers = json.load(f)
    return _customers


class CustomerTools:
    @staticmethod
    def get_customer(customer_id: str) -> dict:
        """Get customer profile."""
        customers = _load_customers()
        for c in customers:
            if c["customer_id"] == customer_id:
                return c
        return {"error": f"Customer {customer_id} not found"}

    @staticmethod
    def list_customers() -> dict:
        """List all demo customers."""
        customers = _load_customers()
        return {
            "customers": [
                {
                    "customer_id": c["customer_id"],
                    "name": c["name"],
                    "language": c["language"],
                    "is_premium": c["is_premium"],
                }
                for c in customers
            ]
        }
