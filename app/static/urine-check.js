(() => {
  const dialog = document.getElementById("urine-check-dialog");
  const openButton = document.getElementById("open-urine-check");
  const closeButton = document.querySelector("[data-close-urine-check]");
  const form = document.getElementById("urine-check-form");
  const result = document.getElementById("urine-check-result");
  const error = document.getElementById("urine-check-error");

  if (!dialog || !openButton || !closeButton || !form || !result || !error) return;

  openButton.addEventListener("click", () => {
    dialog.showModal();
    form.querySelector("input")?.focus();
  });
  closeButton.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
  dialog.addEventListener("close", () => openButton.focus());

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    result.textContent = "";
    result.className = "urine-check__result";
    error.textContent = "";

    const formData = new FormData(form);
    const payload = {
      ca: Number(formData.get("ca")),
      ntx: Number(formData.get("ntx")),
      pyridinoline: Number(formData.get("pyridinoline"))
    };
    if (form.dataset.sex === "female") {
      payload.period = formData.get("period") === "true";
    }

    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    try {
      const response = await fetch(form.dataset.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        error.textContent = data.error || "Could not check these values.";
        return;
      }

      result.textContent = data.passed
        ? "Passed"
        : `Not passed. Outside the expected range: ${data.failed_tests.join(", ")}.`;
      result.classList.add(data.passed ? "urine-check__result--pass" : "urine-check__result--fail");
    } catch (requestError) {
      error.textContent = requestError.message || "Could not check these values.";
    } finally {
      submitButton.disabled = false;
    }
  });
})();
