"""Product catalog + search tools."""
import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent / "mock_data" / "products.json"
_products: list[dict] | None = None


def _load_products() -> list[dict]:
    global _products
    if _products is None:
        with open(_DATA_PATH) as f:
            _products = json.load(f)
    return _products


class ProductTools:
    @staticmethod
    def search_products(query: str, category: str = "", max_price: float = 0) -> dict:
        """Search the catalog."""
        products = _load_products()
        results = []
        query_lower = query.lower()

        for p in products:
            # Match by name, category, or description
            match = (
                query_lower in p["name"].lower()
                or query_lower in p.get("description", "").lower()
                or query_lower in p.get("category", "").lower()
            )
            if category:
                match = match and (category.lower() in p["category"].lower())
            if max_price > 0:
                match = match and (p["price"] <= max_price)
            if match:
                results.append({
                    "sku": p["sku"],
                    "name": p["name"],
                    "price": p["price"],
                    "rating": p["rating"],
                    "in_stock": p["in_stock"],
                    "seller": p["seller"],
                    "category": p["category"],
                })

        # If no exact matches, try partial matching on individual words
        if not results:
            words = query_lower.split()
            for p in products:
                text = f"{p['name']} {p.get('description', '')} {p.get('category', '')}".lower()
                if any(w in text for w in words):
                    if category and category.lower() not in p["category"].lower():
                        continue
                    if max_price > 0 and p["price"] > max_price:
                        continue
                    results.append({
                        "sku": p["sku"],
                        "name": p["name"],
                        "price": p["price"],
                        "rating": p["rating"],
                        "in_stock": p["in_stock"],
                        "seller": p["seller"],
                        "category": p["category"],
                    })

        return {"query": query, "results": results[:10], "count": len(results)}

    @staticmethod
    def get_product_details(sku: str) -> dict:
        """Full specs and reviews."""
        products = _load_products()
        for p in products:
            if p["sku"] == sku:
                return p
        return {"error": f"Product {sku} not found"}

    @staticmethod
    def compare_products(skus: list[str]) -> dict:
        """Side-by-side comparison."""
        products = _load_products()
        comparison = []
        for sku in skus:
            for p in products:
                if p["sku"] == sku:
                    comparison.append(p)
                    break

        if len(comparison) < 2:
            return {"error": "Need at least 2 valid SKUs to compare"}

        return {
            "products": comparison,
            "count": len(comparison),
        }

    @staticmethod
    def get_customer_history(customer_id: str) -> dict:
        """Past purchases for recommendation context."""
        orders_path = Path(__file__).parent.parent / "mock_data" / "orders.json"
        with open(orders_path) as f:
            orders = json.load(f)

        past_items = []
        for order in orders:
            if order["customer_id"] == customer_id:
                for item in order["items"]:
                    past_items.append({
                        "name": item["name"],
                        "sku": item["sku"],
                        "price": item["price"],
                        "order_date": order["placed_at"],
                    })

        return {
            "customer_id": customer_id,
            "past_purchases": past_items,
            "count": len(past_items),
        }
