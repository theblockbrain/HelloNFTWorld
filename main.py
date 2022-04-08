import os

from typing import Optional

from fastapi import FastAPI
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

w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_INFURA_URL")))

IPFS_AUTH = (os.getenv("INFURA_IPFS_PROJECT"), os.getenv("INFURA_IPFS_SECRET"))

# initialize ETH
eth = Etherscan(os.getenv("ES-TOKEN"))

from metadata import get_collection_meta


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/metadata/{collection_address}")
async def get_metadata(collection_address: str, token_id: Optional[int] = None):
    res = await get_collection_meta(collection_address.lower(), token_id=token_id)

    return res
