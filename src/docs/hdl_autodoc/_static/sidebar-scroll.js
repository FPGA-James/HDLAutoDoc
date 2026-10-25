/* Keep Furo's left sidebar at the same scroll position across page loads */
(function () {
  var KEY = "hdl-autodoc-sidebar-scroll";

  function pane() {
    return document.querySelector(".sidebar-scroll");
  }

  function restore() {
    var el = pane();
    if (!el) return;
    try {
      var saved = sessionStorage.getItem(KEY);
      if (saved !== null) el.scrollTop = parseInt(saved, 10);
    } catch (e) {}
  }

  function save() {
    var el = pane();
    if (!el) return;
    try {
      sessionStorage.setItem(KEY, String(el.scrollTop));
    } catch (e) {}
  }

  // Furo scrolls the current item into view on load; restore afterwards.
  document.addEventListener("DOMContentLoaded", restore);
  window.addEventListener("load", restore);
  window.addEventListener("pagehide", save);
  document.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest(".sidebar-scroll a")) save();
  });
})();
