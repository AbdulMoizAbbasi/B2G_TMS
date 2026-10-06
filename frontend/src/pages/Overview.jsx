import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowUpRight, Building2, CalendarClock, CircleCheck, ClipboardList, Clock3, Eye, Filter, Gauge, Package, RotateCcw, Target } from "lucide-react";
import api from "../api";
import formatEstimatedValue from "../utils/formatEstimatedValue";
import "./Overview.css";

const STATUSES = ["ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING", "NOT_REVIEWED"];
const PARTICIPATION_CHART_STATUSES = ["NOT_REVIEWED", "ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING"];
const PARTICIPATION_REGIONS = ["North1", "North2", "Central", "South"];
const STATUS_LABELS = {
  ENGAGING: "Engaging",
  PARTICIPATED: "Participated",
  PARTICIPATING: "Engaging",
  NOT_PARTICIPATING: "Not Participating",
  NOT_REVIEWED: "Review Pending",
};
const isEngaging = (status) => status === "ENGAGING" || status === "PARTICIPATING";
const SCORE_BANDS = [
  { id: "high", label: "High · 70–100", min: 70, max: 100 },
  { id: "medium", label: "Medium · 40–69", min: 40, max: 69.999 },
  { id: "low", label: "Low · 1–39", min: 1, max: 39.999 },
  { id: "zero", label: "No score", min: 0, max: 0 },
];

function dateOnly(value) {
  if (!value) return "";
  const text = String(value);
  return /^\d{4}-\d{2}-\d{2}/.test(text) ? text.slice(0, 10) : "";
}

function formatDate(value) {
  const day = dateOnly(value);
  if (!day) return "—";
  const date = new Date(`${day}T00:00:00`);
  return Number.isNaN(date.getTime()) ? "—" : new Intl.DateTimeFormat("en-GB", { day: "2-digit", month: "short", year: "numeric" }).format(date);
}

function withinRange(value, range) {
  const day = dateOnly(value);
  return (!range.from || (day && day >= range.from)) && (!range.to || (day && day <= range.to));
}

function MultiSelect({ title, icon: Icon, options, selected, onChange, placeholder, disabled = false }) {
  const [open, setOpen] = useState(false);
  const toggle = (value) => onChange(selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]);
  return (
    <div className="overview-filter-group">
      <div className="overview-filter-label"><Icon size={15} />{title}</div>
      <button className="overview-select-trigger" type="button" onClick={() => setOpen((value) => !value)} disabled={disabled} aria-expanded={open}>
        <span>{selected.length ? `${selected.length} selected` : placeholder}</span><span className="overview-select-chevron">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="overview-select-options">
        {options.length ? options.map((option) => (
          <label className="overview-check-option" key={option.value}>
            <input type="checkbox" checked={selected.includes(option.value)} onChange={() => toggle(option.value)} />
            <span>{option.label}</span>
          </label>
        )) : <span className="overview-options-empty">No options available</span>}
      </div>}
    </div>
  );
}

async function fetchAllTenders() {
  const pageSize = 100;
  const firstResponse = await api.get("/api/tenders", {
    params: { page: 1, page_size: pageSize },
  });
  const firstItems = Array.isArray(firstResponse.data?.items)
    ? firstResponse.data.items
    : [];
  const totalPages = Number(firstResponse.data?.pagination?.total_pages) || 1;

  if (totalPages <= 1) return firstItems;

  const remainingResponses = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) =>
      api.get("/api/tenders", {
        params: { page: index + 2, page_size: pageSize },
      })
    )
  );

  return firstItems.concat(
    ...remainingResponses.map((response) =>
      Array.isArray(response.data?.items) ? response.data.items : []
    )
  );
}

function OverviewTable({ title, icon: Icon, tenders, navigate, emptyText }) {
  return (
    <section className="overview-panel overview-table-panel">
      <div className="overview-panel-heading"><div className="overview-panel-title"><span className="overview-panel-icon"><Icon size={17} /></span><h2>{title}</h2></div><span className="overview-table-count">{tenders.length}</span></div>
      <div className="overview-table-scroll">
        <table className="overview-table">
          <thead><tr><th>Tender Name</th><th>Organization</th><th>Submission Date</th><th>Estimated Value</th><th>Participation Status</th><th>View</th></tr></thead>
          <tbody>{tenders.length ? tenders.map((tender) => (
            <tr key={tender.jazzid}>
              <td><span className="overview-tender-name">{tender.tender_name || "Untitled tender"}</span><small>{tender.web_tender_no || tender.tender_reference_no || `#${tender.jazzid}`}</small></td>
              <td>{tender.organization || tender.authority || "—"}</td>
              <td>{formatDate(tender.closed_date)}</td>
              <td>{formatEstimatedValue(tender.estimated_value)}</td>
              <td><span className={`overview-status status-${String(tender.participation_status || "NOT_REVIEWED").toLowerCase()}`}>{STATUS_LABELS[tender.participation_status] || "Review Pending"}</span></td>
              <td><button className="overview-view-button" type="button" aria-label={`View ${tender.tender_name || "tender"}`} onClick={() => navigate(`/tenders/${encodeURIComponent(tender.jazzid)}`)}><Eye size={16} /> View</button></td>
            </tr>
          )) : <tr><td className="overview-empty" colSpan="6">{emptyText}</td></tr>}</tbody>
        </table>
      </div>
    </section>
  );
}

function Overview() {
  const navigate = useNavigate();
  const [tenders, setTenders] = useState([]);
  const [products, setProducts] = useState([]);
  const [productIdsByTender, setProductIdsByTender] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [productAssociationsLoading, setProductAssociationsLoading] = useState(false);
  const [productAssociationsLoaded, setProductAssociationsLoaded] = useState(false);
  const [closingRange, setClosingRange] = useState({ from: "", to: "" });
  const [advertisedRange, setAdvertisedRange] = useState({ from: "", to: "" });
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [selectedScores, setSelectedScores] = useState([]);
  const [selectedStatuses, setSelectedStatuses] = useState([]);
  const [regionalParticipationStatus, setRegionalParticipationStatus] = useState("ALL");
  const [regionalRegion, setRegionalRegion] = useState("ALL");

  useEffect(() => {
    let active = true;
    Promise.all([fetchAllTenders(), api.get("/api/products")])
      .then(([allTenders, productResponse]) => {
        if (!active) return;
        setTenders(allTenders);
        setProducts(Array.isArray(productResponse.data) ? productResponse.data : []);
      })
      .catch((err) => { if (active) setError(err.response?.data?.detail || "Unable to load overview data."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedProducts.length || productAssociationsLoaded || productAssociationsLoading || !tenders.length) return;
    setProductAssociationsLoading(true);
    const reviewedTenders = tenders.filter((tender) => isEngaging(tender.participation_status));
    const loadProductAssignments = async () => {
      const entries = [];
      for (let start = 0; start < reviewedTenders.length; start += 20) {
        const batch = reviewedTenders.slice(start, start + 20);
        const results = await Promise.all(batch.map(async (tender) => {
          try {
            const response = await api.get(`/api/tenders/${encodeURIComponent(tender.jazzid)}/participation`);
            return [String(tender.jazzid), Array.isArray(response.data.product_ids) ? response.data.product_ids.map(String) : []];
          } catch { return [String(tender.jazzid), []]; }
        }));
        entries.push(...results);
      }
      setProductIdsByTender(Object.fromEntries(entries));
      setProductAssociationsLoaded(true);
      setProductAssociationsLoading(false);
    };
    loadProductAssignments().catch(() => {
      setProductAssociationsLoaded(true);
      setProductAssociationsLoading(false);
    }).finally(() => {
      setProductAssociationsLoading(false);
    });
  }, [selectedProducts, productAssociationsLoaded, productAssociationsLoading, tenders]);

  const filteredTenders = useMemo(() => tenders.filter((tender) => {
    const rawStatus = tender.participation_status || "NOT_REVIEWED";
    const status = rawStatus === "PARTICIPATING" ? "ENGAGING" : rawStatus;
    const score = Number(tender.relevance_score || 0);
    return withinRange(tender.closed_date, closingRange)
      && withinRange(tender.advertised_date, advertisedRange)
      && (!selectedStatuses.length || selectedStatuses.includes(status))
      && (!selectedScores.length || selectedScores.some((id) => {
        const band = SCORE_BANDS.find((item) => item.id === id);
        return band && score >= band.min && score <= band.max;
      }))
      && (!selectedProducts.length || selectedProducts.some((id) => (productIdsByTender[String(tender.jazzid)] || []).includes(id)));
  }), [tenders, closingRange, advertisedRange, selectedStatuses, selectedScores, selectedProducts, productIdsByTender]);

  const today = useMemo(() => {
    const date = new Date(); date.setHours(0, 0, 0, 0); return date;
  }, []);
  const closingSoon = useMemo(() => filteredTenders.filter((tender) => {
    const day = dateOnly(tender.closed_date);
    if (!day) return false;
    const close = new Date(`${day}T00:00:00`);
    const delta = (close - today) / 86400000;
    return delta >= 0 && delta <= 3;
  }), [filteredTenders, today]);
  const notReviewed = useMemo(() => filteredTenders.filter((tender) => (tender.participation_status || "NOT_REVIEWED") === "NOT_REVIEWED"), [filteredTenders]);
  const metrics = useMemo(() => ({
    total: filteredTenders.length,
    pending: filteredTenders.filter((tender) => (tender.participation_status || "NOT_REVIEWED") === "NOT_REVIEWED").length,
    engaging: filteredTenders.filter((tender) => isEngaging(tender.participation_status)).length,
    participated: filteredTenders.filter((tender) => tender.participation_status === "PARTICIPATED").length,
    notParticipating: filteredTenders.filter((tender) => tender.participation_status === "NOT_PARTICIPATING").length,
    closing: closingSoon.length,
  }), [filteredTenders, closingSoon]);
  const monthly = useMemo(() => {
    const groups = new Map();
    filteredTenders.forEach((tender) => {
      const day = dateOnly(tender.advertised_date) || dateOnly(tender.closed_date);
      if (!day) return;
      const key = day.slice(0, 7);
      if (!groups.has(key)) groups.set(key, { engaging: 0, participated: 0, notParticipating: 0, notReviewed: 0 });
      const group = groups.get(key);
      if (isEngaging(tender.participation_status)) group.engaging += 1;
      else if (tender.participation_status === "PARTICIPATED") group.participated += 1;
      else if (tender.participation_status === "NOT_PARTICIPATING") group.notParticipating += 1;
      else group.notReviewed += 1;
    });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).slice(-12).map(([key, value]) => ({ key, label: new Intl.DateTimeFormat("en", { month: "short", year: "2-digit" }).format(new Date(`${key}-01T00:00:00`)), ...value }));
  }, [filteredTenders]);
  const regionalMonthly = useMemo(() => {
    const groups = new Map();
    filteredTenders.forEach((tender) => {
      const day = dateOnly(tender.advertised_date) || dateOnly(tender.closed_date);
      const region = PARTICIPATION_REGIONS.find((name) => name.toLowerCase() === String(tender.region || "").trim().toLowerCase());
      if (!day || !region) return;
      const key = day.slice(0, 7);
      if (!groups.has(key)) groups.set(key, Object.fromEntries(PARTICIPATION_REGIONS.map((name) => [name, { NOT_REVIEWED: 0, ENGAGING: 0, PARTICIPATED: 0, NOT_PARTICIPATING: 0 }])));
      const rawStatus = tender.participation_status || "NOT_REVIEWED";
      const status = rawStatus === "PARTICIPATING" ? "ENGAGING" : rawStatus;
      if (PARTICIPATION_CHART_STATUSES.includes(status)) groups.get(key)[region][status] += 1;
    });
    return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([key, regions]) => ({
      key,
      label: new Intl.DateTimeFormat("en", { month: "short", year: "2-digit" }).format(new Date(`${key}-01T00:00:00`)),
      regions,
    }));
  }, [filteredTenders]);
  const visibleRegions = regionalRegion === "ALL" ? PARTICIPATION_REGIONS : [regionalRegion];
  const regionalChartMax = Math.max(1, ...regionalMonthly.flatMap((month) => visibleRegions.map((region) =>
    PARTICIPATION_CHART_STATUSES.filter((status) => regionalParticipationStatus === "ALL" || status === regionalParticipationStatus)
      .reduce((total, status) => total + month.regions[region][status], 0)
  )));
  const leadership = useMemo(() => {
    const reviewed = filteredTenders.filter((tender) => isEngaging(tender.participation_status) || tender.participation_status === "PARTICIPATED" || tender.participation_status === "NOT_PARTICIPATING");
    const participated = reviewed.filter((tender) => tender.participation_status === "PARTICIPATED").length;
    const highScorePending = filteredTenders.filter((tender) => (tender.participation_status || "NOT_REVIEWED") === "NOT_REVIEWED" && Number(tender.relevance_score || 0) >= 70);
    const urgentPending = filteredTenders.filter((tender) => {
      const date = dateOnly(tender.closed_date);
      if (!date || (tender.participation_status || "NOT_REVIEWED") !== "NOT_REVIEWED") return false;
      const days = (new Date(`${date}T00:00:00`) - today) / 86400000;
      return days >= 0 && days <= 7;
    });
    const portals = new Map();
    filteredTenders.forEach((tender) => {
      const name = tender.source || "Portal not specified";
      portals.set(name, (portals.get(name) || 0) + 1);
    });
    return {
      reviewed: reviewed.length,
      reviewRate: filteredTenders.length ? Math.round(reviewed.length / filteredTenders.length * 100) : 0,
      participationRate: reviewed.length ? Math.round(participated / reviewed.length * 100) : 0,
      highScorePending: highScorePending.length,
      urgentPending: urgentPending.length,
      portals: [...portals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 5),
    };
  }, [filteredTenders, today]);
  const chartMax = Math.max(1, ...monthly.map((item) => item.engaging + item.participated + item.notParticipating + item.notReviewed));
  const clearFilters = () => {
    setClosingRange({ from: "", to: "" }); setAdvertisedRange({ from: "", to: "" });
    setSelectedProducts([]); setSelectedScores([]); setSelectedStatuses([]);
  };

  return (
    <div className="overview-page">
      <header className="overview-header"><div><span className="overview-eyebrow">TENDER WORKSPACE</span><h1>Overview</h1><p>Monitor tender activity, deadlines, and participation at a glance.</p></div><div className="overview-header-count"><strong>{loading || error ? "—" : filteredTenders.length}</strong><span>matching tenders</span></div></header>
      {error && <div className="overview-error" role="alert">{error}</div>}
      <section className="overview-kpis" aria-label="Tender summary">
        {[
          { title: "Total Tenders Received", value: metrics.total, icon: ClipboardList, tone: "blue" },
          { title: "Tender Review Pending", value: metrics.pending, icon: Target, tone: "amber" },
          { title: "Engaging", value: metrics.engaging, icon: ArrowUpRight, tone: "green" },
          { title: "Participated", value: metrics.participated, icon: CircleCheck, tone: "violet" },
          { title: "Not Participating", value: metrics.notParticipating, icon: RotateCcw, tone: "red" },
          { title: "Closing in Next 3 Days", value: metrics.closing, icon: CalendarClock, tone: "violet" },
        ].map(({ title, value, icon: Icon, tone }) => <article className={`overview-kpi kpi-${tone}`} key={title}><span className="overview-kpi-icon"><Icon size={18} /></span><span className="overview-kpi-label">{title}</span><strong>{loading || error ? "—" : value}</strong><small>Based on current filters</small></article>)}
      </section>
      <div className="overview-workspace">
        <aside className="overview-filters overview-panel">
          <div className="overview-filter-header"><div><span className="overview-panel-icon"><Filter size={17} /></span><h2>Filters</h2></div><button type="button" onClick={clearFilters}>Clear all</button></div>
          <div className="overview-date-filter"><span>Closing date</span><label>From<input type="date" value={closingRange.from} onChange={(event) => setClosingRange((value) => ({ ...value, from: event.target.value }))} /></label><label>To<input type="date" value={closingRange.to} onChange={(event) => setClosingRange((value) => ({ ...value, to: event.target.value }))} /></label></div>
          <div className="overview-date-filter"><span>Advertised date</span><label>From<input type="date" value={advertisedRange.from} onChange={(event) => setAdvertisedRange((value) => ({ ...value, from: event.target.value }))} /></label><label>To<input type="date" value={advertisedRange.to} onChange={(event) => setAdvertisedRange((value) => ({ ...value, to: event.target.value }))} /></label></div>
          <MultiSelect title="Products" icon={Package} placeholder={loading ? "Loading products…" : "Select products"} disabled={loading || productAssociationsLoading} options={products.map((product) => ({ value: String(product.id), label: product.name }))} selected={selectedProducts} onChange={setSelectedProducts} />
          {productAssociationsLoading && <small className="overview-filter-note">Loading tender product assignments…</small>}
          <MultiSelect title="Relevance score" icon={Target} placeholder="Select score range" options={SCORE_BANDS.map(({ id, label }) => ({ value: id, label }))} selected={selectedScores} onChange={setSelectedScores} />
          <MultiSelect title="Participation status" icon={ClipboardList} placeholder="Select status" options={STATUSES.map((value) => ({ value, label: STATUS_LABELS[value] }))} selected={selectedStatuses} onChange={setSelectedStatuses} />
          {loading && <div className="overview-filter-note">Loading tender data…</div>}
        </aside>
        <main className="overview-main">
          <section className="overview-panel overview-chart-panel">
            <div className="overview-panel-heading"><div className="overview-panel-title"><span className="overview-panel-icon"><CalendarClock size={17} /></span><div><h2>Monthly tender activity</h2><p>Grouped by advertised month, with closing month as a fallback</p></div></div><span className="overview-chart-total">{filteredTenders.length} total</span></div>
            <div className="overview-chart-legend"><span><i className="legend-participating" />Engaging</span><span><i className="legend-participated" />Participated</span><span><i className="legend-not-reviewed" />Not Reviewed</span><span><i className="legend-not-participating" />Not Participating</span></div>
            {loading ? <div className="overview-chart-empty">Loading tender data…</div> : error ? <div className="overview-chart-empty">Overview data could not be loaded.</div> : monthly.length ? <div className="overview-chart-scroll"><div className="overview-chart" role="img" aria-label="Monthly tender counts by participation status"><div className="overview-y-label">Tender count</div><div className="overview-chart-body"><div className="overview-y-ticks">{[chartMax, Math.ceil(chartMax / 2), 0].map((tick, index) => <span key={`${tick}-${index}`}>{tick}</span>)}</div><div className="overview-plot">{monthly.map((item) => <div className="overview-month" key={item.key}><div className="overview-bar-stack" title={`${item.label}: ${item.engaging} engaging, ${item.participated} participated, ${item.notReviewed} not reviewed, ${item.notParticipating} not participating`}><div className="overview-bar-participating" style={{ height: `${item.engaging / chartMax * 100}%` }} /><div className="overview-bar-participated" style={{ height: `${item.participated / chartMax * 100}%` }} /><div className="overview-bar-not-participating" style={{ height: `${item.notParticipating / chartMax * 100}%` }} /><div className="overview-bar-not-reviewed" style={{ height: `${item.notReviewed / chartMax * 100}%` }} /></div><span>{item.label}</span></div>)}</div></div></div></div> : <div className="overview-chart-empty">No dated tenders match the selected filters.</div>}
          </section>
          <section className="overview-panel overview-chart-panel regional-participation-panel">
            <div className="overview-panel-heading"><div className="overview-panel-title"><span className="overview-panel-icon"><CalendarClock size={17} /></span><div><h2>Monthly Regional Participation</h2><p>Grouped by advertised month, with closing month as a fallback</p></div></div>
              <div className="regional-chart-filters">
                <label className="regional-status-filter">Region<select value={regionalRegion} onChange={(event) => setRegionalRegion(event.target.value)}><option value="ALL">All Regions</option>{PARTICIPATION_REGIONS.map((region) => <option key={region} value={region}>{region}</option>)}</select></label>
                <label className="regional-status-filter">Participation Status<select value={regionalParticipationStatus} onChange={(event) => setRegionalParticipationStatus(event.target.value)}><option value="ALL">All</option>{PARTICIPATION_CHART_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select></label>
              </div>
            </div>
            <div className="overview-chart-legend regional-chart-legend">{PARTICIPATION_CHART_STATUSES.map((status) => <span key={status}><i className={`regional-legend-${status.toLowerCase()}`} />{status.replaceAll("_", " ")}</span>)}</div>
            {loading ? <div className="overview-chart-empty">Loading tender data…</div> : error ? <div className="overview-chart-empty">Overview data could not be loaded.</div> : regionalMonthly.length ? <div className="regional-chart"><div className="overview-y-label">Number of tenders</div><div className="regional-chart-body"><div className="regional-y-ticks">{[regionalChartMax, Math.ceil(regionalChartMax / 2), 0].map((tick, index) => <span key={`${tick}-${index}`}>{tick}</span>)}</div><div className="regional-chart-scroll" tabIndex="0" aria-label="Scroll monthly regional participation chart horizontally"><div className="regional-months">{regionalMonthly.map((month) => <div className="regional-month" key={month.key}><div className="regional-month-bars">{visibleRegions.map((region) => {
              const visibleStatuses = PARTICIPATION_CHART_STATUSES.filter((status) => regionalParticipationStatus === "ALL" || status === regionalParticipationStatus);
              return <div className="regional-bar-column" key={region}><div className="regional-bar-stack">{visibleStatuses.map((status) => {
                const count = month.regions[region][status];
                return <div key={status} className={`regional-bar-segment regional-segment-${status.toLowerCase()}`} style={{ height: `${count / regionalChartMax * 100}%` }} title={`${month.label} · ${region} · ${status} · ${count} tenders`} />;
              })}</div><span>{region}</span></div>;
            })}</div><span className="regional-month-label">{month.label}</span></div>)}</div></div></div></div> : <div className="overview-chart-empty">No dated tenders with a recognized region match the selected filters.</div>}
          </section>
          <div className="overview-tables-grid">
            <OverviewTable title="Closing in the next 3 days" icon={CalendarClock} tenders={closingSoon} navigate={navigate} emptyText={loading ? "Loading tenders…" : error ? "Overview data could not be loaded." : "No tenders are closing in this window."} />
            <OverviewTable title="Review pending" icon={ClipboardList} tenders={notReviewed} navigate={navigate} emptyText={loading ? "Loading tenders…" : error ? "Overview data could not be loaded." : "All matching tenders have been reviewed."} />
          </div>
        </main>
      </div>
      <section className="overview-leadership" aria-labelledby="leadership-heading">
        <div className="overview-leadership-heading"><div><span className="overview-eyebrow">DECISION SUPPORT</span><h2 id="leadership-heading">Leadership insights</h2><p>Portfolio signals from the tenders currently in view. These figures respond to the filters above.</p></div></div>
        <div className="overview-insight-grid">
          <article className="overview-insight-card"><span className="insight-icon insight-blue"><Gauge size={17} /></span><div><span className="overview-insight-label">Review coverage</span><strong>{loading || error ? "—" : `${leadership.reviewRate}%`}</strong><p>{error ? "Unavailable because overview data could not be loaded." : `${leadership.reviewed} reviewed of ${filteredTenders.length} matching tenders`}</p></div></article>
          <article className="overview-insight-card"><span className="insight-icon insight-green"><CircleCheck size={17} /></span><div><span className="overview-insight-label">Participation rate</span><strong>{loading || error ? "—" : `${leadership.participationRate}%`}</strong><p>Participated among reviewed tenders</p></div></article>
          <article className="overview-insight-card"><span className="insight-icon insight-amber"><Target size={17} /></span><div><span className="overview-insight-label">High score, awaiting review</span><strong>{loading || error ? "—" : leadership.highScorePending}</strong><p>Pending tenders scored 70 or higher</p></div></article>
          <article className="overview-insight-card"><span className="insight-icon insight-red"><Clock3 size={17} /></span><div><span className="overview-insight-label">Pending, due within 7 days</span><strong>{loading || error ? "—" : leadership.urgentPending}</strong><p>Review queue with an approaching deadline</p></div></article>
          <article className="overview-insight-card overview-source-insight"><div className="overview-source-heading"><span className="insight-icon insight-violet"><Building2 size={17} /></span><div><span className="overview-insight-label">Tender mix by portal</span><p>Matching tenders by source</p></div></div>
            {leadership.portals.length ? <div className="overview-source-list">{leadership.portals.map(([name, count]) => <div className="overview-source-row" key={name}><div><span>{name}</span><strong>{count}</strong></div><div className="overview-source-track"><i style={{ width: `${count / Math.max(1, filteredTenders.length) * 100}%` }} /></div></div>)}</div> : <p className="overview-source-empty">No portal data for the current filters.</p>}
          </article>
        </div>
      </section>
    </div>
  );
}

export default Overview;
