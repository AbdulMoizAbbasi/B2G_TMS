import { createContext, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) {
      setLoading(false);
      return;
    }

    const loadUser = async () => {
      try {
        const response = await api.get("/api/auth/me");
        setUser(response.data);
      } catch (error) {
        console.error("Failed to restore authentication:", error);

        localStorage.removeItem("access_token");
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const login = async (username, password) => {
    const response = await api.post("/api/auth/login", {
      username,
      password,
    });

    const { access_token } = response.data;

    localStorage.setItem("access_token", access_token);

    const meResponse = await api.get("/api/auth/me");

    setUser(meResponse.data);

    navigate("/", { replace: true });
  };

  const logout = () => {
    localStorage.removeItem("access_token");
    setUser(null);
    navigate("/login", { replace: true });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}