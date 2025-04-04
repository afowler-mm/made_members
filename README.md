# Maine Ad + Design Membership Dashboard

A Streamlit app to visualize membership data for Maine Ad + Design members.

## Project Structure

The project has been refactored into a modular structure:

```
.
├── app.py                # Main entry point for the application
├── CLAUDE.md             # Instructions for AI assistant
├── README.md             # This file
├── requirements.txt      # Dependencies
└── src/                  # Source code modules
    ├── api/              # API client code
    │   ├── __init__.py
    │   └── memberful.py  # Memberful API client
    ├── data/             # Data processing modules
    │   ├── __init__.py
    │   ├── activities.py # Activity data processing
    │   └── members.py    # Member data processing
    ├── ui/               # UI components
    │   ├── __init__.py
    │   ├── auth.py       # Authentication components
    │   ├── metrics.py    # Metrics display components
    │   └── member_directory.py # Member directory components
    ├── utils/            # Utility functions
    │   ├── __init__.py
    │   ├── date_utils.py # Date utilities
    │   ├── data_utils.py # Data utilities
    │   ├── member_utils.py # Member-specific utilities
    │   └── ui_utils.py   # UI utility functions
    └── visualizations/   # Visualization components
        ├── __init__.py
        ├── activities.py # Member activities visualization
        ├── education.py  # Education member visualization
        ├── member_growth.py # Member growth visualization
        └── revenue.py    # Revenue visualization components
```

## Features

- View active member count
- Track new memberships over time
- Monitor canceled memberships
- Visualize member activity timeline
- See revenue metrics and trends
- Track education memberships
- View detailed member information
- Filter data by time period

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

## Development

To run linting:

```bash
flake8 *.py src/**/*.py
```

## Customization

You can customize the app by modifying the appropriate module. Some ideas:
- Add additional visualizations in the `src/visualizations` directory
- Enhance the member directory with more filtering options
- Create email export functionality for member communications
- Add filtering by specific membership plans