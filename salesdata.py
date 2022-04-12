import matplotlib.pyplot as plt
import numpy as np
from web3 import Web3
import scipy
from scipy import optimize


def map_sales(sales_events, rarity_data):

    rarity_mapping = {token["_id"]: token["rarity_score"] for token in rarity_data}

    sales = [
        (event["asset"]["token_id"], event["total_price"]) for event in sales_events
    ]

    dates = set([event["created_date"][0:10] for event in sales_events])

    daily_sales_number = []
    daily_information = {}
    for date in dates:
        daily_sales = list(
            filter(lambda sale: date in sale["created_date"], sales_events)
        )
        daily_sales_number.append(len(daily_sales))
        min_sale = min(daily_sales, key=lambda n: int(n["total_price"]))["total_price"]
        daily_information[date] = {
            "daily_sales_number": len(daily_sales),
            "floor_price": int(min_sale),
        }

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

    return sales_with_sugar


def transform_sales_to_arrays(sales, x_kpi, y_kpi):
    if y_kpi == "total_price":
        list_of_tuples = [
            (sale[x_kpi], Web3.fromWei(int(sale["total_price"]), "ether"))
            for sale in sales
        ]
    elif y_kpi == "over_floor":
        list_of_tuples = [(sale[x_kpi], sale["over_floor"]) for sale in sales]
    else:
        raise Exception("Unkown KPI")

    x, y = zip(*list_of_tuples)

    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)

    return x, y


def curve_fit(x, y):
    plt.scatter(x, y)

    fit = np.polyfit(x, np.log(y), 1)

    B, A = fit[0], np.exp(fit[1])
    print(A, B)

    def exp_function(x):
        return A * np.exp(B * x)

    x_line = np.arange(min(x), max(x), ((max(x) - min(x)) / 20), dtype=int)
    y_line = np.array([exp_function(x) for x in x_line])

    plt.plot(x_line, y_line, color="g")


def poly_fit(x, y):
    plt.scatter(x, y)

    fit = np.polyfit(x, np.log(y), 1, w=np.sqrt(y))
    B, A = fit[0], np.exp(fit[1])
    print(A, B)

    def exp_function(x):
        return A * np.exp(B * x)

    x_line = np.arange(min(x), max(x), ((max(x) - min(x)) / 20), dtype=int)
    y_line = np.array([exp_function(x) for x in x_line])

    plt.plot(x_line, y_line, color="g")

    return (A, B)


def scipy_fit(x, y, p0):
    plt.scatter(x, y)
    fit = scipy.optimize.curve_fit(lambda t, a, b: a * np.exp(b * t), x, y, p0=p0)
    A, B = fit[0]
    print(A, B)

    def exp_function(x):
        return A * np.exp(B * x)

    x_line = np.arange(min(x), max(x), ((max(x) - min(x)) / 20), dtype=int)
    y_line = np.array([exp_function(x) for x in x_line])

    plt.plot(x_line, y_line, color="g")

    return (A, B)


# %%
