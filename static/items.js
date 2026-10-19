// Item posts: report, edit, and mark resolved (FR-2).
// Uses api(), getCurrentUser(), showMessage(), and escapeHTML() from app.js.

const itemForm = document.getElementById("item-form");
const itemsList = document.getElementById("items-list");

// Show or hide the item sections depending on who is logged in.
function renderItemsSection(user) {
  const isStudent = user && user.role === "student";
  document.getElementById("item-form-section").classList.toggle("hidden", !isStudent);
  document.getElementById("items-section").classList.toggle("hidden", !user);
  if (user) loadItems();
  else resetItemForm();
}

async function loadItems() {
  try {
    const items = await api("GET", "/items");
    renderItems(items);
  } catch (err) {
    showMessage(err.message, true);
  }
}

function renderItems(items) {
  if (items.length === 0) {
    itemsList.innerHTML = `<p class="text-slate-500">No items have been posted yet.</p>`;
    return;
  }

  const user = getCurrentUser();
  itemsList.innerHTML = items.map((item) => itemCard(item, user)).join("");
}

function itemCard(item, user) {
  const typeBadge = item.item_type === "lost"
    ? `<span class="bg-red-100 text-red-800 text-xs font-semibold uppercase rounded px-2 py-1">Lost</span>`
    : `<span class="bg-green-100 text-green-800 text-xs font-semibold uppercase rounded px-2 py-1">Found</span>`;
  const resolvedBadge = item.is_resolved
    ? `<span class="bg-slate-200 text-slate-700 text-xs font-semibold uppercase rounded px-2 py-1">Resolved</span>`
    : "";

  // Only the owner sees the Edit / Mark resolved buttons.
  let actions = "";
  if (user && item.owner_id === user.id) {
    actions = `
      <div class="flex gap-2 mt-3">
        <button onclick="startEdit(${item.id})" class="text-sm bg-slate-200 hover:bg-slate-300 rounded px-3 py-1">Edit</button>
        ${item.is_resolved ? "" : `<button onclick="resolveItem(${item.id})" class="text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded px-3 py-1">Mark resolved</button>`}
      </div>`;
  }

  return `
    <article class="bg-white rounded-lg shadow p-4 ${item.is_resolved ? "opacity-60" : ""}">
      <div class="flex items-center gap-2 mb-1">
        ${typeBadge} ${resolvedBadge}
        <h3 class="font-semibold">${escapeHTML(item.title)}</h3>
      </div>
      <p class="text-sm text-slate-600 whitespace-pre-line">${escapeHTML(item.description)}</p>
      <p class="text-xs text-slate-500 mt-2">
        📍 ${escapeHTML(item.location)} · Posted by ${escapeHTML(item.owner_name)}
        on ${new Date(item.created_at + "Z").toLocaleDateString()}
      </p>
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
    itemForm.scrollIntoView({ behavior: "smooth" });
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
      showMessage("Item updated.");
    } else {
      await api("POST", "/items", data);
      showMessage("Item posted.");
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

render();
