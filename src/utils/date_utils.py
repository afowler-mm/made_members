"""
Date utility functions
"""
from datetime import datetime

def get_date_n_months_ago(n):
    """Get date n months ago from today"""
    today = datetime.now()
    n_months_ago = today.replace(month=today.month - n) if today.month > n else \
                  today.replace(year=today.year - 1, month=today.month + 12 - n)
    return n_months_ago.strftime("%Y-%m-%d")