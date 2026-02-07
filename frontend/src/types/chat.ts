// A single message in the conversation
interface Message {
  id: string; // UUID, generated client-side
  role: "user" | "assistant"; // who sent the message
  content: string; // message text
  timestamp: string; // ISO 8601 datetime
  metadata?: MessageMetadata;
}

interface MessageMetadata {
  thread_id: string;
  actions?: ActionResult[]; // actions that were executed
  requires_confirmation?: boolean; // true if actions need approval
  confirmation_message?: string; // human-readable description of pending actions
}

// Request body for POST /chat and POST /chat/stream
interface ChatRequest {
  user_message: string;
  thread_id: string | null;
  conversation_history: ConversationEntry[];
}

// Each entry in conversation_history array
interface ConversationEntry {
  role: "user" | "assistant";
  content: string;
}

// Response from POST /chat (synchronous)
interface ChatResponse {
  response: string;
  thread_id: string;
  actions: ActionResult[];
  requires_confirmation: boolean;
  confirmation_message: string | null;
}

// A single action that was planned or executed
interface ActionResult {
  id: string;
  tool: string; // e.g. "gmail.send_email", "calendar.create_event"
  success: boolean;
  result: any; // tool-specific result object
  error: string | null;
}

// Request body for POST /chat/confirm
interface ConfirmActionRequest {
  thread_id: string;
}

// Request body for POST /chat/cancel
interface CancelActionRequest {
  thread_id: string;
}

// TODO: Understand why are you using enum below? Are there any alternatives to this approach?
// SSE event types (enum matching backend StreamEventType)
enum StreamEventType {
  CONNECTED = "CONNECTED",
  ERROR = "ERROR",
  TOKEN = "TOKEN",
  NODE_START = "NODE_START",
  NODE_END = "NODE_END",
  ACTION_START = "ACTION_START",
  ACTION_END = "ACTION_END",
  COMPLETE = "COMPLETE",
  CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED",
}

// A single SSE event from POST /chat/stream
interface StreamEvent {
  event_type: StreamEventType;
  data: Record<string, any>; // payload varies by event_type
  timestamp: string;
}

export {
  Message,
  ChatRequest,
  ChatResponse,
  ActionResult,
  ConfirmActionRequest,
  CancelActionRequest,
  StreamEventType,
  StreamEvent,
  ConversationEntry,
};