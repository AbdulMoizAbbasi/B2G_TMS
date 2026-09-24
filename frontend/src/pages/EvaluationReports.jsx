import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import {
  RefreshCw,
  FileText,
  ClipboardCheck,
  CheckCircle2,
  AlertCircle,
  Users,
  Trophy,
  Tag,
} from "lucide-react";

function EvaluationReports() {
  const navigate = useNavigate();

  const [evaluations, setEvaluations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(false);

  const [error, setError] = useState("");
  const [fetchMessage, setFetchMessage] = useState(null);

  // ---------------------------------------------------------
  // Load stored evaluation reports
  // ---------------------------------------------------------
  const loadEvaluations = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await axios.get(
        "http://127.0.0.1:8000/api/evaluations"
      );

      const data = response.data;

      if (Array.isArray(data)) {
        setEvaluations(data);
      } else if (Array.isArray(data?.value)) {
        setEvaluations(data.value);
      } else {
        setEvaluations([]);
      }
    } catch (err) {
      console.error(
        "Failed to load evaluation reports:",
        err
      );

      setError(
        err.response?.data?.detail ||
          "Failed to load evaluation reports."
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluations();
  }, []);

  // ---------------------------------------------------------
  // Manually check PPRA for new evaluation reports
  // ---------------------------------------------------------
  const checkForNewEvaluations = async () => {
    try {
      setFetching(true);
      setError("");
      setFetchMessage(null);

      // IDs already present before this execution
      const existingIds = new Set(
        evaluations.map(
          (evaluation) =>
            evaluation.evaluation_id
        )
      );

      const response = await axios.post(
        "http://127.0.0.1:8000/api/evaluations/fetch"
      );

      const results =
        response.data?.results || [];

      // Reload evaluations after fetching
      const evaluationsResponse =
        await axios.get(
          "http://127.0.0.1:8000/api/evaluations"
        );

      const data =
        evaluationsResponse.data;

      const latestEvaluations =
        Array.isArray(data)
          ? data
          : Array.isArray(data?.value)
          ? data.value
          : [];

      setEvaluations(
        latestEvaluations
      );

      // Find newly added evaluation reports
      const newEvaluations =
        latestEvaluations.filter(
          (evaluation) =>
            !existingIds.has(
              evaluation.evaluation_id
            )
        );

      // Count execution results
      const processed =
        results.filter(
          (result) =>
            result?.status ===
            "processed"
        ).length;

      const alreadyProcessed =
        results.filter(
          (result) =>
            result?.status ===
            "already_processed"
        ).length;

      const notFound =
        results.filter(
          (result) =>
            result?.status ===
            "not_found"
        ).length;

      const notImplemented =
        results.filter(
          (result) =>
            result?.status ===
            "source_not_implemented"
        ).length;

      setFetchMessage({
        type:
          newEvaluations.length > 0
            ? "success"
            : "info",

        newCount:
          newEvaluations.length,

        processed,

        alreadyProcessed,

        notFound,

        notImplemented,
      });
    } catch (err) {
      console.error(
        "Failed to fetch new evaluations:",
        err
      );

      setError(
        err.response?.data?.detail ||
          "Failed to check for new evaluation reports."
      );
    } finally {
      setFetching(false);
    }
  };

  // ---------------------------------------------------------
  // Group evaluations by tender number
  //
  // One tender = ONE ROW
  // Multiple evaluation reports belong to that row.
  // ---------------------------------------------------------
  const groupedTenders = useMemo(() => {
    const groups = {};

    evaluations.forEach(
      (evaluation) => {
        const tenderNo =
          evaluation?.scraped_data
            ?.tender_no ||
          "Unknown Tender";

        if (!groups[tenderNo]) {
          groups[tenderNo] = {
            tenderNo,

            source:
              evaluation?.scraped_data
                ?.source ||
              "Unknown Source",

            /*
             * Tender data comes from
             * relevant_tenders.json through
             * the backend API.
             */
            tenderData:
              evaluation?.tender_data ||
              null,

            evaluations: [],
          };
        }

        /*
         * If another evaluation contains
         * tender_data, use it.
         */
        if (
          !groups[tenderNo].tenderData &&
          evaluation?.tender_data
        ) {
          groups[tenderNo].tenderData =
            evaluation.tender_data;
        }

        groups[tenderNo].evaluations.push(
          evaluation
        );
      }
    );

    return Object.values(groups);
  }, [evaluations]);

  // ---------------------------------------------------------
  // Get Tender Name
  //
  // IMPORTANT:
  // Tender name comes ONLY from tender_data,
  // which is enriched from relevant_tenders.json.
  //
  // OCR procurement_title is intentionally NOT used.
  // ---------------------------------------------------------
  const getTenderName = (tender) => {
    return (
      tender?.tenderData?.[
        "Tender Title"
      ] ||
      tender?.tenderData
        ?.tender_details ||
      tender?.tenderData?.Name ||
      "N/A"
    );
  };

  // ---------------------------------------------------------
  // Get Relevance
  // ---------------------------------------------------------
  const getRelevance = (tender) => {
    const relevance =
      tender?.tenderData
        ?.relevance || {};

    const keywordScore =
      relevance?.keyword_score;

    if (
      typeof keywordScore !==
      "number"
    ) {
      return "N/A";
    }

    return keywordScore;
  };

  // ---------------------------------------------------------
  // Get Matched Keywords
  // ---------------------------------------------------------
  const getMatchedKeywords = (
    tender
  ) => {
    const keywords =
      tender?.tenderData
        ?.relevance
        ?.matched_keywords;

    if (!Array.isArray(keywords)) {
      return [];
    }

    return keywords;
  };

  // ---------------------------------------------------------
  // OCR evaluation information
  // ---------------------------------------------------------
  const getTenderEvaluationData = (
    tender
  ) => {
    const reports =
      tender?.evaluations || [];

    let bidsReceived = null;

    const bidders = [];
    const winners = [];

    reports.forEach(
      (evaluation) => {
        const ocr =
          evaluation?.ocr_data ||
          {};

        // -----------------------------------------------
        // Number of bidders
        // -----------------------------------------------
        if (
          bidsReceived === null &&
          ocr?.bids_received !==
            null &&
          ocr?.bids_received !==
            undefined
        ) {
          bidsReceived =
            ocr.bids_received;
        }

        // -----------------------------------------------
        // Bidder names
        // -----------------------------------------------
        if (
          Array.isArray(
            ocr?.bid_evaluations
          )
        ) {
          ocr.bid_evaluations.forEach(
            (bid) => {
              const bidder =
                bid?.bidder;

              if (
                bidder &&
                !bidders.some(
                  (existing) =>
                    existing.toLowerCase() ===
                    bidder.toLowerCase()
                )
              ) {
                bidders.push(
                  bidder
                );
              }
            }
          );
        }

        // -----------------------------------------------
        // Winner
        // -----------------------------------------------
        const winner =
          ocr
            ?.lowest_evaluated_bidder
            ?.name;

        if (
          winner &&
          !winners.some(
            (existing) =>
              existing.toLowerCase() ===
              winner.toLowerCase()
          )
        ) {
          winners.push(
            winner
          );
        }
      }
    );

    // -----------------------------------------------
    // Jazz participation
    // -----------------------------------------------
    const jazzParticipated =
      bidders.some(
        (bidder) =>
          bidder
            .toLowerCase()
            .includes("jazz")
      );

    return {
      bidsReceived,
      bidders,
      winners,
      jazzParticipated,
    };
  };

  // ---------------------------------------------------------
  // Open tender-level evaluation detail
  // ---------------------------------------------------------
  const openTenderEvaluation = (
    tender
  ) => {
    navigate(
      `/evaluations/${encodeURIComponent(
        tender.tenderNo
      )}`
    );
  };

  return (
    <div className="page-container">

      {/* -------------------------------------------------- */}
      {/* Page Header */}
      {/* -------------------------------------------------- */}

      <div className="page-header">
        <div>
          <h1>
            Evaluation Reports
          </h1>

          <p>
            Review evaluation reports
            fetched from procurement
            sources.
          </p>
        </div>

        <div
          style={{
            display: "flex",
            gap: "10px",
            alignItems: "center",
          }}
        >
          <button
            type="button"
            className="refresh-btn"
            onClick={
              loadEvaluations
            }
            disabled={
              loading || fetching
            }
          >
            <RefreshCw
              size={17}
              className={
                loading
                  ? "spin"
                  : ""
              }
            />

            {loading
              ? "Refreshing..."
              : "Refresh"}
          </button>

          <button
            type="button"
            className="refresh-btn"
            onClick={
              checkForNewEvaluations
            }
            disabled={
              fetching || loading
            }
          >
            <RefreshCw
              size={17}
              className={
                fetching
                  ? "spin"
                  : ""
              }
            />

            {fetching
              ? "Checking..."
              : "Check for New Evaluations"}
          </button>
        </div>
      </div>

      {/* -------------------------------------------------- */}
      {/* Error */}
      {/* -------------------------------------------------- */}

      {error && (
        <div className="error-message">
          <AlertCircle
            size={17}
          />

          {error}
        </div>
      )}

      {/* -------------------------------------------------- */}
      {/* Fetch Result */}
      {/* -------------------------------------------------- */}

      {fetchMessage && (
        <div
          className={
            fetchMessage.type ===
            "success"
              ? "evaluation-fetch-message success"
              : "evaluation-fetch-message"
          }
        >
          {fetchMessage.type ===
          "success" ? (
            <CheckCircle2
              size={19}
            />
          ) : (
            <ClipboardCheck
              size={19}
            />
          )}

          <div>
            <strong>
              {fetchMessage.newCount >
              0
                ? `${fetchMessage.newCount} new evaluation${
                    fetchMessage.newCount !==
                    1
                      ? "s"
                      : ""
                  } found`
                : "No new evaluations found"}
            </strong>

            <p>
              Processed:{" "}
              {
                fetchMessage.processed
              }
              {"  "}•{"  "}
              Already processed:{" "}
              {
                fetchMessage.alreadyProcessed
              }
              {"  "}•{"  "}
              Not found:{" "}
              {
                fetchMessage.notFound
              }
              {"  "}•{"  "}
              Unsupported source:{" "}
              {
                fetchMessage.notImplemented
              }
            </p>
          </div>
        </div>
      )}

      {/* -------------------------------------------------- */}
      {/* Summary Cards */}
      {/* -------------------------------------------------- */}

      <div className="summary-grid">

        <div className="summary-card">
          <div className="summary-card-icon">
            <FileText
              size={21}
            />
          </div>

          <div>
            <div className="summary-card-label">
              Evaluation Reports
            </div>

            <div className="summary-card-value">
              {
                evaluations.length
              }
            </div>
          </div>
        </div>

        <div className="summary-card">
          <div className="summary-card-icon">
            <ClipboardCheck
              size={21}
            />
          </div>

          <div>
            <div className="summary-card-label">
              Tenders With Evaluations
            </div>

            <div className="summary-card-value">
              {
                groupedTenders.length
              }
            </div>
          </div>
        </div>

      </div>

      {/* -------------------------------------------------- */}
      {/* Evaluation Reports Table */}
      {/* -------------------------------------------------- */}

      <div className="table-section evaluation-section">

        <div className="section-header">
          <div>
            <h2>
              Available Evaluation Reports
            </h2>

            <p>
              {groupedTenders.length ===
              0
                ? "No evaluation reports available."
                : `${groupedTenders.length} tender${
                    groupedTenders.length !==
                    1
                      ? "s"
                      : ""
                  } with evaluation reports`}
            </p>
          </div>
        </div>

        {/* Loading */}
        {loading &&
        evaluations.length ===
          0 ? (
          <div className="evaluation-empty-state">

            <RefreshCw
              size={28}
              className="spin"
            />

            <h3>
              Loading Evaluation Reports
            </h3>

            <p>
              Fetching stored
              evaluation reports...
            </p>

          </div>
        ) : groupedTenders.length ===
          0 ? (

          /* Empty */
          <div className="evaluation-empty-state">

            <FileText
              size={32}
            />

            <h3>
              No Evaluation Reports
            </h3>

            <p>
              No evaluation reports
              have been fetched yet.
            </p>

          </div>
        ) : (

          /* ------------------------------------------------ */
          /* Table */
          /* ------------------------------------------------ */

          <div className="table-wrapper">

            <table>

              <thead>
                <tr>
                  <th>
                    Tender No.
                  </th>

                  <th>
                    Tender Name
                  </th>

                  <th>
                    Source
                  </th>

                  <th>
                    Relevance
                  </th>

                  <th>
                    Keyword Matched
                  </th>

                  <th>
                    Jazz Participated
                  </th>

                  <th>
                    No. of Bidders
                  </th>

                  <th>
                    Who Won
                  </th>
                </tr>
              </thead>

              <tbody>

                {groupedTenders.map(
                  (tender) => {
                    const evaluationData =
                      getTenderEvaluationData(
                        tender
                      );

                    const tenderName =
                      getTenderName(
                        tender
                      );

                    const relevance =
                      getRelevance(
                        tender
                      );

                    const matchedKeywords =
                      getMatchedKeywords(
                        tender
                      );

                    return (
                      <tr
                        key={
                          tender.tenderNo
                        }
                      >

                        {/* -------------------------------- */}
                        {/* Tender Number */}
                        {/* -------------------------------- */}

                        <td>

                          <button
                            type="button"
                            onClick={() =>
                              openTenderEvaluation(
                                tender
                              )
                            }
                            style={{
                              background:
                                "none",
                              border:
                                "none",
                              padding:
                                0,
                              margin:
                                0,
                              color:
                                "inherit",
                              font:
                                "inherit",
                              fontWeight:
                                600,
                              cursor:
                                "pointer",
                              textAlign:
                                "left",
                            }}
                            title="Open evaluation details"
                          >
                            {
                              tender.tenderNo
                            }
                          </button>

                        </td>

                        {/* -------------------------------- */}
                        {/* Tender Name */}
                        {/* -------------------------------- */}

                        <td>

                          <button
                            type="button"
                            onClick={() =>
                              openTenderEvaluation(
                                tender
                              )
                            }
                            className="project-name"
                            style={{
                              background:
                                "none",
                              border:
                                "none",
                              padding:
                                0,
                              margin:
                                0,
                              color:
                                "inherit",
                              font:
                                "inherit",
                              fontWeight:
                                600,
                              cursor:
                                "pointer",
                              textAlign:
                                "left",
                              width:
                                "100%",
                            }}
                            title="Open evaluation details"
                          >
                            {
                              tenderName
                            }
                          </button>

                        </td>

                        {/* -------------------------------- */}
                        {/* Source */}
                        {/* -------------------------------- */}

                        <td>

                          <span className="evaluation-source-badge">
                            {
                              tender.source
                            }
                          </span>

                        </td>

                        {/* -------------------------------- */}
                        {/* Relevance */}
                        {/* -------------------------------- */}

                        <td>

                          {relevance ===
                          "N/A"
                            ? "N/A"
                            : relevance}

                        </td>

                        {/* -------------------------------- */}
                        {/* Keyword Matched */}
                        {/* -------------------------------- */}

                        <td>

                          {matchedKeywords.length >
                          0 ? (

                            <div
                              style={{
                                display:
                                  "flex",
                                flexWrap:
                                  "wrap",
                                gap:
                                  "5px",
                              }}
                            >

                              {matchedKeywords.map(
                                (
                                  keyword,
                                  index
                                ) => (

                                  <span
                                    key={`${keyword}-${index}`}
                                    style={{
                                      display:
                                        "inline-flex",
                                      alignItems:
                                        "center",
                                      gap:
                                        "4px",
                                      padding:
                                        "3px 7px",
                                      borderRadius:
                                        "5px",
                                      background:
                                        "rgba(255,255,255,0.08)",
                                      fontSize:
                                        "11px",
                                      whiteSpace:
                                        "nowrap",
                                    }}
                                  >

                                    <Tag
                                      size={
                                        11
                                      }
                                    />

                                    {
                                      keyword
                                    }

                                  </span>

                                )
                              )}

                            </div>

                          ) : (
                            "N/A"
                          )}

                        </td>

                        {/* -------------------------------- */}
                        {/* Jazz Participated */}
                        {/* -------------------------------- */}

                        <td>

                          <span
                            style={{
                              fontWeight:
                                600,
                            }}
                          >
                            {evaluationData.jazzParticipated
                              ? "Yes"
                              : "No"}
                          </span>

                        </td>

                        {/* -------------------------------- */}
                        {/* Number of Bidders */}
                        {/* -------------------------------- */}

                        <td>

                          <span
                            style={{
                              display:
                                "inline-flex",
                              alignItems:
                                "center",
                              gap:
                                "5px",
                              fontWeight:
                                600,
                            }}
                          >

                            <Users
                              size={
                                14
                              }
                            />

                            {
                              evaluationData.bidsReceived ??
                              "N/A"
                            }

                          </span>

                        </td>

                        {/* -------------------------------- */}
                        {/* Who Won */}
                        {/* -------------------------------- */}

                        <td>

                          <span
                            style={{
                              display:
                                "inline-flex",
                              alignItems:
                                "center",
                              gap:
                                "5px",
                              fontWeight:
                                600,
                            }}
                          >

                            <Trophy
                              size={
                                14
                              }
                            />

                            {evaluationData
                              .winners
                              .length >
                            0
                              ? evaluationData.winners.join(
                                  ", "
                                )
                              : "N/A"}

                          </span>

                        </td>

                      </tr>
                    );
                  }
                )}

              </tbody>

            </table>

          </div>
        )}

      </div>
    </div>
  );
}

export default EvaluationReports;