/* Left-sidebar scrolling for Furo.
   - After clicking a link *in* the sidebar, keep the sidebar exactly where it was.
   - Any other navigation (breadcrumbs, content/overview links, search, direct
     load): scroll the sidebar so the current page's entry is visible.
   Furo itself does neither, so the sidebar otherwise reloads scrolled to the top. */
(function () {
  var KEY = "hdl-autodoc-sidebar-scroll";

  function pane() {
    return document.querySelector(".sidebar-scroll");
  }

  // Furo sets scroll-behavior: smooth, which would make every restore visibly glide
  // down from the top.  Jump instantly instead.
  function jump(el, top) {
    el.scrollTo({ top: top, behavior: "instant" });
  }

  // Scroll the sidebar (not the page) so the current entry sits in view,
  // a third of the way down.  No-op if it is already comfortably visible.
  function revealCurrent(el) {
    var item = el.querySelector("li.current-page > a, .current-page > a");
    if (!item) return;
    var p = el.getBoundingClientRect();
    var i = item.getBoundingClientRect();
    if (i.top < p.top + 16 || i.bottom > p.bottom - 16) {
      jump(el, el.scrollTop + i.top - p.top - p.height / 3);
    }
  }

  function place() {
    var el = pane();
    if (!el) return;
    var saved = null;
    try { saved = sessionStorage.getItem(KEY); } catch (e) {}
    if (saved !== null) {
      jump(el, parseInt(saved, 10));
    } else {
      revealCurrent(el);
    }
  }

  document.addEventListener("DOMContentLoaded", place);
  window.addEventListener("load", function () {
    place();
    // One-shot: the next load only keeps its position if it follows another sidebar click.
    try { sessionStorage.removeItem(KEY); } catch (e) {}
  });

  document.addEventListener("click", function (e) {
    var el = pane();
    if (!el || !e.target.closest || !e.target.closest(".sidebar-scroll a")) return;
    try { sessionStorage.setItem(KEY, String(el.scrollTop)); } catch (e2) {}
  });
})();
