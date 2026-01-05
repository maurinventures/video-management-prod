/**
 * MV Internal - Shared Utility Functions
 * This file contains common functions used across multiple templates.
 * Include this file before template-specific JavaScript.
 */

// ============================================
// Text Utilities
// ============================================

/**
 * Escape HTML special characters to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML string
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Format a date string as relative time (e.g., "5m ago", "2h ago")
 * @param {string} dateStr - ISO date string
 * @returns {string} Formatted relative time
 */
function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`;
    return date.toLocaleDateString();
}

// ============================================
// Sidebar Functions
// ============================================

/**
 * Toggle sidebar collapsed state
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    sidebar.classList.toggle('collapsed');
    localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
}

/**
 * Toggle Library section in sidebar
 */
function toggleLibrarySection() {
    const header = document.getElementById('libraryHeader');
    const section = document.getElementById('librarySection');
    if (!header || !section) return;
    header.classList.toggle('expanded');
    section.classList.toggle('expanded');
    localStorage.setItem('libraryExpanded', section.classList.contains('expanded'));
}

/**
 * Restore sidebar state from localStorage
 * Call this on DOMContentLoaded
 */
function restoreSidebarState() {
    // Restore collapsed state
    if (localStorage.getItem('sidebarCollapsed') === 'true') {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) sidebar.classList.add('collapsed');
    }

    // Restore Library section state (use IDs for reliability)
    const libraryHeader = document.getElementById('libraryHeader');
    const librarySection = document.getElementById('librarySection');
    const libraryExpanded = localStorage.getItem('libraryExpanded');

    if (libraryExpanded === 'false') {
        if (libraryHeader) libraryHeader.classList.remove('expanded');
        if (librarySection) librarySection.classList.remove('expanded');
    } else if (libraryExpanded === 'true') {
        if (libraryHeader) libraryHeader.classList.add('expanded');
        if (librarySection) librarySection.classList.add('expanded');
    }

    // Remove the blocking style override now that classes are properly set
    const overrideStyle = document.getElementById('sidebar-state-override');
    if (overrideStyle) {
        overrideStyle.remove();
    }
}

// ============================================
// Toast Notifications
// ============================================

/**
 * Show a toast notification
 * @param {string} message - Message to display
 * @param {string} type - Type: 'success', 'error', or 'info'
 */
function showToast(message, type = 'info') {
    // Remove existing toasts
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;

    // Add styles if not already in document
    if (!document.getElementById('toast-styles')) {
        const style = document.createElement('style');
        style.id = 'toast-styles';
        style.textContent = `
            .toast {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                padding: 12px 24px;
                border-radius: 8px;
                color: white;
                font-size: 14px;
                z-index: 10000;
                animation: toastIn 0.3s ease;
            }
            .toast-success { background: #10b981; }
            .toast-error { background: #ef4444; }
            .toast-info { background: #3b82f6; }
            @keyframes toastIn {
                from { opacity: 0; transform: translateX(-50%) translateY(20px); }
                to { opacity: 1; transform: translateX(-50%) translateY(0); }
            }
        `;
        document.head.appendChild(style);
    }

    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

// ============================================
// Recents Section
// ============================================

/**
 * Render conversations list (flat list, no project grouping)
 * @param {Array} conversations - Array of conversation objects
 * @param {string} containerId - ID of the container element (default: 'conversationsList')
 */
function renderConversationsGrouped(conversations, containerId = 'conversationsList') {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Filter out empty chats
    const nonEmpty = (conversations || []).filter(c => c.message_count > 0);

    if (nonEmpty.length === 0) {
        container.innerHTML = '<div style="padding: 0.5rem 1rem; font-size: 0.8125rem; color: #888;">No recent chats</div>';
        return;
    }

    container.innerHTML = nonEmpty.map(conv => `
        <a href="/chat?conversation=${conv.id}" class="conversation-item">
            <span class="conversation-title">${escapeHtml(conv.title)}</span>
        </a>
    `).join('');
}

// ============================================
// Auto-initialize on DOM ready
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    restoreSidebarState();
});
