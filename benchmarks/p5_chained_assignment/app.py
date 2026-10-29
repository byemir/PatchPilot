import pandas as pd


def apply_discounts(orders, threshold, rate):
    """Discount the orders above `threshold` by `rate` and mark them as discounted.

    orders: [{"id": ..., "amount": ..., "status": ...}, ...]. Returns [[id, amount, status], ...] in the same order.
    """
    df = pd.DataFrame(orders, columns=["id", "amount", "status"])
    big = df["amount"] > threshold
    df["amount"][big] = df["amount"][big] * (1 - rate)
    df["status"][big] = "discounted"
    return [[int(r.id), round(float(r.amount), 2), str(r.status)] for r in df.itertuples()]
