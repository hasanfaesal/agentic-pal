// Standard error response from the backend
interface ErrorResponse {
  error: string; // error code/type
  message: string; // human-readable message
  details?: any; // optional extra info
}

// Health check response from GET /health
interface HealthCheck {
  status: string; // "healthy"
  version: string; // "0.1.0"
  redis_connected: boolean;
  timestamp: string;
}

export { ErrorResponse, HealthCheck };