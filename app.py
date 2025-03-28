import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# Import our custom modules
import api
from api import get_memberful_data, fetch_all_members
from utils import get_date_n_months_ago, is_education_member, create_download_button
import data_processing
from data_processing import process_members_data, prepare_all_members_view, prepare_new_members, calculate_mrr
import visualizations
from visualizations import show_member_growth, show_plans_and_revenue, show_education_members, show_mrr_waterfall, show_mrr_trend, show_revenue_breakdown

def display_membership_metrics(subs_df):
    """Display metrics about membership counts and revenue"""
    # Calculate metrics
    current_mrr, paying_members_count, active_count, education_count = calculate_mrr(subs_df)
    
    # Store education count in session state for later use
    st.session_state.education_count = education_count
    
    # Set standard time periods for analysis
    today = datetime.now()
    past_30_days = today - timedelta(days=30)
    past_90_days = today - timedelta(days=90)
    past_year = today - timedelta(days=365)
    
    # Create columns for metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
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
            "Monthly revenue", 
            f"${current_mrr:,.2f}", 
            f"{mrr_change_percent:+.1f}% from last month"
        )

    return active_count

# App configuration
st.set_page_config(
    page_title="Maine Ad + Design membership dashboard",
    page_icon="🎨",
    layout="wide",
)

# Sidebar for filters and options
st.title("Maine Ad + Design membership dashboard")

# Debug mode toggle
debug_mode = st.sidebar.checkbox("Debug mode")

# Add a refresh button in the sidebar
refresh_data = False

# Check if the data cache should expire (every 24 hours)
if "last_fetch_time" in st.session_state:
    last_fetch_time = st.session_state.last_fetch_time
    current_time = datetime.now()
    time_difference = current_time - last_fetch_time
    # Force refresh if data is older than 24 hours
    if time_difference.total_seconds() > 24 * 60 * 60:
        refresh_data = True
        st.toast("Data cache expired. Refreshing...", icon="🔄")

if debug_mode:
    with st.sidebar:
        # Add refresh button
        if st.button("🔄 Refresh data"):
            # Clear the cache to force a refresh
            if "members_data" in st.session_state:
                del st.session_state.members_data
            if "members_df" in st.session_state:
                del st.session_state.members_df
            if "subs_df" in st.session_state:
                del st.session_state.subs_df
            if "consolidated_members_cache" in st.session_state:
                del st.session_state.consolidated_members_cache
            # Clear all dependent caches too
            for key in list(st.session_state.keys()):
                if key.endswith("_cache"):
                    del st.session_state[key]
            refresh_data = True
            st.toast("Data cache cleared. Refreshing...", icon="🔄")
        
        # Show the last updated time
        if "last_fetch_time" in st.session_state:
            last_fetch = st.session_state.last_fetch_time.strftime("%b %d, %Y at %I:%M %p")
            st.caption(f"Last updated: {last_fetch}")

# For education feature, force a refresh when running the app for the first time with the new code
# I think we can drop this now that it's been added?
if "education_feature_added" not in st.session_state:
    refresh_data = True
    st.session_state.education_feature_added = True
    # Also clear member caches to ensure they have the education flag
    if "all_members_cache" in st.session_state:
        del st.session_state.all_members_cache
    if "consolidated_members_cache" in st.session_state:
        del st.session_state.consolidated_members_cache
    # st.toast("Adding education member support. Refreshing data...", icon="🔄")

# Check if data is already in session state
if "members_data" not in st.session_state or refresh_data:
    # Loading indicator
    with st.spinner("Loading membership data..."):        
        # Fetch all members with pagination
        progress_text = "Fetching member data (this may take a moment)..."
        progress_bar = st.progress(0, text=progress_text)
        
        for percent_complete in range(0, 100, 10):  # Simulate progress in increments
            time.sleep(0.1)  # Simulate work being done
            progress_bar.progress(percent_complete, text=progress_text)
        
        members_data = fetch_all_members(debug_mode)
        progress_bar.progress(100, text="Data fetching complete!")
        progress_bar.empty()  # Remove the progress bar when complete
        
        if debug_mode:
            st.expander("Members Data Sample").json(members_data[:5] if members_data else [])
        
        if not members_data:
            st.error("Failed to load data. Please check API key and connection.")
            st.stop()
        
        # Process data into a usable format
        st.toast(f"Successfully loaded data for {len(members_data)} members.", icon="🎉")
        
        # Cache the raw data
        st.session_state.members_data = members_data
        
        # Process the data into DataFrames
        members_df, subs_df = process_members_data(members_data)
        
        # Cache the processed dataframes
        st.session_state.members_df = members_df
        st.session_state.subs_df = subs_df
        
        # Update the last fetch timestamp
        st.session_state.last_fetch_time = datetime.now()
else:
    # Use cached data
    members_data = st.session_state.members_data
    members_df = st.session_state.members_df
    subs_df = st.session_state.subs_df

# Display dashboard with membership metrics and visualizations
if 'members_df' in locals() and not members_df.empty:
    
    # Calculate metrics for pass to education visualization
    _, _, active_count, education_count = calculate_mrr(subs_df)
    
    # Store education count in session state for later use
    st.session_state.education_count = education_count
    
    # Main Dashboard Tabs    
    # Create main tabs for the dashboard
    if "is_education" in subs_df.columns:
        main_tabs = st.tabs(["Member growth", "Plans and revenue", "Education members", "Member directory"])
    else:
        main_tabs = st.tabs(["Member growth", "Plans and revenue", "Member directory"])
    
    if not subs_df.empty:
        # Fetch activity data for enhanced visualizations if not already in session state
        # Always force refresh activity data to ensure calculations are updated
        refresh_activities = True
            
        if refresh_activities:
            with st.spinner("Fetching recent subscription activities..."):
                # Get activity data for the past 12 months for more complete financial history
                twelve_months_ago = datetime.now() - timedelta(days=365)
                activities_data = api.fetch_subscription_activities(twelve_months_ago, debug_mode=debug_mode)
                
                # Process activity data if we have any
                if activities_data:
                    activities_df = data_processing.process_subscription_activities(activities_data)
                    
                    # Debug - check first few activities' monthly values
                    if debug_mode and not activities_df.empty:
                        st.write("First 5 activities MRR values:")
                        debug_sample = activities_df.head(5)
                        for i, row in debug_sample.iterrows():
                            st.write(f"{row.get('type')} - {row.get('plan_name')} - ${row.get('mrr_impact_dollars'):.2f}/month")
                    
                    # Store in session state
                    st.session_state.activities_cache = activities_df
                else:
                    st.session_state.activities_cache = pd.DataFrame()  # Empty DataFrame
                    
                # Force clear all computed MRR data to ensure fresh calculation
                for key in list(st.session_state.keys()):
                    if "mrr" in key.lower() and key != "activities_cache":
                        del st.session_state[key]
        
        # Member Growth visualization
        with main_tabs[0]:
            display_membership_metrics(subs_df)
            st.divider()
            
            # Pass activities data to show_member_growth if available
            if "activities_cache" in st.session_state and not st.session_state.activities_cache.empty:
                show_member_growth(subs_df, st.session_state.activities_cache)
            else:
                show_member_growth(subs_df)
        
        # Removed MRR Tracking tab - we'll implement this in the future
        
        # Combined Plans and Revenue visualization
        with main_tabs[1]:
            show_plans_and_revenue(subs_df)
        
        # Education Members visualization (if available)
        if "is_education" in subs_df.columns:
            with main_tabs[2]:
                show_education_members(subs_df, active_count)
                member_directory_tab_index = 3
        else:
            member_directory_tab_index = 2
            
        # Member Directory tab
        with main_tabs[member_directory_tab_index]:
            # Store member data in session state if not already there
            if "all_members_cache" not in st.session_state and not subs_df.empty:
                # Create a unique list of members with their subscription info
                all_members = prepare_all_members_view(members_df, subs_df)
                st.session_state.all_members_cache = all_members
                
                # Also cache available plans
                st.session_state.available_plans = subs_df["plan"].unique().tolist()
                
            # Simplified consolidated member directory
            if not subs_df.empty:
                
                # Get member subscription data with join dates
                # Get all subscriptions to show each member's join date
                if "consolidated_members_cache" not in st.session_state:
                    # Create a joined date column for members by getting their earliest subscription date
                    members_with_joined = subs_df.sort_values("created_at").drop_duplicates("member_id")
                    members_with_joined = members_with_joined[["member_id", "member_name", "member_email", "created_at", 
                                                              "plan", "active", "is_education" if "is_education" in subs_df.columns else None]].dropna(axis=1)
                    members_with_joined.rename(columns={"member_name": "name", "member_email": "email", "created_at": "joined_date"}, inplace=True)
                    st.session_state.consolidated_members_cache = members_with_joined
                
                # Get the cached member data
                consolidated_members = st.session_state.get("consolidated_members_cache", pd.DataFrame())
                
                # Apply filters to the cached data (client-side filtering)
                filtered_members = consolidated_members.copy()
                
                # Create a column for the Memberful profile URL
                filtered_members["memberful_url"] = filtered_members["member_id"].apply(
                    lambda id: f"https://made.memberful.com/admin/members/{id}"
                )
                
                # Set up display columns with join date
                if "is_education" in filtered_members.columns:
                    display_cols = ["name", "email", "joined_date", "plan", "active", "is_education", "memberful_url"]
                    column_config = {
                        "name": "Member Name",
                        "email": "Email",
                        "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                        "plan": "Membership Plan",
                        "active": st.column_config.CheckboxColumn("Active"),
                        "is_education": st.column_config.CheckboxColumn("Education Member"),
                        "memberful_url": st.column_config.LinkColumn("Memberful Profile")
                    }
                else:
                    display_cols = ["name", "email", "joined_date", "plan", "active", "memberful_url"]
                    column_config = {
                        "name": "Member Name",
                        "email": "Email", 
                        "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                        "plan": "Membership Plan",
                        "active": st.column_config.CheckboxColumn("Active"),
                        "memberful_url": st.column_config.LinkColumn("Memberful Profile")
                    }
                
                # Display the complete member table with sorting capability
                st.dataframe(
                    filtered_members[display_cols].sort_values("joined_date", ascending=False),
                    column_config=column_config,
                    hide_index=True,
                    height=600
                )
                
else:
    st.warning("No member data available. Please check your API connection.")

# Footer
st.markdown("---")
st.caption("Made with ❤️ for Maine Ad + Design")