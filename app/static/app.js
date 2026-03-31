document.body.addEventListener("htmx:responseError", function () {
  console.warn("HTMX request failed");
});

function initCardIdInputFocus() {
  if (window.location.pathname !== "/") {
    return;
  }
  const input = document.getElementById("card-id-input");
  if (!input) {
    return;
  }

  const focusInput = () => {
    input.focus({ preventScroll: true });
  };

  focusInput();
  window.setTimeout(focusInput, 100);

  document.addEventListener("click", function (event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }
    if (target.closest("button, a, input, select, textarea, label")) {
      return;
    }
    focusInput();
  });

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      focusInput();
    }
  });
}

initCardIdInputFocus();
