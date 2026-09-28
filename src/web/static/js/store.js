// Browser «cabinet» in localStorage (no server): auth flag, history, favorites, my ratings, feedback.

const PREFIX = "svoe_vino:v1:";
const HISTORY_LIMIT = 50;
const RECENT_LIMIT = 5;

const STATUS_LABELS = {
  high: "Высокая уверенность",
  medium: "Средняя уверенность",
  low: "Низкая уверенность",
  not_found: "Не найдено",
};

const isObject = (v) => v !== null && typeof v === "object" && !Array.isArray(v);

// key -> [fallback factory, shape validator]; corrupt or wrongly shaped values reset the key.
const SCHEMA = {
  auth: [() => ({ logged_in: false }), (v) => isObject(v) && typeof v.logged_in === "boolean"],
  history: [() => [], (v) => Array.isArray(v) && v.every((item) => isObject(item) && typeof item.search_id === "string")],
  favorites: [() => [], (v) => Array.isArray(v) && v.every((s) => typeof s === "string")],
  ratings: [() => ({}), (v) => isObject(v) && Object.values(v).every((n) => Number.isInteger(n) && n >= 1 && n <= 5)],
  feedback: [() => ({}), (v) => isObject(v) && Object.values(v).every((s) => s === "match" || s === "mismatch")],
  // Auxiliary slug -> title cache so /me can show names for favorites and ratings.
  titles: [() => ({}), (v) => isObject(v) && Object.values(v).every((s) => typeof s === "string")],
};

function storage() {
  try {
    return window.localStorage;
  } catch (error) {
    console.warn("localStorage unavailable", error);
    return null;
  }
}

function read(key) {
  const [fallback, valid] = SCHEMA[key];
  const ls = storage();
  if (!ls) {
    return fallback();
  }
  let raw = null;
  try {
    raw = ls.getItem(PREFIX + key);
    if (raw === null) {
      return fallback();
    }
    const value = JSON.parse(raw);
    if (valid(value)) {
      return value;
    }
  } catch (error) {
    console.warn(`corrupt cabinet key ${key}, resetting`, error);
  }
  try {
    ls.removeItem(PREFIX + key);
  } catch (error) {
    console.warn("cannot reset key", error);
  }
  return fallback();
}

function write(key, value) {
  const ls = storage();
  if (!ls) {
    return false;
  }
  try {
    ls.setItem(PREFIX + key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error(`cannot save ${key}`, error);
    return false;
  }
}

export function isLoggedIn() {
  return read("auth").logged_in;
}

export function setLoggedIn(value) {
  write("auth", { logged_in: Boolean(value) });
}

function rememberTitle(slug, title) {
  if (!slug || !title) {
    return;
  }
  const titles = read("titles");
  titles[slug] = title;
  write("titles", titles);
}

export function recordHistory(entry) {
  const history = read("history").filter((item) => item.search_id !== entry.search_id);
  history.unshift(entry);
  write("history", history.slice(0, HISTORY_LIMIT));
  rememberTitle(entry.slug, entry.title);
}

export function recordFeedback(searchId, verdict) {
  const feedback = read("feedback");
  feedback[searchId] = verdict;
  write("feedback", feedback);
}

export function toggleFavorite(slug, title) {
  const favorites = read("favorites");
  const index = favorites.indexOf(slug);
  if (index >= 0) {
    favorites.splice(index, 1);
  } else {
    favorites.unshift(slug);
    rememberTitle(slug, title);
  }
  write("favorites", favorites);
  return index < 0;
}

export function setRating(slug, value, title) {
  const ratings = read("ratings");
  ratings[slug] = value;
  write("ratings", ratings);
  rememberTitle(slug, title);
}

export function clearAll() {
  const ls = storage();
  if (!ls) {
    return;
  }
  Object.keys(SCHEMA)
    .filter((key) => key !== "auth")
    .forEach((key) => {
      try {
        ls.removeItem(PREFIX + key);
      } catch (error) {
        console.error(`cannot clear ${key}`, error);
      }
    });
}

// ---------- DOM ----------

function formatDate(ts) {
  const date = new Date(ts);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toLocaleString("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}

function historyLabel(item) {
  if (item.status === "not_found") {
    return STATUS_LABELS.not_found;
  }
  return STATUS_LABELS[item.level] || "";
}

function listItem(href, text, meta, extra) {
  const li = document.createElement("li");
  li.className = "me-list__item";
  const link = document.createElement("a");
  link.className = "me-list__link";
  link.href = href;
  link.textContent = text;
  const side = document.createElement("span");
  side.className = "me-list__meta";
  side.textContent = meta;
  li.append(link, side);
  if (extra) {
    li.append(extra);
  }
  return li;
}

function wineHref(slug) {
  return `/wine/${encodeURIComponent(slug)}`;
}

function resultHref(searchId) {
  return /^[0-9a-f]{32}$/.test(searchId) ? `/result/${searchId}` : "/";
}

function applyLoginVisibility() {
  const logged = isLoggedIn();
  document.querySelectorAll("[data-requires-login]").forEach((el) => {
    el.hidden = !logged;
  });
  document.querySelectorAll("[data-requires-logout]").forEach((el) => {
    el.hidden = logged;
  });
  document.querySelectorAll("[data-auth-toggle]").forEach((button) => {
    button.hidden = false;
    button.textContent = logged ? "Выйти" : "Войти";
  });
}

function initAuthToggle() {
  document.querySelectorAll("[data-auth-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      if (isLoggedIn()) {
        setLoggedIn(false);
        refresh();
      } else {
        setLoggedIn(true);
        if (window.location.pathname === "/me") {
          refresh();
        } else {
          window.location.assign("/me");
        }
      }
    });
  });
}

function initResultMeta() {
  const meta = document.querySelector("[data-search-meta]");
  if (!meta) {
    return;
  }
  const d = meta.dataset;
  if (!/^[0-9a-f]{32}$/.test(d.searchId || "")) {
    return;
  }
  const existing = read("history").find((item) => item.search_id === d.searchId);
  recordHistory({
    ts: existing ? existing.ts : Date.now(),
    search_id: d.searchId,
    slug: d.slug || null,
    title: d.title || null,
    status: d.status,
    level: d.level,
  });
  if (d.feedbackVerdict === "match" || d.feedbackVerdict === "mismatch") {
    recordFeedback(d.searchId, d.feedbackVerdict);
  }
}

function syncFavoriteButton(button) {
  const active = read("favorites").includes(button.dataset.favSlug);
  button.setAttribute("aria-pressed", String(active));
  const label = button.querySelector("[data-fav-label]");
  if (label) {
    label.textContent = active ? "В избранном" : "В избранное";
  }
}

function syncRatingWidget(widget) {
  const value = read("ratings")[widget.dataset.myRating] || 0;
  widget.querySelectorAll("[data-value]").forEach((button) => {
    const on = Number(button.dataset.value) <= value;
    button.setAttribute("aria-pressed", String(Number(button.dataset.value) === value));
    const img = button.querySelector("img");
    if (img) {
      img.src = on ? img.dataset.srcFull : img.dataset.srcEmpty;
    }
  });
}

function initWineWidgets() {
  document.querySelectorAll("[data-fav-slug]").forEach((button) => {
    syncFavoriteButton(button);
    button.addEventListener("click", () => {
      toggleFavorite(button.dataset.favSlug, button.dataset.favTitle);
      syncFavoriteButton(button);
    });
  });
  document.querySelectorAll("[data-my-rating]").forEach((widget) => {
    syncRatingWidget(widget);
    widget.querySelectorAll("[data-value]").forEach((button) => {
      button.addEventListener("click", () => {
        setRating(widget.dataset.myRating, Number(button.dataset.value), widget.dataset.title);
        syncRatingWidget(widget);
      });
    });
  });
}

function renderRecent() {
  const box = document.querySelector("[data-recent]");
  const list = document.querySelector("[data-recent-list]");
  if (!box || !list) {
    return;
  }
  const items = read("history").slice(0, RECENT_LIMIT);
  list.replaceChildren(
    ...items.map((item) =>
      listItem(resultHref(item.search_id), item.title || "Вино не найдено", historyLabel(item)),
    ),
  );
  box.hidden = !isLoggedIn() || items.length === 0;
}

function renderList(name, items) {
  const list = document.querySelector(`[data-list="${name}"]`);
  const empty = document.querySelector(`[data-empty="${name}"]`);
  if (!list) {
    return;
  }
  list.replaceChildren(...items);
  if (empty) {
    empty.hidden = items.length > 0;
  }
}

function removeFavoriteButton(slug) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn--ghost btn--small";
  button.textContent = "Убрать";
  button.addEventListener("click", () => {
    toggleFavorite(slug);
    renderCabinet();
  });
  return button;
}

function renderCabinet() {
  const titles = read("titles");
  renderList(
    "history",
    read("history").map((item) =>
      listItem(
        resultHref(item.search_id),
        item.title || "Вино не найдено",
        [formatDate(item.ts), historyLabel(item)].filter(Boolean).join(" · "),
      ),
    ),
  );
  renderList(
    "favorites",
    read("favorites").map((slug) =>
      listItem(wineHref(slug), titles[slug] || slug, "", removeFavoriteButton(slug)),
    ),
  );
  renderList(
    "ratings",
    Object.entries(read("ratings")).map(([slug, value]) =>
      listItem(wineHref(slug), titles[slug] || slug, `${value} из 5`),
    ),
  );
}

function selectTab(name) {
  document.querySelectorAll("[data-tab]").forEach((tab) => {
    const active = tab.dataset.tab === name;
    tab.setAttribute("aria-selected", String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== name;
  });
}

function initMePage() {
  const guest = document.querySelector("[data-me-guest]");
  const cabinet = document.querySelector("[data-me-cabinet]");
  if (!guest || !cabinet) {
    return;
  }
  const tabs = [...document.querySelectorAll("[data-tab]")];
  tabs.forEach((tab, index) => {
    tab.addEventListener("click", () => selectTab(tab.dataset.tab));
    tab.addEventListener("keydown", (event) => {
      const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
      if (delta) {
        const next = tabs[(index + delta + tabs.length) % tabs.length];
        selectTab(next.dataset.tab);
        next.focus();
      }
    });
  });
  document.querySelector("[data-login]").addEventListener("click", () => {
    setLoggedIn(true);
    refresh();
  });
  document.querySelector("[data-logout]").addEventListener("click", () => {
    setLoggedIn(false);
    refresh();
  });
  document.querySelector("[data-clear]").addEventListener("click", () => {
    if (window.confirm("Удалить историю, избранное и оценки из этого браузера?")) {
      clearAll();
      refresh();
    }
  });
}

function renderMePage() {
  const guest = document.querySelector("[data-me-guest]");
  const cabinet = document.querySelector("[data-me-cabinet]");
  if (!guest || !cabinet) {
    return;
  }
  const logged = isLoggedIn();
  guest.hidden = logged;
  cabinet.hidden = !logged;
  if (logged) {
    renderCabinet();
  }
}

function refresh() {
  applyLoginVisibility();
  document.querySelectorAll("[data-fav-slug]").forEach(syncFavoriteButton);
  document.querySelectorAll("[data-my-rating]").forEach(syncRatingWidget);
  renderRecent();
  renderMePage();
}

initResultMeta();
initAuthToggle();
initWineWidgets();
initMePage();
refresh();
