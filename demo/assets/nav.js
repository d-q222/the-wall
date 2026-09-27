/* Shared top nav for every page in the demo shell (wall.html, compound.html,
   present.html, /demo/, /scoreboard/). Owned by c4-demo-ui.
   Usage: <div id="site-nav"></div> as the first element in <body>, then
   <script src="/demo/assets/nav.js" defer></script>. Falls back to prepending
   into <body> if #site-nav is missing so it still works with zero markup. */
(function () {
  "use strict";

  var LINKS = [
    { label: "Home", href: "/demo/" },
    { label: "De-identify", href: "/demo/" },
    { label: "Wall", href: "/demo/wall.html" },
    { label: "Compounding", href: "/demo/compound.html" },
    { label: "Scoreboard", href: "/scoreboard/" },
    { label: "Present", href: "/demo/present.html" }
  ];

  function normalize(path) {
    return path.replace(/index\.html$/, "").replace(/\/$/, "") || "/";
  }

  function buildNav() {
    var current = normalize(window.location.pathname);
    var matched = false;

    var nav = document.createElement("nav");
    nav.className = "wall-nav";

    var brand = document.createElement("span");
    brand.className = "wall-nav-brand";
    brand.textContent = "Ethical Wall Brain";
    nav.appendChild(brand);

    var list = document.createElement("div");
    list.className = "wall-nav-links";
    LINKS.forEach(function (link) {
      var a = document.createElement("a");
      a.href = link.href;
      a.textContent = link.label;
      a.className = "wall-nav-link";
      if (!matched && normalize(link.href) === current) {
        a.classList.add("is-active");
        a.setAttribute("aria-current", "page");
        matched = true;
      }
      list.appendChild(a);
    });
    nav.appendChild(list);
    return nav;
  }

  function mount() {
    var nav = buildNav();
    var slot = document.getElementById("site-nav");
    if (slot) {
      slot.appendChild(nav);
    } else {
      document.body.insertBefore(nav, document.body.firstChild);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else {
    mount();
  }
})();
