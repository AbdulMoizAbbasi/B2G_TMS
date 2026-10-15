import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import { AuthProvider } from "./auth/AuthContext";
import Login from "./pages/Login";
import TenderDetail from "./pages/TenderDetail";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AllTenders from "./pages/AllTenders";
import Overview from "./pages/Overview";
import UserManagement from "./pages/UserManagement";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<AllTenders />} />
              <Route path="overview" element={<Overview />} />
              <Route path="tenders/:tenderId" element={<TenderDetail />} />
              <Route path="admin/users" element={<ProtectedRoute adminOnly />}>
                <Route index element={<UserManagement />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
