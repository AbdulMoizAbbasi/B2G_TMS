import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../api";
import { useAuth } from "../auth/AuthContext";
import formatEstimatedValue from "../utils/formatEstimatedValue";
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

const PARTICIPATION_OPTIONS = [
  { value: "NOT_REVIEWED", label: "Not Reviewed" },
  { value: "ENGAGING", label: "Engaging" },
  { value: "PARTICIPATED", label: "Participated" },
  { value: "NOT_PARTICIPATING", label: "Not Participating" },
];

const SOURCE_OPTIONS = [
  { value: "Federal PPRA", label: "Federal" },
  { value: "Punjab PPRA", label: "Punjab" },
  { value: "KP PPRA", label: "KP" },
  { value: "Balochistan PPRA", label: "Balochistan" },
  { value: "Sindh PPRA", label: "Sindh" },
];

const REGION_OPTIONS = ["North1", "North2", "Central", "South"].map((value) => ({ value, label: value }));
const PRODUCT_OPTIONS = ["GSM", "CMT", "Fixed Connectivity", "CPaaS", "SI", "Devices", "M2M", "GPU"]
  .map((value) => ({ value, label: value }));

function MultiSelectFilter({ id, label, placeholder, options, selected, onChange, compact = false, openedFilter, setOpenedFilter }) {
  const open = openedFilter === id;
  const [menuPosition, setMenuPosition] = useState(null);
  const triggerRef = useRef(null);
  const toggle = (value) => onChange(selected.includes(value)
    ? selected.filter((item) => item !== value)
    : [...selected, value]);

  useEffect(() => {
    if (!open) return undefined;
    const updatePosition = () => {
      if (!triggerRef.current) return;
      const rect = triggerRef.current.getBoundingClientRect();
      const width = Math.min(Math.max(rect.width, 190), window.innerWidth - 16);
      const top = window.innerHeight - rect.bottom < 240 ? Math.max(8, rect.top - 234) : rect.bottom + 4;
      setMenuPosition({ left: Math.max(8, Math.min(rect.left, window.innerWidth - width - 8)), top, width });
    };
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open]);

  return (
    <div className={`tender-multi-filter${compact ? " tender-multi-filter-compact" : ""}`}>
      <button ref={triggerRef} type="button" className="tender-multi-filter-trigger column-filter-input" onClick={() => setOpenedFilter(open ? null : id)} aria-expanded={open} aria-label={`Filter by ${label.toLowerCase()}`}>
        {selected.length === 1 ? (options.find((option) => option.value === selected[0])?.label ?? selected[0]) : selected.length ? `${selected.length} selected` : placeholder}
      </button>
      {open && menuPosition && createPortal(<div className="tender-multi-filter-options" style={{ position: "fixed", left: menuPosition.left, top: menuPosition.top, width: menuPosition.width }}>
        <div className="tender-multi-filter-heading"><span>{label}</span><button type="button" onClick={() => onChange([])} disabled={!selected.length}>Clear</button></div>
        {options.length ? options.map((option) => (
          <label key={option.value}>
            <input type="checkbox" checked={selected.includes(option.value)} onChange={() => toggle(option.value)} />
            <span>{option.label}</span>
          </label>
        )) : <span className="tender-multi-filter-empty">No options available</span>}
      </div>, document.body)}
    </div>
  );
}

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

function participationLabel(status) {
  if (status === "ENGAGING" || status === "PARTICIPATING") return "Engaging";
  if (status === "PARTICIPATED") return "Participated";
  if (status === "NOT_PARTICIPATING") return "Not Participating";
  if (status === "NOT_REVIEWED") return "Not Reviewed";
  return displayValue(status);
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

function readTenderStateFromSearch(search) {
  const params = new URLSearchParams(search);
  const parsedPage = Number.parseInt(params.get("page"), 10);
  const requestedSortBy = params.get("sort_by");
  const requestedSortOrder = params.get("sort_order");
  const getValues = (key, legacyKey) => {
    const values = params.getAll(key);
    const legacy = legacyKey ? params.get(legacyKey) : null;
    return (values.length ? values : legacy ? [legacy] : []).filter((value) => value && value !== "ALL");
  };

  return {
    page: Number.isInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1,
    tenderNoFilter: params.get("tender_no") || "",
    tenderNameFilter: params.get("tender_name") || "",
    cityFilter: params.get("city") || "",
    organizationFilter: params.get("organization") || "",
    submissionDateFrom: params.get("submission_date_from") || "",
    submissionDateTo: params.get("submission_date_to") || "",
    estimatedValueMin: params.get("estimated_value_min") || "",
    estimatedValueMax: params.get("estimated_value_max") || "",
    participationStatusFilter: getValues("participation_status", "participation"),
    productFilter: getValues("product"),
    sourceFilter: getValues("source"),
    regionFilter: getValues("region"),
    scoreMin: params.get("score_min") || "",
    scoreMax: params.get("score_max") || "",
    advertisedDateFrom: params.get("advertised_date_from") || "",
    advertisedDateTo: params.get("advertised_date_to") || "",
    sortBy: ["submissionDate", "estimatedValue", "tenderName", "city"].includes(requestedSortBy)
      ? requestedSortBy
      : "submissionDate",
    sortOrder: ["asc", "desc"].includes(requestedSortOrder)
      ? requestedSortOrder
      : "desc",
  };
}

function setArrayIfChanged(setter, nextValues) {
  setter((current) => current.length === nextValues.length && current.every((value, index) => value === nextValues[index])
    ? current
    : nextValues);
}

function AllTenders() {
  const navigate = useNavigate();
  const location = useLocation();
  const [initialTenderState] = useState(() =>
    readTenderStateFromSearch(location.search)
  );
  const { user } = useAuth();

  const isAdmin = user?.role === "ADMIN";

  const [tenders, setTenders] = useState([]);
  const [page, setPage] = useState(initialTenderState.page);
  const [refreshKey, setRefreshKey] = useState(0);
  const [pagination, setPagination] = useState({ total: 0, total_pages: 1 });
  const [summary, setSummary] = useState({ total: 0, review_pending: 0, participating: 0, participated: 0, not_participating: 0, closing_soon: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedTenderIds, setSelectedTenderIds] =
    useState([]);
  const [openedFilter, setOpenedFilter] = useState(null);

  /*
   * Column filters
   */
  const [tenderNoFilter, setTenderNoFilter] =
    useState(initialTenderState.tenderNoFilter);

  const [tenderNameFilter, setTenderNameFilter] =
    useState(initialTenderState.tenderNameFilter);

  const [cityFilter, setCityFilter] =
    useState(initialTenderState.cityFilter);

  const [organizationFilter, setOrganizationFilter] =
    useState(initialTenderState.organizationFilter);

  const [submissionDateFrom, setSubmissionDateFrom] =
    useState(initialTenderState.submissionDateFrom);

  const [submissionDateTo, setSubmissionDateTo] =
    useState(initialTenderState.submissionDateTo);

  const [estimatedValueMin, setEstimatedValueMin] =
    useState(initialTenderState.estimatedValueMin);

  const [estimatedValueMax, setEstimatedValueMax] =
    useState(initialTenderState.estimatedValueMax);

  const [participationStatusFilter, setParticipationStatusFilter] =
    useState(initialTenderState.participationStatusFilter);

  const [productFilter, setProductFilter] = useState(initialTenderState.productFilter);
  const [sourceFilter, setSourceFilter] = useState(initialTenderState.sourceFilter);
  const [regionFilter, setRegionFilter] = useState(initialTenderState.regionFilter);
  const [scoreMin, setScoreMin] = useState(initialTenderState.scoreMin);
  const [scoreMax, setScoreMax] = useState(initialTenderState.scoreMax);
  const [advertisedDateFrom, setAdvertisedDateFrom] = useState(initialTenderState.advertisedDateFrom);
  const [advertisedDateTo, setAdvertisedDateTo] = useState(initialTenderState.advertisedDateTo);
  /*
   * Sorting
   */
  const [sortBy, setSortBy] =
    useState(initialTenderState.sortBy);

  const [sortOrder, setSortOrder] =
    useState(initialTenderState.sortOrder);

  const updateQueryState = (setter, value) => {
    setter(value);
    setPage(1);
  };

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const setOrRemove = (key, value) => {
      if (value === "" || value === null || value === undefined || value === "ALL") {
        params.delete(key);
      } else {
        params.set(key, String(value));
      }
    };
    const setRepeated = (key, values, enabled = true) => {
      params.delete(key);
      if (enabled) values.forEach((value) => params.append(key, value));
    };

    params.set("page", String(page));
    setOrRemove("tender_no", tenderNoFilter);
    setOrRemove("tender_name", tenderNameFilter);
    setOrRemove("city", cityFilter);
    setOrRemove("organization", organizationFilter);
    setOrRemove("submission_date_from", submissionDateFrom);
    setOrRemove("submission_date_to", submissionDateTo);
    setOrRemove("estimated_value_min", estimatedValueMin);
    setOrRemove("estimated_value_max", estimatedValueMax);
    params.delete("participation");
    setRepeated("participation_status", participationStatusFilter);
    setRepeated("product", productFilter);
    setRepeated("source", sourceFilter, isAdmin);
    setRepeated("region", regionFilter, isAdmin);
    setOrRemove("score_min", isAdmin ? scoreMin : "");
    setOrRemove("score_max", isAdmin ? scoreMax : "");
    setOrRemove("advertised_date_from", isAdmin ? advertisedDateFrom : "");
    setOrRemove("advertised_date_to", isAdmin ? advertisedDateTo : "");
    params.set("sort_by", sortBy);
    params.set("sort_order", sortOrder);

    const search = params.toString();
    const nextSearch = search ? `?${search}` : "";
    if (nextSearch !== location.search) {
      navigate(
        { pathname: location.pathname, search: nextSearch },
        { replace: true }
      );
    }
  }, [
    page, tenderNoFilter, tenderNameFilter, cityFilter, organizationFilter,
    submissionDateFrom, submissionDateTo, estimatedValueMin, estimatedValueMax,
    participationStatusFilter, productFilter, sourceFilter, regionFilter, scoreMin, scoreMax,
    advertisedDateFrom, advertisedDateTo, sortBy, sortOrder,
    location.pathname, location.search, navigate,
  ]);

  useEffect(() => {
    const restored = readTenderStateFromSearch(location.search);
    setPage(restored.page);
    setTenderNoFilter(restored.tenderNoFilter);
    setTenderNameFilter(restored.tenderNameFilter);
    setCityFilter(restored.cityFilter);
    setOrganizationFilter(restored.organizationFilter);
    setSubmissionDateFrom(restored.submissionDateFrom);
    setSubmissionDateTo(restored.submissionDateTo);
    setEstimatedValueMin(restored.estimatedValueMin);
    setEstimatedValueMax(restored.estimatedValueMax);
    setArrayIfChanged(setParticipationStatusFilter, restored.participationStatusFilter);
    setArrayIfChanged(setProductFilter, restored.productFilter);
    setArrayIfChanged(setSourceFilter, restored.sourceFilter);
    setArrayIfChanged(setRegionFilter, restored.regionFilter);
    setScoreMin(restored.scoreMin);
    setScoreMax(restored.scoreMax);
    setAdvertisedDateFrom(restored.advertisedDateFrom);
    setAdvertisedDateTo(restored.advertisedDateTo);
    setSortBy(restored.sortBy);
    setSortOrder(restored.sortOrder);
  }, [location.search]);

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
        const params = new URLSearchParams();
        const scalarParams = {
          page, page_size: 10, tender_no: tenderNoFilter, tender_name: tenderNameFilter,
          city: cityFilter, organization: organizationFilter,
          submission_date_from: submissionDateFrom, submission_date_to: submissionDateTo,
          estimated_value_min: estimatedValueMin, estimated_value_max: estimatedValueMax,
          sort_by: sortBy, sort_order: sortOrder,
          score_min: isAdmin ? scoreMin : "", score_max: isAdmin ? scoreMax : "",
          advertised_date_from: isAdmin ? advertisedDateFrom : "",
          advertised_date_to: isAdmin ? advertisedDateTo : "",
        };
        Object.entries(scalarParams).forEach(([key, value]) => {
          if (value !== "" && value !== undefined && value !== null) params.append(key, String(value));
        });
        participationStatusFilter.forEach((value) => params.append("participation_status", value));
        productFilter.forEach((value) => params.append("product", value));
        if (isAdmin) sourceFilter.forEach((value) => params.append("source", value));
    if (isAdmin) regionFilter.forEach((value) => params.append("region", value));

        const response = await api.get(`/api/tenders?${params.toString()}`);

        setTenders(response.data.items || []);
        setPagination(response.data.pagination || { total: 0, total_pages: 1 });
        setSummary(response.data.summary || { total: 0, review_pending: 0, participating: 0, participated: 0, not_participating: 0, closing_soon: 0 });
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
  }, [page, tenderNoFilter, tenderNameFilter, cityFilter, organizationFilter, submissionDateFrom, submissionDateTo, estimatedValueMin, estimatedValueMax, participationStatusFilter, productFilter, sourceFilter, regionFilter, scoreMin, scoreMax, advertisedDateFrom, advertisedDateTo, sortBy, sortOrder, refreshKey, isAdmin]);

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
      120000
    );

    return () => {
      clearInterval(intervalId);
    };
  }, [isAdmin, scraperRunning]);

  const filteredTenders = tenders;

  /*
   * Total visible tenders.
   */
  const totalTenders = summary.total ?? pagination.total ?? 0;

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
  const reviewPendingCount = summary.review_pending ?? 0;

  const participatingCount = summary.engaging ?? summary.participating ?? 0;
  const participatedCount = summary.participated ?? 0;

  const notParticipatingCount = summary.not_participating ?? 0;

  const submissionNextWeekCount = summary.closing_soon ?? 0;

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

      setPage(1);
      setRefreshKey((current) => current + 1);

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
    setParticipationStatusFilter([]);
    setProductFilter([]);
    if (isAdmin) setSourceFilter([]);
    setRegionFilter([]);
    setScoreMin("");
    setScoreMax("");
    setAdvertisedDateFrom("");
    setAdvertisedDateTo("");
    setSortBy("submissionDate");
    setSortOrder("desc");
    setPage(1);
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
        filter === "ENGAGING" ||
        filter === "PARTICIPATED" ||
        filter === "NOT_PARTICIPATING") {
      updateQueryState(setParticipationStatusFilter, [filter]);
      return;
    }

    if (filter === "closing-soon") {
      const range = getNextThreeDayRange();
      setSubmissionDateFrom(range.from);
      setSubmissionDateTo(range.to);
      setPage(1);
    }
  }

  const hasActiveFilters =
    tenderNoFilter ||
    tenderNameFilter ||
    cityFilter ||
    organizationFilter ||
    (isAdmin && regionFilter.length > 0) ||
    submissionDateFrom ||
    submissionDateTo ||
    estimatedValueMin !== "" ||
    estimatedValueMax !== "" ||
    participationStatusFilter.length > 0 ||
    productFilter.length > 0 ||
    (isAdmin && (sourceFilter.length > 0 || scoreMin !== "" || scoreMax !== "" || advertisedDateFrom || advertisedDateTo));

  const hasOtherFilters =
    tenderNoFilter ||
    tenderNameFilter ||
    cityFilter ||
    organizationFilter ||
    (isAdmin && regionFilter.length > 0) ||
    estimatedValueMin !== "" ||
    estimatedValueMax !== "" ||
    productFilter.length > 0 ||
    (isAdmin && (sourceFilter.length > 0 || scoreMin !== "" || scoreMax !== "" || advertisedDateFrom || advertisedDateTo));

  function isSummaryFilterActive(filter) {
    if (filter === "ALL") {
      return !hasActiveFilters;
    }

    if (filter === "closing-soon") {
      const range = getNextThreeDayRange();

      return Boolean(
        !hasOtherFilters &&
        participationStatusFilter.length === 0 &&
        submissionDateFrom === range.from &&
        submissionDateTo === range.to
      );
    }

    return Boolean(
      !hasOtherFilters &&
      !submissionDateFrom &&
      !submissionDateTo &&
      participationStatusFilter.length === 1 && participationStatusFilter[0] === filter
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
      `/tenders/${encodeURIComponent(tenderId)}${location.search}`
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
      ...(isAdmin ? ["Source"] : []),
      "Product",
      ...(isAdmin ? ["Advertised Date"] : []),
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
          ...(isAdmin ? [tender.source] : []),
          Array.isArray(tender.matched_capabilities) ? tender.matched_capabilities.join(", ") : "",
          ...(isAdmin ? [tender.advertised_date] : []),
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
      "jazz_radar_tenders.csv";

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
            Jazz Radar.
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
          className={`tender-summary-card ${isSummaryFilterActive("ENGAGING") ? "active" : ""}`}
          onClick={() => applySummaryFilter("ENGAGING")}
          aria-pressed={isSummaryFilterActive("ENGAGING")}
        >
          <span>
            Engaging
          </span>

          <strong>
            {participatingCount}
          </strong>
        </button>

        <button
          type="button"
          className={`tender-summary-card ${isSummaryFilterActive("PARTICIPATED") ? "active" : ""}`}
          onClick={() => applySummaryFilter("PARTICIPATED")}
          aria-pressed={isSummaryFilterActive("PARTICIPATED")}
        >
          <span>Participated</span>
          <strong>{participatedCount}</strong>
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
              {pagination.total ?? 0}{" "}
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

            {isAdmin && (
              <div className="admin-score-filter">
                <span>Relevance score</span>
                <input type="number" min="0" value={scoreMin} onChange={(event) => updateQueryState(setScoreMin, event.target.value)} aria-label="Relevance score minimum" placeholder="Min" />
                <input type="number" min="0" value={scoreMax} onChange={(event) => updateQueryState(setScoreMax, event.target.value)} aria-label="Relevance score maximum" placeholder="Max" />
              </div>
            )}

            {isAdmin && <MultiSelectFilter id="region" label="Region" placeholder="All regions" options={REGION_OPTIONS} selected={regionFilter} onChange={(value) => updateQueryState(setRegionFilter, value)} compact openedFilter={openedFilter} setOpenedFilter={setOpenedFilter} />}

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
                  updateQueryState(setSortBy,
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
                  updateQueryState(setSortOrder,
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

          <table className={`tenders-table ${isAdmin ? "admin-table" : "coordinator-table"}`}>

            <colgroup>
              {isAdmin && <col className="selection-column" />}
              <col className="web-tender-no-column" />
              <col className="tender-name-column" />
              <col className="city-column" />
              <col className="organization-column" />
              {isAdmin && <col className="source-column" />}
              <col className="product-column" />
              {isAdmin && <col className="advertised-date-column" />}
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
                      updateQueryState(setTenderNoFilter,
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
                      updateQueryState(setTenderNameFilter,
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
                      updateQueryState(setCityFilter,
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
                      updateQueryState(setOrganizationFilter,
                        event.target.value
                      )
                    }
                  />
                </th>

                {isAdmin && <th className="source-column">
                  Source
                  <MultiSelectFilter id="source" label="Source" placeholder="All sources" options={SOURCE_OPTIONS} selected={sourceFilter} onChange={(value) => updateQueryState(setSourceFilter, value)} openedFilter={openedFilter} setOpenedFilter={setOpenedFilter} />
                </th>}

                <th className="product-column">
                  Product
                  <MultiSelectFilter id="product" label="Product" placeholder="All products" options={PRODUCT_OPTIONS} selected={productFilter} onChange={(value) => updateQueryState(setProductFilter, value)} openedFilter={openedFilter} setOpenedFilter={setOpenedFilter} />
                </th>

                {isAdmin && <th className="advertised-date-column">
                  Advertised Date
                  <div className="column-range-filter">
                    <input type="date" value={advertisedDateFrom} onChange={(event) => updateQueryState(setAdvertisedDateFrom, event.target.value)} aria-label="Advertised date from" />
                    <input type="date" value={advertisedDateTo} onChange={(event) => updateQueryState(setAdvertisedDateTo, event.target.value)} aria-label="Advertised date to" />
                  </div>
                </th>}

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
                        updateQueryState(setSubmissionDateFrom,
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
                        updateQueryState(setSubmissionDateTo,
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
                        updateQueryState(setEstimatedValueMin,
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
                        updateQueryState(setEstimatedValueMax,
                          event.target.value
                        )
                      }
                    />

                  </div>
                </th>

                <th>
                  Participation Status
                  <MultiSelectFilter id="status" label="Status" placeholder="All statuses" options={PARTICIPATION_OPTIONS} selected={participationStatusFilter} onChange={(value) => updateQueryState(setParticipationStatusFilter, value)} openedFilter={openedFilter} setOpenedFilter={setOpenedFilter} />
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

                    {isAdmin && <td className="source-column">{displayValue(tender.source)}</td>}

                    <td className="product-column">
                      {displayValue(
                        Array.isArray(tender.matched_capabilities)
                          ? tender.matched_capabilities.join(", ")
                          : tender.matched_capabilities
                      )}
                    </td>

                    {isAdmin && <td className="advertised-date-column">{formatDateOnly(tender.advertised_date)}</td>}

                    <td>
                      {formatDateOnly(
                        tender.closed_date
                      )}
                    </td>

                    <td>
                      {formatEstimatedValue(
                        tender.estimated_value
                      )}
                    </td>

                    <td>
                      {participationLabel(
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

          <div className="tenders-pagination" style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "12px", padding: "16px" }}>
            <button type="button" onClick={() => setPage((current) => Math.max(1, current - 1))} disabled={page <= 1}>Previous</button>
            <span>Page {pagination.page ?? page} of {pagination.total_pages ?? 1}</span>
            <button type="button" onClick={() => setPage((current) => Math.min(pagination.total_pages || 1, current + 1))} disabled={page >= (pagination.total_pages || 1)}>Next</button>
          </div>

        </div>

      </div>

    </div>
  );
}

export default AllTenders;
