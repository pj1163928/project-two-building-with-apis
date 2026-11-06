// The library drawer (catalog/partials/entry_drawer.html, in library.html's
// <dialog id="library-drawer">), Discover's drawer (catalog/partials/
// discover_drawer.html, in discover.html's <dialog id="discover-drawer">), and
// the review's autosave
// (catalog/partials/entry_detail.html), on the drawer and on the full page.
// Listens on the document, like the other scripts, so content that swaps in
// later works too.
//
// Notes are never lost to a failed save:
// - a save's reply replaces only the status line (#entry-save-status), never
//   the text being typed
// - until a save succeeds, the text is kept in this browser (localStorage,
//   under the form's data-draft-key) and put back when the entry opens again
// - any failure (a 4xx or 5xx, no connection, a timeout) shows a message and
//   Try again, and a lost connection retries by itself once it's back
// - closing the drawer, opening another entry or leaving the page with notes
//   that aren't saved yet asks first
(function () {
  var REACH_ERROR = "Couldn't reach the Toolbox, so this didn't save. Your text is still here.";
  var SERVER_ERROR = "Something went wrong, so this didn't save. Your text is still here.";
  var LEAVE_WARNING = "Your notes haven't saved yet. Leave anyway? They're kept in this browser and come back when you open this entry again.";
  var failed = null; // the autosave form whose last save failed, for Try again

  // The page's one drawer: the library's (#library-drawer) or Discover's (#discover-drawer).
  function drawer() { return document.querySelector("dialog.drawer-dialog"); }
  function autosaveForm(element) { return element && element.closest ? element.closest("form[data-autosave]") : null; }
  function notesForms() { return document.querySelectorAll('form[data-autosave="notes"]'); }
  function notesOf(form) { return form.querySelector("textarea[name=notes]"); }

  // ---------- drafts ----------
  function readDraft(form) {
    try { return localStorage.getItem(form.dataset.draftKey); } catch (error) { return null; }
  }
  function writeDraft(form) {
    try { localStorage.setItem(form.dataset.draftKey, notesOf(form).value); } catch (error) { /* storage off */ }
  }
  function dropDraft(form) {
    try { localStorage.removeItem(form.dataset.draftKey); } catch (error) { /* storage off */ }
  }

  // Notes are unsaved while the text differs from the last text the server
  // confirmed (data-saved), and no save of it is on its way.
  function unsaved(form) {
    var notes = notesOf(form);
    return !!notes && notes.value !== form.dataset.saved && form.dataset.saveState !== "saving";
  }
  function anyUnsaved(within) {
    return Array.prototype.some.call(notesForms(), function (form) {
      // A closed drawer's notes were already let go of (their draft is kept).
      var dialog = form.closest("dialog");
      if (dialog && !dialog.open) return false;
      return (!within || within.contains(form)) && unsaved(form);
    });
  }

  // ---------- the status line ----------
  function showStatus(state, message) {
    var line = document.getElementById("entry-save-status");
    if (!line) return;
    line.dataset.saveStatus = state;
    line.setAttribute("role", state === "error" ? "alert" : "status");
    line.textContent = "";
    var text = document.createElement("span");
    text.textContent = message;
    line.appendChild(text);
    if (state === "error") {
      var retry = document.createElement("button");
      retry.type = "button";
      retry.className = "entry-save-link";
      retry.dataset.saveRetry = "";
      retry.textContent = "Try again";
      line.appendChild(retry);
    }
  }

  function fail(form, message) {
    form.dataset.saveState = "error";
    failed = form;
    if (message) showStatus("error", message);
  }

  function retry() {
    if (failed && document.contains(failed)) htmx.trigger(failed, "change");
  }

  // ---------- an entry's review arrives (the full page, or the drawer) ----------
  function setUp(root) {
    if (!root.querySelectorAll) return;
    root.querySelectorAll('form[data-autosave="notes"]').forEach(function (form) {
      var notes = notesOf(form);
      form.dataset.saved = notes.value;
      var draft = readDraft(form);
      if (draft === null || draft === notes.value) {
        dropDraft(form);
        return;
      }
      // Text that never saved last time: put it back and save it now.
      notes.value = draft;
      showStatus("saving", "Restoring notes that hadn't saved…");
      htmx.trigger(form, "change");
    });
  }
  if (window.htmx) htmx.onLoad(setUp);

  document.addEventListener("input", function (event) {
    var form = autosaveForm(event.target);
    if (form && form.dataset.autosave === "notes") writeDraft(form);
  });

  // ---------- each save ----------
  document.addEventListener("htmx:configRequest", function (event) {
    var form = autosaveForm(event.detail.elt);
    if (!form || !form.dataset.autosave) return;
    // Signing in again (in another tab) rotates the CSRF token, so send the
    // newest one from the cookie rather than the one the page was built with.
    var cookie = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    if (cookie) event.detail.headers["X-CSRFToken"] = decodeURIComponent(cookie[1]);
    if (form.dataset.autosave === "notes") form.dataset.sending = notesOf(form).value;
  });

  document.addEventListener("htmx:beforeRequest", function (event) {
    var form = autosaveForm(event.detail.elt);
    if (form && form.dataset.autosave) {
      form.dataset.saveState = "saving";
      showStatus("saving", "Saving…");
    }
  });

  // An error the Toolbox explains (a 400, or 401 when signed out) swaps its own
  // status line in. Anything else (a CSRF page, a server error page) would
  // land in the status line as a whole page, so it's replaced by a message.
  document.addEventListener("htmx:beforeSwap", function (event) {
    var form = autosaveForm(event.detail.requestConfig && event.detail.requestConfig.elt);
    if (!form || !form.dataset.autosave || event.detail.xhr.status < 400) return;
    fail(form);
    if (event.detail.xhr.responseText.indexOf("data-save-status") === -1) {
      event.detail.shouldSwap = false;
      showStatus("error", SERVER_ERROR);
    }
  });

  document.addEventListener("htmx:afterRequest", function (event) {
    var form = autosaveForm(event.detail.elt);
    if (!form || !form.dataset.autosave || !event.detail.successful) return;
    form.dataset.saveState = "saved";
    if (failed === form) failed = null;
    if (form.dataset.autosave !== "notes") return;
    form.dataset.saved = form.dataset.sending;
    // Typed more while it was saving? The draft stays until that saves too.
    if (notesOf(form).value === form.dataset.saved) dropDraft(form);
  });

  ["htmx:sendError", "htmx:timeout"].forEach(function (name) {
    document.addEventListener(name, function (event) {
      var form = autosaveForm(event.detail.elt);
      if (form && form.dataset.autosave) fail(form, REACH_ERROR);
    });
  });

  addEventListener("online", retry);

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-save-retry]")) retry();
  });

  // ---------- opening and closing the drawer ----------
  document.addEventListener("htmx:afterSwap", function (event) {
    var dialog = drawer();
    if (!dialog || event.detail.target !== dialog) return;
    if (!dialog.open) dialog.showModal();
    dialog.scrollTop = 0;
  });

  function closeDrawer() {
    var dialog = drawer();
    if (!dialog || !dialog.open) return;
    if (anyUnsaved(dialog) && !confirm(LEAVE_WARNING)) return;
    dialog.close();
  }

  document.addEventListener("click", function (event) {
    if (event.target.closest("[data-drawer-close]")) return closeDrawer();
    // A click on the backdrop lands on the <dialog> itself, outside its panel.
    if (event.target === drawer()) closeDrawer();
  });

  // Escape asks first too (the dialog's own cancel would close it at once).
  document.addEventListener("cancel", function (event) {
    if (event.target !== drawer()) return;
    event.preventDefault();
    closeDrawer();
  }, true);

  // The drawer's Remove: once the entry is gone, so is its drawer.
  document.addEventListener("htmx:afterRequest", function (event) {
    var dialog = drawer();
    if (dialog && event.detail.successful && event.detail.elt.closest("[data-drawer-remove]")) dialog.close();
  });

  // Opening another entry, or any navigation, would replace unsaved notes.
  document.addEventListener("htmx:beforeRequest", function (event) {
    var elt = event.detail.elt;
    if (autosaveForm(elt) || elt.closest("[data-drawer-remove]")) return;
    var replacesNotes = event.detail.boosted || event.detail.target === drawer();
    if (replacesNotes && anyUnsaved() && !confirm(LEAVE_WARNING)) event.preventDefault();
  });

  addEventListener("beforeunload", function (event) {
    if (anyUnsaved()) event.preventDefault();
  });
})();
