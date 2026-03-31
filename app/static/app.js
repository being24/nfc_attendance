document.body.addEventListener("htmx:responseError", function () {
  console.warn("HTMX request failed");
});
