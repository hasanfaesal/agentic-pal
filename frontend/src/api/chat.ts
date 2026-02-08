// Chat Endpoints
// Two-step streaming pattern: POST message → GET SSE stream

/**
 * An [EventSource](https://developer.mozilla.org/en-US/docs/Web/API/EventSource) or [Server-Sent-Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) instance opens a persistent connection to an HTTP server, which sends events in text/event-stream format.
 * https://vueuse.org/core/useEventSource/
 */

import type {
  ChatRequest,
  ChatResponse,
  ConfirmActionRequest,
  CancelActionRequest,
  StreamEvent,
} from "../types/chat";
import type { ErrorResponse } from "../types/api";
import type { EventSourceStatus } from "@vueuse/core";
import type { Ref, ShallowRef } from "vue";
import { apiClient } from "./client";
import { API_BASE_URL, CHAT_TIMEOUT } from "../utils/constants";
import { useEventSource } from "@vueuse/core";
import axios from "axios";

/**
 * Backend SSE event names (lowercase, matching backend StreamEventType enum values)
 */
const SSE_EVENTS = [
  "connected",
  "error",
  "token",
  "node_start",
  "node_end",
  "action_start",
  "action_end",
  "complete",
  "confirmation_required",
] as const;

type SSEEventName = (typeof SSE_EVENTS)[number];

/**
 * Response from POST /chat/message
 */
interface SendMessageResponse {
  thread_id: string;
  status: string;
}

/**
 * Stream connection wrapping VueUse's useEventSource
 */
interface StreamConnection {
  /** Reactive reference to raw event data (parse with JSON.parse to get StreamEvent) */
  data: ShallowRef<string | null>;
  /** Reactive reference to the latest event name */
  event: Ref<SSEEventName | null>;
  /** Connection status: 'CONNECTING' | 'OPEN' | 'CLOSED' */
  status: Ref<EventSourceStatus>;
  /** Connection error, if any */
  error: ShallowRef<Event | null>;
  /** Close the SSE connection */
  close: () => void;
  /** Reopen the SSE connection */
  open: () => void;
}

/**
 * Send a message and get a synchronous full response
 * @param req - Chat request with user message and thread ID
 * @returns Full chat response with actions and confirmation status
 * @throws Error with user-friendly message
 */
async function sendMessage(req: ChatRequest): Promise<ChatResponse> {
  try {
    const response = await apiClient.post<ChatResponse>("/chat", req, {
      timeout: CHAT_TIMEOUT,
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to send message");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Step 1: Store a user message on the backend via POST
 *
 * Sends the message securely in the request body.
 * Returns a thread_id to use when opening the SSE stream.
 *
 * @param userMessage - The user's message text
 * @param threadId - Optional existing thread ID for conversation continuity
 * @returns Object with thread_id and status
 * @throws Error with user-friendly message
 */
async function postMessage(
  userMessage: string,
  threadId: string | null = null,
): Promise<SendMessageResponse> {
  try {
    const response = await apiClient.post<SendMessageResponse>(
      "/chat/message",
      {
        user_message: userMessage,
        thread_id: threadId,
      },
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to send message");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Step 2: Open SSE stream with just the thread_id
 *
 * The backend retrieves the pending message from Redis and streams
 * the agent's response. No sensitive data is sent in the URL.
 *
 * @param threadId - Thread ID returned by postMessage()
 * @returns StreamConnection with reactive refs and control methods
 */
function openStream(threadId: string): StreamConnection {
  const url = `${API_BASE_URL}/chat/stream?thread_id=${encodeURIComponent(threadId)}`;

  const es = useEventSource(url, [...SSE_EVENTS], {
    withCredentials: true,
    immediate: true,
    autoReconnect: false,
  });

  return {
    data: es.data,
    event: es.event as Ref<SSEEventName | null>,
    status: es.status,
    error: es.error,
    close: es.close,
    open: es.open,
  };
}

/**
 * Convenience: Post a message and immediately open the SSE stream
 *
 * Combines Step 1 (postMessage) and Step 2 (openStream) into one call.
 *
 * @param userMessage - The user's message text
 * @param threadId - Optional existing thread ID
 * @returns Object containing the StreamConnection and the resolved thread_id
 * @throws Error with user-friendly message
 */
async function streamMessage(
  userMessage: string,
  threadId: string | null = null,
): Promise<{ stream: StreamConnection; threadId: string }> {
  // Step 1: POST the message securely
  const { thread_id } = await postMessage(userMessage, threadId);

  // Step 2: Open SSE with just the thread_id
  const stream = openStream(thread_id);

  return { stream, threadId: thread_id };
}

/**
 * Confirm and execute pending actions
 * @param req - Confirmation request with thread ID
 * @returns Chat response with execution results
 * @throws Error with user-friendly message
 */
async function confirmActions(
  req: ConfirmActionRequest,
): Promise<ChatResponse> {
  try {
    const response = await apiClient.post<ChatResponse>("/chat/confirm", req, {
      timeout: CHAT_TIMEOUT,
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to confirm actions");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Cancel pending actions
 * @param req - Cancel request with thread ID
 * @returns Confirmation message
 * @throws Error with user-friendly message
 */
async function cancelActions(
  req: CancelActionRequest,
): Promise<{ message: string }> {
  try {
    const response = await apiClient.post<{ message: string }>(
      "/chat/cancel",
      req,
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to cancel actions");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

export {
  sendMessage,
  postMessage,
  openStream,
  streamMessage,
  confirmActions,
  cancelActions,
};
export type { StreamConnection, SendMessageResponse, SSEEventName };
