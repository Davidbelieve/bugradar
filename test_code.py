def calculate_discount(price, customer_type, years, purchases, region):
    if customer_type == "premium":
        if years > 5:
            if purchases > 100:
                discount = 0.30
            elif purchases > 50:
                discount = 0.25
            else:
                discount = 0.20
        elif years > 2:
            discount = 0.15
        else:
            discount = 0.10
    elif customer_type == "standard":
        if region == "UK":
            discount = 0.05
        else:
            discount = 0.02
    else:
        discount = 0.0
    return price * (1 - discount)


def process_order(items, user):
    total = 0
    for item in items:
        if item["stock"] > 0:
            total += item["price"] * item["quantity"]
    return total


def validate_user(user):
    if not user:
        return False
    if user.get("email"):
        return True
    return False