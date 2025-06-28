import os
import asyncio

import numpy as np

embeddings = system.import_library("./llm/openai/embeddings.py")

CONFIG = system.import_library("../../Config/Chat.py").CONFIG

EMBEDDING_MODEL = "text-embedding-ada-002"
CACHE_DIR = "/home/tritium/vector_search_cache"
if not os.path.isdir(CACHE_DIR):
    os.makedirs(CACHE_DIR)


def load_from_cache(sentence):
    cache_path = os.path.join(CACHE_DIR, sentence + ".npy")
    if os.path.isfile(cache_path):
        return np.load(cache_path, allow_pickle=False), True
    else:
        return None, False


def save_to_cache(sentence, embeds):
    cache_path = os.path.join(CACHE_DIR, sentence)
    try:
        np.save(cache_path, embeds, allow_pickle=False)
    except OSError as e:
        probe("Error::", "save_to_cache" + str(e))


async def get_embeds(sentence):
    loaded_vec, loaded = load_from_cache(sentence)
    if loaded:
        return loaded_vec
    # If not cached, regenerate
    res = await embeddings.get_embedding(
        input_str=sentence,
        engine=EMBEDDING_MODEL,
    )
    embeds = [record.embedding for record in res.data]
    embeds = np.array(embeds, dtype=np.float32)
    # Save to cache
    save_to_cache(sentence, embeds)
    return embeds


class L2_String_Vector_Index:
    embedding_tasks = set()

    def __init__(self, dimension=1536):
        self._index = []
        self._contents = []
        self._meta_data = []

    async def fetch_embeds_and_add(self, sentence, meta_data):
        embeds = await get_embeds(sentence)
        self._contents.append(sentence)
        self._meta_data.append(meta_data)
        self._index.append(embeds)

    def add(self, *items):
        # TODO: Batch the embeds
        for item in items:
            sentence = item["sentence"]
            meta_data = item["meta_data"]
            if sentence in self._contents:
                continue
            loop = asyncio.get_event_loop()
            task = loop.create_task(self.fetch_embeds_and_add(sentence, meta_data))
            self.embedding_tasks.add(task)
            task.add_done_callback(lambda _: self.embedding_tasks.remove(task))

    def remove(self):
        pass

    async def query(self, query, k=1):
        def L2(a, b):
            return np.sqrt(np.sum(np.power(a - b, 2)))

        embeds = await get_embeds(query)
        distances_and_indices = sorted(
            [[L2(embeds, I), idx] for idx, I in enumerate(self._index)]
        )[:k]
        query_results = []
        result = []
        for idx, (distance, indx) in enumerate(distances_and_indices):
            try:
                indx = int(indx)
            except OverflowError:
                continue
            if indx == -1:
                continue
            result.append(
                {
                    "content": self._contents[indx],
                    "meta_data": self._meta_data[indx],
                    "distance": distance,
                }
            )
        query_results.append(result)
        return query_results