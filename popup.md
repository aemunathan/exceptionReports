Got it — you don’t need the whole file. Below are **only the sections that changed** (shown as **Before → After**), so you can manually update your original `popup.vm`.

---

## 1) Replace global `message-container` usage (3 places)

### A) Right after creating the modal (show “message” area)

**BEFORE**

```js
document.getElementById('message-container').style.display = "block";
```

**AFTER**

```js
var msgEl = document.getElementById(myModalId + '-message-container');
if (msgEl) { msgEl.style.display = "block"; }
```

---

### B) In AJAX `success` (hide “message” area)

**BEFORE**

```js
document.getElementById('message-container').style.display = "none";
```

**AFTER**

```js
var msgEl2 = document.getElementById(myModalId + '-message-container');
if (msgEl2) { msgEl2.style.display = "none"; }
```

---

### C) In AJAX `error` (hide “message” area)

**BEFORE**

```js
document.getElementById('message-container').style.display = "none";
```

**AFTER**

```js
var msgEl3 = document.getElementById(myModalId + '-message-container');
if (msgEl3) { msgEl3.style.display = "none"; }
```

---

## 2) Update modal HTML template (inside `createAndManageModal`)

### A) Outer modal `<div …>` attributes

**BEFORE**

```html
<div id="${modalId}" class="aui-dialog2 aui-dialog2-large my-custom-modal" role="dialog" aria-hidden="true">
```

**AFTER**

```html
<div id="${modalId}" class="aui-dialog2 aui-dialog2-large my-custom-modal" role="dialog" aria-hidden="true" data-aui-modal="true" data-aui-remove-on-hide="true" tabindex="-1">
```

### B) Header title formatting (optional, cosmetic but harmless)

**BEFORE**

```html
<h2 class="aui-dialog2-header-main">ScanR
Results</h2>
```

**AFTER**

```html
<h2 class="aui-dialog2-header-main">ScanR Results</h2>
```

### C) Message container div ID must be unique per modal (IMPORTANT)

**BEFORE**

```html
<div id="message-container" style="position: absolute;
bottom: 10px; left: 0; width: 100%;
text-align: left; color: #0052CC; display: none;
word-wrap: break-word; padding: 5px 0;
box-sizing: border-box;"></div>
```

**AFTER**  *(keep as 1–2 lines if you want; key is the **id**)*

```html
<div id="${modalId}-message-container" style="position: absolute; bottom: 10px; left: 0; width: 100%; text-align: left; color: #0052CC; display: none; word-wrap: break-word; padding: 5px 0; box-sizing: border-box;"></div>
```

---

## 3) Replace the close-handler block in `createAndManageModal` (IMPORTANT)

### A) Add “defensive cleanup” at top of `createAndManageModal`

Insert **right after**:

```js
console.log("[DEBUG] Creating modal with ID:", modalId);
```

Add:

```js
// Defensive cleanup: remove any existing instance of this modal + orphan blankets
if (typeof cleanupExistingModals === "function") {
    cleanupExistingModals();
}
AJS.$("#" + modalId).remove();
AJS.$(".aui-blanket").each(function() {
    var blanket = AJS.$(this);
    if (!blanket.siblings(".aui-dialog2:visible").length) {
        blanket.remove();
    }
});
```

---

### B) Replace the old click-to-close handler (this fixes the “blank white box” behavior)

**BEFORE** (your old block looked like this)

```js
dialog.show();
AJS.$("#" + modalId + "-close-button, #" + modalId + " .aui-dialog2-header-close").click(function() {
    console.log("[DEBUG] Closing modal:", modalId);
    dialog.hide();
    setTimeout(function() {
        AJS.$("#" + modalId).remove();
    }, 300);
});
return modalId;
```

**AFTER**

```js
dialog.show();

// Ensure cleanup happens no matter how the dialog is closed (ESC, header close, programmatic, etc.)
var cleanup = function() {
    console.log("[DEBUG] Cleaning up modal:", modalId);
    AJS.$("#" + modalId).off(".scanr");
    AJS.$("#" + modalId).remove();
    // Remove any orphaned blankets
    AJS.$(".aui-blanket").each(function() {
        var blanket = AJS.$(this);
        if (!blanket.siblings(".aui-dialog2:visible").length) {
            blanket.remove();
        }
    });
};

AJS.$("#" + modalId).on("aui-dialog2-hide.scanr hide.scanr", cleanup);

// Wire close buttons
AJS.$("#" + modalId + "-close-button, #" + modalId + " .aui-dialog2-header-close")
    .off("click.scanr")
    .on("click.scanr", function(e) {
        e.preventDefault();
        e.stopPropagation();
        console.log("[DEBUG] Closing modal:", modalId);
        dialog.hide();
        return false;
    });

// Prevent blanket click from closing the dialog (avoids "blank white box" / orphan modal state)
setTimeout(function() {
    var blanket = AJS.$(".aui-blanket").last();
    blanket.off("click.scanr").on("click.scanr", function(e) {
        e.preventDefault();
        e.stopPropagation();
        return false;
    });
    AJS.$("#" + modalId).focus();
}, 0);

return modalId;
```

---

## 4) In `handleApiResponse` (message container ID updated)

**BEFORE**

```js
document.getElementById('message-container').style.paddingLeft = "20px";
document.getElementById('message-container').style.display = "block";
```

**AFTER**

```js
var msgEl4 = document.getElementById(modalId + '-message-container');
if (msgEl4) {
    msgEl4.style.paddingLeft = "20px";
    msgEl4.style.display = "block";
}
```

---

### Quick tip (so Word doesn’t mislead you)

Even if Word “wraps” a long line, that’s not a real code newline. The only thing you must avoid is **actual hard line breaks inside an HTML attribute** (like `style="..."`). In the “AFTER” snippets above, I kept the critical ones **as single lines** so you can paste safely.

If you want, tell me which section in Word shows the “commented-looking” lines, and I’ll point to the exact spot (but you can already apply the changes above directly).
