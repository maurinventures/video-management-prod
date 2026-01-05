# Changelog

All notable changes to MV Internal will be documented in this file.

## [2026-01-05] - Chat Recents Page Redesign

### Added
- Modern Claude.ai-style design for `/chat/recents` page
- Clean header layout with "Chats" title and "+ New chat" button
- Search bar with integrated search icon
- Enhanced chat list items with improved typography and spacing
- Smooth hover effects and transitions
- Responsive design for mobile devices
- Selection mode styling for bulk operations

### Changed
- Updated CSS architecture by moving chat list styles from template to `components.css`
- Improved visual hierarchy and spacing throughout chat recents page
- Enhanced user experience with modern, professional interface

### Technical
- Added 320+ lines of CSS to `web/static/css/components.css`
- Removed conflicting styles from `web/templates/chat_new.html`
- Maintained compatibility with existing light color scheme
- Preserved all existing functionality (search, selection mode, etc.)