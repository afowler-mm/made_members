# CLAUDE.md - Guidelines for AI Agent Usage

## Commands

- Run application: `streamlit run app.py`
- Install dependencies: `pip install -r requirements.txt`
- Run linting: `flake8 *.py`
- Type checking: Not currently used in this project

## Code Style Guidelines

- **Imports**: Group standard library imports first, followed by third-party packages, then local imports
- **Docstrings**: Use triple-quoted docstrings for modules and functions
- **Function Names**: Use snake_case for function names
- **Variable Names**: Use descriptive snake_case names
- **Error Handling**: Use try-except blocks when dealing with external APIs or data parsing
- **Type Hints**: Not currently used, but can be added when needed
- **Formatting**: Follow PEP 8 style guide
- **Comments**: Add comments for complex sections of code
- **Documentation**: Include useful information in docstrings
- **Streamlit Best Practices**: Use st.session_state for persistent data between reruns
- **Data Processing**: Use pandas for data manipulation