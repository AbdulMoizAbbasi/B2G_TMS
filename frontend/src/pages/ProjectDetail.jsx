import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  RefreshCw,
  CalendarDays,
  Newspaper,
} from "lucide-react";

import api from "../api";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [refreshMessage, setRefreshMessage] = useState("");

  const loadProject = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await api.get(
        `/api/projects/${encodeURIComponent(projectId)}`
      );

      setProject(response.data);
    } catch (err) {
      console.error("Failed to load project:", err);
      setError("Failed to load project details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProject();
  }, [projectId]);

  const refreshNews = async () => {
    if (refreshing) return;

    try {
      setRefreshing(true);
      setRefreshMessage("");

      const response = await api.post(
        `/api/projects/${encodeURIComponent(
          projectId
        )}/news/refresh`
      );

      setRefreshMessage(
        response.data?.new_count > 0
          ? `${response.data.new_count} new update${
              response.data.new_count === 1
                ? ""
                : "s"
            } found.`
          : "No new updates found."
      );

      await loadProject();
    } catch (err) {
      console.error(
        "Failed to refresh project news:",
        err
      );

      setRefreshMessage(
        "Failed to refresh project updates."
      );
    } finally {
      setRefreshing(false);
    }
  };

  const formatValue = (value) => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    return String(value);
  };

  const formatNewsDate = (value) => {
    if (!value) {
      return "Date unavailable";
    }

    return String(value);
  };

  const isUrl = (value) => {
    return (
      typeof value === "string" &&
      /^https?:\/\//i.test(value)
    );
  };

  /*
   * Backend currently returns Keypoints as:
   *
   * "• Point one
   *  • Point two"
   *
   * This converts that string into individual
   * keypoints for clean frontend rendering.
   */
  const parseKeypoints = (value) => {
    if (Array.isArray(value)) {
      return value
        .map((point) => String(point).trim())
        .filter(Boolean);
    }

    if (typeof value === "string") {
      return value
        .split(/\r?\n/)
        .map((point) => point.trim())
        .filter(Boolean)
        .map((point) =>
          point.replace(/^•\s*/, "")
        );
    }

    return [];
  };

  if (loading) {
    return (
      <div className="tender-detail-page">
        <h1>Loading project...</h1>
      </div>
    );
  }

  if (error) {
    return (
      <div className="tender-detail-page">
        <button
          className="back-button"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft size={17} />
          Back to Project Updates
        </button>

        <h1>{error}</h1>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="tender-detail-page">
        <h1>Project not found.</h1>
      </div>
    );
  }

  const requiredServices = Array.isArray(
    project.required_services
  )
    ? project.required_services
    : [];

  const news = Array.isArray(project.news)
    ? project.news
    : [];

  return (
    <div className="tender-detail-page">

      {/* ======================================================
          BACK
          ====================================================== */}

      <button
        className="back-button"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={17} />
        Back to Project Updates
      </button>

      {/* ======================================================
          HEADER
          ====================================================== */}

      <div className="page-header project-detail-header">

        <div>
          <h1>
            {project["Project / Scheme Name"] ||
              "Project Details"}
          </h1>

          <p>
            {project["Region"] || "—"}

            {project["Project ID"] && (
              <>
                {" • Project ID: "}
                <strong>
                  {project["Project ID"]}
                </strong>
              </>
            )}
          </p>
        </div>

        <div className="page-header-actions">

          <button
            type="button"
            className="project-refresh-button"
            onClick={refreshNews}
            disabled={refreshing}
          >
            <RefreshCw
              size={16}
              className={
                refreshing
                  ? "scraper-spinning"
                  : ""
              }
            />

            {refreshing
              ? "Refreshing..."
              : "Refresh Updates"}
          </button>

        </div>

      </div>

      {/* ======================================================
          REFRESH MESSAGE
          ====================================================== */}

      {refreshMessage && (
        <div className="scraper-message">
          {refreshMessage}
        </div>
      )}

      {/* ======================================================
          SUMMARY
          ====================================================== */}

      <div className="summary-grid project-summary-grid">

        <div className="summary-card">
          <div>
            <span className="summary-label">
              ICT TAM on Allocation
            </span>

            <span className="summary-value">
              {formatValue(
                project[
                  "ICT TAM on Allocation (M PKR)"
                ]
              )}
            </span>
          </div>
        </div>

        <div className="summary-card">
          <div>
            <span className="summary-label">
              ICT Involvement
            </span>

            <span className="summary-value">
              {formatValue(
                project["ICT Involvement %"]
              )}
            </span>
          </div>
        </div>

        <div className="summary-card">
          <div>
            <span className="summary-label">
              Project Status
            </span>

            <span className="summary-value">
              {formatValue(
                project["Status"]
              )}
            </span>
          </div>
        </div>

        <div className="summary-card">
          <div>
            <span className="summary-label">
              Latest Updates
            </span>

            <span className="summary-value">
              {news.length}
            </span>
          </div>
        </div>

      </div>

      {/* ======================================================
          MAIN PROJECT DETAIL
          ====================================================== */}

      <div
        className="project-detail-layout"
        style={{
          alignItems: "stretch",
        }}
      >

        {/* ====================================================
            LEFT — ICT OPPORTUNITY
            ==================================================== */}

        <div
          className="detail-card project-opportunity-card"
          style={{
            height: "560px",
            minHeight: "560px",
            boxSizing: "border-box",
          }}
        >

          <div className="project-section-header">

            <div>
              <h2>ICT Opportunity</h2>

              <p>
                ICT requirements and opportunity value
                identified for this project.
              </p>
            </div>

          </div>

          <div className="opportunity-metrics">

            <div className="opportunity-metric primary">

              <span>
                ICT TAM on Allocation
              </span>

              <strong>
                {formatValue(
                  project[
                    "ICT TAM on Allocation (M PKR)"
                  ]
                )}
              </strong>

              <small>
                M PKR
              </small>

            </div>

            <div className="opportunity-metric">

              <span>
                ICT Involvement
              </span>

              <strong>
                {formatValue(
                  project["ICT Involvement %"]
                )}
              </strong>

            </div>

            <div className="opportunity-metric">

              <span>
                ICT TAM on Total Cost
              </span>

              <strong>
                {formatValue(
                  project[
                    "ICT TAM on Total Cost (M PKR)"
                  ]
                )}
              </strong>

              <small>
                M PKR
              </small>

            </div>

          </div>

          <div className="project-reasoning">

            <span>ICT Reasoning</span>

            <p>
              {formatValue(
                project["ICT Reasoning"]
              )}
            </p>

          </div>

          <div className="project-services-section">

            <span>
              Required Devices / Services
            </span>

            <div className="service-chips">

              {requiredServices.length > 0 ? (
                requiredServices.map(
                  (service) => (
                    <span
                      key={service}
                      className="service-chip"
                    >
                      {service}
                    </span>
                  )
                )
              ) : (
                <span className="no-services">
                  No specific ICT services identified.
                </span>
              )}

            </div>

          </div>

        </div>

        {/* ====================================================
            RIGHT — LATEST PROJECT UPDATES
            ==================================================== */}

        <div
          className="detail-card project-news-card"
          style={{
            height: "560px",
            minHeight: "560px",
            boxSizing: "border-box",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >

          <div className="project-news-header">

            <div>

              <div className="project-news-title-row">

                <Newspaper size={19} />

                <h2>
                  Latest Project Updates
                </h2>

              </div>

              <p>
                Recent publicly available updates
                related to this project.
              </p>

            </div>

            <span className="project-news-count">
              {news.length}{" "}
              {news.length === 1
                ? "Update"
                : "Updates"}
            </span>

          </div>

          {news.length === 0 ? (
            <div className="empty-state">

              <h3>
                No updates available
              </h3>

              <p>
                Click "Refresh Updates" to search
                for recent project news.
              </p>

            </div>
          ) : (
            <div
              className="project-news-list"
              style={{
                flex: 1,
                minHeight: 0,
                overflowY: "auto",
                overflowX: "hidden",
                paddingRight: "8px",
              }}
            >

              {news.map((item, index) => {

                const keypoints =
                  parseKeypoints(
                    item["Keypoints"]
                  );

                return (
                  <article
                    className={`project-news-item ${
                      index === 0
                        ? "latest"
                        : ""
                    }`}
                    key={
                      item.URL ||
                      `${item["News Title"]}-${index}`
                    }
                  >

                    {/* News title */}

                    <h3>
                      {item["News Title"] ||
                        "Untitled Update"}
                    </h3>

                    {/* Keypoints — PRIMARY */}

                    {keypoints.length > 0 ? (
                      <div className="project-news-keypoints">

                        {keypoints.map(
                          (
                            point,
                            pointIndex
                          ) => (
                            <div
                              className="project-news-keypoint"
                              key={
                                pointIndex
                              }
                            >
                              <span className="keypoint-dot" />

                              <span>
                                {point}
                              </span>
                            </div>
                          )
                        )}

                      </div>
                    ) : (
                      <p className="project-news-no-keypoints">
                        No keypoints available.
                      </p>
                    )}

                    {/* Source / Date / Link */}

                    <div className="project-news-footer">

                      <div className="project-news-meta">

                        <span className="project-news-source-name">
                          {formatValue(
                            item["Source"]
                          )}
                        </span>

                        <span className="project-news-date">

                          <CalendarDays
                            size={13}
                          />

                          {formatNewsDate(
                            item["News Date"]
                          )}

                        </span>

                      </div>

                      {isUrl(
                        item["URL"]
                      ) && (
                        <a
                          href={item["URL"]}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="project-news-link"
                        >
                          Open Source

                          <ExternalLink
                            size={13}
                          />
                        </a>
                      )}

                    </div>

                  </article>
                );
              })}

            </div>
          )}

        </div>

        {/* ====================================================
            BELOW — PROJECT INFORMATION
            ==================================================== */}

        <div className="detail-card project-information-card">

          <div className="project-section-header">

            <div>
              <h2>Project Information</h2>

              <p>
                Complete project details from the
                ICT Projects database.
              </p>
            </div>

          </div>

          <div className="detail-grid">

            <div className="detail-item">
              <span>Region</span>

              <strong>
                {formatValue(
                  project["Region"]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Project ID</span>

              <strong>
                {formatValue(
                  project["Project ID"]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Project / Scheme Name</span>

              <strong>
                {formatValue(
                  project[
                    "Project / Scheme Name"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Sector / Division</span>

              <strong>
                {formatValue(
                  project[
                    "Sector / Division"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Sub-Sector</span>

              <strong>
                {formatValue(
                  project["Sub-Sector"]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                Ministry / Department / Authority
              </span>

              <strong>
                {formatValue(
                  project[
                    "Ministry / Department / Authority"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Location</span>

              <strong>
                {formatValue(
                  project["Location"]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>Status</span>

              <strong>
                {formatValue(
                  project["Status"]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                Total Project Cost (M PKR)
              </span>

              <strong>
                {formatValue(
                  project[
                    "Total Project Cost (M PKR)"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                FY2026-27 Allocation (M PKR)
              </span>

              <strong>
                {formatValue(
                  project[
                    "FY2026-27 Allocation (M PKR)"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                ICT Involvement %
              </span>

              <strong>
                {formatValue(
                  project[
                    "ICT Involvement %"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                ICT TAM on Allocation (M PKR)
              </span>

              <strong>
                {formatValue(
                  project[
                    "ICT TAM on Allocation (M PKR)"
                  ]
                )}
              </strong>
            </div>

            <div className="detail-item">
              <span>
                ICT TAM on Total Cost (M PKR)
              </span>

              <strong>
                {formatValue(
                  project[
                    "ICT TAM on Total Cost (M PKR)"
                  ]
                )}
              </strong>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
};

export default ProjectDetail;