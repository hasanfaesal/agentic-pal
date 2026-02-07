// Thread metadata (stored in localStorage)
interface Thread {
  id: string; // UUID
  title: string; // auto-generated or user-set title
  created_at: string; // ISO 8601
  last_message_at: string; // ISO 8601
  message_count: number;
}

// Notification toast
interface Notification {
  id: string; // UUID
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration: number; // auto-dismiss in ms (0 = manual dismiss)
}

export { Thread, Notification };