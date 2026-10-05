const CONFIG = {
  username: "tomrick99",
  api: "https://github-contributions-api.jogruber.de/v4/tomrick99?y=last",
  localData: "./contributions.json",
};

const els = {
  frame: document.querySelector("#heatmapFrame"),
  heatmap: document.querySelector("#heatmap"),
  monthRow: document.querySelector("#monthRow"),
  loading: document.querySelector("#loadingState"),
  tooltip: document.querySelector("#tooltip"),
  replay: document.querySelector("#replayButton"),
  comet: document.querySelector("#comet"),
  total: document.querySelector("#totalCount"),
  active: document.querySelector("#activeDays"),
  streak: document.querySelector("#longestStreak"),
};

const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
let contributionDays = [];
let cometAnimation;

async function loadContributions() {
  const sources = [CONFIG.api, CONFIG.localData];
  let lastError;

  for (const source of sources) {
    try {
      const response = await fetch(source, { cache: source === CONFIG.api ? "default" : "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data.contributions)) throw new Error("Invalid contribution payload");
      return data;
    } catch (error) {
      lastError = error;
    }
  }

  throw lastError || new Error("Could not load contribution data");
}

function normaliseDays(days) {
  return [...days]
    .filter((day) => day && day.date)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-371)
    .map((day) => ({
      date: day.date,
      count: Number(day.count) || 0,
      level: Math.max(0, Math.min(4, Number(day.level) || 0)),
    }));
}

function getStats(days) {
  const total = days.reduce((sum, day) => sum + day.count, 0);
  const active = days.filter((day) => day.count > 0).length;
  let current = 0;
  let longest = 0;

  for (const day of days) {
    if (day.count > 0) {
      current += 1;
      longest = Math.max(longest, current);
    } else {
      current = 0;
    }
  }

  return { total, active, longest };
}

function getGridPosition(days) {
  if (!days.length) return [];
  const firstDate = new Date(`${days[0].date}T12:00:00`);
  const sundayOffset = firstDate.getDay();
  return days.map((day, index) => ({ ...day, gridIndex: index + sundayOffset }));
}

function renderMonths(days) {
  els.monthRow.innerHTML = "";
  const seen = new Set();
  const formatter = new Intl.DateTimeFormat("en", { month: "short" });

  days.forEach((day) => {
    const date = new Date(`${day.date}T12:00:00`);
    const key = `${date.getFullYear()}-${date.getMonth()}`;
    if (seen.has(key) || date.getDate() > 7) return;
    seen.add(key);
    const label = document.createElement("span");
    label.textContent = formatter.format(date);
    label.style.left = `calc(${Math.floor(day.gridIndex / 7)} * (var(--cell) + var(--gap)))`;
    els.monthRow.appendChild(label);
  });
}

function positionTooltip(event, day) {
  const countLabel = `${day.count} contribution${day.count === 1 ? "" : "s"}`;
  const prettyDate = new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" })
    .format(new Date(`${day.date}T12:00:00`));
  els.tooltip.innerHTML = `<b>${countLabel}</b><span>${prettyDate}</span>`;
  els.tooltip.style.left = `${event.clientX}px`;
  els.tooltip.style.top = `${event.clientY}px`;
  els.tooltip.classList.add("visible");
}

function renderHeatmap(days) {
  const positioned = getGridPosition(days);
  els.heatmap.innerHTML = "";
  const activeCandidates = positioned.filter((day) => day.level >= 3);
  const pulseDates = new Set(activeCandidates.slice(-5).map((day) => day.date));

  positioned.forEach((day) => {
    const cell = document.createElement("button");
    cell.className = `day${pulseDates.has(day.date) ? " pulse" : ""}`;
    cell.type = "button";
    cell.dataset.level = String(day.level);
    cell.dataset.date = day.date;
    cell.dataset.count = String(day.count);
    cell.setAttribute("role", "gridcell");
    cell.setAttribute("aria-label", `${day.date}: ${day.count} contributions`);
    cell.style.setProperty("--delay", `${Math.min(1550, Math.floor(day.gridIndex / 7) * 26 + (day.gridIndex % 7) * 13)}ms`);
    cell.style.setProperty("--pulse-delay", `${1.1 + (day.gridIndex % 5) * .37}s`);
    cell.addEventListener("pointerenter", (event) => positionTooltip(event, day));
    cell.addEventListener("pointermove", (event) => positionTooltip(event, day));
    cell.addEventListener("pointerleave", () => els.tooltip.classList.remove("visible"));
    cell.addEventListener("focus", (event) => {
      const rect = event.currentTarget.getBoundingClientRect();
      positionTooltip({ clientX: rect.left + rect.width / 2, clientY: rect.top }, day);
    });
    cell.addEventListener("blur", () => els.tooltip.classList.remove("visible"));
    els.heatmap.appendChild(cell);
  });

  renderMonths(positioned);
}

function animateNumber(element, target, suffix = "") {
  if (reduceMotion) {
    element.textContent = `${target.toLocaleString()}${suffix}`;
    return;
  }
  const duration = 900;
  const start = performance.now();
  const tick = (now) => {
    const progress = Math.min(1, (now - start) / duration);
    const eased = 1 - Math.pow(1 - progress, 3);
    element.textContent = `${Math.round(target * eased).toLocaleString()}${suffix}`;
    if (progress < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function animateComet() {
  if (reduceMotion) return;
  cometAnimation?.cancel();
  const activeCells = [...els.heatmap.querySelectorAll(".day")].filter((cell) => Number(cell.dataset.count) > 0);
  if (activeCells.length < 2) return;

  const picks = activeCells.filter((_, index) => index % Math.max(1, Math.floor(activeCells.length / 7)) === 0).slice(-8);
  const stageRect = els.comet.parentElement.getBoundingClientRect();
  const keyframes = picks.map((cell, index) => {
    const rect = cell.getBoundingClientRect();
    return {
      left: `${rect.left - stageRect.left + rect.width / 2}px`,
      top: `${rect.top - stageRect.top + rect.height / 2}px`,
      opacity: index === 0 || index === picks.length - 1 ? 0 : .95,
      offset: index / Math.max(1, picks.length - 1),
    };
  });

  cometAnimation = els.comet.animate(keyframes, {
    delay: 1550,
    duration: 2600,
    easing: "cubic-bezier(.42,0,.25,1)",
    fill: "both",
  });
}

function replay() {
  els.frame.classList.remove("playing");
  void els.frame.offsetWidth;
  els.frame.classList.add("playing");
  animateComet();
}

async function init() {
  try {
    const data = await loadContributions();
    contributionDays = normaliseDays(data.contributions);
    renderHeatmap(contributionDays);
    els.loading.classList.add("hidden");
    const stats = getStats(contributionDays);
    animateNumber(els.total, stats.total);
    animateNumber(els.active, stats.active);
    animateNumber(els.streak, stats.longest, "d");
    requestAnimationFrame(replay);
  } catch (error) {
    els.loading.innerHTML = `<strong>Could not load the timeline.</strong><span style="display:none"></span><small>Refresh to try again.</small>`;
    console.error(error);
  }
}

els.replay.addEventListener("click", replay);
window.addEventListener("resize", () => {
  els.tooltip.classList.remove("visible");
  cometAnimation?.cancel();
});

init();
