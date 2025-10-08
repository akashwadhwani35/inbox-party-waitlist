(() => {
  const resolveApiBase = () => {
    const overridden = window.INBOX_PARTY_API?.baseUrl;
    if (typeof overridden === "string" && overridden.trim()) {
      return overridden.replace(/\/$/, "");
    }

    const { hostname, protocol } = window.location;
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://localhost:8000";
    }
    return `${protocol}//${hostname}`;
  };

  const API_BASE = resolveApiBase();
  const API_ENDPOINT = `${API_BASE}/api/waitlist/entries`;

  const refreshButton = document.getElementById("refresh");
  const exportButton = document.getElementById("export");
  const totalEl = document.getElementById("signup-total");
  const updatedEl = document.getElementById("last-updated");
  const tableBody = document.getElementById("entries-body");

  const formatTimestamp = (value) => {
    if (!value) {
      return "—";
    }
    const isoLike = `${value.replace(" ", "T")}Z`;
    const date = new Date(isoLike);
    if (Number.isNaN(date.getTime())) {
      return value;
    }

    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(date);
  };

  const setStatusRow = (message) => {
    if (!tableBody) {
      return;
    }
    tableBody.innerHTML = `
      <tr>
        <td colspan="3">${message}</td>
      </tr>
    `;
  };

  const renderEntries = (entries) => {
    if (!tableBody) {
      return;
    }

    if (!entries.length) {
      setStatusRow("No signups yet.");
      return;
    }

    tableBody.innerHTML = entries
      .map(
        (entry) => `
        <tr>
          <td>${entry.name || "—"}</td>
          <td><a href="mailto:${entry.email}">${entry.email}</a></td>
          <td>${formatTimestamp(entry.created_at)}</td>
        </tr>`
      )
      .join("");
  };

  const setLastUpdated = () => {
    if (!updatedEl) {
      return;
    }
    const now = new Date();
    updatedEl.textContent = new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(now);
  };

  const loadEntries = async () => {
    if (refreshButton) {
      refreshButton.disabled = true;
      refreshButton.textContent = "Refreshing…";
    }
    setStatusRow("Loading waitlist…");

    try {
      const response = await fetch(API_ENDPOINT);
      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }
      const payload = await response.json();
      const entries = Array.isArray(payload.entries) ? payload.entries : [];
      renderEntries(entries);
      if (totalEl) {
        totalEl.textContent = String(payload.count ?? entries.length);
      }
      setLastUpdated();
    } catch (error) {
      console.error("Unable to load waitlist entries", error);
      setStatusRow("We couldn't load the waitlist right now. Try again in a moment.");
    } finally {
      if (refreshButton) {
        refreshButton.disabled = false;
        refreshButton.textContent = "Refresh";
      }
    }
  };

  refreshButton?.addEventListener("click", () => {
    loadEntries();
  });

  exportButton?.addEventListener("click", async () => {
    if (!exportButton) {
      return;
    }

    exportButton.disabled = true;
    exportButton.textContent = "Preparing…";

    try {
      const response = await fetch(`${API_ENDPOINT}?format=csv`);
      if (!response.ok) {
        throw new Error(`CSV export failed with status ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "inbox-party-waitlist.csv";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Unable to export waitlist CSV", error);
      alert("We couldn't prepare the export. Try again shortly.");
    } finally {
      exportButton.disabled = false;
      exportButton.textContent = "Export CSV";
    }
  });

  loadEntries();
})();
