(() => {
  "use strict";

  // 1. Dark-default (LX 263) / Light opt-in (LX 512) toggle with cross-tab storage sync
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
    if (e.key !== "color-scheme" || !meta) return;
    meta.content = e.newValue === "light" ? "light" : "dark";
    syncTheme();
  });

  if (themeBtn && meta) {
    themeBtn.addEventListener("click", () => {
      const target = currentMode() === "dark" ? "light" : "dark";
      const apply = () => {
        try {
          if (target === "dark") localStorage.removeItem("color-scheme");
          else localStorage.setItem("color-scheme", "light");
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

  // 2. Accessible PrivacyNotes tabs with roving keyboard nav & hidden="until-found" beforematch sync
  const tabs = Array.from(document.querySelectorAll('.pn-tab[role="tab"]'));
  const panels = Array.from(document.querySelectorAll('.pn-panel[role="tabpanel"]'));

  const selectTab = (tab, moveFocus = false) => {
    const targetId = tab.dataset.panel;
    tabs.forEach((t) => {
      const hit = t === tab;
      t.setAttribute("aria-selected", String(hit));
      t.tabIndex = hit ? 0 : -1;
    });
    panels.forEach((p) => {
      if (p.id === targetId) p.removeAttribute("hidden");
      else p.setAttribute("hidden", "until-found");
    });
    tab.scrollIntoView({ block: "nearest", inline: "nearest" });
    if (moveFocus) tab.focus();
  };

  tabs.forEach((tab, idx) => {
    tab.addEventListener("click", () => selectTab(tab, false));
    tab.addEventListener("keydown", (e) => {
      let next = -1;
      if (e.key === "ArrowRight") next = (idx + 1) % tabs.length;
      else if (e.key === "ArrowLeft") next = (idx - 1 + tabs.length) % tabs.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = tabs.length - 1;
      if (next !== -1) {
        e.preventDefault();
        selectTab(tabs[next], true);
      }
    });
  });

  panels.forEach((panel) => {
    panel.addEventListener("beforematch", () => {
      const owner = tabs.find((t) => t.dataset.panel === panel.id);
      if (owner) selectTab(owner, false);
    });
  });

  // 3. Semantic colored popover="manual" toast region with focus-safe auto-dismiss + ariaNotify fallback
  const toastRegion = document.getElementById("toast-region");
  const liveStatus = document.getElementById("live-status");

  const announce = (msg) => {
    if (typeof document.ariaNotify === "function") {
      try { document.ariaNotify(msg); return; } catch {}
    }
    if (liveStatus) {
      liveStatus.textContent = "";
      requestAnimationFrame(() => { liveStatus.textContent = msg; });
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

  const showToast = (msg, triggerEl) => {
    if (!toastRegion) return;
    const el = document.createElement("div");
    el.className = "rfs-toast is-ok";

    const badge = document.createElement("span");
    badge.className = "rfs-badge b-ok";
    const k = document.createElement("span");
    k.className = "k";
    k.textContent = "[ok]";
    badge.append(k);

    const body = document.createElement("span");
    body.style.flex = "1 1 auto";
    body.textContent = msg;

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "rfs-toast-close";
    closeBtn.setAttribute("aria-label", "Dismiss notification");
    closeBtn.textContent = "×";

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

  // 4. One-click copy for pn1: theme codes and hex color swatches (with inline + toast confirmation)
  document.querySelectorAll("[data-copy]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const text = btn.getAttribute("data-copy") || "";
      const themeName = btn.getAttribute("data-theme-name");
      const ok = await copyText(text);
      const labelSpan = btn.querySelector("span:last-child");
      if (ok && btn.classList.contains("copy-code-btn")) {
        if (!btn.dataset.origLabel) {
          btn.dataset.origLabel = labelSpan ? labelSpan.textContent : btn.textContent;
        }
        const orig = btn.dataset.origLabel;
        if (labelSpan) labelSpan.textContent = "[ok] copied";
        else btn.textContent = "[ok] copied";
        clearTimeout(btn._copyTimer);
        btn._copyTimer = setTimeout(() => {
          if (labelSpan) labelSpan.textContent = orig;
          else btn.textContent = orig;
        }, 1800);
      }
      showToast(
        ok
          ? (themeName ? `Copied ${themeName} pn1: theme code.` : `Copied ${text}`)
          : "Clipboard unavailable — copy directly from the code block.",
        btn
      );
    });
  });
})();
