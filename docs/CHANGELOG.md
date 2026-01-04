# Changelog

## 2026-01-04: Fix race condition causing multiple views to display

### What Changed
Fixed a race condition in `loadConversations()` that caused BOTH a list view (Chats/Projects) AND the welcome screen to display simultaneously.

### Why
When navigating to Chats or Projects, the async `loadConversations()` function would complete after the view was already shown, then unconditionally call `createNewConversation()` which displayed the welcome screen on top of the list view.

### Root Cause
The default else block in `loadConversations()` always called `createNewConversation()` without checking if a list view was already intentionally displayed.

### Fix
Added condition check before calling `createNewConversation()`:
```javascript
// Before:
} else {
    await createNewConversation();
}

// After:
} else if (!isChatsListViewActive && !isProjectsListViewActive && !isLibraryListViewActive) {
    await createNewConversation();
}
```

### Files Modified
- `web/templates/chat.html` (lines 4266-4268)

### Issues Encountered
- SSH deployment initially failed due to wrong username (`ubuntu` vs `ec2-user`)
- Server doesn't use git for deployment; used `scp` to copy file directly

### Current State
- Fix deployed to production
- Service restarted and running
- Awaiting user verification of the fix
