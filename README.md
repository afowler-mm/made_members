# Maine Ad + Design Membership Dashboard

A Streamlit app to visualize membership data for Maine Ad + Design board members.

## Features

- View active member count
- Track new memberships over time
- Monitor canceled memberships
- See memberships expiring soon
- Filter data by time period
- View detailed member information

## Setup

1. Clone this repository:
   ```
   git clone <repository-url>
   cd made_members
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Memberful API key:
   - Option 1: Set an environment variable:
     ```
     export MEMBERFUL_API_KEY=your_api_key_here
     ```
   - Option 2: Add to `.streamlit/secrets.toml`:
     ```
     MEMBERFUL_API_KEY = "your_api_key_here"
     ```

## Running the App

Start the Streamlit server:
```
streamlit run app.py
```

The app will open in your default web browser at http://localhost:8501

## Getting a Memberful API Key

1. Log in to your Memberful admin dashboard
2. Go to Settings > API
3. Generate a new API key with appropriate permissions
4. Keep this key secure and never commit it to version control

## Customization

You can customize the app by modifying `app.py`. Some ideas:
- Add additional visualizations
- Include revenue metrics
- Create email export functionality for member communications
- Add filtering by membership plan