"""
API functions for the Maine Ad + Design membership dashboard
"""
import os
import requests
import streamlit as st

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