(() => {
  "use strict";

  const REPO_BLOB_BASE = "https://github.com/Real-Fruit-Snacks/rfs-themes/blob/main/";
  const REPO_TREE_BASE = "https://github.com/Real-Fruit-Snacks/rfs-themes/tree/main/";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const VARIANT_DOTS = {
    "cyclorama-dawn": "#FF9254",
    "cyclorama-steel": "#74B8E8",
    "cyclorama-day": "#AD3D0A",
  };

  // =========================================================================
  // 1. Dark-default (LX 263) / Light opt-in (LX 512) toggle + cross-tab sync
  // =========================================================================
  const root = document.documentElement;
  const meta = document.querySelector('meta[name="color-scheme"]');
  const themeBtn = document.getElementById("theme-toggle");

  const currentMode = () => (meta && meta.content === "light" ? "light" : "dark");

  const syncTheme = () => {
    const mode = currentMode();
    if (themeBtn) themeBtn.setAttribute("aria-pressed", String(mode === "light"));
    for (const tm of document.querySelectorAll('meta[name="theme-color"]')) {
      tm.content = mode === "light" ? "#f5f7f9" : "#050507";
    }
  };

  syncTheme();

  window.addEventListener("storage", (e) => {
    if ((e.key !== "rfs-theme" && e.key !== "color-scheme") || !meta) return;
    meta.content = e.newValue === "light" ? "light" : "dark";
    syncTheme();
  });

  if (themeBtn && meta) {
    themeBtn.addEventListener("click", () => {
      const target = currentMode() === "dark" ? "light" : "dark";
      const apply = () => {
        try {
          if (target === "dark") {
            localStorage.removeItem("rfs-theme");
            localStorage.removeItem("color-scheme");
          } else {
            localStorage.setItem("rfs-theme", "light");
            localStorage.setItem("color-scheme", "light");
          }
        } catch {}
        meta.content = target;
        syncTheme();
      };
      if (!document.startViewTransition) return apply();
      const r = themeBtn.getBoundingClientRect();
      const x = r.left + r.width / 2;
      const y = r.top + r.height / 2;
      const rad = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      root.style.setProperty("--vt-x", `${x.toFixed(1)}px`);
      root.style.setProperty("--vt-y", `${y.toFixed(1)}px`);
      root.style.setProperty("--vt-r", `${rad.toFixed(1)}px`);
      document.startViewTransition(apply);
    });
  }

  // =========================================================================
  // 2. Semantic colored popover="manual" toast region + ariaNotify fallback
  // =========================================================================
  const toastRegion = document.getElementById("toast-region");
  const liveStatus = document.getElementById("live-status");

  const announce = (msg) => {
    if (typeof document.ariaNotify === "function") {
      try {
        document.ariaNotify(msg);
        return;
      } catch {}
    }
    if (liveStatus) {
      liveStatus.textContent = "";
      requestAnimationFrame(() => {
        liveStatus.textContent = msg;
      });
    }
  };

  const openRegion = () => {
    if (!toastRegion) return;
    if (typeof toastRegion.showPopover === "function") {
      try {
        if (!toastRegion.matches(":popover-open")) toastRegion.showPopover();
      } catch {
        toastRegion.classList.add(":popover-open");
      }
    } else {
      toastRegion.classList.add(":popover-open");
    }
  };

  const closeRegionIfEmpty = () => {
    if (!toastRegion || toastRegion.children.length > 0) return;
    if (typeof toastRegion.hidePopover === "function") {
      try {
        if (toastRegion.matches(":popover-open")) toastRegion.hidePopover();
      } catch {}
    }
    toastRegion.classList.remove(":popover-open");
  };

  const showToast = (msg, triggerEl, tone = "ok") => {
    if (!toastRegion) return;
    const el = document.createElement("div");
    el.className = `rfs-toast is-${tone}`;

    const badge = document.createElement("span");
    badge.className = `rfs-badge b-${tone}`;
    const k = document.createElement("span");
    k.className = "k";
    k.textContent = tone === "fail" ? "[err]" : "[ok]";
    badge.append(k);

    const body = document.createElement("span");
    body.style.flex = "1 1 auto";
    body.textContent = msg;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "rfs-toast-close";
    closeBtn.setAttribute("aria-label", "Dismiss notification");
    closeBtn.textContent = "\u00D7";

    el.append(badge, body, closeBtn);
    toastRegion.append(el);
    openRegion();
    announce(msg);

    const dismiss = () => {
      const hadFocus = el.contains(document.activeElement);
      el.remove();
      closeRegionIfEmpty();
      if (hadFocus) {
        const nextClose = toastRegion.querySelector(".rfs-toast-close");
        if (nextClose) nextClose.focus();
        else if (triggerEl && typeof triggerEl.focus === "function") triggerEl.focus();
      }
    };

    closeBtn.addEventListener("click", dismiss);

    let timer = setTimeout(() => {
      if (!el.contains(document.activeElement)) dismiss();
    }, 4000);

    el.addEventListener("focusin", () => clearTimeout(timer));
    el.addEventListener("focusout", () => {
      timer = setTimeout(() => {
        if (!el.contains(document.activeElement)) dismiss();
      }, 2200);
    });
  };

  // =========================================================================
  // 3. Clipboard Copy + Blob Download + Safe DOM Helpers
  // =========================================================================
  const copyText = async (text) => {
    if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {}
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.append(ta);
      ta.select();
      const ok = document.execCommand("copy");
      ta.remove();
      return ok;
    } catch {
      return false;
    }
  };

  const triggerDownload = (filename, content) => {
    const blob = new Blob([content.endsWith("\n") ? content : `${content}\n`], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.style.display = "none";
    document.body.append(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const makeIcon = (symbolId, extraClass = "rfs-icon-sm") => {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("class", `rfs-icon ${extraClass}`.trim());
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(SVG_NS, "use");
    use.setAttribute("href", `assets/rfs-icons.svg#${symbolId}`);
    svg.append(use);
    return svg;
  };

  const safeHref = (url) => {
    if (typeof url !== "string") return "#";
    const trimmed = url.trim();
    if (trimmed.startsWith("https://") || trimmed.startsWith("http://")) return trimmed;
    return "#";
  };

  // XSS-safe inline formatting for `code` and **bold** inside installSteps
  const appendRichText = (parent, text) => {
    const str = String(text || "");
    const rx = /(`[^`]+`|\*\*[^*]+\*\*)/g;
    let last = 0;
    let m;
    while ((m = rx.exec(str)) !== null) {
      if (m.index > last) {
        parent.append(document.createTextNode(str.slice(last, m.index)));
      }
      const token = m[0];
      if (token.startsWith("`")) {
        const code = document.createElement("code");
        code.textContent = token.slice(1, -1);
        parent.append(code);
      } else {
        const strong = document.createElement("strong");
        strong.textContent = token.slice(2, -2);
        parent.append(strong);
      }
      last = m.index + token.length;
    }
    if (last < str.length) {
      parent.append(document.createTextNode(str.slice(last)));
    }
  };

  // XSS-safe lightweight syntax highlighter (pure textNode + span creation)
  const appendHighlightedLine = (parent, line, lang) => {
    const trimmed = line.trimStart();
    if (
      trimmed.startsWith("#") ||
      trimmed.startsWith(";") ||
      trimmed.startsWith("//") ||
      trimmed.startsWith("--") ||
      trimmed.startsWith("/*") ||
      trimmed.startsWith("<!--")
    ) {
      const span = document.createElement("span");
      span.className = "syn-cm";
      span.textContent = line;
      parent.append(span);
      return;
    }

    if (lang === "pn1" && line.startsWith("pn1:")) {
      const parts = line.split(":");
      if (parts.length >= 4) {
        const add = (cls, txt) => {
          const s = document.createElement("span");
          if (cls) s.className = cls;
          s.textContent = txt;
          parent.append(s);
        };
        add("syn-kw", parts[0]);
        parent.append(document.createTextNode(":"));
        add("syn-fn", parts[1]);
        parent.append(document.createTextNode(":"));
        add("syn-str", parts[2]);
        parent.append(document.createTextNode(":"));
        const rest = parts.slice(3).join(":");
        const byIdx = rest.lastIndexOf(",by=");
        if (byIdx !== -1) {
          add("syn-num", rest.slice(0, byIdx));
          parent.append(document.createTextNode(","));
          add("syn-cm", rest.slice(byIdx + 1));
        } else {
          add("syn-num", rest);
        }
        return;
      }
    }

    if ((lang === "toml" || lang === "ini") && /^\[[^\]]+\]\s*$/.test(trimmed)) {
      const span = document.createElement("span");
      span.className = "syn-fn";
      span.textContent = line;
      parent.append(span);
      return;
    }

    // Tokenize quoted strings, hex colors, keys before : or =
    const tokenRx = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|#[0-9A-Fa-f]{6,8}\b)/g;
    let last = 0;
    let m;
    while ((m = tokenRx.exec(line)) !== null) {
      if (m.index > last) {
        const chunk = line.slice(last, m.index);
        if (last === 0 && /^[\s]*[A-Za-z0-9_.\-@]+\s*[=:]/.test(chunk)) {
          const eqMatch = chunk.match(/^(\s*)([A-Za-z0-9_.\-@]+)(\s*[=:])(.*)$/);
          if (eqMatch) {
            if (eqMatch[1]) parent.append(document.createTextNode(eqMatch[1]));
            const k = document.createElement("span");
            k.className = "syn-fn";
            k.textContent = eqMatch[2];
            parent.append(k);
            parent.append(document.createTextNode(eqMatch[3] + eqMatch[4]));
          } else {
            parent.append(document.createTextNode(chunk));
          }
        } else {
          parent.append(document.createTextNode(chunk));
        }
      }
      const tok = m[0];
      const sp = document.createElement("span");
      if (tok.startsWith("#")) {
        sp.className = "syn-num";
      } else if (lang === "json" && line.slice(m.index + tok.length).trimStart().startsWith(":")) {
        sp.className = "syn-fn";
      } else {
        sp.className = "syn-str";
      }
      sp.textContent = tok;
      parent.append(sp);
      last = m.index + tok.length;
    }
    if (last < line.length) {
      parent.append(document.createTextNode(line.slice(last)));
    }
  };

  const renderHighlightedCode = (codeEl, snippet, lang) => {
    codeEl.replaceChildren();
    const lines = String(snippet || "").split("\n");
    lines.forEach((line, idx) => {
      appendHighlightedLine(codeEl, line, lang);
      if (idx < lines.length - 1) {
        codeEl.append(document.createTextNode("\n"));
      }
    });
  };

  const repoUrl = (base, relPath) =>
    encodeURI(`${base}${String(relPath || "").replace(/^\/+/, "")}`);

  const deriveDownloadFilename = (app, variant) => {
    const extByLang = {
      json: "json",
      toml: "toml",
      lua: "lua",
      css: "css",
      sh: "sh",
      ps1: "ps1",
      ini: "gitconfig",
      conf: "conf",
      xml: "xaml",
      pn1: "txt",
    };
    const allowedExtsByLang = {
      json: [".json"],
      toml: [".toml"],
      lua: [".lua"],
      css: [".css"],
      sh: [".sh"],
      ps1: [".ps1"],
      ini: [".gitconfig", ".ini", ".theme", ".cfg", ".colorscheme", ".reg"],
      conf: [".conf", ".minttyrc"],
      xml: [".xaml", ".xml", ".ps1xml"],
      pn1: [".txt"],
    };
    const lang = variant.copyLang || "text";
    const ext = extByLang[lang] || "txt";
    const filePath = variant.file || "";
    const base = filePath.split("/").pop() || "";
    const lowerBase = base.toLowerCase();

    if (app.slug === "privacynotes") {
      return `privacynotes-${variant.id}.txt`;
    }
    if (!base || lowerBase === "manifest.json" || lowerBase === "stylesheet.qss") {
      return `${app.slug}-${variant.id}.${ext}`;
    }
    if (app.slug === "ghostty" && lang === "conf" && !base.includes(".")) {
      return `${app.slug}-${lowerBase}`;
    }
    const allowed = allowedExtsByLang[lang] || [];
    const extMatches = allowed.some((suffix) => lowerBase.endsWith(suffix));
    if (extMatches) {
      return `${app.slug}-${lowerBase.replace(/\s+/g, "-")}`;
    }
    return `${app.slug}-${variant.id}.${ext}`;
  };

  // Delegated click handler for copy & download buttons (works on SSR fallback & hydrated DOM)
  document.addEventListener("click", async (e) => {
    const copyBtn = e.target.closest("[data-copy]");
    if (copyBtn) {
      const text = copyBtn.getAttribute("data-copy") || "";
      const themeName = copyBtn.getAttribute("data-theme-name");
      const ok = await copyText(text);
      const labelSpan = copyBtn.querySelector("span:last-child");
      if (ok && copyBtn.classList.contains("copy-code-btn")) {
        if (!copyBtn.dataset.origLabel) {
          copyBtn.dataset.origLabel = labelSpan ? labelSpan.textContent : copyBtn.textContent;
        }
        const orig = copyBtn.dataset.origLabel;
        if (labelSpan) labelSpan.textContent = "[ok] copied";
        else copyBtn.textContent = "[ok] copied";
        clearTimeout(copyBtn._copyTimer);
        copyBtn._copyTimer = setTimeout(() => {
          if (labelSpan) labelSpan.textContent = orig;
          else copyBtn.textContent = orig;
        }, 1800);
      }
      showToast(
        ok
          ? (themeName ? `Copied ${themeName}.` : `Copied ${text}`)
          : "Clipboard unavailable — copy directly from the code block.",
        copyBtn,
        ok ? "ok" : "fail"
      );
      return;
    }

    const dlBtn = e.target.closest("[data-download]");
    if (dlBtn) {
      const content = dlBtn.getAttribute("data-download") || "";
      const filename = dlBtn.getAttribute("data-filename") || "cyclorama-theme.txt";
      triggerDownload(filename, content);
      showToast(`Downloaded ${filename}`, dlBtn, "ok");
    }
  });

  // =========================================================================
  // 4. Accessible Inspector Tabs (roving keys + hidden="until-found" beforematch)
  // =========================================================================
  const tablistEl = document.getElementById("inspector-tablist");
  const panelsEl = document.getElementById("inspector-panels");

  const selectVariantTab = (variantId, moveFocus = false) => {
    if (!tablistEl || !panelsEl) return;
    const tabs = Array.from(tablistEl.querySelectorAll('.pn-tab[role="tab"]'));
    const panels = Array.from(panelsEl.querySelectorAll('.pn-panel[role="tabpanel"]'));
    const targetTab = tabs.find((t) => t.dataset.variantId === variantId) || tabs[0];
    if (!targetTab) return;
    const targetPanelId = targetTab.dataset.panel;

    tabs.forEach((t) => {
      const hit = t === targetTab;
      t.setAttribute("aria-selected", String(hit));
      t.tabIndex = hit ? 0 : -1;
    });

    panels.forEach((p) => {
      if (p.id === targetPanelId) p.removeAttribute("hidden");
      else p.setAttribute("hidden", "until-found");
    });

    targetTab.scrollIntoView({ block: "nearest", inline: "nearest" });
    if (moveFocus) targetTab.focus();
  };

  const bindTablistInteraction = () => {
    if (!tablistEl || !panelsEl) return;
    tablistEl.addEventListener("click", (e) => {
      const tab = e.target.closest('.pn-tab[role="tab"]');
      if (!tab) return;
      selectVariantTab(tab.dataset.variantId, false);
      state.activeVariantId = tab.dataset.variantId;
    });

    tablistEl.addEventListener("keydown", (e) => {
      const tabs = Array.from(tablistEl.querySelectorAll('.pn-tab[role="tab"]'));
      const current = e.target.closest('.pn-tab[role="tab"]');
      if (!current) return;
      const idx = tabs.indexOf(current);
      if (idx === -1) return;
      let next = -1;
      if (e.key === "ArrowRight") next = (idx + 1) % tabs.length;
      else if (e.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = tabs.length - 1;
      if (next !== -1) {
        e.preventDefault();
        const nextTab = tabs[next];
        state.activeVariantId = nextTab.dataset.variantId;
        selectVariantTab(nextTab.dataset.variantId, true);
      }
    });

    panelsEl.addEventListener("beforematch", (e) => {
      const panel = e.target.closest('.pn-panel[role="tabpanel"]');
      if (!panel) return;
      const owner = Array.from(tablistEl.querySelectorAll('.pn-tab[role="tab"]')).find(
        (t) => t.dataset.panel === panel.id
      );
      if (owner) {
        state.activeVariantId = owner.dataset.variantId;
        selectVariantTab(owner.dataset.variantId, false);
      }
    });
  };

  // =========================================================================
  // 5. 28-App Gallery State, Directory Grid, and Dynamic Inspector Hydration
  // =========================================================================
  const state = {
    catalog: null,
    activeCategory: "all",
    searchQuery: "",
    globalPreviewVariant: "cyclorama-dawn",
    activeAppSlug: "privacynotes",
    activeVariantId: "cyclorama-dawn",
  };

  bindTablistInteraction();

  const pageScrollEl = document.getElementById("page-scroll");
  const appsGridEl = document.getElementById("apps-grid");
  const categoryBarEl = document.getElementById("category-bar");
  const searchInputEl = document.getElementById("app-search");
  const resultCountEl = document.getElementById("result-count");
  const appSelectEl = document.getElementById("app-select");
  const prevBtnEl = document.getElementById("inspector-prev");
  const nextBtnEl = document.getElementById("inspector-next");
  const inspectorEl = document.getElementById("inspector");
  const inspectorKickerEl = document.getElementById("inspector-kicker");
  const inspectorFormatEl = document.getElementById("inspector-format");
  const inspectorHomepageEl = document.getElementById("inspector-homepage");
  const inspectorHeadingEl = document.getElementById("inspector-heading");
  const inspectorInstallEl = document.getElementById("inspector-install-summary");

  const getFilteredApps = () => {
    if (!state.catalog) return [];
    const q = state.searchQuery.trim().toLowerCase();
    return state.catalog.apps.filter((app) => {
      if (state.activeCategory !== "all" && app.category !== state.activeCategory) {
        return false;
      }
      if (!q) return true;
      const haystack = [
        app.name,
        app.slug,
        app.category,
        app.format,
        app.install,
        ...(app.variants || []).map((v) => `${v.name} ${v.tagline} ${v.copyLang}`),
      ]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  };

  const scrollToInspector = () => {
    if (!inspectorEl) return;
    if (pageScrollEl) {
      const containerRect = pageScrollEl.getBoundingClientRect();
      const targetRect = inspectorEl.getBoundingClientRect();
      const top = pageScrollEl.scrollTop + (targetRect.top - containerRect.top) - 20;
      pageScrollEl.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    } else {
      inspectorEl.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const updateHash = (slug) => {
    try {
      history.replaceState(null, "", `#app=${encodeURIComponent(slug)}`);
    } catch {}
  };

  const buildInspectorPanel = (app, variant, isActive) => {
    const panel = document.createElement("div");
    panel.className = "pn-panel";
    panel.setAttribute("role", "tabpanel");
    panel.id = `panel-${variant.id}`;
    panel.setAttribute("aria-labelledby", `tab-${variant.id}`);
    if (!isActive) panel.setAttribute("hidden", "until-found");

    const inner = document.createElement("div");
    inner.className = "pn-panel-inner";

    // Left column: Preview SVG + Install Steps + Raw GitHub files
    const previewCol = document.createElement("div");
    previewCol.className = "pn-preview-col";

    const img = document.createElement("img");
    img.src = variant.preview;
    img.alt = `${app.name} ${variant.name} (${variant.lx} ${variant.mode}) theme preview`;
    img.width = 660;
    img.height = 390;
    if (!isActive) img.loading = "lazy";
    previewCol.append(img);

    const guideCard = document.createElement("div");
    guideCard.className = "inspector-guide-card";

    if (Array.isArray(app.installSteps) && app.installSteps.length > 0) {
      const stepsBlock = document.createElement("div");
      stepsBlock.className = "guide-block";
      const h4 = document.createElement("h4");
      h4.textContent = "Install Steps";
      const ol = document.createElement("ol");
      ol.className = "install-steps-list";
      app.installSteps.forEach((stepText) => {
        const li = document.createElement("li");
        appendRichText(li, stepText);
        ol.append(li);
      });
      stepsBlock.append(h4, ol);
      guideCard.append(stepsBlock);
    }

    if (Array.isArray(app.files) && app.files.length > 0) {
      const filesBlock = document.createElement("div");
      filesBlock.className = "guide-block";
      const h4 = document.createElement("h4");
      h4.textContent = "Repository Files";
      const ul = document.createElement("ul");
      ul.className = "raw-files-list";
      app.files.forEach((f) => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = repoUrl(REPO_BLOB_BASE, f.path);
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.append(makeIcon("rfs-i-file-code", "rfs-icon-sm"));
        const span = document.createElement("span");
        span.textContent = f.label;
        a.append(span);
        li.append(a);
        ul.append(li);
      });
      filesBlock.append(h4, ul);
      guideCard.append(filesBlock);
    }

    previewCol.append(guideCard);

    // Right column: Details, Swatches, Code Card (Copy + Download), Meta row
    const detailCol = document.createElement("div");
    detailCol.className = "pn-detail-col";

    const detailTop = document.createElement("div");
    detailTop.className = "pn-detail-top";
    const h3 = document.createElement("h3");
    h3.textContent = variant.name;

    const badges = document.createElement("div");
    badges.className = "detail-badges";
    const lxBadge = document.createElement("span");
    lxBadge.className = `rfs-badge ${variant.id === "cyclorama-steel" ? "is-steel" : "is-beacon"}`;
    lxBadge.textContent = `${variant.lx} \u00B7 ${variant.mode === "light" ? "Light" : "Dark"}`;
    const okBadge = document.createElement("span");
    okBadge.className = "rfs-badge is-ok";
    okBadge.textContent = app.slug === "privacynotes" ? "[17/17 PASS]" : "[WCAG AA PASS]";
    badges.append(lxBadge, okBadge);
    detailTop.append(h3, badges);

    const desc = document.createElement("p");
    desc.className = "pn-desc";
    desc.textContent = variant.tagline;

    // 6 Click-to-Copy Hex Swatches
    const swatchStrip = document.createElement("div");
    swatchStrip.className = "swatch-strip";
    swatchStrip.setAttribute("aria-label", "Click any color swatch to copy hex");
    (variant.swatches || []).slice(0, 6).forEach((sw) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "sw-btn";
      btn.setAttribute("data-copy", sw.hex);
      const chip = document.createElement("span");
      chip.className = "sw-chip";
      chip.style.background = sw.hex;
      const lbl = document.createElement("span");
      lbl.textContent = sw.label;
      const hex = document.createElement("code");
      hex.textContent = sw.hex;
      btn.append(chip, lbl, hex);
      swatchStrip.append(btn);
    });

    // Code Card with Copy + Download
    const codeCard = document.createElement("div");
    codeCard.className = "rfs-code-card";

    const codeHead = document.createElement("div");
    codeHead.className = "rfs-code-head";
    const langSpan = document.createElement("span");
    langSpan.className = "rfs-code-lang";
    langSpan.textContent = `[${variant.copyLang || "text"}] ${variant.copyLabel || "Theme snippet"}`;

    const codeActions = document.createElement("div");
    codeActions.className = "code-actions";

    const dlBtn = document.createElement("button");
    dlBtn.type = "button";
    dlBtn.className = "rfs-btn rfs-btn-sm rfs-btn-outline download-code-btn";
    dlBtn.setAttribute("data-filename", deriveDownloadFilename(app, variant));
    dlBtn.setAttribute("data-download", variant.copySnippet || "");
    const dlText = document.createElement("span");
    dlText.textContent = "Download";
    dlBtn.append(makeIcon("rfs-i-download", "rfs-icon-sm"), dlText);

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "rfs-btn rfs-btn-sm rfs-btn-horizon copy-code-btn";
    copyBtn.setAttribute("data-theme-name", `${app.name} \u2014 ${variant.name}`);
    copyBtn.setAttribute("data-copy", variant.copySnippet || "");
    const copySpan = document.createElement("span");
    copySpan.textContent = "Copy";
    copyBtn.append(makeIcon("rfs-i-copy", "rfs-icon-sm"), copySpan);

    codeActions.append(dlBtn, copyBtn);
    codeHead.append(langSpan, codeActions);

    const pre = document.createElement("pre");
    pre.className = "pn-code-pre";
    const code = document.createElement("code");
    renderHighlightedCode(code, variant.copySnippet || "", variant.copyLang || "text");
    pre.append(code);
    codeCard.append(codeHead, pre);

    // Metadata Row
    const metaRow = document.createElement("div");
    metaRow.className = "pn-meta-row";
    const roleSpan = document.createElement("span");
    roleSpan.append(document.createTextNode("Role: "));
    const roleStrong = document.createElement("strong");
    roleStrong.textContent = variant.accentRole;
    roleSpan.append(roleStrong);

    const fileSpan = document.createElement("span");
    fileSpan.append(document.createTextNode("File: "));
    const fileCode = document.createElement("code");
    fileCode.textContent = variant.file;
    fileSpan.append(fileCode);

    const ghLink = document.createElement("a");
    ghLink.href = repoUrl(REPO_BLOB_BASE, variant.file);
    ghLink.target = "_blank";
    ghLink.rel = "noopener noreferrer";
    ghLink.textContent = "View on GitHub";

    metaRow.append(roleSpan, fileSpan, ghLink);

    detailCol.append(detailTop, desc, swatchStrip, codeCard, metaRow);
    inner.append(previewCol, detailCol);
    panel.append(inner);
    return panel;
  };

  const renderInspector = (slug, variantId = state.activeVariantId, shouldScroll = false, shouldPushHash = false) => {
    if (!state.catalog || !tablistEl || !panelsEl) return;
    const apps = state.catalog.apps;
    const idx = apps.findIndex((a) => a.slug === slug);
    const app = idx !== -1 ? apps[idx] : apps[0];
    if (!app) return;

    state.activeAppSlug = app.slug;
    const activeVid = app.variants.some((v) => v.id === variantId) ? variantId : app.variants[0].id;
    state.activeVariantId = activeVid;

    const appNum = String(apps.indexOf(app) + 1).padStart(2, "0");
    if (inspectorKickerEl) {
      inspectorKickerEl.textContent = `[${app.category.toLowerCase()} \u00B7 ${appNum}/${apps.length}]`;
    }
    if (inspectorFormatEl) inspectorFormatEl.textContent = app.format;
    if (inspectorHomepageEl) {
      inspectorHomepageEl.href = safeHref(app.homepage);
      inspectorHomepageEl.textContent = "Official site";
    }
    if (inspectorHeadingEl) inspectorHeadingEl.textContent = app.name;
    if (inspectorInstallEl) {
      inspectorInstallEl.replaceChildren();
      inspectorInstallEl.append(document.createTextNode("Install: "));
      const strong = document.createElement("strong");
      strong.textContent = app.install;
      inspectorInstallEl.append(strong);
    }
    if (appSelectEl) appSelectEl.value = app.slug;

    // Update tablist
    tablistEl.setAttribute("aria-label", `${app.name} Cyclorama Dawn variants`);
    const tabFrag = document.createDocumentFragment();
    const panelFrag = document.createDocumentFragment();

    app.variants.forEach((v) => {
      const isHit = v.id === activeVid;
      const tab = document.createElement("button");
      tab.type = "button";
      tab.className = "pn-tab";
      tab.setAttribute("role", "tab");
      tab.id = `tab-${v.id}`;
      tab.setAttribute("aria-selected", String(isHit));
      tab.setAttribute("aria-controls", `panel-${v.id}`);
      if (!isHit) tab.tabIndex = -1;
      tab.dataset.panel = `panel-${v.id}`;
      tab.dataset.variantId = v.id;

      const dot = document.createElement("span");
      dot.className = "tab-dot";
      dot.style.background = VARIANT_DOTS[v.id] || "#FF9254";
      dot.setAttribute("aria-hidden", "true");

      const name = document.createElement("span");
      name.className = "tab-name";
      name.textContent = v.name;

      const lx = document.createElement("span");
      lx.className = "tab-lx";
      lx.textContent = `${v.lx} \u00B7 ${v.mode === "light" ? "Light" : v.accentRole.split(" ")[0]}`;

      tab.append(dot, name, lx);
      tabFrag.append(tab);
      panelFrag.append(buildInspectorPanel(app, v, isHit));
    });

    tablistEl.replaceChildren(tabFrag);
    panelsEl.replaceChildren(panelFrag);

    // Sync active highlight in directory grid
    if (appsGridEl) {
      appsGridEl.querySelectorAll(".app-card").forEach((card) => {
        card.classList.toggle("is-active", card.dataset.slug === app.slug);
      });
    }

    if (shouldPushHash) updateHash(app.slug);
    if (shouldScroll) scrollToInspector();
  };

  const renderAppsGrid = () => {
    if (!state.catalog || !appsGridEl) return;
    const filtered = getFilteredApps();
    const total = state.catalog.apps.length;

    if (resultCountEl) {
      resultCountEl.textContent =
        filtered.length === total
          ? `Showing ${total} of ${total} apps`
          : `Showing ${filtered.length} of ${total} apps`;
    }

    if (filtered.length === 0) {
      const wrap = document.createElement("div");
      wrap.className = "rfs-state-box is-empty apps-empty-wrap";

      const badge = document.createElement("span");
      badge.className = "rfs-badge b-warn";
      const k = document.createElement("span");
      k.className = "k";
      k.textContent = "[0 matches]";
      badge.append(k, document.createTextNode(" No app ports match that filter"));

      const msg = document.createElement("p");
      msg.className = "section-sub";
      msg.textContent = "Try clearing the search query or switching back to All categories.";

      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.className = "rfs-btn rfs-btn-sm rfs-btn-outline";
      resetBtn.style.justifySelf = "start";
      resetBtn.textContent = "Reset filters";
      resetBtn.addEventListener("click", () => {
        state.activeCategory = "all";
        state.searchQuery = "";
        if (searchInputEl) searchInputEl.value = "";
        syncCategoryButtons();
        renderAppsGrid();
      });

      wrap.append(badge, msg, resetBtn);
      appsGridEl.replaceChildren(wrap);
      return;
    }

    const frag = document.createDocumentFragment();
    filtered.forEach((app, idx) => {
      const variant =
        app.variants.find((v) => v.id === state.globalPreviewVariant) || app.variants[0];

      const card = document.createElement("article");
      card.className = "app-card";
      if (app.slug === state.activeAppSlug) card.classList.add("is-active");
      card.dataset.slug = app.slug;

      // Preview thumbnail button
      const thumbBtn = document.createElement("button");
      thumbBtn.type = "button";
      thumbBtn.className = "app-card-thumb";
      thumbBtn.setAttribute("aria-label", `Inspect ${app.name} themes`);
      thumbBtn.addEventListener("click", () => {
        renderInspector(app.slug, state.globalPreviewVariant, true, true);
      });

      const img = document.createElement("img");
      img.src = variant.preview;
      img.alt = `${app.name} ${variant.name} preview`;
      img.width = 660;
      img.height = 390;
      if (idx >= 4) img.loading = "lazy";
      thumbBtn.append(img);

      // Card body
      const body = document.createElement("div");
      body.className = "app-card-body";

      const kickerRow = document.createElement("div");
      kickerRow.className = "app-card-kicker-row";
      const catSpan = document.createElement("span");
      catSpan.className = "app-card-cat";
      catSpan.textContent = app.category;

      const dots = document.createElement("span");
      dots.className = "app-card-dots";
      dots.setAttribute("aria-label", "3 variants: Dawn, Steel, Day");
      ["cyclorama-dawn", "cyclorama-steel", "cyclorama-day"].forEach((vid) => {
        const d = document.createElement("span");
        d.className = "app-card-dot";
        d.style.background = VARIANT_DOTS[vid];
        dots.append(d);
      });
      kickerRow.append(catSpan, dots);

      const titleBtn = document.createElement("button");
      titleBtn.type = "button";
      titleBtn.className = "app-card-title-btn";
      titleBtn.textContent = app.name;
      titleBtn.addEventListener("click", () => {
        renderInspector(app.slug, state.globalPreviewVariant, true, true);
      });

      const fmtSpan = document.createElement("span");
      fmtSpan.className = "app-card-format";
      fmtSpan.textContent = app.format;

      const installP = document.createElement("p");
      installP.className = "app-card-install";
      installP.textContent = app.install;

      body.append(kickerRow, titleBtn, fmtSpan, installP);

      // Card footer
      const foot = document.createElement("div");
      foot.className = "app-card-foot";

      const inspectBtn = document.createElement("button");
      inspectBtn.type = "button";
      inspectBtn.className = "rfs-btn rfs-btn-sm rfs-btn-outline";
      const inspectLbl = document.createElement("span");
      inspectLbl.textContent = "Inspect & Copy";
      inspectBtn.append(makeIcon("rfs-i-code", "rfs-icon-sm"), inspectLbl);
      inspectBtn.addEventListener("click", () => {
        renderInspector(app.slug, state.globalPreviewVariant, true, true);
      });

      const dirLink = document.createElement("a");
      dirLink.className = "app-card-dir-link";
      dirLink.href = repoUrl(REPO_TREE_BASE, app.path);
      dirLink.target = "_blank";
      dirLink.rel = "noopener noreferrer";
      dirLink.setAttribute("aria-label", `Open ${app.name} files on GitHub`);
      dirLink.textContent = "files/";

      foot.append(inspectBtn, dirLink);

      card.append(thumbBtn, body, foot);
      frag.append(card);
    });

    appsGridEl.replaceChildren(frag);
  };

  const syncCategoryButtons = () => {
    if (!categoryBarEl) return;
    categoryBarEl.querySelectorAll("[data-category]").forEach((btn) => {
      btn.setAttribute("aria-pressed", String(btn.dataset.category === state.activeCategory));
    });
  };

  const populateCategoryBar = (catalog) => {
    if (!categoryBarEl) return;
    const frag = document.createDocumentFragment();

    const makeChip = (categoryValue, label, count, showTag) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "rfs-chip";
      btn.dataset.category = categoryValue;
      btn.setAttribute("aria-pressed", String(state.activeCategory === categoryValue));
      if (showTag) {
        const k = document.createElement("span");
        k.className = "k";
        k.textContent = "[all]";
        btn.append(k, document.createTextNode(" "));
      }
      const lbl = document.createElement("span");
      lbl.textContent = label;
      const cnt = document.createElement("span");
      cnt.className = "chip-count";
      cnt.textContent = `(${count})`;
      btn.append(lbl, document.createTextNode(" "), cnt);
      btn.addEventListener("click", () => {
        state.activeCategory = categoryValue;
        syncCategoryButtons();
        renderAppsGrid();
      });
      return btn;
    };

    frag.append(makeChip("all", "All", catalog.stats.apps, true));
    catalog.categories.forEach((cat) => {
      frag.append(makeChip(cat.name, cat.name, cat.count, false));
    });
    categoryBarEl.replaceChildren(frag);
  };

  const populateAppSelect = (catalog) => {
    if (!appSelectEl) return;
    const frag = document.createDocumentFragment();
    catalog.categories.forEach((cat) => {
      const group = document.createElement("optgroup");
      group.label = `${cat.name} (${cat.count})`;
      catalog.apps
        .filter((a) => a.category === cat.name)
        .forEach((app) => {
          const opt = document.createElement("option");
          opt.value = app.slug;
          opt.textContent = app.name;
          group.append(opt);
        });
      frag.append(group);
    });
    appSelectEl.replaceChildren(frag);
  };

  const parseDeepLink = (catalog) => {
    const raw = (window.location.hash || "").replace(/^#/, "");
    if (!raw) return null;
    if (raw.startsWith("app=")) {
      const params = new URLSearchParams(raw);
      const slug = params.get("app");
      const variant = params.get("variant");
      if (slug && catalog.apps.some((a) => a.slug === slug)) {
        return { slug, variant };
      }
    }
    if (catalog.apps.some((a) => a.slug === raw)) {
      return { slug: raw, variant: null };
    }
    return null;
  };

  // Global Dawn/Steel/Day preview switcher
  document.querySelectorAll("[data-global-variant]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const vid = btn.dataset.globalVariant;
      if (!vid) return;
      state.globalPreviewVariant = vid;
      document.querySelectorAll("[data-global-variant]").forEach((b) => {
        b.setAttribute("aria-pressed", String(b === btn));
      });

      // Flip all visible cards' live SVG thumbnails in-place without layout shift
      if (state.catalog && appsGridEl) {
        const bySlug = new Map(state.catalog.apps.map((a) => [a.slug, a]));
        appsGridEl.querySelectorAll(".app-card").forEach((card) => {
          const app = bySlug.get(card.dataset.slug);
          if (!app) return;
          const v = app.variants.find((item) => item.id === vid) || app.variants[0];
          const img = card.querySelector(".app-card-thumb img");
          if (img && v) {
            img.src = v.preview;
            img.alt = `${app.name} ${v.name} preview`;
          }
        });
      }
    });
  });

  if (searchInputEl) {
    searchInputEl.addEventListener("input", () => {
      state.searchQuery = searchInputEl.value;
      renderAppsGrid();
    });
  }

  if (appSelectEl) {
    appSelectEl.addEventListener("change", () => {
      renderInspector(appSelectEl.value, state.activeVariantId, false, true);
    });
  }

  const stepInspector = (delta) => {
    if (!state.catalog) return;
    const apps = state.catalog.apps;
    const idx = apps.findIndex((a) => a.slug === state.activeAppSlug);
    const nextIdx = (idx + delta + apps.length) % apps.length;
    renderInspector(apps[nextIdx].slug, state.activeVariantId, false, true);
  };

  if (prevBtnEl) prevBtnEl.addEventListener("click", () => stepInspector(-1));
  if (nextBtnEl) nextBtnEl.addEventListener("click", () => stepInspector(1));

  // Hydrate from docs/assets/catalog.json
  const hydrate = async () => {
    try {
      const resp = await fetch("assets/catalog.json", { cache: "no-cache" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const catalog = await resp.json();
      state.catalog = catalog;

      const statApps = document.getElementById("stat-apps");
      const statVariants = document.getElementById("stat-variants");
      const statTokens = document.getElementById("stat-tokens");
      if (statApps) {
        statApps.textContent = `${catalog.stats.apps} \u00B7 Across ${catalog.stats.categories} categories`;
      }
      if (statVariants) {
        statVariants.textContent = `${catalog.stats.variants} \u00B7 Dawn, Steel, Day`;
      }
      if (statTokens) {
        statTokens.textContent = `rfs.tokens.json v${catalog.version}`;
      }

      populateCategoryBar(catalog);
      populateAppSelect(catalog);

      const deep = parseDeepLink(catalog);
      if (deep) {
        state.activeAppSlug = deep.slug;
        if (deep.variant) state.activeVariantId = deep.variant;
      }

      renderAppsGrid();
      renderInspector(state.activeAppSlug, state.activeVariantId, Boolean(deep), false);

      window.addEventListener("hashchange", () => {
        const target = parseDeepLink(catalog);
        if (target) {
          renderInspector(
            target.slug,
            target.variant || state.activeVariantId,
            true,
            false
          );
        }
      });
    } catch (err) {
      if (appsGridEl) {
        const box = document.createElement("div");
        box.className = "rfs-state-box is-error apps-empty-wrap";
        const badge = document.createElement("span");
        badge.className = "rfs-badge b-fail";
        const k = document.createElement("span");
        k.className = "k";
        k.textContent = "[err]";
        badge.append(k, document.createTextNode(" Could not load assets/catalog.json"));
        const p = document.createElement("p");
        p.className = "section-sub";
        p.textContent = "Serve docs/ over HTTP (e.g. python -m http.server) or browse the live GitHub Pages gallery. PrivacyNotes themes remain available below.";
        box.append(badge, p);
        appsGridEl.replaceChildren(box);
      }
    }
  };

  hydrate();
})();
