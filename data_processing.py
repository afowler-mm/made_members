"""
Data processing functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
import streamlit as st
from utils import is_education_member
from datetime import datetime, timedelta
import calendar

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

def process_subscription_activities(activities_data):
    """
    Process subscription activity data from Memberful API
    
    This function processes the activities data to track new subscriptions,
    cancellations, upgrades, downgrades, reactivations, and failed payments.
    
    Args:
        activities_data (list): List of activity objects from the Memberful API
        
    Returns:
        pd.DataFrame: DataFrame with processed activities data
    """
    if not activities_data:
        return pd.DataFrame()
    
    # Create a dataframe for the activities
    activity_records = []
    
    for activity in activities_data:
        # Skip activities without subscription data
        if not activity.get("subscription"):
            continue
            
        # Basic activity info
        activity_type = activity.get("type")
        created_at = activity.get("createdAt")
        member_id = activity.get("member", {}).get("id")
        member_name = activity.get("member", {}).get("fullName")
        subscription_id = activity.get("subscription", {}).get("id")
        
        # Extract plan data
        plan_data = activity.get("subscription", {}).get("plan", {})
        plan_name = plan_data.get("name", "Unknown")
        plan_price_cents = plan_data.get("priceCents", 0)
        interval_unit = plan_data.get("intervalUnit", "month")
        interval_count = plan_data.get("intervalCount", 1)
        
        # Calculate monthly value for MRR calculations
        monthly_multiplier = 1
        if interval_unit == "week":
            monthly_multiplier = 0.25
        elif interval_unit == "year":
            monthly_multiplier = 12
            
        monthly_value = plan_price_cents / (monthly_multiplier * (interval_count or 1))
        
        # Previous plan data for upgrades/downgrades (if available)
        previous_data = activity.get("previousData", {})
        old_plan_id = None
        old_plan_price_cents = 0
        old_monthly_value = 0
        
        # For upgrades/downgrades, calculate the change in MRR
        if activity_type in ["upgrade", "downgrade"] and previous_data:
            if isinstance(previous_data, dict) and "plan" in previous_data:
                old_plan_id = previous_data.get("plan", {}).get("id")
                old_plan_price_cents = previous_data.get("plan", {}).get("priceCents", 0)
                old_interval_unit = previous_data.get("plan", {}).get("intervalUnit", "month")
                old_interval_count = previous_data.get("plan", {}).get("intervalCount", 1)
                
                old_monthly_multiplier = 1
                if old_interval_unit == "week":
                    old_monthly_multiplier = 0.25
                elif old_interval_unit == "year":
                    old_monthly_multiplier = 12
                    
                old_monthly_value = old_plan_price_cents / (old_monthly_multiplier * (old_interval_count or 1))
        
        # Calculate financial impact based on activity type
        mrr_impact = 0
        
        if activity_type == "new_subscription":
            # New subscription adds the full monthly value
            mrr_impact = monthly_value
            activity_category = "New Members"
        elif activity_type == "subscription_reactivated":
            # Reactivation adds the full monthly value
            mrr_impact = monthly_value
            activity_category = "Reactivations"
        elif activity_type == "upgrade":
            # Upgrade adds the difference between new and old plan
            mrr_impact = monthly_value - old_monthly_value
            activity_category = "Upgrades"
        elif activity_type == "downgrade":
            # Downgrade subtracts the difference between old and new plan
            mrr_impact = -(old_monthly_value - monthly_value)
            activity_category = "Downgrades"
        elif activity_type == "subscription_deleted" or activity_type == "subscription_deactivated":
            # Cancellation removes the full monthly value
            mrr_impact = -monthly_value
            activity_category = "Cancellations"
        elif activity_type == "renewal_payment_failed":
            # Failed payment potentially removes the full monthly value
            mrr_impact = -monthly_value
            activity_category = "Failed Payments"
        else:
            # Other activities like regular renewals
            activity_category = "Other"
        
        # Add record to the list
        activity_records.append({
            "id": activity.get("id"),
            "type": activity_type,
            "category": activity_category,
            "created_at": datetime.fromtimestamp(created_at) if created_at else None,
            "member_id": member_id,
            "member_name": member_name,
            "subscription_id": subscription_id,
            "plan_name": plan_name,
            "plan_price_cents": plan_price_cents,
            "monthly_value": monthly_value,
            "mrr_impact_cents": mrr_impact,
            "mrr_impact_dollars": mrr_impact / 100 if mrr_impact else 0,
            "old_plan_id": old_plan_id,
            "old_plan_price_cents": old_plan_price_cents,
            "old_monthly_value": old_monthly_value
        })
    
    # Create DataFrame and sort by created_at
    activities_df = pd.DataFrame(activity_records)
    
    if not activities_df.empty:
        # Add month for grouping
        activities_df["month"] = activities_df["created_at"].dt.to_period("M")
        activities_df["month_dt"] = activities_df["created_at"].dt.to_period("M").dt.to_timestamp()
        activities_df["month_name"] = activities_df["month_dt"].dt.strftime("%b %Y")
    
    return activities_df

def calculate_monthly_mrr_changes(activities_df, start_date, end_date=None):
    """
    Calculate monthly MRR changes from subscription activities
    
    Args:
        activities_df (pd.DataFrame): DataFrame of processed activities
        start_date (datetime): Start date for analysis
        end_date (datetime, optional): End date for analysis. Defaults to today.
        
    Returns:
        pd.DataFrame: DataFrame with monthly MRR changes
    """
    if activities_df.empty:
        return pd.DataFrame()
    
    # Set end date to today if not provided
    if end_date is None:
        end_date = datetime.now()
    
    # Generate a list of all months in the date range
    months_range = []
    current_date = start_date.replace(day=1)
    
    while current_date <= end_date:
        months_range.append(current_date)
        # Move to next month
        if current_date.month == 12:
            current_date = current_date.replace(year=current_date.year + 1, month=1)
        else:
            current_date = current_date.replace(month=current_date.month + 1)
    
    # Create month periods for joining
    month_periods = [pd.Period(m, freq='M') for m in months_range]
    
    # Group activities by month and category to calculate MRR changes
    mrr_changes = activities_df.groupby(["month", "category"])["mrr_impact_dollars"].sum().reset_index()
    
    # Create a month lookup table for easy reference
    month_data = []
    for month in month_periods:
        month_start = month.to_timestamp()
        month_end = month_start + pd.offsets.MonthEnd(0)
        
        # Calculate month label for display
        month_label = month_start.strftime("%b %Y")
        
        month_data.append({
            "month": month,
            "month_dt": month_start,
            "month_label": month_label,
            "days_in_month": calendar.monthrange(month_start.year, month_start.month)[1]
        })
    
    # Create dataframe of all months
    months_df = pd.DataFrame(month_data)
    
    # Create a baseline table with all months and zero values for all categories
    categories = ["Starting MRR", "New Members", "Reactivations", "Upgrades", 
                 "Downgrades", "Cancellations", "Failed Payments", "Total MRR"]
    
    baseline = []
    for _, row in months_df.iterrows():
        for category in categories:
            baseline.append({
                "month": row["month"],
                "month_dt": row["month_dt"],
                "month_label": row["month_label"],
                "category": category,
                "mrr_impact_dollars": 0
            })
    
    baseline_df = pd.DataFrame(baseline)
    
    # Merge to get a complete dataframe with all months and categories
    if not mrr_changes.empty:
        # Only merge if we have actual data
        result = pd.merge(
            baseline_df, 
            mrr_changes,
            on=["month", "category"],
            how="left",
            suffixes=("", "_actual")
        )
        
        # Replace null values with zero
        result["mrr_impact_dollars"] = result.apply(
            lambda x: x.get("mrr_impact_dollars_actual", 0) if pd.notna(x.get("mrr_impact_dollars_actual")) else x["mrr_impact_dollars"],
            axis=1
        )
        
        # Drop the duplicate column
        result = result.drop(columns=["mrr_impact_dollars_actual"])
    else:
        result = baseline_df
    
    # Sort by month and ensure categories are in the right order
    result["category_order"] = result["category"].map({
        "Starting MRR": 0,
        "New Members": 1, 
        "Reactivations": 2,
        "Upgrades": 3,
        "Downgrades": 4,
        "Cancellations": 5,
        "Failed Payments": 6,
        "Total MRR": 7
    })
    
    result = result.sort_values(["month_dt", "category_order"])
    
    # Calculate Starting MRR and Total MRR for each month
    months_sorted = months_df["month"].sort_values().tolist()
    
    # We need to know the starting MRR for the first month in our analysis
    # For now, set it to a placeholder value that can be updated later
    initial_mrr = 0  # This needs to be set by the calling function
    
    for i, month in enumerate(months_sorted):
        # Filter result to just this month's data
        month_data = result[result["month"] == month]
        
        if i == 0:
            # For the first month, set the starting value from external data
            starting_mrr = initial_mrr
        else:
            # For subsequent months, the starting MRR is the total MRR from the previous month
            prev_month = months_sorted[i-1]
            starting_mrr = result.loc[
                (result["month"] == prev_month) & 
                (result["category"] == "Total MRR"), 
                "mrr_impact_dollars"
            ].iloc[0]
        
        # Update the Starting MRR for this month
        result.loc[(result["month"] == month) & (result["category"] == "Starting MRR"), "mrr_impact_dollars"] = starting_mrr
        
        # Calculate the Total MRR for this month
        total_mrr = starting_mrr + result.loc[
            (result["month"] == month) & 
            (result["category"].isin(["New Members", "Reactivations", "Upgrades", "Downgrades", "Cancellations", "Failed Payments"])), 
            "mrr_impact_dollars"
        ].sum()
        
        # Update the Total MRR for this month
        result.loc[(result["month"] == month) & (result["category"] == "Total MRR"), "mrr_impact_dollars"] = total_mrr
    
    return result