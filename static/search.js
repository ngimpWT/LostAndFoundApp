// Search and filtering for the campus feed (FR-5).
// Uses api(), showMessage(), and escapeHTML() from app.js, and itemsList /
// renderList() from items.js.

const searchForm = document.getElementById("search-form");
const locationSelect = searchForm.elements.location;
const resultCount = document.getElementById("result-count");

// Build the /items/search URL from whatever is filled in on the form.
function searchUrl() {
  const params = new URLSearchParams();
  const { q, item_type, location, include_resolved } = searchForm.elements;
  if (q.value.trim()) params.set("q", q.value.trim());
  if (item_type.value) params.set("item_type", item_type.value);
  if (location.value) params.set("location", location.value);
  if (include_resolved.checked) params.set("include_resolved", "true");
  return `/items/search?${params}`;
}

function hasFilters() {
  return searchUrl() !== "/items/search?";
}

// Each search gets a number. If the user types fast, an older, slower
// response may arrive after a newer one; we ignore anything but the latest.
let latestSearch = 0;

async function loadFeed() {
  const searchNumber = ++latestSearch;
  try {
    const items = await api("GET", searchUrl());
    if (searchNumber !== latestSearch) return; // a newer search has started

    resultCount.textContent = `${items.length} ${items.length === 1 ? "post" : "posts"}`;
    const emptyText = hasFilters() ? "No posts match your search." : "No approved posts yet.";
    renderList(itemsList, items, { feed: true }, emptyText);
  } catch (err) {
    showMessage(err.message, true);
  }
}

// Fill the location dropdown with locations that actually have posts.
async function loadLocations() {
  try {
    const locations = await api("GET", "/items/locations");
    const selected = locationSelect.value;
    locationSelect.innerHTML = `<option value="">All locations</option>` +
      locations.map((loc) => `<option>${escapeHTML(loc)}</option>`).join("");
    locationSelect.value = locations.includes(selected) ? selected : "";
  } catch (err) {
    showMessage(err.message, true);
  }
}

// Wait until the user pauses typing for a moment before searching.
let typingTimer;
searchForm.elements.q.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(loadFeed, 250);
});

// Dropdowns and the checkbox search right away.
searchForm.addEventListener("change", (event) => {
  if (event.target.name !== "q") loadFeed();
});

// Pressing Enter in the keyword box shouldn't reload the page.
searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadFeed();
});

document.getElementById("clear-search-btn").addEventListener("click", () => {
  searchForm.reset();
  loadFeed();
});
