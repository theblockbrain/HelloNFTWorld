#%%
import requests
from operator import itemgetter

#%%
def plot_sales():
    res = requests.get(
        "http://127.0.0.1:8000/os-sales/0xed5af388653567af2f388e6224dc7c4b3241c544"
    )

    res2 = requests.get(
        "http://127.0.0.1:8000/rarity/0xed5af388653567af2f388e6224dc7c4b3241c544"
    )

    sales_events = res.json()
    rarity = res2.json()

    sales = [
        (event["asset"]["token_id"], event["total_price"]) for event in sales_events
    ]
    print(sales[0])
    dates = set([event["created_date"][0:10] for event in sales_events])
    print(dates)

    daily_sales_number = []
    daily_information = {}
    for date in dates:
        daily_sales = list(
            filter(lambda sale: date in sale["created_date"], sales_events)
        )
        print(date, len(daily_sales))
        daily_sales_number.append(len(daily_sales))
        min_sale = min(daily_sales, key=lambda n: int(n["total_price"]))["total_price"]
        print(date, min_sale)
        daily_information[date] = {
            "daily_sales_number": len(daily_sales),
            "floor_price": int(min_sale),
        }

    print(daily_information)

    sales_with_sugar = []
    for sale in sales_events:
        sale_object = {
            "token_id": sale["asset"]["token_id"],
            "total_price": sale["total_price"],
            "over floor": round(
                (
                    int(sale["total_price"])
                    - daily_information[sale["created_date"][0:10]]["floor_price"]
                )
                / daily_information[sale["created_date"][0:10]]["floor_price"],
                2,
            ),
        }
        sales_with_sugar.append(sale_object)

    return "yes"


plot_sales()

# %%
