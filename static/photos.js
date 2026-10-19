// Photo attachments with captions (FR-3).
// Uses api(), showMessage(), and escapeHTML() from app.js, and loadItems() from items.js.

// HTML for an item's photos, plus an upload form if the viewer owns the post.
function photoGallery(item, isOwner) {
  const photos = item.photos.map((photo) => `
    <figure class="relative w-32">
      <a href="${photo.url}" target="_blank">
        <img src="${photo.url}" alt="${escapeHTML(photo.caption)}"
             class="w-32 h-32 object-cover rounded border">
      </a>
      <figcaption class="text-xs text-slate-600 mt-1">${escapeHTML(photo.caption)}</figcaption>
      ${isOwner ? `
        <button onclick="deletePhoto(${photo.id})" title="Delete photo"
                class="absolute top-1 right-1 bg-white/90 hover:bg-red-100 text-red-700 rounded-full w-6 h-6 text-sm leading-6">&times;</button>` : ""}
    </figure>`).join("");

  const uploadForm = isOwner ? `
    <form onsubmit="uploadPhoto(event, ${item.id})" class="flex flex-wrap items-center gap-2 mt-3 text-sm">
      <input type="file" name="file" accept="image/jpeg,image/png,image/gif,image/webp" required class="text-sm">
      <input name="caption" required maxlength="200" placeholder="Caption, e.g. Front view"
             class="flex-1 min-w-40 rounded border-slate-300 border px-2 py-1">
      <button class="bg-slate-200 hover:bg-slate-300 rounded px-3 py-1">Add photo</button>
    </form>` : "";

  if (!photos && !uploadForm) return "";
  return `
    <div class="mt-3">
      ${photos ? `<div class="flex flex-wrap gap-3">${photos}</div>` : ""}
      ${uploadForm}
    </div>`;
}

async function uploadPhoto(event, itemId) {
  event.preventDefault();
  const form = event.target;
  try {
    await api("POST", `/items/${itemId}/photos`, new FormData(form));
    showMessage("Photo added.");
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
}

async function deletePhoto(photoId) {
  if (!confirm("Delete this photo?")) return;
  try {
    await api("DELETE", `/photos/${photoId}`);
    showMessage("Photo deleted.");
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
}
