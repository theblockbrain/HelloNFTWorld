import asyncio
from typing import Tuple
import httpx
from datetime import datetime
from pymongo import collection, errors

"""
To speed up the querying of metadata, I dabbled a bit in async here (first time)
httpx is generally working fine, but I had to slap on a semaphore to avoid any PoolTimeouts.
This is surely optimizable, as I have only a very limited understanding of async in Python.
"""


async def fetch(client, token_uri, collection, semaphore) -> tuple:
    async with semaphore:
        id = token_uri.split("/")[-1]
        response = await client.get(token_uri)
        metadata = response.json()
        metadata["_id"] = int("".join(c for c in id if c.isdigit()))
        metadata["last_updated"] = datetime.utcnow()

        try:
            collection.insert_one(metadata)
        except errors.DuplicateKeyError:
            pass

        return (id, metadata)


async def make_requests(urls: list, collection: collection) -> list:
    # windows supports 64 connections max
    limits = httpx.Limits(max_connections=60, max_keepalive_connections=30)
    timeout = httpx.Timeout(10.0, read=None)
    client = httpx.AsyncClient(limits=limits, timeout=timeout)
    # keeps httpx from throwing a PoolTimeout
    semaphore = asyncio.Semaphore(60)

    async with client:
        tasks = []
        for url in urls:
            tasks.append(
                fetch(
                    client=client,
                    token_uri=url,
                    collection=collection,
                    semaphore=semaphore,
                )
            )
        result = await asyncio.gather(*tasks)
        return result
