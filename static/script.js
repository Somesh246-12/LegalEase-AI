document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Tabbed Interface for Upload/Paste ---
    const tabs = document.querySelectorAll('.tab-button');
    const panels = document.querySelectorAll('.input-panel');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            const panelId = tab.getAttribute('data-tab');
            document.getElementById(panelId).classList.add('active');
        });
    });

    // --- 2. File Upload Area Interaction ---
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-input');
    if (uploadBox && fileInput) {
        uploadBox.addEventListener('click', () => {
            fileInput.click();
        });
        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                uploadBox.querySelector('h3').textContent = fileInput.files[0].name;
                uploadBox.querySelector('p').textContent = 'File selected. Ready to simplify!';
            }
        });
    }

    // --- 3. Form Submission Loader ---
    const uploadForm = document.getElementById('upload-form');
    const loader = document.getElementById('loader');
    if (uploadForm && loader) {
        uploadForm.addEventListener('submit', () => {
            loader.style.display = 'flex';
        });
    }

    // --- 4. Chatbot Widget Functionality ---
    const chatWindow = document.getElementById('chat-window');
    const chatToggleButton = document.getElementById('chat-toggle-button');
    const chatCloseButton = document.getElementById('chat-close-button');
    const chatInput = document.getElementById('chat-input');
    const chatSendButton = document.getElementById('chat-send-button');
    const chatBody = document.getElementById('chat-body');

    if (chatToggleButton && chatWindow) {
        chatToggleButton.addEventListener('click', () => {
            chatWindow.style.display = chatWindow.style.display === 'flex' ? 'none' : 'flex';
        });
    }
    if (chatCloseButton && chatWindow) {
        chatCloseButton.addEventListener('click', () => {
            chatWindow.style.display = 'none';
        });
    }

    function addMessage(text, sender) {
        if (!chatBody) return;
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;
        messageDiv.textContent = text;
        chatBody.appendChild(messageDiv);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    async function sendMessage() {
        const userInput = chatInput ? chatInput.value.trim() : '';
        if (userInput === '') return;

        addMessage(userInput, 'user');
        if (chatInput) chatInput.value = '';

        const docCtxEl = document.getElementById('document-context');
        const documentContext = docCtxEl ? docCtxEl.textContent : '';

        const messages = chatBody ? Array.from(chatBody.querySelectorAll('.chat-message')).map(msg => ({
            role: msg.classList.contains('user') ? 'user' : 'model',
            text: msg.textContent,
        })) : [];

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    history: messages,
                    document_text: documentContext
                }),
            });
            const data = await response.json();
            addMessage(data.response, 'bot');
        } catch (error) {
            addMessage("Sorry, I couldn't get a response right now.", 'bot');
            console.error('Chat error:', error);
        }
    }

    if (chatSendButton) {
        chatSendButton.addEventListener('click', sendMessage);
    }
    if (chatInput) {
        chatInput.addEventListener('keypress', (event) => {
            if (event.key === 'Enter') {
                sendMessage();
            }
        });
    }

    // --- 5. "Why LegalEase?" Documentation Modal ---
    const docsModal = document.getElementById('docs-modal');
    const whyLegaleaseBtn = document.getElementById('why-legalease-btn');
    const docsCloseBtn = document.getElementById('docs-close-btn');

    if (whyLegaleaseBtn) {
        whyLegaleaseBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (docsModal) docsModal.style.display = 'flex';
        });
    }
    if (docsCloseBtn) {
        docsCloseBtn.addEventListener('click', () => {
            if (docsModal) docsModal.style.display = 'none';
        });
    }

    // --- 6. Functions to run ONLY if results are on the page ---
    async function loadRiskData() {
        try {
            const res = await fetch('/risks.json');
            const data = await res.json();
            const stats = data.stats || { severity: {}, type: {} };
            const sev = stats.severity || {};
            const sevCtx = document.getElementById('severityChart');
            if (sevCtx) {
                new Chart(sevCtx, {
                    type: 'doughnut',
                    data: {
                        labels: ['High', 'Medium', 'Low'],
                        datasets: [{
                            data: [sev.high || 0, sev.medium || 0, sev.low || 0],
                            backgroundColor: ['#ff6b6b', '#ffd166', '#06d6a0'],
                            hoverOffset: 6,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        cutout: '60%',
                        plugins: { legend: { position: 'bottom' } }
                    }
                });
            }
        } catch (e) {
            console.error('Charts error', e);
        }
    }

    /**
     * Finds all risk items on the page and makes their headers clickable
     * to show/hide the detailed risk body.
     */
    function initializeRiskAccordion() {
        const riskItems = document.querySelectorAll('.risk-item');
        if (!riskItems.length) return;

        riskItems.forEach(item => {
            const header = item.querySelector('.risk-header');
            if (header) {
                header.addEventListener('click', () => {
                    item.classList.toggle('active');
                });
                header.setAttribute('title', 'Click to expand/collapse details');
            }
        });
    }

    // --- Initialization logic ---
    // Check if the results div exists by checking the flask variable
    const hasResult = document.querySelector('.main-content.container');
    if (hasResult) {
        loadRiskData();
        initializeRiskAccordion();
    }

});