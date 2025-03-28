"""
UI utility functions
"""
import streamlit as st

def create_download_button(df, filename, button_text="Download as CSV"):
    """Create a download button for a dataframe"""
    csv = df.to_csv(index=False)
    st.download_button(
        label=button_text,
        data=csv,
        file_name=filename,
        mime="text/csv",
    )