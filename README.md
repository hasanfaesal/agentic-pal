# AgenticPal

An AI personal assistant designed to make all your productivity and personal apps easier to manage. Currently developed for Google Workspace (Calendar, Gmail, Tasks) but architected to be platform-agnostic.

## Features

### Core Capabilities

- Performs CRUD operations over Calendar, Gmail, Tasks, and other productivity services
- Natural Language Interface: Describe requests in plain English
- Multi-turn Conversations: Context-aware interactions with clarifying questions
- Confirmation Flows: Safety prompts for destructive operations
- Intelligent Date/Time Parsing: Understands relative dates like "next Tuesday" or "in 2 hours"

### Planned Enhancements

- Persistent conversation history
- User preferences configuration
- Batch operations
- Semantic email search with embeddings
- Web UI
- Email label management
- Calendar invitation handling

## Architecture

Three-layer design for clean separation of concerns:

1. Agent Layer: High-level orchestration using LLM for intent parsing and routing
2. Tool Registry Layer: Pydantic-based validation and standardized execution
3. Services Layer: Direct Google API integration for Calendar, Gmail, and Tasks

Tool execution flows from user input through the agent, validated by the registry, wrapped by tool handlers, and executed by service classes.

## Getting Started

### Requirements

- Python 3.12 or higher
- Google Cloud Platform account
- OAuth credentials for Calendar, Gmail, and Tasks APIs

### Installation

1. Clone the repository and navigate to the project directory
2. Install dependencies: `uv sync`
3. Enable required APIs in Google Cloud Console
4. Create OAuth Client ID (Desktop application)
5. Download credentials as `credentials.json` in the project root
6. Add your email as a test user on the OAuth consent screen
7. Run: `python main.py`

First run will open a browser for OAuth authentication. The token is cached for future sessions.

## Usage Examples

Calendar: "Add a meeting with John next Tuesday at 2pm"
Email: "Summarize my emails from this week"
Tasks: "Create a task: buy groceries"
Multi-turn: Agent can ask clarifying questions to complete ambiguous requests

## Development

To add new tools:

1. Implement wrapper in appropriate `tools_*.py` file
2. Define Pydantic schema in `schemas.py`
3. Register tool in `registry.py`
4. Update system prompt documentation
5. Add tests

## Key Dependencies

- google-api-python-client: Google API access
- google-auth-oauthlib: OAuth 2.0 authentication
- langchain-qwq: LLM integration
- pydantic: Schema validation
- python-dateutil: Date parsing

## References

This project draws inspiration from the official Google Workspace Python quickstart examples. The quickstart files are not committed to this repository; please refer to the canonical sources below:

- Google Calendar Quickstart: https://developers.google.com/calendar/api/quickstart/python
- Gmail Quickstart: https://developers.google.com/gmail/api/quickstart/python
- Google Tasks Quickstart: https://developers.google.com/tasks/quickstart/python
