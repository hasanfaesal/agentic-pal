// The user object returned by /auth/session
interface User {
  email: string;
  session_id: string;
}

// Response from GET /auth/session
interface SessionInfo {
  session_id: string;
  user_email: string;
  authenticated: boolean;
  created_at: string; // ISO 8601 datetime string
}

// Response from GET /auth/google/login
interface OAuthLoginResponse {
  authorization_url: string; // URL to redirect the browser to
}

// Stored in the auth store after OAuth callback
interface AuthState {
  user: User | null; // | null is called a union type
  isLoggedIn: boolean; // computed from !!user
  isLoading: boolean;
  error: string | null;
}

export { User, SessionInfo, OAuthLoginResponse, AuthState };