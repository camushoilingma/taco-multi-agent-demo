"""
Order Tracker Agent — Order status + tracking.
Uses Qwen2.5-VL-7B on Slice 2 (port 8082).
"""
import json
import asyncio
from typing import Callable

from .base import BaseAgent
from tools.orders import OrderTools

SYSTEM_PROMPT = """You are an order tracking assistant for an e-commerce platform.
You can see images — if a customer sends a screenshot of their order confirmation or tracking page, extract the order ID or tracking number from the image.

You have access to tools. To use a tool, output EXACTLY this format:
<tool_call>{"name": "get_order_status", "args": {"order_id": "ORD-123"}}</tool_call>

Available tools:
- get_order_status: Get order details and tracking info. Args: {"order_id": "string"}
- get_customer_orders: List recent orders for a customer. Args: {"customer_id": "string"}
- get_carrier_tracking: Get courier tracking timeline. Args: {"tracking_number": "string"}

Rules:
- ALWAYS look up the order before responding — never guess
- If customer sends an image of an order/receipt, read the order ID from it
- If customer doesnt provide an order ID, use get_customer_orders first
- If delivery is late, acknowledge the delay and apologize
- Premium members: acknowledge their premium status
- Keep responses under 4 sentences
- If customer wants to return/cancel -> hand off:
  <reroute>{"agent": "returns", "reason": "customer wants to return/cancel"}</reroute>
- Respond in the customers language"""


class OrderTrackerAgent(BaseAgent):
    agent_type = "order_tracker"
    system_prompt = SYSTEM_PROMPT
    enable_thinking = False
    temperature = 0.7

    def __init__(self):
        super().__init__()
        self.tools_map = {
            "get_order_status": OrderTools.get_order_status,
            "get_customer_orders": OrderTools.get_customer_orders,
            "get_carrier_tracking": OrderTools.get_carrier_tracking,
        }

    async def _mock_process(self, message: str, customer_id: str, image_data: str | None, emit: Callable) -> dict:
        """Mock order tracking with realistic tool calls."""
        await asyncio.sleep(0.1)
        msg_lower = message.lower()
        tool_calls = []

        # Scenario 6 check: cancel/return request during order tracking
        if any(kw in msg_lower for kw in ["cancel", "return", "don't want", "actually i want to"]):
            # First look up the order
            orders_result = OrderTools.get_customer_orders(customer_id)
            await emit({"type": "tool_call", "data": {"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "status": "executing"}})
            await asyncio.sleep(0.05)
            await emit({"type": "tool_result", "data": {"tool": "get_customer_orders", "result": orders_result, "latency_ms": 3}})
            tool_calls.append({"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "result": orders_result})

            await emit({
                "type": "reroute",
                "data": {
                    "from": "order_tracker",
                    "to": "returns",
                    "from_model": "Qwen2.5-VL-7B",
                    "to_model": "Qwen2.5-VL-7B",
                    "reason": "Customer wants to cancel/return an order",
                }
            })

            return {
                "text": "",
                "reroute": {"agent": "returns", "reason": "Customer wants to cancel/return an order"},
                "thinking": "",
                "tool_calls": tool_calls,
            }

        # Scenario 2: Image-based order lookup
        if image_data:
            # Simulate reading order ID from image
            await emit({"type": "tool_call", "data": {"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "status": "executing"}})
            await asyncio.sleep(0.05)
            orders_result = OrderTools.get_customer_orders(customer_id)
            await emit({"type": "tool_result", "data": {"tool": "get_customer_orders", "result": orders_result, "latency_ms": 2}})
            tool_calls.append({"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "result": orders_result})

            if orders_result.get("orders"):
                first_order = orders_result["orders"][0]
                oid = first_order["order_id"]
                await emit({"type": "tool_call", "data": {"tool": "get_order_status", "args": {"order_id": oid}, "status": "executing"}})
                await asyncio.sleep(0.05)
                status_result = OrderTools.get_order_status(oid)
                await emit({"type": "tool_result", "data": {"tool": "get_order_status", "result": status_result, "latency_ms": 2}})
                tool_calls.append({"tool": "get_order_status", "args": {"order_id": oid}, "result": status_result})

                return {
                    "text": f"I was able to read the order details from your screenshot! Your order **{oid}** ({first_order['items_summary']}) is currently **{status_result.get('status', 'unknown')}**. "
                           + (f"It's being shipped via {status_result.get('carrier', 'our carrier')} and the current location is: {status_result.get('current_location', 'in transit')}. Estimated delivery: {status_result.get('estimated_delivery', 'soon')}."
                              if status_result.get("carrier") else f"Placed on {status_result.get('placed_at', 'recently')}."),
                    "thinking": "",
                    "tool_calls": tool_calls,
                }

        # Scenario 1: Text-based order tracking
        # Try to extract order ID from message
        import re
        order_match = re.search(r'ORD-\d{4}-\d+', message)

        if order_match:
            oid = order_match.group()
            await emit({"type": "tool_call", "data": {"tool": "get_order_status", "args": {"order_id": oid}, "status": "executing"}})
            await asyncio.sleep(0.05)
            status_result = OrderTools.get_order_status(oid)
            await emit({"type": "tool_result", "data": {"tool": "get_order_status", "result": status_result, "latency_ms": 2}})
            tool_calls.append({"tool": "get_order_status", "args": {"order_id": oid}, "result": status_result})
        else:
            # Look up customer orders first
            await emit({"type": "tool_call", "data": {"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "status": "executing"}})
            await asyncio.sleep(0.05)
            orders_result = OrderTools.get_customer_orders(customer_id)
            await emit({"type": "tool_result", "data": {"tool": "get_customer_orders", "result": orders_result, "latency_ms": 2}})
            tool_calls.append({"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "result": orders_result})

            # Find most relevant order based on message
            if orders_result.get("orders"):
                # Try to match by product name
                best_order = None
                for o in orders_result["orders"]:
                    summary_lower = o["items_summary"].lower()
                    if any(word in summary_lower for word in msg_lower.split() if len(word) > 3):
                        best_order = o
                        break

                if not best_order:
                    # Default: most recent non-delivered, non-cancelled order
                    for o in orders_result["orders"]:
                        if o["status"] in ("in_transit", "shipped", "processing"):
                            best_order = o
                            break
                    if not best_order:
                        best_order = orders_result["orders"][0]

                oid = best_order["order_id"]
                await emit({"type": "tool_call", "data": {"tool": "get_order_status", "args": {"order_id": oid}, "status": "executing"}})
                await asyncio.sleep(0.05)
                status_result = OrderTools.get_order_status(oid)
                await emit({"type": "tool_result", "data": {"tool": "get_order_status", "result": status_result, "latency_ms": 2}})
                tool_calls.append({"tool": "get_order_status", "args": {"order_id": oid}, "result": status_result})
            else:
                return {
                    "text": "I couldn't find any orders associated with your account. Could you please provide your order ID? It starts with ORD-.",
                    "thinking": "",
                    "tool_calls": tool_calls,
                }

        # Build response from order status
        status = status_result.get("status", "unknown")
        items = ", ".join(i["name"] for i in status_result.get("items", []))
        oid = status_result.get("order_id", "your order")

        # Check premium
        from tools.customers import CustomerTools
        customer = CustomerTools.get_customer(customer_id)
        premium_prefix = "As a valued Premium member, " if customer.get("is_premium") else ""

        if status == "in_transit":
            text = (
                f"{premium_prefix}great news! Your order **{oid}** ({items}) is currently **out for delivery**! "
                f"It's being shipped via {status_result.get('carrier', 'our carrier')} — current location: "
                f"**{status_result.get('current_location', 'in transit')}**. "
                f"Estimated delivery: **{status_result.get('estimated_delivery', 'today')}**."
            )
        elif status == "delivered":
            text = (
                f"{premium_prefix}your order **{oid}** ({items}) was **delivered** "
                f"on {status_result.get('delivered_at', 'recently')}. "
                f"If you haven't received it or have any issues, please let me know!"
            )
        elif status == "processing":
            text = (
                f"{premium_prefix}your order **{oid}** ({items}) is currently being **processed** and prepared for shipping. "
                f"Estimated delivery: **{status_result.get('estimated_delivery', 'within a few days')}**."
                + (f" Note: {status_result.get('note')}" if status_result.get("note") else "")
            )
        elif status == "shipped":
            text = (
                f"{premium_prefix}your order **{oid}** ({items}) has been **shipped**! "
                f"Carrier: {status_result.get('carrier', 'our partner')} | Tracking: {status_result.get('tracking_number', 'N/A')}. "
                f"Estimated delivery: **{status_result.get('estimated_delivery', 'soon')}**."
            )
        elif status == "cancelled":
            text = f"{premium_prefix}your order **{oid}** ({items}) was **cancelled**. If you'd like to reorder or need any help, I'm here for you!"
        else:
            text = f"{premium_prefix}your order **{oid}** is currently in status: **{status}**. Let me know if you need more details!"

        # Emit cost
        await emit({
            "type": "cost",
            "data": {
                "input_tokens": 280,
                "output_tokens": 156,
                "model": self.model_info["model"],
                "estimated_cost_usd": 0.0003,
            }
        })

        return {
            "text": text,
            "thinking": "",
            "tool_calls": tool_calls,
        }
