// Application Constants
// Contains configuration values and magic strings

/**
 * Base URL for API calls
 * Reads from environment variable or falls back to localhost
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Application display name
 */
const APP_NAME = import.meta.env.VITE_APP_NAME || "Agentic Pal";

/**
 * LocalStorage keys for persisting data
 */
const STORAGE_KEYS = {
  /** Key for storing thread metadata list */
  THREADS: "threads_metadata",
  /** Prefix for storing individual thread messages */
  THREAD_PREFIX: "thread:",
  /** Key for storing UI preferences */
  UI_PREFS: "ui_preferences",
} as const;

/**
 * Default API timeout in milliseconds
 */
const DEFAULT_TIMEOUT = 30_000;

/**
 * Chat endpoint timeout in milliseconds
 * Longer timeout to accommodate LLM processing time
 */
const CHAT_TIMEOUT = 120_000;

/**
 * Maximum characters allowed in user message
 */
const MAX_MESSAGE_LENGTH = 2000;

/**
 * Default notification auto-dismiss duration in milliseconds
 */
const NOTIFICATION_DURATION = 2500;

export {
  API_BASE_URL,
  APP_NAME,
  STORAGE_KEYS,
  DEFAULT_TIMEOUT,
  CHAT_TIMEOUT,
  MAX_MESSAGE_LENGTH,
  NOTIFICATION_DURATION,
};
