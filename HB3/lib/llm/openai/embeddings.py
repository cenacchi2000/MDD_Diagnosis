llm_functions = system.import_library("./utils.py")

client = system.import_library("./setup.py").CLIENT


@llm_functions.try_n_times
async def get_embedding(input_str: str, engine: str):
    return await client.embeddings.create(
        input=input_str,
        model=engine,
    )
