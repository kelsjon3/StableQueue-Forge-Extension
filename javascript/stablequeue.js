// StableQueue Forge Extension - JavaScript UI Only
// Python AlwaysOnScript handles all parameter capture and processing

(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] JavaScript UI loading...`);

    // Add queue buttons to txt2img and img2img tabs
    function addQueueButtons() {
        setTimeout(() => {
            addButtonToTab('txt2img');
            addButtonToTab('img2img');
            console.log(`[${EXTENSION_NAME}] Queue buttons added`);
        }, 1000);
    }

    function addButtonToTab(tabId) {
        const generateBtn = document.querySelector(`#${tabId}_generate`);
        if (!generateBtn) {
            console.log(`[${EXTENSION_NAME}] Generate button not found for ${tabId}`);
            return;
        }
        
        // Create Queue button
        const queueBtn = document.createElement('button');
        queueBtn.id = `${tabId}_queue_stablequeue`;
        queueBtn.className = generateBtn.className;
        queueBtn.innerHTML = 'Queue in StableQueue';
        queueBtn.style.backgroundColor = '#3498db';
        queueBtn.style.marginLeft = '5px';
        
        // Create Bulk Queue button
        const bulkQueueBtn = document.createElement('button');
        bulkQueueBtn.id = `${tabId}_bulk_queue_stablequeue`;
        bulkQueueBtn.className = generateBtn.className;
        bulkQueueBtn.innerHTML = 'Bulk Queue';
        bulkQueueBtn.style.backgroundColor = '#2980b9';
        bulkQueueBtn.style.marginLeft = '5px';
        
        // Insert buttons after Generate
        generateBtn.parentNode.insertBefore(queueBtn, generateBtn.nextSibling);
        generateBtn.parentNode.insertBefore(bulkQueueBtn, queueBtn.nextSibling);
        
        // Add click event listeners - simple API calls to Python backend
        queueBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (queueBtn.disabled) return;
            queueBtn.disabled = true;
            
            try {
                await queueJob(tabId, 'single');
            } finally {
                queueBtn.disabled = false;
            }
        });
        
        bulkQueueBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (bulkQueueBtn.disabled) return;
            bulkQueueBtn.disabled = true;
            
            try {
                await queueJob(tabId, 'bulk');
            } finally {
                bulkQueueBtn.disabled = false;
            }
        });
    }

        // Trigger queue by setting flag and clicking Generate (AlwaysOnScript intercepts)
    async function queueJob(tabId, jobType) {
        try {
            // Get selected server
            const serverAlias = getSelectedServer();
            if (!serverAlias) {
                showNotification('No server selected in StableQueue tab. Please select a server first.', 'error');
                return;
            }

            console.log(`[${EXTENSION_NAME}] Setting queue flag for ${jobType} on server: ${serverAlias}`);
            
            // Set the pending queue request in Python backend
            const response = await fetch('/stablequeue/trigger_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tab_id: tabId,
                    job_type: jobType,
                    server_alias: serverAlias
                })
            });
            
            if (!response.ok) {
                const text = await response.text();
                throw new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                // Queue flag is set - now trigger the actual generation flow
                // This will create the real StableDiffusionProcessing object that AlwaysOnScript can intercept
                console.log(`[${EXTENSION_NAME}] Queue flag set, triggering generation for parameter capture`);
                
                const generateBtn = document.querySelector(`#${tabId}_generate`);
                if (generateBtn) {
                    generateBtn.click(); // This triggers normal parameter collection + AlwaysOnScript interception
                } else {
                    showNotification('Generate button not found - cannot capture parameters', 'error');
                }
            } else {
                showNotification(`Error: ${data.message || 'Unknown error'}`, 'error');
            }
            
        } catch (error) {
            console.error(`[${EXTENSION_NAME}] Error triggering queue:`, error);
            showNotification(`Connection error: ${error.message}`, 'error');
        }
    }

    // Get selected server from StableQueue tab
    function getSelectedServer() {
        const serverDropdown = document.querySelector('#stablequeue_server_dropdown');
        
        if (!serverDropdown) {
            console.error(`[${EXTENSION_NAME}] Server dropdown not found`);
            return null;
        }
        
        // Handle Gradio dropdown
        const selectedOption = serverDropdown.querySelector('input[type="radio"]:checked');
        if (selectedOption) {
            return selectedOption.value;
        }
        
        // Fallback: try to get from select element
        if (serverDropdown.tagName === 'SELECT') {
            return serverDropdown.value;
        }
        
        console.error(`[${EXTENSION_NAME}] Could not determine selected server`);
        return null;
    }

    // Simple notification system
    function showNotification(message, type) {
        let notificationArea = document.querySelector('#stablequeue-notifications');
        if (!notificationArea) {
            notificationArea = document.createElement('div');
            notificationArea.id = 'stablequeue-notifications';
            notificationArea.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 10000;
                max-width: 400px;
            `;
            document.body.appendChild(notificationArea);
        }
        
        const notification = document.createElement('div');
        notification.style.cssText = `
            padding: 12px 16px;
            margin-bottom: 8px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            background-color: ${type === 'success' ? '#28a745' : '#dc3545'};
        `;
        notification.textContent = message;
        
        notificationArea.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    // Context menu handlers (simple forwarding to Python)
    function registerContextMenuHandlers() {
        if (typeof gradioApp === 'undefined') {
            setTimeout(registerContextMenuHandlers, 1000);
            return;
        }
        
        window.stablequeue_send_single = function(params) {
            const serverAlias = getSelectedServer();
            if (!serverAlias) {
                params.notification = { text: 'No server selected in StableQueue tab. Please select a server first.', type: 'error' };
                return params;
            }
            
            // Forward to Python backend
            fetch('/stablequeue/context_menu_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    context_data: params,
                    server_alias: serverAlias,
                    job_type: 'single'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    params.notification = { text: data.message, type: 'success' };
                } else {
                    params.notification = { text: `Error: ${data.message || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Error:`, error);
                params.notification = { text: `Connection error: ${error.message}`, type: 'error' };
            });
            
            return params;
        };
        
        window.stablequeue_send_bulk = function(params) {
            const serverAlias = getSelectedServer();
            if (!serverAlias) {
                params.notification = { text: 'No server selected in StableQueue tab. Please select a server first.', type: 'error' };
                return params;
            }
            
            // Forward to Python backend
            fetch('/stablequeue/context_menu_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    context_data: params,
                    server_alias: serverAlias,
                    job_type: 'bulk'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    params.notification = { text: data.message, type: 'success' };
                } else {
                    params.notification = { text: `Error: ${data.message || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Error:`, error);
                params.notification = { text: `Connection error: ${error.message}`, type: 'error' };
            });
            
            return params;
        };
        
        console.log(`[${EXTENSION_NAME}] Context menu handlers registered`);
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    function initialize() {
        console.log(`[${EXTENSION_NAME}] Initializing UI...`);
        addQueueButtons();
        registerContextMenuHandlers();
    }

})(); 