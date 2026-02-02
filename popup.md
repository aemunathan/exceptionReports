Yes — **this function needs a small change**, but you do **not** need to rewrite the whole thing.

### Why a change is needed

Your current `initButtonClickHandler()` uses:

* `AJS.$("#show-popup").click(...)` and a `.data('events-attached')` flag.

In Jira issue view (SPA-ish), the button can be re-rendered and the element replaced, so the `.data()` flag can be lost and **duplicate handlers** can be attached (your logs show repeated init). Duplicate handlers = multiple modals/blankets = greyed screen.

So I recommend switching to a **namespaced off/on delegated binding**. It’s the most reliable way in Jira.

---

# ✅ What to remove (only this portion)

Inside `initButtonClickHandler()`, remove everything from:

```js
if (AJS.$("#show-popup").length && !AJS.$("#show-popup").data('events-attached')) {
    console.log("[DEBUG] Attaching click event to show-popup button");

    AJS.$("#show-popup").click(function(e) {
        ...
    });

    AJS.$("#show-popup").data('events-attached', true);
}
```

(That whole `if (...) { ... }` block.)

Keep the function wrapper and your debug line.

---

# ✅ Replace it with this (drop-in)

```js
function initButtonClickHandler() {
    console.log("[DEBUG] Initializing button click handler");

    // Reliable in Jira (handles re-render): remove previous handler, then bind again
    AJS.$(document)
        .off('click.scanr', '#show-popup')
        .on('click.scanr', '#show-popup', function (e) {
            console.log("[DEBUG] Show popup button clicked");
            e.preventDefault();
            e.stopPropagation();

            getAttestationProperty(function (attestation) {
                attestationChecked = true;

                if (isAttestationValid(attestation)) {
                    console.log("[DEBUG] Valid attestation found, proceeding with scan");
                    attestationAccepted = true;
                    proceedWithScan();
                } else {
                    console.log("[DEBUG] No valid attestation, showing modal");
                    showAttestationModal(
                        proceedWithScan,
                        function () { console.log("[DEBUG] Attestation cancelled by user"); }
                    );
                }
            });

            return false;
        });
}
```

---

## Do you still need the earlier suggestions for this function?

**Yes — this is the only part you need from earlier suggestions for this function.**
Everything else (hide-event sequencing, removing manual modal CSS forcing) stays in the modal functions, not here.

---

## Quick validation (after replacing)

* Reload issue page → click Scan → you should see **only one** “Show popup button clicked” log per click.
* If you still see multiple logs per click, then the init is being invoked multiple times and you’ll need the “init once” guard too (but try this first).

If you want, share the line where `initButtonClickHandler()` is called (e.g., in `initStuff()`), and I’ll tell you whether you should add the one-time guard there.
