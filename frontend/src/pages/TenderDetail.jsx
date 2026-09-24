import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Circle,
  Trash2,
} from "lucide-react";
import api from "../api";

const PROGRESS_STAGES = [
  "Participation",
  "Bid Preparation",
  "Bid Submitted",
];

const RESULT_OPTIONS = [
  "Win",
  "Lost",
  "Result Not Announced",
];

function formatKey(key) {
  return String(key)
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function isUrl(value) {
  return (
    typeof value === "string" &&
    /^https?:\/\//i.test(value)
  );
}

function formatDateOnly(value) {
  if (!value) {
    return "—";
  }

  const rawValue = String(value).trim();

  // Handle formats such as:
  // 2026-09-01T00:00:00
  // 2026-09-01T00:00:00.000
  // 2026-09-01
  if (/^\d{4}-\d{2}-\d{2}/.test(rawValue)) {
    const datePart = rawValue.slice(0, 10);

    const [year, month, day] =
      datePart.split("-");

    if (year && month && day) {
      const date = new Date(
        Number(year),
        Number(month) - 1,
        Number(day)
      );

      if (!Number.isNaN(date.getTime())) {
        return date.toLocaleDateString("en-GB", {
          day: "2-digit",
          month: "short",
          year: "numeric",
        });
      }
    }
  }

  // Handle formats such as:
  // 9/18/2026 12:00:00 AM
  // 09/18/2026 12:00:00 AM
  const slashDateMatch = rawValue.match(
    /^(\d{1,2})\/(\d{1,2})\/(\d{4})/
  );

  if (slashDateMatch) {
    const month = Number(
      slashDateMatch[1]
    );
    const day = Number(
      slashDateMatch[2]
    );
    const year = Number(
      slashDateMatch[3]
    );

    const date = new Date(
      year,
      month - 1,
      day
    );

    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleDateString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
      });
    }
  }

  // Fallback: try normal Date parsing.
  const date = new Date(rawValue);

  if (!Number.isNaN(date.getTime())) {
    return date.toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  return rawValue;
}

function getBalochistanTenderUrl(tender) {
  if (
    tender?.source !== "Balochistan PPRA" ||
    !tender?.Id
  ) {
    return null;
  }

  return (
    `https://bpptest.vdc.solutions/tenderdetail/` +
    `?Id=${encodeURIComponent(tender.Id)}` +
    `&frm=h&type=tenders&app=new`
  );
}

function displayPrimitive(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  if (isUrl(value)) {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="detail-link"
      >
        Open Link
        <ExternalLink size={14} />
      </a>
    );
  }

  return String(value);
}

function renderValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  if (typeof value !== "object") {
    return displayPrimitive(value);
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return "—";
    }

    return (
      <div className="detail-array">
        {value.map((item, index) => (
          <div
            className="detail-array-item"
            key={index}
          >
            {typeof item === "object" &&
            item !== null ? (
              <div className="detail-nested-grid">
                {Object.entries(item).map(
                  ([key, nestedValue]) => (
                    <div
                      className="detail-nested-item"
                      key={key}
                    >
                      <span>
                        {formatKey(key)}
                      </span>

                      <strong>
                        {renderValue(
                          nestedValue
                        )}
                      </strong>
                    </div>
                  )
                )}
              </div>
            ) : (
              displayPrimitive(item)
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="detail-nested-grid">
      {Object.entries(value).map(
        ([key, nestedValue]) => (
          <div
            className="detail-nested-item"
            key={key}
          >
            <span>
              {formatKey(key)}
            </span>

            <strong>
              {renderValue(
                nestedValue
              )}
            </strong>
          </div>
        )
      )}
    </div>
  );
}

function TenderDetail() {
  const { tenderId } = useParams();
  const navigate = useNavigate();

  const [tender, setTender] = useState(null);

  const [participating, setParticipating] =
    useState(false);

  const [stage, setStage] =
    useState("Participation");

  const [result, setResult] =
    useState(null);

  const [participationLoading, setParticipationLoading] =
    useState(false);

  const [stageLoading, setStageLoading] =
    useState(false);

  const [resultLoading, setResultLoading] =
    useState(false);

  const [deleteLoading, setDeleteLoading] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  useEffect(() => {
    const fetchTenderData = async () => {
      try {
        const [
          tenderResponse,
          progressResponse,
        ] = await Promise.all([
          api.get(
            `/api/tenders/${tenderId}`
          ),
          api.get(
            `/api/tenders/${tenderId}/progress`
          ),
        ]);

        setTender(
          tenderResponse.data
        );

        const progress =
          progressResponse.data;

        setParticipating(
          Boolean(
            progress?.participating
          )
        );

        setStage(
          progress?.stage ||
            "Participation"
        );

        setResult(
          progress?.result || null
        );
      } catch (err) {
        console.error(err);

        setError(
          "Failed to load tender details."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchTenderData();
  }, [tenderId]);

  async function handleParticipationChange(
    value
  ) {
    if (participationLoading) return;

    try {
      setParticipationLoading(true);

      await api.patch(
        `/api/tenders/${tenderId}/participation`,
        {
          participating: value,
        }
      );

      setParticipating(value);

      if (!value) {
        setStage("Participation");
        setResult(null);
      }
    } catch (err) {
      console.error(err);

      alert(
        "Failed to update participation status."
      );
    } finally {
      setParticipationLoading(false);
    }
  }

  async function handleStageChange(
    newStage
  ) {
    if (
      stageLoading ||
      !participating
    ) {
      return;
    }

    try {
      setStageLoading(true);

      const response =
        await api.patch(
          `/api/tenders/${tenderId}/progress`,
          {
            stage: newStage,
          }
        );

      setStage(
        response.data?.stage ||
          newStage
      );
    } catch (err) {
      console.error(err);

      alert(
        "Failed to update project progress."
      );
    } finally {
      setStageLoading(false);
    }
  }

  async function handleResultChange(
    newResult
  ) {
    if (
      resultLoading ||
      !participating
    ) {
      return;
    }

    try {
      setResultLoading(true);

      const response =
        await api.patch(
          `/api/tenders/${tenderId}/result`,
          {
            result: newResult,
          }
        );

      setResult(
        response.data?.result ||
          newResult
      );

      setStage("Bid Submitted");
    } catch (err) {
      console.error(err);

      alert(
        "Failed to update tender result."
      );
    } finally {
      setResultLoading(false);
    }
  }

  async function handleDeleteTender() {
    const confirmed =
      window.confirm(
        "Are you sure you want to delete this tender?\n\nThis action cannot be undone."
      );

    if (!confirmed) {
      return;
    }

    try {
      setDeleteLoading(true);

      await api.delete(
        `/api/tenders/${encodeURIComponent(
          tenderId
        )}`
      );

      navigate("/");
    } catch (err) {
      console.error(err);

      alert(
        "Failed to delete the tender."
      );
    } finally {
      setDeleteLoading(false);
    }
  }

  function getStageIndex() {
    return PROGRESS_STAGES.indexOf(
      stage
    );
  }

  if (loading) {
    return (
      <h1>
        Loading tender...
      </h1>
    );
  }

  if (error) {
    return <h1>{error}</h1>;
  }

  if (!tender) {
    return (
      <h1>
        Tender not found.
      </h1>
    );
  }

  const currentStageIndex =
    getStageIndex();

  const isBalochistan =
    tender.source ===
    "Balochistan PPRA";

  const balochistanTenderUrl =
    getBalochistanTenderUrl(
      tender
    );

  return (
    <div className="tender-detail-page">

      <button
        className="back-button"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={17} />
        Back to Tenders
      </button>

      <div className="page-header">
        <div>
          <h1>
            {tender["Tender Title"] ||
              tender.tender_details ||
              tender.TenderName ||
              tender.TenderTitle ||
              "Tender Details"}
          </h1>

          <p>
            Source:{" "}
            <strong>
              {tender.source || "—"}
            </strong>
          </p>
        </div>
      </div>

      {/* Balochistan Tender Link */}

      {isBalochistan &&
        balochistanTenderUrl && (
          <div className="detail-card">
            <div className="progress-section-header">
              <div>
                <h2>
                  Balochistan PPRA
                </h2>

                <p>
                  Open the complete tender
                  details on the Balochistan
                  PPRA portal.
                </p>
              </div>

              <a
                href={
                  balochistanTenderUrl
                }
                target="_blank"
                rel="noopener noreferrer"
                className="detail-link"
              >
                Open Tender
                <ExternalLink
                  size={14}
                />
              </a>
            </div>
          </div>
        )}

      {/* Participation */}

      <div className="detail-card participation-card">

        <div className="participation-header">

          <div>
            <h2>
              Participation
            </h2>

            <p>
              Mark whether JazzWorld is
              participating in this tender.
            </p>
          </div>

          <div
            className={`participation-status ${
              participating
                ? "participating"
                : "not-participating"
            }`}
          >
            {participating ? (
              <>
                <CheckCircle2
                  size={16}
                />
                Participating
              </>
            ) : (
              <>
                <XCircle
                  size={16}
                />
                Not Participating
              </>
            )}
          </div>

        </div>

        <div className="participation-actions">

          <button
            type="button"
            className={`participation-button ${
              !participating
                ? "selected"
                : ""
            }`}
            disabled={
              participationLoading
            }
            onClick={() =>
              handleParticipationChange(
                false
              )
            }
          >
            <XCircle size={16} />
            Not Participating
          </button>

          <button
            type="button"
            className={`participation-button ${
              participating
                ? "selected"
                : ""
            }`}
            disabled={
              participationLoading
            }
            onClick={() =>
              handleParticipationChange(
                true
              )
            }
          >
            <CheckCircle2 size={16} />
            Participating
          </button>

        </div>

      </div>

      {/* Project Progress */}

      {participating && (
        <div className="detail-card progress-card">

          <div className="progress-section-header">

            <div>
              <h2>
                Project Progress
              </h2>

              <p>
                Track the current bidding
                stage for this tender.
              </p>
            </div>

            <span className="progress-current-badge">
              {stage}
            </span>

          </div>

          <div className="detail-progress-tracker">

            {PROGRESS_STAGES.map(
              (
                progressStage,
                index
              ) => {

                const completed =
                  index <=
                  currentStageIndex;

                const active =
                  index ===
                  currentStageIndex;

                return (
                  <div
                    className="detail-progress-wrapper"
                    key={
                      progressStage
                    }
                  >

                    <button
                      type="button"
                      disabled={
                        stageLoading
                      }
                      className={`detail-progress-stage ${
                        completed
                          ? "completed"
                          : ""
                      } ${
                        active
                          ? "active"
                          : ""
                      }`}
                      onClick={() =>
                        handleStageChange(
                          progressStage
                        )
                      }
                    >

                      {completed ? (
                        <CheckCircle2
                          size={19}
                        />
                      ) : (
                        <span className="progress-circle">
                          {index + 1}
                        </span>
                      )}

                      <span>
                        {
                          progressStage
                        }
                      </span>

                    </button>

                    {index <
                      PROGRESS_STAGES.length -
                        1 && (
                      <span
                        className={`detail-progress-line ${
                          index <
                          currentStageIndex
                            ? "completed"
                            : ""
                        }`}
                      />
                    )}

                  </div>
                );
              }
            )}

          </div>

        </div>
      )}

      {/* Result */}

      {participating &&
        stage ===
          "Bid Submitted" && (
          <div className="detail-card result-card">

            <div className="progress-section-header">

              <div>
                <h2>
                  Tender Result
                </h2>

                <p>
                  Update the result once the
                  tender outcome is available.
                </p>
              </div>

              {result && (
                <span
                  className={`result-status ${
                    result === "Win"
                      ? "result-win"
                      : result === "Lost"
                      ? "result-lost"
                      : "result-pending"
                  }`}
                >
                  {result}
                </span>
              )}

            </div>

            <div className="result-actions">

              {RESULT_OPTIONS.map(
                (option) => (
                  <button
                    type="button"
                    key={option}
                    disabled={
                      resultLoading
                    }
                    className={`result-button ${
                      result === option
                        ? "selected"
                        : ""
                    }`}
                    onClick={() =>
                      handleResultChange(
                        option
                      )
                    }
                  >

                    {option ===
                      "Win" && (
                      <CheckCircle2
                        size={16}
                      />
                    )}

                    {option ===
                      "Lost" && (
                      <XCircle
                        size={16}
                      />
                    )}

                    {option ===
                      "Result Not Announced" && (
                      <Circle
                        size={16}
                      />
                    )}

                    {option}

                  </button>
                )
              )}

            </div>

          </div>
        )}

      {/* Tender Data */}

      <div className="detail-card">

        <h2>
          Tender Data
        </h2>

        <div className="detail-grid">

          {Object.entries(
            tender
          ).map(
            ([key, value]) => {

              /*
               * Balochistan's raw API response
               * contains document paths which are
               * not useful to display directly.
               */
              if (
                isBalochistan &&
                (
                  key ===
                    "tenderNoticeDoc" ||
                  key ===
                    "tenderBidDoc"
                )
              ) {
                return null;
              }

              let displayValue =
                renderValue(value);

              /*
               * Balochistan API returns
               * timestamps for these fields.
               * Display date only.
               */
              if (
                isBalochistan &&
                key ===
                  "PublishedDate"
              ) {
                displayValue =
                  formatDateOnly(
                    value
                  );
              }

              if (
                isBalochistan &&
                key === "CloseDate"
              ) {
                displayValue =
                  formatDateOnly(
                    value
                  );
              }

              return (
                <div
                  className="detail-item"
                  key={key}
                >
                  <span>
                    {formatKey(key)}
                  </span>

                  <strong>
                    {displayValue}
                  </strong>
                </div>
              );
            }
          )}

        </div>

      </div>

      {/* Delete Tender */}

      <div className="delete-tender-section">

        <button
          type="button"
          className="delete-tender-button"
          disabled={deleteLoading}
          onClick={
            handleDeleteTender
          }
        >
          <Trash2 size={16} />

          {deleteLoading
            ? "Deleting..."
            : "Delete Tender"}
        </button>

      </div>

    </div>
  );
}

export default TenderDetail;