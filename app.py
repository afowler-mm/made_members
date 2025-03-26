import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# App configuration
st.set_page_config(
    page_title="Maine Ad + Design Member Dashboard",
    page_icon="🎨",
    layout="wide",
)

# Authentication and API setup
def get_memberful_data(query, variables=None):
    """Make a GraphQL request to the Memberful API"""
    api_key = os.environ.get("MEMBERFUL_API_KEY") or st.secrets.get("MEMBERFUL_API_KEY")
    if not api_key:
        st.error("Memberful API Key Missing")
        st.markdown("""
        ### API Key Setup Instructions
        
        1. **Get your API key from Memberful:**
           - Log in to your Memberful admin dashboard
           - Go to Settings > API
           - Generate a new API key
        
        2. **Set up your API key in one of these ways:**
           - Create a `.streamlit/secrets.toml` file with:
             ```
             MEMBERFUL_API_KEY = "your_api_key_here"
             ```
           - Or set an environment variable before running the app:
             ```
             export MEMBERFUL_API_KEY=your_api_key_here
             streamlit run app.py
             ```
        """)
        st.stop()
        
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Memberful GraphQL endpoint URL
    url = "https://made.memberful.com/api/graphql"
    response = requests.post(
        url, 
        json={"query": query, "variables": variables or {}},
        headers=headers
    )
    
    if response.status_code != 200:
        st.error(f"Error from API: {response.status_code} - {response.text}")
        return None
    
    # Check if response is valid JSON
    try:
        json_response = response.json()
        return json_response
    except ValueError:
        st.error("Invalid JSON response from API")
        if debug_mode:
            st.code(response.text)
        return None

# Helper functions
def get_date_n_months_ago(n):
    """Get date n months ago from today"""
    today = datetime.now()
    n_months_ago = today.replace(month=today.month - n) if today.month > n else \
                  today.replace(year=today.year - 1, month=today.month + 12 - n)
    return n_months_ago.strftime("%Y-%m-%d")

# Sidebar for filters and options
st.sidebar.title("Maine Ad + Design")
st.sidebar.image("https://site-assets.memberful.com/qiyhr8wsbhqpdf9s9p4yn78mlcsy", width=200)

time_period = st.sidebar.selectbox(
    "Time period for analysis:",
    ["Past month", "Past 3 months", "Past 6 months", "Past year", "All time"]
)

# Debug mode toggle
debug_mode = st.sidebar.checkbox("Debug Mode")

# Main content
st.title("Maine Ad + Design Membership Dashboard")

# Add date information
st.caption(f"Data as of {datetime.now().strftime('%B %d, %Y')}")

# Loading indicator
with st.spinner("Loading membership data..."):
    # Define a function to fetch all members with pagination
    def fetch_all_members():
        all_members = []
        has_next_page = True
        after_cursor = None
        
        while has_next_page:
            # Build pagination parameters
            pagination = f'first: 100, after: "{after_cursor}"' if after_cursor else 'first: 100'
            
            # GraphQL query with pagination
            paginated_query = f"""
            query {{
                members({pagination}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        id
                        email
                        fullName
                        subscriptions {{
                            id
                            active
                            autorenew
                            createdAt
                            expiresAt
                            plan {{
                                name
                            }}
                        }}
                    }}
                }}
            }}
            """
            
            # Make the API request
            page_result = get_memberful_data(paginated_query)
            
            if not page_result or "data" not in page_result:
                break
                
            # Extract member data
            page_data = page_result.get("data", {}).get("members", {})
            page_members = page_data.get("nodes", [])
            all_members.extend(page_members)
            
            # Update pagination info
            page_info = page_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            after_cursor = page_info.get("endCursor")
            
            if debug_mode:
                st.write(f"Fetched page with {len(page_members)} members. More pages: {has_next_page}")
        
        return all_members
    
    # Fetch all members with pagination
    progress_text = "Fetching member data (this may take a moment)..."
    progress_bar = st.progress(0, text=progress_text)
    members_data = fetch_all_members()
    progress_bar.progress(100, text="Data fetching complete!")
    
    if debug_mode:
        st.expander("Members Data Sample").json(members_data[:5] if members_data else [])
    
    if not members_data:
        st.error("Failed to load data. Please check API key and connection.")
        st.stop()
    
    # Process data into a usable format
    st.success(f"Successfully loaded data for {len(members_data)} members.")
    
    # Create dataframes for analysis
    members_df = pd.DataFrame([
        {
            "id": member["id"],
            "email": member["email"],
            "name": member["fullName"],
        }
        for member in members_data
    ])
    
    # Create subscriptions dataframe
    subscriptions = []
    for member in members_data:
        member_id = member["id"]
        member_name = member["fullName"]
        member_email = member["email"]
        
        for sub in member.get("subscriptions", []):
            subscriptions.append({
                "subscription_id": sub["id"],
                "member_id": member_id,
                "member_name": member_name,
                "member_email": member_email,
                "active": sub.get("active", False),
                "auto_renew": sub.get("autorenew", False),
                "plan": sub.get("plan", {}).get("name", "Unknown"),
                "created_at": sub.get("createdAt"),
                "expires_at": sub.get("expiresAt")
            })
    
    subs_df = pd.DataFrame(subscriptions)
    
    if not subs_df.empty:
        # Convert Unix timestamps to datetime
        for col in ["created_at", "expires_at"]:
            if col in subs_df.columns:
                # Convert Unix timestamp (seconds) to datetime
                subs_df[col] = pd.to_datetime(subs_df[col], unit='s')

# Display membership metrics and visualizations
if 'members_df' in locals() and not members_df.empty:
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    # Get date filters based on selection
    if time_period == "Past month":
        filter_date = datetime.now() - timedelta(days=30)
    elif time_period == "Past 3 months":
        filter_date = datetime.now() - timedelta(days=90)
    elif time_period == "Past 6 months":
        filter_date = datetime.now() - timedelta(days=180)
    elif time_period == "Past year":
        filter_date = datetime.now() - timedelta(days=365)
    else:  # All time
        filter_date = datetime.min
    
    # Total active members
    active_subs = subs_df[subs_df["active"] == True] if not subs_df.empty else pd.DataFrame()
    col1.metric("Active Members", len(active_subs))
    
    # New members in selected period
    new_subs = subs_df[subs_df["created_at"] >= filter_date] if not subs_df.empty else pd.DataFrame()
    col2.metric("New Subscriptions", len(new_subs))
    
    # Calculate unique member count
    unique_members = len(subs_df["member_id"].unique()) if not subs_df.empty else 0
    col3.metric("Total Members", unique_members)
    
    # Expiring soon (in next 30 days)
    today = datetime.now()
    thirty_days = today + timedelta(days=30)
    expiring_soon = subs_df[(subs_df["active"] == True) & 
                           (subs_df["expires_at"] <= thirty_days) &
                           (subs_df["expires_at"] >= today)] if not subs_df.empty else pd.DataFrame()
    col4.metric("Expiring Soon", len(expiring_soon))
    
    # Visualizations
    st.subheader("Membership Insights")
    
    if not subs_df.empty:
        # Create tabs for different visualizations
        viz_tabs = st.tabs(["New Subscriptions", "Membership Plan Distribution", "Renewal Status"])
        
        with viz_tabs[0]:
            # New subscriptions by month
            subs_df["month"] = subs_df["created_at"].dt.to_period("M")
            monthly_signups = subs_df.groupby(subs_df["month"]).size().reset_index(name="count")
            monthly_signups["month"] = monthly_signups["month"].dt.to_timestamp()
            
            fig = px.line(monthly_signups, x="month", y="count", 
                         title="New Subscriptions by Month",
                         labels={"month": "Month", "count": "New Subscriptions"})
            st.plotly_chart(fig, use_container_width=True)
        
        with viz_tabs[1]:
            # Membership plan distribution
            plan_counts = subs_df[subs_df["active"] == True].groupby("plan").size().reset_index(name="count")
            if not plan_counts.empty:
                fig = px.pie(plan_counts, values="count", names="plan", 
                            title="Active Membership by Plan Type")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No active membership data available for plan distribution.")
        
        with viz_tabs[2]:
            # Auto-renew status for active memberships
            auto_renew_counts = subs_df[subs_df["active"] == True].groupby("auto_renew").size().reset_index(name="count")
            if not auto_renew_counts.empty:
                auto_renew_counts["status"] = auto_renew_counts["auto_renew"].map({True: "Auto-renew ON", False: "Auto-renew OFF"})
                fig = px.pie(auto_renew_counts, values="count", names="status", 
                            title="Auto-Renewal Status for Active Memberships",
                            color_discrete_sequence=["#4CAF50", "#FF5252"])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No active membership data available for renewal status.")
    
    # Member details
    st.subheader("Member Details")
    tabs = st.tabs(["All Members", "New Subscriptions", "Auto-Renew Off", "Expiring Soon"])
    
    # Helper function to create a download button for dataframes
    def create_download_button(df, filename, button_text="Download as CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label=button_text,
            data=csv,
            file_name=filename,
            mime="text/csv",
        )
    
    with tabs[0]:
        if not subs_df.empty:
            all_members = pd.merge(members_df, subs_df[["member_id", "active", "plan"]], 
                                  left_on="id", right_on="member_id", how="left")
            display_cols = ["name", "email", "plan", "active"]
            st.dataframe(all_members[display_cols])
            create_download_button(all_members[display_cols], "made_all_members.csv")
    
    with tabs[1]:
        if not new_subs.empty:
            display_cols = ["member_name", "member_email", "created_at", "plan", "active"]
            st.dataframe(new_subs[display_cols])
            create_download_button(new_subs[display_cols], "made_new_members.csv")
        else:
            st.info(f"No new subscriptions in the {time_period.lower()}.")
    
    with tabs[2]:
        auto_renew_off = subs_df[(subs_df["active"] == True) & (subs_df["auto_renew"] == False)] if not subs_df.empty else pd.DataFrame()
        if not auto_renew_off.empty:
            display_cols = ["member_name", "member_email", "expires_at", "plan"]
            st.dataframe(auto_renew_off[display_cols])
            create_download_button(auto_renew_off[display_cols], "made_auto_renew_off.csv")
        else:
            st.info("No members with auto-renew disabled.")
    
    with tabs[3]:
        if not expiring_soon.empty:
            display_cols = ["member_name", "member_email", "expires_at", "plan"]
            st.dataframe(expiring_soon[display_cols])
            create_download_button(expiring_soon[display_cols], "made_expiring_soon.csv")
        else:
            st.info("No memberships expiring in the next 30 days.")
else:
    st.warning("No member data available. Please check your API connection.")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ for Maine Ad + Design")