"""
Visualization functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
import plotly.express as px
import streamlit as st
from utils import clean_period_data, create_download_button
from datetime import datetime

def show_member_growth(subs_df):
    """Show member growth visualization"""
    if subs_df.empty:
        st.info("No subscription data available for growth chart.")
        return
        
    # Prepare data for growth chart
    # Get new subscriptions by month
    subs_df["month"] = subs_df["created_at"].dt.to_period("M")
    
    # Filter to data only since July 2024
    start_date = datetime(2024, 7, 1)
    recent_subs = subs_df[subs_df["created_at"] >= start_date]
    
    # Get new by month
    new_by_month = recent_subs.groupby(recent_subs["month"]).size().reset_index(name="new")
    
    # Get expired/canceled subscriptions by month
    expired_subs = recent_subs[recent_subs["expires_at"].notna()]
    expired_subs["end_month"] = expired_subs["expires_at"].dt.to_period("M")
    churn_by_month = expired_subs.groupby(expired_subs["end_month"]).size().reset_index(name="churned")
    
    # Merge the data
    growth_data = pd.merge(new_by_month, churn_by_month, left_on="month", right_on="end_month", how="outer").fillna(0)
    
    # Clean and prepare the data
    growth_data = clean_period_data(growth_data)
    
    # Calculate net change
    growth_data["net"] = growth_data["new"] - growth_data["churned"]
    
    # Prepare data for plotting with formatted month names
    plot_data = []
    for _, row in growth_data.iterrows():
        # Skip rows with zero sort key (these are invalid/placeholder entries)
        if row["sort_key"] == 0:
            continue
            
        # Create nicely formatted month label (Jan 2023)
        try:
            if isinstance(row["month"], pd.Period):
                month_name = row["month"].strftime("%b %Y")
            else:
                # Parse from string (YYYY-MM)
                parts = row["month_str"].split('-')
                if len(parts) == 2:
                    year, month = int(parts[0]), int(parts[1])
                    month_name = f"{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month-1]} {year}"
                else:
                    # Skip invalid month strings
                    continue
        except Exception:
            # Skip entries that can't be properly formatted
            continue
        
        # Add valid data points to the plot data
        plot_data.append({"month": month_name, "sort_key": row["sort_key"], "type": "New", "count": row["new"]})
        plot_data.append({"month": month_name, "sort_key": row["sort_key"], "type": "Churned", "count": -row["churned"]})
        plot_data.append({"month": month_name, "sort_key": row["sort_key"], "type": "Net", "count": row["net"]})
    
    plot_df = pd.DataFrame(plot_data)
    
    # Filter out any entries with blank or invalid month names
    plot_df = plot_df[plot_df["month"].notna() & (plot_df["month"] != "") & (plot_df["month"] != "0")]
    
    # Sort the data
    plot_df = plot_df.sort_values("sort_key")
    
    # Get sorted month names for category ordering
    month_order = plot_df["month"].unique()
    
    # Create the bar chart
    fig = px.bar(
        plot_df, 
        x="month", 
        y="count", 
        color="type",
        barmode="group",
        color_discrete_map={"New": "#4CAF50", "Churned": "#FF5252", "Net": "#2196F3"},
        title="Member Growth by Month",
        labels={"month": "Month", "count": "Members", "type": ""},
        category_orders={"month": month_order}
    )
    
    # Add a horizontal line at y=0
    fig.add_shape(
        type="line",
        x0=0,
        y0=0,
        x1=1,
        y1=0,
        line=dict(color="black", width=1, dash="dash"),
        xref="paper",
        yref="y"
    )
    
    # Adjust layout for better readability
    fig.update_layout(
        xaxis_tickangle=-45,
        margin=dict(b=70)
    )
    
    st.plotly_chart(fig, use_container_width=True)

def show_plan_distribution(subs_df):
    """Show membership plan distribution visualization"""
    if subs_df.empty:
        st.info("No subscription data available for plan distribution.")
        return
        
    # Membership plan distribution
    plan_counts = subs_df[subs_df["active"] == True].groupby("plan").size().reset_index(name="count")
    if not plan_counts.empty:
        fig = px.pie(plan_counts, values="count", names="plan", 
                    title="Active Membership by Plan Type")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No active membership data available for plan distribution.")

def show_plan_revenue(subs_df):
    """Show plan revenue visualization"""
    if subs_df.empty:
        st.info("No subscription data available for revenue analysis.")
        return
        
    # Get unique subscriptions to avoid double-counting group members
    unique_active_subs = subs_df[subs_df["active"] == True].drop_duplicates("subscription_id")
    
    # Group plans by monthly revenue
    plan_revenue = unique_active_subs.groupby("plan").agg({
        "monthly_value": "sum",
        "member_id": "nunique"
    }).reset_index()
    
    plan_revenue["monthly_revenue"] = plan_revenue["monthly_value"] / 100  # Convert to dollars
    plan_revenue.rename(columns={"member_id": "members"}, inplace=True)
    plan_revenue = plan_revenue.sort_values("monthly_revenue", ascending=False)
    
    # Create the bar chart
    fig = px.bar(
        plan_revenue, 
        x="plan", 
        y="monthly_revenue",
        title="Monthly Revenue by Plan",
        labels={"plan": "Plan", "monthly_revenue": "Monthly Revenue ($)"}
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Add a table with more detailed information
    st.subheader("Plan Revenue Details")
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

def show_education_members(subs_df, active_count):
    """Show education members visualization"""
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
    
    edu_pie_data = pd.DataFrame([
        {"type": "Education Members", "count": education_count},
        {"type": "Standard Members", "count": non_education_count}
    ])
    
    fig1 = px.pie(
        edu_pie_data, 
        values="count", 
        names="type",
        title="Education vs Standard Members",
        color_discrete_map={"Education Members": "#4CAF50", "Standard Members": "#2196F3"}
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Calculate growth of education members over time
    education_members["month"] = education_members["created_at"].dt.to_period("M")
    edu_by_month = education_members.groupby(education_members["month"]).size().reset_index(name="count")
    
    # Format month for display
    edu_by_month["month_str"] = edu_by_month["month"].astype(str)
    edu_by_month["sort_key"] = edu_by_month["month_str"].apply(lambda p: int(p.split("-")[0]) * 100 + int(p.split("-")[1]))
    edu_by_month = edu_by_month.sort_values("sort_key")
    
    # Format the month names nicely
    edu_by_month["month_display"] = edu_by_month["month_str"].apply(
        lambda m: f"{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][int(m.split('-')[1])-1]} {m.split('-')[0]}"
    )
    
    # Create a bar chart of education members by month
    fig2 = px.bar(
        edu_by_month,
        x="month_display",
        y="count",
        title="Education Member Growth by Month",
        labels={"month_display": "Month", "count": "New Education Members"}
    )
    
    fig2.update_layout(
        xaxis_tickangle=-45,
        margin=dict(b=70)
    )
    
    st.plotly_chart(fig2, use_container_width=True)
    
    # Display education members table
    st.subheader("Education Members Details")
    edu_display = education_members.drop_duplicates("member_id")[
        ["member_name", "member_email", "plan", "created_at"]
    ]
    
    st.dataframe(
        edu_display,
        column_config={
            "member_name": "Member Name",
            "member_email": "Email",
            "plan": "Membership Plan",
            "created_at": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY")
        },
        hide_index=True
    )
    
    create_download_button(edu_display, "made_education_members.csv", "Download Education Members")