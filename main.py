import os

from typing import Optional

from fastapi import FastAPI
from matplotlib.pyplot import sci
from pymongo import MongoClient
from web3 import Web3
from etherscan import Etherscan
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

client = MongoClient(os.getenv("MONGODB_STRING"), 27017)
gen_db = client.bb_hackathon
rarity_db = client.rarity

abi_collection = gen_db.abis
slug_collection = gen_db.slugs

w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_INFURA_URL")))

IPFS_AUTH = (os.getenv("INFURA_IPFS_PROJECT"), os.getenv("INFURA_IPFS_SECRET"))

# initialize ETH
eth = Etherscan(os.getenv("ES-TOKEN"))

from metadata import get_collection_meta, get_rarity_meta
from os_api import get_collection_slug, get_os_sales_events
from salesdata import (
    map_sales,
    transform_sales_to_arrays,
    scipy_fit,
    poly_fit,
    curve_fit,
)


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/metadata/{collection_address}")
async def get_metadata(collection_address: str, token_id: Optional[int] = None):
    # TODO: Querying metadata for single tokens
    res = await get_collection_meta(collection_address.lower(), token_id=token_id)

    return res


@app.get("/rarity/{collection_address}")
def get_rarity(collection_address: str):
    rarity = get_rarity_meta(collection_address.lower())
    return rarity


@app.get("/os-sales/{collection_address}")
def get_os_sales(collection_address: str, token_id: Optional[int] = None):
    slug_doc = slug_collection.find_one({"_id": collection_address.lower()})
    if slug_doc:
        slug = slug_doc["slug"]
    else:
        slug = get_collection_slug(collection_address.lower())
    sales_events = get_os_sales_events(slug, num_queries=4)
    print(len(sales_events))
    return sales_events


@app.get("/curve-fit/{collection_address}")
def get_curve(collection_address: str, method: Optional[str] = "scipy"):
    slug_doc = slug_collection.find_one({"_id": collection_address.lower()})
    if slug_doc:
        slug = slug_doc["slug"]
    else:
        slug = get_collection_slug(collection_address.lower())
    sales_events = get_os_sales_events(slug, num_queries=4)
    rarity_data = rarity_db[collection_address.lower()].find({})

    mapped_sales = map_sales(sales_events=sales_events, rarity_data=rarity_data)
    x, y = transform_sales_to_arrays(mapped_sales, x_kpi="points", y_kpi="total_price")

    match method:
        case "scipy":
            A, B = scipy_fit(x, y, (18, 0.01))
        case "poly":
            A, B = poly_fit(x, y)
        case "curve":
            A, B = poly_fit(x, y)

    return f"Fitted Curve: {A}*exp({B}*x)"
