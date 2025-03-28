"""
Education members visualization functions
"""
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

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