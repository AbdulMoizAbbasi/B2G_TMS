import axios from "axios";

const api = axios.create({
  baseURL: "/",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || "";
    const isCredentialSubmission = /\/api\/auth\/(login|reauthenticate)$/.test(requestUrl);
    const code = error.response?.data?.detail?.code;

    if (!isCredentialSubmission && code) {
      window.dispatchEvent(new CustomEvent("auth:api-error", {
        detail: { code, status: error.response?.status },
      }));
    }
    return Promise.reject(error);
  },
);

export default api;
