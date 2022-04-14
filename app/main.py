import asyncio
from operator import itemgetter
import os

from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from web3 import Web3
from etherscan import Etherscan
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

origins = ["http://localhost:3000", "https://nft.wassenich.dev"]

app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"]
)

client = MongoClient(os.getenv("MONGODB_STRING"), 27017)
gen_db = client.bb_hackathon
rarity_db = client.rarity

abi_collection = gen_db.abis
slug_collection = gen_db.slugs

w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_INFURA_URL")))

IPFS_AUTH = (os.getenv("INFURA_IPFS_PROJECT"), os.getenv("INFURA_IPFS_SECRET"))

# initialize ETH
eth = Etherscan(os.getenv("ES-TOKEN"))

from app.metadata import get_collection_meta, get_rarity_meta, database_rarity_check
from app.os_api import get_collection_slug, get_os_sales_events
from app.salesdata import curve_fitter, estimate_values


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
    rarity = get_rarity_meta(collection_address.lower())
    A, B = curve_fitter(
        collection_address=collection_address.lower(), rarity_data=rarity, method=method
    )

    return f"Fitted Curve: {A}*exp({B}*x)"


@app.get("/estimates/{collection_address}")
async def get_estimates(collection_address: str):
    rarity_coll = rarity_db[collection_address.lower()]
    doc = rarity_coll.find_one({})
    if not doc:
        print("need to get metadata")
        res = await asyncio.wait_for(
            get_collection_meta(collection_address.lower()), timeout=None
        )
    rarity = get_rarity_meta(collection_address.lower())

    A, B = curve_fitter(collection_address.lower(), rarity_data=rarity)
    estimates = estimate_values(A, B, rarity_information=rarity)
    sorted_estimates = sorted(estimates, key=itemgetter("token_id"))

    return sorted_estimates


@app.get("/front-end/{collection_address}")
async def frontend_get_data(collection_address: str):
    rarity_coll = rarity_db[collection_address.lower()]
    await asyncio.wait_for(
        get_collection_meta(collection_address.lower()), timeout=None
    )

    missing_rarity = list(database_rarity_check(rarity_collection=rarity_coll))
    print(f"From Main function: {len(missing_rarity)} missing rarity docs!")
    rarity = get_rarity_meta(collection_address.lower())

    A, B = curve_fitter(collection_address.lower(), rarity_data=rarity)
    estimates = estimate_values(A, B, rarity_information=rarity)

    for token in rarity:
        match = next((x for x in estimates if x["token_id"] == token["_id"]), None)
        token.update(match)

    return rarity
