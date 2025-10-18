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
        uploadForm.addEventListener('submit', async (event) => {
            // 1. Prevent the form from submitting immediately
            event.preventDefault();
    
            // 2. Show the main loader
            const loaderText = document.getElementById('loader-text');
            loaderText.textContent = 'Analyzing document integrity...'; // Updated text
            loader.style.display = 'flex';
    
            // 3. Send the form data to our authenticity endpoint
            try {
                const formData = new FormData(uploadForm);
                const response = await fetch('/check-authenticity', {
                    method: 'POST',
                    body: formData,
                });
    
                if (!response.ok) {
                    throw new Error('Server error during pre-check.');
                }
    
                const report = await response.json();
    
                // 4. Hide the loader and show the correct modal
                loader.style.display = 'none';
                
                if (report.verdict === 'PAGE_LIMIT_EXCEEDED') {
                    displayPageLimitModal(report);
                } 
                // --- NEW: Handle BLURRY verdict ---
                else if (report.verdict === 'BLURRY') {
                    displayBlurryModal(report);
                } 
                // --- END NEW ---
                else {
                    // All checks passed, show normal authenticity modal
                    displayAuthenticityModal(report);
                }
    
            } catch (error) {
                console.error("Pre-check failed:", error);
                loader.style.display = 'none';
                alert("Could not perform the document pre-check. Please try again.");
            }
        });
    }
    // In your static/script.js file

// In your static/script.js file

function displayAuthenticityModal(report) {
    const modal = document.getElementById('authenticity-modal');
    const verdictEl = document.getElementById('auth-verdict');
    const summaryEl = document.getElementById('auth-summary');
    
    // --- Populate the content ---
    verdictEl.textContent = report.verdict;
    
    // Set basic summary
    summaryEl.textContent = report.summary;
    
    // Handle logo analysis display
    const logoAnalysisSection = document.getElementById('logo-analysis-section');
    const logoAnalysisContent = document.getElementById('logo-analysis-content');
    
    if (report.logo_analysis && report.logo_analysis.total_logos_detected > 0) {
        const logoAnalysis = report.logo_analysis;
        
        let logoHtml = `<div class="logo-analysis-stats">
            <p><strong>Total logos detected:</strong> ${logoAnalysis.total_logos_detected}</p>
            <p><strong>Logo authenticity score:</strong> ${logoAnalysis.overall_logo_authenticity_score}/100</p>
        </div>`;
        
        if (logoAnalysis.authentic_logos.length > 0) {
            logoHtml += '<div class="logo-category"><h4>✅ Authentic Logos</h4>';
            logoAnalysis.authentic_logos.forEach(logo => {
                logoHtml += `<div class="logo-item">
                    <span class="logo-status-icon">✅</span>
                    <span class="logo-name">${logo.logo_name}</span>
                    <span class="logo-company">(${logo.company})</span>
                </div>`;
            });
            logoHtml += '</div>';
        }
        
        if (logoAnalysis.suspicious_logos.length > 0) {
            logoHtml += '<div class="logo-category"><h4>⚠️ Suspicious Logos</h4>';
            logoAnalysis.suspicious_logos.forEach(logo => {
                logoHtml += `<div class="logo-item">
                    <span class="logo-status-icon">⚠️</span>
                    <span class="logo-name">${logo.logo_name}</span>
                    <span class="logo-company">(${logo.company})</span>
                </div>`;
            });
            logoHtml += '</div>';
        }
        
        if (logoAnalysis.unknown_logos.length > 0) {
            logoHtml += '<div class="logo-category"><h4>❓ Unknown Logos</h4>';
            logoAnalysis.unknown_logos.forEach(logo => {
                logoHtml += `<div class="logo-item">
                    <span class="logo-status-icon">❓</span>
                    <span class="logo-name">${logo.logo_name}</span>
                </div>`;
            });
            logoHtml += '</div>';
        }
        
        if (logoAnalysis.logo_risk_factors.length > 0) {
            logoHtml += `<div class="logo-risk-factors">
                <strong>Risk factors:</strong> ${logoAnalysis.logo_risk_factors.join(', ')}
            </div>`;
        }
        
        logoAnalysisContent.innerHTML = logoHtml;
        logoAnalysisSection.style.display = 'block';
    } else {
        logoAnalysisSection.style.display = 'none';
    }

    // --- NEW: Add a class for CSS highlighting ---
    // First, remove any classes from a previous analysis
    verdictEl.classList.remove('verdict-FAKE', 'verdict-SUSPICIOUS', 'verdict-REAL');
    // Then, add the correct class based on the new verdict
    if (report.verdict) {
        verdictEl.classList.add(`verdict-${report.verdict}`);
    }

    // Show the modal
    modal.style.display = 'flex';

    // --- Button handler logic (this part remains the same) ---
    const uploadForm = document.getElementById('upload-form');
    const continueBtn = document.getElementById('auth-continue-btn');
    const cancelBtn = document.getElementById('auth-cancel-btn');

    const continueHandler = () => {
        modal.style.display = 'none';
        
        // Show loader with analysis message
        const loaderText = document.getElementById('loader-text');
        loaderText.textContent = 'Analyzing your document... This may take a moment.';
        loader.style.display = 'flex';
        
        // Submit the form for actual analysis
        uploadForm.submit();
    };

    const cancelHandler = () => {
        modal.style.display = 'none';
    };
    
    const newContinueBtn = continueBtn.cloneNode(true);
    continueBtn.parentNode.replaceChild(newContinueBtn, continueBtn);
    newContinueBtn.addEventListener('click', continueHandler);

    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    newCancelBtn.addEventListener('click', cancelHandler);
}
function displayBlurryModal(report) {
    const modal = document.getElementById('authenticity-modal');
    const verdictEl = document.getElementById('auth-verdict');
    const summaryEl = document.getElementById('auth-summary');
    
    // Update modal title
    const modalHeader = modal.querySelector('.modal-header h3');
    if (modalHeader) {
        modalHeader.textContent = '⚠️ Document is Blurry';
    }
    
    // Populate the content
    verdictEl.textContent = 'BLURRY';
    verdictEl.className = 'auth-verdict verdict-BLURRY'; // Add new CSS class
    
    // Use the detailed summary from the backend
    summaryEl.textContent = report.summary || "The uploaded document or image is too blurry. Please upload a clearer version.";

    // Hide the logo analysis section, it's not relevant here
    const logoAnalysisSection = document.getElementById('logo-analysis-section');
    if (logoAnalysisSection) {
        logoAnalysisSection.style.display = 'none';
    }

    // Show the modal
    modal.style.display = 'flex';

    // --- Button handler logic ---
    // We want the buttons to allow for a re-upload
    
    const continueBtn = document.getElementById('auth-continue-btn');
    const cancelBtn = document.getElementById('auth-cancel-btn');

    const continueHandler = () => {
        modal.style.display = 'none';
        // Clear the file input to allow re-upload
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.value = ''; 
        }
        // Reset upload area text
        const uploadBox = document.getElementById('upload-box');
        if (uploadBox) {
            uploadBox.querySelector('h3').textContent = 'Drag & Drop Your File Here';
            uploadBox.querySelector('p').textContent = 'or click to select a file (PDF, TXT, JPG, PNG)';
        }
    };

    const cancelHandler = () => {
        modal.style.display = 'none';
    };
    
    // Re-bind events to prevent old listeners from stacking
    const newContinueBtn = continueBtn.cloneNode(true);
    continueBtn.parentNode.replaceChild(newContinueBtn, continueBtn);
    newContinueBtn.textContent = 'Upload New Document'; // Change button text
    newContinueBtn.addEventListener('click', continueHandler);

    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    newCancelBtn.textContent = 'Cancel';
    newCancelBtn.addEventListener('click', cancelHandler);
}

function displayPageLimitModal(report) {
    const modal = document.getElementById('authenticity-modal');
    const verdictEl = document.getElementById('auth-verdict');
    const summaryEl = document.getElementById('auth-summary');
    
    // Update modal title
    const modalHeader = modal.querySelector('.modal-header h3');
    if (modalHeader) {
        modalHeader.textContent = '📄 Document Page Limit Exceeded';
    }
    
    // Populate the content with better messaging
    verdictEl.textContent = 'PAGE LIMIT EXCEEDED';
    verdictEl.className = 'auth-verdict verdict-PAGE_LIMIT_EXCEEDED';
    
    // Create a more detailed message
    const pageDetails = report.page_details || {};
    const pageCount = pageDetails.page_count || 0;
    const maxPages = pageDetails.max_pages || 15;
    
    let detailedMessage = `Your document exceeds the maximum page limit.\n\n`;
    detailedMessage += `Document Pages: ${pageCount}\n`;
    detailedMessage += `Maximum Allowed: ${maxPages}\n\n`;
    detailedMessage += `Recommendation: ${report.summary}`;
    
    summaryEl.textContent = detailedMessage;

    // Show the modal
    modal.style.display = 'flex';

    // Update button handlers
    const uploadForm = document.getElementById('upload-form');
    const continueBtn = document.getElementById('auth-continue-btn');
    const cancelBtn = document.getElementById('auth-cancel-btn');

    const continueHandler = () => {
        modal.style.display = 'none';
        // Clear the file input to allow re-upload
        const fileInput = document.getElementById('file-input');
        if (fileInput) {
            fileInput.value = '';
        }
        // Reset upload area text
        const uploadBox = document.getElementById('upload-box');
        if (uploadBox) {
            uploadBox.querySelector('h3').textContent = 'Drag & Drop Your File Here';
            uploadBox.querySelector('p').textContent = 'or click to select a file (PDF, TXT, JPG, PNG)';
        }
    };

    const cancelHandler = () => {
        modal.style.display = 'none';
    };
    
    const newContinueBtn = continueBtn.cloneNode(true);
    continueBtn.parentNode.replaceChild(newContinueBtn, continueBtn);
    newContinueBtn.textContent = 'Upload New Document';
    newContinueBtn.addEventListener('click', continueHandler);

    const newCancelBtn = cancelBtn.cloneNode(true);
    cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
    newCancelBtn.textContent = 'Cancel';
    newCancelBtn.addEventListener('click', cancelHandler);
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
        messageDiv.innerHTML = text;
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

    /**
     * Initialize risk filtering functionality
     */
    function initializeRiskFiltering() {
        const filterButtons = {
            'filter-high-risks': 'risk-high',
            'filter-medium-risks': 'risk-medium',
            'filter-low-risks': 'risk-low',
            'show-all-risks': 'all'
        };

        Object.entries(filterButtons).forEach(([buttonId, filterClass]) => {
            const button = document.getElementById(buttonId);
            if (button) {
                button.addEventListener('click', () => {
                    // Remove active class from all buttons
                    Object.keys(filterButtons).forEach(id => {
                        const btn = document.getElementById(id);
                        if (btn) {
                            btn.classList.remove('btn-primary');
                            btn.classList.add('btn-outline');
                        }
                    });

                    // Add active class to clicked button
                    button.classList.remove('btn-outline');
                    button.classList.add('btn-primary');

                    // Filter risk items
                    const riskItems = document.querySelectorAll('.risk-item');
                    riskItems.forEach(item => {
                        if (filterClass === 'all' || item.classList.contains(filterClass)) {
                            item.style.display = 'block';
                            item.style.animation = 'fadeIn 0.5s ease-in';
                        } else {
                            item.style.display = 'none';
                        }
                    });
                });
            }
        });
    }

    /**
     * Initialize summary interactive features
     */
    function initializeSummaryFeatures() {
        // Copy summary functionality
        const copyBtn = document.getElementById('copy-summary');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const summaryContent = document.getElementById('summary-content');
                if (summaryContent) {
                    const text = summaryContent.textContent || summaryContent.innerText;
                    navigator.clipboard.writeText(text).then(() => {
                        copyBtn.innerHTML = '<span class="btn-icon">✅</span><span>Copied!</span>';
                        setTimeout(() => {
                            copyBtn.innerHTML = '<span class="btn-icon">📋</span><span>Copy Summary</span>';
                        }, 2000);
                    }).catch(err => {
                        console.error('Failed to copy text: ', err);
                    });
                }
            });
        }

        // Highlight key points functionality
        const highlightBtn = document.getElementById('highlight-key-points');
        if (highlightBtn) {
            highlightBtn.addEventListener('click', () => {
                const summaryContent = document.getElementById('summary-content');
                if (summaryContent) {
                    const paragraphs = summaryContent.querySelectorAll('p');
                    paragraphs.forEach((p, index) => {
                        if (index % 2 === 0) { // Highlight every other paragraph
                            p.style.background = 'rgba(77, 171, 247, 0.1)';
                            p.style.borderLeft = '4px solid #4dabf7';
                            p.style.paddingLeft = '1rem';
                        }
                    });
                    highlightBtn.innerHTML = '<span class="btn-icon">🎯</span><span>Key Points Highlighted</span>';
                }
            });
        }

        // Toggle readability functionality
        const readabilityBtn = document.getElementById('toggle-readability');
        if (readabilityBtn) {
            let isReadabilityMode = false;
            readabilityBtn.addEventListener('click', () => {
                const summaryContent = document.getElementById('summary-content');
                if (summaryContent) {
                    if (!isReadabilityMode) {
                        // Enable readability mode
                        summaryContent.style.fontSize = '1.2rem';
                        summaryContent.style.lineHeight = '2';
                        summaryContent.style.letterSpacing = '0.5px';
                        readabilityBtn.innerHTML = '<span class="btn-icon">🔍</span><span>Normal View</span>';
                        isReadabilityMode = true;
                    } else {
                        // Disable readability mode
                        summaryContent.style.fontSize = '';
                        summaryContent.style.lineHeight = '';
                        summaryContent.style.letterSpacing = '';
                        readabilityBtn.innerHTML = '<span class="btn-icon">👁️</span><span>Toggle Readability</span>';
                        isReadabilityMode = false;
                    }
                }
            });
        }
    }

    // --- Initialization logic ---
    // Check if the results div exists by checking the flask variable
    const hasResult = document.querySelector('.main-content.container');
    if (hasResult) {
        initializeRiskAccordion();
        initializeRiskFiltering();
        initializeSummaryFeatures();
    }

});
