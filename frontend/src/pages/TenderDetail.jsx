import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import formatEstimatedValue from "../utils/formatEstimatedValue";
import {
  ArrowLeft,
  ExternalLink,
  CheckCircle2,
  XCircle,
  Trash2,
  Pencil,
  Save,
  Ban,
  ClipboardList,
  ChevronDown,
  Check,
} from "lucide-react";
import api from "../api";
import { useAuth } from "../auth/AuthContext";
import "./TenderDetail.css";

const NON_PARTICIPATION_REASONS = [
  { value: "IRRELEVANT_TENDER", label: "Irrelevant tender" },
  { value: "TIME_CONSTRAINTS", label: "Time Constraints" },
  { value: "PRODUCT_LIMITATION", label: "Product Limitation" },
  { value: "OTHER", label: "Other" },
];

function nonParticipationReasonLabel(value) {
  return NON_PARTICIPATION_REASONS.find((reason) => reason.value === value)?.label || "";
}

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

function TenderDetailContent() {
  const { user } = useAuth();

  const { tenderId } = useParams();
  const navigate = useNavigate();

  const isAdmin = user?.role === "ADMIN";
  const isCoordinator =
    user?.role === "COORDINATOR";

  const [tender, setTender] = useState(null);
  const [regions, setRegions] = useState([]);

  /*
   * ---------------------------------------------------------
   * Participation
   * ---------------------------------------------------------
   */

  const [participation, setParticipation] =
    useState("NOT_REVIEWED");

  const [savedParticipation, setSavedParticipation] =
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

  const [nonParticipationReason, setNonParticipationReason] = useState("");
  const [nonParticipationRemarks, setNonParticipationRemarks] = useState("");
  const [nonParticipationFieldErrors, setNonParticipationFieldErrors] = useState({});
  const nonParticipationDirtyRef = useRef({ reason: false, remarks: false });
  const participationDirtyRef = useRef(false);
  const assignmentDirtyRef = useRef(false);

  const [assignmentEmailLoading, setAssignmentEmailLoading] =
    useState(false);

  const [assignmentEmailSuccess, setAssignmentEmailSuccess] =
    useState("");

  const assignmentEmailRequestRef = useRef(false);

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

  const [loadedTenderId, setLoadedTenderId] = useState(null);

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
    let active = true;
    const fetchTender = async () => {
      try {
        const response = await api.get(
          `/api/tenders/${tenderId}`
        );

        if (active) {
          setTender(response.data);
          setLoadedTenderId(tenderId);
          setError("");
        }
      } catch (err) {
        console.error(err);

        if (active) {
          setError(err.response?.data?.detail || "Failed to load tender details.");
          setLoadedTenderId(tenderId);
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchTender();
    return () => { active = false; };
  }, [tenderId]);

  /*
   * ---------------------------------------------------------
   * Fetch regions
   * ---------------------------------------------------------
   */

  useEffect(() => {
    const fetchRegions = async () => {
      try {
        const response = await api.get("/api/regions");
        setRegions(response.data);
      } catch (err) {
        console.error(
          "Failed to load regions:",
          err
        );
      }
    };

    fetchRegions();
  }, []);

  /*
   * ---------------------------------------------------------
   * Fetch participation
   * ---------------------------------------------------------
   */

  useEffect(() => {
    let active = true;
    participationDirtyRef.current = false;
    assignmentDirtyRef.current = false;
    nonParticipationDirtyRef.current = { reason: false, remarks: false };

    const fetchParticipation = async () => {
      try {
        setParticipationError("");

        const response = await api.get(
          `/api/tenders/${tenderId}/participation`
        );

        if (!active) return;
        if (!participationDirtyRef.current) {
          setParticipation(response.data.status);
          setSavedParticipation(response.data.status);
        }
        if (!nonParticipationDirtyRef.current.reason) {
          setNonParticipationReason(response.data.non_participation_reason ?? "");
        }
        if (!nonParticipationDirtyRef.current.remarks) {
          setNonParticipationRemarks(response.data.non_participation_remarks ?? "");
        }

        if (!assignmentDirtyRef.current) {
          setDelegatedEmployeeId(response.data.delegated_employee_id ?? null);
          setDelegatedEmployeeName(response.data.delegated_employee_name ?? null);
          const productIds = Array.isArray(response.data.product_ids)
            ? response.data.product_ids.map((id) => Number(id))
            : [];
          setSelectedProductIds(productIds);
        }
      } catch (err) {
        if (!active) return;
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

    return () => {
      active = false;
    };
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

        const employeeRecords = Array.isArray(response.data) ? response.data : [];
        setEmployees(employeeRecords.filter(
          (employee) => employee.is_active !== false && (employee.designation ?? "JBC") === "JBC"
        ));
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

      region_id:
        tender.region_id ?? "",

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

      const selectedRegionId =
        editValues.region_id === "" ||
        editValues.region_id === null ||
        editValues.region_id === undefined
          ? null
          : Number(editValues.region_id);

      const currentRegionId =
        tender.region_id === null ||
        tender.region_id === undefined
          ? null
          : Number(tender.region_id);

      if (
        selectedRegionId !== null &&
        selectedRegionId !== currentRegionId
      ) {
        await api.patch(
          `/api/tenders/${encodeURIComponent(
            tenderId
          )}/region`,
          {
            region_id: selectedRegionId,
          }
        );
      }

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
    setNonParticipationFieldErrors({});
    setParticipationEditMode(true);
  }

  function cancelParticipationEditing() {
    participationDirtyRef.current = false;
    assignmentDirtyRef.current = false;
    nonParticipationDirtyRef.current = { reason: false, remarks: false };
    const reloadParticipation = async () => {
      try {
        setParticipationError("");

        const response = await api.get(
          `/api/tenders/${tenderId}/participation`
        );

        setParticipation(
          response.data.status
        );
        setSavedParticipation(response.data.status);
        setNonParticipationReason(response.data.non_participation_reason || "");
        setNonParticipationRemarks(response.data.non_participation_remarks || "");

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

    if (
      newStatus === "PARTICIPATED" &&
      (participation !== "ENGAGING" || savedParticipation !== "ENGAGING")
    ) {
      return;
    }

    participationDirtyRef.current = true;

    if (newStatus === "ENGAGING") {
      setNonParticipationReason("");
      setNonParticipationRemarks("");
      setNonParticipationFieldErrors({});
      setParticipation(
        "ENGAGING"
      );

      setParticipationError("");

      return;
    }

    if (newStatus === "NOT_PARTICIPATING") {
      setParticipation(newStatus);
      setParticipationEditMode(true);
      setNonParticipationFieldErrors({});
      setParticipationError("");
      setProductDropdownOpen(false);
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
      setSavedParticipation(response.data.status);
      setNonParticipationReason("");
      setNonParticipationRemarks("");
      setNonParticipationFieldErrors({});

      if (newStatus !== "PARTICIPATED") {
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

        setSelectedProductIds(returnedProductIds);
      setNonParticipationReason(response.data.non_participation_reason || "");
      setNonParticipationRemarks(response.data.non_participation_remarks || "");
      }

      if (
        newStatus !== "ENGAGING" &&
        newStatus !== "PARTICIPATED"
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

  async function handleSaveNonParticipation() {
    if (participationLoading) return;

    const fieldErrors = {};
    if (!nonParticipationReason) fieldErrors.reason = "Select a reason for not participating.";
    if (!nonParticipationRemarks.trim()) fieldErrors.remarks = "Enter remarks before saving.";
    setNonParticipationFieldErrors(fieldErrors);
    if (Object.keys(fieldErrors).length) return;

    try {
      setParticipationLoading(true);
      setParticipationError("");
      const response = await api.put(
        `/api/tenders/${tenderId}/participation`,
        {
          status: "NOT_PARTICIPATING",
          non_participation_reason: nonParticipationReason,
          non_participation_remarks: nonParticipationRemarks,
        }
      );
      setParticipation(response.data.status);
      setSavedParticipation(response.data.status);
      setNonParticipationReason(
        response.data.non_participation_reason || nonParticipationReason
      );
      setNonParticipationRemarks(
        response.data.non_participation_remarks ?? nonParticipationRemarks
      );
      setDelegatedEmployeeId(
        response.data.delegated_employee_id ??
          response.data.employee_id ??
          delegatedEmployeeId
      );
      setDelegatedEmployeeName(
        response.data.delegated_employee_name ||
          response.data.employee_name ||
          delegatedEmployeeName ||
          null
      );
      setNonParticipationFieldErrors({});
      setParticipationEditMode(false);
    } catch (err) {
      console.error(err);
      setParticipationError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          "Failed to save participation."
      );
    } finally {
      setParticipationLoading(false);
    }
  }

  /*
   * ---------------------------------------------------------
   * Save ENGAGING
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
          status: "ENGAGING",

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

      const selectedEmployee = employees.find(
        (employee) => Number(employee.id) === Number(delegatedEmployeeId)
      );

      setParticipation(
        response.data.status
      );
      setSavedParticipation(response.data.status);

      setDelegatedEmployeeId(
        response.data.delegated_employee_id ??
          response.data.employee_id ??
          Number(delegatedEmployeeId)
      );

      setDelegatedEmployeeName(
        response.data.delegated_employee_name ||
          response.data.employee_name ||
          selectedEmployee?.name ||
          delegatedEmployeeName ||
          null
      );

      const returnedProductIds =
        Array.isArray(
          response.data.product_ids
        )
          ? response.data.product_ids.map(
              (id) => Number(id)
            )
          : selectedProductIds.map((id) => Number(id));

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

  async function handleSendAssignmentEmail() {
    if (
      assignmentEmailRequestRef.current ||
      assignmentEmailLoading ||
      savedParticipation !== "ENGAGING" ||
      !delegatedEmployeeId ||
      !tender?.jazzid
    ) {
      return;
    }

    try {
      assignmentEmailRequestRef.current = true;
      setAssignmentEmailLoading(true);
      setAssignmentEmailSuccess("");
      setParticipationError("");

      const response = await api.post(
        `/api/tenders/${encodeURIComponent(tender.jazzid)}/send-assignment-email`
      );

      setAssignmentEmailSuccess(
        response.data?.message || "Assignment email sent successfully."
      );
    } catch (err) {
      console.error("Failed to send assignment email:", err);

      setParticipationError(
        err.response?.data?.detail ||
          err.response?.data?.message ||
          (err.response
            ? `Failed to send assignment email (${err.response.status}).`
            : "Network error. Could not confirm whether the assignment email was sent; please check before trying again.")
      );
    } finally {
      assignmentEmailRequestRef.current = false;
      setAssignmentEmailLoading(false);
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

    assignmentDirtyRef.current = true;

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

    assignmentDirtyRef.current = true;

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
      case "ENGAGING":
      case "PARTICIPATING":
        return "Engaging";

      case "PARTICIPATED":
        return "Participated";

      case "NOT_PARTICIPATING":
        return "Not Participating";

      case "NOT_REVIEWED":
      default:
        return "Not Reviewed";
    }
  }

  function isEngaging(status = participation) {
    return status === "ENGAGING" || status === "PARTICIPATING";
  }

  function getParticipationStatusClass() {
    switch (participation) {
      case "ENGAGING":
      case "PARTICIPATING":
        return "engaging";

      case "PARTICIPATED":
        return "participated";

      case "NOT_PARTICIPATING":
        return "not-participating";

      case "NOT_REVIEWED":
      default:
        return "not-reviewed";
    }
  }

  function getParticipationIcon() {
    switch (participation) {
      case "ENGAGING":
      case "PARTICIPATING":
        return <CheckCircle2 size={16} />;

      case "PARTICIPATED":
        return <CheckCircle2 size={16} />;

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

  if (loading || loadedTenderId !== tenderId) {
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
                {formatEstimatedValue(
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

            {editMode ? (
              <select
                value={editValues.region_id ?? ""}
                onChange={(event) =>
                  handleEditChange(
                    "region_id",
                    event.target.value
                  )
                }
                className="detail-edit-input"
              >
                <option value="">
                  Select Region
                </option>

                {regions.map((region) => (
                  <option
                    key={region.id}
                    value={region.id}
                  >
                    {region.name}
                  </option>
                ))}
              </select>
            ) : (
              <strong>
                {displayValue(
                  tender.region
                )}
              </strong>
            )}
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
                  href={tender.primary_document_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="detail-link"
                >
                  View Document
                  <ExternalLink size={14} />
                </a>
              ) : (
                "Document Not Available"
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

                {participation !== "NOT_PARTICIPATING" && (
                  <>
                {/* JBC */}

                <div className="participation-summary-item">

                  <span className="participation-summary-label">
                    Assigned JBC / Employee
                  </span>

                  <strong className="participation-summary-value">
                    {(isEngaging() || participation === "PARTICIPATED") &&
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

                  {(isEngaging() || participation === "PARTICIPATED") &&
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
                  </>
                )}

                {participation === "NOT_PARTICIPATING" && (
                  <>
                    <div className="participation-summary-item">
                      <span className="participation-summary-label">Assigned JBC / Employee</span>
                      <strong className="participation-summary-value">
                        {delegatedEmployeeName || "Not assigned"}
                      </strong>
                    </div>
                    <div className="participation-summary-item">
                      <span className="participation-summary-label">Reason for Not Participating</span>
                      <strong className="participation-summary-value">
                        {nonParticipationReasonLabel(nonParticipationReason) || "Not provided"}
                      </strong>
                    </div>
                    <div className="participation-summary-item participation-products-item">
                      <span className="participation-summary-label">Remarks</span>
                      <strong className="participation-summary-value participation-remarks-value">
                        {nonParticipationRemarks || "Not provided"}
                      </strong>
                    </div>
                  </>
                )}

              </div>

              {/* Edit */}

              <div className="participation-summary-actions">

                {savedParticipation === "ENGAGING" &&
                  delegatedEmployeeId && (
                    <button
                      type="button"
                      className="save-participation-button"
                      onClick={handleSendAssignmentEmail}
                      disabled={assignmentEmailLoading}
                    >
                      {assignmentEmailLoading
                        ? "Sending..."
                        : "Send Assignment Email"}
                    </button>
                  )}

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

                {participation === "ENGAGING" && (
                  <button
                    type="button"
                    className="save-participation-button"
                    onClick={() => handleParticipationChange("PARTICIPATED")}
                    disabled={participationLoading}
                  >
                    <CheckCircle2 size={16} />
                    {participationLoading ? "Updating..." : "Mark as Participated"}
                  </button>
                )}

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

                {/* Engaging */}

                <button
                  type="button"
                  className={`participation-button ${
                    isEngaging()
                      ? "selected"
                      : ""
                  }`}
                  disabled={
                    participationLoading
                  }
                  onClick={() =>
                    handleParticipationChange(
                      "ENGAGING"
                    )
                  }
                >
                  <CheckCircle2
                    size={16}
                  />

                  Engaging
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

                {savedParticipation === "ENGAGING" && participation === "ENGAGING" && (
                  <button
                    type="button"
                    className="participation-button"
                    onClick={() => handleParticipationChange("PARTICIPATED")}
                    disabled={participationLoading}
                  >
                    <CheckCircle2 size={16} />
                    {participationLoading ? "Updating..." : "Mark as Participated"}
                  </button>
                )}

              </div>

              {/* ENGAGING DETAILS */}

              {isEngaging() && (
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
                        participationLoading || employees.length === 0
                      }
                    >
                      <option value="">
                        {employees.length ? "Select JBC / Employee" : "No active JBC employees available"}
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
                        Engaging requires:
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

              {participation === "NOT_PARTICIPATING" && (
                <div className="participation-assignment">
                  <div className="delegation-section">
                    <label htmlFor="non-participation-reason">Reason for Not Participating</label>
                    <select
                      id="non-participation-reason"
                      value={nonParticipationReason}
                      onChange={(event) => {
                        participationDirtyRef.current = true;
                        nonParticipationDirtyRef.current.reason = true;
                        setNonParticipationReason(event.target.value);
                        setNonParticipationFieldErrors((errors) => ({ ...errors, reason: "" }));
                      }}
                      disabled={participationLoading}
                      aria-invalid={Boolean(nonParticipationFieldErrors.reason)}
                      aria-describedby={nonParticipationFieldErrors.reason ? "non-participation-reason-error" : undefined}
                    >
                      <option value="">Select a reason</option>
                      {NON_PARTICIPATION_REASONS.map((reason) => (
                        <option key={reason.value} value={reason.value}>{reason.label}</option>
                      ))}
                    </select>
                    {nonParticipationFieldErrors.reason && (
                      <span id="non-participation-reason-error" className="participation-field-error" role="alert">
                        {nonParticipationFieldErrors.reason}
                      </span>
                    )}
                  </div>
                  <div className="delegation-section">
                    <label htmlFor="non-participation-remarks">Remarks</label>
                    <textarea
                      id="non-participation-remarks"
                      value={nonParticipationRemarks}
                      onChange={(event) => {
                        participationDirtyRef.current = true;
                        nonParticipationDirtyRef.current.remarks = true;
                        setNonParticipationRemarks(event.target.value);
                        setNonParticipationFieldErrors((errors) => ({ ...errors, remarks: "" }));
                      }}
                      disabled={participationLoading}
                      rows={4}
                      aria-invalid={Boolean(nonParticipationFieldErrors.remarks)}
                      aria-describedby={nonParticipationFieldErrors.remarks ? "non-participation-remarks-error" : undefined}
                    />
                    {nonParticipationFieldErrors.remarks && (
                      <span id="non-participation-remarks-error" className="participation-field-error" role="alert">
                        {nonParticipationFieldErrors.remarks}
                      </span>
                    )}
                  </div>
                  <div className="participation-save-row">
                    <button type="button" className="cancel-edit-button" onClick={cancelParticipationEditing} disabled={participationLoading}>
                      <Ban size={16} /> Cancel
                    </button>
                    <button type="button" className="save-participation-button" onClick={handleSaveNonParticipation} disabled={participationLoading}>
                      <Save size={16} /> {participationLoading ? "Saving..." : "Save Participation"}
                    </button>
                  </div>
                </div>
              )}

              {/* Cancel editing for non-participating statuses */}

              {!isEngaging() && participation !== "NOT_PARTICIPATING" && (
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

              {participation === "NOT_PARTICIPATING" && (
                <>
                  <div className="participation-summary-item">
                    <span className="participation-summary-label">Assigned JBC / Employee</span>
                    <strong className="participation-summary-value">
                      {delegatedEmployeeName || "Not assigned"}
                    </strong>
                  </div>
                  <div className="participation-summary-item">
                    <span className="participation-summary-label">Reason for Not Participating</span>
                    <strong className="participation-summary-value">
                      {nonParticipationReasonLabel(nonParticipationReason) || "Not provided"}
                    </strong>
                  </div>
                  <div className="participation-summary-item participation-products-item">
                    <span className="participation-summary-label">Remarks</span>
                    <strong className="participation-summary-value participation-remarks-value">
                      {nonParticipationRemarks || "Not provided"}
                    </strong>
                  </div>
                </>
              )}

              {participation !== "NOT_PARTICIPATING" && (
                <>
              {/* JBC */}

              <div className="participation-summary-item">

                <span className="participation-summary-label">
                  Assigned JBC / Employee
                </span>

                <strong className="participation-summary-value">
                  {(isEngaging() || participation === "PARTICIPATED") &&
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

                {(isEngaging() || participation === "PARTICIPATED") &&
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
                </>
              )}

            </div>

          </div>
        )}

        {participationError && (
          <div className="edit-error">
            {participationError}
          </div>
        )}

        {assignmentEmailSuccess && (
          <div className="assignment-email-success" role="status">
            {assignmentEmailSuccess}
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

function TenderDetail() {
  const { tenderId } = useParams();
  return <TenderDetailContent key={tenderId} />;
}

export default TenderDetail;
