import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Search,
  RefreshCw,
} from "lucide-react";

import api from "../api";
import MultiSelect from "../components/MultiSelect";

const ProjectUpdates = () => {
  const navigate = useNavigate();

  const [projects, setProjects] = useState([]);
  const [search, setSearch] = useState("");
  const [regionFilter, setRegionFilter] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ============================================================
  // LOAD PROJECTS
  // ============================================================

  const loadProjects = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get(
        "/api/projects"
      );

      setProjects(
        Array.isArray(response.data)
          ? response.data
          : []
      );
    } catch (err) {
      console.error(
        "Failed to load projects:",
        err
      );

      setError(
        "Failed to load project updates."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  // ============================================================
  // REGION OPTIONS
  // ============================================================

  const regions = useMemo(() => {
    const values = projects
      .map(
        (project) =>
          project["Region"]
      )
      .filter(Boolean);

    return [
      ...new Set(values),
    ];
  }, [projects]);

  // ============================================================
  // FILTER PROJECTS
  // ============================================================

  const filteredProjects = useMemo(() => {
    const query =
      search.trim().toLowerCase();

    return projects.filter(
      (project) => {
        const projectName =
          String(
            project[
              "Project / Scheme Name"
            ] || ""
          ).toLowerCase();

        const region =
          String(
            project["Region"] || ""
          );

        const matchesSearch =
          !query ||
          projectName.includes(
            query
          );

        const matchesRegion =
          regionFilter.length === 0 ||
          regionFilter.includes(
            region
          );

        return (
          matchesSearch &&
          matchesRegion
        );
      }
    );
  }, [
    projects,
    search,
    regionFilter,
  ]);

  // ============================================================
  // FORMAT NUMBER
  // ============================================================

  const formatNumber = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    if (typeof value === "number") {
      return value.toLocaleString();
    }

    return String(value);
  };

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="tenders-page">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="page-header">

        <div>
          <h1>
            Project Updates
          </h1>

          <p>
            Track government projects and identify
            ICT opportunities relevant to Jazz.
          </p>
        </div>

        <div className="page-header-actions">

          <button
            className="project-refresh-button"
            onClick={loadProjects}
            disabled={loading}
          >
            <RefreshCw
              size={16}
              className={
                loading
                  ? "scraper-spinning"
                  : ""
              }
            />

            {loading
              ? "Loading..."
              : "Refresh Projects"}
          </button>

        </div>

      </div>


      {/* ======================================================
          SUMMARY
      ====================================================== */}

      <div className="summary-grid">

        <div className="summary-card">

          <div>
            <span className="summary-label">
              Total Projects
            </span>

            <span className="summary-value">
              {projects.length}
            </span>
          </div>

        </div>

      </div>


      {/* ======================================================
          SEARCH + REGION FILTER
      ====================================================== */}

      <div className="project-filters">

        <div className="project-search">

          <Search size={17} />

          <input
            type="text"
            placeholder="Search project name..."
            value={search}
            onChange={(e) =>
              setSearch(
                e.target.value
              )
            }
          />

        </div>

        <div className="project-region-select">
          <MultiSelect
            label="Region"
            options={regions}
            selected={regionFilter}
            onChange={setRegionFilter}
            placeholder="All Regions"
          />
        </div>

      </div>


      {/* ======================================================
          RESULTS TOOLBAR
      ====================================================== */}

      <div className="results-toolbar">

        <span className="results-count">
          Showing{" "}
          <strong>
            {filteredProjects.length}
          </strong>{" "}
          of{" "}
          <strong>
            {projects.length}
          </strong>{" "}
          projects
        </span>

      </div>


      {/* ======================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="scraper-message">
          {error}
        </div>
      )}


      {/* ======================================================
          PROJECT TABLE
      ====================================================== */}

      <div className="table-section">

        <div className="table-header">

          <div>
            <h2>
              Government Projects
            </h2>

            <span>
              Projects with identified ICT
              requirements and opportunity value.
            </span>
          </div>

        </div>

        <div className="table-container">

          <table>

            <thead>
              <tr>

                <th>
                  Region
                </th>

                <th>
                  Project / Scheme Name
                </th>

                <th>
                  ICT TAM on Allocation (M PKR)
                </th>

                <th>
                  Required Devices / Services
                </th>

              </tr>
            </thead>

            <tbody>

              {loading ? (
                <tr>

                  <td
                    colSpan="4"
                    className="empty-state"
                  >
                    Loading projects...
                  </td>

                </tr>
              ) : filteredProjects.length ===
                0 ? (
                <tr>

                  <td
                    colSpan="4"
                    className="empty-state"
                  >
                    <h3>
                      No projects found
                    </h3>

                    <p>
                      Try changing your
                      search or region filter.
                    </p>
                  </td>

                </tr>
              ) : (
                filteredProjects.map(
                  (
                    project,
                    index
                  ) => {

                    const projectId =
                      project[
                        "Project ID"
                      ];

                    const projectName =
                      project[
                        "Project / Scheme Name"
                      ];

                    const requiredServices =
                      Array.isArray(
                        project.required_services
                      )
                        ? project.required_services
                        : [];

                    return (
                      <tr
                        key={
                          projectId ??
                          `${projectName}-${index}`
                        }
                        className="clickable-row"
                        onClick={() =>
                          navigate(
                            `/project-updates/${encodeURIComponent(
                              String(
                                projectId
                              )
                            )}`
                          )
                        }
                      >

                        {/* REGION */}

                        <td>

                          <span className="region-badge">
                            {project[
                              "Region"
                            ] || "—"}
                          </span>

                        </td>


                        {/* PROJECT NAME */}

                        <td>

                          <div className="project-name">
                            {projectName}
                          </div>

                        </td>


                        {/* ICT TAM */}

                        <td>

                          <strong>
                            {formatNumber(
                              project[
                                "ICT TAM on Allocation (M PKR)"
                              ]
                            )}
                          </strong>

                        </td>


                        {/* REQUIRED SERVICES */}

                        <td>

                          <div className="service-chips">

                            {requiredServices.length >
                            0 ? (
                              requiredServices.map(
                                (
                                  service
                                ) => (
                                  <span
                                    key={
                                      service
                                    }
                                    className="service-chip"
                                  >
                                    {service}
                                  </span>
                                )
                              )
                            ) : (
                              <span className="no-services">
                                —
                              </span>
                            )}

                          </div>

                        </td>

                      </tr>
                    );
                  }
                )
              )}

            </tbody>

          </table>

        </div>

      </div>

    </div>
  );
};

export default ProjectUpdates;