// Axios Instance & Interceptors
// Single configured axios instance shared by all endpoint files

import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { API_BASE_URL, DEFAULT_TIMEOUT } from "../utils/constants";

/**
 * Create axios instance with base configuration
 */
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true, // Send HttpOnly cookies (session_id)
  timeout: DEFAULT_TIMEOUT,
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Request Interceptor
 * No-op for now. The backend uses HttpOnly cookies for auth.
 * If bearer tokens are added later, attach them here.
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Pass through unchanged
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

/**
 * Response Interceptor
 * Handles token refresh on 401 errors
 */
apiClient.interceptors.response.use(
  // Success - pass through unchanged
  (response) => response,

  // Error handling
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // If 401 error and we haven't retried yet
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Attempt to refresh credentials
        await apiClient.post("/auth/refresh");

        // Retry the original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Refresh failed - clear auth state and redirect to login
        // Note: The actual redirect will be handled by the auth store/composable
        // We just reject the promise here
        return Promise.reject(refreshError);
      }
    }

    // For all other errors, reject the promise
    return Promise.reject(error);
  },
);

export { apiClient };
