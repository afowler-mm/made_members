"""
Data utility functions
"""
import pandas as pd

def clean_period_data(period_df, period_column="month", sort_key_column="sort_key"):
    """Clean and format period data (like months) for visualizations"""
    # Convert Period to string 
    period_df[f"{period_column}_str"] = period_df[period_column].astype(str)
    
    # Extract year and month for proper sorting
    def extract_ym(period_str):
        # Period strings are in format 'YYYY-MM'
        if pd.isna(period_str) or not isinstance(period_str, str):
            return None
        parts = period_str.split('-')
        if len(parts) == 2:
            try:
                return int(parts[0]) * 100 + int(parts[1])
            except (ValueError, IndexError):
                return None
        return None
        
    period_df[sort_key_column] = period_df[f"{period_column}_str"].apply(extract_ym)
    
    # Filter out rows with invalid sort keys
    period_df = period_df[period_df[sort_key_column].notna()]
    
    # Sort the data
    period_df = period_df.sort_values(sort_key_column)
    
    return period_df