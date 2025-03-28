"""
Member directory component for the dashboard
"""
import pandas as pd
import streamlit as st
from ..data.members import prepare_all_members_view

def show_member_directory(members_df, subs_df):
    """Display the member directory with filterable columns"""
    # Store member data in session state if not already there
    if "all_members_cache" not in st.session_state and not subs_df.empty:
        # Create a unique list of members with their subscription info
        all_members = prepare_all_members_view(members_df, subs_df)
        st.session_state.all_members_cache = all_members
        
        # Also cache available plans
        st.session_state.available_plans = subs_df["plan"].unique().tolist()
        
    # Simplified consolidated member directory
    if not subs_df.empty:
        # Get member subscription data with join dates
        # Get all subscriptions to show each member's join date
        if "consolidated_members_cache" not in st.session_state:
            # Create a joined date column for members by getting their earliest subscription date
            members_with_joined = subs_df.sort_values("created_at").drop_duplicates("member_id")
            members_with_joined = members_with_joined[["member_id", "member_name", "member_email", "created_at", 
                                                      "plan", "active", "is_education" if "is_education" in subs_df.columns else None]].dropna(axis=1)
            members_with_joined.rename(columns={"member_name": "name", "member_email": "email", "created_at": "joined_date"}, inplace=True)
            st.session_state.consolidated_members_cache = members_with_joined
        
        # Get the cached member data
        consolidated_members = st.session_state.get("consolidated_members_cache", pd.DataFrame())
        
        # Apply filters to the cached data (client-side filtering)
        filtered_members = consolidated_members.copy()
        
        # Create a column for the Memberful profile URL
        filtered_members["memberful_url"] = filtered_members["member_id"].apply(
            lambda id: f"https://made.memberful.com/admin/members/{id}"
        )
        
        # Set up display columns with join date
        if "is_education" in filtered_members.columns:
            display_cols = ["name", "email", "joined_date", "plan", "active", "is_education", "memberful_url"]
            column_config = {
                "name": "Member Name",
                "email": "Email",
                "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                "plan": "Membership Plan",
                "active": st.column_config.CheckboxColumn("Active"),
                "is_education": st.column_config.CheckboxColumn("Education Member"),
                "memberful_url": st.column_config.LinkColumn("Memberful Profile")
            }
        else:
            display_cols = ["name", "email", "joined_date", "plan", "active", "memberful_url"]
            column_config = {
                "name": "Member Name",
                "email": "Email", 
                "joined_date": st.column_config.DatetimeColumn("Joined", format="MMM DD, YYYY"),
                "plan": "Membership Plan",
                "active": st.column_config.CheckboxColumn("Active"),
                "memberful_url": st.column_config.LinkColumn("Memberful Profile")
            }
        
        # Display the complete member table with sorting capability
        st.dataframe(
            filtered_members[display_cols].sort_values("joined_date", ascending=False),
            column_config=column_config,
            hide_index=True,
            height=600
        )