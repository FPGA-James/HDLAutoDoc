Registers
=========

.. raw:: html

   <style>
     /* Remove content area padding so iframe butts up cleanly */
     .wy-nav-content {
       max-width: 100% !important;
       padding: 0 !important;
     }
     .document, .documentwrapper, .bodywrapper, .body, section {
       height: 100%;
       margin: 0 !important;
       padding: 0 !important;
     }
     /* Fixed iframe that starts exactly where the sidebar ends.
        RTD sidebar is 300px wide. Top bar is ~60px.
        JS below reads the actual sidebar width at runtime for robustness. */
     #registers-frame {
       position: fixed;
       top: 60px;
       left: 300px;
       width: calc(100vw - 300px);
       height: calc(100vh - 60px);
       border: none;
       z-index: 100;
     }
     /* Floating info strip — sits above the iframe, clear of the sidebar */
     #reg-info {
       position: fixed;
       bottom: 1.5rem;
       right: 1.5rem;
       z-index: 200;
       background: rgba(30, 30, 46, 0.82);
       color: #cdd6f4;
       font-family: 'IBM Plex Mono', monospace;
       font-size: 0.78em;
       padding: 0.4rem 1rem;
       border-radius: 2rem;
       border: 1px solid rgba(137, 180, 250, 0.3);
       backdrop-filter: blur(8px);
       pointer-events: none;
       white-space: nowrap;
     }
   </style>
   <script>
     // Measure the actual sidebar width at runtime so the iframe aligns
     // correctly if the user has resized or the theme has changed.
     document.addEventListener("DOMContentLoaded", function() {
       var sidebar = document.querySelector(".wy-nav-side");
       var topbar  = document.querySelector(".wy-nav-top");
       var frame   = document.getElementById("registers-frame");
       if (sidebar && frame) {
         var sw = sidebar.offsetWidth;
         var th = topbar ? topbar.offsetHeight : 60;
         frame.style.left   = sw + "px";
         frame.style.width  = "calc(100vw - " + sw + "px)";
         frame.style.top    = th + "px";
         frame.style.height = "calc(100vh - " + th + "px)";
       }
     });
   </script>
   <iframe
     id="registers-frame"
     src="_static/registers/counter_regs.html"
     title="Register Map">
   </iframe>
   <div id="reg-info">Register Map &mdash; re-run <code>make html</code> to update</div>

