import { BrowserRouter, Routes, Route } from "react-router-dom";
import "./App.css";

import TenderDetail from "./pages/TenderDetail";
import Layout from "./components/Layout";
import AllTenders from "./pages/AllTenders";
import ParticipatedTenders from "./pages/ParticipatedTenders";
import EvaluationReports from "./pages/EvaluationReports";
import EvaluationDetail from "./pages/EvaluationDetail";
import ProjectUpdates from "./pages/ProjectUpdates";
import ProjectDetail from "./pages/ProjectDetail";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          
          {/* All Tenders */}
          <Route
            index
            element={<AllTenders />}
          />

          {/* Tender Detail */}
          <Route
            path="tenders/:tenderId"
            element={<TenderDetail />}
          />

          {/* Participated Tenders */}
          <Route
            path="participated"
            element={<ParticipatedTenders />}
          />

          {/* Evaluation Reports */}
          <Route
            path="evaluations"
            element={<EvaluationReports />}
          />

          {/* Evaluation Detail */}
          <Route
            path="evaluations/:tenderNo"
            element={<EvaluationDetail />}
          />

          {/* Project Updates */}
          <Route
            path="project-updates"
            element={<ProjectUpdates />}
          />

          {/* Project Detail */}
          <Route
            path="project-updates/:projectId"
            element={<ProjectDetail />}
          />

        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;