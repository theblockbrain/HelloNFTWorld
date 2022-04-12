#%%
import requests
import matplotlib.pyplot as plt
import numpy as np
from operator import itemgetter
from web3 import Web3
from sklearn.linear_model import LinearRegression
from scipy.optimize import curve_fit

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

    rarity_mapping = {token["_id"]: token["rarity_score"] for token in rarity}

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
            "over_floor": round(
                (
                    int(sale["total_price"])
                    - daily_information[sale["created_date"][0:10]]["floor_price"]
                )
                / daily_information[sale["created_date"][0:10]]["floor_price"],
                2,
            ),
            "points": rarity_mapping[int(sale["asset"]["token_id"])],
        }
        sales_with_sugar.append(sale_object)

    print(sales_with_sugar[5])

    return sales_with_sugar


sales = plot_sales()

# %%
def draw_plot(sales):
    list_of_tuples = [
        (sale["points"], Web3.fromWei(int(sale["total_price"]), "ether"))
        for sale in sales
    ]
    # list_of_tuples = [(sale["points"], sale["over floor"]) for sale in sales]
    print(list_of_tuples[0])

    x, y = zip(*list_of_tuples)

    x = np.array(x).reshape(-1, 1)
    y = np.array(y)

    model = LinearRegression().fit(x, y)

    r_sq = model.score(x, y)
    print(r_sq)


draw_plot(sales)
# %%
def curve_fit(sales):
    list_of_tuples = [
        (sale["points"], Web3.fromWei(int(sale["total_price"]), "ether"))
        for sale in sales
    ]
    # list_of_tuples = [(sale["points"], sale["over floor"]) for sale in sales]
    print(list_of_tuples[0])

    x, y = zip(*list_of_tuples)

    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    fit = np.polyfit(np.log(x), y, 1)
    print(fit)
    # curve_fit(lambda t,a,b: a*np.exp(b*t),  x,  y,  p0=(900, 40))


curve_fit(sales)
# %%
