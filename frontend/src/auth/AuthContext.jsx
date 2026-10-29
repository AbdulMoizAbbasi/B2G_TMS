import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const AuthContext = createContext(null);
const IDLE_TIMEOUT_MS = 300_000;
const LAST_ACTIVITY_KEY = "auth_last_activity";
const LOCKED_KEY = "auth_locked_at";
const ACTIVITY_THROTTLE_MS = 15_000;
const LOCAL_ACTIVITY_THROTTLE_MS = 1_000;

export function AuthProvider({ children }) {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem("access_token")));
  const [locked, setLocked] = useState(() => Boolean(localStorage.getItem(LOCKED_KEY)));
  const [lastActivity, setLastActivity] = useState(() => Number(localStorage.getItem(LAST_ACTIVITY_KEY)) || Date.now());
  const authOperationRef = useRef(0);
  const lastWriteRef = useRef(0);
  const lastActivityRequestRef = useRef(0);
  const activityTimerRef = useRef(null);

  const lock = useCallback(() => {
    if (!localStorage.getItem(LOCKED_KEY)) localStorage.setItem(LOCKED_KEY, String(Date.now()));
    setLocked(true);
  }, []);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return;
    const operation = authOperationRef.current;
    const loadUser = async () => {
      try {
        const response = await api.get("/api/auth/me");
        if (operation !== authOperationRef.current || localStorage.getItem("access_token") !== token) return;
        setUser(response.data);
        const last = Number(localStorage.getItem(LAST_ACTIVITY_KEY));
        if (!last) {
          const now = Date.now();
          localStorage.setItem(LAST_ACTIVITY_KEY, String(now));
          setLastActivity(now);
        } else setLastActivity(last);
        if (localStorage.getItem(LOCKED_KEY) || Date.now() - last >= IDLE_TIMEOUT_MS) lock();
      } catch (error) {
        if (operation !== authOperationRef.current || localStorage.getItem("access_token") !== token) return;
        if (error.response?.data?.detail?.code === "session_idle_expired") {
          setUser({});
          lock();
        } else {
          localStorage.removeItem("access_token");
          localStorage.removeItem(LOCKED_KEY);
          localStorage.removeItem(LAST_ACTIVITY_KEY);
          setUser(null);
        }
      } finally {
        if (operation === authOperationRef.current) setLoading(false);
      }
    };
    loadUser();
  }, [lock]);

  const login = async (username, password) => {
    const operation = ++authOperationRef.current;
    try {
      const response = await api.post("/api/auth/login", { username, password });
      if (operation !== authOperationRef.current) return;
      const { access_token } = response.data;
      localStorage.setItem("access_token", access_token);
      const meResponse = await api.get("/api/auth/me");
      if (operation !== authOperationRef.current || localStorage.getItem("access_token") !== access_token) return;
      const now = Date.now();
      localStorage.removeItem(LOCKED_KEY);
      localStorage.setItem(LAST_ACTIVITY_KEY, String(now));
      setLastActivity(now);
      lastWriteRef.current = 0;
      lastActivityRequestRef.current = 0;
      setLocked(false);
      setUser(meResponse.data);
      setLoading(false);
      navigate("/", { replace: true });
    } catch (error) {
      if (operation === authOperationRef.current) setLoading(false);
      throw error;
    }
  };

  const reauthenticate = async (password) => {
    const operation = authOperationRef.current;
    const response = await api.post("/api/auth/reauthenticate", { password });
    if (operation !== authOperationRef.current || !localStorage.getItem("access_token")) return;
    const { access_token } = response.data;
    localStorage.setItem("access_token", access_token);
    setUser(response.data.user);
    const now = Date.now();
    localStorage.removeItem(LOCKED_KEY);
    localStorage.setItem(LAST_ACTIVITY_KEY, String(now));
    setLastActivity(now);
    lastWriteRef.current = 0;
    lastActivityRequestRef.current = now;
    setLocked(false);
  };

  const logout = () => {
    authOperationRef.current += 1;
    const token = localStorage.getItem("access_token");
    if (token) {
      api.post("/api/auth/logout", {}, { headers: { Authorization: `Bearer ${token}` } }).catch(() => {});
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem(LOCKED_KEY);
    localStorage.removeItem(LAST_ACTIVITY_KEY);
    setLocked(false);
    setUser(null);
    navigate("/login", { replace: true });
  };

  useEffect(() => {
    if (!user || locked) return undefined;
    const checkIdle = () => {
      const sharedLast = Number(localStorage.getItem(LAST_ACTIVITY_KEY));
      if (sharedLast && Date.now() - sharedLast >= IDLE_TIMEOUT_MS) lock();
    };
    const events = ["pointermove", "pointerdown", "click", "keydown", "touchstart", "touchmove", "wheel", "scroll"];
    const recordActivity = () => {
      if (document.visibilityState === "hidden" || localStorage.getItem(LOCKED_KEY)) return;
      const now = Date.now();
      if (now - lastWriteRef.current >= LOCAL_ACTIVITY_THROTTLE_MS) {
        lastWriteRef.current = now;
        localStorage.setItem(LAST_ACTIVITY_KEY, String(now));
        setLastActivity(now);
      }

      const sendActivity = () => {
        activityTimerRef.current = null;
        if (document.visibilityState === "hidden" || localStorage.getItem(LOCKED_KEY)) return;
        lastActivityRequestRef.current = Date.now();
        api.post("/api/auth/activity", {}).catch(() => {});
      };
      const elapsed = now - lastActivityRequestRef.current;
      if (elapsed >= ACTIVITY_THROTTLE_MS) {
        if (activityTimerRef.current) window.clearTimeout(activityTimerRef.current);
        sendActivity();
      } else if (!activityTimerRef.current) {
        activityTimerRef.current = window.setTimeout(sendActivity, ACTIVITY_THROTTLE_MS - elapsed);
      }
    };
    events.forEach((event) => window.addEventListener(event, recordActivity, { passive: true }));
    document.addEventListener("visibilitychange", checkIdle);
    return () => {
      if (activityTimerRef.current) window.clearTimeout(activityTimerRef.current);
      activityTimerRef.current = null;
      events.forEach((event) => window.removeEventListener(event, recordActivity));
      document.removeEventListener("visibilitychange", checkIdle);
    };
  }, [user, locked, lock]);

  useEffect(() => {
    if (!user || locked) return undefined;
    const delay = Math.max(0, lastActivity + IDLE_TIMEOUT_MS - Date.now());
    const timer = window.setTimeout(() => {
      const sharedLast = Number(localStorage.getItem(LAST_ACTIVITY_KEY)) || lastActivity;
      if (Date.now() - sharedLast >= IDLE_TIMEOUT_MS) lock();
      else setLastActivity(sharedLast);
    }, delay);
    return () => window.clearTimeout(timer);
  }, [user, locked, lastActivity, lock]);

  useEffect(() => {
    const onStorage = (event) => {
      if (event.key === LOCKED_KEY) setLocked(Boolean(event.newValue));
      if (event.key === LAST_ACTIVITY_KEY && event.newValue) setLastActivity(Number(event.newValue));
      if (event.key === "access_token" && !event.newValue) {
        authOperationRef.current += 1;
        setUser(null);
        setLocked(false);
        setLoading(false);
        navigate("/login", { replace: true });
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, [navigate]);

  useEffect(() => {
    const onApiAuthError = (event) => {
      if (!localStorage.getItem("access_token")) return;
      if (event.detail?.code === "session_idle_expired") {
        lock();
        return;
      }
      if (["token_expired", "invalid_token", "session_required", "session_invalid", "session_revoked", "user_not_found", "user_inactive"].includes(event.detail?.code)) {
        authOperationRef.current += 1;
        localStorage.removeItem("access_token");
        localStorage.removeItem(LOCKED_KEY);
        localStorage.removeItem(LAST_ACTIVITY_KEY);
        setLocked(false);
        setUser(null);
        setLoading(false);
        navigate("/login", { replace: true });
      }
    };
    window.addEventListener("auth:api-error", onApiAuthError);
    return () => window.removeEventListener("auth:api-error", onApiAuthError);
  }, [lock, navigate]);

  return <AuthContext.Provider value={{ user, loading, locked, login, logout, reauthenticate }}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() { return useContext(AuthContext); }
