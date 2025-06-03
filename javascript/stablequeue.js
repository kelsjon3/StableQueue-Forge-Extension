// StableQueue Forge Extension - JavaScript UI Only
// Python AlwaysOnScript handles all parameter capture and processing

(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] JavaScript UI loading...`);

    // Phase 2: No longer need to add buttons via JavaScript
    // Queue buttons are now integrated directly via Gradio in the Python Script.ui() method
    function addQueueButtons() {
        console.log(`[${EXTENSION_NAME}] Queue buttons are now integrated via Gradio - no JavaScript DOM manipulation needed`);
    }

    // Phase 2: Queue functionality now handled entirely by Python Gradio integration
    // No need for JavaScript queue functions or server selection logic

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

    // Phase 2: Context menu functionality preserved but simplified  
    // (Still uses the old approach for now - can be enhanced later)
    function registerContextMenuHandlers() {
        if (typeof gradioApp === 'undefined') {
            setTimeout(registerContextMenuHandlers, 1000);
            return;
        }
        
        // Note: Context menu still uses the old server selection approach
        // This could be enhanced in Phase 3 to integrate with the new Gradio UI
        window.stablequeue_send_single = function(params) {
            // Use StableQueue tab server selection for context menu
            // For now, just forward to Python backend
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
            // Use StableQueue tab server selection for context menu
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
        
        console.log(`[${EXTENSION_NAME}] Context menu handlers registered (simplified)`);
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

    // Debug function to inspect dropdown structure
    window.stablequeue_debug_dropdown = function() {
        const dropdown = document.querySelector('#stablequeue_server_dropdown');
        if (!dropdown) {
            console.log('Dropdown not found');
            return;
        }
        
        console.log('Dropdown element:', dropdown);
        console.log('Dropdown HTML:', dropdown.outerHTML);
        console.log('Dropdown value:', dropdown.value);
        console.log('All inputs inside dropdown:', dropdown.querySelectorAll('input'));
        console.log('All selects inside dropdown:', dropdown.querySelectorAll('select'));
        
        const inputs = dropdown.querySelectorAll('input');
        inputs.forEach((input, i) => {
            console.log(`Input ${i}:`, input, 'value:', input.value, 'type:', input.type);
        });
        
        return dropdown;
    };

})(); 