"""
Revenue visualization functions
"""
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

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