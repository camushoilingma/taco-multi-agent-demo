"""
FastAPI Orchestrator — Multi-model routing with WebSocket support.

Every message hits the Router first (Qwen3-VL-8B on Slice 1).
The orchestrator reads the classification, then calls the right specialist
on the correct model endpoint (which may be a different qGPU slice).
"""
import json
import uuid
import asyncio
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from agents.router import RouterAgent
from agents.order_tracker import OrderTrackerAgent
from agents.returns import ReturnsAgent
from agents.product_advisor import ProductAdvisorAgent
from tools.customers import CustomerTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Agent instances
router_agent = RouterAgent()
order_tracker = OrderTrackerAgent()
returns_agent = ReturnsAgent()
product_advisor = ProductAdvisorAgent()

AGENT_MAP = {
    "ORDER_STATUS": order_tracker,
    "RETURNS": returns_agent,
    "PRODUCT_ADVISOR": product_advisor,
}

# In-memory conversation store
conversations: dict[str, list[dict]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("Multi-Agent E-Commerce Customer Service")
    logger.info(f"Mock LLM: {settings.mock_llm}")
    logger.info(f"Model 1: {settings.model1_display} @ {settings.model1_base_url}")
    logger.info(f"Model 2: {settings.model2_display} @ {settings.model2_base_url}")
    logger.info("=" * 60)
    yield


app = FastAPI(
    title="Multi-Agent E-Commerce Customer Service",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    customer_id: str = "C-1001"
    conversation_id: Optional[str] = None
    image: Optional[str] = None  # base64


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    agent: str
    model: str
    qgpu_slice: str
    classification: dict
    events: list[dict]
    total_latency_ms: int


async def process_message(
    message: str,
    customer_id: str,
    conversation_id: str,
    image: Optional[str] = None,
    event_callback=None,
) -> dict:
    """Core orchestration: route -> classify -> specialist."""
    history = conversations.get(conversation_id, [])

    # Step 1: Route (always Qwen3-VL-8B on Slice 1)
    router_result = await router_agent.process(
        message=message,
        customer_id=customer_id,
        conversation_history=history,
        image_data=image,
        event_callback=event_callback,
    )

    classification = await router_agent.parse_classification(router_result)
    category = classification.get("category", "CLARIFY")

    # Step 2: Handle special categories
    if category == "ESCALATE":
        # Return empathetic escalation response
        escalation_text = (
            "I completely understand your frustration, and I sincerely apologize for the difficulties you've experienced. "
            "Your case is important to us. I'm escalating this to our **senior support team** right now — "
            "a supervisor will contact you within **2 hours** via your preferred contact method. "
            "They will have full context of your previous interactions. "
            "Your case reference is **ESC-" + uuid.uuid4().hex[:6].upper() + "**. "
            "Is there anything else I can note for the supervisor?"
        )
        model_info = settings.get_model_info("router")
        if event_callback:
            await event_callback({
                "type": "agent_start",
                "data": {"agent": "escalation", **model_info}
            })
            await event_callback({
                "type": "response",
                "data": {
                    "text": escalation_text,
                    "agent": "escalation",
                    **model_info,
                    "total_latency_ms": router_result.get("total_latency_ms", 0) + 50,
                }
            })

        # Store in history
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": escalation_text})
        conversations[conversation_id] = history

        return {
            "conversation_id": conversation_id,
            "response": escalation_text,
            "agent": "escalation",
            "model": model_info["model"],
            "qgpu_slice": model_info["qgpu_slice"],
            "classification": classification,
            "events": router_result.get("events", []),
            "total_latency_ms": router_result.get("total_latency_ms", 0) + 50,
        }

    if category == "CLARIFY":
        clarify_text = (
            "I'd like to help you! Could you tell me a bit more about what you need? For example:\n"
            "- **Order tracking**: \"Where is my order?\" or provide an order ID\n"
            "- **Returns/refunds**: \"I want to return...\" or \"My item is damaged\"\n"
            "- **Product advice**: \"Which laptop should I buy?\" or \"Compare these TVs\""
        )
        model_info = settings.get_model_info("router")
        if event_callback:
            await event_callback({
                "type": "response",
                "data": {"text": clarify_text, "agent": "router", **model_info, "total_latency_ms": 50}
            })

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": clarify_text})
        conversations[conversation_id] = history

        return {
            "conversation_id": conversation_id,
            "response": clarify_text,
            "agent": "router",
            "model": model_info["model"],
            "qgpu_slice": model_info["qgpu_slice"],
            "classification": classification,
            "events": router_result.get("events", []),
            "total_latency_ms": 50,
        }

    # Step 3: Call specialist agent
    specialist = AGENT_MAP.get(category)
    if not specialist:
        specialist = order_tracker  # fallback

    # Emit model switch if crossing slices
    router_info = settings.get_model_info("router")
    specialist_info = settings.get_model_info(specialist.agent_type)
    if router_info["qgpu_slice"] != specialist_info["qgpu_slice"]:
        if event_callback:
            await event_callback({
                "type": "model_switch",
                "data": {
                    "from_model": router_info["model"],
                    "from_slice": router_info["qgpu_slice"],
                    "to_model": specialist_info["model"],
                    "to_slice": specialist_info["qgpu_slice"],
                }
            })

    specialist_result = await specialist.process(
        message=message,
        customer_id=customer_id,
        conversation_history=history,
        image_data=image,
        event_callback=event_callback,
    )

    response_text = specialist_result.get("text", "")
    all_events = router_result.get("events", []) + specialist_result.get("events", [])

    # Step 4: Handle rerouting
    reroute = specialist_result.get("reroute")
    reroute_count = 0
    while reroute and reroute_count < settings.max_reroutes:
        reroute_count += 1
        target_agent_name = reroute.get("agent", "")
        target_agent = AGENT_MAP.get(target_agent_name.upper(), None)
        if not target_agent:
            # Try mapping agent names
            name_map = {"returns": returns_agent, "order_tracker": order_tracker, "product_advisor": product_advisor}
            target_agent = name_map.get(target_agent_name, None)

        if not target_agent:
            break

        from_info = settings.get_model_info(specialist.agent_type)
        to_info = settings.get_model_info(target_agent.agent_type)

        if event_callback:
            await event_callback({
                "type": "reroute",
                "data": {
                    "from": specialist.agent_type,
                    "to": target_agent.agent_type,
                    "from_model": from_info["model"],
                    "to_model": to_info["model"],
                    "reason": reroute.get("reason", ""),
                }
            })

            if from_info["qgpu_slice"] != to_info["qgpu_slice"]:
                await event_callback({
                    "type": "model_switch",
                    "data": {
                        "from_model": from_info["model"],
                        "from_slice": from_info["qgpu_slice"],
                        "to_model": to_info["model"],
                        "to_slice": to_info["qgpu_slice"],
                    }
                })

        specialist = target_agent
        specialist_result = await specialist.process(
            message=message,
            customer_id=customer_id,
            conversation_history=history,
            image_data=image,
            event_callback=event_callback,
        )
        response_text = specialist_result.get("text", "")
        all_events.extend(specialist_result.get("events", []))
        reroute = specialist_result.get("reroute")

    # Emit final response
    if event_callback:
        await event_callback({
            "type": "response",
            "data": {
                "text": response_text,
                "agent": specialist.agent_type,
                "model": specialist.model_info["model"],
                "qgpu_slice": specialist.model_info["qgpu_slice"],
                "total_latency_ms": specialist_result.get("total_latency_ms", 0),
            }
        })

    # Store in history
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response_text})
    conversations[conversation_id] = history

    total_ms = router_result.get("total_latency_ms", 0) + specialist_result.get("total_latency_ms", 0)

    return {
        "conversation_id": conversation_id,
        "response": response_text,
        "agent": specialist.agent_type,
        "model": specialist.model_info["model"],
        "qgpu_slice": specialist.model_info["qgpu_slice"],
        "classification": classification,
        "events": all_events,
        "total_latency_ms": total_ms,
    }


# ──────────────────────── REST Endpoint ────────────────────────

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    result = await process_message(
        message=req.message,
        customer_id=req.customer_id,
        conversation_id=conversation_id,
        image=req.image,
    )
    return ChatResponse(**result)


# ──────────────────────── WebSocket Endpoint ────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            data = await ws.receive_json()
            message = data.get("message", "")
            customer_id = data.get("customer_id", "C-1001")
            conversation_id = data.get("conversation_id", str(uuid.uuid4()))
            image = data.get("image")

            async def send_event(event: dict):
                try:
                    await ws.send_json(event)
                except Exception:
                    pass

            result = await process_message(
                message=message,
                customer_id=customer_id,
                conversation_id=conversation_id,
                image=image,
                event_callback=send_event,
            )

            # Send final done event
            await ws.send_json({
                "type": "done",
                "data": {
                    "conversation_id": result["conversation_id"],
                    "response": result["response"],
                    "agent": result["agent"],
                    "model": result["model"],
                    "qgpu_slice": result["qgpu_slice"],
                    "classification": result["classification"],
                    "total_latency_ms": result["total_latency_ms"],
                }
            })

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


# ──────────────────────── Utility Endpoints ────────────────────────

@app.get("/customers")
async def list_customers():
    return CustomerTools.list_customers()


@app.get("/customers/{customer_id}")
async def get_customer(customer_id: str):
    result = CustomerTools.get_customer(customer_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "mock_llm": settings.mock_llm,
        "models": {
            "model1": {"name": settings.model1_display, "endpoint": settings.model1_base_url, "slice": settings.model1_qgpu_slice},
            "model2": {"name": settings.model2_display, "endpoint": settings.model2_base_url, "slice": settings.model2_qgpu_slice},
        }
    }


@app.get("/scenarios")
async def list_scenarios():
    """List demo scenarios for easy testing."""
    return {
        "scenarios": [
            {
                "id": 1,
                "name": "Order Tracking (text)",
                "message": "Where is my Samsung order?",
                "customer_id": "C-1001",
                "description": "Routes to Order Tracker via Slice 2, finds in-transit Samsung order"
            },
            {
                "id": 2,
                "name": "Order Tracking (image)",
                "message": "Can you find this order?",
                "customer_id": "C-1001",
                "image": True,
                "description": "Vision: reads order ID from screenshot, routes to Order Tracker"
            },
            {
                "id": 3,
                "name": "Return with Defect Photo",
                "message": "I want to return this, it arrived broken",
                "customer_id": "C-1003",
                "image": True,
                "description": "Vision: analyzes damage photo, fast-tracks return with free pickup"
            },
            {
                "id": 4,
                "name": "Product Comparison (thinking)",
                "message": "Should I get the LG C4 OLED or Samsung S90D?",
                "customer_id": "C-1001",
                "description": "Product Advisor with Qwen3 thinking mode, detailed comparison"
            },
            {
                "id": 5,
                "name": "Product ID from Photo",
                "message": "I have this at home, looking for a compatible case",
                "customer_id": "C-1001",
                "image": True,
                "description": "Vision: identifies phone from photo, searches compatible accessories"
            },
            {
                "id": 6,
                "name": "Mid-conversation Reroute",
                "messages": [
                    "Where is my TV order?",
                    "Actually I want to cancel it"
                ],
                "customer_id": "C-1001",
                "description": "Order Tracker -> reroute to Returns Agent, shows handoff"
            },
            {
                "id": 7,
                "name": "Escalation",
                "message": "I've called 5 times, nobody helps, I'm filing a complaint",
                "customer_id": "C-1003",
                "description": "Detects frustration, escalates with case reference"
            },
        ]
    }


@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    if conversation_id in conversations:
        del conversations[conversation_id]
    return {"status": "cleared"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
