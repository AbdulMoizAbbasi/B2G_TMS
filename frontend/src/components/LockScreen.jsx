import { useState } from "react";
import { LockKeyhole } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import "./LockScreen.css";

function LockScreen() {
  const { reauthenticate, logout } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await reauthenticate(password);
      setPassword("");
    } catch (failure) {
      const detail = failure.response?.data?.detail;
      setError(detail?.message || (typeof detail === "string" ? detail : "Unable to verify your password. Please try again."));
    } finally {
      setPassword("");
      setSubmitting(false);
    }
  };

  return (
    <main className="lock-page">
      <section className="lock-card" aria-labelledby="lock-title">
        <div className="lock-icon" aria-hidden="true"><LockKeyhole size={30} /></div>
        <h1 id="lock-title">Session locked</h1>
        <p>For your security, this session was locked after inactivity.</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="lock-password">Password</label>
          <input id="lock-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required autoFocus />
          {error && <div className="lock-error" role="alert">{error}</div>}
          <button className="lock-submit" type="submit" disabled={submitting}>{submitting ? "Verifying..." : "Unlock"}</button>
        </form>
        <button className="lock-logout" type="button" onClick={logout}>Sign out</button>
      </section>
    </main>
  );
}

export default LockScreen;
