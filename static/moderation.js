// Admin review queue (FR-4).
// Uses api(), showMessage(), and escapeHTML() from app.js, and loadItems() from items.js.

const reviewList = document.getElementById("review-list");

// The approve / reject controls shown under each pending post.
function reviewForm(item) {
  return `
    <form onsubmit="submitReview(event, ${item.id})" class="mt-3 space-y-2">
      <textarea name="comments" rows="2" maxlength="1000"
                placeholder="Review comments (required when rejecting)"
                class="w-full text-sm rounded border-slate-300 border px-3 py-2"></textarea>
      <div class="flex gap-2">
        <button value="approve" class="text-sm bg-green-600 hover:bg-green-700 text-white rounded px-3 py-1">Approve</button>
        <button value="reject" class="text-sm bg-red-600 hover:bg-red-700 text-white rounded px-3 py-1">Reject</button>
      </div>
    </form>`;
}

async function sendReview(itemId, decision, comments) {
  await api("POST", `/items/${itemId}/reviews`, { decision, comments });
}

async function submitReview(event, itemId) {
  event.preventDefault();
  // event.submitter is the button that was clicked: Approve or Reject.
  const decision = event.submitter.value;
  const comments = event.target.elements.comments.value;
  try {
    await sendReview(itemId, decision, comments);
    showMessage(decision === "approve" ? "Post approved and published." : "Post rejected.");
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
}

// Admins can remove an already-approved post from the feed by rejecting it.
async function takeDownItem(itemId) {
  const comments = prompt("Why is this post being taken down? The student will see this.");
  if (comments === null) return; // cancelled
  try {
    await sendReview(itemId, "reject", comments);
    showMessage("Post taken down.");
    loadItems();
  } catch (err) {
    showMessage(err.message, true);
  }
}
