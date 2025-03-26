import streamlit as st
import requests
import time
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# App configuration
st.set_page_config(
    page_title="Maine Ad + Design membership dashboard",
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
st.sidebar.title("Maine Ad + Design membership dashboard")
# st.sidebar.image("https://site-assets.memberful.com/qiyhr8wsbhqpdf9s9p4yn78mlcsy", width=200)

# Debug mode toggle
debug_mode = st.sidebar.checkbox("Debug Mode")

# Add additional sidebar content
st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ for Maine Ad + Design")

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
                    totalSpendCents
                    subscriptions {{
                        id
                        active
                        autorenew
                        createdAt
                        expiresAt
                        plan {{
                            name
                            priceCents
                            intervalUnit
                            intervalCount
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
        # Clear all dependent caches too
        for key in list(st.session_state.keys()):
            if key.endswith("_cache"):
                del st.session_state[key]
        refresh_data = True
        st.toast("Data cache cleared. Refreshing...", icon="🔄")

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
        
        members_data = fetch_all_members()
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
        
        # Create dataframes for analysis
        members_df = pd.DataFrame([
            {
                "id": member["id"],
                "email": member["email"],
                "name": member["fullName"],
                "total_spend_cents": member.get("totalSpendCents", 0)
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
                    "price_cents": sub.get("plan", {}).get("priceCents", 0),
                    "interval_unit": sub.get("plan", {}).get("intervalUnit", ""),
                    "interval_count": sub.get("plan", {}).get("intervalCount", 1),
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
    col1, col2, col3, col4 = st.columns(4)
    
    # Add value calculations for MRR
    if not subs_df.empty:
        # Add monthly value column
        subs_df["monthly_value"] = subs_df.apply(
            lambda x: x["price_cents"] / 
                     (1 if x["interval_unit"] == "month" else
                      0.25 if x["interval_unit"] == "week" else
                      12 if x["interval_unit"] == "year" else 0) / 
                     (x["interval_count"] or 1),
            axis=1
        )
    
    # Set standard time periods for analysis
    today = datetime.now()
    past_30_days = today - timedelta(days=30)
    past_90_days = today - timedelta(days=90)
    past_year = today - timedelta(days=365)
    
    # Total active members
    active_subs = subs_df[subs_df["active"] == True] if not subs_df.empty else pd.DataFrame()
    active_count = len(active_subs)
    
    # Active members last year (for comparison)
    one_year_ago = today - timedelta(days=365)
    active_last_year = len(subs_df[(subs_df["active"] == True) & 
                                 (subs_df["created_at"] <= one_year_ago)]) if not subs_df.empty else 0
    
    # Calculate yearly growth percentage
    yearly_growth = active_count - active_last_year
    col1.metric("Active Members", active_count, f"{yearly_growth:+d} from last year")
    
    # Calculate MRR and paying members
    if not subs_df.empty:
        # For MRR calculation, we need to deduplicate subscriptions to handle group memberships
        # Get the unique subscription IDs to avoid double-counting members of the same group
        unique_subs = subs_df[subs_df["active"] == True].drop_duplicates("subscription_id")
        current_mrr = unique_subs["monthly_value"].sum() / 100  # Convert cents to dollars
        
        # Count paying members (unique subscription IDs to avoid counting group members)
        paying_members_count = len(unique_subs)
        
        # Calculate MRR from last month (30 days ago)
        thirty_days_ago = today - timedelta(days=30)
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
            "Monthly Recurring Revenue", 
            f"${current_mrr:,.2f}", 
            f"{mrr_change_percent:+.1f}% from last month"
        )
        
        # Display paying members count (vs total members)
        col3.metric(
            "Paying Members", 
            paying_members_count,
            f"of {active_count} total members"
        )
    else:
        col2.metric("Monthly Recurring Revenue", "$0.00")
        col3.metric("Paying Members", 0)
    
    # New members in last 30 days
    new_subs_30d = subs_df[subs_df["created_at"] >= past_30_days] if not subs_df.empty else pd.DataFrame()
    # Deduplicate subscriptions for consistent counting
    unique_new_subs = new_subs_30d.drop_duplicates("subscription_id") if not new_subs_30d.empty else pd.DataFrame()
    new_count_30d = len(unique_new_subs)
    
    # New members in the 30 days before that (for comparison)
    prev_30_days = past_30_days - timedelta(days=30)
    prev_period_subs = subs_df[(subs_df["created_at"] >= prev_30_days) & 
                             (subs_df["created_at"] < past_30_days)]
    new_prev_30d = len(prev_period_subs.drop_duplicates("subscription_id")) if not prev_period_subs.empty else 0
    
    # Calculate monthly growth delta
    monthly_growth = new_count_30d - new_prev_30d
    col4.metric("New Subscriptions (30d)", new_count_30d, f"{monthly_growth:+d} vs previous 30d")
    
    # Skip expiring subscriptions section as requested

    # Visualizations
    st.divider()
    st.subheader("Visualizations")
    
    if not subs_df.empty:
        # Create tabs for different visualizations
        viz_tabs = st.tabs(["Member Growth", "Membership Plan Distribution", "Revenue by Plan"])
        
        with viz_tabs[0]:
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
            
            # Convert Period to string and create proper sort keys
            growth_data["month_str"] = growth_data["month"].astype(str)
            
            # Extract year and month for proper sorting
            # Use a safer approach that doesn't rely on date parsing
            def extract_ym(period_str):
                # Period strings are in format 'YYYY-MM'
                if pd.isna(period_str) or not isinstance(period_str, str):
                    return None  # Mark invalid values as None so we can filter them out
                parts = period_str.split('-')
                if len(parts) == 2:
                    try:
                        return int(parts[0]) * 100 + int(parts[1])  # YYYYMM as integer
                    except (ValueError, IndexError):
                        return None
                return None
                
            growth_data["sort_key"] = growth_data["month_str"].apply(extract_ym)
            
            # Filter out rows with invalid sort keys (None values)
            growth_data = growth_data[growth_data["sort_key"].notna()]
            
            # Now sort the valid data
            growth_data = growth_data.sort_values("sort_key")
            
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
            # Revenue by plan
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
                plan_revenue = plan_revenue.sort_values("monthly_revenue", ascending=False)
                
                # Create the bar chart
                fig = px.bar(
                    plan_revenue, 
                    x="plan", 
                    y="monthly_revenue",
                    title="Monthly Revenue by Plan",
                    labels={"plan": "Plan", "monthly_revenue": "Monthly Revenue ($)"}
                )
                
                # Format the labels properly
                # fig.update_traces(
                #     texttemplate='${:.2f}', 
                #     textposition='outside',
                #     textfont_size=12,
                #     text=plan_revenue["monthly_revenue"]
                # )
                
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
        
        # Renewal Status tab removed as requested
    
    # Member details
    st.divider()
    st.subheader("Member details")
    tabs = st.tabs(["All Members", "New Subscriptions (30d)", "New Subscriptions (90d)"])
    
    # Helper function to create a download button for dataframes
    def create_download_button(df, filename, button_text="Download as CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label=button_text,
            data=csv,
            file_name=filename,
            mime="text/csv",
        )
    
    # Store member data in session state if not already there
    if "all_members_cache" not in st.session_state and not subs_df.empty:
        # Create a unique list of members with their subscription info
        # Get latest subscription for each member to show current status
        member_subs = subs_df.sort_values("created_at", ascending=False).drop_duplicates("member_id")
        all_members = pd.merge(members_df, member_subs[["member_id", "active", "plan", "subscription_id"]], 
                              left_on="id", right_on="member_id", how="left")
        st.session_state.all_members_cache = all_members
        
        # Also cache available plans
        st.session_state.available_plans = subs_df["plan"].unique().tolist()
        
        # Initialize filter states
        if "show_active_only" not in st.session_state:
            st.session_state.show_active_only = False
        if "selected_plans" not in st.session_state:
            st.session_state.selected_plans = []
    
    # Function to handle filter changes without page reload
    def update_active_filter():
        # Toggle will be handled by Streamlit automatically
        pass
        
    def update_plan_filter():
        # Selected plans will be updated by Streamlit automatically
        pass
        
    with tabs[0]:
        if not subs_df.empty:
            # Add filters using session state to avoid reloads
            st.write("Filter members:")
            col1, col2 = st.columns(2)
            
            # Active members filter with on_change callback
            show_active_only = col1.checkbox(
                "Show active members only", 
                value=st.session_state.get("show_active_only", False),
                key="show_active_only",
                on_change=update_active_filter
            )
            
            # Plan filter with on_change callback
            available_plans = st.session_state.get("available_plans", [])
            selected_plans = col2.multiselect(
                "Filter by plan", 
                options=available_plans,
                default=st.session_state.get("selected_plans", []),
                key="selected_plans",
                on_change=update_plan_filter
            )
            
            # Get the cached member data
            all_members = st.session_state.get("all_members_cache", pd.DataFrame())
            
            # Apply filters to the cached data (client-side filtering)
            filtered_members = all_members
            if show_active_only:
                filtered_members = filtered_members[filtered_members["active"] == True]
            
            if selected_plans:
                filtered_members = filtered_members[filtered_members["plan"].isin(selected_plans)]
            
            # Display the filtered table
            display_cols = ["name", "email", "plan", "active"]
            st.dataframe(
                filtered_members[display_cols],
                column_config={
                    "name": "Member Name",
                    "email": "Email",
                    "plan": "Membership Plan",
                    "active": st.column_config.CheckboxColumn("Active")
                },
                hide_index=True
            )
            create_download_button(filtered_members[display_cols], "made_members.csv")
    
    with tabs[1]:
        # Cache new subscriptions data for 30 days
        if "new_subs_30d_cache" not in st.session_state and not subs_df.empty:
            # Get unique new subscriptions for 30 days
            new_subs_30d = subs_df[subs_df["created_at"] >= past_30_days]
            unique_new_30d = new_subs_30d.drop_duplicates("subscription_id") if not new_subs_30d.empty else pd.DataFrame()
            st.session_state.new_subs_30d_cache = unique_new_30d
        
        # Display cached data
        unique_new_30d = st.session_state.get("new_subs_30d_cache", pd.DataFrame())
        if not unique_new_30d.empty:
            display_cols = ["member_name", "member_email", "created_at", "plan", "active"]
            st.dataframe(
                unique_new_30d[display_cols],
                column_config={
                    "member_name": "Member Name",
                    "member_email": "Email",
                    "created_at": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                    "plan": "Membership Plan",
                    "active": st.column_config.CheckboxColumn("Active")
                },
                hide_index=True
            )
            create_download_button(unique_new_30d[display_cols], "made_new_members_30d.csv")
        else:
            st.info("No new subscriptions in the past 30 days.")
            
    with tabs[2]:
        # Cache new subscriptions data for 90 days
        if "new_subs_90d_cache" not in st.session_state and not subs_df.empty:
            # Get unique new subscriptions for 90 days
            new_subs_90d = subs_df[subs_df["created_at"] >= past_90_days]
            unique_new_90d = new_subs_90d.drop_duplicates("subscription_id") if not new_subs_90d.empty else pd.DataFrame()
            st.session_state.new_subs_90d_cache = unique_new_90d
        
        # Display cached data
        unique_new_90d = st.session_state.get("new_subs_90d_cache", pd.DataFrame())
        if not unique_new_90d.empty:
            display_cols = ["member_name", "member_email", "created_at", "plan", "active"]
            st.dataframe(
                unique_new_90d[display_cols],
                column_config={
                    "member_name": "Member Name",
                    "member_email": "Email",
                    "created_at": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                    "plan": "Membership Plan",
                    "active": st.column_config.CheckboxColumn("Active")
                },
                hide_index=True
            )
            create_download_button(unique_new_90d[display_cols], "made_new_members_90d.csv")
        else:
            st.info("No new subscriptions in the past 90 days.")
else:
    st.warning("No member data available. Please check your API connection.")

# Footer
st.markdown("---")
st.markdown("Made with ❤️ for Maine Ad + Design")