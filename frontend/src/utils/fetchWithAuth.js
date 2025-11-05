// ✅ src/utils/fetchWithAuth.js
export async function fetchWithAuth(url, options = {}) {
  const token = localStorage.getItem("token");
  if (!token) throw new Error("No token found. Please log in again.");

  // Detect FormData uploads
  const isFormData = options.body instanceof FormData;

  const headers = {
    Authorization: `Bearer ${token}`,
    ...(isFormData ? {} : { "Content-Type": "application/json" }),
    ...options.headers,
  };

  // Default options merged with headers
  const fetchOptions = {
    ...options,
    headers,
    credentials: "include", // ✅ ensures cookies & CORS credentials are handled
  };

  let response;
  try {
    response = await fetch(url, fetchOptions);
  } catch (networkError) {
    console.error("❌ Network error:", networkError);
    throw new Error("Failed to connect to the server. Please try again.");
  }

  // Handle expired/invalid JWT
  if (response.status === 401) {
    console.warn("⚠️ Unauthorized (401): Token expired or invalid.");
    localStorage.removeItem("token");
    window.location.href = "/login"; // redirect to login
    throw new Error("Unauthorized - Session expired. Please log in again.");
  }

  // Handle CORS preflight or no content
  if (response.status === 204) {
    return {};
  }

  // Try to parse JSON safely
  let data;
  try {
    data = await response.json();
  } catch {
    try {
      data = await response.text();
    } catch {
      data = {};
    }
  }

  if (!response.ok) {
    console.error("❌ API Error:", response.status, data);
    const message =
      typeof data === "string"
        ? data
        : data?.error || data?.message || "Unknown error from server";
    throw new Error(message);
  }

  return data;
}
