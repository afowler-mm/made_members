"""
Metrics display components for the dashboard
"""
import streamlit as st
from datetime import datetime, timedelta
from ..data.members import calculate_mrr, calculate_recent_orders

def display_membership_metrics(subs_df, members_data=None):
    """Display metrics about membership counts and revenue"""
    # Calculate metrics
    current_mrr, paying_members_count, active_count, education_count = calculate_mrr(subs_df)
    
    # Calculate recent orders if members_data is provided
    recent_orders_value = 0
    if members_data:
        recent_orders_value = calculate_recent_orders(members_data, days=30)
    
    # Store education count in session state for later use
    st.session_state.education_count = education_count
    
    # Set standard time periods for analysis
    today = datetime.now()
    past_30_days = today - timedelta(days=30)
    past_90_days = today - timedelta(days=90)
    past_year = today - timedelta(days=365)
    
    # Create columns for metrics
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    # Calculate counts for different membership types
    if not subs_df.empty:
        # Current active members by plan type
        active_subs = subs_df[subs_df["active"] == True]
        
        # Individual members
        individual_members = active_subs[active_subs["plan"] == "Individual membership"]
        individual_count = len(individual_members.drop_duplicates("member_id"))
        
        # Small business members - count both accounts and total members
        small_business_members = active_subs[active_subs["plan"] == "Small business membership"]
        small_business_accounts = len(small_business_members.drop_duplicates("subscription_id"))
        small_business_count = len(small_business_members.drop_duplicates("member_id"))
        
        # Large business members - count both accounts and total members
        large_business_members = active_subs[active_subs["plan"] == "Large business membership"]
        large_business_accounts = len(large_business_members.drop_duplicates("subscription_id"))
        large_business_count = len(large_business_members.drop_duplicates("member_id"))
        
        # For month-over-month comparisons, get the active members from 30 days ago
        thirty_days_ago = today - timedelta(days=30)
        
        # Get a snapshot of active members 30 days ago
        active_month_ago = subs_df[
            (subs_df["created_at"] <= thirty_days_ago) & 
            ((subs_df["expires_at"] > thirty_days_ago) | (subs_df["expires_at"].isna()))
        ]
        
        # Get counts by plan type 30 days ago
        individual_month_ago = active_month_ago[active_month_ago["plan"] == "Individual membership"]
        individual_count_month_ago = len(individual_month_ago.drop_duplicates("member_id"))
        individual_change = individual_count - individual_count_month_ago
        
        small_business_month_ago = active_month_ago[active_month_ago["plan"] == "Small business membership"]
        small_business_accounts_month_ago = len(small_business_month_ago.drop_duplicates("subscription_id"))
        small_business_count_month_ago = len(small_business_month_ago.drop_duplicates("member_id"))
        small_business_accounts_change = small_business_accounts - small_business_accounts_month_ago
        small_business_change = small_business_count - small_business_count_month_ago
        
        large_business_month_ago = active_month_ago[active_month_ago["plan"] == "Large business membership"]
        large_business_accounts_month_ago = len(large_business_month_ago.drop_duplicates("subscription_id"))
        large_business_count_month_ago = len(large_business_month_ago.drop_duplicates("member_id"))
        large_business_accounts_change = large_business_accounts - large_business_accounts_month_ago
        large_business_change = large_business_count - large_business_count_month_ago
        
        # Calculate education members month-over-month
        if "is_education" in subs_df.columns:
            education_month_ago = active_month_ago[active_month_ago["is_education"] == True]
            education_count_month_ago = len(education_month_ago.drop_duplicates("member_id"))
            education_change = education_count - education_count_month_ago
        else:
            education_change = 0
        
        # Calculate MRR from last month
        paying_month_ago = active_month_ago
        if "is_education" in subs_df.columns:
            paying_month_ago = paying_month_ago[paying_month_ago["is_education"] == False]
        paying_month_ago = paying_month_ago.drop_duplicates("subscription_id")
        previous_mrr = paying_month_ago["monthly_value"].sum() / 100 if not paying_month_ago.empty else 0
        
        # Calculate month-over-month change for MRR
        mrr_change = current_mrr - previous_mrr
        mrr_change_percent = (mrr_change / previous_mrr * 100) if previous_mrr > 0 else 0
        
        # Display metrics with month-over-month changes
        col1.metric(
            "Individual members", 
            individual_count,
            f"{individual_change:+d} from last month"
        )
        col1.caption("Includes education members")
        
        col2.metric(
            "Small business memberships", 
            f"{small_business_accounts} ({small_business_count}👥)",
            f"{small_business_accounts_change:+d} from last month"
        )
        
        col3.metric(
            "Large business memberships", 
            f"{large_business_accounts} ({large_business_count}👥)",
            f"{large_business_accounts_change:+d} from last month"
        )
        
        col4.metric(
            "Education members", 
            f"{education_count}",
            f"{education_change:+d} from last month"
        )
        
        col5.metric(
            "Monthly recurring revenue", 
            f"${current_mrr:,.2f}", 
            f"{mrr_change_percent:+.1f}% from last month"
        )
        col5.caption("See more details in [Memberful admin](https://made.memberful.com/admin/metrics/mrr).")
        
        # Calculate 30-day orders for previous period to show delta
        previous_30_days = 0
        if members_data:
            # Calculate orders from 60-30 days ago
            today = datetime.now()
            prev_period_start = today - timedelta(days=60)
            prev_period_end = today - timedelta(days=30)
            prev_period_start_ts = prev_period_start.timestamp()
            prev_period_end_ts = prev_period_end.timestamp()
            
            for member in members_data:
                for order in member.get("orders", []):
                    order_time = order.get("createdAt", 0)
                    if order.get("status") == "completed" and prev_period_start_ts <= order_time <= prev_period_end_ts:
                        previous_30_days += order.get("totalCents", 0)
            
            previous_30_days = previous_30_days / 100  # Convert to dollars
        
        # Calculate delta percentage if previous period had orders
        if previous_30_days > 0:
            delta_pct = ((recent_orders_value - previous_30_days) / previous_30_days) * 100
            delta_display = f"{delta_pct:+.1f}% vs previous 30 days"
        else:
            delta_display = None
        
        col6.metric(
            "Orders in past 30 days", 
            f"${recent_orders_value:,.2f}", 
            delta_display
        )
        col6.caption("Total value of completed orders")

    return active_count