import json
import uuid
import asyncio
import dataclasses
from random import randrange
from typing import Optional, AsyncGenerator

import websockets
from tritium.serde import deserialize_from_dict
from websockets.client import connect
from websockets.exceptions import InvalidURI, InvalidHandshake

RAGResources = system.import_library("../../../robot_state/RAGCollectionInfo.py")


@dataclasses.dataclass
class RequestStatus:
    item_id: str
    responses: asyncio.Queue[dict] = dataclasses.field(default_factory=asyncio.Queue)


class ServiceProxyLLMClient:

    MAX_RESPONSE_WAIT_TIME_SECONDS = 30

    def __init__(self, url, system_id, credentials) -> None:
        self.llm_items: dict[str, RequestStatus] = {}
        self.request_queue: asyncio.Queue[str] = asyncio.Queue()
        self.url = url
        self.system_id = system_id
        self.credentials = credentials
        self._connection_task = None
        self._needs_to_reconnect = asyncio.Event()
        self._connection_ready = asyncio.Event()
        self._disconnect = asyncio.Event()

    async def start(self):
        self.stop()
        # Old connection clean up, doing it here because `Activit.on_stop()` can not be async
        if self._connection_task:
            await self._connection_task
        self._disconnect.clear()
        self._connection_task = asyncio.create_task(self._connection(self._disconnect))

    def stop(self):
        if self._connection_task:
            self._disconnect.set()

    async def _connection(self, _disconnect: asyncio.Event):
        async def cancel_task_log_exceptions(task: asyncio.Task):
            if task:
                task.cancel()
                try:
                    await task
                except (
                    websockets.exceptions.ConnectionClosedError,
                    websockets.exceptions.ConnectionClosedOK,
                    asyncio.CancelledError,
                ):
                    pass
                except Exception:
                    log.exception("Error while cancelling response_task")

        while not _disconnect.is_set():
            responses_loop: asyncio.Task | None = None
            requests_loop: asyncio.Task | None = None
            try:
                async with connect(
                    self.url,
                    extra_headers={
                        "x-tritium-system-uuid": self.system_id,
                        "x-tritium-system-token": self.credentials,
                    },
                    open_timeout=5,
                ) as websocket:
                    log.info(f'Connected to "{self.url}"')

                    responses_loop = asyncio.create_task(
                        self._handle_response(websocket, _disconnect)
                    )
                    requests_loop = asyncio.create_task(
                        self._handle_request(websocket, _disconnect)
                    )

                    while True:
                        _ = await asyncio.wait(
                            [responses_loop, requests_loop],
                            return_when=asyncio.FIRST_COMPLETED,
                        )
                        if responses_loop.done():
                            responses_loop.result()  # Raise error...
                            break  # We deliberately disconnected...
                        if requests_loop.done():
                            requests_loop.result()  # Raise error...
                            break  # We deliberately disconnected...

            except websockets.ConnectionClosed:
                log.warning("Connection closed, reconnecting ...")
            except (ConnectionRefusedError, asyncio.TimeoutError):
                log.warning("Failed to connect, reconnecting ...")
            except (InvalidHandshake, InvalidURI, OSError):
                log.error(
                    "Unable to establish connection. Check tritium credentials are valid, and connectivity, trying to reconnect ..."
                )
            except Exception:
                log.exception("Unhandled connection error, reconnecting ...")
            finally:
                self._connection_ready.clear()
                await cancel_task_log_exceptions(responses_loop)
                await cancel_task_log_exceptions(requests_loop)

            self.llm_items.clear()
            await asyncio.sleep(
                randrange(10, 50) / 10
            )  # wait 1-5 seconds before trying to reconnect

    async def _handle_request(
        self, ws: websockets.WebSocketClientProtocol, _disconnect: asyncio.Event
    ):
        async def _process_request_queue(
            ws: websockets.WebSocketClientProtocol,
        ) -> None:
            while True:
                try:
                    request = await self.request_queue.get()
                    await ws.send(request)
                    log.info(f"Request sent: {request}")
                except websockets.exceptions.WebSocketException:
                    # Propagate WebSocket exceptions for reconnection handling, etc.
                    raise
                except Exception:
                    log.exception("Error while sending request")
                    raise

        disconnect_task = asyncio.create_task(_disconnect.wait())
        getter_task = asyncio.create_task(_process_request_queue(ws))

        self._connection_ready.set()
        log.info("Connection ready")
        try:
            # Wait until either the disconnect event or the getter task terminates.
            _, pending = await asyncio.wait(
                [disconnect_task, getter_task], return_when=asyncio.FIRST_COMPLETED
            )

            # If disconnect was triggered, cancel the getter task.
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        except asyncio.CancelledError:
            # If _handle_request is canceled externally, cancel both tasks.
            disconnect_task.cancel()
            getter_task.cancel()
            # Optionally we safeguard completion of cancellation of the tasks.
            await asyncio.gather(disconnect_task, getter_task, return_exceptions=True)
            raise

    async def _handle_response(
        self, ws: websockets.WebSocketClientProtocol, _disconnect: asyncio.Event
    ):
        recv_task = asyncio.create_task(ws.recv())
        disconnect_task = asyncio.create_task(_disconnect.wait())

        while True:
            done, _ = await asyncio.wait(
                [disconnect_task, recv_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if disconnect_task in done:
                recv_task.cancel()
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass
                break

            if recv_task in done:
                try:
                    message = recv_task.result()
                    payload = json.loads(message)

                    response = payload["response"]
                    response_type = response["type"]
                    response_id = response["item_id"]
                    match response_type:
                        case "llm_chunk" | "llm_done" | "error":
                            if response_id is None:
                                log.error(f"Error response: {response['message']}")
                                return  # reconnect
                            try:
                                await self.llm_items[response_id].responses.put(payload)
                            except KeyError:
                                log.error(
                                    f"No matching `item_id` found for res: {response}\n {self.llm_items.keys()}"
                                )
                                return  # reconnect
                        case "reconnect":
                            log.info("Reconnect request received, reconnecting now")
                            break
                        case "schema":
                            meta_data = response.get("meta_info", None)
                            # Publish RAGCollectionInfoList global_resource from meta_data
                            if meta_data is not None and "rag_collection" in meta_data:
                                RAGResources.RAGCollectionInfoList.set(
                                    deserialize_from_dict(
                                        meta_data, RAGResources.RAGCollectionInfoList
                                    )
                                )
                        case other:
                            log.error(f"Unexpected response type: {other!r}")
                except websockets.exceptions.ConnectionClosed:
                    raise
                except Exception:
                    log.exception("Error in _handle_response while receiving message")
                # start a new recv_task for the next iteration
                recv_task = asyncio.create_task(ws.recv())

    async def _request(
        self,
        request_id: str,
        model: str,
        message: list[dict],
        function: Optional[list[dict]] = None,
        backend: Optional[dict] = None,
        parent_item_id: Optional[str] = None,
        purpose: Optional[str] = None,
        post_process: Optional[list[str]] = [
            "re_sentence_chunker_v1",
            "ml_lang_detector_v2",
        ],
        **kwargs,
    ):
        assert (
            self._connection_task is not None
        ), "Attempt to call LLM function but `start` hasn't been called on the client yet"
        request: dict = {
            "item_id": request_id,
            "model": model,
            "messages": message,
            "post_process": post_process,
            "parent_item_id": parent_item_id,
            "purpose": purpose,
        }
        if function:
            request.update({"function": function})
        if backend:
            request.update({"backend": backend})

        retries: int = 3
        for attempt in range(retries):
            try:
                await asyncio.wait_for(
                    self._connection_ready.wait(),
                    (ServiceProxyLLMClient.MAX_RESPONSE_WAIT_TIME_SECONDS / 10),
                )
                break  # Exit the loop if the connection becomes ready
            except asyncio.TimeoutError:
                if attempt < retries - 1:
                    log.warning(
                        "llm request pending, waiting for connection to be ready ..."
                    )
                else:
                    raise asyncio.TimeoutError(
                        "LLM connection has not been established"
                    )

        try:
            msg: str = json.dumps(request)
            self.llm_items[request_id] = RequestStatus(request_id)
            await self.request_queue.put(msg)
        except Exception:
            log.exception(
                "Failed to send LLM request",
                warning=True,
            )
            log.error(f"request the caused the error: {request}")
            raise

    async def run_chat_streamed(
        self,
        model: str,
        messages: list[dict],
        functions: Optional[list[dict]] = None,
        parent_item_id: Optional[str] = None,
        purpose: Optional[str] = None,
        **kwargs,
    ) -> Optional[AsyncGenerator[dict[str, str], None]]:
        request_id = str(uuid.uuid4())
        backend: dict[str, any] = kwargs
        try:
            await self._request(
                request_id,
                model=model,
                message=messages,
                function=functions,
                backend=backend,
                parent_item_id=parent_item_id,
                purpose=purpose,
            )
        except asyncio.TimeoutError as e:
            log.error(f"{e}: {request_id}: \n {messages}")
            return

        request_status = self.llm_items[request_id]

        async def response_generator():
            while True:
                # Create two tasks: one for the response and one for self._disconnect.wait()
                response_task = asyncio.create_task(request_status.responses.get())
                disconnect_task = asyncio.create_task(self._disconnect.wait())

                # Wait for either the response or the disconnect.
                done, _ = await asyncio.wait(
                    [response_task, disconnect_task],
                    timeout=ServiceProxyLLMClient.MAX_RESPONSE_WAIT_TIME_SECONDS,
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if disconnect_task in done:
                    log.warning(
                        "Disconnect event set during wait; stopping response generation."
                    )
                    # Cancel the other pending task.
                    if not response_task.done():
                        response_task.cancel()
                    return

                if response_task not in done:
                    log.error(f"service proxy LLM timeout: {request_id}: \n {messages}")
                    self.llm_items.pop(request_id, None)
                    disconnect_task.cancel()
                    return

                # Response is ready.
                response = response_task.result()
                disconnect_task.cancel()
                item: dict = response["response"]

                res_type: str = item.get("type")

                match res_type:
                    case "llm_chunk":
                        yield item.copy()
                    case "llm_done":
                        self.llm_items.pop(request_id, None)
                        return
                    case "error":
                        log.error(f"Error: {item}")
                        self.llm_items.pop(request_id, None)
                        return
                    case _:
                        log.warning(f"Unhandled item: {item}")

        return response_generator()

    async def run_chat(
        self,
        model: str,
        messages=list[dict],
        functions: Optional[list[dict]] = None,
        parent_item_id: Optional[str] = None,
        purpose: Optional[str] = None,
        **kwargs,
    ) -> Optional[dict[str, any]]:
        backend: dict[str, any] = kwargs
        request_id = str(uuid.uuid4())
        try:
            await self._request(
                request_id,
                model=model,
                message=messages,
                function=functions,
                post_process=["re_sentence_chunker_v1"],
                backend=backend,
                parent_item_id=parent_item_id,
                purpose=purpose,
            )
        except asyncio.TimeoutError as e:
            log.error(f"{e}: {request_id}: \n {messages}")
            return

        request_status = self.llm_items[request_id]

        while True:
            # Create two tasks: one for the response and one for self._disconnect.wait()
            response_task = asyncio.create_task(request_status.responses.get())
            disconnect_task = asyncio.create_task(self._disconnect.wait())

            # Wait for either the response or the disconnect.
            done, _ = await asyncio.wait(
                [response_task, disconnect_task],
                timeout=ServiceProxyLLMClient.MAX_RESPONSE_WAIT_TIME_SECONDS,
                return_when=asyncio.FIRST_COMPLETED,
            )

            if disconnect_task in done:
                log.warning(
                    "Disconnect event set during wait; stopping response generation."
                )
                # Cancel the other pending task.
                if not response_task.done():
                    response_task.cancel()
                return

            if response_task not in done:
                log.error(f"service proxy LLM timeout: {request_id}: \n {messages}")
                self.llm_items.pop(request_id, None)
                disconnect_task.cancel()
                return

            # Response is ready.
            response = response_task.result()
            disconnect_task.cancel()
            item: dict = response["response"]

            res_type: str = item.get("type")

            match (res_type):
                case "llm_chunk":
                    pass
                case "llm_done":
                    choices: list[dict] = item["choices"]
                    index: Optional[int] = None
                    role: Optional[str] = None
                    content: str = ""
                    for c in choices:
                        delta = c["delta"]
                        index = c["index"] if index is None else index
                        role = delta["role"] if role is None else role
                        if index == c["index"] and isinstance(delta["content"], str):
                            content += delta["content"]

                    self.llm_items.pop(request_id)
                    return {"content": content, "role": role}
                case "error":
                    log.error(f"Error: {item}")
                    self.llm_items.pop(request_id)
                    return
                case _:
                    log.warning(f"Unhandled item: {item}")

    async def run_completion(self, **kwargs) -> Optional[dict[str, any]]:
        """Run the completion mode, with no streaming."""
        raise NotImplementedError("run_completion() not implemented")