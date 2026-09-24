import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  FileText,
  Calendar,
  ClipboardCheck,
  ExternalLink,
  Tag,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

function EvaluationDetail() {
  const { tenderNo } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // ---------------------------------------------------------
  // Load tender + all evaluation reports
  // ---------------------------------------------------------
  const loadEvaluationData = async () => {
    try {
      setLoading(true);
      setError("");

      const response = await axios.get(
        `http://127.0.0.1:8000/api/evaluations/${encodeURIComponent(
          tenderNo
        )}`
      );

      setData(response.data);
    } catch (err) {
      console.error("Failed to load evaluation details:", err);

      setError(
        err.response?.data?.detail ||
          "Failed to load evaluation details."
      );
    } finally {
      setLoading(false);
    }
  };

  // ---------------------------------------------------------
  // Load data whenever tender number changes
  // ---------------------------------------------------------
  useEffect(() => {
    loadEvaluationData();
  }, [tenderNo]);

  // ---------------------------------------------------------
  // Data
  //
  // IMPORTANT:
  // All calculations/hooks are before conditional returns.
  // ---------------------------------------------------------
  const tenderData = data?.tender_data || null;

  const evaluations = Array.isArray(data?.evaluations)
    ? data.evaluations
    : [];

  // ---------------------------------------------------------
  // Tender name
  //
  // Comes from relevant_tenders.json only.
  // ---------------------------------------------------------
  const tenderName =
    tenderData?.["Tender Title"] ||
    tenderData?.["tender_details"] ||
    tenderData?.["Name"] ||
    "N/A";

  // ---------------------------------------------------------
  // Relevance
  // ---------------------------------------------------------
  const relevance = tenderData?.relevance?.keyword_score;

  // ---------------------------------------------------------
  // Matched keywords
  // ---------------------------------------------------------
  const matchedKeywords = Array.isArray(
    tenderData?.relevance?.matched_keywords
  )
    ? tenderData.relevance.matched_keywords
    : [];

  // ---------------------------------------------------------
  // Aggregate OCR information across
  // all evaluation reports
  // ---------------------------------------------------------
  const evaluationSummary = useMemo(() => {
    let bidsReceived = null;

    const bidders = [];
    const winners = [];

    evaluations.forEach((evaluation) => {
      const ocr = evaluation?.ocr_data || {};

      // -----------------------------------------------------
      // Number of bids
      // -----------------------------------------------------
      if (
        bidsReceived === null &&
        ocr?.bids_received !== null &&
        ocr?.bids_received !== undefined
      ) {
        bidsReceived = ocr.bids_received;
      }

      // -----------------------------------------------------
      // Bidder names
      // -----------------------------------------------------
      if (Array.isArray(ocr?.bid_evaluations)) {
        ocr.bid_evaluations.forEach((bid) => {
          const bidder = bid?.bidder;

          if (
            bidder &&
            !bidders.some(
              (existing) =>
                existing.toLowerCase() === bidder.toLowerCase()
            )
          ) {
            bidders.push(bidder);
          }
        });
      }

      // -----------------------------------------------------
      // Winners
      // -----------------------------------------------------
      const winner =
        ocr?.lowest_evaluated_bidder?.name;

      if (
        winner &&
        !winners.some(
          (existing) =>
            existing.toLowerCase() === winner.toLowerCase()
        )
      ) {
        winners.push(winner);
      }
    });

    // -------------------------------------------------------
    // Determine whether Jazz participated
    // -------------------------------------------------------
    const jazzParticipated = bidders.some((bidder) =>
      bidder.toLowerCase().includes("jazz")
    );

    return {
      bidsReceived,
      bidders,
      winners,
      jazzParticipated,
    };
  }, [evaluations]);

  // ---------------------------------------------------------
  // Tender field helper
  // ---------------------------------------------------------
  const getTenderField = (...fields) => {
    for (const field of fields) {
      if (
        field !== null &&
        field !== undefined &&
        String(field).trim() !== ""
      ) {
        return field;
      }
    }

    return "N/A";
  };

  // ---------------------------------------------------------
  // Loading
  // ---------------------------------------------------------
  if (loading) {
    return (
      <div className="page-container">
        <div className="evaluation-detail-loading">
          <RefreshCw size={30} className="spin" />

          <h2>Loading Evaluation Details</h2>

          <p>
            Please wait while the tender and evaluation
            reports are loaded.
          </p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------
  // Error
  // ---------------------------------------------------------
  if (error) {
    return (
      <div className="page-container">
        <button
          type="button"
          className="evaluation-back-btn"
          onClick={() => navigate("/evaluations")}
        >
          <ArrowLeft size={17} />
          Back to Evaluation Reports
        </button>

        <div className="evaluation-detail-error">
          <AlertCircle size={30} />

          <h2>Evaluation Details Not Found</h2>

          <p>{error}</p>
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------
  // No data
  // ---------------------------------------------------------
  if (!data) {
    return null;
  }

  return (
    <div className="page-container evaluation-detail-page">

      {/* ================================================== */}
      {/* Back */}
      {/* ================================================== */}

      <button
        type="button"
        className="evaluation-back-btn"
        onClick={() => navigate("/evaluations")}
      >
        <ArrowLeft size={17} />
        Back to Evaluation Reports
      </button>

      {/* ================================================== */}
      {/* Header */}
      {/* ================================================== */}

      <div className="evaluation-detail-header">
        <div>
          <div className="evaluation-detail-label">
            Evaluation Details
          </div>

          <h1>{tenderName}</h1>

          <p>
            Tender No.{" "}
            <strong>
              {data.tender_no || tenderNo || "N/A"}
            </strong>
          </p>
        </div>

        <div className="evaluation-detail-actions">
          <button
            type="button"
            className="evaluation-pdf-btn"
            onClick={loadEvaluationData}
            disabled={loading}
          >
            <RefreshCw
              size={17}
              className={loading ? "spin" : ""}
            />

            Refresh
          </button>
        </div>
      </div>

      {/* ================================================== */}
      {/* Tender Summary */}
      {/* ================================================== */}

      <div className="evaluation-detail-grid">

        {/* ------------------------------------------------ */}
        {/* Relevance */}
        {/* ------------------------------------------------ */}

        <div className="evaluation-detail-card">
          <div className="evaluation-detail-card-header">
            <Tag size={18} />
            <h2>Relevance</h2>
          </div>

          <div className="evaluation-info-grid">

            <div>
              <span>Keyword Score</span>

              <strong>
                {typeof relevance === "number"
                  ? relevance
                  : "N/A"}
              </strong>
            </div>

            <div>
              <span>Matched Keywords</span>

              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "6px",
                  marginTop: "6px",
                }}
              >
                {matchedKeywords.length > 0 ? (
                  matchedKeywords.map((keyword, index) => (
                    <span
                      key={`${keyword}-${index}`}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "4px",
                        padding: "4px 8px",
                        borderRadius: "5px",
                        background:
                          "rgba(255,255,255,0.08)",
                        fontSize: "12px",
                      }}
                    >
                      <Tag size={11} />
                      {keyword}
                    </span>
                  ))
                ) : (
                  <strong>N/A</strong>
                )}
              </div>
            </div>

          </div>
        </div>

        {/* ------------------------------------------------ */}
        {/* Evaluation Summary */}
        {/* ------------------------------------------------ */}

        <div className="evaluation-detail-card">
          <div className="evaluation-detail-card-header">
            <ClipboardCheck size={18} />
            <h2>Evaluation Summary</h2>
          </div>

          <div className="evaluation-info-grid">

            <div>
              <span>Jazz Participated</span>

              <strong>
                {evaluationSummary.jazzParticipated
                  ? "Yes"
                  : "No"}
              </strong>
            </div>

            <div>
              <span>No. of Bidders</span>

              <strong>
                {evaluationSummary.bidsReceived ?? "N/A"}
              </strong>
            </div>

            <div>
              <span>Who Won</span>

              <strong>
                {evaluationSummary.winners.length > 0
                  ? evaluationSummary.winners.join(", ")
                  : "N/A"}
              </strong>
            </div>

            <div>
              <span>Evaluation Reports</span>

              <strong>{evaluations.length}</strong>
            </div>

          </div>
        </div>

      </div>

      {/* ================================================== */}
      {/* Complete Tender Information */}
      {/* ================================================== */}

      <div className="evaluation-detail-card evaluation-full-card">

        <div className="evaluation-detail-card-header">
          <FileText size={18} />
          <h2>Tender Information</h2>
        </div>

        {tenderData ? (
          <div className="evaluation-info-grid">

            <div>
              <span>Tender No.</span>

              <strong>
                {getTenderField(
                  tenderData["web_tender_no"],
                  tenderData["TSENumber"],
                  tenderData["tender_number"],
                  data.tender_no
                )}
              </strong>
            </div>

            <div>
              <span>Tender Title</span>

              <strong>
                {getTenderField(
                  tenderData["Tender Title"],
                  tenderData["tender_details"],
                  tenderData["Name"]
                )}
              </strong>
            </div>

            <div>
              <span>Organization</span>

              <strong>
                {getTenderField(
                  tenderData["Organization Name"],
                  tenderData["organization_details"],
                  tenderData["Agency"]
                )}
              </strong>
            </div>

            <div>
              <span>Office</span>

              <strong>
                {getTenderField(
                  tenderData["Office Name"]
                )}
              </strong>
            </div>

            <div>
              <span>Office Address</span>

              <strong>
                {getTenderField(
                  tenderData["Office Address"]
                )}
              </strong>
            </div>

            <div>
              <span>City</span>

              <strong>
                {getTenderField(
                  tenderData["City"],
                  tenderData["Location"]
                )}
              </strong>
            </div>

            <div>
              <span>Contact Person</span>

              <strong>
                {getTenderField(
                  tenderData["Contact Person"]
                )}
              </strong>
            </div>

            <div>
              <span>Contact Email</span>

              <strong>
                {getTenderField(
                  tenderData["Contact Email"]
                )}
              </strong>
            </div>

            <div>
              <span>Contact Phone</span>

              <strong>
                {getTenderField(
                  tenderData["Contact Phone"]
                )}
              </strong>
            </div>

            <div>
              <span>Tender Type</span>

              <strong>
                {getTenderField(
                  tenderData["Tender Type"]
                )}
              </strong>
            </div>

            <div>
              <span>Procurement Category</span>

              <strong>
                {getTenderField(
                  tenderData["Procurement Category"]
                )}
              </strong>
            </div>

            <div>
              <span>Procurement Procedure</span>

              <strong>
                {getTenderField(
                  tenderData["Procurement Procedure"]
                )}
              </strong>
            </div>

            <div>
              <span>Sector</span>

              <strong>
                {getTenderField(
                  tenderData["Sector"]
                )}
              </strong>
            </div>

            <div>
              <span>Tender Nature</span>

              <strong>
                {getTenderField(
                  tenderData["Tender Nature"]
                )}
              </strong>
            </div>

            <div>
              <span>Advertisement Date</span>

              <strong>
                {getTenderField(
                  tenderData["Advertisement Date"],
                  tenderData["advertised_date"]
                )}
              </strong>
            </div>

            <div>
              <span>Closing Date & Time</span>

              <strong>
                {getTenderField(
                  tenderData["Closing Date & Time"],
                  tenderData["closing_date"]
                )}
              </strong>
            </div>

            <div>
              <span>Opening Time</span>

              <strong>
                {getTenderField(
                  tenderData["Opening Time"]
                )}
              </strong>
            </div>

            <div>
              <span>Bid Security</span>

              <strong>
                {getTenderField(
                  tenderData["Bid Security"]
                )}
              </strong>
            </div>

            <div>
              <span>Bid Validity</span>

              <strong>
                {getTenderField(
                  tenderData["Bid Validity"]
                )}
              </strong>
            </div>

            <div>
              <span>Method</span>

              <strong>
                {getTenderField(
                  tenderData["Method"]
                )}
              </strong>
            </div>

            <div>
              <span>Workflow Type</span>

              <strong>
                {getTenderField(
                  tenderData["Workflow Type"]
                )}
              </strong>
            </div>

          </div>
        ) : (
          <div className="evaluation-no-tender-data">

            <FileText size={24} />

            <div>
              <strong>
                Original tender information unavailable
              </strong>

              <p>
                This tender is not currently available
                in the relevant tender records.
              </p>
            </div>

          </div>
        )}

      </div>

      {/* ================================================== */}
      {/* Evaluation Documents */}
      {/* ================================================== */}

      <div className="evaluation-detail-card evaluation-full-card">

        <div className="evaluation-detail-card-header">
          <FileText size={18} />
          <h2>Evaluation Documents</h2>
        </div>

        {evaluations.length === 0 ? (
          <div className="evaluation-no-bids">
            No evaluation reports found for this tender.
          </div>
        ) : (
          <div className="evaluation-document-list">

            {evaluations.map((evaluation) => {
              const scrapedData =
                evaluation?.scraped_data || {};

              const ocr =
                evaluation?.ocr_data || {};

              return (
                <div
                  key={evaluation.evaluation_id}
                  className="evaluation-document-card"
                >

                  {/* --------------------------------------- */}
                  {/* Document Icon */}
                  {/* --------------------------------------- */}

                  <div className="evaluation-document-icon">
                    <FileText size={22} />
                  </div>

                  {/* --------------------------------------- */}
                  {/* Main Information */}
                  {/* --------------------------------------- */}

                  <div className="evaluation-document-content">

                    <div className="evaluation-document-title">
                      Evaluation{" "}
                      <strong>
                        {evaluation.evaluation_id}
                      </strong>
                    </div>

                    <div className="evaluation-document-meta">

                      <span className="evaluation-document-meta-item">
                        <Calendar size={14} />

                        {scrapedData.evaluation_date ||
                          "Date unavailable"}
                      </span>

                      {ocr.procurement_method && (
                        <span className="evaluation-document-meta-item">
                          <ClipboardCheck size={14} />

                          {ocr.procurement_method}
                        </span>
                      )}

                    </div>

                  </div>

                  {/* --------------------------------------- */}
                  {/* Right Side Actions */}
                  {/* --------------------------------------- */}

                  <div className="evaluation-document-actions">

                    {evaluation.pdf_path ? (
                      <span className="evaluation-pdf-badge available">
                        <CheckCircle2 size={15} />
                        PDF Available
                      </span>
                    ) : (
                      <span className="evaluation-pdf-badge unavailable">
                        <AlertCircle size={15} />
                        PDF Unavailable
                      </span>
                    )}

                    {evaluation.pdf_path && (
                      <a
                        href={`http://127.0.0.1:8000/api/evaluations/${encodeURIComponent(
                          evaluation.evaluation_id
                        )}/pdf`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="evaluation-open-btn"
                      >
                        <FileText size={15} />
                        Open PDF
                        <ExternalLink size={14} />
                      </a>
                    )}

                  </div>

                </div>
              );
            })}

          </div>
        )}

      </div>

      {/* ================================================== */}
      {/* OCR Evaluation Details */}
      {/* ================================================== */}

      {evaluations.map((evaluation) => {
        const ocr =
          evaluation?.ocr_data || {};

        const bidEvaluations =
          Array.isArray(ocr.bid_evaluations)
            ? ocr.bid_evaluations
            : [];

        return (
          <div
            key={`ocr-${evaluation.evaluation_id}`}
            className="evaluation-detail-card evaluation-full-card"
          >

            <div className="evaluation-detail-card-header">

              <ClipboardCheck size={18} />

              <h2>
                OCR Evaluation Details —{" "}
                {evaluation.evaluation_id}
              </h2>

            </div>

            <div className="evaluation-info-grid">

              <div>
                <span>Evaluation ID</span>

                <strong>
                  {evaluation.evaluation_id}
                </strong>
              </div>

              <div>
                <span>Evaluation Date</span>

                <strong>
                  {evaluation?.scraped_data
                    ?.evaluation_date || "N/A"}
                </strong>
              </div>

              <div>
                <span>Procuring Agency</span>

                <strong>
                  {ocr.procuring_agency || "N/A"}
                </strong>
              </div>

              <div>
                <span>Procurement Method</span>

                <strong>
                  {ocr.procurement_method || "N/A"}
                </strong>
              </div>

              <div>
                <span>Procurement Title</span>

                <strong>
                  {ocr.procurement_title || "N/A"}
                </strong>
              </div>

              <div>
                <span>Tender Inquiry No.</span>

                <strong>
                  {ocr.tender_inquiry_no || "N/A"}
                </strong>
              </div>

              <div>
                <span>PPRA Ref. No.</span>

                <strong>
                  {ocr.ppra_ref_no || "N/A"}
                </strong>
              </div>

              <div>
                <span>Bid Closing</span>

                <strong>
                  {ocr.bid_closing || "N/A"}
                </strong>
              </div>

              <div>
                <span>Bid Opening</span>

                <strong>
                  {ocr.bid_opening || "N/A"}
                </strong>
              </div>

              <div>
                <span>Bids Received</span>

                <strong>
                  {ocr.bids_received ?? "N/A"}
                </strong>
              </div>

              <div>
                <span>Financial Bid Opening</span>

                <strong>
                  {ocr.financial_bid_opening || "N/A"}
                </strong>
              </div>

              <div>
                <span>Evaluation Criteria</span>

                <strong>
                  {ocr.evaluation_criteria || "N/A"}
                </strong>
              </div>

              <div>
                <span>Additional Information</span>

                <strong>
                  {ocr.additional_information || "N/A"}
                </strong>
              </div>

            </div>

            {/* --------------------------------------------- */}
            {/* Bid Evaluation */}
            {/* --------------------------------------------- */}

            <div
              style={{
                marginTop: "24px",
              }}
            >

              <h3
                style={{
                  marginBottom: "14px",
                }}
              >
                Bid Evaluation
              </h3>

              {bidEvaluations.length > 0 ? (
                <div className="evaluation-bid-table-wrapper">

                  <table className="evaluation-bid-table">

                    <thead>
                      <tr>
                        <th>Bidder</th>

                        <th>
                          Technically Qualified
                        </th>

                        <th>
                          Contract Price
                        </th>

                        <th>
                          Delivery Period
                        </th>
                      </tr>
                    </thead>

                    <tbody>

                      {bidEvaluations.map(
                        (bid, index) => (
                          <tr key={index}>

                            <td>
                              {bid.bidder || "N/A"}
                            </td>

                            <td>
                              {bid.technically_qualified ||
                                "N/A"}
                            </td>

                            <td>
                              {bid.contract_price ||
                                "N/A"}
                            </td>

                            <td>
                              {bid.delivery_period ||
                                "N/A"}
                            </td>

                          </tr>
                        )
                      )}

                    </tbody>

                  </table>

                </div>
              ) : (
                <div className="evaluation-no-bids">
                  No structured bid evaluation data
                  was extracted from this evaluation report.
                </div>
              )}

            </div>

          </div>
        );
      })}

    </div>
  );
}

export default EvaluationDetail;