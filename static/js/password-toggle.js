// Show/hide toggles for password inputs (partials/form_fields.html).
// Navigation is boosted, so this loads once for every page and listens on the
// document: a [data-password-toggle] button anywhere, now or after a swap,
// flips the input it controls between type="password" and type="text", keeps
// aria-pressed and its label in step, and leaves focus in the input.
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-password-toggle]");
  if (!button) return;
  var input = document.getElementById(button.getAttribute("aria-controls"));
  if (!input) return;
  var show = input.type === "password";
  input.type = show ? "text" : "password";
  button.setAttribute("aria-pressed", String(show));
  button.setAttribute("aria-label", show ? "Hide password" : "Show password");
  input.focus();
});
