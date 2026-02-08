// Authentication Endpoints
// Wrapper functions for all /auth/* endpoints

import type { OAuthLoginResponse, SessionInfo } from "../types/auth";
import type { ErrorResponse } from "../types/api";
import { apiClient } from "./client";
import axios from "axios";

/**
 * Get Google OAuth login URL
 * @returns Object containing authorization URL to redirect to
 * @throws Error with user-friendly message
 */
async function getGoogleLoginUrl(): Promise<OAuthLoginResponse> {
  try {
    const response =
      await apiClient.get<OAuthLoginResponse>("/auth/google/login");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to get login URL");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Get current session information
 * Check if user is logged in; called on app mount
 * @returns Session information including user email and auth status
 * @throws Error with user-friendly message
 */
async function getSession(): Promise<SessionInfo> {
  try {
    const response = await apiClient.get<SessionInfo>("/auth/session");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to get session");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Refresh Google OAuth credentials server-side
 * Called by interceptor when access token expires
 * @throws Error with user-friendly message
 */
async function refreshCredentials(): Promise<void> {
  try {
    await apiClient.post("/auth/refresh");
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to refresh credentials");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

/**
 * Logout current user
 * Clears session cookie and server-side session
 * @throws Error with user-friendly message
 */
async function logout(): Promise<void> {
  try {
    await apiClient.post("/auth/logout");
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      const errData = error.response.data as ErrorResponse;
      throw new Error(errData.message || "Failed to logout");
    }
    throw new Error("Network error. Please check your connection.");
  }
}

export { getGoogleLoginUrl, getSession, refreshCredentials, logout };
