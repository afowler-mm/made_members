"""
Visualization functions for the Maine Ad + Design membership dashboard
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from utils import clean_period_data, create_download_button
from datetime import datetime

def show_member_growth(subs_df):
    """Show member growth visualization using Streamlit charts"""
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
    
    # Group by month to get new subscriptions
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
    
    # Create a list of all unique months from both dataframes
    all_months = pd.concat([
        new_by_month["month"] if not new_by_month.empty else pd.Series(dtype='period[M]'),
        churned_by_month["month"] if not churned_by_month.empty else pd.Series(dtype='period[M]')
    ]).unique()
    
    # Create a dataframe with all months
    monthly_changes = pd.DataFrame({"month": all_months})
    
    # Merge in the new and churned values
    monthly_changes = pd.merge(monthly_changes, new_by_month, on="month", how="left").fillna(0)
    monthly_changes = pd.merge(monthly_changes, churned_by_month, on="month", how="left").fillna(0)
    
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
    
    # Display explanatory text
    if monthly_changes["churned"].sum() == 0:
        pass
    else:
        st.caption("Shows monthly subscription activity: new additions, cancellations, and lapses")
    
    # Use Plotly for better control over x-axis ordering
    fig = px.bar(
        monthly_changes,
        x="display_month",
        y=["new", "churned"],
        barmode="group",
        labels={
            "display_month": "Month",
            "new": "New Subscriptions",
            "churned": "Cancellations",
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
    newnames = {'new': 'New Subscriptions', 'churned': 'Cancellations'}
    fig.for_each_trace(lambda t: t.update(name = newnames[t.name]))
    
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
            
            # If this is the most recent month (first in reversed loop)
            if i == 0:
                # For the latest month, keep the current count
                month_total = running_total
            else:
                # For earlier months, reverse-calculate the total
                # by subtracting new members and adding churned members
                running_total = running_total - new_members + churned_members
                month_total = running_total
            
            # Add to our temporary data
            temp_membership_data.append({
                "Month": display_month,
                "Continuing Members": month_total - new_members,
                "New Members": new_members,
                "Cancelled Members": -churned_members if churned_members > 0 else 0,
                "Total Active": month_total
            })
    
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
        
        # Display explanation
        st.caption("Shows the total active membership each month, broken down by continuing, new, and cancelled members")
        
        # Determine columns for stacked bar chart
        stack_columns = ["Continuing Members", "New Members"]
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
    
    # Display education members table
    st.subheader("Education members details")
    edu_display = education_members.drop_duplicates("member_id")
    
    # Create a column for the Memberful profile URL
    edu_display["memberful_url"] = edu_display["member_id"].apply(
        lambda id: f"https://made.memberful.com/admin/members/{id}"
    )
    
    st.dataframe(
        edu_display[[
            "member_name", "member_email", "plan", "created_at", "memberful_url"
        ]],
        column_config={
            "member_name": "Member Name",
            "member_email": "Email",
            "plan": "Membership Plan",
            "created_at": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
            "memberful_url": st.column_config.LinkColumn("Memberful Profile")
        },
        hide_index=True
    )