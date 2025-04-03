"""
Member data processing functions
"""
import pandas as pd
from datetime import datetime, timedelta
from ..utils.member_utils import is_education_member

def process_members_data(members_data):
    """Process raw members data into usable dataframes"""
    # Create dataframes for analysis
    members_df = pd.DataFrame([
        {
            "id": member["id"],
            "email": member["email"],
            "name": member["fullName"],
            "total_spend_cents": member.get("totalSpendCents", 0),
            "is_education": is_education_member(member)
        }
        for member in members_data
    ])
    
    # Create subscriptions dataframe
    subscriptions = []
    for member in members_data:
        member_id = member["id"]
        member_name = member["fullName"]
        member_email = member["email"]
        is_edu = is_education_member(member)
        
        for sub in member.get("subscriptions", []):
            subscriptions.append({
                "subscription_id": sub["id"],
                "member_id": member_id,
                "member_name": member_name,
                "member_email": member_email,
                "active": sub.get("active", False),
                "auto_renew": sub.get("autorenew", False),
                "plan": sub.get("plan", {}).get("name", "Unknown"),
                "price_cents": sub.get("plan", {}).get("priceCents", 0),
                "interval_unit": sub.get("plan", {}).get("intervalUnit", ""),
                "interval_count": sub.get("plan", {}).get("intervalCount", 1),
                "created_at": sub.get("createdAt"),
                "expires_at": sub.get("expiresAt"),
                "is_education": is_edu
            })
    
    subs_df = pd.DataFrame(subscriptions)
    
    if not subs_df.empty:
        # Convert Unix timestamps to datetime
        for col in ["created_at", "expires_at"]:
            if col in subs_df.columns:
                # Convert Unix timestamp (seconds) to datetime
                subs_df[col] = pd.to_datetime(subs_df[col], unit='s')
    
    return members_df, subs_df

def prepare_all_members_view(members_df, subs_df):
    """Prepare data for the all members view"""
    if subs_df.empty:
        return pd.DataFrame()
        
    # Create a unique list of members with their subscription info
    # Get latest subscription for each member to show current status
    member_subs = subs_df.sort_values("created_at", ascending=False).drop_duplicates("member_id")
    columns_to_include = ["member_id", "active", "plan", "subscription_id"]
    
    # Make sure is_education is included if it exists
    if "is_education" in member_subs.columns:
        columns_to_include.append("is_education")
        
    all_members = pd.merge(members_df, member_subs[columns_to_include], 
                         left_on="id", right_on="member_id", how="left")
                         
    return all_members
    
def prepare_new_members(subs_df, days=30):
    """Prepare data for the new members view"""
    if subs_df.empty:
        return pd.DataFrame()
        
    # Define time period
    today = datetime.now()
    past_date = today - timedelta(days=days)
    
    # Get unique new subscriptions for the period
    new_subs = subs_df[subs_df["created_at"] >= past_date]
    unique_new = new_subs.drop_duplicates("subscription_id") if not new_subs.empty else pd.DataFrame()
    
    return unique_new
    
def calculate_recent_orders(members_data, days=30):
    """Calculate the total value of orders in the past N days"""
    if not members_data:
        return 0
        
    today = datetime.now()
    cutoff_date = today - timedelta(days=days)
    cutoff_timestamp = cutoff_date.timestamp()
    
    total_cents = 0
    for member in members_data:
        for order in member.get("orders", []):
            if order.get("status") == "completed" and order.get("createdAt", 0) >= cutoff_timestamp:
                total_cents += order.get("totalCents", 0)
    
    return total_cents / 100  # Convert cents to dollars

def calculate_mrr(subs_df):
    """Calculate Monthly Recurring Revenue for active subscriptions"""
    if subs_df.empty:
        return 0, 0, 0, 0
        
    # Add monthly value column
    subs_df["monthly_value"] = subs_df.apply(
        lambda x: x["price_cents"] / 
                (1 if x["interval_unit"] == "month" else
                0.25 if x["interval_unit"] == "week" else
                12 if x["interval_unit"] == "year" else 0) / 
                (x["interval_count"] or 1),
        axis=1
    )
    
    # For MRR calculation, filter out education members if the column exists
    if "is_education" in subs_df.columns:
        # Filter out education members from MRR calculation
        mrr_subs = subs_df[(subs_df["active"] == True) & (subs_df["is_education"] == False)]
    else:
        mrr_subs = subs_df[subs_df["active"] == True]
    
    # Get the unique subscription IDs to avoid double-counting members
    unique_subs = mrr_subs.drop_duplicates("subscription_id")
    current_mrr = unique_subs["monthly_value"].sum() / 100  # Convert cents to dollars
    
    # Count paying members (unique subscription IDs to avoid counting group members)
    paying_members_count = len(unique_subs)
    
    # Calculate Active Members (including education)
    active_members = subs_df[subs_df["active"] == True]
    active_count = len(active_members.drop_duplicates("member_id"))
    
    # Calculate education members if the column exists
    if "is_education" in subs_df.columns:
        education_members = subs_df[(subs_df["active"] == True) & (subs_df["is_education"] == True)]
        education_count = len(education_members.drop_duplicates("member_id"))
    else:
        education_count = 0
    
    return current_mrr, paying_members_count, active_count, education_count