"""
Authentication components for the dashboard
"""
import streamlit as st
import hashlib

def check_password():
    """Verify the user password or query string bypass"""
    # Define the password - you can change this to any password you want
    correct_password = "madeindashboard"
    hashed_password = hashlib.sha256(correct_password.encode()).hexdigest()
    
    # Check for query string parameter first
    if "pass" in st.query_params:
        query_password = st.query_params["pass"]
        if hashlib.sha256(query_password.encode()).hexdigest() == hashed_password:
            st.session_state["authenticated"] = True
            # Remove password from URL to prevent accidental sharing
            st.query_params.clear()
            return True
    
    # If already authenticated, don't show login again
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        return True
    
    # Show login form
    st.title("🔒 Login")
    password = st.text_input("Enter dashboard password", type="password")
    
    if st.button("Login"):
        if hashlib.sha256(password.encode()).hexdigest() == hashed_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password")
            return False
    
    # If we get here, user has not authenticated
    return False