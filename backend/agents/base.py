"""
Base class for all agents.

Each agent connects to a DIFFERENT inference server (different model, different qGPU slice).
The endpoint is resolved via config.get_model_endpoint(agent_type).

Key responsibilities:
- System prompt management
- Tool calling via XML tags (parsed from text output)
- Image handling (both models are VL — can process images!)
- Conversation memory (in-memory for demo)
- Action logging for debug panel (including model + qGPU slice info)
- Re-routing to other agents (which may use a DIFFERENT model)
- Qwen3 thinking mode control (Qwen3-VL-8B only)
"""
import json
import re
import time
import logging
from typing import Any, Callable

import httpx

from config import settings

logger = logging.getLogger(__name__)


class BaseAgent:
    agent_type: str = "base"
    system_prompt: str = ""
    enable_thinking: bool = False
    temperature: float = 0.7
    tools_map: dict[str, Callable] = {}

    def __init__(self):
        self.model_info = settings.get_model_info(self.agent_type)
        self.endpoint = settings.get_model_endpoint(self.agent_type)

    async def process(
        self,
        message: str,
        customer_id: str = "",
        conversation_history: list[dict] | None = None,
        image_data: str | None = None,
        event_callback: Callable | None = None,
    ) -> dict:
        """
        Process a user message through this agent.
        Returns dict with response text and metadata.
        """
        start_time = time.time()
        events = []

        async def emit(event: dict):
            events.append(event)
            if event_callback:
                await event_callback(event)

        # Emit agent_start
        await emit({
            "type": "agent_start",
            "data": {
                "agent": self.agent_type,
                **self.model_info,
            }
        })

        if settings.mock_llm:
            result = await self._mock_process(message, customer_id, image_data, emit)
        else:
            result = await self._llm_process(
                message, customer_id, conversation_history or [], image_data, emit
            )

        elapsed_ms = int((time.time() - start_time) * 1000)
        result["total_latency_ms"] = elapsed_ms
        result["agent"] = self.agent_type
        result["model"] = self.model_info["model"]
        result["qgpu_slice"] = self.model_info["qgpu_slice"]
        result["events"] = events
        return result

    async def _llm_process(
        self,
        message: str,
        customer_id: str,
        history: list[dict],
        image_data: str | None,
        emit: Callable,
    ) -> dict:
        """Call the actual LLM endpoint with tool-calling loop."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add conversation history
        for h in history[-settings.max_history_messages:]:
            messages.append(h)

        # Build user message content
        if image_data:
            content = [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                {"type": "text", "text": message},
            ]
        else:
            content = message

        messages.append({"role": "user", "content": content})

        full_response = ""
        thinking_text = ""
        tool_calls_made = []

        for iteration in range(settings.max_tool_iterations):
            # Call LLM
            llm_start = time.time()
            try:
                async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
                    resp = await client.post(
                        f"{self.endpoint.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.endpoint.api_key}"},
                        json={
                            "model": self.endpoint.model_name,
                            "messages": messages,
                            "temperature": self.temperature,
                            "max_tokens": 1024,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                return {"text": "I'm sorry, I'm having trouble processing your request right now. Please try again.", "error": str(e)}

            llm_ms = int((time.time() - llm_start) * 1000)
            output = data["choices"][0]["message"]["content"]

            # Parse thinking blocks
            think_match = re.search(r"<think>(.*?)</think>", output, re.DOTALL)
            if think_match:
                thinking_text = think_match.group(1).strip()
                await emit({"type": "thinking", "data": {"text": thinking_text}})
                output = re.sub(r"<think>.*?</think>", "", output, flags=re.DOTALL).strip()

            # Check for reroute
            reroute_match = re.search(r"<reroute>(.*?)</reroute>", output, re.DOTALL)
            if reroute_match:
                try:
                    reroute_data = json.loads(reroute_match.group(1))
                    return {
                        "text": re.sub(r"<reroute>.*?</reroute>", "", output, flags=re.DOTALL).strip(),
                        "reroute": reroute_data,
                        "thinking": thinking_text,
                    }
                except json.JSONDecodeError:
                    pass

            # Check for tool calls
            tool_match = re.search(r"<tool_call>(.*?)</tool_call>", output, re.DOTALL)
            if tool_match:
                try:
                    tool_data = json.loads(tool_match.group(1))
                    tool_name = tool_data["name"]
                    tool_args = tool_data.get("args", {})

                    await emit({
                        "type": "tool_call",
                        "data": {"tool": tool_name, "args": tool_args, "status": "executing"}
                    })

                    # Execute tool
                    tool_start = time.time()
                    tool_result = self._execute_tool(tool_name, tool_args)
                    tool_ms = int((time.time() - tool_start) * 1000)

                    await emit({
                        "type": "tool_result",
                        "data": {"tool": tool_name, "result": tool_result, "latency_ms": tool_ms}
                    })

                    tool_calls_made.append({"tool": tool_name, "args": tool_args, "result": tool_result})

                    # Add tool interaction to messages
                    messages.append({"role": "assistant", "content": output})
                    messages.append({
                        "role": "user",
                        "content": f"Tool result for {tool_name}:\n{json.dumps(tool_result, indent=2)}"
                    })
                    continue  # Loop again for more tool calls or final response

                except (json.JSONDecodeError, KeyError) as e:
                    logger.error(f"Tool call parse error: {e}")

            # No tool call — this is the final response
            full_response = output
            break

        # Emit cost
        input_tokens = sum(len(str(m.get("content", ""))) // 4 for m in messages)
        output_tokens = len(full_response) // 4
        await emit({
            "type": "cost",
            "data": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "model": self.model_info["model"],
                "estimated_cost_usd": round((input_tokens + output_tokens) * 0.000001, 6),
            }
        })

        return {
            "text": full_response,
            "thinking": thinking_text,
            "tool_calls": tool_calls_made,
        }

    def _execute_tool(self, tool_name: str, args: dict) -> Any:
        """Execute a tool by name."""
        if tool_name in self.tools_map:
            func = self.tools_map[tool_name]
            try:
                if isinstance(args, dict):
                    return func(**args)
                return func(args)
            except Exception as e:
                return {"error": str(e)}
        return {"error": f"Unknown tool: {tool_name}"}

    async def _mock_process(
        self,
        message: str,
        customer_id: str,
        image_data: str | None,
        emit: Callable,
    ) -> dict:
        """Override in subclasses for mock responses."""
        return {"text": "Mock response not implemented for this agent.", "thinking": "", "tool_calls": []}
