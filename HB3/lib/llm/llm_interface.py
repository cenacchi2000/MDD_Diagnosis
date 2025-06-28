gpt_interface = system.import_library("./openai/gpt_interface.py")
service_proxy_interface = system.import_library(
    "./service_proxy_llm/service_proxy_llm_interface.py"
)

# Use GPT if openai credentials are provided, else service_proxy
match (gpt_interface.client, service_proxy_interface.client):
    case (None, None):
        raise Exception("Couldn't find valid credentials for GPT or for Service Proxy")
    case (_, None):
        implementation = gpt_interface
        log.info("Using GPT LLM")
    case (None, _):
        implementation = service_proxy_interface
        log.info("Using Service Proxy LLM")
    case (_, _):
        implementation = gpt_interface
        log.warning(
            "Found service proxy credentials and openai credentials. Defaulting to openai. To use service proxy, you must delete the file at /home/tritium/openai_key.txt"
        )

implementation = (
    gpt_interface if gpt_interface.client is not None else service_proxy_interface
)

run_chat = implementation.run_chat
run_chat_streamed = implementation.run_chat_streamed
run_completion = implementation.run_completion
start = implementation.start
stop = implementation.stop
