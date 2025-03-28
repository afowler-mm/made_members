import streamlit as st
import time
import pandas as pd
from datetime import datetime, timedelta

# Import modules from restructured codebase
from src.api import fetch_all_members, fetch_subscription_activities
from src.data import process_members_data, process_subscription_activities, calculate_mrr
from src.ui import check_password, display_membership_metrics, show_member_directory
from src.visualizations import (
    show_member_growth, 
    show_plans_and_revenue, 
    show_education_members, 
    show_member_activities
)

# App configuration
st.set_page_config(
    page_title="Maine Ad + Design membership dashboard",
    page_icon="🎨",
    layout="wide",
)

# Check for authentication before showing the main content
if not check_password():
    # Stop execution if not authenticated
    st.stop()

# Sidebar for filters and options
st.sidebar.title("Maine Ad + Design membership dashboard")

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
if "education_feature_added" not in st.session_state:
    refresh_data = True
    st.session_state.education_feature_added = True
    # Also clear member caches to ensure they have the education flag
    if "all_members_cache" in st.session_state:
        del st.session_state.all_members_cache
    if "consolidated_members_cache" in st.session_state:
        del st.session_state.consolidated_members_cache

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
        main_tabs = st.tabs(["Activities", "Member growth", "Plans and revenue", "Education members", "Member directory"])
    else:
        main_tabs = st.tabs(["Activities", "Member growth", "Plans and revenue", "Member directory"])
    
    if not subs_df.empty:
        # Fetch activity data for enhanced visualizations if not already in session state
        # Always force refresh activity data to ensure calculations are updated
        refresh_activities = True
            
        if refresh_activities:
            with st.spinner("Fetching recent subscription activities..."):
                # Get activity data for the past 12 months for more complete financial history
                twelve_months_ago = datetime.now() - timedelta(days=365)
                activities_data = fetch_subscription_activities(twelve_months_ago, debug_mode=debug_mode)
                
                # Process activity data if we have any
                if activities_data:
                    activities_df = process_subscription_activities(activities_data)
                    
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
        
        # Activities tab (now the first tab)
        with main_tabs[0]:
            # Show member activities if we have activity data
            if "activities_cache" in st.session_state and not st.session_state.activities_cache.empty:
                show_member_activities(st.session_state.activities_cache)
            else:
                st.info("No member activity data available.")
                
                # Add a button to fetch more activity data
                if st.button("Fetch activity data"):
                    with st.spinner("Fetching member activities..."):
                        # Get activity data for the past 12 months
                        twelve_months_ago = datetime.now() - timedelta(days=365)
                        activities_data = fetch_subscription_activities(twelve_months_ago, debug_mode=debug_mode)
                        
                        # Process activity data if we have any
                        if activities_data:
                            activities_df = process_subscription_activities(activities_data)
                            st.session_state.activities_cache = activities_df
                            st.rerun()
                        else:
                            st.error("Failed to fetch activity data. Please try again later.")
        
        # Member Growth visualization
        with main_tabs[1]:
            display_membership_metrics(subs_df)
            st.divider()
            
            # Pass activities data to show_member_growth if available
            if "activities_cache" in st.session_state and not st.session_state.activities_cache.empty:
                show_member_growth(subs_df, st.session_state.activities_cache)
            else:
                show_member_growth(subs_df)
        
        # Combined Plans and Revenue visualization
        with main_tabs[2]:
            show_plans_and_revenue(subs_df)
        
        # Education Members visualization (if available)
        if "is_education" in subs_df.columns:
            with main_tabs[3]:
                show_education_members(subs_df, active_count)
                member_directory_tab_index = 4
        else:
            member_directory_tab_index = 3
            
        # Member Directory tab
        with main_tabs[member_directory_tab_index]:
            show_member_directory(members_df, subs_df)
            
else:
    st.warning("No member data available. Please check your API connection.")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ for Maine Ad + Design")

# Add logout button
if st.sidebar.button("Logout"):
    st.session_state.pop("authenticated", None)
    st.rerun()