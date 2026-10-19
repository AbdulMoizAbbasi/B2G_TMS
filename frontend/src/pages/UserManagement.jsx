import { useCallback, useEffect, useState } from "react";
import { ContactRound, KeyRound, Pencil, Plus, RefreshCw, ShieldCheck, UserRound, UserRoundX } from "lucide-react";
import api from "../api";
import "./UserManagement.css";

const EMPTY_FORM = { username: "", name: "", email: "", role: "USER", region_id: "", password: "" };
const EMPTY_EMPLOYEE_FORM = { employee_code: "", name: "", email: "", region_id: "", designation: "JBC" };
const isActive = (user) => user.is_active ?? user.active ?? false;
const regionLabel = (user) => user.region_name ?? user.region?.name ?? user.region ?? "—";
const employeeActive = (employee) => employee.is_active ?? employee.active ?? false;
const employeeCode = (employee) => employee.employee_code ?? employee.code ?? "—";
const recordsOf = (data) => Array.isArray(data) ? data : data?.items ?? [];

function errorText(error, fallback) {
  const detail = error.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map((item) => `${item.loc?.slice(-1)[0] ?? "Field"}: ${item.msg}`).join(" ");
  if (typeof detail === "string") return detail;
  if (detail?.message) return detail.message;
  if (!error.response) return "Unable to reach the server. Check your connection and try again.";
  return fallback;
}

function UserManagement() {
  const [users, setUsers] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [resetUser, setResetUser] = useState(null);
  const [newPassword, setNewPassword] = useState("");
  const [actionId, setActionId] = useState(null);
  const [employees, setEmployees] = useState([]);
  const [employeeLoading, setEmployeeLoading] = useState(true);
  const [employeeSearch, setEmployeeSearch] = useState("");
  const [employeeRegion, setEmployeeRegion] = useState("");
  const [employeeStatus, setEmployeeStatus] = useState("ALL");
  const [employeeDialog, setEmployeeDialog] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState(null);
  const [employeeForm, setEmployeeForm] = useState(EMPTY_EMPLOYEE_FORM);
  const [employeeEmailError, setEmployeeEmailError] = useState("");
  const [employeeSaving, setEmployeeSaving] = useState(false);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get("/api/admin/users");
      setUsers(Array.isArray(response.data) ? response.data : response.data?.items ?? []);
    } catch (requestError) {
      setError(errorText(requestError, "Unable to load users."));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadEmployees = useCallback(async () => {
    setEmployeeLoading(true);
    try {
      const response = await api.get("/api/admin/employees");
      setEmployees(recordsOf(response.data));
    } catch (requestError) {
      setError(errorText(requestError, "Unable to load JBC employees."));
    } finally { setEmployeeLoading(false); }
  }, []);

  useEffect(() => {
    let active = true;
    Promise.resolve().then(loadUsers);
    Promise.resolve().then(loadEmployees);
    api.get("/api/regions").then((response) => { if (active) setRegions(Array.isArray(response.data) ? response.data : []); })
      .catch((requestError) => { if (active) setError(errorText(requestError, "Unable to load regions.")); });
    return () => { active = false; };
  }, [loadUsers, loadEmployees]);

  const visibleEmployees = employees.filter((employee) => {
    const search = employeeSearch.trim().toLowerCase();
    const regionName = employee.region_name ?? employee.region?.name ?? employee.region ?? "";
    const matchesSearch = !search || [employeeCode(employee), employee.name, employee.email, employee.designation ?? "JBC", regionName].some((value) => String(value ?? "").toLowerCase().includes(search));
    const selectedRegion = regions.find((region) => String(region.id) === employeeRegion);
    const matchesRegion = !employeeRegion || String(employee.region_id ?? employee.region?.id ?? "") === employeeRegion || regionName === selectedRegion?.name;
    const matchesStatus = employeeStatus === "ALL" || (employeeStatus === "ACTIVE" ? employeeActive(employee) : !employeeActive(employee));
    return matchesSearch && matchesRegion && matchesStatus;
  });

  const openEmployeeCreate = () => { setEditingEmployee(null); setEmployeeForm(EMPTY_EMPLOYEE_FORM); setEmployeeEmailError(""); setError(""); setNotice(""); setEmployeeDialog(true); };
  const openEmployeeEdit = (employee) => { setEditingEmployee(employee); setEmployeeForm({ employee_code: employeeCode(employee) === "—" ? "" : String(employeeCode(employee)), name: employee.name ?? "", email: employee.email ?? "", region_id: String(employee.region_id ?? employee.region?.id ?? ""), designation: employee.designation ?? "JBC" }); setEmployeeEmailError(""); setError(""); setNotice(""); setEmployeeDialog(true); };
  const closeEmployeeDialog = () => { setEmployeeDialog(false); setEditingEmployee(null); setEmployeeForm(EMPTY_EMPLOYEE_FORM); setEmployeeEmailError(""); };
  const saveEmployee = async (event) => {
    event.preventDefault(); setError(""); setNotice("");
    const normalizedEmail = employeeForm.email.trim();
    if (!normalizedEmail) {
      setEmployeeEmailError("Email is required.");
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setEmployeeEmailError("Enter a valid email address.");
      return;
    }
    setEmployeeEmailError(""); setEmployeeSaving(true);
    const payload = { employee_code: employeeForm.employee_code.trim(), name: employeeForm.name.trim(), email: normalizedEmail, region_id: Number(employeeForm.region_id), designation: employeeForm.designation };
    try {
      if (editingEmployee) await api.patch(`/api/admin/employees/${editingEmployee.id}`, payload);
      else await api.post("/api/admin/employees", payload);
      closeEmployeeDialog(); setNotice(editingEmployee ? "Employee updated successfully." : "Employee added successfully."); await loadEmployees();
    } catch (requestError) { setError(errorText(requestError, "Unable to save employee.")); }
    finally { setEmployeeSaving(false); }
  };
  const toggleEmployeeStatus = async (employee) => {
    setActionId(employee.id); setError(""); setNotice("");
    try {
      await api.patch(`/api/admin/employees/${employee.id}/status`, { is_active: !employeeActive(employee) });
      setNotice(`${employee.name} ${employeeActive(employee) ? "deactivated" : "activated"}.`); await loadEmployees();
    } catch (requestError) { setError(errorText(requestError, "Unable to update JBC status.")); }
    finally { setActionId(null); }
  };

  const closeForm = () => { setFormOpen(false); setEditing(null); setForm(EMPTY_FORM); };
  const startCreate = () => { setEditing(null); setForm(EMPTY_FORM); setError(""); setNotice(""); setFormOpen(true); };
  const startEdit = (user) => {
    setEditing(user);
    setForm({ username: user.username ?? "", name: user.name ?? "", email: user.email ?? "", role: user.role ?? "USER", region_id: user.region_id == null ? "" : String(user.region_id), password: "" });
    setError(""); setNotice(""); setFormOpen(true);
  };

  const saveUser = async (event) => {
    event.preventDefault();
    setError(""); setNotice("");
    if (form.role === "COORDINATOR" && !form.region_id) {
      setError("Select a region for coordinator accounts.");
      return;
    }
    const payload = { username: form.username.trim(), name: form.name.trim(), email: form.email.trim(), role: form.role, region_id: form.role === "COORDINATOR" ? Number(form.region_id) : null };
    if (!editing) payload.password = form.password;
    setSaving(true);
    try {
      if (editing) await api.patch(`/api/admin/users/${editing.id}`, payload);
      else await api.post("/api/admin/users", payload);
      closeForm();
      setNotice(editing ? "User updated successfully." : "User created successfully.");
      await loadUsers();
    } catch (requestError) {
      setError(errorText(requestError, "Unable to save user."));
    } finally { setSaving(false); }
  };

  const toggleStatus = async (user) => {
    setActionId(user.id); setError(""); setNotice("");
    try {
      await api.patch(`/api/admin/users/${user.id}/status`, { is_active: !isActive(user) });
      setNotice(`${user.username} ${isActive(user) ? "deactivated" : "activated"}.`);
      await loadUsers();
    } catch (requestError) { setError(errorText(requestError, "Unable to update account status.")); }
    finally { setActionId(null); }
  };

  const resetPassword = async (event) => {
    event.preventDefault(); setError(""); setNotice(""); setActionId(resetUser.id);
    try {
      await api.post(`/api/admin/users/${resetUser.id}/reset-password`, { password: newPassword });
      setNotice(`Password reset for ${resetUser.username}.`);
      setResetUser(null); setNewPassword("");
    } catch (requestError) { setError(errorText(requestError, "Unable to reset password.")); }
    finally { setActionId(null); }
  };

  return <section className="user-management">
    <header className="user-management-header"><div><span className="user-management-eyebrow">ADMINISTRATION</span><h1>User Management</h1><p>Create accounts, manage assignments, and control access to Jazz Radar.</p></div><button className="um-primary-button" type="button" onClick={startCreate}><Plus size={17} />Add user</button></header>
    {error && <div className="um-alert um-alert-error" role="alert">{error}</div>}
    {notice && <div className="um-alert um-alert-success" role="status">{notice}</div>}
    <div className="um-table-card"><div className="um-table-heading"><div><h2>Portal users</h2><span>{users.length} accounts</span></div><button className="um-icon-button" type="button" onClick={loadUsers} disabled={loading} aria-label="Refresh users" title="Refresh users"><RefreshCw size={17} /></button></div>
      {loading ? <div className="um-empty-state">Loading users…</div> : users.length ? <div className="um-table-scroll"><table className="um-table"><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Assigned region</th><th>Status</th><th><span className="um-sr-only">Actions</span></th></tr></thead><tbody>{users.map((user) => <tr key={user.id}><td><div className="um-user-cell"><span className="um-avatar"><UserRound size={17} /></span><span><strong>{user.username}</strong><small>{user.name || "—"}</small></span></div></td><td>{user.email || "—"}</td><td><span className="um-role"><ShieldCheck size={14} />{user.role}</span></td><td>{user.role === "COORDINATOR" ? regionLabel(user) : "—"}</td><td><span className={`um-status ${isActive(user) ? "is-active" : "is-inactive"}`}><i />{isActive(user) ? "Active" : "Inactive"}</span></td><td><div className="um-actions"><button type="button" className="um-action-button" onClick={() => startEdit(user)} title="Edit user" aria-label={`Edit ${user.username}`}><Pencil size={16} /></button><button type="button" className="um-action-button" onClick={() => { setResetUser(user); setNewPassword(""); setError(""); setNotice(""); }} title="Reset password" aria-label={`Reset password for ${user.username}`}><KeyRound size={16} /></button><button type="button" className="um-action-button" onClick={() => toggleStatus(user)} disabled={actionId === user.id} title={isActive(user) ? "Deactivate account" : "Activate account"} aria-label={`${isActive(user) ? "Deactivate" : "Activate"} ${user.username}`}>{isActive(user) ? <UserRoundX size={16} /> : <UserRound size={16} />}</button></div></td></tr>)}</tbody></table></div> : <div className="um-empty-state">No users found. Add a user to get started.</div>}
    </div>

    <div className="um-table-card jbc-section"><div className="um-table-heading"><div><h2>Employees</h2><span>{visibleEmployees.length} of {employees.length} employees · Employee records do not have portal login accounts</span></div><div className="um-heading-actions"><button className="um-icon-button" type="button" onClick={loadEmployees} disabled={employeeLoading} aria-label="Refresh employees" title="Refresh employees"><RefreshCw size={17} /></button><button className="um-primary-button" type="button" onClick={openEmployeeCreate}><Plus size={16} />Add employee</button></div></div>
      <div className="jbc-filters"><label className="jbc-search">Search employees<input type="search" value={employeeSearch} onChange={(event) => setEmployeeSearch(event.target.value)} placeholder="Search employee code, name, email, designation, or region" /></label><label>Region<select value={employeeRegion} onChange={(event) => setEmployeeRegion(event.target.value)}><option value="">All regions</option>{regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select></label><label>Status<select value={employeeStatus} onChange={(event) => setEmployeeStatus(event.target.value)}><option value="ALL">All statuses</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label></div>
      {employeeLoading ? <div className="um-empty-state">Loading employees…</div> : visibleEmployees.length ? <div className="um-table-scroll"><table className="um-table jbc-table"><thead><tr><th>Employee code</th><th>Name</th><th>Email</th><th>Designation</th><th>Region</th><th>Status</th><th><span className="um-sr-only">Actions</span></th></tr></thead><tbody>{visibleEmployees.map((employee) => <tr key={employee.id}><td><strong>{employeeCode(employee)}</strong></td><td><div className="um-user-cell"><span className="um-avatar"><ContactRound size={17} /></span><strong>{employee.name || "—"}</strong></div></td><td>{employee.email || "—"}</td><td>{employee.designation || "JBC"}</td><td>{employee.region_name ?? employee.region?.name ?? employee.region ?? "—"}</td><td><span className={`um-status ${employeeActive(employee) ? "is-active" : "is-inactive"}`}><i />{employeeActive(employee) ? "Active" : "Inactive"}</span></td><td><div className="um-actions"><button type="button" className="um-action-button" onClick={() => openEmployeeEdit(employee)} title="Edit employee" aria-label={`Edit ${employee.name}`}><Pencil size={16} /></button><button type="button" className="um-action-button" onClick={() => toggleEmployeeStatus(employee)} disabled={actionId === employee.id} title={employeeActive(employee) ? "Deactivate employee" : "Activate employee"} aria-label={`${employeeActive(employee) ? "Deactivate" : "Activate"} ${employee.name}`}>{employeeActive(employee) ? <UserRoundX size={16} /> : <UserRound size={16} />}</button></div></td></tr>)}</tbody></table></div> : <div className="um-empty-state">{employees.length ? "No employees match these filters." : "No employees found."}</div>}
    </div>

    {employeeDialog && <div className="um-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !employeeSaving) closeEmployeeDialog(); }}><section className="um-modal" role="dialog" aria-modal="true" aria-labelledby="jbc-form-title"><header><div><span className="user-management-eyebrow">EMPLOYEE DETAILS</span><h2 id="jbc-form-title">{editingEmployee ? "Edit employee" : "Add employee"}</h2></div><button type="button" className="um-modal-close" onClick={closeEmployeeDialog} aria-label="Close">×</button></header><form onSubmit={saveEmployee}><div className="um-form-grid"><label>Employee code<input required autoComplete="off" value={employeeForm.employee_code} onChange={(event) => setEmployeeForm({ ...employeeForm, employee_code: event.target.value })} /></label><label>Full name<input required value={employeeForm.name} onChange={(event) => setEmployeeForm({ ...employeeForm, name: event.target.value })} /></label><label><span>Email <span className="required-marker" aria-hidden="true">*</span></span><input required type="email" autoComplete="email" value={employeeForm.email} aria-invalid={Boolean(employeeEmailError)} aria-describedby={employeeEmailError ? "employee-email-error" : undefined} onChange={(event) => { setEmployeeForm({ ...employeeForm, email: event.target.value }); setEmployeeEmailError(""); }} onBlur={() => { const value = employeeForm.email.trim(); setEmployeeEmailError(!value ? "Email is required." : !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value) ? "Enter a valid email address." : ""); }} />{employeeEmailError && <span className="employee-field-error" id="employee-email-error" role="alert">{employeeEmailError}</span>}</label><label>Designation<select required value={employeeForm.designation} onChange={(event) => setEmployeeForm({ ...employeeForm, designation: event.target.value })}><option value="JBC">JBC</option><option value="REGIONAL_HEAD">REGIONAL_HEAD</option></select></label><label>Assigned region<select required value={employeeForm.region_id} onChange={(event) => setEmployeeForm({ ...employeeForm, region_id: event.target.value })}><option value="">Select a region</option>{regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select></label></div><footer><button type="button" className="um-secondary-button" onClick={closeEmployeeDialog} disabled={employeeSaving}>Cancel</button><button type="submit" className="um-primary-button" disabled={employeeSaving || !regions.length}>{employeeSaving ? "Saving…" : editingEmployee ? "Save changes" : "Add employee"}</button></footer></form></section></div>}

    {formOpen && <div className="um-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !saving) closeForm(); }}><section className="um-modal" role="dialog" aria-modal="true" aria-labelledby="um-form-title"><header><div><span className="user-management-eyebrow">ACCOUNT DETAILS</span><h2 id="um-form-title">{editing ? "Edit user" : "Create user"}</h2></div><button type="button" className="um-modal-close" onClick={closeForm} aria-label="Close">×</button></header><form onSubmit={saveUser}><div className="um-form-grid"><label>Username<input required autoComplete="off" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label><label>Full name<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Email<input required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} /></label><label>Role<select value={form.role} onChange={(event) => setForm({ ...form, role: event.target.value, region_id: event.target.value === "COORDINATOR" ? form.region_id : "" })}><option value="USER">User</option><option value="COORDINATOR">Coordinator</option><option value="ADMIN">Admin</option></select></label>{form.role === "COORDINATOR" && <label className="um-full-width">Assigned region<select required value={form.region_id} onChange={(event) => setForm({ ...form, region_id: event.target.value })}><option value="">Select a region</option>{regions.map((region) => <option key={region.id} value={region.id}>{region.name}</option>)}</select></label>}{!editing && <label className="um-full-width">Temporary password<input required type="password" autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>}</div><footer><button type="button" className="um-secondary-button" onClick={closeForm} disabled={saving}>Cancel</button><button type="submit" className="um-primary-button" disabled={saving}>{saving ? "Saving…" : editing ? "Save changes" : "Create user"}</button></footer></form></section></div>}

    {resetUser && <div className="um-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget && !actionId) { setResetUser(null); setNewPassword(""); } }}><section className="um-modal um-reset-modal" role="dialog" aria-modal="true" aria-labelledby="um-reset-title"><header><div><span className="user-management-eyebrow">SECURITY</span><h2 id="um-reset-title">Reset password</h2></div><button type="button" className="um-modal-close" onClick={() => { setResetUser(null); setNewPassword(""); }} aria-label="Close">×</button></header><p>Set a new password for <strong>{resetUser.username}</strong>.</p><form onSubmit={resetPassword}><label>New password<input type="password" required minLength="8" autoComplete="new-password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label><footer><button type="button" className="um-secondary-button" onClick={() => { setResetUser(null); setNewPassword(""); }}>Cancel</button><button className="um-primary-button" type="submit" disabled={actionId === resetUser.id}>{actionId === resetUser.id ? "Resetting…" : "Reset password"}</button></footer></form></section></div>}
  </section>;
}

export default UserManagement;
