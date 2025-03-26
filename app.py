import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# Import our custom modules
from api import get_memberful_data, fetch_all_members
from utils import get_date_n_months_ago, is_education_member, create_download_button
from data_processing import process_members_data, prepare_all_members_view, prepare_new_members, calculate_mrr
from visualizations import show_member_growth, show_plans_and_revenue, show_education_members

# App configuration
st.set_page_config(
    page_title="Maine Ad + Design membership dashboard",
    page_icon="🎨",
    layout="wide",
)

# Sidebar for filters and options
st.sidebar.title("Maine Ad + Design membership dashboard")
# st.sidebar.image("https://site-assets.memberful.com/qiyhr8wsbhqpdf9s9p4yn78mlcsy", width=200)

# Debug mode toggle
debug_mode = st.sidebar.checkbox("Debug mode")

# Add additional sidebar content
st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ for Maine Ad + Design")

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

with st.sidebar:
    # Show the last updated time
    if "last_fetch_time" in st.session_state:
        last_fetch = st.session_state.last_fetch_time.strftime("%b %d, %Y at %I:%M %p")
        st.caption(f"Last updated: {last_fetch}")
    
    # Add refresh button
    if st.button("🔄 Refresh Data"):
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

# Display membership metrics and visualizations
if 'members_df' in locals() and not members_df.empty:
    # Summary metrics
    st.subheader("Metrics")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Calculate metrics
    current_mrr, paying_members_count, active_count, education_count = calculate_mrr(subs_df)
    
    # Store education count in session state for later use
    st.session_state.education_count = education_count
    
    # Set standard time periods for analysis
    today = datetime.now()
    past_30_days = today - timedelta(days=30)
    past_90_days = today - timedelta(days=90)
    past_year = today - timedelta(days=365)
    
    # Active members last year (for comparison)
    one_year_ago = today - timedelta(days=365)
    active_last_year = len(subs_df[(subs_df["active"] == True) & 
                             (subs_df["created_at"] <= one_year_ago)]) if not subs_df.empty else 0
    
    # Calculate yearly growth percentage
    # yearly_growth = active_count - active_last_year
    # This will be useful once we have a full year of data
    # col1.metric("Active Members", active_count, f"{yearly_growth:+d} from last year")
    col1.metric("Active members", active_count)
    
    # Display MRR
    if not subs_df.empty:
        # Calculate MRR from last month (30 days ago)
        thirty_days_ago = today - timedelta(days=30)
        
        if "is_education" in subs_df.columns:
            active_month_ago = subs_df[
                (subs_df["created_at"] <= thirty_days_ago) & 
                ((subs_df["expires_at"] > thirty_days_ago) | (subs_df["expires_at"].isna())) &
                (subs_df["is_education"] == False)
            ].drop_duplicates("subscription_id")
        else:
            active_month_ago = subs_df[
                (subs_df["created_at"] <= thirty_days_ago) & 
                ((subs_df["expires_at"] > thirty_days_ago) | (subs_df["expires_at"].isna()))
            ].drop_duplicates("subscription_id")
        
        # Calculate MRR from those subscriptions
        previous_mrr = active_month_ago["monthly_value"].sum() / 100 if not active_month_ago.empty else 0
        
        # Calculate month-over-month change
        mrr_change = current_mrr - previous_mrr
        mrr_change_percent = (mrr_change / previous_mrr * 100) if previous_mrr > 0 else 0
        
        col2.metric(
            "Monthly recurring revenue", 
            f"${current_mrr:,.2f}", 
            f"{mrr_change_percent:+.1f}% from last month"
        )
        
        # Display paying members count (vs total members)
        non_education_count = active_count - education_count
        col3.metric(
            "Paying members", 
            paying_members_count,
            f"of {non_education_count} non-education members"
        )
    else:
        col2.metric("Monthly Recurring Revenue", "$0.00")
        col3.metric("Paying Members", 0)
    
    # New members in last 30 days
    new_subs_30d = prepare_new_members(subs_df, 30)
    new_count_30d = len(new_subs_30d)
    
    # New members in the 30 days before that (for comparison)
    prev_30_days = past_30_days - timedelta(days=30)
    prev_period_subs = subs_df[(subs_df["created_at"] >= prev_30_days) & 
                         (subs_df["created_at"] < past_30_days)]
    new_prev_30d = len(prev_period_subs.drop_duplicates("subscription_id")) if not prev_period_subs.empty else 0
    
    # Calculate monthly growth delta
    monthly_growth = new_count_30d - new_prev_30d
    col4.metric("New subscriptions, last 30 days", new_count_30d, f"{monthly_growth:+d} vs previous 30 days")
    
    # Education members count
    education_percentage = (education_count / active_count * 100) if active_count > 0 else 0
    col5.metric("Education members", education_count, f"{education_percentage:.1f}% of active members")
    
    # Main Dashboard Tabs
    st.divider()
    
    # Create main tabs for the dashboard
    if "is_education" in subs_df.columns:
        main_tabs = st.tabs(["Member Growth", "Plans and Revenue", "Education Members", "Member Directory"])
    else:
        main_tabs = st.tabs(["Member Growth", "Plans and Revenue", "Member Directory"])
    
    if not subs_df.empty:
        # Member Growth visualization
        with main_tabs[0]:
            show_member_growth(subs_df)
        
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
                
                # Initialize filter states
                if "show_active_only" not in st.session_state:
                    st.session_state.show_active_only = False
                if "selected_plans" not in st.session_state:
                    st.session_state.selected_plans = []
                if "show_education_only" not in st.session_state:
                    st.session_state.show_education_only = False
                
                
            # Simplified consolidated member directory
            if not subs_df.empty:
                # Add filters using session state to avoid reloads
                col1, col2 = st.columns(2)
                
                # Active members filter with on_change callback
                show_active_only = col1.checkbox(
                    "Show active members only", 
                    value=st.session_state.get("show_active_only", True),
                    key="show_active_only"
                    )
                
                # Education members filter with on_change callback
                show_education_only = col2.checkbox(
                    "Show education members only",
                    value=st.session_state.get("show_education_only", False),
                    key="show_education_only"
                    )
                
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
                
                # Filter active members if requested
                if show_active_only:
                    filtered_members = filtered_members[filtered_members["active"] == True]
                
                # Filter education members if requested
                if show_education_only and "is_education" in filtered_members.columns:
                    # Add debugging info
                    if debug_mode:
                        st.write(f"Before filtering: {len(filtered_members)} members")
                        education_count = filtered_members["is_education"].sum()
                        st.write(f"Found {education_count} education members in the dataset")
                        # Show the first few education members
                        st.write("Education members:", filtered_members[filtered_members["is_education"] == True].head(3))
                    
                    # Apply the filter - convert to string then boolean to ensure proper comparison
                    filtered_members = filtered_members[filtered_members["is_education"] == True]
                    
                    if debug_mode:
                        st.write(f"After filtering: {len(filtered_members)} members")
                
                # Set up display columns with join date
                if "is_education" in filtered_members.columns:
                    display_cols = ["name", "email", "joined_date", "plan", "active", "is_education"]
                    column_config = {
                        "name": "Member Name",
                        "email": "Email",
                        "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                        "plan": "Membership Plan",
                        "active": st.column_config.CheckboxColumn("Active"),
                        "is_education": st.column_config.CheckboxColumn("Education Member")
                    }
                else:
                    display_cols = ["name", "email", "joined_date", "plan", "active"]
                    column_config = {
                        "name": "Member Name",
                        "email": "Email", 
                        "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                        "plan": "Membership Plan",
                        "active": st.column_config.CheckboxColumn("Active")
                    }
                
                # Display the complete member table with sorting capability
                st.dataframe(
                    filtered_members[display_cols].sort_values("joined_date", ascending=False),
                    column_config=column_config,
                    hide_index=True
                )
                
                # Add download button
                create_download_button(filtered_members[display_cols], "made_members.csv")
else:
    st.warning("No member data available. Please check your API connection.")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ for Maine Ad + Design")