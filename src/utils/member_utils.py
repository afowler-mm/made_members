"""
Member utility functions
"""

def is_education_member(member):
    """Check if a member is an education member based on their most recent order"""
    orders = member.get("orders", [])
    if not orders:
        return False
    
    # Sort orders by creation time (newest first)
    sorted_orders = sorted(orders, key=lambda o: o.get("createdAt", 0), reverse=True)
    most_recent_order = sorted_orders[0]
    
    # Check if the most recent order was free and used the Education coupon
    is_free = most_recent_order.get("totalCents", 0) == 0
    has_education_coupon = False
    
    if most_recent_order.get("coupon") and most_recent_order["coupon"].get("code") == "Education":
        has_education_coupon = True
    
    return is_free and has_education_coupon