(function () {
  "use strict";

  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------------- theme toggle ---------------- */

  var THEME_KEY = "tweet-pulse-theme";
  var toggle = document.getElementById("theme-toggle");
  var savedTheme = null;

  try {
    savedTheme = localStorage.getItem(THEME_KEY);
  } catch (e) {
    savedTheme = null;
  }

  if (savedTheme) {
    document.documentElement.setAttribute("data-theme", savedTheme);
  }

  if (toggle) {
    toggle.addEventListener("click", function () {
      var current = document.documentElement.getAttribute("data-theme") || "dark";
      var next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      try {
        localStorage.setItem(THEME_KEY, next);
      } catch (e) {
        /* ignore */
      }
    });
  }

  /* ---------------- animated readout ---------------- */

  function animateCount(el) {
    if (!el) return;
    var target = parseInt(el.getAttribute("data-count-to"), 10) || 0;

    if (reduceMotion) {
      el.textContent = target;
      return;
    }

    var start = null;
    var duration = 900;

    function step(ts) {
      if (start === null) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.round(eased * target);
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  function animateSegments() {
    var segments = document.querySelectorAll(".readout__segment");
    segments.forEach(function (seg) {
      var target = seg.getAttribute("data-target-width") || "0";
      if (reduceMotion) {
        seg.style.width = target + "%";
      } else {
        requestAnimationFrame(function () {
          seg.style.width = target + "%";
        });
      }
    });
  }

  function animateDial() {
    var dial = document.getElementById("confidence-dial");
    var numberEl = document.getElementById("confidence-number");
    if (!dial) return;

    var target = parseFloat(dial.getAttribute("data-target-pct")) || 0;

    if (reduceMotion) {
      dial.style.setProperty("--pct", target);
      if (numberEl) numberEl.textContent = target + "%";
      return;
    }

    var start = null;
    var duration = 900;

    function step(ts) {
      if (start === null) start = ts;
      var progress = Math.min((ts - start) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      var current = eased * target;
      dial.style.setProperty("--pct", current);
      if (numberEl) numberEl.textContent = Math.round(current) + "%";
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  animateCount(document.getElementById("total-number"));
  animateSegments();
  animateDial();

  /* ---------------- tabs ---------------- */

  var tabs = Array.prototype.slice.call(document.querySelectorAll(".tabs__tab"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".tab-panel"));
  var indicator = document.querySelector(".tabs__indicator");

  function moveIndicator(tabEl) {
    if (!indicator || !tabEl) return;
    indicator.style.width = tabEl.offsetWidth + "px";
    indicator.style.transform = "translateX(" + tabEl.offsetLeft + "px)";
  }

  function activateTab(name) {
    tabs.forEach(function (t) {
      var isActive = t.getAttribute("data-tab") === name;
      t.classList.toggle("is-active", isActive);
      t.setAttribute("aria-selected", isActive ? "true" : "false");
      if (isActive) moveIndicator(t);
    });
    panels.forEach(function (p) {
      p.classList.toggle("is-active", p.getAttribute("data-panel") === name);
    });
    applyFilter();
  }

  tabs.forEach(function (t) {
    t.addEventListener("click", function () {
      activateTab(t.getAttribute("data-tab"));
    });
  });

  window.addEventListener("resize", function () {
    var active = document.querySelector(".tabs__tab.is-active");
    moveIndicator(active);
  });

  var initialActive = document.querySelector(".tabs__tab.is-active");
  if (initialActive) {
    // Wait a tick so layout/fonts have settled before measuring.
    requestAnimationFrame(function () {
      moveIndicator(initialActive);
    });
  }

  /* ---------------- all-comments dataset ---------------- */

  var dataEl = document.getElementById("all-comments-data");
  var allComments = [];
  try {
    allComments = dataEl ? JSON.parse(dataEl.textContent) : [];
  } catch (e) {
    allComments = [];
  }

  var PAGE_SIZE = 30;
  var visibleCount = PAGE_SIZE;

  var allListEl = document.getElementById("all-list");
  var loadMoreBtn = document.getElementById("load-more");

  function currentFilters() {
    var searchEl = document.getElementById("comment-search");
    var sentimentEl = document.getElementById("sentiment-filter");
    return {
      text: searchEl ? searchEl.value.trim().toLowerCase() : "",
      sentiment: sentimentEl ? sentimentEl.value : "all",
    };
  }

  function filteredAllComments() {
    var f = currentFilters();
    return allComments.filter(function (row) {
      if (f.sentiment !== "all" && row.sentiment !== f.sentiment) return false;
      if (f.text && row.comment.toLowerCase().indexOf(f.text) === -1) return false;
      return true;
    });
  }

  function transcriptLineHTML(row) {
    var pct = Math.round((row.score || 0) * 1000) / 10;
    var sentiment = row.sentiment || "unknown";
    var safeText = String(row.comment || "").replace(/</g, "&lt;");
    return (
      '<div class="transcript-line transcript-line--' + sentiment + '">' +
      '<span class="transcript-line__tick"></span>' +
      "<p class=\"transcript-line__text\">" + safeText + "</p>" +
      '<span class="transcript-line__meta">' +
      '<span class="transcript-line__score">' + pct + '%</span>' +
      '<span class="transcript-line__sentiment">' + sentiment + "</span>" +
      "</span>" +
      "</div>"
    );
  }

  function renderAllPanel() {
    if (!allListEl) return;

    var rows = filteredAllComments();

    if (rows.length === 0) {
      allListEl.innerHTML = '<p class="empty-note">No comments match your search.</p>';
      if (loadMoreBtn) loadMoreBtn.hidden = true;
      return;
    }

    var slice = rows.slice(0, visibleCount);
    allListEl.innerHTML = slice.map(transcriptLineHTML).join("");

    if (loadMoreBtn) {
      loadMoreBtn.hidden = visibleCount >= rows.length;
    }
  }

  if (loadMoreBtn) {
    loadMoreBtn.addEventListener("click", function () {
      visibleCount += PAGE_SIZE;
      renderAllPanel();
    });
  }

  /* ---------------- search / filter across server-rendered tabs ---------------- */

  function applyFilter() {
    var activePanel = document.querySelector(".tab-panel.is-active");
    if (!activePanel) return;

    if (activePanel.getAttribute("data-panel") === "all") {
      visibleCount = PAGE_SIZE;
      renderAllPanel();
      return;
    }

    var f = currentFilters();
    var lines = activePanel.querySelectorAll(".transcript-line");

    lines.forEach(function (line) {
      var text = line.querySelector(".transcript-line__text").textContent.toLowerCase();
      var sentimentEl = line.querySelector(".transcript-line__sentiment");
      var sentiment = sentimentEl ? sentimentEl.textContent.trim() : "";

      var matchesText = !f.text || text.indexOf(f.text) !== -1;
      var matchesSentiment = f.sentiment === "all" || sentiment === f.sentiment;

      line.style.display = matchesText && matchesSentiment ? "" : "none";
    });
  }

  var searchInput = document.getElementById("comment-search");
  var sentimentSelect = document.getElementById("sentiment-filter");

  if (searchInput) searchInput.addEventListener("input", applyFilter);
  if (sentimentSelect) sentimentSelect.addEventListener("change", applyFilter);

  renderAllPanel();
})();
