import os
from pathlib import Path


def check_version(openai_version):
    from packaging import version

    if version.parse(openai_version) < version.parse("1.9.0"):
        log.error(
            "OpenAI package not up to date. "
            f"Version is {openai_version}, but needs to be >= 1.9.0. "
            "Please run `pip3 install --user -U openai`."
        )


openai_key_file = Path.home() / "openai_key.txt"
if openai_key_file.exists():
    import openai

    check_version(openai.__version__)
    key = openai_key_file.read_text().strip()
    CLIENT = openai.AsyncOpenAI(api_key=key)
elif "OPENAI_API_KEY" in os.environ:
    import openai

    check_version(openai.__version__)
    CLIENT = openai.AsyncOpenAI()
else:
    CLIENT = None
