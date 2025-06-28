from typing import Optional, AsyncGenerator

client = system.import_library("./setup.py").CLIENT
llm_functions = system.import_library("./utils.py")
stream_outputs = system.import_library("../../../chat/lib/utils.py")


def verify_kwargs(kwargs):
    # Our scripts current don't define actions as tool calls, but as deprecated functions.
    # We can easily translate them here so we do that (service proxy does this server-side)
    # This allows us to use `tool_choice=required` which is not available with function arg
    assert "tools" not in kwargs
    tools = [
        {"type": "function", "function": f} for f in (kwargs.pop("functions", []) or [])
    ]
    if tools:
        kwargs["tools"] = tools
    # This is only used for Service Proxy - this interface only supports openai
    assert kwargs.pop("name", "openai_chat") == "openai_chat"
    kwargs.pop("parent_item_id", None)
    kwargs.pop("purpose", None)
    return kwargs


@llm_functions.try_n_times
async def run_chat(**kwargs) -> Optional[dict[str, any]]:
    """Run the chatcompletion mode, with no streaming."""
    assert (
        client is not None
    ), "Attempt to call openai interface but client has not been properly setup."

    kwargs = verify_kwargs(kwargs)

    resp = await client.chat.completions.create(**kwargs)
    return resp.choices[0].message.model_dump()


@llm_functions.try_n_times  # This does not work when the AsyncGenerator throws
async def run_chat_streamed(
    min_chunk_length=4, **kwargs
) -> Optional[AsyncGenerator[dict[str, str], None]]:
    """Run the chatcompletion mode in streaming mode.

    Args:
        min_chunk_length: Prevents streaming chunks with fewer characters if possible.

    Returns:
        A generator of chunks of the openai response, or None if there has been an error.
    """
    return await get_streamed_responses(min_chunk_length=min_chunk_length, **kwargs)


async def get_streamed_responses(
    min_chunk_length=0, **kwargs
) -> AsyncGenerator[dict[str, str], None]:
    """Get the responses from openai.

    Args:
        **kwargs: kwargs to pass to the openai.chat.completions initialiser.

    Yields:
        Generator[dict[str, str], None, None]: the chunks of responses to the openai request.
    """
    assert (
        client is not None
    ), "Attempt to call openai interface but client has not been properly setup."

    kwargs = verify_kwargs(kwargs)

    assert min_chunk_length >= 0, "min_chunk_length cannot be negative"
    stream = await client.chat.completions.create(stream=True, **kwargs)

    def apply_delta(
        buffer: dict,
        delta: any,
    ) -> dict:
        if delta.content:
            buffer["content"] += delta.content
        if delta.tool_calls:
            for tc in delta.tool_calls:
                if len(buffer["tool_calls"]) < tc.index + 1:
                    buffer["tool_calls"].append(
                        {
                            "id": None,
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": "",
                            },
                        }
                    )
                    assert len(buffer["tool_calls"]) == tc.index + 1
                buf = buffer["tool_calls"][tc.index]
                if tc.id:
                    buf["id"] = tc.id
                if tc.function.name:
                    buf["function"]["name"] += tc.function.name
                if tc.function.arguments:
                    buf["function"]["arguments"] += tc.function.arguments
        return buffer

    async def response_generator():
        buffer = {
            "content": "",
            "role": "assistant",
            "tool_calls": [],
        }
        async with stream as response_stream:
            async for response_chunk in response_stream:
                choice = response_chunk.choices[0]

                if choice.delta:
                    buffer = apply_delta(buffer, choice.delta)

                finish_reason = choice.finish_reason
                if finish_reason is not None:
                    break
                # Check if we can start streaming tts. If we are doing a function call, ignore the streaming.
                elif buffer["content"] and not buffer["tool_calls"]:
                    yield_content, remaining_content = stream_outputs.string_chunker(
                        buffer["content"], min_chunk_length
                    )
                    if yield_content:
                        yield {
                            "content": yield_content,
                            "role": "assistant",
                            "tool_calls": None,
                        }
                    buffer["content"] = remaining_content
            if buffer["content"] or buffer["tool_calls"]:
                yield buffer

    return response_generator()


@llm_functions.try_n_times
async def run_completion(**kwargs) -> Optional[dict[str, any]]:
    """Run the completion mode, with no streaming."""
    assert (
        client is not None
    ), "Attempt to call openai interface but client has not been properly setup."
    kwargs = verify_kwargs(kwargs)
    resp = await client.completions.create(**kwargs)
    return resp.choices[0].model_dump()


async def start():
    pass


def stop():
    pass