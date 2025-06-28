import functools

from yaml import YAMLError
from ea.util.yaml import safe_load

client = system.import_library("./setup.py").CLIENT


def try_n_times(func):
    @functools.wraps(func)
    async def _wrapper(max_tries=2, *args, **kwargs):
        if client is None:
            raise Exception(
                "Attempt to use a GPT function but the OpenAI key has not been set."
            )
        import openai

        for i in range(max_tries):
            if i > 0:
                log.warning("Retrying the OpenAI call...")
            try:
                return await func(*args, **kwargs)
            except openai.APIStatusError as e:
                if e.status_code == 400:
                    log.error(f"OpenAI 400 Error (will not retry): {e}")
                    return None
                log.error(f"OpenAI Error: {e}")
            except (openai.APITimeoutError, openai.APIError) as e:
                log.error(f"OpenAI Error: {e}")
            except Exception as e:
                log.error(f"Unhandled error when running openai model: {e}")
                return None
        log.error("Max retry reached.")
        return None

    return _wrapper
