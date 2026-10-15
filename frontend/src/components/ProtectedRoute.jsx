import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

function ProtectedRoute({ adminOnly = false }) {
  const { user, loading } = useAuth();

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

  if (adminOnly && user.role !== "ADMIN") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
