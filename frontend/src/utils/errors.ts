// Error Parsing Utilities
// Pure functions for parsing and handling API errors

import type { ErrorResponse } from "../types/api";

/**
 * Check if an error is an Axios error with a response
 */
function isAxiosError(error: unknown): error is {
  response?: {
    data?: unknown;
    status?: number;
  };
  code?: string;
  message?: string;
} {
  return (
    typeof error === "object" &&
    error !== null &&
    ("response" in error || "code" in error || "message" in error)
  );
}

/**
 * Check if data matches ErrorResponse shape
 */
function isErrorResponse(data: unknown): data is ErrorResponse {
  return (
    typeof data === "object" &&
    data !== null &&
    "message" in data &&
    typeof (data as ErrorResponse).message === "string"
  );
}

/**
 * Parse an API error into a user-friendly message
 * @param error - Unknown error object from API call
 * @returns Human-readable error message
 */
function parseApiError(error: unknown): string {
  // Handle axios errors
  if (isAxiosError(error)) {
    // Check for structured error response
    const responseData = error.response?.data;
    if (responseData && isErrorResponse(responseData)) {
      return responseData.message;
    }

    // Check for network errors
    if (error.code === "ERR_NETWORK" || !error.response) {
      return "Network error. Check your connection.";
    }

    // Check for timeout
    if (error.code === "ECONNABORTED" || error.code === "ERR_CANCELED") {
      return "Request timed out.";
    }

    // Generic axios error message
    if (error.message) {
      return error.message;
    }
  }

  // Fallback for unknown errors
  return "An unexpected error occurred.";
}

/**
 * Check if an error is an authentication error (401/403)
 * @param error - Unknown error object from API call
 * @returns true if status code is 401 or 403
 */
function isAuthError(error: unknown): boolean {
  if (isAxiosError(error) && error.response?.status) {
    return error.response.status === 401 || error.response.status === 403;
  }
  return false;
}

/**
 * Check if an error is a network error
 * @param error - Unknown error object from API call
 * @returns true if it's a network-related error
 */
function isNetworkError(error: unknown): boolean {
  if (isAxiosError(error)) {
    return error.code === "ERR_NETWORK" || !error.response;
  }
  return false;
}

export { parseApiError, isAuthError, isNetworkError };
