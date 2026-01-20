from typing import Optional

from ..date_utils import parse_datetime


class TasksToolsMixin:
    """Tasks-related tool implementations."""

    def create_task(
        self,
        title: str,
        due: Optional[str] = None,
        notes: str = "",
        tasklist: Optional[str] = None,
    ) -> dict:
        """Create a new task."""
        try:
            parsed_due = None
            if due:
                parsed_due, _ = parse_datetime(due, self.default_timezone)
                if not parsed_due.endswith("Z"):
                    parsed_due = parsed_due.split("T")[0] + "T00:00:00.000Z"

            return self.tasks.create_task(
                title=title,
                tasklist=tasklist,
                due=parsed_due,
                notes=notes,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid due date: {e}",
                "error": str(e),
            }

    def list_tasks(
        self,
        tasklist: Optional[str] = None,
        show_completed: bool = False,
        max_results: int = 20,
    ) -> dict:
        """List tasks from a task list."""
        return self.tasks.list_tasks(
            tasklist=tasklist,
            show_completed=show_completed,
            max_results=max_results,
        )

    def mark_task_complete(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Mark a task as completed."""
        return self.tasks.mark_task_complete(task_id=task_id, tasklist=tasklist)

    def mark_task_incomplete(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Mark a task as incomplete."""
        return self.tasks.mark_task_incomplete(task_id=task_id, tasklist=tasklist)

    def delete_task(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
    ) -> dict:
        """Delete a task."""
        return self.tasks.delete_task(task_id=task_id, tasklist=tasklist)

    def update_task(
        self,
        task_id: str,
        tasklist: Optional[str] = None,
        title: Optional[str] = None,
        due: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> dict:
        """Update a task."""
        try:
            parsed_due = None
            if due:
                parsed_due, _ = parse_datetime(due, self.default_timezone)
                if not parsed_due.endswith("Z"):
                    parsed_due = parsed_due.split("T")[0] + "T00:00:00.000Z"

            return self.tasks.update_task(
                task_id=task_id,
                tasklist=tasklist,
                title=title,
                due=parsed_due,
                notes=notes,
            )

        except ValueError as e:
            return {
                "success": False,
                "message": f"Invalid due date: {e}",
                "error": str(e),
            }

    def get_task_lists(self) -> dict:
        """Get all task lists."""
        return self.tasks.get_task_lists()
