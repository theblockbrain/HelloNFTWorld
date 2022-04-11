import pymongo
import json
import requests

from web3 import Web3, exceptions as web3exceptions

from datetime import datetime
from main import w3, eth, abi_collection, rarity_db
from db_functions import find_id_match
from ipfs import get_whole_directory
from re_patterns import match_object, match_token_id
from async_metadata_requests import make_requests


async def get_collection_meta(URI, token_id=None):
    rarity_collection = rarity_db[URI]
    contract = create_contract(URI)
    try:
        total_supply = contract.functions.totalSupply().call()
    except web3exceptions.ABIFunctionNotFound:
        try:
            total_supply = contract.functions.MAX_SUPPLY().call()
        except web3exceptions.ABIFunctionNotFound as e:
            raise e

    try:
        token_uri = contract.functions.tokenURI(0).call()
        starting_id = 0
    except web3exceptions.ContractLogicError:
        try:
            token_uri = contract.functions.tokenURI(1).call()
            starting_id = 1
        except web3exceptions.ContractLogicError as e:
            raise e

    missing_tokens = database_metadata_check(
        rarity_collection=rarity_collection,
        total_supply=total_supply,
        start=starting_id,
    )

    if len(missing_tokens) == 0:
        print("No missing TOOOOKENS")
        meta = list(rarity_collection.find({}).sort("_id"))
        return meta
    else:
        uris = []
        for token_id in missing_tokens:
            if "/0" in token_uri:
                uris.append(token_uri.replace("/0", f"/{token_id}"))
            elif "/1" in token_uri:
                uris.append(token_uri.replace("/0", f"/{token_id}"))
            elif "0" in token_uri:
                uris.append(token_uri.replace("0", f"{token_id}"))
            elif "1" in token_uri:
                uris.append(token_uri.replace("1", f"{token_id}"))
            else:
                print("Can't handle this URI")

        metadata = await make_requests(urls=uris, collection=rarity_collection)
        meta = list(rarity_collection.find({}).sort("_id"))
        return meta

    meta_dict = {}
    abi_string = str(contract.abi)
    """if "base_uri" in abi_string:
        base_uri = contract.functions.baseURI().call()
        print(base_uri)
        if "ipfs://" in base_uri:
            # try:
            raw_data = get_whole_directory(base_uri)
            print(f"Raw Data: {len(raw_data)} Characters")
            strings = raw_data.split("\n")
            print(f"Documents: {len(strings)}")
            for string in strings:
                try:
                    token_meta = json.loads(match_object.findall(string)[0])
                    token_id = match_token_id.findall(string)[0]
                    meta_dict[int(token_id)] = token_meta
                except:
                    pass
    elif """
    if "tokenURI" in abi_string:
        token_uri = contract.functions.tokenURI(0).call()
        max_int = contract.functions.totalSupply().call() - 1

        uris = []
        for token_id in range(0, max_int):
            uris.append(token_uri.replace("/0", f"/{token_id}"))

        metadata = await make_requests(urls=uris, collection=rarity_collection)

        return metadata
    else:  # TODO: Handling for regular APIs
        pass
    return meta_dict


def database_metadata_check(rarity_collection, total_supply, start):
    missing_metadata = []
    documents = rarity_collection.count_documents({})

    if documents == 0:
        return [i for i in range(start, total_supply - 1)]

    if total_supply - documents > 0:
        token_ids = [int(id) for id in rarity_collection.find().distinct("_id")]
        missing_ids = [id for id in range(start, total_supply) if id not in token_ids]
        missing_metadata = missing_ids

    print(len(missing_metadata))
    return missing_metadata


def abi_getter(address):
    doc = find_id_match(abi_collection, address.lower())

    if doc:
        return doc["abi"]
    else:
        ABI = eth.get_contract_abi(address)
        abi_dict = {
            "_id": address.lower(),
            "abi": ABI,
            "last_updated": datetime.utcnow(),
        }

        abi_collection.insert_one(abi_dict)
        return ABI


def create_contract(CONTRACT_ADDRESS):
    ABI = abi_getter(CONTRACT_ADDRESS)
    CONTRACT_ADDRESS = Web3.toChecksumAddress(CONTRACT_ADDRESS)
    contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)
    return contract
