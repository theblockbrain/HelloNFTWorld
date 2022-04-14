import requests
import os

from ratelimit import limits, sleep_and_retry
from dotenv import load_dotenv

from app.main import slug_collection

load_dotenv()


def get_collection_slug(contract_address):
    headers = {"X-API-KEY": os.getenv("OS-TOKEN"), "User-Agent": "Mozilla/5.0"}
    r = requests.get(
        f"https://api.opensea.io/api/v1/asset_contract/{contract_address}",
        headers=headers,
    )
    res = r.json()
    print(res)
    slug = res["collection"]["slug"]
    slug_collection.insert_one({"_id": contract_address, "slug": slug})
    return slug


@sleep_and_retry
@limits(calls=4, period=1)
def get_os_sales_events(slug, num_queries=1, cursor=None):
    res_list = []
    headers = {"X-API-KEY": os.getenv("OS-TOKEN"), "User-Agent": "Mozilla/5.0"}
    if cursor:
        headers["cursor"] = cursor
    params = {"collection_slug": slug, "event_type": "successful", "limit": 200}
    r = requests.get(
        "https://api.opensea.io/api/v1/events", headers=headers, params=params
    )
    res = r.json()
    res_list += res["asset_events"]
    if num_queries > 1 and res["next"]:

        sub_query = get_os_sales_events(
            slug, num_queries=num_queries - 1, cursor=res["next"]
        )
        res_list += sub_query
    return res_list
