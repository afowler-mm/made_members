"""
Utility functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
from datetime import datetime
import streamlit as st

def get_date_n_months_ago(n):
    """Get date n months ago from today"""
    today = datetime.now()
    n_months_ago = today.replace(month=today.month - n) if today.month > n else \
                  today.replace(year=today.year - 1, month=today.month + 12 - n)
    return n_months_ago.strftime("%Y-%m-%d")

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

def create_download_button(df, filename, button_text="Download as CSV"):
    """Create a download button for a dataframe"""
    csv = df.to_csv(index=False)
    st.download_button(
        label=button_text,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )

def clean_period_data(period_df, period_column="month", sort_key_column="sort_key"):
    """Clean and format period data (like months) for visualizations"""
    # Convert Period to string 
    period_df[f"{period_column}_str"] = period_df[period_column].astype(str)
    
    # Extract year and month for proper sorting
    def extract_ym(period_str):
        # Period strings are in format 'YYYY-MM'
        if pd.isna(period_str) or not isinstance(period_str, str):
            return None
        parts = period_str.split('-')
        if len(parts) == 2:
            try:
                return int(parts[0]) * 100 + int(parts[1])
            except (ValueError, IndexError):
                return None
        return None
        
    period_df[sort_key_column] = period_df[f"{period_column}_str"].apply(extract_ym)
    
    # Filter out rows with invalid sort keys
    period_df = period_df[period_df[sort_key_column].notna()]
    
    # Sort the data
    period_df = period_df.sort_values(sort_key_column)
    
    return period_df