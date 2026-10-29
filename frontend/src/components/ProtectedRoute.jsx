import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import LockScreen from "./LockScreen";

function ProtectedRoute({ adminOnly = false }) {
  const { user, loading, locked } = useAuth();

  if (loading) {
    return (
      <div className="auth-loading">
        <span>Loading...</span>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (locked) return <LockScreen />;

  if (adminOnly && user.role !== "ADMIN") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
