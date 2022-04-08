import asyncio
import httpx
from datetime import datetime
from pymongo import collection


async def fetch(client, token_uri, collection) -> tuple:
    id = token_uri.split("/")[-1]
    response = await client.get(token_uri)
    metadata = response.json()
    metadata["_id"] = int(id)
    metadata["last_updated"] = datetime.utcnow()

    collection.insert_one(metadata)

    return (id, metadata)


async def make_requests(urls: list, collection: collection) -> None:
    limits = httpx.Limits(max_connections=10000, max_keepalive_connections=50)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = []
        for url in urls:
            tasks.append(fetch(client=client, token_uri=url, collection=collection))
        result = await asyncio.gather(*tasks)
        return result
