"""
Product Advisor Agent — Product search, compare, recommend.
Uses Qwen3-VL-8B on Slice 1 (port 8081). THINKING ENABLED.
"""
import json
import asyncio
import re
from typing import Callable

from .base import BaseAgent
from tools.products import ProductTools

SYSTEM_PROMPT = """You are a knowledgeable product advisor for an e-commerce platform.
You can see images — if a customer sends a photo of a product they own or are interested in, identify it and provide relevant recommendations.

You have access to tools. To use a tool, output EXACTLY this format:
<tool_call>{"name": "search_products", "args": {"query": "laptop", "category": "laptops", "max_price": 1500}}</tool_call>

Available tools:
- search_products: Search the catalog. Args: {"query": "string", "category": "string", "max_price": number}
- get_product_details: Full specs and reviews. Args: {"sku": "string"}
- compare_products: Side-by-side comparison. Args: {"skus": ["string", "string"]}
- get_customer_history: Past purchases. Args: {"customer_id": "string"}

Rules:
- If customer sends a product photo, identify it and suggest similar/compatible items
- Be a knowledgeable advisor, not a salesperson
- For electronics: highlight real-world differences, not just specs
- When comparing: make a clear recommendation with reasoning
- Suggest max 1-2 complementary products
- Flag marketplace seller items (different warranty/returns)
- If out of stock, suggest alternatives
- Respond conversationally, not in bullet-point dumps"""


class ProductAdvisorAgent(BaseAgent):
    agent_type = "product_advisor"
    system_prompt = SYSTEM_PROMPT
    enable_thinking = True  # Qwen3 thinking mode
    temperature = 0.7

    def __init__(self):
        super().__init__()
        self.tools_map = {
            "search_products": ProductTools.search_products,
            "get_product_details": ProductTools.get_product_details,
            "compare_products": ProductTools.compare_products,
            "get_customer_history": ProductTools.get_customer_history,
        }

    async def _mock_process(self, message: str, customer_id: str, image_data: str | None, emit: Callable) -> dict:
        """Mock product advisor with thinking blocks and tool calls."""
        await asyncio.sleep(0.15)
        msg_lower = message.lower()
        tool_calls = []
        thinking_text = ""

        # Scenario 5: Product ID from photo
        if image_data:
            thinking_text = (
                "The customer has sent a photo of what appears to be a smartphone. "
                "Based on the form factor and camera module layout, this looks like a Samsung Galaxy S25 series device. "
                "I should search for compatible cases and accessories for this phone."
            )
            await emit({"type": "thinking", "data": {"text": thinking_text}})
            await asyncio.sleep(0.1)

            # Search for compatible accessories
            await emit({"type": "tool_call", "data": {"tool": "get_product_details", "args": {"sku": "PHONE-SAM-S25U"}, "status": "executing"}})
            await asyncio.sleep(0.05)
            phone_details = ProductTools.get_product_details("PHONE-SAM-S25U")
            await emit({"type": "tool_result", "data": {"tool": "get_product_details", "result": phone_details, "latency_ms": 2}})
            tool_calls.append({"tool": "get_product_details", "args": {"sku": "PHONE-SAM-S25U"}, "result": phone_details})

            await emit({"type": "tool_call", "data": {"tool": "search_products", "args": {"query": "Samsung S25 case", "category": "accessories"}, "status": "executing"}})
            await asyncio.sleep(0.05)
            cases = ProductTools.search_products("Samsung S25", "accessories")
            await emit({"type": "tool_result", "data": {"tool": "search_products", "result": cases, "latency_ms": 3}})
            tool_calls.append({"tool": "search_products", "args": {"query": "Samsung S25 case"}, "result": cases})

            text = (
                "I can see from your photo that you have a **Samsung Galaxy S25 Ultra** — great phone! "
                "For a compatible case, I'd recommend the **Samsung S25 Ultra Silicone Case** (€29.99). "
                "It's the official Samsung case with a soft-touch finish and precise cutouts for all ports and the S Pen slot. "
                "Available in Black, Navy, Cream, and Coral. Shall I add it to your cart?"
            )

        # Scenario 4: Product comparison (TV)
        elif any(kw in msg_lower for kw in ["compare", "vs", "or the", "lg c4", "s90d", "which tv", "oled"]):
            thinking_text = (
                "The customer is comparing two premium OLED TVs. Let me think about the key differences:\n\n"
                "The LG C4 uses a traditional W-OLED panel with self-emitting pixels — this means perfect blacks and infinite contrast. "
                "It's powered by the α9 Gen7 AI processor and has excellent gaming features with 4x HDMI 2.1.\n\n"
                "The Samsung S90D uses QD-OLED (Quantum Dot OLED), which combines OLED's perfect blacks with "
                "Quantum Dot's superior color volume and brightness. It can get noticeably brighter in HDR content, "
                "and the Object Tracking Sound+ with 60W is significantly better than LG's 40W system.\n\n"
                "For a bright living room: Samsung S90D (brighter highlights).\n"
                "For a dark home theater: LG C4 (proven webOS, slightly cheaper).\n"
                "For gaming: both excellent, but LG's Game Optimizer is more mature.\n\n"
                "I'll pull up the detailed specs to give a comprehensive recommendation."
            )
            await emit({"type": "thinking", "data": {"text": thinking_text}})
            await asyncio.sleep(0.1)

            await emit({"type": "tool_call", "data": {"tool": "compare_products", "args": {"skus": ["TV-LG-OLED55C4", "TV-SAM-S90D55"]}, "status": "executing"}})
            await asyncio.sleep(0.05)
            comparison = ProductTools.compare_products(["TV-LG-OLED55C4", "TV-SAM-S90D55"])
            await emit({"type": "tool_result", "data": {"tool": "compare_products", "result": comparison, "latency_ms": 3}})
            tool_calls.append({"tool": "compare_products", "args": {"skus": ["TV-LG-OLED55C4", "TV-SAM-S90D55"]}, "result": comparison})

            text = (
                "Both are excellent OLED TVs, but they have different strengths:\n\n"
                "The **LG C4 OLED** (€1,199) uses traditional W-OLED — proven technology with perfect blacks, excellent webOS smart platform, "
                "and arguably the best gaming experience with LG's refined Game Optimizer. 4 HDMI 2.1 ports at 4K@120Hz.\n\n"
                "The **Samsung S90D QD-OLED** (€1,299) uses Quantum Dot OLED, which gets **noticeably brighter** in HDR — "
                "if your living room has windows, you'll appreciate this. The sound system is also superior at 60W with Object Tracking Sound+ "
                "vs LG's 40W. It supports 4K@144Hz, a small edge for PC gaming.\n\n"
                "**My recommendation**: If you're in a **bright room**, go Samsung S90D — the extra brightness is worth the €100 premium. "
                "For a **dedicated dark viewing room** or heavy gaming, the LG C4 is the sweet spot at €100 less. "
                "Both have 24-month warranty and 30-day free returns, so you can try risk-free!"
            )

        # General product search/recommendation
        else:
            # Extract what they're looking for
            search_query = msg_lower
            category = ""
            if any(w in msg_lower for w in ["phone", "smartphone", "mobile"]):
                category = "phones"
                search_query = "phone"
            elif any(w in msg_lower for w in ["laptop", "notebook", "macbook"]):
                category = "laptops"
                search_query = "laptop"
            elif any(w in msg_lower for w in ["tv", "television", "oled"]):
                category = "tvs"
                search_query = "tv"
            elif any(w in msg_lower for w in ["headphone", "earbuds", "audio"]):
                category = "audio"
                search_query = "audio"

            thinking_text = (
                f"The customer is looking for product advice. Let me search our catalog "
                f"{'in the ' + category + ' category ' if category else ''}and check their purchase history to give personalized recommendations."
            )
            await emit({"type": "thinking", "data": {"text": thinking_text}})

            # Get customer history for personalization
            await emit({"type": "tool_call", "data": {"tool": "get_customer_history", "args": {"customer_id": customer_id}, "status": "executing"}})
            await asyncio.sleep(0.05)
            history = ProductTools.get_customer_history(customer_id)
            await emit({"type": "tool_result", "data": {"tool": "get_customer_history", "result": history, "latency_ms": 2}})
            tool_calls.append({"tool": "get_customer_history", "args": {"customer_id": customer_id}, "result": history})

            await emit({"type": "tool_call", "data": {"tool": "search_products", "args": {"query": search_query, "category": category}, "status": "executing"}})
            await asyncio.sleep(0.05)
            results = ProductTools.search_products(search_query, category)
            await emit({"type": "tool_result", "data": {"tool": "search_products", "result": results, "latency_ms": 3}})
            tool_calls.append({"tool": "search_products", "args": {"query": search_query, "category": category}, "result": results})

            if results.get("results"):
                top = results["results"][:3]
                recs = "\n".join(
                    f"- **{p['name']}** — €{p['price']:.2f} (⭐ {p['rating']}) {'✅ In stock' if p['in_stock'] else '❌ Out of stock'}"
                    + (f" ⚠️ Marketplace seller" if p['seller'] != 'platform' else "")
                    for p in top
                )
                text = f"Based on what you're looking for, here are my top picks:\n\n{recs}\n\nWould you like me to compare any of these in detail, or do you have a specific budget or feature in mind?"
            else:
                text = "I couldn't find an exact match in our catalog. Could you tell me more about what you're looking for — budget, key features, or how you plan to use it?"

        # Emit cost
        await emit({
            "type": "cost",
            "data": {
                "input_tokens": 420,
                "output_tokens": 310,
                "model": self.model_info["model"],
                "estimated_cost_usd": 0.0005,
            }
        })

        return {
            "text": text,
            "thinking": thinking_text,
            "tool_calls": tool_calls,
        }
