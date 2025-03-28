"""
Visualization functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from utils import clean_period_data, create_download_button
from datetime import datetime, timedelta

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
        
def show_mrr_waterfall(mrr_changes_df):
    """
    Show monthly recurring revenue changes as a waterfall chart
    
    This chart shows MRR changes by category:
    - Starting MRR
    - New members (positive)
    - Reactivations (positive)
    - Upgrades (positive)
    - Downgrades (negative)
    - Cancellations (negative)
    - Failed payments (negative)
    - Total MRR (net)
    
    Args:
        mrr_changes_df (pd.DataFrame): Dataframe of MRR changes by month and category
    """
    if mrr_changes_df.empty:
        st.info("No MRR data available to display")
        return
        
    # Filter to the most recent month
    months = sorted(mrr_changes_df["month_dt"].unique())
    
    # Add month selection
    selected_month_idx = len(months) - 1  # Default to most recent month
    if len(months) > 1:
        month_options = [m.strftime("%B %Y") for m in months]
        selected_month = st.selectbox(
            "Select month", 
            options=month_options,
            index=selected_month_idx
        )
        selected_month_idx = month_options.index(selected_month)
        
    selected_month_dt = months[selected_month_idx]
    month_display = selected_month_dt.strftime("%B %Y")
    
    # Filter data for the selected month
    month_data = mrr_changes_df[mrr_changes_df["month_dt"] == selected_month_dt]
    
    # Sort data by category order
    month_data = month_data.sort_values("category_order")
    
    # Define category colors
    category_colors = {
        "Starting MRR": "#1f77b4",  # Blue
        "New members": "#2ca02c",   # Green
        "Reactivations": "#9467bd", # Purple
        "Upgrades": "#17becf",      # Cyan
        "Downgrades": "#ff7f0e",    # Orange
        "Cancellations": "#d62728", # Red
        "Failed payments": "#e377c2", # Pink
        "Total MRR": "#1f77b4"      # Blue (same as starting)
    }
    
    # Create the waterfall chart
    categories = month_data["category"].tolist()
    values = month_data["mrr_impact_dollars"].tolist()
    
    # Determine the measure for each category (total, relative, or absolute)
    measure = []
    for cat in categories:
        if cat in ["Starting MRR", "Total MRR"]:
            measure.append("total")
        else:
            measure.append("relative")
    
    # Create the text to display on each bar
    text = []
    for cat, value in zip(categories, values):
        if cat in ["Starting MRR", "Total MRR"]:
            text.append(f"${value:.2f}")
        else:
            if value >= 0:
                text.append(f"+${value:.2f}")
            else:
                text.append(f"${value:.2f}")
    
    # Create the figure
    fig = go.Figure(go.Waterfall(
        name="MRR changes",
        orientation="v",
        measure=measure,
        x=categories,
        textposition="outside",
        text=text,
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        decreasing={"marker": {"color": "#d62728"}},  # Red for decreasing
        increasing={"marker": {"color": "#2ca02c"}},  # Green for increasing
        totals={"marker": {"color": "#1f77b4"}}      # Blue for totals
    ))
    
    # Update layout
    fig.update_layout(
        title={
            "text": f"MRR changes for {month_display}",
            "y": 0.9,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top"
        },
        showlegend=False,
        xaxis_title="",
        yaxis_title="Monthly recurring revenue ($)",
        yaxis=dict(
            gridcolor="lightgray"
        ),
        height=500
    )
    
    # Display the waterfall chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Show month-over-month comparison
    if len(months) > 1 and selected_month_idx > 0:
        st.subheader("Month-over-month MRR changes")
        
        # Get current and previous month data
        current_month = months[selected_month_idx]
        previous_month = months[selected_month_idx - 1]
        
        # Get starting and ending MRR for both months
        current_starting_mrr = month_data[month_data["category"] == "Starting MRR"]["mrr_impact_dollars"].iloc[0]
        current_total_mrr = month_data[month_data["category"] == "Total MRR"]["mrr_impact_dollars"].iloc[0]
        
        prev_month_data = mrr_changes_df[mrr_changes_df["month_dt"] == previous_month]
        prev_starting_mrr = prev_month_data[prev_month_data["category"] == "Starting MRR"]["mrr_impact_dollars"].iloc[0]
        prev_total_mrr = prev_month_data[prev_month_data["category"] == "Total MRR"]["mrr_impact_dollars"].iloc[0]
        
        # Calculate changes
        starting_mrr_change = current_starting_mrr - prev_starting_mrr
        starting_mrr_pct = (starting_mrr_change / prev_starting_mrr * 100) if prev_starting_mrr > 0 else 0
        
        total_mrr_change = current_total_mrr - prev_total_mrr
        total_mrr_pct = (total_mrr_change / prev_total_mrr * 100) if prev_total_mrr > 0 else 0
        
        # Display the metrics side by side
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Starting MRR", 
                f"${current_starting_mrr:.2f}", 
                f"{starting_mrr_change:+.2f} ({starting_mrr_pct:+.1f}%) from previous month"
            )
            
        with col2:
            st.metric(
                "Total MRR", 
                f"${current_total_mrr:.2f}", 
                f"{total_mrr_change:+.2f} ({total_mrr_pct:+.1f}%) from previous month"
            )
    
    # Show detailed breakdown in a table
    st.subheader(f"Detailed MRR breakdown for {month_display}")
    
    # Create a clean table for display
    table_data = month_data.copy()
    table_data = table_data[["category", "mrr_impact_dollars"]]
    table_data.columns = ["Category", "Amount ($)"]
    
    # Format the amount column
    table_data["Amount ($)"] = table_data["Amount ($)"].apply(
        lambda x: f"${x:,.2f}"
    )
    
    # Display the table
    st.dataframe(table_data, hide_index=True)
    
def show_mrr_trend(mrr_changes_df):
    """
    Show MRR trend over time
    
    Args:
        mrr_changes_df (pd.DataFrame): Dataframe of MRR changes by month and category
    """
    if mrr_changes_df.empty:
        st.info("No MRR data available to display")
        return
    
    # Get total MRR by month
    total_mrr = mrr_changes_df[mrr_changes_df["category"] == "Total MRR"].copy()
    starting_mrr = mrr_changes_df[mrr_changes_df["category"] == "Starting MRR"].copy()
    
    # Format month labels
    total_mrr["month_label"] = total_mrr["month_dt"].dt.strftime("%b %Y")
    starting_mrr["month_label"] = starting_mrr["month_dt"].dt.strftime("%b %Y")
    
    # Sort by month
    total_mrr = total_mrr.sort_values("month_dt")
    starting_mrr = starting_mrr.sort_values("month_dt")
    
    # Create the figure
    fig = go.Figure()
    
    # Add starting MRR line
    fig.add_trace(go.Scatter(
        x=starting_mrr["month_label"],
        y=starting_mrr["mrr_impact_dollars"],
        mode="lines+markers",
        name="Starting MRR",
        line=dict(color="#1f77b4", width=2),
        marker=dict(size=8)
    ))
    
    # Add total MRR line
    fig.add_trace(go.Scatter(
        x=total_mrr["month_label"],
        y=total_mrr["mrr_impact_dollars"],
        mode="lines+markers",
        name="Total MRR",
        line=dict(color="#2ca02c", width=2),
        marker=dict(size=8)
    ))
    
    # Update layout
    fig.update_layout(
        title={
            "text": "Monthly recurring revenue (MRR) trend",
            "y": 0.9,
            "x": 0.5,
            "xanchor": "center",
            "yanchor": "top"
        },
        xaxis_title="",
        yaxis_title="Monthly recurring revenue ($)",
        yaxis=dict(
            gridcolor="lightgray"
        ),
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Display the trend chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate growth metrics
    if len(total_mrr) > 1:
        # Calculate month-over-month growth rate
        latest_mrr = total_mrr["mrr_impact_dollars"].iloc[-1]
        previous_mrr = total_mrr["mrr_impact_dollars"].iloc[-2]
        mom_growth = (latest_mrr - previous_mrr) / previous_mrr * 100 if previous_mrr > 0 else 0
        
        # Calculate month-over-month growth amount
        mom_growth_amount = latest_mrr - previous_mrr
        
        # Calculate estimated annual MRR
        annual_mrr = latest_mrr * 12
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Month-over-month growth", 
                f"{mom_growth:.1f}%", 
                f"${mom_growth_amount:+,.2f}"
            )
            
        with col2:
            st.metric(
                "Current MRR", 
                f"${latest_mrr:,.2f}"
            )
            
        with col3:
            st.metric(
                "Estimated annual revenue", 
                f"${annual_mrr:,.2f}"
            )
            
def show_revenue_breakdown(activities_df):
    """
    Show revenue breakdown by category
    
    Args:
        activities_df (pd.DataFrame): Dataframe of subscription activities
    """
    if activities_df.empty:
        st.info("No activity data available to display")
        return
        
    # Get the latest 12 months of data
    today = datetime.now()
    twelve_months_ago = today - timedelta(days=365)
    
    # Filter for recent activities
    recent_activities = activities_df[activities_df["created_at"] >= twelve_months_ago].copy()
    
    if recent_activities.empty:
        st.info("No recent activity data available to display")
        return
        
    # Group by month and type
    monthly_data = recent_activities.groupby(["month_name", "category"])["mrr_impact_dollars"].sum().reset_index()
    
    # Filter to only include main categories
    categories = ["New members", "Reactivations", "Upgrades", "Downgrades", "Cancellations", "Failed payments"]
    monthly_data = monthly_data[monthly_data["category"].isin(categories)]
    
    # Add month datetime for sorting
    monthly_data["month_dt"] = monthly_data["month_name"].apply(
        lambda x: datetime.strptime(x, "%b %Y") if isinstance(x, str) else None
    )
    
    # Sort by month
    monthly_data = monthly_data.sort_values("month_dt")
    
    # Get list of months for x-axis order
    months = sorted(monthly_data["month_dt"].unique())
    month_labels = [m.strftime("%b %Y") for m in months]
    
    # Create stacked bar chart
    positive_categories = ["New members", "Reactivations", "Upgrades"]
    negative_categories = ["Downgrades", "Cancellations", "Failed payments"]
    
    # Prepare data for visualization
    positive_data = monthly_data[monthly_data["category"].isin(positive_categories)].copy()
    negative_data = monthly_data[monthly_data["category"].isin(negative_categories)].copy()
    
    # Ensure negative values are actually negative
    negative_data["mrr_impact_dollars"] = negative_data["mrr_impact_dollars"].abs() * -1
    
    # Combine data for visualization
    viz_data = pd.concat([positive_data, negative_data])
    
    # Create the figure
    fig = px.bar(
        viz_data,
        x="month_name",
        y="mrr_impact_dollars",
        color="category",
        color_discrete_map={
            "New members": "#2ca02c",      # Green
            "Reactivations": "#9467bd",    # Purple
            "Upgrades": "#17becf",         # Cyan
            "Downgrades": "#ff7f0e",       # Orange
            "Cancellations": "#d62728",    # Red
            "Failed payments": "#e377c2"   # Pink
        },
        title="Monthly revenue changes by category",
        labels={
            "month_name": "",
            "mrr_impact_dollars": "MRR impact ($)",
            "category": "Category"
        },
        barmode="relative"
    )
    
    # Update layout
    fig.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=month_labels
        ),
        yaxis=dict(
            title="MRR impact ($)",
            gridcolor="lightgray"
        ),
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )
    
    # Display the chart
    st.plotly_chart(fig, use_container_width=True)
    
    # Display net MRR change by month
    st.subheader("Net MRR change by month")
    
    # Calculate net change by month
    net_by_month = monthly_data.groupby("month_name")["mrr_impact_dollars"].sum().reset_index()
    net_by_month["month_dt"] = net_by_month["month_name"].apply(
        lambda x: datetime.strptime(x, "%b %Y") if isinstance(x, str) else None
    )
    net_by_month = net_by_month.sort_values("month_dt")
    
    # Create a bar chart for net change
    net_fig = px.bar(
        net_by_month,
        x="month_name",
        y="mrr_impact_dollars",
        title="",
        labels={
            "month_name": "",
            "mrr_impact_dollars": "Net MRR change ($)"
        },
        color="mrr_impact_dollars",
        color_continuous_scale=["#d62728", "#d62728", "#ffffff", "#2ca02c", "#2ca02c"],
        range_color=[-max(abs(net_by_month["mrr_impact_dollars"])), max(abs(net_by_month["mrr_impact_dollars"]))]
    )
    
    # Update layout
    net_fig.update_layout(
        xaxis=dict(
            categoryorder='array',
            categoryarray=month_labels
        ),
        yaxis=dict(
            title="Net MRR change ($)",
            gridcolor="lightgray"
        ),
        height=400,
        coloraxis_showscale=False
    )
    
    # Add a line for zero
    net_fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="gray")
    
    # Display the chart
    st.plotly_chart(net_fig, use_container_width=True)

def show_plans_and_revenue(subs_df):
    """Show combined membership plan and revenue visualizations"""
    if subs_df.empty:
        st.info("No subscription data available for plan distribution.")
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Active membership by plan")
        # Membership plan distribution
        plan_counts = subs_df[subs_df["active"] == True].groupby("plan").size().reset_index(name="count")
        if not plan_counts.empty:
            # Convert to percentages for pie chart
            total = plan_counts["count"].sum()
            # Use pandas apply with round function for proper rounding
            plan_counts["percentage"] = plan_counts["count"].apply(lambda x: round(x / total * 100, 1))
            
            # Add percentage to labels
            plan_counts["label"] = plan_counts.apply(
                lambda row: f"{row['plan']} ({row['percentage']}%)", axis=1
            )
            
            # Convert to dictionary for pie chart
            pie_data = {row["label"]: row["count"] for _, row in plan_counts.iterrows()}
            
            # Display pie chart using Plotly
            fig = px.pie(
                plan_counts, 
                values="count", 
                names="label",
                title="",  # Title is already added as a subheader
                hole=0.4,  # Create a donut chart for better aesthetics
                color_discrete_sequence=px.colors.qualitative.Pastel  # Use a nice color palette
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))  # Remove margins
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No active membership data available for plan distribution.")
    
    with col2:
        st.subheader("Monthly revenue by plan")
        if not subs_df.empty:
            # Get unique subscriptions to avoid double-counting group members
            unique_active_subs = subs_df[subs_df["active"] == True].drop_duplicates("subscription_id")
            
            # Group plans by monthly revenue
            plan_revenue = unique_active_subs.groupby("plan").agg({
                "monthly_value": "sum",
                "member_id": "nunique"
            }).reset_index()
            
            plan_revenue["monthly_revenue"] = plan_revenue["monthly_value"] / 100  # Convert to dollars
            plan_revenue.rename(columns={"member_id": "members"}, inplace=True)
            
            # Convert to percentages for pie chart
            total_revenue = plan_revenue["monthly_revenue"].sum()
            # Use pandas apply with round function for proper rounding
            plan_revenue["percentage"] = plan_revenue["monthly_revenue"].apply(lambda x: round(x / total_revenue * 100, 1))
            
            # Add percentage and revenue to labels
            plan_revenue["label"] = plan_revenue.apply(
                lambda row: f"{row['plan']} (${row['monthly_revenue']:.0f}, {row['percentage']}%)", axis=1
            )
            
            # Convert to dictionary for pie chart
            revenue_pie_data = {row["label"]: row["monthly_revenue"] for _, row in plan_revenue.iterrows()}
            
            # Display pie chart using Plotly
            fig = px.pie(
                plan_revenue, 
                values="monthly_revenue", 
                names="label",
                title="",  # Title is already added as a subheader
                hole=0.4,  # Create a donut chart for better aesthetics
                color_discrete_sequence=px.colors.qualitative.Pastel  # Use a nice color palette
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))  # Remove margins
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add a table with more detailed information
            st.subheader("Plan revenue details")
            detail_table = plan_revenue[["plan", "members", "monthly_revenue"]].copy()
            # Avoid division by zero
            detail_table["avg_per_member"] = detail_table.apply(
                lambda x: x["monthly_revenue"] / x["members"] if x["members"] > 0 else 0, 
                axis=1
            )
            detail_table["monthly_revenue"] = detail_table["monthly_revenue"].map("${:.2f}".format)
            detail_table["avg_per_member"] = detail_table["avg_per_member"].map("${:.2f}".format)
            detail_table.columns = ["Plan", "Members", "Monthly Revenue", "Avg Revenue per Member"]
            
            st.dataframe(detail_table)
        else:
            st.info("No active membership data available for revenue analysis.")

def show_education_members(subs_df, active_count):
    """Show education members visualization using native Streamlit charts"""
    if subs_df.empty or "is_education" not in subs_df.columns:
        st.info("No education member data available for analysis.")
        return
        
    # Count active education members
    education_members = subs_df[(subs_df["active"] == True) & (subs_df["is_education"] == True)]
    
    if education_members.empty:
        st.info("No education members found.")
        return
        
    # Create a pie chart of education vs non-education active members
    education_count = len(education_members.drop_duplicates("member_id"))
    non_education_count = active_count - education_count
    
    # Calculate percentages
    total = education_count + non_education_count
    edu_percent = round((education_count / total * 100), 1)
    non_edu_percent = round((non_education_count / total * 100), 1)
    
    # Create pie chart data
    st.subheader("Education members vs all others")
    pie_data = {
        f"Education Members ({edu_percent}%)": education_count,
        f"Standard Members ({non_edu_percent}%)": non_education_count
    }
    
    # Create data for pie chart
    edu_pie_data = pd.DataFrame([
        {"type": f"Education Members ({edu_percent}%)", "count": education_count},
        {"type": f"Standard Members ({non_edu_percent}%)", "count": non_education_count}
    ])
    
    # Display pie chart using Plotly
    fig = px.pie(
        edu_pie_data, 
        values="count", 
        names="type",
        title="",  # Title is already added as a subheader
        hole=0.4,  # Create a donut chart for better aesthetics
        color_discrete_sequence=[px.colors.qualitative.Pastel[2], px.colors.qualitative.Pastel[0]]  # Use consistent colors
    )
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))  # Remove margins
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate growth of education members over time
    education_members["month"] = education_members["created_at"].dt.to_period("M")
    edu_by_month = education_members.groupby(education_members["month"]).size().reset_index(name="count")
    
    # Format month for display
    edu_by_month["month_str"] = edu_by_month["month"].astype(str)
    edu_by_month["sort_key"] = edu_by_month["month_str"].apply(
        lambda p: int(p.split("-")[0]) * 100 + int(p.split("-")[1]) if len(p.split("-")) == 2 else 0
    )
    edu_by_month = edu_by_month.sort_values("sort_key")
    
    # Format the month names nicely
    month_display = []
    for _, row in edu_by_month.iterrows():
        try:
            parts = row["month_str"].split('-')
            if len(parts) == 2:
                year, month = int(parts[0]), int(parts[1])
                month_name = f"{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]} {year}"
                month_display.append(month_name)
        except Exception:
            continue
    
    # Create a bar chart for education member growth by month
    st.subheader("Education member growth by month")
    
    if month_display:
        # Create datetime values for sorting
        month_dt_values = []
        for month_name in month_display:
            try:
                # Parse month names like "Jan 2022"
                month_dt = datetime.strptime(month_name, "%b %Y")
                month_dt_values.append(month_dt)
            except ValueError:
                month_dt_values.append(None)
        
        # Create and sort data
        chart_data = pd.DataFrame({
            "Month": month_display,
            "Month_dt": month_dt_values,
            "New Education Members": edu_by_month["count"].tolist()[:len(month_display)]
        })
        
        # Sort by date
        chart_data = chart_data.sort_values("Month_dt").dropna(subset=["Month_dt"])
        
        # Create Plotly bar chart with chronological ordering
        fig = px.bar(
            chart_data,
            x="Month",
            y="New Education Members",
            title=""
        )
        
        # Ensure proper chronological order
        fig.update_layout(
            xaxis=dict(
                categoryorder='array',
                categoryarray=chart_data["Month"].tolist(),
                title=""
            ),
            yaxis=dict(title="")
        )
        
        # Display the chart
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No monthly data available for education members.")
        
def show_member_activities(activities_df):
    """
    Display recent member activities in reverse chronological order
    
    Args:
        activities_df (pd.DataFrame): DataFrame of processed activities
    """
    if activities_df.empty:
        st.info("No activity data available to display")
        return
    
    st.subheader("Recent membership activities")
    
    # Helper function to format activity types nicely
    def format_activity_type(activity_type):
        if activity_type == "new_order" or activity_type == "new_subscription":
            return "New subscription"
        elif activity_type == "subscription_deactivated":
            return "Subscription deactivated"
        elif activity_type == "subscription_reactivated":
            return "Subscription reactivated"
        elif activity_type == "free_signup":
            return "Free signup"
        elif "renewal" in activity_type and "failed" in activity_type:
            return "Renewal failed"
        elif activity_type == "renewal":
            return "Subscription renewed"
        elif activity_type == "upgrade":
            return "Plan upgraded"
        elif activity_type == "downgrade":
            return "Plan downgraded"
        elif activity_type == "auto_renew_disabled":
            return "Auto-renewal disabled"
        elif activity_type == "team_member_deleted":
            return "Team member removed"
        elif activity_type == "new_team_member":
            return "New team member added"
        else:
            return activity_type.replace("_", " ").title()
    
    # Define emoji for different activity types
    activity_emojis = {
        "New subscription": "🟢",
        "Subscription renewed": "🔄",
        "Free signup": "🔵",
        "Subscription deactivated": "🔴",
        "Auto-renewal disabled": "🟠",
        "Team member removed": "👤❌",
        "New team member added": "👤➕",
        "Renewal failed": "⚠️",
        "Plan upgraded": "⬆️",
        "Plan downgraded": "⬇️",
        "Education members": "🎓",
        "Education renewals": "🎓",
        "Education cancellations": "🎓",
        "Education changes": "🎓"
    }
    
    # Default emoji for other activities
    default_emoji = "ℹ️"
    
    # Fixed number of activities to show
    num_activities = 100
    
    # Create a copy of the activities dataframe to avoid modifying the original
    display_activities = activities_df.copy()
    
    # Format the timestamp for display
    display_activities["timestamp"] = display_activities["created_at"].dt.strftime("%b %d %I:%M %p")
    
    # Create columns for the display
    display_activities["member_name"] = display_activities["member_name"].fillna("Unknown")
    
    # Format activity types
    display_activities["activity"] = display_activities["type"].apply(format_activity_type)
    
    # Add emoji to each activity, with special emoji for education members
    def get_activity_emoji(row):
        activity = row["activity"]
        is_education = row.get("is_education", False)
        
        # Use education emoji for education members
        if is_education:
            if "New subscription" in activity or "new_order" in activity:
                return "🎓"
            elif "Subscription renewed" in activity:
                return "🎓"
            elif "Subscription deactivated" in activity:
                return "🎓❌"
            else:
                return "🎓"
        
        # Regular emoji for non-education members
        return activity_emojis.get(activity, default_emoji)
        
    display_activities["emoji"] = display_activities.apply(get_activity_emoji, axis=1)
    
    # Make sure required plan columns exist
    for col in ["plan_name", "plan_price_cents", "interval_unit", "interval_count"]:
        if col not in display_activities.columns:
            display_activities[col] = None
    
    # Add memberful profile link
    display_activities["memberful_url"] = display_activities["member_id"].apply(
        lambda id: f"https://made.memberful.com/admin/members/{id}" if pd.notna(id) else None
    )
    
    # Format plan details in a compact way
    def format_plan_details(row):
        if pd.notna(row["plan_name"]) and pd.notna(row["plan_price_cents"]):
            price = row["plan_price_cents"] / 100
            interval = row["interval_unit"] if pd.notna(row["interval_unit"]) else "month"
            interval_count = row["interval_count"] if pd.notna(row["interval_count"]) else 1
            
            if interval_count > 1:
                return f"{row['plan_name']} (${price:.0f}/{interval_count} {interval}s)"
            else:
                return f"{row['plan_name']} (${price:.0f}/{interval})"
        return ""
    
    display_activities["plan_details"] = display_activities.apply(format_plan_details, axis=1)
    
    # Create a compact description for each activity
    def format_compact_description(row):
        activity = row["activity"].lower()
        name = row["member_name"]
        is_education = row.get("is_education", False)
        category = row.get("category", "")
        
        # Make name a link if we have a member URL
        if pd.notna(row["memberful_url"]):
            name = f"[{name}]({row['memberful_url']})"
            
        plan = row["plan_details"]
        
        # Add education indicator for plan if applicable
        if is_education and plan:
            # Extract the plan name but remove the price since it's an education plan
            plan_name_only = plan.split(" ($")[0]
            plan = f"{plan_name_only} (Free - Education membership)"
        
        # Handle education members specifically
        if is_education:
            if "new subscription" in activity.lower() or "new order" in activity.lower():
                return f"{name} joined with {plan}"
            elif "renewed" in activity.lower():
                return f"{name} renewed {plan}"
            elif "deactivated" in activity.lower():
                return f"{name} cancelled {plan}"
            elif "disabled" in activity.lower():
                return f"{name} disabled auto-renewal for {plan}"
            elif "upgrade" in activity.lower() or "downgrade" in activity.lower():
                return f"{name} changed plan to {plan}"
        # Handle regular members
        elif "new subscription" in activity or "new order" in activity:
            return f"{name} joined with {plan}"
        elif "renewed" in activity:
            return f"{name} renewed {plan}"
        elif "deactivated" in activity:
            return f"{name} cancelled {plan}"
        elif "disabled" in activity:
            return f"{name} disabled auto-renewal for {plan}"
        elif "team member" in activity:
            if "added" in activity:
                return f"{name} was added as a team member"
            else:
                return f"{name} was removed as a team member"
        elif "free signup" in activity:
            return f"{name} signed up (free account)"
        elif "plan" in activity:
            if "upgrade" in activity:
                return f"{name} upgraded to {plan}"
            elif "downgrade" in activity:
                return f"{name} downgraded to {plan}"
        
        # Default case
        if plan:
            return f"{name}: {activity} - {plan}"
        else:
            return f"{name}: {activity}"
    
    display_activities["compact_description"] = display_activities.apply(format_compact_description, axis=1)
    
    # Sort by created_at in descending order (newest first)
    display_activities = display_activities.sort_values("created_at", ascending=False)
    
    # Limit number of activities to display
    display_activities = display_activities.head(num_activities)
    
    # Display as a compact linear feed
    for i, activity in display_activities.iterrows():
        # Create a compact row with emoji, description, and time
        with st.container():
            cols = st.columns([1, 15, 4])
            
            with cols[0]:
                st.markdown(f"<div style='font-size:24px; text-align:center;'>{activity['emoji']}</div>", unsafe_allow_html=True)
            
            with cols[1]:
                st.markdown(activity["compact_description"])
            
            with cols[2]:
                st.caption(activity["timestamp"])
    
    # Show a message if no activities are available
    if display_activities.empty:
        st.info("No activities available to display.")
