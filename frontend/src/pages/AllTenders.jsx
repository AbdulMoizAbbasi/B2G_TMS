import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth/AuthContext";
import "./AllTenders.css";
import {
  Search,
  ArrowUpDown,
  X,
  Download,
  RefreshCw,
  Trash2,
  Info,
} from "lucide-react";

const SCRAPER_PORTALS = [
  "Federal PPRA",
  "Punjab PPRA",
  "KP PPRA",
  "Sindh PPRA",
  "Balochistan PPRA",
];

function formatCheckpointDate(value) {
  if (!value) return "—";

  const datePart = String(value).slice(0, 10);
  const date = /^\d{4}-\d{2}-\d{2}$/.test(datePart)
    ? new Date(`${datePart}T00:00:00Z`)
    : new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
}

function formatCheckpointTime(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return "—";

  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Karachi",
  }).format(date);
}

function displayValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  return value;
}

function parseDate(value) {
  if (!value) return null;

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return null;
  }

  return date;
}

function formatDateOnly(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "—";
  }

  const day = String(
    date.getDate()
  ).padStart(2, "0");

  const month = String(
    date.getMonth() + 1
  ).padStart(2, "0");

  const year = date.getFullYear();

  return `${day}-${month}-${year}`;
}

function formatDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function getNextThreeDayRange() {
  const from = new Date();
  from.setHours(0, 0, 0, 0);

  const to = new Date(from);
  to.setDate(to.getDate() + 3);

  return {
    from: formatDateInputValue(from),
    to: formatDateInputValue(to),
  };
}

function getEstimatedValue(tender) {
  if (
    tender.estimated_value === null ||
    tender.estimated_value === undefined
  ) {
    return null;
  }

  const value = String(tender.estimated_value)
    .replace(/,/g, "")
    .replace(/[^\d.-]/g, "");

  const number = Number(value);

  return Number.isNaN(number) ? null : number;
}

function csvValue(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  if (Array.isArray(value)) {
    value = value.join(", ");
  }

  const stringValue = String(value);

  return `"${stringValue.replace(/"/g, '""')}"`;
}

function AllTenders() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const isAdmin = user?.role === "ADMIN";

  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedTenderIds, setSelectedTenderIds] =
    useState([]);

  /*
   * Column filters
   */
  const [tenderNoFilter, setTenderNoFilter] =
    useState("");

  const [tenderNameFilter, setTenderNameFilter] =
    useState("");

  const [cityFilter, setCityFilter] =
    useState("");

  const [organizationFilter, setOrganizationFilter] =
    useState("");

  const [submissionDateFrom, setSubmissionDateFrom] =
    useState("");

  const [submissionDateTo, setSubmissionDateTo] =
    useState("");

  const [estimatedValueMin, setEstimatedValueMin] =
    useState("");

  const [estimatedValueMax, setEstimatedValueMax] =
    useState("");

  const [participationStatusFilter, setParticipationStatusFilter] =
    useState("ALL");

  const [productFilter, setProductFilter] = useState("ALL");

  const productOptions = useMemo(() => {
    const products = new Set();
    tenders.forEach((tender) => {
      if (Array.isArray(tender.matched_capabilities)) {
        tender.matched_capabilities.forEach((capability) => {
          if (capability) products.add(String(capability));
        });
      }
    });
    return [...products].sort((a, b) => a.localeCompare(b));
  }, [tenders]);

  /*
   * Sorting
   */
  const [sortBy, setSortBy] =
    useState("submissionDate");

  const [sortOrder, setSortOrder] =
    useState("asc");

  /*
   * Admin scraper
   */
  const [scraperRunning, setScraperRunning] =
    useState(false);

  const [scraperMessage, setScraperMessage] =
    useState("");

  const [checkpointOpen, setCheckpointOpen] =
    useState(false);

  const [checkpointLoading, setCheckpointLoading] =
    useState(false);

  const [checkpointError, setCheckpointError] =
    useState("");

  const [scraperCheckpoint, setScraperCheckpoint] =
    useState(null);

  /*
   * Admin bulk delete
   */
  const [deleteRunning, setDeleteRunning] =
    useState(false);

  /*
   * Fetch tenders
   */
  useEffect(() => {
    const fetchTenders = async () => {
      try {
        const response = await api.get(
          "/api/tenders"
        );

        setTenders(response.data);
      } catch (err) {
        console.error(err);

        setError(
          "Failed to load tenders."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchTenders();
  }, []);

  /*
   * Check scraper status.
   *
   * Admin only.
   */
  useEffect(() => {
    if (!isAdmin) {
      setScraperRunning(false);
      return;
    }

    const checkScraperStatus = async () => {
      try {
        const response = await api.get(
          "/api/admin/scraper/status"
        );

        setScraperRunning(
          response.data.running === true
        );
      } catch (err) {
        console.error(
          "Failed to check scraper status:",
          err
        );
      }
    };

    checkScraperStatus();

    return () => {};
  }, [isAdmin]);

  /*
   * Poll scraper status while running.
   */
  useEffect(() => {
    if (!isAdmin || !scraperRunning) {
      return;
    }

    const intervalId = setInterval(
      async () => {
        try {
          const response = await api.get(
            "/api/admin/scraper/status"
          );

          setScraperRunning(
            response.data.running === true
          );
        } catch (err) {
          console.error(
            "Failed to check scraper status:",
            err
          );
        }
      },
      2000
    );

    return () => {
      clearInterval(intervalId);
    };
  }, [isAdmin, scraperRunning]);

  /*
   * Filter + sort tenders.
   */
  const filteredTenders = useMemo(() => {
    const tenderNoTerm =
      tenderNoFilter
        .trim()
        .toLowerCase();

    const tenderNameTerm =
      tenderNameFilter
        .trim()
        .toLowerCase();

    const cityTerm =
      cityFilter
        .trim()
        .toLowerCase();

    const organizationTerm =
      organizationFilter
        .trim()
        .toLowerCase();

    const result = tenders.filter(
      (tender) => {
        /*
         * Tender No filter
         */
        if (tenderNoTerm) {
          const tenderNo =
            String(
              tender.web_tender_no ?? ""
            ).toLowerCase();

          if (
            !tenderNo.includes(
              tenderNoTerm
            )
          ) {
            return false;
          }
        }

        /*
         * Tender Name filter
         */
        if (tenderNameTerm) {
          const tenderName =
            String(
              tender.tender_name ?? ""
            ).toLowerCase();

          if (
            !tenderName.includes(
              tenderNameTerm
            )
          ) {
            return false;
          }
        }

        /*
         * City filter
         */
        if (cityTerm) {
          const city =
            String(
              tender.city ?? ""
            ).toLowerCase();

          if (
            !city.includes(cityTerm)
          ) {
            return false;
          }
        }

        /*
         * Organization filter
         */
        if (organizationTerm) {
          const organization =
            String(
              tender.organization ?? ""
            ).toLowerCase();

          if (
            !organization.includes(
              organizationTerm
            )
          ) {
            return false;
          }
        }

        /*
         * Submission Date range
         *
         * Submission Date is currently
         * backed by tender.closed_date.
         */
        const submissionDate =
          parseDate(
            tender.closed_date
          );

        if (submissionDateFrom) {
          const from =
            new Date(
              submissionDateFrom
            );

          from.setHours(
            0,
            0,
            0,
            0
          );

          if (
            !submissionDate ||
            submissionDate < from
          ) {
            return false;
          }
        }

        if (submissionDateTo) {
          const to =
            new Date(
              submissionDateTo
            );

          to.setHours(
            23,
            59,
            59,
            999
          );

          if (
            !submissionDate ||
            submissionDate > to
          ) {
            return false;
          }
        }

        /*
         * Estimated Value range
         */
        const estimatedValue =
          getEstimatedValue(
            tender
          );

        if (
          estimatedValueMin !== ""
        ) {
          const min =
            Number(
              estimatedValueMin
            );

          if (
            Number.isNaN(min) ||
            estimatedValue === null ||
            estimatedValue < min
          ) {
            return false;
          }
        }

        if (
          estimatedValueMax !== ""
        ) {
          const max =
            Number(
              estimatedValueMax
            );

          if (
            Number.isNaN(max) ||
            estimatedValue === null ||
            estimatedValue > max
          ) {
            return false;
          }
        }

        /*
         * Participation Status filter
         */
        if (
          participationStatusFilter !==
          "ALL"
        ) {
          const participationStatus =
            tender.participation_status ||
            "NOT_REVIEWED";

          if (
            participationStatus !==
            participationStatusFilter
          ) {
            return false;
          }
        }

        if (productFilter !== "ALL") {
          const matchedCapabilities = Array.isArray(tender.matched_capabilities)
            ? tender.matched_capabilities.map(String)
            : [];
          if (!matchedCapabilities.includes(productFilter)) return false;
        }

        return true;
      }
    );

    /*
     * Sorting
     */
    result.sort((a, b) => {
      let valueA;
      let valueB;

      if (
        sortBy === "submissionDate"
      ) {
        valueA =
          parseDate(
            a.closed_date
          )?.getTime() ??
          Infinity;

        valueB =
          parseDate(
            b.closed_date
          )?.getTime() ??
          Infinity;
      }

      if (
        sortBy === "estimatedValue"
      ) {
        valueA =
          getEstimatedValue(a) ??
          -Infinity;

        valueB =
          getEstimatedValue(b) ??
          -Infinity;
      }

      if (sortBy === "tenderName") {
        valueA =
          String(
            a.tender_name ?? ""
          ).toLowerCase();

        valueB =
          String(
            b.tender_name ?? ""
          ).toLowerCase();

        if (
          sortOrder === "asc"
        ) {
          return valueA.localeCompare(
            valueB
          );
        }

        return valueB.localeCompare(
          valueA
        );
      }

      if (sortBy === "city") {
        valueA =
          String(
            a.city ?? ""
          ).toLowerCase();

        valueB =
          String(
            b.city ?? ""
          ).toLowerCase();

        if (
          sortOrder === "asc"
        ) {
          return valueA.localeCompare(
            valueB
          );
        }

        return valueB.localeCompare(
          valueA
        );
      }

      if (
        sortOrder === "asc"
      ) {
        return valueA - valueB;
      }

      return valueB - valueA;
    });

    return result;
  }, [
    tenders,
    tenderNoFilter,
    tenderNameFilter,
    cityFilter,
    organizationFilter,
    submissionDateFrom,
    submissionDateTo,
    estimatedValueMin,
    estimatedValueMax,
    participationStatusFilter,
    productFilter,
    sortBy,
    sortOrder,
  ]);

  /*
   * Total visible tenders.
   */
  const totalTenders =
    tenders.length;

  /*
   * Participation summary counts.
   *
   * These are calculated from the
   * participation_status returned
   * by /api/tenders.
   *
   * No participation record means
   * the backend returns NOT_REVIEWED.
   */
  const reviewPendingCount =
    useMemo(() => {
      return tenders.filter(
        (tender) =>
          tender.participation_status ===
          "NOT_REVIEWED"
      ).length;
    }, [tenders]);

  const participatingCount =
    useMemo(() => {
      return tenders.filter(
        (tender) =>
          tender.participation_status ===
          "PARTICIPATING"
      ).length;
    }, [tenders]);

  const notParticipatingCount =
    useMemo(() => {
      return tenders.filter(
        (tender) =>
          tender.participation_status ===
          "NOT_PARTICIPATING"
      ).length;
    }, [tenders]);

  /*
   * Tenders whose submission date
   * falls within the next 3 days.
   *
   * This is calculated from the full
   * tender set, not the currently
   * filtered table.
   */
  const submissionNextWeekCount =
    useMemo(() => {
      const now = new Date();

      const startOfToday =
        new Date(now);

      startOfToday.setHours(
        0,
        0,
        0,
        0
      );

      const nextWeek =
        new Date(
          startOfToday
        );

      nextWeek.setDate(
        nextWeek.getDate() + 3
      );

      nextWeek.setHours(
        23,
        59,
        59,
        999
      );

      return tenders.filter(
        (tender) => {
          const submissionDate =
            parseDate(
              tender.closed_date
            );

          if (!submissionDate) {
            return false;
          }

          return (
            submissionDate >=
              startOfToday &&
            submissionDate <=
              nextWeek
          );
        }
      ).length;
    }, [tenders]);

  /*
   * Selection
   */
  function toggleTenderSelection(
    tenderId
  ) {
    setSelectedTenderIds(
      (current) => {
        if (
          current.includes(
            tenderId
          )
        ) {
          return current.filter(
            (id) =>
              id !== tenderId
          );
        }

        return [
          ...current,
          tenderId,
        ];
      }
    );
  }

  function toggleSelectAll() {
    const filteredIds =
      filteredTenders.map(
        (tender) =>
          tender.jazzid
      );

    const allSelected =
      filteredIds.length > 0 &&
      filteredIds.every(
        (id) =>
          selectedTenderIds.includes(
            id
          )
      );

    if (allSelected) {
      setSelectedTenderIds(
        (current) =>
          current.filter(
            (id) =>
              !filteredIds.includes(
                id
              )
          )
      );
    } else {
      setSelectedTenderIds(
        (current) => [
          ...new Set([
            ...current,
            ...filteredIds,
          ]),
        ]
      );
    }
  }

  const allFilteredSelected =
    filteredTenders.length > 0 &&
    filteredTenders.every(
      (tender) =>
        selectedTenderIds.includes(
          tender.jazzid
        )
    );

  /*
   * Bulk delete.
   *
   * Admin only.
   */
  async function deleteSelectedTenders() {
    if (
      selectedTenderIds.length === 0 ||
      deleteRunning
    ) {
      return;
    }

    const confirmed =
      window.confirm(
        `Are you sure you want to delete ${selectedTenderIds.length} selected tender${
          selectedTenderIds.length ===
          1
            ? ""
            : "s"
        }?`
      );

    if (!confirmed) {
      return;
    }

    try {
      setDeleteRunning(true);

      await api.delete(
        "/api/tenders",
        {
          data: {
            jazzids:
              selectedTenderIds,
          },
        }
      );

      setTenders(
        (current) =>
          current.filter(
            (tender) =>
              !selectedTenderIds.includes(
                tender.jazzid
              )
          )
      );

      setSelectedTenderIds([]);
    } catch (err) {
      console.error(
        "Failed to delete selected tenders:",
        err
      );

      const detail =
        err.response?.data
          ?.detail;

      if (
        detail &&
        typeof detail ===
          "object"
      ) {
        window.alert(
          detail.message ||
            "Failed to delete selected tenders."
        );
      } else {
        window.alert(
          detail ||
            "Failed to delete selected tenders."
        );
      }
    } finally {
      setDeleteRunning(false);
    }
  }

  /*
   * Admin scraper.
   */
  async function runScraper() {
    if (scraperRunning) {
      return;
    }

    try {
      setScraperMessage("");

      setScraperRunning(true);

      await api.post(
        "/api/admin/run-scraper"
      );

      setScraperMessage(
        "Tender scraper started successfully."
      );
    } catch (err) {
      console.error(
        "Scraper error:",
        err
      );

      if (
        err.response?.status ===
        409
      ) {
        setScraperRunning(true);

        setScraperMessage(
          "Scraper is already running."
        );

        return;
      }

      setScraperRunning(false);

      setScraperMessage(
        "Failed to start scraper."
      );
    }
  }

  /*
   * Clear all column filters.
   */
  function clearFilters() {
    setTenderNoFilter("");
    setTenderNameFilter("");
    setCityFilter("");
    setOrganizationFilter("");
    setSubmissionDateFrom("");
    setSubmissionDateTo("");
    setEstimatedValueMin("");
    setEstimatedValueMax("");
    setParticipationStatusFilter("ALL");
    setProductFilter("ALL");
    setSortBy("submissionDate");
    setSortOrder("asc");
  }

  async function toggleCheckpointPanel() {
    if (checkpointOpen) {
      setCheckpointOpen(false);
      return;
    }

    setCheckpointOpen(true);
    setCheckpointLoading(true);
    setCheckpointError("");

    try {
      const response = await api.get(
        "/api/admin/scraper/checkpoint"
      );

      setScraperCheckpoint(response.data);
    } catch (err) {
      console.error("Failed to load scraper checkpoint:", err);
      setCheckpointError(
        "Could not load scraper checkpoint. Please try again."
      );
    } finally {
      setCheckpointLoading(false);
    }
  }

  function applySummaryFilter(filter) {
    clearFilters();

    if (filter === "NOT_REVIEWED" ||
        filter === "PARTICIPATING" ||
        filter === "NOT_PARTICIPATING") {
      setParticipationStatusFilter(filter);
      return;
    }

    if (filter === "closing-soon") {
      const range = getNextThreeDayRange();
      setSubmissionDateFrom(range.from);
      setSubmissionDateTo(range.to);
    }
  }

  const hasActiveFilters =
    tenderNoFilter ||
    tenderNameFilter ||
    cityFilter ||
    organizationFilter ||
    submissionDateFrom ||
    submissionDateTo ||
    estimatedValueMin !== "" ||
    estimatedValueMax !== "" ||
    participationStatusFilter !== "ALL" ||
    productFilter !== "ALL";

  const hasOtherFilters =
    tenderNoFilter ||
    tenderNameFilter ||
    cityFilter ||
    organizationFilter ||
    estimatedValueMin !== "" ||
    estimatedValueMax !== "" ||
    productFilter !== "ALL";

  function isSummaryFilterActive(filter) {
    if (filter === "ALL") {
      return !hasActiveFilters;
    }

    if (filter === "closing-soon") {
      const range = getNextThreeDayRange();

      return Boolean(
        !hasOtherFilters &&
        participationStatusFilter === "ALL" &&
        submissionDateFrom === range.from &&
        submissionDateTo === range.to
      );
    }

    return Boolean(
      !hasOtherFilters &&
      !submissionDateFrom &&
      !submissionDateTo &&
      participationStatusFilter === filter
    );
  }

  /*
   * Open tender detail.
   */
  function openTender(
    tenderId
  ) {
    if (!tenderId) {
      return;
    }

    navigate(
      `/tenders/${encodeURIComponent(
        tenderId
      )}`
    );
  }

  /*
   * CSV export.
   *
   * Matches the current table columns.
   */
  function downloadCSV() {
    const headers = [
      "Web Tender No",
      "Tender Name",
      "City",
      "Organization",
      "Submission Date",
      "Estimated Value",
      "Participation Status",
    ];

    const rows =
      filteredTenders.map(
        (tender) => [
          tender.web_tender_no,
          tender.tender_name,
          tender.city,
          tender.organization,
          tender.closed_date,
          tender.estimated_value,
          tender.participation_status,
        ]
      );

    const csv = [
      headers
        .map(csvValue)
        .join(","),
      ...rows.map(
        (row) =>
          row
            .map(csvValue)
            .join(",")
      ),
    ].join("\n");

    const blob =
      new Blob(
        [csv],
        {
          type:
            "text/csv;charset=utf-8;",
        }
      );

    const url =
      URL.createObjectURL(
        blob
      );

    const link =
      document.createElement(
        "a"
      );

    link.href = url;

    link.download =
      "jazzworld_tenders.csv";

    document.body.appendChild(
      link
    );

    link.click();

    document.body.removeChild(
      link
    );

    URL.revokeObjectURL(
      url
    );
  }

  if (loading) {
    return (
      <h1>
        Loading tenders...
      </h1>
    );
  }

  if (error) {
    return <h1>{error}</h1>;
  }

  return (
    <div className="tenders-page">

      {/* =========================
          PAGE HEADER
      ========================== */}

      <div className="page-header">

        <div>
          <h1>
            All Tenders
          </h1>

          <p>
            Monitor and discover
            relevant government
            procurement
            opportunities for
            JazzWorld.
          </p>
        </div>

        <div className="page-header-actions">

          {isAdmin && (
            <div className="scraper-button-group">
              <button
                type="button"
                className="run-scraper-button"
                onClick={
                  runScraper
                }
                disabled={
                  scraperRunning
                }
              >
                <RefreshCw
                  size={16}
                  className={
                    scraperRunning
                      ? "scraper-spinning"
                      : ""
                  }
                />

                {scraperRunning
                  ? "Executing..."
                  : "Run Scraper"}
              </button>

              <button
                type="button"
                className="run-scraper-button scraper-info-button"
                onClick={toggleCheckpointPanel}
                aria-label={
                  checkpointOpen
                    ? "Close scraper checkpoint"
                    : "Show scraper checkpoint"
                }
                aria-expanded={checkpointOpen}
                aria-controls="scraper-checkpoint-panel"
                title="Scraper checkpoint"
              >
                <Info size={17} />
              </button>

              {checkpointOpen && (
                <section
                  id="scraper-checkpoint-panel"
                  className="scraper-checkpoint-panel"
                  aria-label="Scraper checkpoint"
                >
                  <div className="scraper-checkpoint-header">
                    <h2>Scraper Checkpoint</h2>
                    <button
                      type="button"
                      className="scraper-checkpoint-close"
                      onClick={() => setCheckpointOpen(false)}
                      aria-label="Close scraper checkpoint"
                    >
                      <X size={16} />
                    </button>
                  </div>

                  {checkpointLoading ? (
                    <p className="scraper-checkpoint-state" role="status">
                      Loading checkpoint information...
                    </p>
                  ) : checkpointError ? (
                    <p className="scraper-checkpoint-error" role="alert">
                      {checkpointError}
                    </p>
                  ) : (
                    <div className="scraper-checkpoint-table-wrap">
                      <table className="scraper-checkpoint-table">
                        <thead>
                          <tr>
                            <th>Portal</th>
                            <th>Last Scraped Date</th>
                            <th>Last Run</th>
                          </tr>
                        </thead>
                        <tbody>
                          {SCRAPER_PORTALS.map((portal) => {
                            const checkpoint = scraperCheckpoint?.[portal];

                            return (
                              <tr key={portal}>
                                <td>{portal}</td>
                                <td>{formatCheckpointDate(checkpoint?.last_date)}</td>
                                <td>{formatCheckpointTime(checkpoint?.last_run_at)}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </section>
              )}
            </div>
          )}

          <div className="total-tenders">
            <span>
              Total Tenders
            </span>

            <strong>
              {totalTenders}
            </strong>
          </div>

        </div>

      </div>

      {/* =========================
          SCRAPER MESSAGE
      ========================== */}

      {scraperMessage && (
        <div className="scraper-message">
          {scraperMessage}
        </div>
      )}

      {/* =========================
          SUMMARY BOXES
      ========================== */}

      <div className="tender-summary-cards">

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("ALL") ? "active" : ""}`}
          onClick={() => applySummaryFilter("ALL")}
          aria-pressed={isSummaryFilterActive("ALL")}
        >
          <span>
            Total Tenders
          </span>

          <strong>
            {totalTenders}
          </strong>
        </button>

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("NOT_REVIEWED") ? "active" : ""}`}
          onClick={() => applySummaryFilter("NOT_REVIEWED")}
          aria-pressed={isSummaryFilterActive("NOT_REVIEWED")}
        >
          <span>
            Tenders Review Pending
          </span>

          <strong>
            {reviewPendingCount}
          </strong>
        </button>

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("PARTICIPATING") ? "active" : ""}`}
          onClick={() => applySummaryFilter("PARTICIPATING")}
          aria-pressed={isSummaryFilterActive("PARTICIPATING")}
        >
          <span>
            Participating
          </span>

          <strong>
            {participatingCount}
          </strong>
        </button>

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("NOT_PARTICIPATING") ? "active" : ""}`}
          onClick={() => applySummaryFilter("NOT_PARTICIPATING")}
          aria-pressed={isSummaryFilterActive("NOT_PARTICIPATING")}
        >
          <span>
            Not Participating
          </span>

          <strong>
            {notParticipatingCount}
          </strong>
        </button>

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("closing-soon") ? "active" : ""}`}
          onClick={() => applySummaryFilter("closing-soon")}
          aria-pressed={isSummaryFilterActive("closing-soon")}
        >
          <span>
            Tender Closing in Next 3 Days
          </span>

          <strong>
            {submissionNextWeekCount}
          </strong>
        </button>

      </div>

      {/* =========================
          TABLE
      ========================== */}

      <div className="table-section">

        <div className="table-header">

          <div>
            <h2>
              Tender Opportunities
            </h2>

            <span>
              {filteredTenders.length}{" "}
              matching opportunities
            </span>
          </div>

          <div className="table-header-actions">

            {hasActiveFilters && (
              <button
                type="button"
                className="clear-filters"
                onClick={
                  clearFilters
                }
              >
                Clear Filters
              </button>
            )}

            <label className="product-filter-control">
              <span>Product</span>
              <select
                value={productFilter}
                onChange={(event) => setProductFilter(event.target.value)}
                aria-label="Filter by product capability"
              >
                <option value="ALL">All products</option>
                {productOptions.map((product) => (
                  <option key={product} value={product}>{product}</option>
                ))}
              </select>
            </label>

            <div className="sort-controls">

              <ArrowUpDown
                size={16}
              />

              <span>
                Sort by
              </span>

              <select
                value={sortBy}
                onChange={(
                  event
                ) =>
                  setSortBy(
                    event.target.value
                  )
                }
              >
                <option value="submissionDate">
                  Submission Date
                </option>

                <option value="estimatedValue">
                  Estimated Value
                </option>

                <option value="tenderName">
                  Tender Name
                </option>

                <option value="city">
                  City
                </option>
              </select>

              <select
                value={sortOrder}
                onChange={(
                  event
                ) =>
                  setSortOrder(
                    event.target.value
                  )
                }
              >
                <option value="asc">
                  Ascending
                </option>

                <option value="desc">
                  Descending
                </option>
              </select>

            </div>

            <button
              type="button"
              className="download-csv-button"
              onClick={
                downloadCSV
              }
            >
              <Download
                size={16}
              />

              Download CSV
            </button>

            {isAdmin && (
              <div className="selection-actions">

                <span>
                  {
                    selectedTenderIds.length
                  }{" "}
                  selected
                </span>

                <button
                  type="button"
                  onClick={
                    toggleSelectAll
                  }
                  disabled={
                    filteredTenders.length ===
                    0
                  }
                >
                  {allFilteredSelected
                    ? "Deselect All"
                    : "Select All"}
                </button>

                {selectedTenderIds.length >
                  0 && (
                  <button
                    type="button"
                    className="delete-selected-button"
                    onClick={
                      deleteSelectedTenders
                    }
                    disabled={
                      deleteRunning
                    }
                  >
                    <Trash2
                      size={16}
                    />

                    {deleteRunning
                      ? "Deleting..."
                      : "Delete Selected"}
                  </button>
                )}

              </div>
            )}

          </div>

        </div>

        <div className="table-container">

          <table className="tenders-table">

            <colgroup>
              {isAdmin && <col className="selection-column" />}
              <col className="web-tender-no-column" />
              <col className="tender-name-column" />
              <col className="city-column" />
              <col className="organization-column" />
              <col className="submission-date-column" />
              <col className="estimated-value-column" />
              <col className="participation-status-column" />
              <col className="actions-column" />
            </colgroup>

            <thead>

              {/* =========================
                  TABLE HEADER
              ========================== */}

              <tr>

                {isAdmin && (
                  <th>
                    <input
                      type="checkbox"
                      checked={
                        allFilteredSelected
                      }
                      onChange={
                        toggleSelectAll
                      }
                      disabled={
                        filteredTenders.length ===
                        0
                      }
                      aria-label="Select all filtered tenders"
                    />
                  </th>
                )}

                <th className="web-tender-no-column">
                  Web Tender No

                  <input
                    type="text"
                    className="column-filter-input"
                    placeholder="Filter..."
                    value={
                      tenderNoFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setTenderNoFilter(
                        event.target.value
                      )
                    }
                  />
                </th>

                <th className="tender-name-column">
                  Tender Name

                  <input
                    type="text"
                    className="column-filter-input"
                    placeholder="Filter..."
                    value={
                      tenderNameFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setTenderNameFilter(
                        event.target.value
                      )
                    }
                  />
                </th>

                <th>
                  City

                  <input
                    type="text"
                    className="column-filter-input"
                    placeholder="Filter..."
                    value={
                      cityFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setCityFilter(
                        event.target.value
                      )
                    }
                  />
                </th>

                <th>
                  Organization

                  <input
                    type="text"
                    className="column-filter-input"
                    placeholder="Filter..."
                    value={
                      organizationFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setOrganizationFilter(
                        event.target.value
                      )
                    }
                  />
                </th>

                <th>
                  Submission Date

                  <div className="column-range-filter">

                    <input
                      type="date"
                      value={
                        submissionDateFrom
                      }
                      onChange={(
                        event
                      ) =>
                        setSubmissionDateFrom(
                          event.target.value
                        )
                      }
                      aria-label="Submission date from"
                    />

                    <input
                      type="date"
                      value={
                        submissionDateTo
                      }
                      onChange={(
                        event
                      ) =>
                        setSubmissionDateTo(
                          event.target.value
                        )
                      }
                      aria-label="Submission date to"
                    />

                  </div>
                </th>

                <th>
                  Estimated Value

                  <div className="column-range-filter">

                    <input
                      type="number"
                      min="0"
                      placeholder="Min"
                      value={
                        estimatedValueMin
                      }
                      onChange={(
                        event
                      ) =>
                        setEstimatedValueMin(
                          event.target.value
                        )
                      }
                    />

                    <input
                      type="number"
                      min="0"
                      placeholder="Max"
                      value={
                        estimatedValueMax
                      }
                      onChange={(
                        event
                      ) =>
                        setEstimatedValueMax(
                          event.target.value
                        )
                      }
                    />

                  </div>
                </th>

                <th>
                  Participation Status

                  <select
                    className="column-filter-input"
                    value={
                      participationStatusFilter
                    }
                    onChange={(
                      event
                    ) =>
                      setParticipationStatusFilter(
                        event.target.value
                      )
                    }
                  >
                    <option value="ALL">
                      All
                    </option>

                    <option value="NOT_REVIEWED">
                      Not Reviewed
                    </option>

                    <option value="PARTICIPATING">
                      Participating
                    </option>

                    <option value="NOT_PARTICIPATING">
                      Not Participating
                    </option>
                  </select>
                </th>

                <th>
                  Actions
                </th>

              </tr>

            </thead>

            <tbody>

              {filteredTenders.map(
                (tender) => (
                  <tr
                    key={
                      tender.jazzid
                    }
                  >

                    {isAdmin && (
                      <td>
                        <input
                          type="checkbox"
                          checked={selectedTenderIds.includes(
                            tender.jazzid
                          )}
                          onChange={() =>
                            toggleTenderSelection(
                              tender.jazzid
                            )
                          }
                          aria-label={`Select tender ${
                            tender.web_tender_no ||
                            tender.jazzid
                          }`}
                        />
                      </td>
                    )}

                    <td className="web-tender-no-column">
                      <button
                        type="button"
                        className="tender-link"
                        onClick={() =>
                          openTender(
                            tender.jazzid
                          )
                        }
                      >
                        {displayValue(
                          tender.web_tender_no
                        )}
                      </button>
                    </td>

                    <td className="tender-name">

                      <button
                        type="button"
                        className="tender-link tender-name-link"
                        onClick={() =>
                          openTender(
                            tender.jazzid
                          )
                        }
                      >
                        {displayValue(
                          tender.tender_name
                        )}
                      </button>

                    </td>

                    <td>
                      {displayValue(
                        tender.city
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.organization
                      )}
                    </td>

                    <td>
                      {formatDateOnly(
                        tender.closed_date
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.estimated_value
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.participation_status
                      )}
                    </td>

                    <td>
                      <button
                        type="button"
                        className="view-tender-button"
                        onClick={() =>
                          openTender(
                            tender.jazzid
                          )
                        }
                      >
                        View
                      </button>
                    </td>

                  </tr>
                )
              )}

            </tbody>

          </table>

          {filteredTenders.length ===
            0 && (
            <div className="empty-state">

              <h3>
                No tenders found
              </h3>

              <p>
                Try changing your
                filters.
              </p>

              <button
                onClick={
                  clearFilters
                }
                className="clear-empty-button"
              >
                Clear Filters
              </button>

            </div>
          )}

        </div>

      </div>

    </div>
  );
}

export default AllTenders;
