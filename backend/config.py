"""
Multi-model configuration. Each agent type points to a different inference server.
Two TACO-LLM/vLLM servers run on the same GPU via qGPU slicing.
"""
from pydantic_settings import BaseSettings


class ModelEndpoint:
    """One inference server = one model on one qGPU slice."""
    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name


class Settings(BaseSettings):
    # Model Server 1: Qwen3-VL-8B (Router + Product Advisor)
    model1_base_url: str = "http://localhost:8081/v1"
    model1_api_key: str = "demo-key"
    model1_name: str = "qwen3-vl-8b"
    model1_display: str = "Qwen3-VL-8B"
    model1_qgpu_slice: str = "Slice 1 (16GB)"

    # Model Server 2: Qwen2.5-VL-7B (Order Tracker + Returns)
    model2_base_url: str = "http://localhost:8082/v1"
    model2_api_key: str = "demo-key"
    model2_name: str = "qwen2.5-vl-7b"
    model2_display: str = "Qwen2.5-VL-7B"
    model2_qgpu_slice: str = "Slice 2 (16GB)"

    # Agent behavior
    router_temperature: float = 0.1
    agent_temperature: float = 0.7
    llm_timeout: int = 30
    max_tool_iterations: int = 5
    max_reroutes: int = 2
    max_history_messages: int = 20

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]

    # Feature flags
    mock_llm: bool = False
    enable_streaming: bool = True
    debug_mode: bool = True

    class Config:
        env_file = ".env"

    def get_model_endpoint(self, agent_type: str) -> ModelEndpoint:
        """Return the correct model endpoint for each agent type."""
        if agent_type in ("router", "product_advisor"):
            return ModelEndpoint(self.model1_base_url, self.model1_api_key, self.model1_name)
        elif agent_type in ("order_tracker", "returns"):
            return ModelEndpoint(self.model2_base_url, self.model2_api_key, self.model2_name)
        else:
            return ModelEndpoint(self.model1_base_url, self.model1_api_key, self.model1_name)

    def get_model_info(self, agent_type: str) -> dict:
        """Return display info for the debug panel."""
        if agent_type in ("router", "product_advisor"):
            return {
                "model": self.model1_display,
                "qgpu_slice": self.model1_qgpu_slice,
                "endpoint": self.model1_base_url,
            }
        else:
            return {
                "model": self.model2_display,
                "qgpu_slice": self.model2_qgpu_slice,
                "endpoint": self.model2_base_url,
            }


settings = Settings()
