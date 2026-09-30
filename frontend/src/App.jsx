import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import { AuthProvider } from "./auth/AuthContext";
import Login from "./pages/Login";
import TenderDetail from "./pages/TenderDetail";
import Layout from "./components/Layout";
import ProtectedRoute from "./components/ProtectedRoute";
import AllTenders from "./pages/AllTenders";
import ParticipatedTenders from "./pages/ParticipatedTenders";
import EvaluationReports from "./pages/EvaluationReports";
import EvaluationDetail from "./pages/EvaluationDetail";
import ProjectUpdates from "./pages/ProjectUpdates";
import ProjectDetail from "./pages/ProjectDetail";

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Layout />}>
              <Route index element={<AllTenders />} />
              <Route path="tenders/:tenderId" element={<TenderDetail />} />
              <Route
                path="participated"
                element={<ParticipatedTenders />}
              />
              <Route
                path="evaluations"
                element={<EvaluationReports />}
              />
              <Route
                path="evaluations/:tenderNo"
                element={<EvaluationDetail />}
              />
              <Route
                path="project-updates"
                element={<ProjectUpdates />}
              />
              <Route
                path="project-updates/:projectId"
                element={<ProjectDetail />}
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;