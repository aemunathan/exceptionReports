You’re right to suspect the implementation flow (not just “CSS/z-index”). From your **current code in the Word file**, the main problem is:

**You call `proceedWithScan()` immediately after `dialog.hide()` for the policy modal**, while Jira/AUI is still in the process of hiding it and removing its blanket. That leaves the **policy backdrop/blanket active**, and your **Scan Results dialog opens “behind” it**, so everything looks greyed out and unclickable.

This happens here: you hide the attestation dialog and immediately call `onAccept()` (which triggers `proceedWithScan`). 

Below is an alternative approach that fixes the root cause without hacks.

---

## 1) Fix the flow: **wait until the policy modal is fully closed** before scan

### Change ONLY the **success** part inside the accept button handler

**CURRENT (problem)**
`dialog.hide(); ... if (onAccept) onAccept();` happens back-to-back. 

**REPLACE with this (recommended):**

```js
if (success) {
    console.log("[DEBUG] Attestation saved successfully, hiding modal");

    var $dlgEl = jQuery('#ai-attestation-modal');
    var dialog = AJS.dialog2('#ai-attestation-modal');

    // IMPORTANT: run scan only after the modal is actually hidden
    $dlgEl.one('aui-dialog2-hide.scanr', function () {
        console.log("[DEBUG] Attestation modal fully hidden");
        attestationAccepted = true;
        if (onAccept) onAccept();   // proceedWithScan() runs here
    });

    dialog.hide();
} else {
    alert('Failed to save attestation. Please try again.');
}
```

✅ This ensures the **blanket is gone** and the policy screen is no longer on top before opening your results modal.

---

## 2) Fix repeated init/click bindings (your logs show init running many times)

Right now you attach the click handler using a `.data('events-attached')` flag. 
This can fail in Jira because the issue view / web panel can re-render and recreate the button DOM.

### Replace the button click binding with a **namespaced off/on** (more reliable)

Inside `initButtonClickHandler()` replace the click binding block with:

```js
AJS.$(document).off('click.scanr', '#show-popup').on('click.scanr', '#show-popup', function(e) {
    console.log("[DEBUG] Show popup button clicked");
    e.preventDefault();

    getAttestationProperty(function(attestation) {
        attestationChecked = true;

        if (isAttestationValid(attestation)) {
            console.log("[DEBUG] Valid attestation found, proceeding with scan");
            attestationAccepted = true;
            proceedWithScan();
        } else {
            console.log("[DEBUG] No valid attestation, showing modal");
            showAttestationModal(proceedWithScan, function() {
                console.log("[DEBUG] Attestation cancelled by user");
            });
        }
    });

    return false;
});
```

✅ This prevents multiple handlers even if Jira redraws the panel.

---


