import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../api";
import { normalizeTenders } from "../utils/tenderNormalizer";
import {
  Search,
  SlidersHorizontal,
  ArrowUpDown,
  X,
  Download,
} from "lucide-react";
import MultiSelect from "../components/MultiSelect";

const PROGRESS_OPTIONS = [
  "Participation",
  "Bid Preparation",
  "Bid Submitted",
];

const RESULT_OPTIONS = [
  "Win",
  "Lost",
  "Result Not Announced",
];

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

function csvValue(value) {
  if (
    value === null ||
    value === undefined
  ) {
    return "";
  }

  const stringValue = String(value);

  return `"${stringValue.replace(/"/g, '""')}"`;
}

function ParticipatedTenders() {
  const navigate = useNavigate();

  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");

  const [selectedSources, setSelectedSources] =
    useState([]);

  const [selectedProgress, setSelectedProgress] =
    useState([]);

  const [selectedResults, setSelectedResults] =
    useState([]);

  const [sortBy, setSortBy] =
    useState("tenderNo");

  const [sortOrder, setSortOrder] =
    useState("asc");

  useEffect(() => {
    fetchParticipatedTenders();
  }, []);

  async function fetchParticipatedTenders() {
    try {
      setLoading(true);

      const response =
        await api.get("/api/tenders");

      const normalized =
        normalizeTenders(response.data);

      const progressResults =
        await Promise.all(
          normalized.map(async (tender) => {
            try {
              const progressResponse =
                await api.get(
                  `/api/tenders/${encodeURIComponent(
                    tender.id
                  )}/progress`
                );

              return {
                ...tender,
                progress:
                  progressResponse.data,
              };
            } catch (err) {
              console.error(
                `Failed to load progress for ${tender.id}`,
                err
              );

              return null;
            }
          })
        );

      const participated =
        progressResults.filter(
          (tender) =>
            tender &&
            tender.progress?.participating === true
        );

      setTenders(participated);
    } catch (err) {
      console.error(err);

      setError(
        "Failed to load participated tenders."
      );
    } finally {
      setLoading(false);
    }
  }

  const filterOptions = useMemo(() => {
    const sources = new Set();

    tenders.forEach((tender) => {
      if (tender.source) {
        sources.add(tender.source);
      }
    });

    return {
      sources: [...sources].sort(),
    };
  }, [tenders]);

  const filteredTenders = useMemo(() => {
    const searchTerm = search
      .trim()
      .toLowerCase();

    const result = tenders.filter((tender) => {
      const currentProgress =
        tender.progress?.stage ||
        "Participation";

      const currentResult =
        tender.progress?.result || null;

      /* Search */
      if (searchTerm) {
        const searchableText = [
          tender.tenderNo,
          tender.tenderName,
          tender.authority,
          tender.organization,
          tender.city,
          tender.source,
          currentProgress,
          currentResult,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        if (
          !searchableText.includes(
            searchTerm
          )
        ) {
          return false;
        }
      }

      /* Source filter */
      if (
        selectedSources.length > 0 &&
        !selectedSources.includes(
          tender.source
        )
      ) {
        return false;
      }

      /* Progress filter */
      if (
        selectedProgress.length > 0 &&
        !selectedProgress.includes(
          currentProgress
        )
      ) {
        return false;
      }

      /* Result filter */
      if (
        selectedResults.length > 0
      ) {
        if (
          !currentResult ||
          !selectedResults.includes(
            currentResult
          )
        ) {
          return false;
        }
      }

      return true;
    });

    /* Sorting */
    result.sort((a, b) => {
      const progressA =
        a.progress?.stage ||
        "Participation";

      const progressB =
        b.progress?.stage ||
        "Participation";

      const resultA =
        a.progress?.result || "";

      const resultB =
        b.progress?.result || "";

      let valueA;
      let valueB;

      if (sortBy === "tenderNo") {
        valueA =
          a.tenderNo || "";
        valueB =
          b.tenderNo || "";
      }

      if (sortBy === "tenderName") {
        valueA =
          a.tenderName || "";
        valueB =
          b.tenderName || "";
      }

      if (sortBy === "city") {
        valueA =
          a.city || "";
        valueB =
          b.city || "";
      }

      if (sortBy === "progress") {
        valueA =
          progressA;
        valueB =
          progressB;
      }

      if (sortBy === "result") {
        valueA =
          resultA;
        valueB =
          resultB;
      }

      if (sortBy === "source") {
        valueA =
          a.source || "";
        valueB =
          b.source || "";
      }

      const comparison =
        String(valueA).localeCompare(
          String(valueB),
          undefined,
          {
            numeric: true,
            sensitivity: "base",
          }
        );

      return sortOrder === "asc"
        ? comparison
        : -comparison;
    });

    return result;
  }, [
    tenders,
    search,
    selectedSources,
    selectedProgress,
    selectedResults,
    sortBy,
    sortOrder,
  ]);

  function clearFilters() {
    setSearch("");
    setSelectedSources([]);
    setSelectedProgress([]);
    setSelectedResults([]);
    setSortBy("tenderNo");
    setSortOrder("asc");
  }

  function openTender(tenderId) {
    if (!tenderId) return;

    navigate(
      `/tenders/${encodeURIComponent(
        tenderId
      )}`
    );
  }

  function downloadCSV() {
    const headers = [
      "Tender No",
      "Tender Name",
      "Authority",
      "Organization",
      "City",
      "Progress",
      "Result",
      "Source",
    ];

    const rows =
      filteredTenders.map((tender) => [
        tender.tenderNo,
        tender.tenderName,
        tender.authority,
        tender.organization,
        tender.city,
        tender.progress?.stage ||
          "Participation",
        tender.progress?.result ||
          "",
        tender.source,
      ]);

    const csv = [
      headers
        .map(csvValue)
        .join(","),
      ...rows.map((row) =>
        row
          .map(csvValue)
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob(
      [csv],
      {
        type: "text/csv;charset=utf-8;",
      }
    );

    const url =
      URL.createObjectURL(blob);

    const link =
      document.createElement("a");

    link.href = url;

    link.download =
      "jazzworld_participated_tenders.csv";

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  const hasActiveFilters =
    search ||
    selectedSources.length > 0 ||
    selectedProgress.length > 0 ||
    selectedResults.length > 0;

  if (loading) {
    return (
      <h1>
        Loading participated tenders...
      </h1>
    );
  }

  if (error) {
    return <h1>{error}</h1>;
  }

  return (
    <div className="tenders-page">
      <div className="page-header">
        <div>
          <h1>
            Participated Tenders
          </h1>

          <p>
            Track government procurement
            opportunities selected for
            participation by JazzWorld.
          </p>
        </div>

        <div className="total-tenders">
          <span>
            Participating Tenders
          </span>

          <strong>
            {tenders.length}
          </strong>
        </div>
      </div>

      {/* Search */}
      <div className="search-bar">
        <Search size={19} />

        <input
          type="text"
          placeholder="Search tender no, name, authority, organization, city, source..."
          value={search}
          onChange={(event) =>
            setSearch(
              event.target.value
            )
          }
        />

        {search && (
          <button
            className="clear-search"
            onClick={() =>
              setSearch("")
            }
            aria-label="Clear search"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="filter-panel">
        <div className="filter-panel-header">
          <div>
            <SlidersHorizontal
              size={17}
            />

            <span>Filters</span>
          </div>

          {hasActiveFilters && (
            <button
              className="clear-filters"
              onClick={
                clearFilters
              }
            >
              Clear filters
            </button>
          )}
        </div>

        <div className="filter-grid">
          <MultiSelect
            label="Source"
            options={
              filterOptions.sources
            }
            selected={
              selectedSources
            }
            onChange={
              setSelectedSources
            }
            placeholder="Select sources"
          />

          <MultiSelect
            label="Progress"
            options={
              PROGRESS_OPTIONS
            }
            selected={
              selectedProgress
            }
            onChange={
              setSelectedProgress
            }
            placeholder="Select progress"
          />

          <MultiSelect
            label="Result"
            options={
              RESULT_OPTIONS
            }
            selected={
              selectedResults
            }
            onChange={
              setSelectedResults
            }
            placeholder="Select results"
          />
        </div>
      </div>

      {/* Toolbar */}
      <div className="results-toolbar">
        <div className="results-count">
          Showing{" "}
          <strong>
            {filteredTenders.length}
          </strong>{" "}
          of{" "}
          <strong>
            {tenders.length}
          </strong>{" "}
          participated tenders
        </div>

        <div className="sort-controls">
          <ArrowUpDown size={16} />

          <span>Sort by</span>

          <select
            value={sortBy}
            onChange={(event) =>
              setSortBy(
                event.target.value
              )
            }
          >
            <option value="tenderNo">
              Tender No
            </option>

            <option value="tenderName">
              Tender Name
            </option>

            <option value="city">
              City
            </option>

            <option value="progress">
              Progress
            </option>

            <option value="result">
              Result
            </option>

            <option value="source">
              Source
            </option>
          </select>

          <select
            value={sortOrder}
            onChange={(event) =>
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

          <button
            type="button"
            className="download-csv-button"
            onClick={
              downloadCSV
            }
          >
            <Download size={16} />
            Download CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="table-section">
        <div className="table-header">
          <div>
            <h2>
              Participated Opportunities
            </h2>

            <span>
              {
                filteredTenders.length
              }{" "}
              matching opportunities
            </span>
          </div>
        </div>

        <div className="table-container">
          {filteredTenders.length ===
          0 ? (
            <div className="empty-state">
              <h3>
                No participated
                tenders found
              </h3>

              <p>
                Try changing your
                search or filters.
              </p>

              {hasActiveFilters && (
                <button
                  onClick={
                    clearFilters
                  }
                  className="clear-empty-button"
                >
                  Clear Filters
                </button>
              )}
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Tender No</th>
                  <th>Tender Name</th>
                  <th>Authority</th>
                  <th>Organization</th>
                  <th>City</th>
                  <th>Progress</th>
                  <th>Result</th>
                  <th>Source</th>
                </tr>
              </thead>

              <tbody>
                {filteredTenders.map(
                  (tender) => {
                    const currentProgress =
                      tender.progress?.stage ||
                      "Participation";

                    const currentResult =
                      tender.progress?.result ||
                      null;

                    return (
                      <tr
                        key={tender.id}
                      >
                        <td>
                          <button
                            type="button"
                            className="tender-link"
                            onClick={() =>
                              openTender(
                                tender.id
                              )
                            }
                          >
                            {displayValue(
                              tender.tenderNo
                            )}
                          </button>
                        </td>

                        <td className="tender-name">
                          <button
                            type="button"
                            className="tender-link tender-name-link"
                            onClick={() =>
                              openTender(
                                tender.id
                              )
                            }
                          >
                            {displayValue(
                              tender.tenderName
                            )}
                          </button>
                        </td>

                        <td>
                          {displayValue(
                            tender.authority
                          )}
                        </td>

                        <td>
                          {displayValue(
                            tender.organization
                          )}
                        </td>

                        <td>
                          {displayValue(
                            tender.city
                          )}
                        </td>

                        <td>
                          <span className="progress-stage-badge">
                            {
                              currentProgress
                            }
                          </span>
                        </td>

                        <td>
                          {currentResult ? (
                            <span
                              className={`result-table-badge ${
                                currentResult ===
                                "Win"
                                  ? "result-win"
                                  : currentResult ===
                                    "Lost"
                                  ? "result-lost"
                                  : "result-pending"
                              }`}
                            >
                              {
                                currentResult
                              }
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>

                        <td>
                          <span className="source-badge">
                            {displayValue(
                              tender.source
                            )}
                          </span>
                        </td>
                      </tr>
                    );
                  }
                )}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}

export default ParticipatedTenders;