"""Google Tasks service module for creating, listing, and managing tasks."""

from typing import Optional
from googleapiclient.errors import HttpError


class TasksService:
    """Handles Google Tasks API interactions."""

    def __init__(self, service):
        """Initialize with authenticated Google Tasks service."""
        self.service = service
        self._default_list_id = None

    def _get_default_list_id(self) -> Optional[str]:
        """
        Get the default task list ID (cached).
        
        Returns:
            Default task list ID or None if error
        """
        if self._default_list_id:
            return self._default_list_id
        
        try:
            lists = self.service.tasklists().list().execute()
            items = lists.get("items", [])
            if items:
                self._default_list_id = items[0]["id"]
                return self._default_list_id
        except Exception:
            pass
        return None

    def get_task_lists(self) -> dict:
        """
        List all task lists.
        
        Returns:
            Dict with list of task lists (id, title)
        """
        try:
            lists_result = self.service.tasklists().list().execute()
            lists = lists_result.get("items", [])
            
            if not lists:
                return {
                    "success": True,
                    "message": "No task lists found.",
                    "lists": [],
                }
            
            formatted_lists = []
            for lst in lists:
                formatted_lists.append({
                    "id": lst["id"],
                    "title": lst.get("title", "Untitled List"),
                    "updated": lst.get("updated", ""),
                })
            
            return {
                "success": True,
                "message": f"Found {len(formatted_lists)} task list(s).",
                "lists": formatted_lists,
            }
        
        except HttpError as error:
            return {
                "success": False,
                "message": f"Failed to list task lists: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error listing task lists: {e}",
                "error": str(e),
            }

    def list_tasks(
        self,
        tasklist: Optional[str] = None,
        show_completed: bool = False,
        max_results: int = 20,
    ) -> dict:
        """
        List tasks from a specific task list.
        
        Args:
            tasklist: Task list ID (defaults to primary list)
            show_completed: Include completed tasks (default: False)
            max_results: Maximum number of tasks to return
            
        Returns:
            Dict with list of tasks
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            # By default, show only incomplete tasks
            show_hidden = "true" if show_completed else "false"
            
            tasks_result = (
                self.service.tasks()
                .list(tasklist=tasklist, maxResults=max_results, showHidden=show_hidden)
                .execute()
            )
            
            tasks = tasks_result.get("items", [])
            
            if not tasks:
                return {
                    "success": True,
                    "message": "No tasks found.",
                    "tasks": [],
                }
            
            formatted_tasks = []
            for task in tasks:
                formatted_tasks.append({
                    "id": task["id"],
                    "title": task.get("title", "Untitled Task"),
                    "status": task.get("status", "needsAction"),  # needsAction or completed
                    "due": task.get("due", ""),
                    "notes": task.get("notes", ""),
                    "updated": task.get("updated", ""),
                })
            
            return {
                "success": True,
                "message": f"Found {len(formatted_tasks)} task(s).",
                "tasks": formatted_tasks,
                "list_id": tasklist,
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task list '{tasklist}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to list tasks: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error listing tasks: {e}",
                "error": str(e),
            }

    def create_task(
        self,
        title: str,
        tasklist: Optional[str] = None,
        due: Optional[str] = None,
        notes: str = "",
    ) -> dict:
        """
        Create a new task.
        
        Args:
            title: Task title
            tasklist: Task list ID (defaults to primary list)
            due: Due date in RFC 3339 format (e.g., "2026-02-15T00:00:00Z")
            notes: Task notes/description
            
        Returns:
            Dict with created task details
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            task_body = {
                "title": title,
                "status": "needsAction",
            }
            
            if due:
                task_body["due"] = due
            if notes:
                task_body["notes"] = notes
            
            created_task = (
                self.service.tasks()
                .insert(tasklist=tasklist, body=task_body)
                .execute()
            )
            
            return {
                "success": True,
                "task_id": created_task["id"],
                "message": f"Task '{title}' created successfully.",
                "task": {
                    "id": created_task["id"],
                    "title": created_task.get("title", ""),
                    "status": created_task.get("status", "needsAction"),
                    "due": created_task.get("due", ""),
                    "notes": created_task.get("notes", ""),
                },
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task list '{tasklist}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to create task: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error creating task: {e}",
                "error": str(e),
            }

    def mark_task_complete(self, task_id: str, tasklist: Optional[str] = None) -> dict:
        """
        Mark a task as completed.
        
        Args:
            task_id: Task ID
            tasklist: Task list ID (defaults to primary list)
            
        Returns:
            Dict with confirmation message
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            # Fetch the task first
            task = (
                self.service.tasks()
                .get(tasklist=tasklist, task=task_id)
                .execute()
            )
            
            # Update status to completed
            task["status"] = "completed"
            
            updated_task = (
                self.service.tasks()
                .update(tasklist=tasklist, task=task_id, body=task)
                .execute()
            )
            
            return {
                "success": True,
                "message": f"Task '{updated_task.get('title', task_id)}' marked as completed.",
                "task": {
                    "id": updated_task["id"],
                    "title": updated_task.get("title", ""),
                    "status": updated_task.get("status", ""),
                },
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task '{task_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to mark task complete: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error marking task complete: {e}",
                "error": str(e),
            }

    def mark_task_incomplete(self, task_id: str, tasklist: Optional[str] = None) -> dict:
        """
        Mark a task as incomplete.
        
        Args:
            task_id: Task ID
            tasklist: Task list ID (defaults to primary list)
            
        Returns:
            Dict with confirmation message
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            # Fetch the task first
            task = (
                self.service.tasks()
                .get(tasklist=tasklist, task=task_id)
                .execute()
            )
            
            # Update status to incomplete
            task["status"] = "needsAction"
            
            updated_task = (
                self.service.tasks()
                .update(tasklist=tasklist, task=task_id, body=task)
                .execute()
            )
            
            return {
                "success": True,
                "message": f"Task '{updated_task.get('title', task_id)}' marked as incomplete.",
                "task": {
                    "id": updated_task["id"],
                    "title": updated_task.get("title", ""),
                    "status": updated_task.get("status", ""),
                },
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task '{task_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to mark task incomplete: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error marking task incomplete: {e}",
                "error": str(e),
            }

    def delete_task(self, task_id: str, tasklist: Optional[str] = None) -> dict:
        """
        Delete a task.
        
        Args:
            task_id: Task ID
            tasklist: Task list ID (defaults to primary list)
            
        Returns:
            Dict with confirmation message
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            self.service.tasks().delete(tasklist=tasklist, task=task_id).execute()
            
            return {
                "success": True,
                "message": f"Task '{task_id}' deleted successfully.",
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task '{task_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to delete task: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error deleting task: {e}",
                "error": str(e),
            }

    def update_task(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
        title: Optional[str] = None,
        due: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """
        Update task details.
        
        Args:
            task_id: Task ID
            tasklist: Task list ID (defaults to primary list)
            title: New task title (optional)
            due: New due date (optional)
            notes: New notes (optional)
            
        Returns:
            Dict with updated task details
        """
        try:
            if not tasklist:
                tasklist = self._get_default_list_id()
                if not tasklist:
                    return {
                        "success": False,
                        "message": "No default task list found.",
                        "error": "Unable to determine default task list",
                    }
            
            # Fetch the task first
            task = (
                self.service.tasks()
                .get(tasklist=tasklist, task=task_id)
                .execute()
            )
            
            # Update only provided fields
            if title:
                task["title"] = title
            if due:
                task["due"] = due
            if notes is not None:
                task["notes"] = notes
            
            updated_task = (
                self.service.tasks()
                .update(tasklist=tasklist, task=task_id, body=task)
                .execute()
            )
            
            return {
                "success": True,
                "message": f"Task '{task_id}' updated successfully.",
                "task": {
                    "id": updated_task["id"],
                    "title": updated_task.get("title", ""),
                    "status": updated_task.get("status", ""),
                    "due": updated_task.get("due", ""),
                    "notes": updated_task.get("notes", ""),
                },
            }
        
        except HttpError as error:
            if error.resp.status == 404:
                return {
                    "success": False,
                    "message": f"Task '{task_id}' not found.",
                    "error": str(error),
                }
            return {
                "success": False,
                "message": f"Failed to update task: {error}",
                "error": str(error),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error updating task: {e}",
                "error": str(e),
            }
