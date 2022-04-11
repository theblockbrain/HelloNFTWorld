import token
import pymongo
import json
import requests
import pandas as pd
import numpy as np
import operator

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
        if start == 0:
            return [i for i in range(start, total_supply - 1)]
        else:
            return [i for i in range(start, total_supply)]

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


def get_rarity_meta(contract_address):
    meta_mapping = {}
    rarity_collection = rarity_db[contract_address]
    first_doc = rarity_collection.find_one({})
    if not "rarity_rank" in first_doc.keys():
        metadict = {}
        cursor = rarity_collection.find({})
        for token in cursor:
            metadict[token["_id"]] = token
        df = get_attribute_dataframe(meta_dict=metadict)
        trait_counts = get_trait_counts(df)

        attribute_dict = df.to_dict("index")

        for key, value in attribute_dict.items():
            rarity_scores, trait_count = get_token_rarity(trait_counts, value)
            single_meta_dict = metadict.get(key)
            attribute_list = single_meta_dict["attributes"]
            new_attribute_list = []
            while attribute_list:
                attribute = attribute_list.pop()
                attribute["score"] = rarity_scores[attribute["trait_type"]]
                new_attribute_list.append(attribute)
            trait_count_dict = {
                "trait_type": "Trait Count",
                "value": trait_count,
                "score": rarity_scores["Trait Count"],
            }
            new_attribute_list.append(trait_count_dict)
            single_meta_dict["attributes"] = new_attribute_list
            single_meta_dict["rarity_score"] = round(rarity_scores["Total"], 2)

            meta_mapping[key] = single_meta_dict

        mapping_with_ranks = calculate_ranks(meta_mapping)

        for token in mapping_with_ranks:
            token_updated = token
            token_updated["last_updated"] = datetime.utcnow()
            rarity_collection.replace_one({"_id": token_updated["_id"]}, token_updated)
        return meta_mapping
    else:
        return "Rarity already calculated"


def get_attribute_dataframe(meta_dict):
    """
    meta_dict: Expects a dictionary with one key, value pair per token.
    Example: { ('0': { metadata }, '1': { metadata } ...) }
    """
    list_of_dicts = []
    for token_id, meta in meta_dict.items():
        token_dict = {}
        token_dict["tokenID"] = token_id
        for attribute in meta["attributes"]:
            token_dict[attribute["trait_type"]] = attribute["value"]
        list_of_dicts.append(token_dict)

    # create new DataFrame
    attribute_df = pd.DataFrame(list_of_dicts)
    attribute_df.set_index("tokenID", inplace=True)

    # replace NaN Values as they tend to make Problems
    attribute_df.fillna("None", inplace=True)

    # create a new column with trait counts for each token
    attribute_df["Trait Count"] = (attribute_df != "None").sum(1)

    return attribute_df


def get_trait_counts(attribute_df):
    attribute_dist_dict = {}
    for col in attribute_df.columns:
        attribute_counts_df = attribute_df[col].value_counts(dropna=False)
        attribute_dist_dict[str(col)] = attribute_counts_df.to_dict()
    return attribute_dist_dict


def get_token_rarity(attribute_dist_dict, token_attributes, trait_weighting={}):
    """
    attribute_dist_dict: as returned by .get_trait_counts()
    token_attributes: a dict containing key: value pairs for each trait of the NFT
            ( if a trait is left out, it is assumed to be missing )
    trait_weighting: pass an optional dict of weightings for your traits
            (e.g.: {"Background": 1, "Eyes": 2, "trait_count": 8})
    """
    nft_count = sum(attribute_dist_dict[list(attribute_dist_dict.keys())[0]].values())
    scores = {}
    for attr in attribute_dist_dict.keys():
        if attr == "Trait Count":
            trait_count = token_attributes["Trait Count"]
            score_preweight = round(
                (1 / (attribute_dist_dict["Trait Count"][trait_count] / nft_count)), 2
            )
        else:
            val = token_attributes.get(attr, "None")
            # print(f"Checking attribute {attr} for value {val}")
            count = attribute_dist_dict[attr][val]
            score_preweight = round(1 / (count / nft_count), 2)
        scores[attr] = score_preweight * trait_weighting.get(attr, 1)
    scores["Total"] = sum(scores.values())
    return scores, trait_count


def calculate_ranks(meta_mapping):
    token_list = list(meta_mapping.values())
    print(token_list[0])
    token_list.sort(key=operator.itemgetter("rarity_score"), reverse=True)
    print(token_list[0])
    ranked_list = []
    for index, item in enumerate(token_list, start=1):
        item["rarity_rank"] = index
        ranked_list.append(item)
    return ranked_list
