import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Trash2,
  Pencil,
  Save,
  Ban,
  Clock3,
  ClipboardList,
  ChevronDown,
  Check,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../auth/AuthContext";

function displayValue(value) {
  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {
    return "—";
  }

  return String(value);
}

function isUrl(value) {
  return (
    typeof value === "string" &&
    /^https?:\/\//i.test(value)
  );
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return displayValue(value);
  }

  return date.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function toDateInputValue(value) {
  if (!value) {
    return "";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "";
  }

  return date.toISOString().split("T")[0];
}

function TenderDetail() {
  const { user } = useAuth();

  const { tenderId } = useParams();
  const navigate = useNavigate();

  const isAdmin = user?.role === "ADMIN";
  const isCoordinator =
    user?.role === "COORDINATOR";

  const [tender, setTender] = useState(null);

  /*
   * ---------------------------------------------------------
   * Participation
   * ---------------------------------------------------------
   */

  const [participation, setParticipation] =
    useState("NOT_REVIEWED");

  const [participationLoading, setParticipationLoading] =
    useState(false);

  const [delegatedEmployeeId, setDelegatedEmployeeId] =
    useState(null);

  const [delegatedEmployeeName, setDelegatedEmployeeName] =
    useState(null);

  const [employees, setEmployees] =
    useState([]);

  const [products, setProducts] =
    useState([]);

  const [selectedProductIds, setSelectedProductIds] =
    useState([]);

  const [participationError, setParticipationError] =
    useState("");

  /*
   * ---------------------------------------------------------
   * Product dropdown
   * ---------------------------------------------------------
   */

  const [productDropdownOpen, setProductDropdownOpen] =
    useState(false);

  const productDropdownRef = useRef(null);

  /*
   * ---------------------------------------------------------
   * Coordinator participation edit mode
   * ---------------------------------------------------------
   */

  const [participationEditMode, setParticipationEditMode] =
    useState(false);

  /*
   * ---------------------------------------------------------
   * Tender / page state
   * ---------------------------------------------------------
   */

  const [deleteLoading, setDeleteLoading] =
    useState(false);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState("");

  /*
   * ---------------------------------------------------------
   * Edit state
   * ---------------------------------------------------------
   */

  const [editMode, setEditMode] =
    useState(false);

  const [editValues, setEditValues] =
    useState({});

  const [editLoading, setEditLoading] =
    useState(false);

  const [editError, setEditError] =
    useState("");

  /*
   * ---------------------------------------------------------
   * Fetch tender
   * ---------------------------------------------------------
   */

  useEffect(() => {
    const fetchTender = async () => {
      try {
        const response = await api.get(
          `/api/tenders/${tenderId}`
        );

        setTender(response.data);
      } catch (err) {
        console.error(err);

        setError(
          "Failed to load tender details."
        );
      } finally {
        setLoading(false);
      }
    };

    fetchTender();
  }, [tenderId]);

  /*
   * ---------------------------------------------------------
   * Fetch participation
   * ---------------------------------------------------------
   */

  useEffect(() => {
    const fetchParticipation = async () => {
      try {
        setParticipationError("");

        const response = await api.get(
          `/api/tenders/${tenderId}/participation`
        );

        setParticipation(
          response.data.status
        );

        setDelegatedEmployeeId(
          response.data.delegated_employee_id
        );

        setDelegatedEmployeeName(
          response.data.delegated_employee_name
        );

        const productIds =
          Array.isArray(
            response.data.product_ids
          )
            ? response.data.product_ids.map(
                (id) => Number(id)
              )
            : [];

        setSelectedProductIds(
          productIds
        );
      } catch (err) {
        console.error(
          "Failed to load participation:",
          err
        );

        setParticipationError(
          err.response?.data?.detail ||
            "Failed to load participation status."
        );
      }
    };

    fetchParticipation();
  }, [tenderId]);

  /*
   * ---------------------------------------------------------
   * Fetch employees for Coordinator
   * ---------------------------------------------------------
   */

  useEffect(() => {
    if (!isCoordinator) {
      return;
    }

    const fetchEmployees = async () => {
      try {
        const response = await api.get(
          "/api/employees"
        );

        setEmployees(response.data);
      } catch (err) {
        console.error(
          "Failed to load employees:",
          err
        );

        setParticipationError(
          err.response?.data?.detail ||
            "Failed to load employees."
        );
      }
    };

    fetchEmployees();
  }, [isCoordinator]);

  /*
  * ---------------------------------------------------------
  * Fetch products
  * ---------------------------------------------------------
  */

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await api.get(
          "/api/products"
        );

        setProducts(response.data);
      } catch (err) {
        console.error(
          "Failed to load products:",
          err
        );

        if (isCoordinator) {
          setParticipationError(
            err.response?.data?.detail ||
              "Failed to load products."
          );
        }
      }
    };

    fetchProducts();
  }, [isCoordinator]);

  /*
   * ---------------------------------------------------------
   * Close product dropdown when clicking outside
   * ---------------------------------------------------------
   */

  useEffect(() => {
    function handleClickOutside(event) {
      if (
        productDropdownRef.current &&
        !productDropdownRef.current.contains(
          event.target
        )
      ) {
        setProductDropdownOpen(false);
      }
    }

    document.addEventListener(
      "mousedown",
      handleClickOutside
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleClickOutside
      );
    };
  }, []);

  /*
   * ---------------------------------------------------------
   * Edit tender
   * ---------------------------------------------------------
   */

  function startEditing() {
    if (!tender) {
      return;
    }

    setEditError("");

    setEditValues({
      web_tender_no:
        tender.web_tender_no ?? "",

      tender_reference_no:
        tender.tender_reference_no ?? "",

      tender_name:
        tender.tender_name ?? "",

      city:
        tender.city ?? "",

      authority:
        tender.authority ?? "",

      organization:
        tender.organization ?? "",

      estimated_value:
        tender.estimated_value ?? "",

      advertised_date:
        toDateInputValue(
          tender.advertised_date
        ),

      closed_date:
        toDateInputValue(
          tender.closed_date
        ),

      relevance_score:
        tender.relevance_score ?? "",
    });

    setEditMode(true);
  }

  function cancelEditing() {
    setEditMode(false);
    setEditValues({});
    setEditError("");
  }

  function handleEditChange(
    field,
    value
  ) {
    setEditValues((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleSaveChanges() {
    if (editLoading) {
      return;
    }

    try {
      setEditLoading(true);
      setEditError("");

      const payload = {
        web_tender_no:
          editValues.web_tender_no || null,

        tender_reference_no:
          editValues.tender_reference_no || null,

        tender_name:
          editValues.tender_name || null,

        city:
          editValues.city || null,

        authority:
          editValues.authority || null,

        organization:
          editValues.organization || null,

        estimated_value:
          editValues.estimated_value === ""
            ? null
            : Number(
                editValues.estimated_value
              ),

        advertised_date:
          editValues.advertised_date
            ? `${editValues.advertised_date}T00:00:00`
            : null,

        closed_date:
          editValues.closed_date
            ? `${editValues.closed_date}T00:00:00`
            : null,

        relevance_score:
          editValues.relevance_score === ""
            ? null
            : Number(
                editValues.relevance_score
              ),
      };

      await api.put(
        `/api/tenders/${encodeURIComponent(
          tenderId
        )}`,
        payload
      );

      const response = await api.get(
        `/api/tenders/${tenderId}`
      );

      setTender(response.data);

      setEditMode(false);
      setEditValues({});
    } catch (err) {
      console.error(err);

      setEditError(
        err.response?.data?.detail ||
          "Failed to update tender."
      );
    } finally {
      setEditLoading(false);
    }
  }

  /*
   * ---------------------------------------------------------
   * Participation edit mode
   * ---------------------------------------------------------
   */

  function startParticipationEditing() {
    setParticipationError("");
    setParticipationEditMode(true);
  }

  function cancelParticipationEditing() {
    const reloadParticipation = async () => {
      try {
        setParticipationError("");

        const response = await api.get(
          `/api/tenders/${tenderId}/participation`
        );

        setParticipation(
          response.data.status
        );

        setDelegatedEmployeeId(
          response.data.delegated_employee_id
        );

        setDelegatedEmployeeName(
          response.data.delegated_employee_name
        );

        const productIds =
          Array.isArray(
            response.data.product_ids
          )
            ? response.data.product_ids.map(
                (id) => Number(id)
              )
            : [];

        setSelectedProductIds(
          productIds
        );

        setProductDropdownOpen(false);
      } catch (err) {
        console.error(
          "Failed to restore participation:",
          err
        );

        setParticipationError(
          err.response?.data?.detail ||
            "Failed to restore participation."
        );
      } finally {
        setParticipationEditMode(false);
      }
    };

    reloadParticipation();
  }

  /*
   * ---------------------------------------------------------
   * Participation status selection
   * ---------------------------------------------------------
   */

  async function handleParticipationChange(
    newStatus
  ) {
    if (participationLoading) {
      return;
    }

    if (newStatus === "PARTICIPATING") {
      setParticipation(
        "PARTICIPATING"
      );

      setParticipationError("");

      return;
    }

    try {
      setParticipationLoading(true);
      setParticipationError("");

      const response = await api.put(
        `/api/tenders/${tenderId}/participation`,
        {
          status: newStatus,
        }
      );

      setParticipation(
        response.data.status
      );

      setDelegatedEmployeeId(
        response.data.delegated_employee_id
      );

      setDelegatedEmployeeName(
        response.data.delegated_employee_name ||
          null
      );

      const returnedProductIds =
        Array.isArray(
          response.data.product_ids
        )
          ? response.data.product_ids.map(
              (id) => Number(id)
            )
          : [];

      setSelectedProductIds(
        returnedProductIds
      );

      if (
        newStatus !== "PARTICIPATING"
      ) {
        setDelegatedEmployeeId(
          null
        );

        setDelegatedEmployeeName(
          null
        );

        setSelectedProductIds([]);
      }

      setProductDropdownOpen(false);
      setParticipationEditMode(false);
    } catch (err) {
      console.error(err);

      setParticipationError(
        err.response?.data?.detail ||
          "Failed to update participation status."
      );
    } finally {
      setParticipationLoading(false);
    }
  }

  /*
   * ---------------------------------------------------------
   * Save PARTICIPATING
   * ---------------------------------------------------------
   */

  async function handleSaveParticipation() {
    if (participationLoading) {
      return;
    }

    if (!delegatedEmployeeId) {
      setParticipationError(
        "Please select a JBC / Employee before saving participation."
      );

      return;
    }

    if (
      !selectedProductIds ||
      selectedProductIds.length === 0
    ) {
      setParticipationError(
        "Please select at least one product before saving participation."
      );

      return;
    }

    try {
      setParticipationLoading(true);
      setParticipationError("");

      const response = await api.put(
        `/api/tenders/${tenderId}/participation`,
        {
          status: "PARTICIPATING",

          employee_id:
            Number(
              delegatedEmployeeId
            ),

          product_ids:
            selectedProductIds.map(
              (id) => Number(id)
            ),
        }
      );

      setParticipation(
        response.data.status
      );

      setDelegatedEmployeeId(
        response.data.delegated_employee_id
      );

      setDelegatedEmployeeName(
        response.data.delegated_employee_name ||
          null
      );

      const returnedProductIds =
        Array.isArray(
          response.data.product_ids
        )
          ? response.data.product_ids.map(
              (id) => Number(id)
            )
          : [];

      setSelectedProductIds(
        returnedProductIds
      );

      setParticipationError("");
      setProductDropdownOpen(false);
      setParticipationEditMode(false);
    } catch (err) {
      console.error(err);

      setParticipationError(
        err.response?.data?.detail ||
          "Failed to save participation."
      );
    } finally {
      setParticipationLoading(false);
    }
  }

  /*
   * ---------------------------------------------------------
   * JBC selection
   * ---------------------------------------------------------
   */

  function handleEmployeeChange(
    employeeId
  ) {
    if (participationLoading) {
      return;
    }

    if (!employeeId) {
      setDelegatedEmployeeId(null);
      setDelegatedEmployeeName(null);
      return;
    }

    const numericEmployeeId =
      Number(employeeId);

    const selectedEmployee =
      employees.find(
        (employee) =>
          Number(employee.id) ===
          numericEmployeeId
      );

    setDelegatedEmployeeId(
      numericEmployeeId
    );

    setDelegatedEmployeeName(
      selectedEmployee?.name || null
    );

    setParticipationError("");
  }

  /*
   * ---------------------------------------------------------
   * Product selection
   * ---------------------------------------------------------
   *
   * Custom multi-select.
   *
   * Clicking a product toggles it.
   * No Ctrl / Command key is required.
   */

  function handleProductToggle(
    productId
  ) {
    if (participationLoading) {
      return;
    }

    const numericProductId =
      Number(productId);

    setSelectedProductIds(
      (currentIds) => {
        if (
          currentIds.includes(
            numericProductId
          )
        ) {
          return currentIds.filter(
            (id) =>
              Number(id) !==
              numericProductId
          );
        }

        return [
          ...currentIds,
          numericProductId,
        ];
      }
    );

    setParticipationError("");
  }

  function getSelectedProductNames() {
    return selectedProductIds
      .map((productId) => {
        const product =
          products.find(
            (item) =>
              Number(item.id) ===
              Number(productId)
          );

        return product?.name;
      })
      .filter(Boolean);
  }

  /*
   * ---------------------------------------------------------
   * Delete tender
   * ---------------------------------------------------------
   */

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

  /*
   * ---------------------------------------------------------
   * Display helpers
   * ---------------------------------------------------------
   */

  function renderValue(value) {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "—";
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return "—";
      }

      return (
        <div className="detail-array">
          {value.map((item, index) => (
            <span
              className="tag"
              key={`${String(item)}-${index}`}
            >
              {String(item)}
            </span>
          ))}
        </div>
      );
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

  function renderEditInput(
    field,
    type = "text"
  ) {
    return (
      <input
        type={type}
        value={
          editValues[field] ?? ""
        }
        onChange={(event) =>
          handleEditChange(
            field,
            event.target.value
          )
        }
        className="detail-edit-input"
      />
    );
  }

  /*
   * ---------------------------------------------------------
   * Participation display
   * ---------------------------------------------------------
   */

  function getParticipationLabel() {
    switch (participation) {
      case "PARTICIPATING":
        return "Participating";

      case "UNDER_REVIEW":
        return "Under Review";

      case "NOT_PARTICIPATING":
        return "Not Participating";

      case "NOT_REVIEWED":
      default:
        return "Not Reviewed";
    }
  }

  function getParticipationStatusClass() {
    switch (participation) {
      case "PARTICIPATING":
        return "participating";

      case "UNDER_REVIEW":
        return "under-review";

      case "NOT_PARTICIPATING":
        return "not-participating";

      case "NOT_REVIEWED":
      default:
        return "not-reviewed";
    }
  }

  function getParticipationIcon() {
    switch (participation) {
      case "PARTICIPATING":
        return <CheckCircle2 size={16} />;

      case "UNDER_REVIEW":
        return <Clock3 size={16} />;

      case "NOT_PARTICIPATING":
        return <XCircle size={16} />;

      case "NOT_REVIEWED":
      default:
        return <ClipboardList size={16} />;
    }
  }

  function getProductName(productId) {
    const product =
      products.find(
        (item) =>
          Number(item.id) ===
          Number(productId)
      );

    return product?.name || null;
  }

  /*
   * ---------------------------------------------------------
   * Loading / error states
   * ---------------------------------------------------------
   */

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

  /*
   * ---------------------------------------------------------
   * Render
   * ---------------------------------------------------------
   */

  return (
    <div className="tender-detail-page">

      {/* Back */}

      <button
        className="back-button"
        onClick={() => navigate(-1)}
      >
        <ArrowLeft size={17} />
        Back to Tenders
      </button>

      {/* Header */}

      <div className="page-header">

        <div>
          {editMode ? (
            <>
              <input
                type="text"
                value={
                  editValues.tender_name ??
                  ""
                }
                onChange={(event) =>
                  handleEditChange(
                    "tender_name",
                    event.target.value
                  )
                }
                className="detail-title-input"
              />

              <p>
                Source:{" "}
                <strong>
                  {displayValue(
                    tender.source
                  )}
                </strong>
              </p>
            </>
          ) : (
            <>
              <h1>
                {displayValue(
                  tender.tender_name
                )}
              </h1>

              <p>
                Source:{" "}
                <strong>
                  {displayValue(
                    tender.source
                  )}
                </strong>
              </p>
            </>
          )}
        </div>

        {isAdmin && !editMode && (
          <button
            type="button"
            className="edit-tender-button"
            onClick={startEditing}
          >
            <Pencil size={16} />
            Edit Tender
          </button>
        )}

        {isAdmin && editMode && (
          <div className="edit-actions">

            <button
              type="button"
              className="cancel-edit-button"
              onClick={cancelEditing}
              disabled={editLoading}
            >
              <Ban size={16} />
              Cancel
            </button>

            <button
              type="button"
              className="save-edit-button"
              onClick={handleSaveChanges}
              disabled={editLoading}
            >
              <Save size={16} />

              {editLoading
                ? "Saving..."
                : "Save Changes"}
            </button>

          </div>
        )}

      </div>

      {editError && (
        <div className="edit-error">
          {editError}
        </div>
      )}

      {/* Tender Summary */}

      <div className="detail-card">

        <h2>
          Tender Information
        </h2>

        <div className="detail-grid">

          <div className="detail-item">
            <span>
              Web Tender No
            </span>

            {editMode ? (
              renderEditInput(
                "web_tender_no"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.web_tender_no
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Tender Reference No
            </span>

            {editMode ? (
              renderEditInput(
                "tender_reference_no"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.tender_reference_no
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Tender Name
            </span>

            {editMode ? (
              renderEditInput(
                "tender_name"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.tender_name
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              City
            </span>

            {editMode ? (
              renderEditInput("city")
            ) : (
              <strong>
                {displayValue(
                  tender.city
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Authority
            </span>

            {editMode ? (
              renderEditInput(
                "authority"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.authority
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Organization
            </span>

            {editMode ? (
              renderEditInput(
                "organization"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.organization
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Estimated Value
            </span>

            {editMode ? (
              renderEditInput(
                "estimated_value",
                "number"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.estimated_value
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Advertised Date
            </span>

            {editMode ? (
              renderEditInput(
                "advertised_date",
                "date"
              )
            ) : (
              <strong>
                {formatDate(
                  tender.advertised_date
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Closed Date
            </span>

            {editMode ? (
              renderEditInput(
                "closed_date",
                "date"
              )
            ) : (
              <strong>
                {formatDate(
                  tender.closed_date
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Source
            </span>

            <strong>
              {displayValue(
                tender.source
              )}
            </strong>
          </div>

          <div className="detail-item">
            <span>
              Region
            </span>

            <strong>
              {displayValue(
                tender.region
              )}
            </strong>
          </div>

          <div className="detail-item">
            <span>
              Jazz ID
            </span>

            <strong>
              {displayValue(
                tender.jazzid
              )}
            </strong>
          </div>

        </div>

      </div>

      {/* Relevance */}

      <div className="detail-card">

        <h2>
          Relevance
        </h2>

        <div className="detail-grid">

          <div className="detail-item">
            <span>
              Relevance Score
            </span>

            {editMode ? (
              renderEditInput(
                "relevance_score",
                "number"
              )
            ) : (
              <strong>
                {displayValue(
                  tender.relevance_score
                )}
              </strong>
            )}
          </div>

          <div className="detail-item">
            <span>
              Matched Keywords
            </span>

            <strong>
              {tender.keywords_matched?.length
                ? tender.keywords_matched.join(
                    ", "
                  )
                : "—"}
            </strong>
          </div>

          <div className="detail-item">
            <span>
              Matched Capabilities
            </span>

            <strong>
              {tender.matched_capabilities?.length
                ? tender.matched_capabilities.join(
                    ", "
                  )
                : "—"}
            </strong>
          </div>

        </div>

      </div>

      {/* Source / Documents */}

      <div className="detail-card">

        <h2>
          Source & Documents
        </h2>

        <div className="detail-grid">

          <div className="detail-item">
            <span>
              Source Detail
            </span>

            <strong>
              {tender.source_detail_url ? (
                <a
                  href={
                    tender.source_detail_url
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="detail-link"
                >
                  Open Source Tender
                  <ExternalLink
                    size={14}
                  />
                </a>
              ) : (
                "—"
              )}
            </strong>
          </div>

          <div className="detail-item">
            <span>
              Primary Document
            </span>

            <strong>
              {tender.primary_document_url ? (
                <a
                  href={
                    tender.primary_document_url
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="detail-link"
                >
                  Open Document
                  <ExternalLink
                    size={14}
                  />
                </a>
              ) : (
                "—"
              )}
            </strong>
          </div>

        </div>

      </div>

      {/* Participation */}

      <div className="detail-card participation-card">

        <div className="participation-header">

          <div>
            <h2>
              Participation
            </h2>

            <p>
              Participation status for this
              tender.
            </p>
          </div>

          <div
            className={`participation-status ${getParticipationStatusClass()}`}
          >
            {getParticipationIcon()}

            {getParticipationLabel()}
          </div>

        </div>

        {/* --------------------------------------------------
            Coordinator read-only view
            -------------------------------------------------- */}

        {isCoordinator &&
          !participationEditMode && (
            <div className="participation-summary">

              <div className="participation-summary-grid">

                {/* Status */}

                <div className="participation-summary-item">

                  <span className="participation-summary-label">
                    Status
                  </span>

                  <div
                    className={`participation-summary-status ${getParticipationStatusClass()}`}
                  >
                    {getParticipationIcon()}
                    {getParticipationLabel()}
                  </div>

                </div>

                {/* JBC */}

                <div className="participation-summary-item">

                  <span className="participation-summary-label">
                    Assigned JBC / Employee
                  </span>

                  <strong className="participation-summary-value">
                    {participation ===
                      "PARTICIPATING" &&
                    delegatedEmployeeName
                      ? delegatedEmployeeName
                      : "Not assigned"}
                  </strong>

                </div>

                {/* Products */}

                <div className="participation-summary-item participation-products-item">

                  <span className="participation-summary-label">
                    Products
                  </span>

                  {participation ===
                    "PARTICIPATING" &&
                  selectedProductIds.length >
                    0 ? (
                    <div className="participation-product-tags">
                      {selectedProductIds.map(
                        (productId) => {
                          const productName =
                            getProductName(
                              productId
                            );

                          return (
                            <span
                              className="participation-product-tag"
                              key={productId}
                            >
                              {productName ||
                                `Product ${productId}`}
                            </span>
                          );
                        }
                      )}
                    </div>
                  ) : (
                    <span className="participation-empty">
                      No products selected
                    </span>
                  )}

                </div>

              </div>

              {/* Edit */}

              <div className="participation-summary-actions">

                <button
                  type="button"
                  className="edit-participation-button"
                  onClick={
                    startParticipationEditing
                  }
                >
                  <Pencil size={16} />
                  Edit Participation
                </button>

              </div>

            </div>
          )}

        {/* --------------------------------------------------
            Coordinator edit view
            -------------------------------------------------- */}

        {isCoordinator &&
          participationEditMode && (
            <>
              <div className="participation-actions">

                {/* Not Reviewed */}

                <button
                  type="button"
                  className={`participation-button ${
                    participation ===
                    "NOT_REVIEWED"
                      ? "selected"
                      : ""
                  }`}
                  disabled={
                    participationLoading
                  }
                  onClick={() =>
                    handleParticipationChange(
                      "NOT_REVIEWED"
                    )
                  }
                >
                  <ClipboardList
                    size={16}
                  />

                  Not Reviewed
                </button>

                {/* Under Review */}

                <button
                  type="button"
                  className={`participation-button ${
                    participation ===
                    "UNDER_REVIEW"
                      ? "selected"
                      : ""
                  }`}
                  disabled={
                    participationLoading
                  }
                  onClick={() =>
                    handleParticipationChange(
                      "UNDER_REVIEW"
                    )
                  }
                >
                  <Clock3 size={16} />

                  Under Review
                </button>

                {/* Participating */}

                <button
                  type="button"
                  className={`participation-button ${
                    participation ===
                    "PARTICIPATING"
                      ? "selected"
                      : ""
                  }`}
                  disabled={
                    participationLoading
                  }
                  onClick={() =>
                    handleParticipationChange(
                      "PARTICIPATING"
                    )
                  }
                >
                  <CheckCircle2
                    size={16}
                  />

                  Participating
                </button>

                {/* Not Participating */}

                <button
                  type="button"
                  className={`participation-button ${
                    participation ===
                    "NOT_PARTICIPATING"
                      ? "selected"
                      : ""
                  }`}
                  disabled={
                    participationLoading
                  }
                  onClick={() =>
                    handleParticipationChange(
                      "NOT_PARTICIPATING"
                    )
                  }
                >
                  <XCircle size={16} />

                  Not Participating
                </button>

              </div>

              {/* PARTICIPATING DETAILS */}

              {participation ===
                "PARTICIPATING" && (
                <div className="participation-assignment">

                  {/* JBC */}

                  <div className="delegation-section">

                    <label
                      htmlFor="delegated-employee"
                    >
                      Assign JBC / Employee
                    </label>

                    <select
                      id="delegated-employee"
                      value={
                        delegatedEmployeeId ??
                        ""
                      }
                      onChange={(event) =>
                        handleEmployeeChange(
                          event.target.value
                        )
                      }
                      disabled={
                        participationLoading
                      }
                    >
                      <option value="">
                        Select JBC / Employee
                      </option>

                      {employees.map(
                        (employee) => (
                          <option
                            key={employee.id}
                            value={
                              employee.id
                            }
                          >
                            {employee.name}
                          </option>
                        )
                      )}
                    </select>

                  </div>

                  {/* Products */}

                  <div
                    className="delegation-section product-selection-section"
                    ref={productDropdownRef}
                  >
                    <label>
                      Select Product(s)
                    </label>

                    <button
                      type="button"
                      className={`product-multi-select ${
                        productDropdownOpen
                          ? "open"
                          : ""
                      }`}
                      onClick={() =>
                        setProductDropdownOpen(
                          (current) =>
                            !current
                        )
                      }
                      disabled={
                        participationLoading
                      }
                    >
                      <span className="product-multi-select-value">
                        {selectedProductIds.length ===
                        0 ? (
                          "Select Product(s)"
                        ) : (
                          <span className="product-selected-tags">
                            {getSelectedProductNames().map(
                              (productName) => (
                                <span
                                  className="product-selected-tag"
                                  key={
                                    productName
                                  }
                                >
                                  {productName}
                                </span>
                              )
                            )}
                          </span>
                        )}
                      </span>

                      <ChevronDown
                        size={17}
                        className={`product-multi-select-icon ${
                          productDropdownOpen
                            ? "rotated"
                            : ""
                        }`}
                      />
                    </button>

                    {productDropdownOpen && (
                      <div className="product-multi-select-menu">
                        {products.length ===
                        0 ? (
                          <div className="product-multi-select-empty">
                            No products available.
                          </div>
                        ) : (
                          products.map(
                            (product) => {
                              const isSelected =
                                selectedProductIds.includes(
                                  Number(
                                    product.id
                                  )
                                );

                              return (
                                <button
                                  type="button"
                                  key={
                                    product.id
                                  }
                                  className={`product-multi-select-option ${
                                    isSelected
                                      ? "selected"
                                      : ""
                                  }`}
                                  onClick={() =>
                                    handleProductToggle(
                                      product.id
                                    )
                                  }
                                  disabled={
                                    participationLoading
                                  }
                                >
                                  <span className="product-multi-select-checkbox">
                                    {isSelected && (
                                      <Check
                                        size={14}
                                      />
                                    )}
                                  </span>

                                  <span>
                                    {
                                      product.name
                                    }
                                  </span>
                                </button>
                              );
                            }
                          )
                        )}
                      </div>
                    )}

                    <span className="product-selection-help">
                      Click products to select
                      multiple.
                    </span>
                  </div>

                  {/* Requirements */}

                  {(!delegatedEmployeeId ||
                    selectedProductIds.length ===
                      0) && (
                    <div className="participation-requirement">

                      <strong>
                        Participating requires:
                      </strong>

                      <span
                        className={
                          delegatedEmployeeId
                            ? "requirement-complete"
                            : "requirement-pending"
                        }
                      >
                        JBC / Employee
                      </span>

                      <span
                        className={
                          selectedProductIds.length >
                          0
                            ? "requirement-complete"
                            : "requirement-pending"
                        }
                      >
                        At least one Product
                      </span>

                    </div>
                  )}

                  {/* Save */}

                  <div className="participation-save-row">

                    <button
                      type="button"
                      className="cancel-edit-button"
                      onClick={
                        cancelParticipationEditing
                      }
                      disabled={
                        participationLoading
                      }
                    >
                      <Ban size={16} />
                      Cancel
                    </button>

                    <button
                      type="button"
                      className="save-participation-button"
                      disabled={
                        participationLoading ||
                        !delegatedEmployeeId ||
                        selectedProductIds.length ===
                          0
                      }
                      onClick={
                        handleSaveParticipation
                      }
                    >
                      <Save size={16} />

                      {participationLoading
                        ? "Saving..."
                        : "Save Participation"}
                    </button>

                  </div>

                </div>
              )}

              {/* Cancel editing for non-participating statuses */}

              {participation !==
                "PARTICIPATING" && (
                <div className="participation-save-row">

                  <button
                    type="button"
                    className="cancel-edit-button"
                    onClick={
                      cancelParticipationEditing
                    }
                    disabled={
                      participationLoading
                    }
                  >
                    <Ban size={16} />
                    Cancel
                  </button>

                </div>
              )}

            </>
          )}


        {/* --------------------------------------------------
            Read-only view for Admin / Viewer
            -------------------------------------------------- */}

        {!isCoordinator && (
          <div className="participation-summary">

            <div className="participation-summary-grid">

              {/* Status */}

              <div className="participation-summary-item">

                <span className="participation-summary-label">
                  Status
                </span>

                <div
                  className={`participation-summary-status ${getParticipationStatusClass()}`}
                >
                  {getParticipationIcon()}
                  {getParticipationLabel()}
                </div>

              </div>

              {/* JBC */}

              <div className="participation-summary-item">

                <span className="participation-summary-label">
                  Assigned JBC / Employee
                </span>

                <strong className="participation-summary-value">
                  {participation ===
                    "PARTICIPATING" &&
                  delegatedEmployeeName
                    ? delegatedEmployeeName
                    : "Not assigned"}
                </strong>

              </div>

              {/* Products */}

              <div className="participation-summary-item participation-products-item">

                <span className="participation-summary-label">
                  Products
                </span>

                {participation ===
                  "PARTICIPATING" &&
                selectedProductIds.length >
                  0 ? (
                  <div className="participation-product-tags">

                    {selectedProductIds.map(
                      (productId) => {
                        const productName =
                          getProductName(
                            productId
                          );

                        return (
                          <span
                            className="participation-product-tag"
                            key={productId}
                          >
                            {productName ||
                              `Product ${productId}`}
                          </span>
                        );
                      }
                    )}

                  </div>
                ) : (
                  <span className="participation-empty">
                    No products selected
                  </span>
                )}

              </div>

            </div>

          </div>
        )}

        {participationError && (
          <div className="edit-error">
            {participationError}
          </div>
        )}

      </div>

      {/* Delete - Admin Only */}

      {isAdmin && (
        <div className="delete-tender-section">

          <button
            type="button"
            className="delete-tender-button"
            disabled={
              deleteLoading ||
              editMode
            }
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
      )}

    </div>
  );
}

export default TenderDetail;