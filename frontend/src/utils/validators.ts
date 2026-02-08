// Input Validation Utilities
// Pure functions for validating user input

import { MAX_MESSAGE_LENGTH } from "./constants";

/**
 * Validation result type
 */
interface ValidationResult {
  valid: boolean;
  error?: string;
}

/**
 * Validate a user message
 * @param text - Message text to validate
 * @returns Validation result with error message if invalid
 */
function validateMessage(text: string): ValidationResult {
  const trimmed = text.trim();

  if (trimmed.length === 0) {
    return {
      valid: false,
      error: "Message cannot be empty",
    };
  }

  if (trimmed.length > MAX_MESSAGE_LENGTH) {
    return {
      valid: false,
      error: `Message cannot exceed ${MAX_MESSAGE_LENGTH} characters`,
    };
  }

  return {
    valid: true,
  };
}

/**
 * Check if a string is a valid UUID v4
 * @param str - String to validate
 * @returns true if valid UUID v4 format
 */
function isValidUUID(str: string): boolean {
  const uuidRegex =
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
}

/**
 * Check if a thread ID is valid
 * Alias for isValidUUID, used by router guard
 * @param id - Thread ID to validate
 * @returns true if valid thread ID
 */
function isValidThreadId(id: string): boolean {
  return isValidUUID(id);
}

export { ValidationResult, validateMessage, isValidUUID, isValidThreadId };
