(() => {
  const form = document.getElementById("waitlist-form");
  const feedback = document.getElementById("form-feedback");
  const submitButton = form?.querySelector("button[type='submit']");
  const yearEl = document.getElementById("year");
  const countEl = document.getElementById("signup-count");
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
  const API_ENDPOINT = `${API_BASE}/api/waitlist`;

  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  const updateCount = (value) => {
    if (!countEl || typeof value !== "number" || Number.isNaN(value)) {
      return;
    }

    if (value === 0) {
      countEl.textContent = "You're the first to join the celebration.";
    } else if (value === 1) {
      countEl.textContent = "1 person is waiting for Inbox Party.";
    } else {
      countEl.textContent = `${value.toLocaleString()} people are ready for Inbox Party.`;
    }
  };

  const loadCount = async () => {
    if (!countEl) {
      return;
    }

    try {
      const response = await fetch(API_ENDPOINT);
      if (!response.ok) {
        return;
      }
      const data = await response.json();
      updateCount(Number(data.count));
    } catch (error) {
      console.warn("Unable to fetch waitlist count", error);
    }
  };

  loadCount();

  if (!form || !feedback || !submitButton) {
    return;
  }

  const setFeedback = (message, variant = "info") => {
    feedback.textContent = message;
    feedback.classList.remove("feedback--success", "feedback--error");

    if (variant === "success") {
      feedback.classList.add("feedback--success");
    }

    if (variant === "error") {
      feedback.classList.add("feedback--error");
    }
  };

  const isValidEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value).toLowerCase());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const formData = new FormData(form);
    const name = String(formData.get("name") || "").trim();
    const email = String(formData.get("email") || "").trim();

    if (name.length < 2) {
      setFeedback("Please share your full name so we know who to invite.", "error");
      return;
    }

    if (!isValidEmail(email)) {
      setFeedback("We need a valid email to send your invite.", "error");
      return;
    }

    submitButton.disabled = true;
    submitButton.setAttribute("aria-busy", "true");
    submitButton.textContent = "Adding you…";
    setFeedback("Hang tight—we're saving your spot.");

    try {
      const response = await fetch(API_ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ name, email }),
      });

      const payload = await response.json().catch(() => null);

      if (!response.ok) {
        const message = payload?.error || "We couldn't save that. Try again in a moment.";

        if (response.status === 409) {
          setFeedback("You're already on the list. We'll email you when invites roll out!", "success");
        } else {
          setFeedback(message, "error");
        }
        updateCount(Number(payload?.count));
        return;
      }

      setFeedback("You're on the list! We'll reach out as soon as we're ready.", "success");
      updateCount(Number(payload?.count));
      form.reset();
    } catch (error) {
      console.error("Waitlist submission failed", error);
      setFeedback("Looks like we're offline. Try again when you're connected.", "error");
    } finally {
      submitButton.disabled = false;
      submitButton.removeAttribute("aria-busy");
      submitButton.textContent = "Join now";
    }
  });
})();
