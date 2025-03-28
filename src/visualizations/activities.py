"""
Member activities visualization functions
"""
import pandas as pd
import streamlit as st

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