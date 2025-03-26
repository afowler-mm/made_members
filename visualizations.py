"""
Visualization functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from utils import clean_period_data, create_download_button
from datetime import datetime

def show_member_growth(subs_df):
    """Show member growth visualization using native Streamlit charts"""
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
    
    # Format month strings for display
    month_display = []
    for _, row in growth_data.iterrows():
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
                    continue
            month_display.append(month_name)
        except Exception:
            continue
    
    # Create pivot data for bar chart    
    st.subheader("Member Growth by Month")
    
    # Prepare data for streamlit bar chart
    # Convert to negative values individually before creating the list
    churned_values = [-x for x in growth_data["churned"].tolist()[:len(month_display)]]
    
    chart_data = pd.DataFrame({
        "Month": month_display,
        "New": growth_data["new"].tolist()[:len(month_display)],
        "Churned": churned_values,
        "Net": growth_data["net"].tolist()[:len(month_display)],
    })
    
    # Set the month as the index
    chart_data = chart_data.set_index("Month")
    
    # Display the bar chart
    st.bar_chart(chart_data)
    
    # Add a small legend
    col1, col2, col3 = st.columns(3)
    col1.color_picker("New", "#FF9900", disabled=True)
    col1.write("New Members")
    col2.color_picker("Churned", "#00CCFF", disabled=True)
    col2.write("Churned Members")
    col3.color_picker("Net", "#33FF99", disabled=True)
    col3.write("Net Change")

def show_plans_and_revenue(subs_df):
    """Show combined membership plan and revenue visualizations"""
    if subs_df.empty:
        st.info("No subscription data available for plan distribution.")
        return
        
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Active Membership by Plan Type")
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
        st.subheader("Monthly Revenue by Plan")
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
    st.subheader("Education vs Standard Members")
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
    st.subheader("Education Member Growth by Month")
    
    if month_display:
        # Create bar chart data
        chart_data = pd.DataFrame({
            "Month": month_display,
            "New Education Members": edu_by_month["count"].tolist()[:len(month_display)]
        })
        
        # Set month as index
        chart_data = chart_data.set_index("Month")
        
        # Display bar chart
        st.bar_chart(chart_data)
    else:
        st.info("No monthly data available for education members.")
    
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