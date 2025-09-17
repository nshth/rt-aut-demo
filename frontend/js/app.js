// Global variables
let ws = null;
let sessions = {};
let currentSession = null;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

// Initialize everything when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('ðŸš€ Dashboard initializing...');
    
    // Check for ephemeral token first
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');
    
    if (token) {
        validateEphemeralToken(token);
    } else {
        initializeDashboard();
    }
});

function initializeDashboard() {
    setupEventListeners();
    initWebSocket();
    loadSessions();
}

function setupEventListeners() {
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            const filter = this.getAttribute('data-filter');
            filterSessions(filter);
        });
    });

    // Message input
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
}

function initWebSocket() {
    const token = "demo-admin-token-12345";
    const wsUrl = `ws://localhost:8000/ws/hitl?token=${token}`;
    
    console.log('ðŸ”Œ Connecting to WebSocket:', wsUrl);
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function(event) {
        console.log('âœ… WebSocket connected');
        reconnectAttempts = 0;
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        console.log('ðŸ“¥ WebSocket message:', data);
        handleWebSocketMessage(data);
    };
    
    ws.onclose = function(event) {
        console.log('âŒ WebSocket disconnected');
        if (reconnectAttempts < maxReconnectAttempts) {
            setTimeout(() => {
                reconnectAttempts++;
                console.log(`ðŸ”„ Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
                initWebSocket();
            }, 2000 * reconnectAttempts);
        }
    };
    
    ws.onerror = function(error) {
        console.error('âŒ WebSocket error:', error);
    };
}

function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'sessions:counts':
            updateSessionCounts(data.counts);
            break;
        case 'session:update':
            updateSessionInSidebar(data);
            break;
        case 'message:created':
            if (currentSession && currentSession.id === data.session_id) {
                addMessageToChat(data.message);
            }
            break;
        case 'pong':
            console.log('ðŸ“ Pong received');
            break;
    }
}

async function loadSessions() {
    try {
        console.log('ðŸ“¥ Loading sessions...');
        const response = await fetch('/api/hitl/sessions');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const sessionList = await response.json();
        console.log('âœ… Sessions loaded:', sessionList.length);
        
        // Convert to sessions object
        sessions = {};
        sessionList.forEach(session => {
            sessions[session.session_id] = session;
        });
        
        updateSessionSidebar(sessionList);
        updateSessionCounts();
        
    } catch (error) {
        console.error('âŒ Failed to load sessions:', error);
        showError('Failed to load sessions: ' + error.message);
    }
}

function updateSessionSidebar(sessionList) {
    const sessionsList = document.querySelector('.sessions-list');
    if (!sessionsList) {
        console.error('Sessions list container not found');
        return;
    }
    
    sessionsList.innerHTML = '';
    
    if (sessionList.length === 0) {
        sessionsList.innerHTML = '<div style="padding: 20px; text-align: center; color: #6b7280;">No active sessions</div>';
        return;
    }
    
    sessionList.forEach(session => {
        const sessionItem = document.createElement('div');
        sessionItem.className = `session-item ${getStatusClass(session.status)}`;
        sessionItem.setAttribute('data-session-id', session.session_id);
        
        const timeAgo = formatTimeAgo(session.updated_at);
        const preview = session.last_message || 'No messages yet';
        
        sessionItem.innerHTML = `
            <div class="session-header">
                <span class="customer-number">${session.customer_number || 'Unknown'}</span>
                <span class="session-time">${timeAgo}</span>
            </div>
            <div class="last-message">${preview}</div>
            <div class="status-badge ${getBadgeStatusClass(session.status)}">${getStatusDisplayText(session.status)}</div>
        `;
        
        sessionItem.addEventListener('click', () => loadSession(session.session_id));
        sessionsList.appendChild(sessionItem);
    });
}

async function loadSession(sessionId) {
    try {
        console.log('ðŸ“– Loading session:', sessionId);
        
        // Mark as active in sidebar
        document.querySelectorAll('.session-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-session-id="${sessionId}"]`)?.classList.add('active');
        
        const response = await fetch(`/api/hitl/sessions/${sessionId}/history`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const messages = await response.json();
        const sessionData = sessions[sessionId];
        
        currentSession = {
            id: sessionId,
            ...sessionData,
            messages: messages
        };
        
        // Update UI
        showChatArea();
        loadMessages(messages);
        setupSessionControls();
        
        // Subscribe to session updates via WebSocket
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'subscribe_session',
                session_id: sessionId
            }));
        }
        
    } catch (error) {
        console.error('âŒ Failed to load session:', error);
        showError('Failed to load session: ' + error.message);
    }
}

function showChatArea() {
    const chatArea = document.getElementById('chatArea');
    const chatHeader = document.getElementById('chatHeader');
    const chatTitle = document.getElementById('chatTitle');
    const sessionStatus = document.getElementById('sessionStatus');
    
    chatArea.classList.add('has-session');
    chatHeader.style.display = 'flex';
    chatTitle.textContent = currentSession.customer_number || 'Customer Chat';
    
    const statusText = getStatusDisplayText(currentSession.status);
    sessionStatus.textContent = statusText;
    sessionStatus.className = `session-status ${getBadgeStatusClass(currentSession.status)}`;
}

function loadMessages(messages) {
    const messagesContainer = document.getElementById('chatMessages');
    messagesContainer.innerHTML = '';
    
    messages.forEach(message => {
        addMessageToDOM(message);
    });
    
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function addMessageToDOM(message) {
    const messagesContainer = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${message.sender}`;
    
    const time = formatMessageTime(message.timestamp);
    const senderName = message.sender.charAt(0).toUpperCase() + message.sender.slice(1);
    
    messageDiv.innerHTML = `
        <div class="message-sender">${senderName}</div>
        <div class="message-bubble">${escapeHtml(message.text)}</div>
        <div class="message-time">${time}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function setupSessionControls() {
    const chatArea = document.getElementById('chatArea');
    
    // Clear previous states
    chatArea.classList.remove('show-input', 'show-actions');
    
    if (currentSession.status === 'need-human-support') {
        chatArea.classList.add('show-actions');
    } else if (currentSession.status === 'under-human-control') {
        chatArea.classList.add('show-input');
    }
}

// Human action functions
function replyAsHuman() {
    if (currentSession) {
        const chatArea = document.getElementById('chatArea');
        chatArea.classList.add('show-input');
        chatArea.classList.remove('show-actions');
        document.getElementById('messageInput').focus();
    }
}

async function handleAsHuman() {
    if (!currentSession) return;
    
    try {
        const response = await fetch(`/api/hitl/sessions/${currentSession.id}/takeover`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (response.ok) {
            console.log('âœ… Session taken over');
        }
    } catch (error) {
        console.error('âŒ Failed to take over session:', error);
        showError('Failed to take over session');
    }
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message || !currentSession) return;
    
    try {
        const response = await fetch(`/api/hitl/sessions/${currentSession.id}/reply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: message })
        });
        
        if (response.ok) {
            input.value = '';
            console.log('âœ… Message sent');
            // Message will appear via WebSocket
        }
    } catch (error) {
        console.error('âŒ Failed to send message:', error);
        showError('Failed to send message');
    }
}

// Utility functions
function getStatusClass(status) {
    switch(status) {
        case 'need-human-support': return 'need-support';
        case 'under-human-control': return 'under-human';
        case 'under-agent-control': return 'under-agent';
        default: return 'under-agent';
    }
}

function getBadgeStatusClass(status) {
    switch(status) {
        case 'need-human-support': return 'status-need-support';
        case 'under-human-control': return 'status-under-human';
        case 'under-agent-control': return 'status-under-agent';
        default: return 'status-under-agent';
    }
}

function getStatusDisplayText(status) {
    switch(status) {
        case 'need-human-support': return 'Need Human Support';
        case 'under-human-control': return 'Under Human Control';
        case 'under-agent-control': return 'Under Agent Control';
        default: return 'Unknown Status';
    }
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return date.toLocaleDateString();
}

function formatMessageTime(timestamp) {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { 
        hour12: false, 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function updateSessionCounts(counts) {
    if (!counts) {
        // Calculate from current sessions
        const sessionList = Object.values(sessions);
        counts = {
            all: sessionList.length,
            agent_control: sessionList.filter(s => s.status === 'under-agent-control').length,
            human_control: sessionList.filter(s => s.status === 'under-human-control').length,
            need_human_support: sessionList.filter(s => s.status === 'need-human-support').length
        };
    }
    
    document.querySelector('[data-filter="all"] .filter-count').textContent = counts.all || 0;
    document.querySelector('[data-filter="under-agent-control"] .filter-count').textContent = counts.agent_control || 0;
    document.querySelector('[data-filter="under-human-control"] .filter-count').textContent = counts.human_control || 0;
    document.querySelector('[data-filter="need-human-support"] .filter-count').textContent = counts.need_human_support || 0;
}

function filterSessions(filter) {
    const sessionItems = document.querySelectorAll('.session-item');
    sessionItems.forEach(item => {
        const sessionId = item.getAttribute('data-session-id');
        const session = sessions[sessionId];
        
        if (filter === 'all' || 
            (filter === 'need-human-support' && session?.status === 'need-human-support') ||
            (filter === 'under-human-control' && session?.status === 'under-human-control') ||
            (filter === 'under-agent-control' && session?.status === 'under-agent-control')) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function showError(message) {
    console.error('âŒ', message);
    // You can implement a toast/notification system here
    alert(message); // Simple fallback
}

function validateEphemeralToken(token) {
    fetch(`/api/hitl/auth/ephemeral?token=${token}`)
        .then(response => response.json())
        .then(data => {
            if (data.valid && data.session_id) {
                console.log('âœ… Valid ephemeral token, opening session:', data.session_id);
                initializeDashboard();
                setTimeout(() => {
                    loadSession(data.session_id);
                }, 1000);
            } else {
                console.error('âŒ Invalid ephemeral token');
                alert('Invalid or expired link');
                initializeDashboard();
            }
        })
        .catch(error => {
            console.error('âŒ Token validation failed:', error);
            initializeDashboard();
        });
}

// WebSocket message handlers
function updateSessionInSidebar(data) {
    const sessionItem = document.querySelector(`[data-session-id="${data.session_id}"]`);
    if (sessionItem) {
        // Update status classes
        sessionItem.className = `session-item ${getStatusClass(data.status)}`;
        if (currentSession && currentSession.id === data.session_id) {
            sessionItem.classList.add('active');
        }
        
        // Update status badge
        const statusBadge = sessionItem.querySelector('.status-badge');
        if (statusBadge) {
            statusBadge.className = `status-badge ${getBadgeStatusClass(data.status)}`;
            statusBadge.textContent = getStatusDisplayText(data.status);
        }
        
        // Update preview
        if (data.preview) {
            const lastMessage = sessionItem.querySelector('.last-message');
            if (lastMessage) {
                lastMessage.textContent = data.preview;
            }
        }
    }
    
    // Update current session if it matches
    if (currentSession && currentSession.id === data.session_id) {
        currentSession.status = data.status;
        setupSessionControls();
        
        const sessionStatus = document.getElementById('sessionStatus');
        if (sessionStatus) {
            sessionStatus.textContent = getStatusDisplayText(data.status);
            sessionStatus.className = `session-status ${getBadgeStatusClass(data.status)}`;
        }
    }
}

function addMessageToChat(message) {
    addMessageToDOM(message);
    
    // Update current session messages
    if (currentSession) {
        currentSession.messages.push(message);
    }
}