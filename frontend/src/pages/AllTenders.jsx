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
  RefreshCw,
} from "lucide-react";
import MultiSelect from "../components/MultiSelect";

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

function getEstimatedValue(tender) {
  if (tender.estimatedValue === null) {
    return null;
  }

  const value = String(tender.estimatedValue)
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

  const [tenders, setTenders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [search, setSearch] = useState("");

  const [selectedSources, setSelectedSources] =
    useState([]);

  const [selectedCapabilities, setSelectedCapabilities] =
    useState([]);

  const [relevanceFilter, setRelevanceFilter] =
    useState("all");

  const [advertisedFrom, setAdvertisedFrom] =
    useState("");

  const [advertisedTo, setAdvertisedTo] =
    useState("");

  const [closingFrom, setClosingFrom] =
    useState("");

  const [closingTo, setClosingTo] =
    useState("");

  const [sortBy, setSortBy] =
    useState("relevance");

  const [sortOrder, setSortOrder] =
    useState("desc");

  const [scraperRunning, setScraperRunning] =
    useState(false);

  const [scraperMessage, setScraperMessage] =
    useState("");

  useEffect(() => {
    const fetchTenders = async () => {
      try {
        const response = await api.get(
          "/api/tenders"
        );

        const normalized = normalizeTenders(
          response.data
        );

        setTenders(normalized);
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

  const filterOptions = useMemo(() => {
    const sources = new Set();
    const capabilities = new Set();

    tenders.forEach((tender) => {
      if (tender.source) {
        sources.add(tender.source);
      }

      tender.capability?.forEach(
        (capability) => {
          if (capability) {
            capabilities.add(capability);
          }
        }
      );
    });

    return {
      sources: [...sources].sort(),
      capabilities: [...capabilities].sort(),
    };
  }, [tenders]);

  const filteredTenders = useMemo(() => {
    const searchTerm = search
      .trim()
      .toLowerCase();

    const result = tenders.filter((tender) => {
      if (searchTerm) {
        const searchableText = [
          tender.tenderNo,
          tender.referenceNo,
          tender.tenderName,
          tender.authority,
          tender.organization,
          tender.city,
          tender.location,
          tender.source,
          tender.status,
          ...(tender.capability || []),
          ...(tender.matchedKeywords || []),
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

      if (selectedSources.length > 0) {
        if (
          !selectedSources.includes(
            tender.source
          )
        ) {
          return false;
        }
      }

      if (
        selectedCapabilities.length > 0
      ) {
        const hasCapability =
          tender.capability?.some(
            (capability) =>
              selectedCapabilities.includes(
                capability
              )
          );

        if (!hasCapability) {
          return false;
        }
      }

      const relevance =
        typeof tender.relevanceScore ===
        "number"
          ? tender.relevanceScore
          : null;

      if (relevanceFilter !== "all") {
        if (relevance === null) {
          return false;
        }

        if (relevanceFilter === "0-20") {
          if (
            relevance < 0 ||
            relevance >= 20
          ) {
            return false;
          }
        }

        if (relevanceFilter === "20-40") {
          if (
            relevance < 20 ||
            relevance >= 40
          ) {
            return false;
          }
        }

        if (relevanceFilter === "40-60") {
          if (
            relevance < 40 ||
            relevance >= 60
          ) {
            return false;
          }
        }

        if (relevanceFilter === "60-80") {
          if (
            relevance < 60 ||
            relevance >= 80
          ) {
            return false;
          }
        }

        if (relevanceFilter === "80-100") {
          if (
            relevance < 80 ||
            relevance > 100
          ) {
            return false;
          }
        }
      }

      const advertisedDate =
        parseDate(
          tender.advertisedDate
        );

      if (advertisedFrom) {
        const from =
          new Date(advertisedFrom);

        if (
          !advertisedDate ||
          advertisedDate < from
        ) {
          return false;
        }
      }

      if (advertisedTo) {
        const to =
          new Date(advertisedTo);

        to.setHours(
          23,
          59,
          59,
          999
        );

        if (
          !advertisedDate ||
          advertisedDate > to
        ) {
          return false;
        }
      }

      const closingDate =
        parseDate(
          tender.closingDate
        );

      if (closingFrom) {
        const from =
          new Date(closingFrom);

        if (
          !closingDate ||
          closingDate < from
        ) {
          return false;
        }
      }

      if (closingTo) {
        const to =
          new Date(closingTo);

        to.setHours(
          23,
          59,
          59,
          999
        );

        if (
          !closingDate ||
          closingDate > to
        ) {
          return false;
        }
      }

      return true;
    });

    result.sort((a, b) => {
      let valueA;
      let valueB;

      if (sortBy === "relevance") {
        valueA =
          a.relevanceScore ?? -Infinity;

        valueB =
          b.relevanceScore ?? -Infinity;
      }

      if (sortBy === "closingDate") {
        valueA =
          parseDate(
            a.closingDate
          )?.getTime() ?? Infinity;

        valueB =
          parseDate(
            b.closingDate
          )?.getTime() ?? Infinity;
      }

      if (sortBy === "estimatedValue") {
        valueA =
          getEstimatedValue(a) ??
          -Infinity;

        valueB =
          getEstimatedValue(b) ??
          -Infinity;
      }

      if (sortBy === "advertisedDate") {
        valueA =
          parseDate(
            a.advertisedDate
          )?.getTime() ?? -Infinity;

        valueB =
          parseDate(
            b.advertisedDate
          )?.getTime() ?? -Infinity;
      }

      if (sortOrder === "asc") {
        return valueA - valueB;
      }

      return valueB - valueA;
    });

    return result;
  }, [
    tenders,
    search,
    selectedSources,
    selectedCapabilities,
    relevanceFilter,
    advertisedFrom,
    advertisedTo,
    closingFrom,
    closingTo,
    sortBy,
    sortOrder,
  ]);

  async function runScraper() {
    if (scraperRunning) return;

    try {
      setScraperRunning(true);
      setScraperMessage("");

      const response =
        await api.post(
          "/api/scraper/tenders/run"
        );

      console.log(
        "SCRAPER RESULTS:",
        JSON.stringify(
          response.data.results,
          null,
          2
        )
      );

      const tenderResponse =
        await api.get(
          "/api/tenders"
        );

      const normalized =
        normalizeTenders(
          tenderResponse.data
        );

      setTenders(normalized);

      const results =
        response.data.results || {};

      const federal =
        results["Federal PPRA"] || {};

      const punjab =
        results["Punjab PPRA"] || {};

      const balochistan =
        results["Balochistan PPRA"] || {};

      const totalKept =
        Number(federal.kept || 0) +
        Number(punjab.kept || 0) +
        Number(balochistan.kept || 0);

      const inserted =
        Number(
          punjab.storage?.inserted || 0
        );

      const updated =
        Number(
          punjab.storage?.updated || 0
        );

      setScraperMessage(
        `Scraper completed successfully. ` +
        `Federal: ${federal.kept || 0} relevant, ` +
        `Punjab: ${punjab.kept || 0} relevant, ` +
        `Balochistan: ${balochistan.kept || 0} relevant. ` +
        `New: ${inserted}, Updated: ${updated}, ` +
        `Total: ${normalized.length}.`
      );
    } catch (err) {
      console.error(
        "Scraper error:",
        err
      );

      setScraperMessage(
        "Failed to run scraper."
      );
    } finally {
      setScraperRunning(false);
    }
  }

  function clearFilters() {
    setSearch("");
    setSelectedSources([]);
    setSelectedCapabilities([]);
    setRelevanceFilter("all");
    setAdvertisedFrom("");
    setAdvertisedTo("");
    setClosingFrom("");
    setClosingTo("");
    setSortBy("relevance");
    setSortOrder("desc");
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
      "Reference No",
      "Tender Name",
      "Authority",
      "Organization",
      "City",
      "Estimated Value",
      "Bid Security",
      "Advertised Date",
      "Closing Date",
      "Matched Keywords",
      "Relevance",
      "Source",
      "Status",
    ];

    const rows =
      filteredTenders.map((tender) => [
        tender.tenderNo,
        tender.referenceNo,
        tender.tenderName,
        tender.authority,
        tender.organization,
        tender.city,
        tender.estimatedValue,
        tender.bidSecurity,
        tender.advertisedDate,
        tender.closingDate,
        tender.matchedKeywords,
        tender.relevanceScore,
        tender.source,
        tender.status,
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
      "jazzworld_tenders.csv";

    document.body.appendChild(link);

    link.click();

    document.body.removeChild(link);

    URL.revokeObjectURL(url);
  }

  const hasActiveFilters =
    search ||
    selectedSources.length > 0 ||
    selectedCapabilities.length > 0 ||
    relevanceFilter !== "all" ||
    advertisedFrom ||
    advertisedTo ||
    closingFrom ||
    closingTo;

  if (loading) {
    return <h1>Loading tenders...</h1>;
  }

  if (error) {
    return <h1>{error}</h1>;
  }

  return (
    <div className="tenders-page">

      <div className="page-header">

        <div>
          <h1>All Tenders</h1>

          <p>
            Monitor and discover relevant
            government procurement
            opportunities for JazzWorld.
          </p>
        </div>

        <div className="page-header-actions">

          <button
            type="button"
            className="run-scraper-button"
            onClick={runScraper}
            disabled={scraperRunning}
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
              ? "Running Scraper..."
              : "Run Scraper"}
          </button>

          <div className="total-tenders">
            <span>Total Tenders</span>

            <strong>
              {tenders.length}
            </strong>
          </div>

        </div>

      </div>

      {scraperMessage && (
        <div className="scraper-message">
          {scraperMessage}
        </div>
      )}

      <div className="search-bar">

        <Search size={19} />

        <input
          type="text"
          placeholder="Search tender no, reference, name, authority, organization, city..."
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
            label="Capability"
            options={
              filterOptions.capabilities
            }
            selected={
              selectedCapabilities
            }
            onChange={
              setSelectedCapabilities
            }
            placeholder="Select capabilities"
          />

          <label className="filter-field">
            <span>
              Relevance Score
            </span>

            <select
              value={
                relevanceFilter
              }
              onChange={(event) =>
                setRelevanceFilter(
                  event.target.value
                )
              }
            >
              <option value="all">
                All Scores
              </option>

              <option value="0-20">
                0 – 20
              </option>

              <option value="20-40">
                20 – 40
              </option>

              <option value="40-60">
                40 – 60
              </option>

              <option value="60-80">
                60 – 80
              </option>

              <option value="80-100">
                80 – 100
              </option>
            </select>
          </label>

          <label className="filter-field">
            <span>
              Advertised From
            </span>

            <input
              type="date"
              value={
                advertisedFrom
              }
              onChange={(event) =>
                setAdvertisedFrom(
                  event.target.value
                )
              }
            />
          </label>

          <label className="filter-field">
            <span>
              Advertised To
            </span>

            <input
              type="date"
              value={
                advertisedTo
              }
              onChange={(event) =>
                setAdvertisedTo(
                  event.target.value
                )
              }
            />
          </label>

          <label className="filter-field">
            <span>
              Closing From
            </span>

            <input
              type="date"
              value={
                closingFrom
              }
              onChange={(event) =>
                setClosingFrom(
                  event.target.value
                )
              }
            />
          </label>

          <label className="filter-field">
            <span>
              Closing To
            </span>

            <input
              type="date"
              value={
                closingTo
              }
              onChange={(event) =>
                setClosingTo(
                  event.target.value
                )
              }
            />
          </label>

        </div>

      </div>

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
          tenders
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
            <option value="relevance">
              Relevance
            </option>

            <option value="closingDate">
              Closing Date
            </option>

            <option value="estimatedValue">
              Estimated Value
            </option>

            <option value="advertisedDate">
              Advertised Date
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
            <option value="desc">
              Descending
            </option>

            <option value="asc">
              Ascending
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

      <div className="table-section">

        <div className="table-header">

          <div>
            <h2>
              Tender Opportunities
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

          <table>

            <thead>

              <tr>
                <th>Tender No</th>
                <th>Reference No</th>
                <th>Tender Name</th>
                <th>Authority</th>
                <th>Organization</th>
                <th>City</th>
                <th>Estimated Value</th>
                <th>Bid Security</th>
                <th>Advertised Date</th>
                <th>Closing Date</th>
                <th>Matched Keywords</th>
                <th>Relevance</th>
                <th>Source</th>
                <th>Status</th>
              </tr>

            </thead>

            <tbody>

              {filteredTenders.map(
                (tender) => (
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

                    <td className="reference-cell">
                      {displayValue(
                        tender.referenceNo
                      )}
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
                      {displayValue(
                        tender.estimatedValue
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.bidSecurity
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.advertisedDate
                      )}
                    </td>

                    <td>
                      {displayValue(
                        tender.closingDate
                      )}
                    </td>

                    <td>
                      <div className="tag-list">

                        {tender
                          .matchedKeywords
                          ?.length
                          ? tender.matchedKeywords.map(
                              (keyword) => (
                                <span
                                  className="tag keyword-tag"
                                  key={
                                    keyword
                                  }
                                >
                                  {
                                    keyword
                                  }
                                </span>
                              )
                            )
                          : "—"}

                      </div>
                    </td>

                    <td>
                      <span className="relevance-score">
                        {displayValue(
                          tender.relevanceScore
                        )}
                      </span>
                    </td>

                    <td>
                      <span className="source-badge">
                        {displayValue(
                          tender.source
                        )}
                      </span>
                    </td>

                    <td>
                      {displayValue(
                        tender.status
                      )}
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
                search or filters.
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