# Changelog

## 2026-01-04: Complete fix for project context and sidebar layout shift

### Bug 1: Project context lost (complete fix)

**What Changed**
When clicking "New chat" from a project page, the welcome screen now shows the project badge with name and color.

**Root Cause**
Previous fix only set `currentProjectId` but not `currentProject` (full object with name, color). The welcome screen badge requires the full project object.

**Fix**
- `chat.html:3920-3932` - Fetch full project object via `/api/projects/${PROJECT_ID}`
- Show welcome project badge with name and color dot
- Set `currentProject` for subsequent operations

### Bug 2: Sidebar layout shift (complete fix)

**What Changed**
Sidebar content no longer jumps when scrollbar appears/disappears.

**Root Cause**
`overflow-y: auto` on `.projects-list` and `.conversations-list` causes scrollbar to appear/disappear, shifting layout.

**Fix**
- `chat.html:265` - Added `scrollbar-gutter: stable` to `.projects-list`
- `chat.html:357` - Added `scrollbar-gutter: stable` to `.conversations-list`

### Files Modified
- `web/templates/chat.html` - Fetch project object, show badge, scrollbar-gutter CSS

### Current State
- Deployed to production (PID 3365616)
- Service running

---

## 2026-01-04: Fix project New Chat context loss and sidebar layout shift (superseded)

### Bug 1: Project "New Chat" loses context

**What Changed**
When inside a project, clicking "New chat" now correctly creates a conversation in that project.

**Root Cause**
- `project.html:849` - Sidebar link was `<a href="/chat">` - lost project context
- `project.html:1234` - `startNewChat()` passed `?project=${projectId}` but `/chat` route ignored it
- `app.py:1570-1574` - `/chat` route didn't read the `project` query parameter
- `chat.html:4657` - `sendWelcomeMessage()` didn't include project_id when creating conversation

**Fix**
- `app.py:1574-1576` - Read `project` param and pass to template
- `chat.html:3848` - Define `PROJECT_ID` constant from template
- `chat.html:3914-3916` - Initialize `currentProjectId` from `PROJECT_ID` on new chat view
- `chat.html:4654-4657` - Include `project_id` in conversation creation
- `project.html:849` - Changed link to `/chat?project={{ project_id }}`

### Bug 2: Sidebar layout shift

**What Changed**
Sidebar content no longer jumps when clicking items or loading dynamic content.

**Root Cause**
- `chat.html:181` - `.sidebar-nav-item` had `transition: all 0.15s` which animates layout properties
- `chat.html:261-264` - `.projects-list` had no min-height, collapsed when empty
- `chat.html:352-356` - `.conversations-list` had no min-height, resized on dynamic content

**Fix**
- `chat.html:181` - Changed to `transition: background 0.15s, color 0.15s`
- `chat.html:263` - Added `min-height: 32px` to `.projects-list`
- `chat.html:354` - Added `min-height: 100px` to `.conversations-list`

### Files Modified
- `web/app.py` - Read project query param in /chat route
- `web/templates/chat.html` - CSS fixes, PROJECT_ID constant, sendWelcomeMessage fix
- `web/templates/project.html` - Sidebar New Chat link with project ID

### Current State
- Deployed to production
- Service running (PID 3364187)

---

## 2026-01-04: Implement route-based view architecture

### What Changed
Completely rewrote the view system from state-based toggling to route-based navigation. Each view now has its own URL:
- `/chat` → New chat (welcome screen)
- `/chat/recents` → Chat list
- `/chat/projects` → Projects list
- `/chat/<conversation_id>` → Specific conversation

### Why
The previous state-based architecture had race conditions where async operations (like `loadConversations()`) would modify view state after the intended view was already shown. Adding guards wasn't sufficient because multiple code paths could show views.

### Root Cause
State-based view toggling is fundamentally prone to race conditions. Multiple functions (`clearChat`, `showChatView`, `createNewConversation`) all manipulated display state, and async operations competed with synchronous view initialization.

### Solution
**Architecture change**: One route = one view. No state toggles.
- Views are now rendered server-side via Jinja2 conditionals based on `{{ view }}` variable
- Sidebar items are `<a href>` links that navigate (not onclick handlers that toggle state)
- Removed: `hideAllViews()`, `showChatsListView()`, `showProjectsListView()`, `showLibraryListView()`, `showNewChatView()`
- Removed: `isChatsListViewActive`, `isProjectsListViewActive`, `isLibraryListViewActive` state variables
- Added: `loadConversationData()` for loading conversation on conversation view
- Added: `sessionStorage` for pending messages when creating new conversation from welcome screen

### Files Modified
- `web/app.py` - Added routes: `/chat/recents`, `/chat/projects`, `/chat/<id>`; updated `/chat` route
- `web/templates/chat.html` - Conditional view rendering, navigation links, removed state toggling

### Issues Encountered
- None - clean implementation

### Current State
- Deployed to production
- Service running
- Ready for testing

---

## 2026-01-04: Fix race condition causing multiple views to display (superseded)

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
