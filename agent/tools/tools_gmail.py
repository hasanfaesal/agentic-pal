class GmailToolsMixin:
    """Gmail-related tool implementations."""

    def read_emails(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> dict:
        """Read/list emails with optional query filter."""
        return self.gmail.list_messages(query=query, max_results=max_results)

    def get_email_details(self, message_id: str) -> dict:
        """Get full details of a specific email."""
        return self.gmail.get_message_full(message_id=message_id)

    def summarize_weekly_emails(
        self,
        days: int = 7,
        max_results: int = 20,
    ) -> dict:
        """Get a summary of emails from the past N days."""
        return self.gmail.weekly_summary(days=days, max_results=max_results)

    def search_emails(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict:
        """Search emails using Gmail search syntax."""
        return self.gmail.search_messages(query=query, max_results=max_results)

    def list_unread_emails(self, max_results: int = 10) -> dict:
        """List unread emails."""
        return self.gmail.list_unread_messages(max_results=max_results)
