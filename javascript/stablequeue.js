// StableQueue Forge Extension - JavaScript UI Only
// Python AlwaysOnScript handles all parameter capture and processing via process() hook
// Queue buttons work through Gradio's native event system, NOT artificial button triggering

(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] JavaScript UI loading...`);
    console.log(`[${EXTENSION_NAME}] Using research-backed approach: queue buttons -> Gradio native flow -> process() hook`);

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

    // Context menu functionality (preserved for compatibility)
    function registerContextMenuHandlers() {
        if (typeof gradioApp === 'undefined') {
            setTimeout(registerContextMenuHandlers, 1000);
            return;
        }
        
        // Context menu handlers for right-click queue functionality
        window.stablequeue_send_single = function(params) {
            console.log(`[${EXTENSION_NAME}] Context menu: single queue request`);
            fetch('/stablequeue/context_menu_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    context_data: params,
                    server_alias: '', // Will be handled by Python
                    job_type: 'single'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    params.notification = { text: data.message, type: 'success' };
                } else {
                    showNotification(`Error: ${data.message || 'Unknown error'}`, 'error');
                    params.notification = { text: `Error: ${data.message || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Context menu error:`, error);
                showNotification(`Connection error: ${error.message}`, 'error');
                params.notification = { text: `Connection error: ${error.message}`, type: 'error' };
            });
            
            return params;
        };
        
        window.stablequeue_send_bulk = function(params) {
            console.log(`[${EXTENSION_NAME}] Context menu: bulk queue request`);
            fetch('/stablequeue/context_menu_queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    context_data: params,
                    server_alias: '', // Will be handled by Python 
                    job_type: 'bulk'
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showNotification(data.message, 'success');
                    params.notification = { text: data.message, type: 'success' };
                } else {
                    showNotification(`Error: ${data.message || 'Unknown error'}`, 'error');
                    params.notification = { text: `Error: ${data.message || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Context menu error:`, error);
                showNotification(`Connection error: ${error.message}`, 'error');
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
        console.log(`[${EXTENSION_NAME}] Queue buttons use Gradio native flow - NO artificial triggering`);
        registerContextMenuHandlers();
    }

})(); 