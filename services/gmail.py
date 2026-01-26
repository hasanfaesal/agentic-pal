"""Google Gmail service module for reading, listing, and summarizing emails.

Based on Google Workspace API quickstart example:
https://github.com/googleworkspace/python-samples/tree/main/gmail/quickstart
"""

from datetime import datetime, timedelta
from typing import Optional
import base64
from googleapiclient.errors import HttpError


class GmailService:
    """Handles Gmail API interactions (read-only)."""

    def __init__(self, service):
        """Initialize with authenticated Gmail service."""
        self.service = service

    def _decode_message_part(self, part: dict) -> str:
        """
        Decode email body from base64-encoded MIME part.
        
        Args:
            part: MIME part dict from Gmail API
            
        Returns:
            Decoded message body
        """
        try:
            if "data" in part:
                return base64.urlsafe_b64decode(part["data"]).decode("utf-8")
        except Exception:
            pass
        return ""

    def _get_message_body(self, message: dict) -> str:
        """
        Extract plain text body from email message.
        Prioritizes plain text over HTML.
        
        Args:
            message: Gmail message dict from API
            
        Returns:
            Message body text
        """
        try:
            payload = message.get("payload", {})
            headers = payload.get("headers", [])
            
            # Get MIME type
            mime_type = payload.get("mimeType", "text/plain")
            
            # Simple message (not multipart)
            if mime_type.startswith("text/"):
                if "parts" not in payload:
                    return self._decode_message_part(payload)
            
            # Multipart message: find plain text part
            parts = payload.get("parts", [])
            plain_text_body = ""
            html_body = ""
            
            for part in parts:
                part_mime = part.get("mimeType", "")
                if part_mime == "text/plain":
                    plain_text_body = self._decode_message_part(part)
                    break  # Prefer plain text
                elif part_mime == "text/html":
                    html_body = self._decode_message_part(part)
            
            return plain_text_body or html_body
        except Exception:
            return ""

    def list_messages(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> dict:
        """
        List messages from inbox with optional filtering.
        
        Args:
            query: Gmail search query (e.g., "from:sender@example.com", "is:unread", "before:2026-01-20")
            max_results: Maximum number of messages to return
            
        Returns:
            Dict with list of messages (id, subject, sender, snippet, date)
        """
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            
            message_ids = [msg["id"] for msg in results.get("messages", [])]
            
            if not message_ids:
                return {
                    "success": True,
                    "message": "No messages found.",
                    "messages": [],
                }
            
            # Fetch full message data
            messages = []
            for msg_id in message_ids:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )
                
                headers = msg.get("payload", {}).get("headers", [])
                headers_dict = {h["name"]: h["value"] for h in headers}
                
                messages.append({
                    "id": msg_id,
                    "subject": headers_dict.get("Subject", "(No Subject)"),
                    "from": headers_dict.get("From", "Unknown"),
                    "to": headers_dict.get("To", ""),
                    "date": headers_dict.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                })
            
            return {
                "success": True,
                "message": f"Found {len(messages)} message(s).",
                "messages": messages,
            }
        
        except HttpError as error:
            return {
                "success": False,
                "message": f"Failed to list messages: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error listing messages: {e}",
                "error": str(e),
            }

    def get_message_full(self, message_id: str) -> dict:
        """
        Get full message details including body.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dict with full message details
        """
        try:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )
            
            headers = msg.get("payload", {}).get("headers", [])
            headers_dict = {h["name"]: h["value"] for h in headers}
            body = self._get_message_body(msg)
            
            return {
                "success": True,
                "message": "Message retrieved successfully.",
                "id": message_id,
                "subject": headers_dict.get("Subject", "(No Subject)"),
                "from": headers_dict.get("From", "Unknown"),
                "to": headers_dict.get("To", ""),
                "date": headers_dict.get("Date", ""),
                "snippet": msg.get("snippet", ""),
                "body": body,
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Message '{message_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to get message: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error getting message: {e}",
                "error": str(e),
            }

    def list_messages_from_sender(
        self,
        sender_email: str,
        max_results: int = 10,
    ) -> dict:
        """
        List messages from a specific sender.
        
        Args:
            sender_email: Sender's email address
            max_results: Maximum number of messages to return
            
        Returns:
            Dict with list of messages
        """
        query = f"from:{sender_email}"
        return self.list_messages(query=query, max_results=max_results)

    def list_messages_by_label(
        self,
        label_name: str,
        max_results: int = 10,
    ) -> dict:
        """
        List messages with a specific label.
        
        Args:
            label_name: Label name (e.g., "INBOX", "UNREAD", "STARRED")
            max_results: Maximum number of messages to return
            
        Returns:
            Dict with list of messages
        """
        query = f"label:{label_name}"
        return self.list_messages(query=query, max_results=max_results)

    def list_unread_messages(self, max_results: int = 10) -> dict:
        """
        List unread messages.
        
        Args:
            max_results: Maximum number of messages to return
            
        Returns:
            Dict with list of unread messages
        """
        query = "is:unread"
        return self.list_messages(query=query, max_results=max_results)

    def weekly_summary(self, days: int = 7, max_results: int = 20) -> dict:
        """
        Get a summary of messages from the past N days.
        
        Args:
            days: Number of days to look back (default: 7 for weekly)
            max_results: Maximum number of messages to include
            
        Returns:
            Dict with summary of subjects/senders and snippets
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Format dates for Gmail query (YYYY/MM/DD)
            start_str = start_date.strftime("%Y/%m/%d")
            end_str = end_date.strftime("%Y/%m/%d")
            
            query = f"after:{start_str} before:{end_str}"
            
            messages_result = self.list_messages(query=query, max_results=max_results)
            
            if not messages_result.get("success"):
                return messages_result
            
            messages = messages_result.get("messages", [])
            
            if not messages:
                return {
                    "success": True,
                    "message": f"No messages found in the past {days} days.",
                    "summary": {
                        "period": f"Past {days} days",
                        "message_count": 0,
                        "senders": [],
                        "subjects": [],
                    },
                }
            
            # Extract senders and subjects
            senders = {}
            subjects = []
            
            for msg in messages:
                sender = msg.get("from", "Unknown").split("<")[0].strip()
                senders[sender] = senders.get(sender, 0) + 1
                subjects.append(msg.get("subject", "(No Subject)"))
            
            return {
                "success": True,
                "message": f"Weekly summary from past {days} days.",
                "summary": {
                    "period": f"Past {days} days ({start_str} to {end_str})",
                    "message_count": len(messages),
                    "top_senders": sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5],
                    "sample_subjects": subjects[:10],
                    "messages": messages,
                },
            }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error generating summary: {e}",
                "error": str(e),
            }

    def search_messages(
        self,
        query: str,
        max_results: int = 10,
    ) -> dict:
        """
        Search messages using Gmail search syntax.
        
        Args:
            query: Gmail search query (e.g., "subject:project", "has:attachment")
            max_results: Maximum number of messages to return
            
        Returns:
            Dict with matching messages
        """
        return self.list_messages(query=query, max_results=max_results)
