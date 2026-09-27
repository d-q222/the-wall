/* App shell for every screen (design v2, docs/DESIGN.md). Owned by c4-demo-ui.
   Usage:
     <link rel="stylesheet" href="/demo/assets/theme.css">
     <script src="/demo/assets/nav.js" defer></script>
     <body data-crumb="Review">  <main class="app-main">...</main>  </body>
   nav.js wraps <main> in the ink sidebar + top bar and highlights the current screen.
   Optional: <body data-matter-switcher> shows the matter switcher (immigration matters).
     Selection is kept in localStorage "wall.matter"; pages listen for
     window "wall:matter" events ({detail: {id}}) or read WallShell.matter().
     A "?matter=<id>" query parameter preselects a matter (used by onboarding and deep links).
   Optional: <div data-topbar-extra> inside <main> is moved into the top bar's right side.
   Optional: <body data-shell="none"> applies the saved theme and exposes WallShell without
     mounting the sidebar (landing and onboarding are full-bleed pages).
   Setup nudge: while localStorage "wall.onboarding" is not {done: true}, the sidebar foot shows a
     quiet "Finish setup" link that resumes onboarding. Pattern from Mattermost's onboarding task
     list (webapp/channels/src/components/onboarding_tasklist/onboarding_tasklist.tsx): a persistent
     bottom-left trigger with the number of steps left and a way to dismiss it. */
(function () {
  "use strict";

  // Grouped like shadcn/ui's sidebar (apps/v4/registry/new-york-v4/ui/sidebar.tsx: SidebarGroup +
  // SidebarGroupLabel), in the order of the canonical flow (docs/USER_FLOW.md).
  var GROUPS = [
    { id: "work", label: "Workflow" },
    { id: "proof", label: "Proof" },
    { id: "firm", label: "Firm" }
  ];
  var SCREENS = [
    { id: "review", group: "work", label: "Review", href: "/demo/", icon: "M4 3h9l5 5v13H4zM13 3v5h5M8 13h8M8 17h6" },
    { id: "datasets", group: "work", label: "Datasets", href: "/demo/datasets.html", icon: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" },
    { id: "model", group: "work", label: "Model", href: "/demo/training.html", icon: "M12 3v3M12 18v3M3 12h3M18 12h3M7 7h10v10H7zM10 10h4v4h-4z" },
    { id: "wall", group: "proof", label: "Access wall", href: "/demo/wall.html", icon: "M3 5h18v14H3zM3 10h18M3 15h18M9 5v5M15 10v5M9 15v4" },
    { id: "knowhow", group: "proof", label: "Know-how", href: "/demo/compound.html", icon: "M12 3a6 6 0 0 0-3.5 10.9V17h7v-3.1A6 6 0 0 0 12 3zM9.5 21h5" },
    { id: "evaluation", group: "proof", label: "Evaluation", href: "/scoreboard/", icon: "M4 20V10M10 20V4M16 20v-7M22 20H2" },
    { id: "matters", group: "firm", label: "Matters", href: "/demo/matters.html", icon: "M3 7h18v13H3zM8 7V4h8v3M3 12h18" },
    { id: "policy", group: "firm", label: "Policy", href: "/demo/policy.html", icon: "M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6zM9 12l2 2 4-4" },
    { id: "audit", group: "firm", label: "Audit log", href: "/demo/audit.html", icon: "M5 3h14v18H5zM9 8h6M9 12h6M9 16h4" },
    { id: "stack", group: "firm", label: "Who helped", href: "/demo/stack.html", icon: "M4 17l8 4 8-4M4 12l8 4 8-4M12 3l8 4-8 4-8-4z" }
  ];
  var PRESENT = { label: "Present", href: "/demo/present.html" };
  var WELCOME = "/demo/welcome.html";
  var ONBOARDING = "/demo/onboarding.html";
  var ONB_STEPS = ["firm", "policy", "matters", "petition"];
  var FIRM = "Okafor & Lind Immigration";
  var MATTER_KEY = "wall.matter";
  var THEME_KEY = "wall.theme";
  var ONB_KEY = "wall.onboarding";

  function store(key, val) {
    try {
      if (val === undefined) return localStorage.getItem(key);
      localStorage.setItem(key, val);
    } catch (e) { return null; }
  }

  function onboarding() {
    try { return JSON.parse(store(ONB_KEY) || "null") || {}; } catch (e) { return {}; }
  }

  // apply theme before paint where possible
  var savedTheme = store(THEME_KEY);
  if (savedTheme === "dark" || savedTheme === "light") document.documentElement.setAttribute("data-theme", savedTheme);

  var params = new URLSearchParams(location.search);
  var embedded = params.get("embed") === "1";
  if (params.get("matter")) store(MATTER_KEY, params.get("matter"));

  function norm(p) { return p.replace(/index\.html$/, "").replace(/\/+$/, "") || "/"; }

  function el(tag, attrs, children) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      if (k === "text") n.textContent = attrs[k];
      else if (k === "html") n.innerHTML = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { if (c) n.appendChild(c); });
    return n;
  }

  function icon(d) {
    var s = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("fill", "none");
    s.setAttribute("stroke", "currentColor");
    s.setAttribute("stroke-width", "1.7");
    s.setAttribute("stroke-linecap", "round");
    s.setAttribute("stroke-linejoin", "round");
    s.setAttribute("aria-hidden", "true");
    var p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", d);
    s.appendChild(p);
    return s;
  }

  function currentScreen() {
    var here = norm(location.pathname);
    for (var i = 0; i < SCREENS.length; i++) if (norm(SCREENS[i].href) === here) return SCREENS[i];
    return null;
  }

  function isDark() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t === "dark";
    return false;
  }

  function setTheme(next) {
    document.documentElement.setAttribute("data-theme", next);
    store(THEME_KEY, next);
  }

  // "Finish setup": resumes onboarding at the first unfinished step. Hidden once done, when
  // dismissed, and inside the Present deck's embeds.
  function buildSetupNudge() {
    var s = onboarding();
    if (s.done === true || s.dismissed === true || embedded) return null;
    var reached = Math.max(0, Math.min(ONB_STEPS.length - 1, (Number(s.step) || 1) - 1));
    var finished = Math.max(0, Math.min(ONB_STEPS.length, Number(s.completed) || 0));
    var bars = el("span", { class: "setup-bars", "aria-hidden": "true" });
    ONB_STEPS.forEach(function (_s, i) { bars.appendChild(el("i", i < finished ? { class: "on" } : {})); });
    var link = el("a", { class: "sidebar-setup", href: ONBOARDING + "#" + ONB_STEPS[reached] }, [
      el("span", { class: "setup-text" }, [
        el("span", { class: "setup-title", text: "Finish setup" }),
        el("span", { class: "setup-meta", text: finished + " of " + ONB_STEPS.length + " steps done" })
      ]),
      bars
    ]);
    var hide = el("button", { class: "sidebar-setup-hide", type: "button", "aria-label": "Hide the setup reminder" }, [icon("M6 6l12 12M18 6L6 18")]);
    var wrap = el("div", { class: "sidebar-setup-wrap" }, [link, hide]);
    hide.addEventListener("click", function () {
      var cur = onboarding();
      cur.dismissed = true;
      store(ONB_KEY, JSON.stringify(cur));
      wrap.remove();
    });
    return wrap;
  }

  function buildSidebar(cur) {
    var brand = el("a", { class: "sidebar-brand", href: WELCOME, title: "About The Wall" }, [
      el("div", { class: "sidebar-mark", "aria-hidden": "true", text: "O&L" }),
      el("div", {}, [el("div", { class: "sidebar-firm", text: FIRM }), el("div", { class: "sidebar-sub", text: "Petition knowledge base" })])
    ]);
    var nav = el("nav", { class: "sidebar-nav", "aria-label": "Screens" });
    GROUPS.forEach(function (g) {
      nav.appendChild(el("div", { class: "sidebar-group", id: "nav-group-" + g.id, text: g.label }));
      var list = el("div", { class: "sidebar-list", role: "group", "aria-labelledby": "nav-group-" + g.id });
      SCREENS.filter(function (s) { return s.group === g.id; }).forEach(function (s) {
        var a = el("a", { class: "sidebar-link", href: s.href }, [icon(s.icon), el("span", { text: s.label })]);
        if (cur && cur.id === s.id) a.setAttribute("aria-current", "page");
        list.appendChild(a);
      });
      nav.appendChild(list);
    });
    var themeBtn = el("button", { class: "sidebar-theme", type: "button" });
    function paintTheme() {
      themeBtn.textContent = "";
      themeBtn.appendChild(icon(isDark() ? "M12 4V2M12 22v-2M4 12H2M22 12h-2M6 6 4.6 4.6M19.4 19.4 18 18M6 18l-1.4 1.4M19.4 4.6 18 6M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z" : "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z"));
      themeBtn.appendChild(el("span", { text: isDark() ? "Light mode" : "Dark mode" }));
      themeBtn.setAttribute("aria-pressed", isDark() ? "true" : "false");
    }
    themeBtn.addEventListener("click", function () { setTheme(isDark() ? "light" : "dark"); paintTheme(); });
    paintTheme();
    var present = el("a", { class: "sidebar-present", href: PRESENT.href }, [icon("M8 5v14l11-7z"), el("span", { text: PRESENT.label })]);
    if (norm(location.pathname) === norm(PRESENT.href)) present.setAttribute("aria-current", "page");
    var foot = el("div", { class: "sidebar-foot" }, [buildSetupNudge(), present, themeBtn]);
    return el("aside", { class: "sidebar" }, [brand, nav, foot]);
  }

  function buildTopbar(cur) {
    var crumbText = document.body.getAttribute("data-crumb") || (cur ? cur.label : document.title);
    var crumbs = el("nav", { class: "crumbs", "aria-label": "Breadcrumb" }, [
      el("a", { href: "/demo/matters.html", text: FIRM }),
      el("span", { class: "sep", "aria-hidden": "true", text: "/" }),
      el("span", { "aria-current": "page", text: crumbText })
    ]);
    var right = el("div", { class: "topbar-right" });
    if (document.body.hasAttribute("data-matter-switcher")) right.appendChild(buildMatterSwitch());
    return el("header", { class: "topbar" }, [crumbs, right]);
  }

  var matterList = [];
  function buildMatterSwitch() {
    var sel = el("select", { id: "matter-switcher", "aria-label": "Matter" });
    sel.appendChild(el("option", { text: "Loading matters" }));
    fetch("/demo/api/matters").then(function (r) { return r.json(); }).then(function (ms) {
      matterList = ms.filter(function (m) { return m.practice === "immigration"; });
      sel.innerHTML = "";
      var saved = store(MATTER_KEY);
      if (!matterList.some(function (m) { return m.id === saved; })) saved = matterList.length ? matterList[0].id : null;
      matterList.forEach(function (m) {
        var o = el("option", { value: m.id, text: m.client + " (" + m.id + ")" });
        if (m.id === saved) o.selected = true;
        sel.appendChild(o);
      });
      if (saved) { store(MATTER_KEY, saved); emit(saved, ms); }
    }).catch(function () {
      sel.innerHTML = "";
      sel.appendChild(el("option", { text: "Matters unavailable" }));
    });
    sel.addEventListener("change", function () { store(MATTER_KEY, sel.value); emit(sel.value); });
    return el("label", { class: "matter-switch" }, [el("span", { text: "Matter" }), sel]);
  }

  function emit(id, all) {
    var m = matterList.filter(function (x) { return x.id === id; })[0] || null;
    window.dispatchEvent(new CustomEvent("wall:matter", { detail: { id: id, matter: m, matters: all || null } }));
  }

  function mount() {
    if (document.querySelector(".shell")) return;
    if (document.body.getAttribute("data-shell") === "none") return;
    var cur = currentScreen();
    var main = document.querySelector("main");
    if (!main) {
      // no <main>: adopt the page's content (everything but scripts) as the content area
      main = el("main", { class: "app-main" });
      Array.prototype.slice.call(document.body.childNodes).forEach(function (n) {
        if (n.nodeName !== "SCRIPT") main.appendChild(n);
      });
      document.body.insertBefore(main, document.body.firstChild);
    }
    if (!main.classList.contains("app-main")) main.classList.add("app-main");
    if (!main.id) main.id = "main-content";
    if (!main.hasAttribute("tabindex")) main.setAttribute("tabindex", "-1");
    var skip = el("a", { class: "skip-link", href: "#" + main.id, text: "Skip to content" });
    var topbar = buildTopbar(cur);
    var extra = main.querySelector("[data-topbar-extra]");
    if (extra) topbar.querySelector(".topbar-right").insertBefore(extra, topbar.querySelector(".topbar-right").firstChild);
    var body = el("div", { class: "shell-body" }, [topbar]);
    var shell = el("div", { class: "shell" }, [buildSidebar(cur), body]);
    document.body.classList.add("has-shell");
    main.parentNode.insertBefore(shell, main);
    shell.parentNode.insertBefore(skip, shell);
    body.appendChild(main);
  }

  window.WallShell = {
    screens: SCREENS,
    matter: function () { return store(MATTER_KEY); },
    setMatter: function (id) { store(MATTER_KEY, id); var s = document.getElementById("matter-switcher"); if (s) s.value = id; emit(id); },
    onboarding: onboarding,
    isDark: isDark,
    setTheme: setTheme
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
