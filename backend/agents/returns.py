"""
Returns Agent — Returns, refunds, warranty.
Uses Qwen2.5-VL-7B on Slice 2 (port 8082).
"""
import json
import asyncio
import re
from typing import Callable

from .base import BaseAgent
from tools.returns import ReturnTools
from tools.orders import OrderTools

SYSTEM_PROMPT = """You are a returns and refunds specialist for an e-commerce platform.
You can see images — if a customer sends a photo of a damaged or defective product, describe the damage in detail and use it to support their return claim.

You have access to tools. To use a tool, output EXACTLY this format:
<tool_call>{"name": "check_return_eligibility", "args": {"order_id": "ORD-123", "sku": "PHONE-SAM-S25U"}}</tool_call>

Available tools:
- get_order_details: Full order with items and prices. Args: {"order_id": "string"}
- check_return_eligibility: Check return window + restrictions. Args: {"order_id": "string", "sku": "string"}
- initiate_return: Start return, generate label. Args: {"order_id": "string", "sku": "string", "reason": "string"}
- process_refund: Issue refund. Args: {"order_id": "string", "amount": number, "method": "string"}
- schedule_pickup: Schedule courier pickup. Args: {"return_id": "string", "date": "string", "address": "string"}

Return policy:
- Platform items: 30-day free returns
- Marketplace items: 14-day returns, restocking fee may apply
- Non-returnable: hygiene products, opened software, custom-made
- Defective/DOA: warranty claim regardless of time, free pickup
- Refund: 3-5 business days to original payment
- Alternative: store credit with 10% bonus value

If customer sends a photo of damage:
1. Describe what you see in the image
2. Note it as evidence for the return claim
3. Fast-track the return (no need to ship back if damage is obvious)

Process:
1. Verify order and check eligibility
2. Explain policy
3. If eligible: initiate return + offer pickup
4. If refund > 200 EUR: mention supervisor approval needed

Tone: empathetic and procedural."""


class ReturnsAgent(BaseAgent):
    agent_type = "returns"
    system_prompt = SYSTEM_PROMPT
    enable_thinking = False
    temperature = 0.7

    def __init__(self):
        super().__init__()
        self.tools_map = {
            "get_order_details": ReturnTools.get_order_details,
            "check_return_eligibility": ReturnTools.check_return_eligibility,
            "initiate_return": ReturnTools.initiate_return,
            "process_refund": ReturnTools.process_refund,
            "schedule_pickup": ReturnTools.schedule_pickup,
        }

    async def _mock_process(self, message: str, customer_id: str, image_data: str | None, emit: Callable) -> dict:
        """Mock returns processing with realistic tool calls."""
        await asyncio.sleep(0.1)
        msg_lower = message.lower()
        tool_calls = []

        # Get customer orders to find the relevant one
        orders_result = OrderTools.get_customer_orders(customer_id)
        await emit({"type": "tool_call", "data": {"tool": "get_customer_orders", "args": {"customer_id": customer_id}, "status": "executing"}})
        await asyncio.sleep(0.05)
        await emit({"type": "tool_result", "data": {"tool": "get_customer_orders", "result": orders_result, "latency_ms": 2}})

        if not orders_result.get("orders"):
            return {
                "text": "I couldn't find any orders on your account. Could you please provide the order ID?",
                "thinking": "",
                "tool_calls": [],
            }

        # Find the most relevant order
        target_order = None
        for o in orders_result["orders"]:
            summary = o["items_summary"].lower()
            if any(word in summary for word in msg_lower.split() if len(word) > 3):
                target_order = o
                break

        # For cancel scenario, find processing orders
        if any(kw in msg_lower for kw in ["cancel"]):
            for o in orders_result["orders"]:
                if o["status"] in ("processing", "shipped"):
                    target_order = o
                    break

        if not target_order:
            # Get the most recent delivered order
            for o in orders_result["orders"]:
                if o["status"] in ("delivered", "return_requested"):
                    target_order = o
                    break
            if not target_order:
                target_order = orders_result["orders"][0]

        oid = target_order["order_id"]

        # Get order details
        await emit({"type": "tool_call", "data": {"tool": "get_order_details", "args": {"order_id": oid}, "status": "executing"}})
        await asyncio.sleep(0.05)
        order_details = ReturnTools.get_order_details(oid)
        await emit({"type": "tool_result", "data": {"tool": "get_order_details", "result": order_details, "latency_ms": 2}})
        tool_calls.append({"tool": "get_order_details", "args": {"order_id": oid}, "result": order_details})

        first_item = order_details.get("items", [{}])[0]
        sku = first_item.get("sku", "")
        item_name = first_item.get("name", "item")
        item_price = first_item.get("price", 0)

        # Scenario 3: Return with defect photo
        if image_data:
            await emit({"type": "tool_call", "data": {"tool": "check_return_eligibility", "args": {"order_id": oid, "sku": sku}, "status": "executing"}})
            await asyncio.sleep(0.05)
            eligibility = ReturnTools.check_return_eligibility(oid, sku)
            await emit({"type": "tool_result", "data": {"tool": "check_return_eligibility", "result": eligibility, "latency_ms": 3}})
            tool_calls.append({"tool": "check_return_eligibility", "args": {"order_id": oid, "sku": sku}, "result": eligibility})

            # Initiate return
            await emit({"type": "tool_call", "data": {"tool": "initiate_return", "args": {"order_id": oid, "sku": sku, "reason": "Defective - visible damage in customer photo"}, "status": "executing"}})
            await asyncio.sleep(0.05)
            return_result = ReturnTools.initiate_return(oid, sku, "Defective - visible damage in customer photo")
            await emit({"type": "tool_result", "data": {"tool": "initiate_return", "result": return_result, "latency_ms": 3}})
            tool_calls.append({"tool": "initiate_return", "args": {"order_id": oid, "sku": sku, "reason": "Defective"}, "result": return_result})

            # Schedule pickup
            from tools.customers import CustomerTools
            customer = CustomerTools.get_customer(customer_id)
            address = customer.get("delivery_address", "your registered address")
            return_id = return_result.get("return_id", "RET-MOCK")

            await emit({"type": "tool_call", "data": {"tool": "schedule_pickup", "args": {"return_id": return_id, "date": "2026-02-13", "address": address}, "status": "executing"}})
            await asyncio.sleep(0.05)
            pickup_result = ReturnTools.schedule_pickup(return_id, "2026-02-13", address)
            await emit({"type": "tool_result", "data": {"tool": "schedule_pickup", "result": pickup_result, "latency_ms": 2}})
            tool_calls.append({"tool": "schedule_pickup", "args": {"return_id": return_id, "date": "2026-02-13", "address": address}, "result": pickup_result})

            text = (
                f"I can see the damage in your photo — it appears there's a **crack across the screen/surface** of your {item_name}. "
                f"I'm very sorry about this!\n\n"
                f"Based on the visible damage, I've **fast-tracked your return** (no need to ship it back for inspection). "
                f"Here's what I've arranged:\n\n"
                f"- **Return ID**: {return_id}\n"
                f"- **Courier pickup**: {pickup_result.get('pickup_date', 'Feb 13')} ({pickup_result.get('time_window', '09:00-18:00')}) at {address}\n"
                f"- **Carrier**: {pickup_result.get('carrier', 'DPD')}\n"
                f"- **Refund**: €{item_price:.2f} will be returned to your original payment method within 3-5 business days after pickup.\n\n"
                f"Confirmation code: **{pickup_result.get('confirmation_code', 'PU-MOCK')}**. Is there anything else I can help with?"
            )
        # Scenario 6: Cancel order (rerouted from order tracker)
        elif any(kw in msg_lower for kw in ["cancel"]):
            status = order_details.get("status", "")
            if status == "processing":
                await emit({"type": "tool_call", "data": {"tool": "initiate_return", "args": {"order_id": oid, "sku": sku, "reason": "Customer requested cancellation"}, "status": "executing"}})
                await asyncio.sleep(0.05)
                return_result = ReturnTools.initiate_return(oid, sku, "Customer requested cancellation")
                await emit({"type": "tool_result", "data": {"tool": "initiate_return", "result": return_result, "latency_ms": 2}})
                tool_calls.append({"tool": "initiate_return", "args": {"order_id": oid, "sku": sku, "reason": "Cancellation"}, "result": return_result})

                await emit({"type": "tool_call", "data": {"tool": "process_refund", "args": {"order_id": oid, "amount": order_details.get("total", 0), "method": order_details.get("payment_method", "card")}, "status": "executing"}})
                await asyncio.sleep(0.05)
                refund_result = ReturnTools.process_refund(oid, order_details.get("total", 0), order_details.get("payment_method", "card"))
                await emit({"type": "tool_result", "data": {"tool": "process_refund", "result": refund_result, "latency_ms": 2}})
                tool_calls.append({"tool": "process_refund", "args": {"order_id": oid, "amount": order_details.get("total", 0)}, "result": refund_result})

                text = (
                    f"I've processed the cancellation for your order **{oid}** ({item_name}). "
                    f"Since it was still in processing, we were able to cancel it immediately.\n\n"
                    f"- **Refund**: €{order_details.get('total', 0):.2f} → {order_details.get('payment_method', 'original payment method')}\n"
                    f"- **Refund ID**: {refund_result.get('refund_id', 'REF-MOCK')}\n"
                    f"- **Timeline**: 3-5 business days\n\n"
                    f"Is there anything else I can help you with?"
                )
            else:
                text = (
                    f"Your order **{oid}** ({item_name}) is currently **{status}**. "
                    + ("Since it has already shipped, we can initiate a return once you receive it. " if status in ("shipped", "in_transit")
                       else "")
                    + "Would you like me to proceed with a return request?"
                )
        # Standard return request
        else:
            await emit({"type": "tool_call", "data": {"tool": "check_return_eligibility", "args": {"order_id": oid, "sku": sku}, "status": "executing"}})
            await asyncio.sleep(0.05)
            eligibility = ReturnTools.check_return_eligibility(oid, sku)
            await emit({"type": "tool_result", "data": {"tool": "check_return_eligibility", "result": eligibility, "latency_ms": 3}})
            tool_calls.append({"tool": "check_return_eligibility", "args": {"order_id": oid, "sku": sku}, "result": eligibility})

            if eligibility.get("eligible"):
                await emit({"type": "tool_call", "data": {"tool": "initiate_return", "args": {"order_id": oid, "sku": sku, "reason": "Customer requested return"}, "status": "executing"}})
                await asyncio.sleep(0.05)
                return_result = ReturnTools.initiate_return(oid, sku, "Customer requested return")
                await emit({"type": "tool_result", "data": {"tool": "initiate_return", "result": return_result, "latency_ms": 3}})
                tool_calls.append({"tool": "initiate_return", "args": {"order_id": oid, "sku": sku}, "result": return_result})

                return_id = return_result.get("return_id", "RET-MOCK")
                restocking = eligibility.get("restocking_fee", 0)
                restocking_note = f"\n- **Restocking fee**: €{restocking:.2f} (marketplace item)" if restocking > 0 else ""

                text = (
                    f"I've checked the return eligibility for your **{item_name}** from order **{oid}**.\n\n"
                    f"**{eligibility.get('reason', 'Eligible for return')}**\n\n"
                    f"I've initiated the return:\n"
                    f"- **Return ID**: {return_id}{restocking_note}\n"
                    f"- **Refund amount**: €{item_price - restocking:.2f} → original payment method\n"
                    f"- **Return label**: [Download label]({return_result.get('return_label', '#')})\n\n"
                    f"Would you like me to schedule a free courier pickup?"
                )
            else:
                text = (
                    f"I've checked the return eligibility for your **{item_name}** from order **{oid}**.\n\n"
                    f"Unfortunately, **{eligibility.get('reason', 'this item is not eligible for return')}**.\n\n"
                    f"If the item is defective, I can file a warranty claim instead. Would you like me to do that?"
                )

        # Emit cost
        await emit({
            "type": "cost",
            "data": {
                "input_tokens": 350,
                "output_tokens": 220,
                "model": self.model_info["model"],
                "estimated_cost_usd": 0.0004,
            }
        })

        return {
            "text": text,
            "thinking": "",
            "tool_calls": tool_calls,
        }
