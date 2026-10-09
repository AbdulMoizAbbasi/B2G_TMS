import { useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Building2, CalendarClock, CircleCheck, ClipboardList, Clock3, Filter, Gauge, Package, RotateCcw, Target } from "lucide-react";
import api from "../api";
import "./Overview.css";

const STATUSES = ["ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING", "NOT_REVIEWED"];
const CHART_STATUSES = ["NOT_REVIEWED", "ENGAGING", "PARTICIPATED", "NOT_PARTICIPATING"];
const REGIONS = ["North1", "North2", "Central", "South"];
const STATUS_LABELS = { ENGAGING: "Engaging", PARTICIPATED: "Participated", NOT_PARTICIPATING: "Not Participating", NOT_REVIEWED: "Review Pending" };
const SCORE_BANDS = [
  { id: "high", label: "High · 70–100", min: 70, max: 100 },
  { id: "medium", label: "Medium · 40–69", min: 40, max: 69.999 },
  { id: "low", label: "Low · 1–39", min: 1, max: 39.999 },
  { id: "zero", label: "No score", min: 0, max: 0 },
];

function MultiSelect({ title, icon: Icon, options, selected, onChange, placeholder, disabled = false, single = false, open, setOpen }) {
  const toggle = (value) => onChange(single
    ? (selected[0] === value ? [] : [value])
    : (selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value]));
  return <div className="overview-filter-group">
    <div className="overview-filter-label"><span><Icon size={15} />{title}</span><button className="overview-filter-clear" type="button" onClick={() => onChange([])} disabled={!selected.length}>Clear</button></div>
    <button className="overview-select-trigger" type="button" onClick={() => setOpen(!open)} disabled={disabled} aria-expanded={open}>
      <span>{selected.length ? `${selected.length} selected` : placeholder}</span><span className="overview-select-chevron">{open ? "−" : "+"}</span>
    </button>
    {open && <div className="overview-select-options">{options.length ? options.map((option) => <label className="overview-check-option" key={option.value}>
      <input type="checkbox" checked={selected.includes(option.value)} onChange={() => toggle(option.value)} /><span>{option.label}</span>
    </label>) : <span className="overview-options-empty">No options available</span>}</div>}
  </div>;
}

function Overview() {
  const [overview, setOverview] = useState(null);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [productsLoading, setProductsLoading] = useState(true);
  const [error, setError] = useState("");
  const [closingRange, setClosingRange] = useState({ from: "", to: "" });
  const [advertisedRange, setAdvertisedRange] = useState({ from: "", to: "" });
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [selectedScores, setSelectedScores] = useState([]);
  const [selectedStatuses, setSelectedStatuses] = useState([]);
  const [selectedRegions, setSelectedRegions] = useState([]);
  const [openFilter, setOpenFilter] = useState(null);
  const [regionalParticipationStatus, setRegionalParticipationStatus] = useState("ALL");
  const [regionalRegion, setRegionalRegion] = useState("ALL");

  useEffect(() => {
    let active = true;
    api.get("/api/products").then((response) => {
      if (active) setProducts(Array.isArray(response.data) ? response.data : []);
    }).catch(() => {
      if (active) setProducts([]);
    }).finally(() => { if (active) setProductsLoading(false); });
    return () => { active = false; };
  }, []);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (closingRange.from) params.append("closing_date_from", closingRange.from);
    if (closingRange.to) params.append("closing_date_to", closingRange.to);
    if (advertisedRange.from) params.append("advertised_date_from", advertisedRange.from);
    if (advertisedRange.to) params.append("advertised_date_to", advertisedRange.to);
    selectedProducts.forEach((value) => params.append("product_id", value));
    selectedStatuses.forEach((value) => params.append("status", value));
    selectedRegions.forEach((value) => params.append("region", value));
    const bands = selectedScores.map((id) => SCORE_BANDS.find((band) => band.id === id)).filter(Boolean);
    if (bands.length) {
      params.append("score_min", Math.min(...bands.map((band) => band.min)));
      params.append("score_max", Math.max(...bands.map((band) => band.max)));
    }
    return params;
  }, [closingRange, advertisedRange, selectedProducts, selectedStatuses, selectedRegions, selectedScores]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    setOverview(null);
    api.get(`/api/overview?${query}`).then((response) => {
      if (active) setOverview(response.data);
    }).catch((err) => {
      if (active) setError(err.response?.data?.detail || "Unable to load overview data.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [query]);

  const leadership = overview?.leadership ?? {
    reviewed: 0,
    review_rate: 0,
    participation_rate: 0,
    high_score_pending: 0,
    urgent_pending: 0,
    portals: [],
  };

  const monthly = useMemo(() => (overview?.monthly_activity || []).map((item) => ({
    ...item,
    key: `${item.year}-${String(item.month).padStart(2, "0")}`,
    label: new Intl.DateTimeFormat("en", { month: "short", year: "2-digit" }).format(new Date(item.year, item.month - 1, 1)),
    notParticipating: item.not_participating,
    notReviewed: item.not_reviewed,
  })), [overview]);
  const regionalMonthly = useMemo(() => (overview?.monthly_regional || []).map((item) => ({
    ...item,
    key: `${item.year}-${String(item.month).padStart(2, "0")}`,
    label: new Intl.DateTimeFormat("en", { month: "short", year: "2-digit" }).format(new Date(item.year, item.month - 1, 1)),
    regions: item.regions || {},
  })), [overview]);
  const visibleRegions = regionalRegion === "ALL" ? REGIONS : [regionalRegion];
  const visibleStatuses = CHART_STATUSES.filter((status) => regionalParticipationStatus === "ALL" || status === regionalParticipationStatus);
  const regionalChartMax = Math.max(1, ...regionalMonthly.flatMap((month) => visibleRegions.map((region) =>
    visibleStatuses.reduce((total, status) => total + (month.regions[region]?.[status] || 0), 0))));
  const chartMax = Math.max(1, ...monthly.map((item) => item.total ?? (item.engaging + item.participated + item.notParticipating + item.notReviewed)));
  const clearFilters = () => {
    setClosingRange({ from: "", to: "" }); setAdvertisedRange({ from: "", to: "" });
    setSelectedProducts([]); setSelectedScores([]); setSelectedStatuses([]); setSelectedRegions([]);
  };

  return <div className="overview-page">
    <header className="overview-header"><div><span className="overview-eyebrow">TENDER WORKSPACE</span><h1>Overview</h1><p>Monitor tender activity, deadlines, and participation at a glance.</p></div><div className="overview-header-count"><strong>{loading || error ? "—" : overview?.summary?.total ?? 0}</strong><span>matching tenders</span></div></header>
    {error && <div className="overview-error" role="alert">{error}</div>}
    <section className="overview-kpis" aria-label="Tender summary">{[
      { title: "Total Tenders Received", value: overview?.summary?.total, icon: ClipboardList, tone: "blue" },
      { title: "Tender Review Pending", value: overview?.summary?.pending, icon: Target, tone: "amber" },
      { title: "Engaging", value: overview?.summary?.engaging, icon: ArrowUpRight, tone: "green" },
      { title: "Participated", value: overview?.summary?.participated, icon: CircleCheck, tone: "violet" },
      { title: "Not Participating", value: overview?.summary?.not_participating, icon: RotateCcw, tone: "red" },
      { title: "Closing in Next 3 Days", value: overview?.summary?.closing, icon: CalendarClock, tone: "violet" },
    ].map(({ title, value, icon: Icon, tone }) => <article className={`overview-kpi kpi-${tone}`} key={title}><span className="overview-kpi-icon"><Icon size={18} /></span><span className="overview-kpi-label">{title}</span><strong>{loading || error ? "—" : value ?? 0}</strong><small>Based on current filters</small></article>)}</section>
    <div className="overview-workspace">
      <aside className="overview-filters overview-panel">
        <div className="overview-filter-header"><div><span className="overview-panel-icon"><Filter size={17} /></span><h2>Filters</h2></div><button type="button" onClick={clearFilters}>Clear all</button></div>
        <div className="overview-date-filter"><div className="overview-date-heading"><span>Closing date</span><button className="overview-filter-clear" type="button" onClick={() => setClosingRange({ from: "", to: "" })} disabled={!closingRange.from && !closingRange.to}>Clear</button></div><label>From<input type="date" value={closingRange.from} onChange={(event) => setClosingRange((value) => ({ ...value, from: event.target.value }))} /></label><label>To<input type="date" value={closingRange.to} onChange={(event) => setClosingRange((value) => ({ ...value, to: event.target.value }))} /></label></div>
        <div className="overview-date-filter"><div className="overview-date-heading"><span>Advertised date</span><button className="overview-filter-clear" type="button" onClick={() => setAdvertisedRange({ from: "", to: "" })} disabled={!advertisedRange.from && !advertisedRange.to}>Clear</button></div><label>From<input type="date" value={advertisedRange.from} onChange={(event) => setAdvertisedRange((value) => ({ ...value, from: event.target.value }))} /></label><label>To<input type="date" value={advertisedRange.to} onChange={(event) => setAdvertisedRange((value) => ({ ...value, to: event.target.value }))} /></label></div>
        <MultiSelect title="Region" icon={Filter} placeholder="Select regions" options={REGIONS.map((value) => ({ value, label: value }))} selected={selectedRegions} onChange={setSelectedRegions} open={openFilter === "region"} setOpen={(open) => setOpenFilter(open ? "region" : null)} />
        <MultiSelect title="Products" icon={Package} placeholder={productsLoading ? "Loading products…" : "Select products"} disabled={productsLoading} options={products.map((product) => ({ value: String(product.id), label: product.name }))} selected={selectedProducts} onChange={setSelectedProducts} open={openFilter === "products"} setOpen={(open) => setOpenFilter(open ? "products" : null)} />
        <MultiSelect title="Relevance score" icon={Target} placeholder="Select score range" options={SCORE_BANDS.map(({ id, label }) => ({ value: id, label }))} selected={selectedScores} onChange={setSelectedScores} open={openFilter === "score"} setOpen={(open) => setOpenFilter(open ? "score" : null)} />
        <MultiSelect title="Participation status" icon={ClipboardList} placeholder="Select status" options={STATUSES.map((value) => ({ value, label: STATUS_LABELS[value] }))} selected={selectedStatuses} onChange={setSelectedStatuses} open={openFilter === "status"} setOpen={(open) => setOpenFilter(open ? "status" : null)} />
        {loading && <div className="overview-filter-note">Loading overview data…</div>}
      </aside>
      <main className="overview-main">
        <section className="overview-panel overview-chart-panel">
          <div className="overview-panel-heading"><div className="overview-panel-title"><span className="overview-panel-icon"><CalendarClock size={17} /></span><div><h2>Monthly tender activity</h2><p>Grouped by advertised month, with closing month as a fallback</p></div></div><span className="overview-chart-total">{loading || error ? "—" : overview?.summary?.total ?? 0} total</span></div>
          <div className="overview-chart-legend"><span><i className="legend-participating" />Engaging</span><span><i className="legend-participated" />Participated</span><span><i className="legend-not-reviewed" />Not Reviewed</span><span><i className="legend-not-participating" />Not Participating</span></div>
          {loading ? <div className="overview-chart-empty">Loading overview data…</div> : error ? <div className="overview-chart-empty">Overview data could not be loaded.</div> : monthly.length ? <div className="overview-chart-scroll"><div className="overview-chart" role="img" aria-label="Monthly tender counts by participation status"><div className="overview-y-label">Tender count</div><div className="overview-chart-body"><div className="overview-y-ticks">{[chartMax, Math.ceil(chartMax / 2), 0].map((tick, index) => <span key={`${tick}-${index}`}>{tick}</span>)}</div><div className="overview-plot">{monthly.map((item) => <div className="overview-month" key={item.key}><div className="overview-bar-stack" title={`${item.label}: ${item.engaging} engaging, ${item.participated} participated, ${item.notReviewed} not reviewed, ${item.notParticipating} not participating`}><div className="overview-bar-participating" style={{ height: `${item.engaging / chartMax * 100}%` }} /><div className="overview-bar-participated" style={{ height: `${item.participated / chartMax * 100}%` }} /><div className="overview-bar-not-participating" style={{ height: `${item.notParticipating / chartMax * 100}%` }} /><div className="overview-bar-not-reviewed" style={{ height: `${item.notReviewed / chartMax * 100}%` }} /></div><span>{item.label}</span></div>)}</div></div></div></div> : <div className="overview-chart-empty">No monthly activity for the selected filters.</div>}
        </section>
        <section className="overview-panel overview-chart-panel regional-participation-panel">
          <div className="overview-panel-heading"><div className="overview-panel-title"><span className="overview-panel-icon"><CalendarClock size={17} /></span><div><h2>Monthly Regional Participation</h2><p>Grouped by advertised month, with closing month as a fallback</p></div></div><div className="regional-chart-filters"><label className="regional-status-filter">Region<select value={regionalRegion} onChange={(event) => setRegionalRegion(event.target.value)}><option value="ALL">All Regions</option>{REGIONS.map((region) => <option key={region} value={region}>{region}</option>)}</select></label><label className="regional-status-filter">Participation Status<select value={regionalParticipationStatus} onChange={(event) => setRegionalParticipationStatus(event.target.value)}><option value="ALL">All</option>{CHART_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}</select></label></div></div>
          <div className="overview-chart-legend regional-chart-legend">{CHART_STATUSES.map((status) => <span key={status}><i className={`regional-legend-${status.toLowerCase()}`} />{status.replaceAll("_", " ")}</span>)}</div>
          {loading ? <div className="overview-chart-empty">Loading overview data…</div> : error ? <div className="overview-chart-empty">Overview data could not be loaded.</div> : regionalMonthly.length ? <div className="regional-chart"><div className="overview-y-label">Number of tenders</div><div className="regional-chart-body"><div className="regional-y-ticks">{[regionalChartMax, Math.ceil(regionalChartMax / 2), 0].map((tick, index) => <span key={`${tick}-${index}`}>{tick}</span>)}</div><div className="regional-chart-scroll" tabIndex="0" aria-label="Scroll monthly regional participation chart horizontally"><div className="regional-months">{regionalMonthly.map((month) => <div className="regional-month" key={month.key}><div className="regional-month-bars">{visibleRegions.map((region) => <div className="regional-bar-column" key={region}><div className="regional-bar-stack">{visibleStatuses.map((status) => { const count = month.regions[region]?.[status] || 0; return <div key={status} className={`regional-bar-segment regional-segment-${status.toLowerCase()}`} style={{ height: `${count / regionalChartMax * 100}%` }} title={`${month.label} · ${region} · ${status} · ${count} tenders`} />; })}</div><span>{region}</span></div>)}</div><span className="regional-month-label">{month.label}</span></div>)}</div></div></div></div> : <div className="overview-chart-empty">No regional activity for the selected filters.</div>}
        </section>
      </main>
    </div>
    <section className="overview-leadership" aria-labelledby="leadership-heading"><div className="overview-leadership-heading"><div><span className="overview-eyebrow">DECISION SUPPORT</span><h2 id="leadership-heading">Leadership insights</h2><p>Portfolio signals from the tenders currently in view. These figures respond to the filters above.</p></div></div>
      <div className="overview-insight-grid">
        <article className="overview-insight-card"><span className="insight-icon insight-blue"><Gauge size={17} /></span><div><span className="overview-insight-label">Review coverage</span><strong>{loading || error ? "—" : `${leadership.review_rate}%`}</strong><p>{error ? "Unavailable because overview data could not be loaded." : `${leadership.reviewed} reviewed of ${overview?.summary?.total ?? 0} matching tenders`}</p></div></article>
        <article className="overview-insight-card"><span className="insight-icon insight-green"><CircleCheck size={17} /></span><div><span className="overview-insight-label">Participation rate</span><strong>{loading || error ? "—" : `${leadership.participation_rate}%`}</strong><p>Participated among reviewed tenders</p></div></article>
        <article className="overview-insight-card"><span className="insight-icon insight-amber"><Target size={17} /></span><div><span className="overview-insight-label">High score, awaiting review</span><strong>{loading || error ? "—" : leadership.high_score_pending}</strong><p>Pending tenders scored 70 or higher</p></div></article>
        <article className="overview-insight-card"><span className="insight-icon insight-red"><Clock3 size={17} /></span><div><span className="overview-insight-label">Pending, due within 7 days</span><strong>{loading || error ? "—" : leadership.urgent_pending}</strong><p>Review queue with an approaching deadline</p></div></article>
        <article className="overview-insight-card overview-source-insight"><div className="overview-source-heading"><span className="insight-icon insight-violet"><Building2 size={17} /></span><div><span className="overview-insight-label">Tender mix by portal</span><p>Matching tenders by source</p></div></div>{error ? <p className="overview-source-empty">Overview data could not be loaded.</p> : leadership.portals.length ? <div className="overview-source-list">{leadership.portals.map(({ source, count }) => <div className="overview-source-row" key={source}><div><span>{source}</span><strong>{count}</strong></div><div className="overview-source-track"><i style={{ width: `${count / Math.max(1, overview?.summary?.total || 0) * 100}%` }} /></div></div>)}</div> : <p className="overview-source-empty">{loading ? "Loading overview data…" : "No portal data for the current filters."}</p>}</article>
      </div>
    </section>
  </div>;
}

export default Overview;
