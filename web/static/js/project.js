// Project page functionality
const PROJECT_ID = window.PROJECT_ID; // Will be set by template
let project = null;
let editColor = '#d97757';

function toggleDropdown(event) {
    event.stopPropagation();
    document.getElementById('dropdownMenu').classList.toggle('active');
}

document.addEventListener('click', function(e) {
    if (!e.target.closest('.dropdown')) {
        document.getElementById('dropdownMenu')?.classList.remove('active');
    }
});

async function loadProject() {
    try {
        const response = await fetch(`/api/projects/${PROJECT_ID}`);
        if (response.ok) {
            project = await response.json();
            renderProject();
        } else if (response.status === 404) {
            window.location.href = '/projects';
        }
    } catch (error) {
        console.error('Failed to load project:', error);
    }
}

function renderProject() {
    document.title = `${project.name} - MV Internal`;
    document.getElementById('projectTitle').textContent = project.name;
    document.getElementById('projectColor').style.background = project.color || '#d97757';
    document.getElementById('projectDescription').textContent = project.description || '';
    document.getElementById('projectDescription').style.display = project.description ? 'block' : 'none';

    renderConversations();
}

function renderConversations() {
    const container = document.getElementById('projectConversations');
    const conversations = project.conversations || [];

    let html = `
        <div class="new-chat-in-project" data-action="start-new-chat">
            <div class="new-chat-in-project-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
            </div>
            <span class="new-chat-in-project-text">Start new chat</span>
        </div>
    `;

    if (conversations.length === 0) {
        html += `
            <div class="empty-conversations">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h3>No chats yet</h3>
                <p>Start a new chat to begin working in this project</p>
            </div>
        `;
    } else {
        conversations.forEach(conv => {
            html += `
                <a href="/chat?conversation=${conv.id}" class="project-conversation-item">
                    <div class="project-conversation-icon">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                    </div>
                    <div class="project-conversation-info">
                        <div class="project-conversation-title">${escapeHtml(conv.title)}</div>
                        <div class="project-conversation-meta">${conv.message_count} message${conv.message_count !== 1 ? 's' : ''}</div>
                    </div>
                    <div class="project-conversation-arrow">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
                    </div>
                </a>
            `;
        });
    }

    container.innerHTML = html;
}

function startNewChat() {
    window.location.href = `/chat?project=${PROJECT_ID}`;
}

function openEditModal() {
    document.getElementById('editProjectName').value = project.name;
    document.getElementById('editProjectDesc').value = project.description || '';
    document.getElementById('editProjectInstructions').value = project.custom_instructions || '';
    editColor = project.color || '#d97757';

    document.querySelectorAll('#editColorPicker .color-option').forEach(el => {
        el.classList.toggle('selected', el.dataset.color === editColor);
    });

    document.getElementById('editModal').classList.add('active');
}

function closeEditModal() {
    document.getElementById('editModal').classList.remove('active');
}

document.getElementById('editColorPicker').addEventListener('click', function(e) {
    const option = e.target.closest('.color-option');
    if (option) {
        document.querySelectorAll('#editColorPicker .color-option').forEach(el => el.classList.remove('selected'));
        option.classList.add('selected');
        editColor = option.dataset.color;
    }
});

async function saveProject() {
    const name = document.getElementById('editProjectName').value.trim();
    const description = document.getElementById('editProjectDesc').value.trim();
    const custom_instructions = document.getElementById('editProjectInstructions').value.trim();

    if (!name) {
        document.getElementById('editProjectName').focus();
        return;
    }

    try {
        const response = await fetch(`/api/projects/${PROJECT_ID}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description, custom_instructions, color: editColor })
        });

        if (response.ok) {
            project = { ...project, name, description, custom_instructions, color: editColor };
            renderProject();
            closeEditModal();
            showToast('Project updated', 'success');
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to update project');
        }
    } catch (error) {
        console.error('Failed to update project:', error);
        alert('Failed to update project');
    }
}

async function deleteProject() {
    if (!confirm('Are you sure you want to delete this project? Chats will be preserved but unassigned.')) {
        return;
    }

    try {
        const response = await fetch(`/api/projects/${PROJECT_ID}?permanent=true`, {
            method: 'DELETE'
        });

        if (response.ok) {
            window.location.href = '/projects';
        } else {
            const error = await response.json();
            alert(error.error || 'Failed to delete project');
        }
    } catch (error) {
        console.error('Failed to delete project:', error);
        alert('Failed to delete project');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    loadProject();
});