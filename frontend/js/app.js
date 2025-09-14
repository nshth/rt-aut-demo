        // Sample session data
        const sessions = {
            'session-1': {
                id: 'session-1',
                customer: '+94 77 123 4567',
                status: 'need-human-support',
                lastMessage: 'I want to cancel my order and get a refund. This is urgent.',
                time: '2 min ago',
                messages: [
                    { sender: 'customer', text: 'I want to cancel my order and get a refund. This is urgent.', time: '14:32' },
                    { sender: 'agent', text: 'I understand your concern. Let me connect you with a human representative who can help you with the cancellation and refund process.', time: '14:33' },
                    { sender: 'customer', text: 'Thank you, how long will it take?', time: '14:34' }
                ],
                humanFirstTime: true
            },
            'session-2': {
                id: 'session-2',
                customer: '+94 77 987 6543',
                status: 'under-human-control',
                lastMessage: 'Thanks for the help with my order status.',
                time: '5 min ago',
                messages: [
                    { sender: 'customer', text: 'Can you check my order status please?', time: '14:20' },
                    { sender: 'human', text: 'Of course! Let me check that for you right away.', time: '14:21' },
                    { sender: 'human', text: 'Your order #12345 has been shipped and will arrive tomorrow by 2 PM.', time: '14:22' },
                    { sender: 'customer', text: 'Thanks for the help with my order status.', time: '14:23' }
                ],
                humanFirstTime: false
            }
        };

        let currentSession = null;

        // Filter functionality
        document.querySelectorAll('.filter-tab').forEach(tab => {
            tab.addEventListener('click', function() {
                document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
                this.classList.add('active');
                
                const filter = this.getAttribute('data-filter');
                filterSessions(filter);
            });
        });

        function filterSessions(filter) {
            const sessionItems = document.querySelectorAll('.session-item');
            sessionItems.forEach(item => {
                const sessionId = item.getAttribute('data-session-id');
                const session = sessions[sessionId];
                
                if (filter === 'all' || 
                    (filter === 'need-human-support' && item.classList.contains('need-support')) ||
                    (filter === 'under-human-control' && item.classList.contains('under-human')) ||
                    (filter === 'under-agent-control' && item.classList.contains('under-agent'))) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }

        // Session selection
        document.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', function() {
                document.querySelectorAll('.session-item').forEach(i => i.classList.remove('active'));
                this.classList.add('active');
                
                const sessionId = this.getAttribute('data-session-id');
                loadSession(sessionId);
            });
        });

        function loadSession(sessionId) {
            const session = sessions[sessionId];
            if (!session) return;
            
            currentSession = session;
            
            // Show chat area
            const chatArea = document.getElementById('chatArea');
            chatArea.classList.add('has-session');
            
            // Update header
            document.getElementById('chatHeader').style.display = 'flex';
            document.getElementById('chatTitle').textContent = session.customer;
            
            const statusEl = document.getElementById('sessionStatus');
            statusEl.textContent = getStatusDisplayText(session.status);
            statusEl.className = 'session-status status-' + session.status.replace('-', '-');
            
            // Load messages
            loadMessages(session.messages);
            
            // Show appropriate input/actions
            if (session.status === 'need-human-support' && session.humanFirstTime) {
                chatArea.classList.add('show-actions');
                chatArea.classList.remove('show-input');
            } else if (session.status === 'under-human-control') {
                chatArea.classList.add('show-input');
                chatArea.classList.remove('show-actions');
            } else {
                chatArea.classList.remove('show-input', 'show-actions');
            }
        }

        function loadMessages(messages) {
            const messagesContainer = document.getElementById('chatMessages');
            messagesContainer.innerHTML = '';
            
            messages.forEach(message => {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message message-${message.sender}`;
                messageDiv.innerHTML = `
                    <div class="message-sender">${capitalizeFirst(message.sender)}</div>
                    <div class="message-bubble">${message.text}</div>
                    <div class="message-time">${message.time}</div>
                `;
                messagesContainer.appendChild(messageDiv);
            });
            
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function getStatusDisplayText(status) {
            switch(status) {
                case 'need-human-support': return 'Need Human Support';
                case 'under-human-control': return 'Under Human Control';
                case 'under-agent-control': return 'Under Agent Control';
                default: return status;
            }
        }

        function capitalizeFirst(str) {
            return str.charAt(0).toUpperCase() + str.slice(1);
        }

        // Human action buttons
        function replyAsHuman() {
            if (currentSession) {
                currentSession.humanFirstTime = false;
                document.getElementById('chatArea').classList.add('show-input');
                document.getElementById('chatArea').classList.remove('show-actions');
                document.getElementById('messageInput').focus();
            }
        }

        function handleAsHuman() {
            if (currentSession) {
                // Send system message
                const systemMessage = {
                    sender: 'system',
                    text: 'One of our staff will contact you via WhatsApp: +94 77 912 3456',
                    time: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })
                };
                
                currentSession.messages.push(systemMessage);
                currentSession.status = 'under-human-control';
                currentSession.humanFirstTime = false;
                
                // Update UI
                loadMessages(currentSession.messages);
                document.getElementById('sessionStatus').textContent = 'Under Human Control';
                document.getElementById('chatArea').classList.add('show-input');
                document.getElementById('chatArea').classList.remove('show-actions');
                
                // Update sidebar status
                const sessionItem = document.querySelector(`[data-session-id="${currentSession.id}"]`);
                sessionItem.className = 'session-item under-human active';
                sessionItem.querySelector('.status-badge').className = 'status-badge status-under-human';
                sessionItem.querySelector('.status-badge').textContent = 'Under Human Control';
                
                document.getElementById('messageInput').focus();
            }
        }

        // Send message
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (!message || !currentSession) return;
            
            const newMessage = {
                sender: 'human',
                text: message,
                time: new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit' })
            };
            
            currentSession.messages.push(newMessage);
            currentSession.lastMessage = message;
            
            // Update UI
            loadMessages(currentSession.messages);
            
            // Update sidebar
            const sessionItem = document.querySelector(`[data-session-id="${currentSession.id}"]`);
            sessionItem.querySelector('.last-message').textContent = message;
            
            input.value = '';
        }

        // Enter key to send
        document.getElementById('messageInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // WebSocket connection and real-time updates
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnectAttempts = 5;
        
        function initWebSocket() {
            // Get admin token (in real app, this would come from login/auth)
            const token = localStorage.getItem('admin_token') || 'demo-admin-token-12345';
            const wsUrl = `ws://localhost:8000/ws/hitl?token=${token}`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function(event) {
                console.log('✅ WebSocket connected');
                reconnectAttempts = 0;
                
                // Subscribe to current session if one is open
                if (currentSession) {
                    subscribeToSession(currentSession.id);
                }
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onclose = function(event) {
                console.log('❌ WebSocket disconnected');
                
                // Attempt to reconnect
                if (reconnectAttempts < maxReconnectAttempts) {
                    setTimeout(() => {
                        reconnectAttempts++;
                        console.log(`🔄 Reconnecting... (${reconnectAttempts}/${maxReconnectAttempts})`);
                        initWebSocket();
                    }, 2000 * reconnectAttempts);
                }
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
            };
        }
        
        function handleWebSocketMessage(data) {
            console.log('📥 WebSocket message:', data);
            
            switch(data.type) {
                case 'sessions:counts':
                    updateSessionCounts(data.counts);
                    break;
                    
                case 'session:update':
                    updateSessionInSidebar(data);
                    if (currentSession && currentSession.id === data.session_id) {
                        updateCurrentSessionStatus(data.status);
                    }
                    break;
                    
                case 'message:created':
                    if (currentSession && currentSession.id === data.session_id) {
                        addMessageToChat(data.message);
                    }
                    break;
                    
                case 'pong':
                    // Handle ping/pong for connection health
                    break;
            }
        }
        
        function subscribeToSession(sessionId) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'subscribe_session',
                    session_id: sessionId
                }));
            }
        }
        
        function unsubscribeFromSession(sessionId) {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'unsubscribe_session', 
                    session_id: sessionId
                }));
            }
        }
        
        function updateSessionCounts(counts) {
            document.querySelector('[data-filter="all"] .filter-count').textContent = counts.all || 0;
            document.querySelector('[data-filter="under-agent-control"] .filter-count').textContent = counts.agent_control || 0;
            document.querySelector('[data-filter="under-human-control"] .filter-count').textContent = counts.human_control || 0;
            document.querySelector('[data-filter="need-human-support"] .filter-count').textContent = counts.need_human_support || 0;
        }
        
        function updateSessionInSidebar(data) {
            const sessionItem = document.querySelector(`[data-session-id="${data.session_id}"]`);
            if (!sessionItem) return;
            
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
            
            // Update last message if provided
            if (data.last_message) {
                const lastMessageEl = sessionItem.querySelector('.last-message');
                if (lastMessageEl) {
                    lastMessageEl.textContent = data.last_message;
                }
            }
        }

        // Initialize
        document.addEventListener('DOMContentLoaded', function() {
            initWebSocket();
        });
