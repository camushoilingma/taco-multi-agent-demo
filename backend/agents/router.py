"""
Router Agent — Intent classifier.
Uses Qwen3-VL-8B on Slice 1 (port 8081).
"""
import json
import re
import logging
from typing import Callable

from .base import BaseAgent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a routing classifier for an e-commerce customer service platform.
Given the customer message (and optionally an image), classify the intent.

Categories:
- ORDER_STATUS: tracking, delivery ETA, where is my package, courier info
- RETURNS: return product, refund, broken/defective, warranty, wrong item, cancel order
- PRODUCT_ADVISOR: recommendations, comparisons, specs, what should I buy, compatibility
- ESCALATE: very angry, legal threats, consumer protection, repeated unresolved issues

If an image is attached:
- Photo of damaged/broken product -> RETURNS
- Photo of a product to identify/compare -> PRODUCT_ADVISOR
- Screenshot of order/receipt -> ORDER_STATUS

Output ONLY this JSON, no other text:
{"category": "ORDER_STATUS", "confidence": 0.95, "language": "en", "has_image": false}

Rules:
- If confidence < 0.65, set category to "CLARIFY"
- If user mentions lawyer, legal action, consumer protection -> always ESCALATE
- If user seems very frustrated (ALL CAPS, profanity) -> ESCALATE
- Detect language from the message (en, ro, hu, bg, de, fr)
- "Cancel order" -> RETURNS (not ORDER_STATUS)"""


# Keywords for mock routing
_ORDER_KEYWORDS = ["order", "track", "delivery", "where is", "package", "shipping", "shipped", "status", "eta", "courier"]
_RETURN_KEYWORDS = ["return", "refund", "broken", "defective", "damaged", "cancel", "warranty", "wrong item", "cracked"]
_PRODUCT_KEYWORDS = ["recommend", "compare", "suggest", "which", "should i", "buy", "compatible", "case for", "specs", "better", "vs", "or the"]
_ESCALATE_KEYWORDS = ["lawyer", "legal", "complaint", "consumer protection", "sue", "called 5 times", "nobody helps", "filing"]


class RouterAgent(BaseAgent):
    agent_type = "router"
    system_prompt = SYSTEM_PROMPT
    enable_thinking = False
    temperature = 0.1

    def _classify_mock(self, message: str, has_image: bool) -> dict:
        """Mock classification based on keywords."""
        msg_lower = message.lower()

        # Check escalation first (highest priority)
        if any(kw in msg_lower for kw in _ESCALATE_KEYWORDS):
            return {"category": "ESCALATE", "confidence": 0.98, "language": "en", "has_image": has_image}

        # Check returns (before order to catch "cancel")
        if any(kw in msg_lower for kw in _RETURN_KEYWORDS):
            conf = 0.97 if has_image else 0.93
            return {"category": "RETURNS", "confidence": conf, "language": "en", "has_image": has_image}

        # Check product advisor
        if any(kw in msg_lower for kw in _PRODUCT_KEYWORDS):
            conf = 0.96 if not has_image else 0.88
            return {"category": "PRODUCT_ADVISOR", "confidence": conf, "language": "en", "has_image": has_image}

        # Check order status
        if any(kw in msg_lower for kw in _ORDER_KEYWORDS):
            conf = 0.93 if not has_image else 0.91
            return {"category": "ORDER_STATUS", "confidence": conf, "language": "en", "has_image": has_image}

        # Image-based routing
        if has_image:
            return {"category": "PRODUCT_ADVISOR", "confidence": 0.75, "language": "en", "has_image": True}

        # Default
        return {"category": "CLARIFY", "confidence": 0.50, "language": "en", "has_image": has_image}

    async def _mock_process(self, message: str, customer_id: str, image_data: str | None, emit: Callable) -> dict:
        """Mock routing classification."""
        import asyncio
        await asyncio.sleep(0.05)  # Simulate 50ms latency

        classification = self._classify_mock(message, image_data is not None)

        await emit({
            "type": "routing",
            "data": {
                **classification,
                "model": self.model_info["model"],
                "qgpu_slice": self.model_info["qgpu_slice"],
                "latency_ms": 45,
            }
        })

        return {
            "text": json.dumps(classification),
            "classification": classification,
            "thinking": "",
            "tool_calls": [],
        }

    async def parse_classification(self, result: dict) -> dict:
        """Parse the router output into a classification dict."""
        if "classification" in result:
            return result["classification"]

        # Parse from LLM text output
        try:
            text = result.get("text", "")
            # Try to extract JSON from the response
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                return json.loads(json_match.group())
        except (json.JSONDecodeError, AttributeError):
            pass

        return {"category": "CLARIFY", "confidence": 0.0, "language": "en", "has_image": False}
