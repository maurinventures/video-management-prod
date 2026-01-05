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
 * Toggle user menu dropdown
 * @param {Event} event - The click event
 */
function toggleUserMenu(event) {
    if (event) event.stopPropagation();
    const dropdown = document.getElementById('userMenuDropdown');
    if (dropdown) dropdown.classList.toggle('active');
}

/**
 * Load a conversation by ID
 * @param {string} conversationId - UUID of the conversation
 */
function loadConversation(conversationId) {
    window.location.href = `/chat?conversation=${conversationId}`;
}

/**
 * Open chat menu for a conversation item
 * @param {Event} event - The click event
 * @param {string} conversationId - UUID of the conversation
 * @param {string} title - Title of the conversation
 */
function openChatMenu(event, conversationId, title) {
    if (event) event.stopPropagation();

    // Close existing menus
    document.querySelectorAll('.chat-item-dropdown').forEach(menu => menu.remove());

    // Create dropdown menu
    const dropdown = document.createElement('div');
    dropdown.className = 'chat-item-dropdown';
    dropdown.innerHTML = `
        <button class="chat-menu-item" data-action="star-conversation" data-conversation-id="${conversationId}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"></polygon>
            </svg>
            Star chat
        </button>
        <button class="chat-menu-item danger" data-action="delete-conversation" data-conversation-id="${conversationId}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3,6 5,6 21,6"></polyline>
                <path d="m19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6m3,0V4a2,2,0,0,1,2,2h4a2,2,0,0,1,2,2v2"></path>
            </svg>
            Delete chat
        </button>
    `;

    // Position dropdown
    const rect = event.target.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = rect.bottom + 'px';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.zIndex = '1000';

    document.body.appendChild(dropdown);

    // Close dropdown when clicking outside
    setTimeout(() => {
        document.addEventListener('click', function closeDropdown() {
            dropdown.remove();
            document.removeEventListener('click', closeDropdown);
        });
    }, 0);
}

/**
 * Star/unstar a conversation
 * @param {string} conversationId - UUID of the conversation
 */
async function starConversation(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}/star`, {
            method: 'POST'
        });
        if (response.ok) {
            showToast('Chat starred', 'success');
            location.reload(); // Refresh to update sidebar
        }
    } catch (error) {
        showToast('Failed to star chat', 'error');
    }
}

/**
 * Delete a conversation
 * @param {string} conversationId - UUID of the conversation
 */
async function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this chat?')) return;

    try {
        const response = await fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        if (response.ok) {
            showToast('Chat deleted', 'success');
            location.reload(); // Refresh to update sidebar
        }
    } catch (error) {
        showToast('Failed to delete chat', 'error');
    }
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
 * Toggle expand/collapse state of a recents project folder
 * @param {string} projectId - UUID of the project
 */
function toggleRecentsProject(projectId) {
    const header = document.querySelector(`.recents-project-header[onclick*="${projectId}"]`);
    const items = document.getElementById(`recents-project-${projectId}`);

    if (!header || !items) return;

    // Toggle expanded class
    header.classList.toggle('expanded');
    items.classList.toggle('expanded');

    // Save state to localStorage
    const isExpanded = items.classList.contains('expanded');
    localStorage.setItem(`recents_project_${projectId}`, isExpanded);
}

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
// Chat Interface (Claude.ai style)
// ============================================

const Chat = {
    conversationId: null,
    selectedModel: 'sonnet-4',
    isLoading: false,
    pendingAttachments: [],

    elements: {},

    init() {
        // Cache DOM elements
        this.elements = {
            welcome: document.getElementById('chatWelcome'),
            greeting: document.getElementById('welcomeGreeting'),
            messages: document.getElementById('chatMessages'),
            input: document.getElementById('chatInput'),
            inputBox: document.getElementById('chatInputBox'),
            sendBtn: document.getElementById('sendBtn'),
            attachBtn: document.getElementById('attachBtn'),
            attachDropdown: document.getElementById('attachDropdown'),
            modelSelectorBtn: document.getElementById('modelSelectorBtn'),
            modelDropdown: document.getElementById('modelDropdown'),
            modelName: document.querySelector('.model-name'),
            quickActions: document.getElementById('quickActions'),
            page: document.querySelector('.chat-page')
        };

        if (!this.elements.input) return;

        this.setGreeting();
        this.bindEvents();
        this.checkExistingChat();

        console.log('Chat initialized');
    },

    setGreeting() {
        const hour = new Date().getHours();
        let greeting;

        if (hour < 12) {
            greeting = 'Good morning, Joy';
        } else if (hour < 17) {
            greeting = 'Good afternoon, Joy';
        } else if (hour < 21) {
            greeting = 'Good evening, Joy';
        } else {
            greeting = 'Coffee and Claude time?';
        }

        if (this.elements.greeting) {
            this.elements.greeting.textContent = greeting;
        }
    },

    bindEvents() {
        // Send button
        this.elements.sendBtn.addEventListener('click', () => this.send());

        // Enter to send (Shift+Enter for newline)
        this.elements.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.send();
            }
        });

        // Input changes
        this.elements.input.addEventListener('input', () => {
            this.autoResize();
            this.elements.sendBtn.disabled = !this.elements.input.value.trim();
        });

        // Attachment menu
        this.elements.attachBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown('attachDropdown');
        });

        // Model selector
        this.elements.modelSelectorBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown('modelDropdown');
        });

        // Model options
        document.querySelectorAll('.model-option[data-model]').forEach(btn => {
            btn.addEventListener('click', () => this.selectModel(btn.dataset.model));
        });

        // Quick action chips
        document.querySelectorAll('.quick-action-chip').forEach(btn => {
            btn.addEventListener('click', () => this.handleQuickAction(btn.dataset.action));
        });

        // Attach options
        document.querySelectorAll('.attach-option').forEach(btn => {
            btn.addEventListener('click', () => this.handleAttachOption(btn.dataset.action));
        });

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            this.closeAllDropdowns();
        });
    },

    autoResize() {
        const input = this.elements.input;
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    },

    toggleDropdown(id) {
        const dropdown = document.getElementById(id);
        const isOpen = dropdown.classList.contains('open');

        this.closeAllDropdowns();

        if (!isOpen) {
            dropdown.classList.add('open');
        }
    },

    closeAllDropdowns() {
        document.querySelectorAll('.model-dropdown, .attach-dropdown').forEach(d => {
            d.classList.remove('open');
        });

        // Also hide project submenu
        const projectSubmenu = document.getElementById('projectSubmenu');
        if (projectSubmenu) {
            projectSubmenu.style.display = 'none';
        }
    },

    selectModel(model) {
        this.selectedModel = model;

        // Update button text
        const names = {
            'opus-4.5': 'Opus 4.5',
            'sonnet-4': 'Sonnet 4',
            'haiku-4.5': 'Haiku 4.5'
        };
        this.elements.modelName.textContent = names[model] || model;

        // Update selected state
        document.querySelectorAll('.model-option').forEach(btn => {
            btn.classList.toggle('selected', btn.dataset.model === model);
        });

        this.closeAllDropdowns();
    },

    handleQuickAction(action) {
        const prompts = {
            'write': 'Help me write ',
            'learn': 'Explain ',
            'code': 'Write code to ',
            'life-stuff': 'Help me with ',
            'claude-choice': ''
        };

        if (prompts[action] !== undefined) {
            this.elements.input.value = prompts[action];
            this.elements.input.focus();
            this.autoResize();
            this.elements.sendBtn.disabled = !this.elements.input.value.trim();
        }
    },

    handleAttachOption(action) {
        switch (action) {
            case 'add-files':
                this.closeAllDropdowns();
                this.openFilePicker();
                break;
            case 'screenshot':
                this.closeAllDropdowns();
                this.captureScreenshot();
                break;
            case 'add-to-project':
                // Don't close dropdowns yet - keep submenu open
                this.showProjectSubmenu();
                break;
            case 'research':
                this.closeAllDropdowns();
                this.elements.input.value = '/research ';
                this.elements.input.focus();
                break;
            case 'web-search':
                this.closeAllDropdowns();
                // Toggle web search
                break;
            default:
                this.closeAllDropdowns();
                console.log('Action:', action);
        }
    },

    openFilePicker() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '*/*'; // Accept all file types as requested
        input.multiple = true;
        input.onchange = async (e) => {
            const files = Array.from(e.target.files);

            if (files.length === 0) return;

            // Upload each file
            for (const file of files) {
                await this.uploadFile(file);
            }
        };
        input.click();
    },

    async uploadFile(file) {
        // Get current conversation ID
        const conversationId = this.getConversationId();
        if (!conversationId) {
            showToast('No active conversation', 'error');
            return;
        }

        try {
            showToast(`Uploading ${file.name}...`, 'info');

            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`/api/conversations/${conversationId}/attachments`, {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast(`${file.name} uploaded successfully`, 'success');

                // Add to pending attachments
                this.pendingAttachments.push(result.attachment);
                this.updateAttachButton();

                console.log('Attachment uploaded:', result.attachment);
            } else {
                showToast(`Upload failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Upload error:', error);
            showToast(`Upload failed: ${error.message}`, 'error');
        }
    },

    getConversationId() {
        // Extract conversation ID from current URL path
        const pathParts = window.location.pathname.split('/');
        if (pathParts[1] === 'chat' && pathParts[2]) {
            return pathParts[2];
        }
        return null;
    },

    async captureScreenshot() {
        // Check for browser support
        if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
            showToast('Screen capture not supported in this browser', 'error');
            return;
        }

        try {
            showToast('Select screen to capture...', 'info');

            // Request screen access
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: {
                    mediaSource: 'screen'
                }
            });

            // Create video element to capture frame
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();

            // Wait for video to load
            await new Promise((resolve) => {
                video.onloadedmetadata = resolve;
            });

            // Create canvas to capture frame
            const canvas = document.createElement('canvas');
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;

            const ctx = canvas.getContext('2d');
            ctx.drawImage(video, 0, 0);

            // Stop the stream
            stream.getTracks().forEach(track => track.stop());

            // Convert canvas to blob
            canvas.toBlob(async (blob) => {
                if (blob) {
                    // Create File object with timestamp filename
                    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
                    const file = new File([blob], `screenshot-${timestamp}.png`, {
                        type: 'image/png'
                    });

                    // Upload the screenshot
                    await this.uploadFile(file);
                } else {
                    showToast('Failed to create screenshot', 'error');
                }
            }, 'image/png');

        } catch (error) {
            console.error('Screenshot capture error:', error);

            if (error.name === 'NotAllowedError') {
                showToast('Screen capture permission denied', 'error');
            } else if (error.name === 'NotSupportedError') {
                showToast('Screen capture not supported', 'error');
            } else {
                showToast('Screenshot capture failed', 'error');
            }
        }
    },

    async showProjectSubmenu() {
        const submenu = document.getElementById('projectSubmenu');
        if (!submenu) return;

        // Load and display projects
        await this.loadProjects();

        // Show the submenu
        submenu.style.display = 'block';
    },

    async loadProjects() {
        try {
            const response = await fetch('/api/projects');
            const result = await response.json();

            if (response.ok && result.projects) {
                this.displayProjects(result.projects);
            } else {
                console.error('Failed to load projects:', result.error);
                showToast('Failed to load projects', 'error');
            }
        } catch (error) {
            console.error('Error loading projects:', error);
            showToast('Error loading projects', 'error');
        }
    },

    displayProjects(projects) {
        const projectList = document.getElementById('projectList');
        if (!projectList) return;

        // Clear existing projects
        projectList.innerHTML = '';

        if (projects.length === 0) {
            projectList.innerHTML = `
                <div class="no-projects">
                    <span style="color: var(--color-text-secondary); font-size: 11px; padding: 16px; display: block; text-align: center;">
                        No projects yet
                    </span>
                </div>
            `;
            return;
        }

        // Add each project
        projects.forEach(project => {
            const projectElement = document.createElement('button');
            projectElement.className = 'project-option';
            projectElement.dataset.projectId = project.id;
            projectElement.innerHTML = `
                <div class="project-color-dot" style="background-color: ${project.color || '#6B7280'}"></div>
                <div class="project-info">
                    <div class="project-name">${project.name}</div>
                    ${project.description ? `<div class="project-description">${project.description}</div>` : ''}
                </div>
            `;

            projectElement.addEventListener('click', () => {
                this.assignToProject(project.id, project.name);
            });

            projectList.appendChild(projectElement);
        });

        // Add event listener for create new project button
        const createBtn = document.querySelector('.project-option.create-new');
        if (createBtn) {
            createBtn.onclick = () => this.showCreateProjectModal();
        }
    },

    async assignToProject(projectId, projectName) {
        const conversationId = this.getConversationId();
        if (!conversationId) {
            showToast('No active conversation', 'error');
            return;
        }

        try {
            showToast(`Adding to ${projectName}...`, 'info');

            const response = await fetch(`/api/conversations/${conversationId}/project`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    project_id: projectId
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                showToast(`Added to ${projectName}`, 'success');
                this.closeAllDropdowns();
                // TODO: Update UI to show project assignment
            } else {
                showToast(`Failed to add to project: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Project assignment error:', error);
            showToast('Failed to add to project', 'error');
        }
    },

    showCreateProjectModal() {
        // TODO: Implement create project modal
        showToast('Create project modal coming soon', 'info');
        this.closeAllDropdowns();
    },

    async send() {
        const message = this.elements.input.value.trim();
        if (!message || this.isLoading) return;

        this.isLoading = true;
        this.elements.sendBtn.disabled = true;

        // Switch to chat mode
        this.elements.page.classList.add('has-messages');

        // Add user message with attachments
        const attachments = [...this.pendingAttachments]; // Copy attachments
        this.addMessage('user', message, false, attachments);

        // Clear input and pending attachments
        this.elements.input.value = '';
        this.autoResize();
        this.pendingAttachments = [];
        this.updateAttachButton();

        // Add loading message
        const loadingId = this.addMessage('assistant', '', true);

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    conversation_id: this.conversationId,
                    model: this.selectedModel,
                    attachments: attachments.length > 0 ? attachments : undefined
                })
            });

            if (!response.ok) throw new Error('Failed to send');

            const data = await response.json();

            // Remove loading, add response
            this.removeMessage(loadingId);
            this.addMessage('assistant', data.response);

            // Update conversation ID
            if (data.conversation_id && !this.conversationId) {
                this.conversationId = data.conversation_id;
                history.pushState({}, '', `/chat/${data.conversation_id}`);
            }

        } catch (error) {
            console.error('Chat error:', error);
            this.removeMessage(loadingId);
            this.addMessage('error', 'Failed to send message. Please try again.');
        } finally {
            this.isLoading = false;
            this.elements.sendBtn.disabled = !this.elements.input.value.trim();
        }
    },

    addMessage(role, content, isLoading = false, attachments = []) {
        const id = 'msg-' + Date.now();
        const div = document.createElement('div');
        div.id = id;
        div.className = `message message-${role}${isLoading ? ' loading' : ''}`;

        // Build attachments HTML
        let attachmentsHtml = '';
        if (attachments && attachments.length > 0) {
            attachmentsHtml = `<div class="message-attachments">${attachments.map(attachment => this.renderAttachment(attachment)).join('')}</div>`;
        }

        div.innerHTML = `
            ${attachmentsHtml}
            <div class="message-content">
                ${isLoading ? '<div class="typing-dots"><span></span><span></span><span></span></div>' : this.formatContent(content)}
            </div>
        `;

        this.elements.messages.appendChild(div);
        this.elements.messages.scrollTop = this.elements.messages.scrollHeight;

        return id;
    },

    removeMessage(id) {
        document.getElementById(id)?.remove();
    },

    formatContent(content) {
        // Basic formatting - escape HTML and convert newlines
        return content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
    },

    renderAttachment(attachment) {
        const isImage = attachment.file_type.startsWith('image/');
        const isVideo = attachment.file_type.startsWith('video/');
        const isAudio = attachment.file_type.startsWith('audio/');

        if (isImage) {
            return `
                <div class="attachment attachment-image" data-attachment-id="${attachment.id}">
                    <img src="${attachment.preview_url}" alt="${attachment.filename}" onclick="window.open('${attachment.preview_url}', '_blank')">
                    <div class="attachment-info">
                        <span class="attachment-name">${attachment.filename}</span>
                        <span class="attachment-size">${this.formatFileSize(attachment.file_size)}</span>
                    </div>
                </div>
            `;
        } else if (isVideo) {
            return `
                <div class="attachment attachment-video" data-attachment-id="${attachment.id}">
                    <video controls preload="metadata">
                        <source src="${attachment.preview_url}" type="${attachment.file_type}">
                        Your browser does not support the video tag.
                    </video>
                    <div class="attachment-info">
                        <span class="attachment-name">${attachment.filename}</span>
                        <span class="attachment-size">${this.formatFileSize(attachment.file_size)}</span>
                    </div>
                </div>
            `;
        } else if (isAudio) {
            return `
                <div class="attachment attachment-audio" data-attachment-id="${attachment.id}">
                    <div class="attachment-icon">🎵</div>
                    <div class="attachment-details">
                        <div class="attachment-info">
                            <span class="attachment-name">${attachment.filename}</span>
                            <span class="attachment-size">${this.formatFileSize(attachment.file_size)}</span>
                        </div>
                        <audio controls>
                            <source src="${attachment.preview_url}" type="${attachment.file_type}">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                </div>
            `;
        } else {
            // Generic file
            const fileIcon = this.getFileIcon(attachment.file_type, attachment.filename);
            return `
                <div class="attachment attachment-file" data-attachment-id="${attachment.id}">
                    <div class="attachment-icon">${fileIcon}</div>
                    <div class="attachment-details">
                        <div class="attachment-info">
                            <span class="attachment-name">${attachment.filename}</span>
                            <span class="attachment-size">${this.formatFileSize(attachment.file_size)}</span>
                        </div>
                        <a href="${attachment.preview_url}" download="${attachment.filename}" class="attachment-download">Download</a>
                    </div>
                </div>
            `;
        }
    },

    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    },

    getFileIcon(mimeType, filename) {
        if (mimeType.startsWith('text/')) return '📄';
        if (mimeType.includes('pdf')) return '📕';
        if (mimeType.includes('word') || filename.endsWith('.doc') || filename.endsWith('.docx')) return '📘';
        if (mimeType.includes('spreadsheet') || filename.endsWith('.xls') || filename.endsWith('.xlsx')) return '📊';
        if (mimeType.includes('presentation') || filename.endsWith('.ppt') || filename.endsWith('.pptx')) return '📋';
        if (mimeType.includes('zip') || mimeType.includes('archive')) return '📦';
        if (mimeType.includes('json') || mimeType.includes('javascript')) return '⚙️';
        return '📎';
    },

    updateAttachButton() {
        const attachBtn = document.getElementById('attachBtn');
        if (!attachBtn) return;

        // Update button appearance to show pending attachments count
        if (this.pendingAttachments.length > 0) {
            attachBtn.classList.add('has-attachments');
            attachBtn.title = `${this.pendingAttachments.length} attachment(s) ready to send`;

            // Add a small badge showing count
            let badge = attachBtn.querySelector('.attachment-count');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'attachment-count';
                attachBtn.appendChild(badge);
            }
            badge.textContent = this.pendingAttachments.length;
        } else {
            attachBtn.classList.remove('has-attachments');
            attachBtn.title = 'Attach files';
            const badge = attachBtn.querySelector('.attachment-count');
            if (badge) {
                badge.remove();
            }
        }
    },

    checkExistingChat() {
        const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
        if (match) {
            this.conversationId = match[1];
            this.loadChat();
        }
    },

    async loadChat() {
        try {
            const response = await fetch(`/api/chat/${this.conversationId}`);
            if (!response.ok) return;

            const data = await response.json();

            this.elements.page.classList.add('has-messages');

            data.messages.forEach(msg => {
                this.addMessage(msg.role, msg.content);
            });
        } catch (error) {
            console.error('Failed to load chat:', error);
        }
    }
};

// ============================================
// Event Delegation System
// ============================================

/**
 * Set up event delegation for all interactive elements
 * This replaces onclick handlers with proper event delegation
 */
function setupEventDelegation() {
    document.addEventListener('click', function(event) {
        const target = event.target.closest('[data-action]');
        if (!target) return;

        const action = target.dataset.action;
        const params = target.dataset;

        switch (action) {
            case 'toggle-sidebar':
                toggleSidebar();
                break;

            case 'toggle-library':
                toggleLibrarySection();
                break;

            case 'toggle-recents-project':
                toggleRecentsProject(params.projectId);
                break;

            case 'load-conversation':
                loadConversation(params.conversationId);
                break;

            case 'open-chat-menu':
                event.stopPropagation();
                openChatMenu(event, params.conversationId, params.title);
                break;

            case 'toggle-user-menu':
                toggleUserMenu(event);
                break;

            case 'star-conversation':
                starConversation(params.conversationId);
                break;

            case 'delete-conversation':
                deleteConversation(params.conversationId);
                break;

            case 'toggle-dropdown':
                event.stopPropagation();
                toggleGenericDropdown(params.targetId);
                break;

            case 'close-modal':
                closeModal(event);
                break;

            case 'share-chat':
                shareChat();
                break;

            case 'go-to-project':
                goToProject(event);
                break;

            case 'toggle-select-mode':
                toggleSelectMode();
                break;

            case 'delete-selected-chats':
                deleteSelectedChats();
                break;

            case 'open-chat-from-list':
                openChatFromList(params.conversationId);
                break;

            case 'toggle-chat-selection':
                event.stopPropagation();
                toggleChatSelection(params.conversationId);
                break;

            case 'close-share-modal':
                closeShareModal(event);
                break;

            case 'open-edit-modal':
                openEditModal();
                break;

            case 'close-edit-modal':
                closeEditModal();
                break;

            case 'save-project':
                saveProject();
                break;

            case 'delete-project':
                deleteProject();
                break;

            case 'start-new-chat':
                startNewChat();
                break;

            default:
                console.log('Unknown action:', action);
        }
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', function(event) {
        // Close user menu if clicking outside
        if (!event.target.closest('.sidebar-footer')) {
            const userMenu = document.getElementById('userMenuDropdown');
            if (userMenu) userMenu.classList.remove('active');
        }

        // Close any open chat menus
        if (!event.target.closest('.chat-item-dropdown')) {
            document.querySelectorAll('.chat-item-dropdown').forEach(menu => menu.remove());
        }

        // Close any dropdowns with 'active' class
        if (!event.target.closest('.dropdown')) {
            document.querySelectorAll('.dropdown-menu.active').forEach(menu => {
                menu.classList.remove('active');
            });
        }
    });
}

/**
 * Toggle generic dropdown by ID
 * @param {string} targetId - ID of dropdown to toggle
 */
function toggleGenericDropdown(targetId) {
    const dropdown = document.getElementById(targetId);
    if (dropdown) dropdown.classList.toggle('active');
}

// ============================================
// Chat Page Functions
// ============================================

/**
 * Close modal by clicking outside
 * @param {Event} event - The click event
 */
function closeModal(event) {
    if (event.target === event.currentTarget) {
        event.currentTarget.style.display = 'none';
    }
}

/**
 * Share current chat
 */
function shareChat() {
    const modal = document.getElementById('shareModal');
    if (modal) {
        modal.style.display = 'flex';
        const searchInput = document.getElementById('userSearch');
        if (searchInput) searchInput.focus();
    }
}

/**
 * Go to project page from chat
 * @param {Event} event - The click event
 */
function goToProject(event) {
    if (event) event.preventDefault();
    const projectId = event.target.closest('[data-project-id]')?.dataset.projectId;
    if (projectId) {
        window.location.href = `/project/${projectId}`;
    }
}

/**
 * Toggle chat selection mode
 */
function toggleSelectMode() {
    const selectActions = document.querySelector('.chats-select-actions');
    const selectBtn = document.querySelector('.chats-select-btn');
    const countRow = document.querySelector('.chats-count-row');

    if (selectActions && selectBtn && countRow) {
        const isVisible = selectActions.style.display === 'flex';
        selectActions.style.display = isVisible ? 'none' : 'flex';
        selectBtn.style.display = isVisible ? 'block' : 'none';
        countRow.style.display = isVisible ? 'flex' : 'none';

        // Clear selections if exiting select mode
        if (isVisible) {
            document.querySelectorAll('.chat-list-checkbox').forEach(cb => cb.checked = false);
            updateSelectCount();
        }
    }
}

/**
 * Delete selected chats
 */
async function deleteSelectedChats() {
    const selectedCheckboxes = document.querySelectorAll('.chat-list-checkbox:checked');
    const chatIds = Array.from(selectedCheckboxes).map(cb => cb.closest('[data-id]')?.dataset.id).filter(Boolean);

    if (chatIds.length === 0) return;

    if (!confirm(`Delete ${chatIds.length} chat${chatIds.length > 1 ? 's' : ''}?`)) return;

    try {
        const promises = chatIds.map(id =>
            fetch(`/api/conversations/${id}`, { method: 'DELETE' })
        );

        await Promise.all(promises);
        showToast(`${chatIds.length} chat${chatIds.length > 1 ? 's' : ''} deleted`, 'success');

        // Reload the page to refresh the list
        window.location.reload();
    } catch (error) {
        showToast('Failed to delete chats', 'error');
    }
}

/**
 * Open chat from list
 * @param {string} conversationId - ID of the conversation
 */
function openChatFromList(conversationId) {
    window.location.href = `/chat?conversation=${conversationId}`;
}

/**
 * Toggle chat selection checkbox
 * @param {string} conversationId - ID of the conversation
 */
function toggleChatSelection(conversationId) {
    const checkbox = document.querySelector(`[data-id="${conversationId}"] .chat-list-checkbox`);
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
        updateSelectCount();
    }
}

/**
 * Update the selection count display
 */
function updateSelectCount() {
    const selectedCount = document.querySelectorAll('.chat-list-checkbox:checked').length;
    const countDisplay = document.getElementById('selectCount');
    if (countDisplay) {
        countDisplay.textContent = `${selectedCount} selected`;
    }
}

/**
 * Close share modal
 * @param {Event} event - The click event
 */
function closeShareModal(event) {
    if (event.target === event.currentTarget) {
        const modal = document.getElementById('shareModal');
        if (modal) modal.style.display = 'none';
    }
}

// ============================================
// Project Page Functions
// ============================================

/**
 * Open project edit modal
 */
function openEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.add('active');

    // This function should be overridden by page-specific logic
    if (typeof window.openEditModal === 'function') {
        window.openEditModal();
    }
}

/**
 * Close project edit modal
 */
function closeEditModal() {
    const modal = document.getElementById('editModal');
    if (modal) modal.classList.remove('active');
}

/**
 * Save project changes
 */
function saveProject() {
    // This function should be overridden by page-specific logic
    if (typeof window.saveProject === 'function') {
        window.saveProject();
    }
}

/**
 * Delete current project
 */
function deleteProject() {
    // This function should be overridden by page-specific logic
    if (typeof window.deleteProject === 'function') {
        window.deleteProject();
    }
}

/**
 * Start new chat in project
 */
function startNewChat() {
    // Check if PROJECT_ID is available (for project pages)
    if (typeof PROJECT_ID !== 'undefined') {
        window.location.href = `/chat?project=${PROJECT_ID}`;
        return;
    }

    // Fallback - this function should be overridden by page-specific logic
    if (typeof window.startNewChat === 'function') {
        window.startNewChat();
    }
}

// ============================================
// Auto-initialize on DOM ready
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    restoreSidebarState();
    setupEventDelegation();

    // Initialize Chat interface if on chat page
    if (document.querySelector('.chat-page')) {
        Chat.init();
    }
});
