/* Keep Furo's left sidebar at the same scroll position when navigating *from*
   the sidebar.  Any other navigation (breadcrumbs, content links, search) leaves
   Furo's default behaviour alone: it scrolls the current page into view. */
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
      if (saved === null) return;
      el.scrollTop = parseInt(saved, 10);
    } catch (e) {}
  }

  // Furo scrolls the current item into view on load; restore afterwards.
  document.addEventListener("DOMContentLoaded", restore);
  window.addEventListener("load", function () {
    restore();
    // One-shot: the next page load only restores if it follows another sidebar click.
    try { sessionStorage.removeItem(KEY); } catch (e) {}
  });

  document.addEventListener("click", function (e) {
    var el = pane();
    if (!el || !e.target.closest || !e.target.closest(".sidebar-scroll a")) return;
    try { sessionStorage.setItem(KEY, String(el.scrollTop)); } catch (e2) {}
  });
})();
