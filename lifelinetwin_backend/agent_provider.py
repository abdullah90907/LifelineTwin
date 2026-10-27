"""Standard SDK adapter. No default provider/model, credentials in memory only."""
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from pydantic import SecretStr
from .agent_failures import FailureMetadata, ProviderFailure, safe_request_id
from .agent_context import ContextPolicy, request_metrics, fits, DEFAULT_MAX_INPUT_TOKENS


class ProviderConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class ProviderConfig:
    model: str
    base_url: str
    api_key: SecretStr = field(repr=False)
    token_parameter: str = "max_completion_tokens"
    max_input_tokens: int = DEFAULT_MAX_INPUT_TOKENS
    max_request_bytes: int = 12000
    output_tokens: int = 1800
    tokens_per_minute: int | None = None
    max_rate_wait_seconds: int = 60

    @classmethod
    def from_environment(cls):
        names = ["LIFELINETWIN_LLM_MODEL", "LIFELINETWIN_LLM_BASE_URL", "LIFELINETWIN_LLM_API_KEY"]
        values = [os.getenv(name, "").strip() for name in names]
        if not all(values):
            missing = [name for name, value in zip(names, values) if not value]
            raise ProviderConfigurationError("LLM is not configured; set " + ", ".join(missing))
        parsed = urlsplit(values[1])
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ProviderConfigurationError("LLM base URL must be HTTP(S) without embedded credentials, query or fragment")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ProviderConfigurationError("Plain HTTP LLM endpoints are allowed only on localhost")
        token_parameter = os.getenv("LIFELINETWIN_LLM_TOKEN_PARAMETER", "max_completion_tokens")
        if token_parameter not in ("max_completion_tokens", "max_tokens"):
            raise ProviderConfigurationError("LLM token parameter must be max_completion_tokens or max_tokens")
        limits={}
        for key,env,default,low,high in [
            ("max_input_tokens","LIFELINETWIN_LLM_MAX_INPUT_TOKENS",DEFAULT_MAX_INPUT_TOKENS,1024,32000),
            ("max_request_bytes","LIFELINETWIN_LLM_MAX_REQUEST_BYTES",12000,4096,200000),
            ("output_tokens","LIFELINETWIN_LLM_MAX_OUTPUT_TOKENS",1800,256,1800),
            ("tokens_per_minute","LIFELINETWIN_LLM_TOKENS_PER_MINUTE",None,1024,1000000),
            ("max_rate_wait_seconds","LIFELINETWIN_LLM_MAX_RATE_WAIT_SECONDS",60,0,60)]:
            raw=os.getenv(env)
            try:
                number=int(raw) if raw else default
            except ValueError:
                raise ProviderConfigurationError(env+" must be an integer") from None
            if number is not None and not low<=number<=high:
                raise ProviderConfigurationError(env+" is outside supported bounds")
            limits[key]=number
        return cls(values[0], values[1], SecretStr(values[2]), token_parameter, **limits)


class OpenAICompatibleProvider:
    def __init__(self, config):
        self.config = config
        self.secret = config.api_key.get_secret_value()
        self.identity = {"adapter": "openai_python_chat_completions", "configured_model": config.model,
                         "base_url": config.base_url, "live_llm": True}
        self.context_policy = ContextPolicy(config.max_input_tokens,config.max_request_bytes,config.output_tokens,config.tokens_per_minute,config.max_rate_wait_seconds)

    def complete(self, messages, tools, timeout):
        from openai import OpenAI
        metrics=request_metrics(messages,tools,self.config.model,self.config.token_parameter,self.context_policy)
        if not fits(metrics):
            raise ProviderFailure(FailureMetadata(category="context_budget",stage="context_management"))
        # No retries or implicit endpoint/model. Keys never enter messages or persistence.
        with OpenAI(api_key=self.secret, base_url=self.config.base_url, timeout=timeout, max_retries=0) as client:
            response = client.chat.completions.create(model=self.config.model, messages=messages,
                tools=tools, tool_choice="auto", **{self.config.token_parameter: self.config.output_tokens})
        request_id = safe_request_id(getattr(response, "_request_id", None))
        try:
            message = response.choices[0].message
            usage={}
            for source,target in (("prompt_tokens","input_tokens"),("completion_tokens","output_tokens"),("total_tokens","total_tokens")):
                value=getattr(getattr(response,"usage",None),source,None)
                if type(value) is int and 0<=value<=10000000:
                    usage[target]=value
            return {"model": response.model, "note": (message.content or "")[:1000],
                    "request_id": request_id,
                    "usage":usage,
                    "calls": [{"id": c.id, "name": c.function.name, "arguments": c.function.arguments}
                              for c in (message.tool_calls or [])]}
        except (AttributeError, IndexError, TypeError):
            raise ProviderFailure(FailureMetadata(category="invalid_agent_output", request_id=request_id,
                                                  stage="provider_response")) from None
