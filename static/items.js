// Item posts: report, edit, and mark resolved (FR-2).
// Uses api(), getCurrentUser(), showMessage(), and escapeHTML() from app.js,
// photoGallery() and loadPhotoImages() from photos.js, reviewList, reviewForm(),
// and takeDownItem() from moderation.js, and loadFeed() / loadLocations() from search.js.

const itemForm = document.getElementById("item-form");
const itemsList = document.getElementById("items-list");
const myItemsList = document.getElementById("my-items-list");

// Show or hide the item sections depending on who is logged in.
function renderItemsSection(user) {
  const isStudent = user && user.role === "student";
  const isAdmin = user && user.role === "admin";
  document.getElementById("item-form-section").classList.toggle("hidden", !isStudent);
  document.getElementById("my-items-section").classList.toggle("hidden", !isStudent);
  document.getElementById("review-section").classList.toggle("hidden", !isAdmin);
  document.getElementById("items-section").classList.toggle("hidden", !user);
  document.getElementById("search-form").classList.toggle("hidden", !user);
  if (user) {
    loadItems();
  } else {
    resetItemForm();
    document.getElementById("search-form").reset();
  }
}

// Reload every list the current user can see.
async function loadItems() {
  const user = getCurrentUser();
  try {
    await Promise.all([loadFeed(), loadLocations()]);

    if (user.role === "student") {
      const mine = await api("GET", "/items/mine");
      await addRejectionReasons(mine);
      renderList(myItemsList, mine, { manage: true }, "You haven't posted anything yet.");
    }
    if (user.role === "admin") {
      const pending = await api("GET", "/moderation/pending");
      renderList(reviewList, pending, { moderate: true }, "Nothing waiting for review. 🎉");
    }
  } catch (err) {
    showMessage(err.message, true);
  }
}

// For rejected posts, look up the admin's latest comments so the owner knows why.
async function addRejectionReasons(items) {
  for (const item of items.filter((i) => i.status === "rejected")) {
    const reviews = await api("GET", `/items/${item.id}/reviews`);
    item.rejection_reason = reviews.at(-1)?.comments;
  }
}

function renderList(container, items, options, emptyText) {
  if (items.length === 0) {
    container.innerHTML = `<p class="text-slate-500">${emptyText}</p>`;
    return;
  }
  container.innerHTML = items.map((item) => itemCard(item, options)).join("");
  loadPhotoImages(container);
}

const STATUS_BADGES = {
  pending: `<span class="bg-amber-100 text-amber-800 text-xs font-semibold uppercase rounded px-2 py-1">Awaiting review</span>`,
  approved: `<span class="bg-sky-100 text-sky-800 text-xs font-semibold uppercase rounded px-2 py-1">Approved</span>`,
  rejected: `<span class="bg-red-600 text-white text-xs font-semibold uppercase rounded px-2 py-1">Rejected</span>`,
};

// options.feed:     a post in the public feed
// options.manage:   one of the student's own posts (edit / resolve / photos)
// options.moderate: a post in the admin review queue
function itemCard(item, options) {
  const user = getCurrentUser();
  const typeBadge = item.item_type === "lost"
    ? `<span class="bg-red-100 text-red-800 text-xs font-semibold uppercase rounded px-2 py-1">Lost</span>`
    : `<span class="bg-green-100 text-green-800 text-xs font-semibold uppercase rounded px-2 py-1">Found</span>`;
  const resolvedBadge = item.is_resolved
    ? `<span class="bg-slate-200 text-slate-700 text-xs font-semibold uppercase rounded px-2 py-1">Resolved</span>`
    : "";
  const statusBadge = options.manage ? STATUS_BADGES[item.status] : "";

  const rejection = item.rejection_reason
    ? `<p class="text-sm text-red-700 bg-red-50 rounded px-3 py-2 mt-2">
         <strong>Admin feedback:</strong> ${escapeHTML(item.rejection_reason)}
         <br><span class="text-xs">Edit your post to send it back for review.</span>
       </p>`
    : "";

  let actions = "";
  if (options.manage) {
    actions = `
      <div class="flex gap-2 mt-3">
        <button onclick="startEdit(${item.id})" class="text-sm bg-slate-200 hover:bg-slate-300 rounded px-3 py-1">Edit</button>
        ${item.is_resolved ? "" : `<button onclick="resolveItem(${item.id})" class="text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded px-3 py-1">Mark resolved</button>`}
      </div>`;
  } else if (options.moderate) {
    actions = reviewForm(item);
  } else if (options.feed && user.role === "admin") {
    actions = `
      <div class="mt-3">
        <button onclick="takeDownItem(${item.id})" class="text-sm bg-red-100 hover:bg-red-200 text-red-800 rounded px-3 py-1">Take down</button>
      </div>`;
  }

  return `
    <article class="bg-white rounded-lg shadow p-4 ${item.is_resolved ? "opacity-60" : ""}">
      <div class="flex flex-wrap items-center gap-2 mb-1">
        ${typeBadge} ${statusBadge} ${resolvedBadge}
        <h3 class="font-semibold">${escapeHTML(item.title)}</h3>
      </div>
      <p class="text-sm text-slate-600 whitespace-pre-line">${escapeHTML(item.description)}</p>
      <p class="text-xs text-slate-500 mt-2">
        📍 ${escapeHTML(item.location)} · Posted by ${escapeHTML(item.owner_name)}
        on ${new Date(item.created_at + "Z").toLocaleDateString()}
      </p>
      ${rejection}
      ${photoGallery(item, options.manage)}
      ${actions}
    </article>`;
}

// ---------- Create / edit ----------

function resetItemForm() {
  itemForm.reset();
  itemForm.elements.id.value = "";
  document.getElementById("item-form-title").textContent = "Report an item";
  document.getElementById("item-submit-btn").textContent = "Post item";
  document.getElementById("item-cancel-btn").classList.add("hidden");
}

// Fill the form with an existing item so the owner can edit it.
async function startEdit(itemId) {
  try {
    const item = await api("GET", `/items/${itemId}`);
    itemForm.elements.id.value = item.id;
    itemForm.elements.title.value = item.title;
    itemForm.elements.description.value = item.description;
    itemForm.elements.location.value = item.location;
    itemForm.elements.item_type.value = item.item_type;
    document.getElementById("item-form-title").textContent = "Edit item";
    document.getElementById("item-submit-btn").textContent = "Save changes";
    document.getElementById("item-cancel-btn").classList.remove("hidden");
    document.getElementById("item-form-section").scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showMessage(err.message, true);
  }
}

itemForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const { id, ...data } = Object.fromEntries(new FormData(itemForm));
  try {
    if (id) {
      await api("PUT", `/items/${id}`, data);
      showMessage("Item updated. It will reappear in the feed once an admin re-approves it.");
    } else {
      await api("POST", "/items", data);
      showMessage("Item submitted! It will appear in the feed once an admin approves it.");
    }
    resetItemForm();
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
});

document.getElementById("item-cancel-btn").addEventListener("click", resetItemForm);

// ---------- Resolve ----------

async function resolveItem(itemId) {
  if (!confirm("Mark this item as resolved?")) return;
  try {
    await api("PUT", `/items/${itemId}/resolve`);
    showMessage("Item marked as resolved.");
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
}

// Check any saved login with the server, then draw the page.
verifySession().then(render);
