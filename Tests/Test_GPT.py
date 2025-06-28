gpt_functions = system.import_library("../HB3/lib/llm/llm_interface.py")


class Activity:
    async def on_start(self):
        kwargs = dict(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a poetic assistant, skilled in explaining complex programming concepts with creative flair.",
                },
                {
                    "role": "user",
                    "content": "Compose a poem that explains the concept of recursion in programming.",
                },
            ],
        )

        result = await gpt_functions.run_chat(**kwargs)
        log.info(f"non-streamed result: {result}")

        generator = await gpt_functions.run_chat_streamed(**kwargs)
        log.info(f"streamed response: {generator}")
        if generator:
            async for item in generator:
                log.info(f"chunk: {item}")
