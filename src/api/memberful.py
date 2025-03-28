"""
Memberful API client for the Maine Ad + Design membership dashboard
"""
import os
import requests
import streamlit as st
from datetime import datetime

def get_memberful_data(query, variables=None, debug_mode=False):
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

def fetch_all_members(debug_mode=False):
    """Fetch all members with their subscriptions and orders from the Memberful API"""
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
                    orders {{
                        totalCents
                        createdAt
                        status
                        couponDiscountAmountCents
                        coupon {{
                            code
                        }}
                    }}
                }}
            }}
        }}
        """
        
        # Make the API request
        page_result = get_memberful_data(paginated_query, debug_mode=debug_mode)
        
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

def fetch_subscription_activities(start_date, end_date=None, debug_mode=False):
    """
    Fetch subscription-related activities from the Memberful API for a given time period.
    
    This includes new subscriptions, renewals, upgrades, downgrades, cancellations, 
    reactivations, and failed payments.
    
    Args:
        start_date (datetime): Start date for activities
        end_date (datetime, optional): End date for activities. Defaults to today.
        debug_mode (bool, optional): Whether to print debug messages. Defaults to False.
        
    Returns:
        list: A list of activity objects
    """
    all_activities = []
    has_next_page = True
    after_cursor = None
    
    # Convert dates to Unix timestamps
    start_timestamp = int(start_date.timestamp())
    end_timestamp = int(end_date.timestamp()) if end_date else int(datetime.now().timestamp())
    
    # Try fetching activities
    while has_next_page:
        # Build pagination parameters
        pagination = f'first: 100, after: "{after_cursor}"' if after_cursor else 'first: 100'
        
        # Build a more complete query for activities
        # We'll do date filtering in Python code instead of GraphQL
        
        # GraphQL query with only pagination
        paginated_query = f"""
        query {{
            activities({pagination}) {{
                pageInfo {{
                    hasNextPage
                    endCursor
                }}
                nodes {{
                    id
                    type
                    createdAt
                    member {{
                        id
                        email
                        fullName
                    }}
                    subscription {{
                        id
                        orders {{
                            coupon {{
                                id
                                code
                                amountOffCents
                            }}
                            totalCents
                        }}
                        plan {{
                            id
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
        
        if debug_mode:
            st.write("Executing GraphQL query:")
            st.code(paginated_query, language="graphql")
        
        # Make the API request
        page_result = get_memberful_data(paginated_query, debug_mode=debug_mode)
        
        if debug_mode and page_result:
            if "errors" in page_result:
                st.error("GraphQL errors:")
                st.json(page_result["errors"])
            elif "data" not in page_result:
                st.error("No data in response")
                st.json(page_result)
            else:
                st.success("Query successful")
        
        if not page_result or "data" not in page_result:
            if debug_mode:
                st.write("Failed to fetch activities or empty response")
            break
            
        # Extract activity data
        page_data = page_result.get("data", {}).get("activities", {})
        page_activities = page_data.get("nodes", [])
        
        if debug_mode:
            st.write(f"Received {len(page_activities)} activities in this page")
            
        # Filter activities by date since we couldn't do it in the query
        filtered_activities = []
        for activity in page_activities:
            activity_time = activity.get("createdAt")
            if activity_time:
                # Convert to int if it's a string
                if isinstance(activity_time, str) and activity_time.isdigit():
                    activity_time = int(activity_time)
                # Filter by date range
                if start_timestamp <= activity_time <= end_timestamp:
                    filtered_activities.append(activity)
        
        if debug_mode and len(filtered_activities) != len(page_activities):
            st.write(f"Filtered from {len(page_activities)} to {len(filtered_activities)} activities in date range")
            
        all_activities.extend(filtered_activities)
        
        # Update pagination info
        page_info = page_data.get("pageInfo", {})
        has_next_page = page_info.get("hasNextPage", False)
        after_cursor = page_info.get("endCursor")
        
        if debug_mode:
            st.write(f"Fetched page with {len(filtered_activities)} activities in date range. More pages: {has_next_page}")
    
    # If debug mode and we still have no activities, check schema to understand available field types
    if debug_mode:
        st.write("Checking for ActivityType enum type...")
        schema_query = """
        query {
          __type(name: "ActivityType") {
            name
            enumValues {
              name
            }
          }
        }
        """
        schema_result = get_memberful_data(schema_query, debug_mode=debug_mode)
        if schema_result and "data" in schema_result:
            enum_data = schema_result["data"].get("__type", {})
            if enum_data and "enumValues" in enum_data:
                activity_types = [v["name"] for v in enum_data["enumValues"]]
                st.write("Available activity types:", activity_types)
                
        # Show sample activities if we found any
        if all_activities:
            st.write("Sample activities:")
            st.json(all_activities[:3])
    
    return all_activities