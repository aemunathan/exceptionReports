Perfect — these two screenshots show **exactly** where the flow breaks.

### What’s wrong in your current implementation (from your screenshots)

#### 1) You run the scan **while the policy modal is still “in the middle of closing”**

In your accept handler you do:

```js
dialog.hide();
attestationAccepted = true;
if (onAccept) onAccept();
```

So the **Scan Results modal opens while the policy modal blanket is still active** → results modal appears greyed / behind / unclickable.

#### 2) In `showAttestationModal()` you are manually fighting AUI:

You are doing things like:

* `existingModal.removeAttr('data-aui-focus')`
* `existingModal.removeAttr('data-aui-blanketed')`
* forcing CSS `z-index: 3000`, `display:block`, `pointer-events:auto`
* forcing `aria-hidden=false`

Those override AUI dialog2’s internal state machine and are a common reason for **stuck blankets** and **broken close behavior**.

✅ The fix is to **let AUI manage the dialog lifecycle**, and only “continue scan” after the dialog fully hides.

---

# Fix #1 — Change ONLY the accept button handler (most important)

In `bindAttestationModal(onAccept, onCancel)` replace your success block with this:

```js
if (success) {
    console.log("[DEBUG] Attestation saved successfully, hiding modal");

    var $dlgEl = jQuery('#ai-attestation-modal');
    var dialog = AJS.dialog2('#ai-attestation-modal');

    // Continue ONLY after the modal is fully hidden (blanket removed)
    $dlgEl.one('aui-dialog2-hide.scanr', function () {
        console.log("[DEBUG] Attestation modal fully hidden, proceeding");
        attestationAccepted = true;
        if (onAccept) onAccept();
    });

    dialog.hide();
} else {
    alert('Failed to save attestation. Please try again.');
}
```

**Why this works:** the scan won’t start until AUI has removed the blanket and finished closing.

---

# Fix #2 — Remove the “manual state forcing” from `showAttestationModal()`

In your `showAttestationModal(onAccept, onCancel)` **delete this entire “Force proper modal state” block**:

```js
// Force proper modal state
setTimeout(function() {
  existingModal.attr('aria-hidden','false');
  existingModal.css({
    'z-index':'3000',
    'display':'block',
    'pointer-events':'auto'
  });
  existingModal.focus();
}, 100);
```

Also remove these lines (don’t touch AUI internal attributes):

```js
existingModal.attr('aria-hidden', 'false');
existingModal.removeAttr('data-aui-focus');
existingModal.removeAttr('data-aui-blanketed');
```

✅ Keep it simple:

```js
function showAttestationModal(onAccept, onCancel) {
    console.log("[DEBUG] Showing attestation modal");

    var $modal = jQuery('#ai-attestation-modal');
    if ($modal.length === 0) {
        console.error("[DEBUG] Attestation modal template not found");
        alert('Attestation modal not available. Please contact the administrator.');
        if (onCancel) onCancel();
        return;
    }

    // Bind events before showing
    bindAttestationModal(onAccept, onCancel);

    // Show using AUI only
    AJS.dialog2('#ai-attestation-modal').show();
}
```

---

# Fix #3 — Make your event unbinding safe (use namespace)

Right now you do `.off('click')` which can remove other handlers accidentally and still allow duplicates in some Jira re-render situations.

Change your bindings like this:

```js
jQuery('#ai-attestation-accept').off('click.scanr').on('click.scanr', function(e) { ... });
jQuery('#ai-attestation-cancel').off('click.scanr').on('click.scanr', function(e) { ... });
jQuery('#ai-attestation-checkbox').off('change.scanr').on('change.scanr', function() { ... });
```

This prevents duplicates **without breaking other code**.

---

# Why you are seeing “greyed out results + no close”

Because:

* the policy modal is still holding the blanket when your results modal opens (race condition), **and**
* manual z-index / aria / data-aui-* changes can confuse AUI so it doesn’t restore interaction correctly.

After the 3 fixes above, the flow becomes:

✅ Click Scan
✅ If not accepted → show attestation modal
✅ Click Accept → save → **wait for hide event** → then start scan
✅ Results modal opens normally, clickable, close works, no stuck grey overlay.

---

If you apply only ONE change first, do **Fix #1 (hide event before onAccept)** — that alone typically resolves the “second screen hidden/greyed” issue.
