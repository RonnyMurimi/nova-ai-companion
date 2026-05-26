const API_BASE = 'https://web-production-e8938.up.railway.app';

let userId = null;
let username = null;
let token = null;
let currentThreadId = null;
let threads = [];
let backendOnline = false;

/* ==================== INITIALIZATION ==================== */

document.addEventListener('DOMContentLoaded', async () => {
    await checkBackendConnection();

    if (checkAuth()) {
        await initApp();
    }

    // Auto-resize textarea
    const textarea = document.getElementById('message-input');
    if (textarea) {
        textarea.addEventListener('input', autoResizeTextarea);
    }
});

async function initApp() {
    await loadUserProfile();
    await loadThreads();
    await loadVoiceSettings();

    // Select first thread or create new one
    if (threads.length === 0) {
        await createNewThread();
    } else {
        const savedThreadId = localStorage.getItem('nova_current_thread');
        const threadExists = threads.find(t => t.thread_id === savedThreadId);

        if (savedThreadId && threadExists) {
            await selectThread(savedThreadId);
        } else {
            await selectThread(threads[0].thread_id);
        }
    }
}

/* ==================== BACKEND CONNECTION ==================== */

async function checkBackendConnection() {
    try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 5000);

        const res = await fetch(`${API_BASE}/health`, {
            signal: controller.signal
        });

        clearTimeout(timeout);

        if (res.ok) {
            backendOnline = true;
            hideConnectionWarning();
            return true;
        }

        throw new Error('Backend not responding');
    } catch (err) {
        backendOnline = false;
        showConnectionWarning();
        return false;
    }
}

function showConnectionWarning() {
    const warning = document.getElementById('connection-warning');
    if (warning) warning.classList.remove('hidden');
}

function hideConnectionWarning() {
    const warning = document.getElementById('connection-warning');
    if (warning) warning.classList.add('hidden');
}

/* ==================== AUTH ==================== */

function checkAuth() {
    token = localStorage.getItem('nova_token');
    username = localStorage.getItem('nova_username');
    userId = localStorage.getItem('nova_user_id');

    if (token && username && userId) {
        showApp();
        return true;
    }

    showAuth();
    return false;
}

function showAuth() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('app-screen').classList.add('hidden');
}

function showApp() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('app-screen').classList.remove('hidden');
    document.getElementById('current-username').textContent = username;
}

function switchAuthTab(tab) {
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(form => form.classList.remove('active'));

    if (tab === 'login') {
        document.querySelector('.tab-btn:first-child').classList.add('active');
        document.getElementById('login-form').classList.add('active');
    } else {
        document.querySelector('.tab-btn:last-child').classList.add('active');
        document.getElementById('register-form').classList.add('active');
    }

    hideAuthMessage();
}

function showAuthMessage(message, type = 'error') {
    const el = document.getElementById('auth-message');
    if (!el) return;

    el.textContent = message;
    el.className = `auth-message ${type}`;
    el.classList.remove('hidden');
}

function hideAuthMessage() {
    const el = document.getElementById('auth-message');
    if (el) el.classList.add('hidden');
}

async function handleLogin() {
    const usernameInput = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    if (!usernameInput || !password) {
        showAuthMessage('Please fill in all fields', 'error');
        return;
    }

    const connected = await checkBackendConnection();
    if (!connected) {
        showAuthMessage('Cannot connect to backend. Please start the server.', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: usernameInput, password })
        });

        const data = await res.json();

        if (data.success) {
            localStorage.setItem('nova_token', data.token);
            localStorage.setItem('nova_username', data.username);
            localStorage.setItem('nova_user_id', data.user_id);

            token = data.token;
            username = data.username;
            userId = data.user_id;

            await initApp();
            showApp();
        } else {
            showAuthMessage(data.message || 'Login failed', 'error');
        }
    } catch (err) {
        console.error('Login error:', err);
        showAuthMessage('Connection error', 'error');
    }
}

async function handleRegister() {
    const usernameInput = document.getElementById('register-username').value.trim();
    const email = document.getElementById('register-email').value.trim();
    const password = document.getElementById('register-password').value;

    if (!usernameInput || !password) {
        showAuthMessage('Username and password required', 'error');
        return;
    }

    const connected = await checkBackendConnection();
    if (!connected) {
        showAuthMessage('Cannot connect to backend. Please start the server.', 'error');
        return;
    }

    try {
        const res = await fetch(`${API_BASE}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: usernameInput,
                password,
                email: email || null
            })
        });

        const data = await res.json();

        if (data.success) {
            showAuthMessage('Account created! Please login.', 'success');
            setTimeout(() => {
                switchAuthTab('login');
                document.getElementById('login-username').value = usernameInput;
            }, 1500);
        } else {
            showAuthMessage(data.message || 'Registration failed', 'error');
        }
    } catch (err) {
        console.error('Register error:', err);
        showAuthMessage('Connection error', 'error');
    }
}

function logout() {
    if (!confirm('Are you sure you want to logout?')) return;

    localStorage.removeItem('nova_token');
    localStorage.removeItem('nova_username');
    localStorage.removeItem('nova_user_id');
    localStorage.removeItem('nova_current_thread');

    token = null;
    username = null;
    userId = null;
    currentThreadId = null;
    threads = [];

    stopSpeaking();

    document.getElementById('chat-box').innerHTML = '';
    showAuth();
}

/* ==================== THREADS ==================== */

async function loadThreads() {
    if (!userId) return;

    try {
        const res = await fetch(`${API_BASE}/threads/${userId}`);
        const data = await res.json();

        if (data.success) {
            threads = data.threads || [];
            renderThreads();
        }
    } catch (err) {
        console.error('Load threads error:', err);
        showToast('Failed to load chats', 'error');
    }
}

function renderThreads() {
    const list = document.getElementById('thread-list');
    if (!list) return;

    if (threads.length === 0) {
        list.innerHTML = '<div class="thread-item">No chats yet</div>';
        return;
    }

    list.innerHTML = threads.map(thread => {
        const active = thread.thread_id === currentThreadId ? 'active' : '';
        const title = escapeHTML(thread.title || 'New Chat');
        const count = thread.message_count || 0;

        return `
            <div class="thread-item ${active}" onclick="selectThread('${thread.thread_id}')">
                <div class="thread-title">${title}</div>
                <div class="thread-meta">${count} messages</div>
            </div>
        `;
    }).join('');
}

async function createNewThread() {
    if (!userId) return;

    try {
        const fd = new FormData();
        fd.append('title', 'New Chat');

        const res = await fetch(`${API_BASE}/threads/${userId}/create`, {
            method: 'POST',
            body: fd
        });

        const data = await res.json();

        if (data.success) {
            await loadThreads();
            await selectThread(data.thread_id);
            showToast('New chat started', 'success');
        }
    } catch (err) {
        console.error('Create thread error:', err);
        showToast('Failed to create chat', 'error');
    }
}

async function selectThread(threadId) {
    currentThreadId = threadId;
    localStorage.setItem('nova_current_thread', threadId);

    const thread = threads.find(t => t.thread_id === threadId);
    const title = thread ? thread.title : 'New Chat';

    document.getElementById('current-thread-title').textContent = title;

    renderThreads();
    await loadThreadHistory(threadId);
}

async function loadThreadHistory(threadId) {
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';

    try {
        const res = await fetch(`${API_BASE}/threads/${userId}/${threadId}/history?limit=100`);
        const data = await res.json();

        if (data.success && data.history.length > 0) {
            data.history.forEach(msg => {
                addMessageToUI(msg.content, msg.role === 'user' ? 'user' : 'ai', false);
            });
        } else {
            addWelcomeMessage();
        }

        scrollToBottom();
    } catch (err) {
        console.error('Load history error:', err);
        showToast('Failed to load chat history', 'error');
    }
}

async function renameThread() {
    if (!currentThreadId) return;

    const thread = threads.find(t => t.thread_id === currentThreadId);
    const currentTitle = thread ? thread.title : 'New Chat';

    const newTitle = prompt('Rename this chat:', currentTitle);
    if (!newTitle || newTitle.trim() === '') return;

    try {
        const fd = new FormData();
        fd.append('title', newTitle.trim());

        const res = await fetch(`${API_BASE}/threads/${userId}/${currentThreadId}`, {
            method: 'PUT',
            body: fd
        });

        const data = await res.json();

        if (data.success) {
            document.getElementById('current-thread-title').textContent = newTitle.trim();
            await loadThreads();
            showToast('Chat renamed', 'success');
        }
    } catch (err) {
        console.error('Rename error:', err);
        showToast('Failed to rename', 'error');
    }
}

async function deleteThread() {
    if (!currentThreadId) return;

    const thread = threads.find(t => t.thread_id === currentThreadId);
    const title = thread ? thread.title : 'this chat';

    if (!confirm(`Delete "${title}"?`)) return;

    try {
        const res = await fetch(`${API_BASE}/threads/${userId}/${currentThreadId}`, {
            method: 'DELETE'
        });

        const data = await res.json();

        if (data.success) {
            currentThreadId = null;
            localStorage.removeItem('nova_current_thread');

            await loadThreads();

            if (threads.length > 0) {
                await selectThread(threads[0].thread_id);
            } else {
                await createNewThread();
            }

            showToast('Chat deleted', 'success');
        }
    } catch (err) {
        console.error('Delete error:', err);
        showToast('Failed to delete', 'error');
    }
}

/* ==================== PROFILE ==================== */

async function loadUserProfile() {
    if (!userId) return;

    try {
        const res = await fetch(`${API_BASE}/profile/${userId}`);
        const data = await res.json();

        if (data.success) {
            const profile = data.profile;

            if (profile.name) {
                document.getElementById('display-name').value = profile.name;
            }

            const adj = profile.personality_adjustments || {};

            if (adj.formality !== undefined) {
                document.getElementById('formality').value = adj.formality * 100;
                updateFormalityDisplay(adj.formality * 100);
            }

            if (adj.enthusiasm !== undefined) {
                document.getElementById('enthusiasm').value = adj.enthusiasm * 100;
                updateEnthusiasmDisplay(adj.enthusiasm * 100);
            }

            if (adj.verbosity !== undefined) {
                document.getElementById('verbosity').value = adj.verbosity * 100;
                updateVerbosityDisplay(adj.verbosity * 100);
            }
        }
    } catch (err) {
        console.error('Profile load error:', err);
    }
}

async function saveProfile() {
    const name = document.getElementById('display-name').value.trim();

    if (!name) {
        showToast('Please enter a name', 'error');
        return;
    }

    try {
        const fd = new FormData();
        fd.append('name', name);

        const res = await fetch(`${API_BASE}/profile/${userId}/update`, {
            method: 'POST',
            body: fd
        });

        const data = await res.json();

        if (data.success) {
            showToast('Profile saved', 'success');
        }
    } catch (err) {
        console.error('Save profile error:', err);
        showToast('Failed to save profile', 'error');
    }
}

async function savePersonality() {
    try {
        const fd = new FormData();
        fd.append('formality', document.getElementById('formality').value / 100);
        fd.append('enthusiasm', document.getElementById('enthusiasm').value / 100);
        fd.append('verbosity', document.getElementById('verbosity').value / 100);

        const res = await fetch(`${API_BASE}/profile/${userId}/update`, {
            method: 'POST',
            body: fd
        });

        const data = await res.json();

        if (data.success) {
            showToast('Personality updated', 'success');
        }
    } catch (err) {
        console.error('Save personality error:', err);
        showToast('Failed to update personality', 'error');
    }
}

/* ==================== CHAT ==================== */

function addWelcomeMessage() {
    const message = `Hello **${username}**! I'm Nova, your AI companion. I'll remember our conversations and adapt to you over time. What would you like to talk about?`;
    addMessageToUI(message, 'ai', true);
}

function addMessageToUI(text, sender, animate = true) {
    const chatBox = document.getElementById('chat-box');

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    if (!animate) messageDiv.style.animation = 'none';

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = sender === 'ai' ? 'N' : (username?.[0]?.toUpperCase() || 'U');

    const content = document.createElement('div');
    content.className = 'message-content';

    if (sender === 'ai') {
        content.innerHTML = marked.parse(text);
    } else {
        content.textContent = text;
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);

    chatBox.appendChild(messageDiv);

    if (animate) {
        scrollToBottom();

        // Auto-read if enabled and it's an AI message
        if (sender === 'ai' && isAutoReadEnabled()) {
            speakText(text);
        }
    }
}

function showTyping() {
    document.getElementById('typing-indicator').classList.remove('hidden');
    scrollToBottom();
}

function hideTyping() {
    document.getElementById('typing-indicator').classList.add('hidden');
}

async function sendMessage() {
    if (!userId || !currentThreadId) {
        showToast('Please wait, loading...', 'error');
        return;
    }

    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (!message) return;

    const connected = await checkBackendConnection();
    if (!connected) {
        showToast('Backend offline. Please start the server.', 'error');
        return;
    }

    addMessageToUI(message, 'user');
    input.value = '';
    autoResizeTextarea();

    showTyping();
    document.getElementById('send-btn').disabled = true;

    try {
        const fd = new FormData();
        fd.append('user_id', userId);
        fd.append('message', message);
        fd.append('thread_id', currentThreadId);

        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            body: fd
        });

        if (!res.ok) {
            throw new Error(`Server error: ${res.status}`);
        }

        const data = await res.json();

        hideTyping();

        if (data.success) {
            addMessageToUI(data.reply, 'ai');

            // Auto-rename thread based on first message
            await autoRenameThread(message);

            // Reload threads to update message count
            await loadThreads();
        } else {
            throw new Error(data.detail || 'Unknown error');
        }
    } catch (err) {
        hideTyping();
        console.error('Send message error:', err);
        addMessageToUI(`⚠️ Error: ${err.message}`, 'ai');
        showToast('Failed to send message', 'error');
    } finally {
        document.getElementById('send-btn').disabled = false;
    }
}

async function autoRenameThread(firstMessage) {
    const thread = threads.find(t => t.thread_id === currentThreadId);
    if (!thread) return;

    const isDefaultName = thread.title === 'New Chat';
    const messageCount = thread.message_count || 0;

    if (isDefaultName && messageCount <= 1) {
        const title = firstMessage.length > 35 ? firstMessage.slice(0, 35) + '...' : firstMessage;

        try {
            const fd = new FormData();
            fd.append('title', title);

            await fetch(`${API_BASE}/threads/${userId}/${currentThreadId}`, {
                method: 'PUT',
                body: fd
            });

            document.getElementById('current-thread-title').textContent = title;
        } catch (err) {
            console.warn('Auto-rename failed', err);
        }
    }
}

/* ==================== UI HELPERS ==================== */

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('hidden');
}

function handleEnterKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    const textarea = document.getElementById('message-input');
    if (!textarea) return;

    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
}

function scrollToBottom() {
    const chatBox = document.getElementById('chat-box');
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/* ==================== SETTINGS MODAL ==================== */

function openSettings() {
    document.getElementById('settings-modal').classList.remove('hidden');
    loadVoices(); // Reload voices when opening
}

function closeSettings() {
    document.getElementById('settings-modal').classList.add('hidden');
}

function updateFormalityDisplay(value) {
    document.getElementById('formality-display').textContent = `${Math.round(value)}%`;
}

function updateEnthusiasmDisplay(value) {
    document.getElementById('enthusiasm-display').textContent = `${Math.round(value)}%`;
}

function updateVerbosityDisplay(value) {
    document.getElementById('verbosity-display').textContent = `${Math.round(value)}%`;
}

/* ==================== KEYBOARD SHORTCUTS ==================== */

document.addEventListener('keydown', (e) => {
    // Login screen shortcuts
    if (!document.getElementById('auth-screen').classList.contains('hidden')) {
        if (e.key === 'Enter') {
            if (document.getElementById('login-form').classList.contains('active')) {
                handleLogin();
            } else {
                handleRegister();
            }
        }
    }
});