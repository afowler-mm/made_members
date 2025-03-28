"""
Member growth visualization functions
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

def show_member_growth(subs_df, activities_df=None):
    """
    Show member growth visualization using Streamlit charts
    
    Args:
        subs_df: DataFrame of subscription data
        activities_df: Optional DataFrame of activity data from the Memberful API
    """
    if subs_df.empty:
        st.info("No subscription data available for growth chart.")
        return
    
    # PART 1: Subscription Changes by Month (New/Canceled/Net)
    st.subheader("Membership growth by month")
    
    # Get new subscriptions by month
    subs_df["month"] = subs_df["created_at"].dt.to_period("M")
    
    # Filter to recent data (since July 2024)
    start_date = datetime(2024, 7, 1)
    recent_subs = subs_df[subs_df["created_at"] >= start_date]
    
    # Count only unique subscriptions to avoid double-counting
    unique_subs = recent_subs.drop_duplicates('subscription_id')
    
    # Initialize dataframes for different types of changes
    activity_types = {
        'new': ['new_order'],  # New subscriptions
        'churned': ['subscription_deactivated'],  # Cancellations
        'renewed': ['renewal']  # Renewals
    }
    
    # If we have activity data, use it for more detailed metrics
    if activities_df is not None and not activities_df.empty:
        # Convert timestamp to datetime if needed
        if "created_at" in activities_df.columns and not pd.api.types.is_datetime64_any_dtype(activities_df["created_at"]):
            activities_df["created_at"] = pd.to_datetime(activities_df["created_at"], unit='s')
        
        # Filter to recent activities
        recent_activities = activities_df[activities_df["created_at"] >= start_date]
        
        if not recent_activities.empty:
            # Add month column for grouping
            recent_activities["month"] = recent_activities["created_at"].dt.to_period("M")
            
            # Get counts by month for each activity type
            change_by_type = {}
            
            for change_type, act_types in activity_types.items():
                # Filter activities by type
                type_activities = recent_activities[recent_activities["type"].isin(act_types)]
                
                if not type_activities.empty:
                    # Count unique subscriptions per month
                    by_month = type_activities.drop_duplicates('subscription_id').groupby("month").size().reset_index(name=change_type)
                    change_by_type[change_type] = by_month
            
            # Group by month to get new subscriptions from activity data
            if 'new' in change_by_type:
                new_by_month = change_by_type['new']
            else:
                # Fall back to subscription data
                new_by_month = unique_subs.groupby(unique_subs["month"]).size().reset_index(name="new")
            
            # Get churned subscriptions from activity data
            if 'churned' in change_by_type:
                churned_by_month = change_by_type['churned']
            else:
                # Fall back to subscription data for churned
                today = datetime.now()
                expired_subs = recent_subs[(recent_subs["expires_at"].notna()) & 
                                        (recent_subs["expires_at"] <= today) & 
                                        (recent_subs["active"] == False)]
                
                # Process expiration dates into months and count unique cancellations
                churned_by_month = pd.DataFrame(columns=["month", "churned"])
                if not expired_subs.empty:
                    expired_subs["month"] = expired_subs["expires_at"].dt.to_period("M")
                    churned_by_month = expired_subs.drop_duplicates('subscription_id').groupby("month").size().reset_index(name="churned")
            
            # Get renewals from activity data
            if 'renewed' in change_by_type:
                renewed_by_month = change_by_type['renewed']
            else:
                # No renewal data available from subscriptions
                renewed_by_month = pd.DataFrame(columns=["month", "renewed"])
        else:
            # Fall back to subscription data
            new_by_month = unique_subs.groupby(unique_subs["month"]).size().reset_index(name="new")
            
            # Get expired/canceled subscriptions by month
            today = datetime.now()
            expired_subs = recent_subs[(recent_subs["expires_at"].notna()) & 
                                    (recent_subs["expires_at"] <= today) & 
                                    (recent_subs["active"] == False)]
            
            # Process expiration dates into months and count unique cancellations
            churned_by_month = pd.DataFrame(columns=["month", "churned"])
            if not expired_subs.empty:
                expired_subs["month"] = expired_subs["expires_at"].dt.to_period("M")
                churned_by_month = expired_subs.drop_duplicates('subscription_id').groupby("month").size().reset_index(name="churned")
            
            # No renewal data available from subscriptions
            renewed_by_month = pd.DataFrame(columns=["month", "renewed"])
    else:
        # Use subscription data only
        new_by_month = unique_subs.groupby(unique_subs["month"]).size().reset_index(name="new")
        
        # Get expired/canceled subscriptions by month
        today = datetime.now()
        expired_subs = recent_subs[(recent_subs["expires_at"].notna()) & 
                                (recent_subs["expires_at"] <= today) & 
                                (recent_subs["active"] == False)]
        
        # Process expiration dates into months and count unique cancellations
        churned_by_month = pd.DataFrame(columns=["month", "churned"])
        if not expired_subs.empty:
            expired_subs["month"] = expired_subs["expires_at"].dt.to_period("M")
            churned_by_month = expired_subs.drop_duplicates('subscription_id').groupby("month").size().reset_index(name="churned")
        
        # No renewal data available from subscriptions
        renewed_by_month = pd.DataFrame(columns=["month", "renewed"])
    
    # Create a list of all unique months from all dataframes
    all_months = pd.concat([
        new_by_month["month"] if not new_by_month.empty else pd.Series(dtype='period[M]'),
        churned_by_month["month"] if not churned_by_month.empty else pd.Series(dtype='period[M]'),
        renewed_by_month["month"] if not renewed_by_month.empty and not renewed_by_month.empty else pd.Series(dtype='period[M]')
    ]).unique()
    
    # Create a dataframe with all months
    monthly_changes = pd.DataFrame({"month": all_months})
    
    # Merge in all the changes
    monthly_changes = pd.merge(monthly_changes, new_by_month, on="month", how="left").fillna(0)
    monthly_changes = pd.merge(monthly_changes, churned_by_month, on="month", how="left").fillna(0)
    
    # Add renewals if available
    if not renewed_by_month.empty and "renewed" in renewed_by_month.columns:
        monthly_changes = pd.merge(monthly_changes, renewed_by_month, on="month", how="left").fillna(0)
    else:
        monthly_changes["renewed"] = 0
    
    # Calculate net change
    monthly_changes["net"] = monthly_changes["new"] - monthly_changes["churned"]
    
    # Format month strings for display
    monthly_changes["month_str"] = monthly_changes["month"].astype(str)
    
    # Convert to datetime for proper sorting
    monthly_changes["month_dt"] = monthly_changes["month_str"].apply(
        lambda m: datetime.strptime(m, "%Y-%m") if "-" in m else None
    )
    
    # Sort by date
    monthly_changes = monthly_changes.sort_values("month_dt")
    
    # Format month names nicely
    monthly_changes["display_month"] = monthly_changes["month_dt"].apply(
        lambda dt: dt.strftime("%b %Y") if pd.notna(dt) else ""
    )
    
    # Sort monthly_changes chronologically first
    monthly_changes = monthly_changes.sort_values("month_dt")
    
    # Determine which columns to plot based on data availability
    plot_columns = ["new", "churned"]
    if monthly_changes["renewed"].sum() > 0:
        plot_columns.append("renewed")
    
    # Only show explanation if we have cancellations
    if monthly_changes["churned"].sum() > 0:
        st.caption("Shows monthly subscription activity: new additions, cancellations, and renewals")
    
    # Use Plotly for better control over x-axis ordering
    fig = px.bar(
        monthly_changes,
        x="display_month",
        y=plot_columns,
        barmode="group",
        labels={
            "display_month": "Month",
            "new": "New Subscriptions",
            "churned": "Cancellations",
            "renewed": "Renewals",
            "value": "Count",
            "variable": "Type"
        },
        title=""
    )
    
    # Negate churned values for visualization
    fig.update_traces(
        y=[-y for y in monthly_changes["churned"].values],
        selector=dict(name="churned")
    )
    
    # Define better names for the traces
    newnames = {
        'new': 'New Subscriptions', 
        'churned': 'Cancellations',
        'renewed': 'Renewals'
    }
    
    # Set custom axis labels and ensure correct order
    fig.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=monthly_changes["display_month"].tolist(),
            title=""
        ),
        yaxis=dict(title=""),
        legend_title_text="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    # Update trace names
    fig.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name)))
    
    # Display the plotly chart
    st.plotly_chart(fig, use_container_width=True)
    
    # PART 2: Total Membership Over Time
    st.subheader("Total membership by month")
    
    # Calculate the current active member count
    active_members = subs_df[subs_df["active"] == True]
    current_active_count = len(active_members.drop_duplicates("member_id"))
    
    # For each month, calculate the total active members working backwards from current count
    all_months_sorted = sorted(all_months)
    
    # Create a DataFrame for tracking membership over time
    membership_data = []
    
    # Start with the current total and work backwards
    running_total = current_active_count
    
    # First, create a temporary list to build the data backwards
    temp_membership_data = []
    
    # Determine what categories we have data for
    has_renewals = monthly_changes["renewed"].sum() > 0
    
    # Reverse the months to calculate backwards from current
    for i, month in enumerate(reversed(all_months_sorted)):
        # Get data for this month in our changes dataframe
        month_data = monthly_changes[monthly_changes["month"] == month]
        
        if not month_data.empty:
            # Get the month string for display
            display_month = month_data["display_month"].iloc[0]
            
            # Get the change numbers for this month
            new_members = int(month_data["new"].iloc[0])
            churned_members = int(month_data["churned"].iloc[0])
            renewed_members = int(month_data["renewed"].iloc[0]) if has_renewals else 0
            
            # If this is the most recent month (first in reversed loop)
            if i == 0:
                # For the latest month, keep the current count
                month_total = running_total
            else:
                # For earlier months, reverse-calculate the total
                # by subtracting new members and adding churned members
                running_total = running_total - new_members + churned_members
                month_total = running_total
            
            # Prepare data object for this month
            month_obj = {
                "Month": display_month,
                "Continuing Members": month_total - new_members,
                "New Members": new_members,
                "Cancelled Members": -churned_members if churned_members > 0 else 0,
                "Total Active": month_total
            }
            
            # Add renewals if we have them
            if has_renewals:
                month_obj["Renewals"] = renewed_members
                
            # Add to our temporary data
            temp_membership_data.append(month_obj)
    
    # Reverse the data back to chronological order
    membership_data = list(reversed(temp_membership_data))
    
    # Create dataframe for the total membership chart
    membership_df = pd.DataFrame(membership_data)
    
    if not membership_df.empty:
        # Create datetime for sorting
        membership_df["Month_dt"] = pd.to_datetime([
            datetime.strptime(m, "%b %Y") if isinstance(m, str) else None 
            for m in membership_df["Month"]
        ])
        
        # Sort by date
        membership_df = membership_df.sort_values("Month_dt")
        
        # Display explanation with appropriate categories
        caption = "Shows the total active membership each month, broken down by continuing, new"
        
        # Add renewals to caption if we have them
        if has_renewals and "Renewals" in membership_df.columns:
            caption += ", renewals"
            
        # Add cancellations to caption if we have them
        if membership_df["Cancelled Members"].sum() < 0:
            caption += ", and cancelled members"
        else:
            caption += " members"
            
        st.caption(caption)
        
        # Determine columns for stacked bar chart
        stack_columns = ["Continuing Members", "New Members"]
        
        # Add renewals to stack if we have them
        if has_renewals and "Renewals" in membership_df.columns and membership_df["Renewals"].sum() > 0:
            stack_columns.append("Renewals")
            
        # Only include cancelled if we have any
        if membership_df["Cancelled Members"].sum() < 0:
            stack_columns.append("Cancelled Members")
        
        # Create a stacked bar chart using Plotly
        fig = px.bar(
            membership_df, 
            x="Month", 
            y=stack_columns,
            title="",
            labels={"value": "Members", "variable": "Type"}
        )
        
        # Ensure proper chronological order of months on x-axis
        fig.update_layout(
            xaxis=dict(
                categoryorder='array',
                categoryarray=membership_df["Month"].tolist(),
                title=""
            ),
            yaxis=dict(title=""),
            legend_title_text=""
        )
        
        # Display the stacked bar chart
        st.plotly_chart(fig, use_container_width=True)
        
        # Create line chart for total active members
        line_fig = px.line(
            membership_df, 
            x="Month", 
            y="Total Active",
            markers=True,
            title=""
        )
        
        # Ensure proper chronological order
        line_fig.update_layout(
            xaxis=dict(
                categoryorder='array',
                categoryarray=membership_df["Month"].tolist(),
                title=""
            ),
            yaxis=dict(title="")
        )
        
        # Display the line chart
        st.plotly_chart(line_fig, use_container_width=True)
    else:
        st.info("No membership data available to display.")