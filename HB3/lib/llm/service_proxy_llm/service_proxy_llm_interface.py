from typing import Optional, AsyncGenerator

from tritium.config import Protocol, get_service_config
from tritium.exceptions import TritiumConfigError

CONFIG = system.import_library("../../../../Config/Chat.py").CONFIG
ServiceProxyLLMClient = system.import_library(
    "./service_proxy_llm_client.py"
).ServiceProxyLLMClient

try:
    service_config = get_service_config(
        Protocol.Websocket, "api/v1/llm", "service_proxy_llm", True
    )
except TritiumConfigError as e:
    log.warning(e)
    service_config = None


if service_config is None:
    client = None
else:
    config = service_config[0]
    service_proxy_url = (
        CONFIG["SERVICE_PROXY_LLM_URL_OVERRIDE"]
        if CONFIG["SERVICE_PROXY_LLM_URL_OVERRIDE"]
        else config.url
    )
    client = ServiceProxyLLMClient(service_proxy_url, config.identifier, config.token)


async def start():
    assert (
        client is not None
    ), "Attempt to use service proxy client but client was not properly initialized"
    await client.start()


def stop():
    assert (
        client is not None
    ), "Attempt to use service proxy client but client was not properly initialized"
    client.stop()


async def run_chat_streamed(
    model: str,
    messages: list[dict],
    functions: Optional[list[dict]] = None,
    min_chunk_length=4,
    parent_item_id: Optional[str] = None,
    purpose: Optional[str] = None,
    **kwargs,
) -> Optional[AsyncGenerator[dict[str, str], None]]:
    assert (
        client is not None
    ), "Attempt to use service proxy client but client was not properly initialized"
    return await client.run_chat_streamed(
        model,
        messages,
        functions,
        parent_item_id=parent_item_id,
        purpose=purpose,
        **kwargs,
    )


async def run_chat(
    model: str,
    messages=list[dict],
    functions: Optional[list[dict]] = None,
    min_chunk_length=4,
    **kwargs,
) -> Optional[dict[str, any]]:
    assert (
        client is not None
    ), "Attempt to use service proxy client but client was not properly initialized"
    return await client.run_chat(
        model,
        messages,
        functions,
        **kwargs,
    )


async def run_completion(**kwargs) -> Optional[dict[str, any]]:
    """Run the completion mode, with no streaming."""
    assert (
        client is not None
    ), "Attempt to use service proxy client but client was not properly initialized"
    return await client.run_completion(**kwargs)