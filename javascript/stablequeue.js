// StableQueue Forge Extension - JavaScript Integration

(function() {
    // Configuration
    const EXTENSION_NAME = "StableQueue";
    const EXTENSION_VERSION = "1.0.0";
    
    // Add "Queue in StableQueue" button next to the Generate button
    function addQueueButtons() {
        // Wait for UI to be fully loaded
        setTimeout(() => {
            // Add to txt2img tab
            addButtonToTab('txt2img');
            
            // Add to img2img tab
            addButtonToTab('img2img');
            
            console.log(`[${EXTENSION_NAME}] Queue buttons added successfully`);
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
        
        // Add click event listeners
        queueBtn.addEventListener('click', () => {
            // Find and click the StableQueue tab's queue button
            const accordionBtn = document.querySelector(`.accordion-button[aria-controls*="stablequeue"]`);
            if (accordionBtn && !accordionBtn.classList.contains('expanded')) {
                accordionBtn.click();
            }
            
            // Click the Queue button in our extension UI
            setTimeout(() => {
                const extensionQueueBtn = document.querySelector('#tab_stablequeue button[aria-label="Queue in StableQueue"]');
                if (extensionQueueBtn) {
                    extensionQueueBtn.click();
                } else {
                    console.log(`[${EXTENSION_NAME}] Could not find Queue button in extension UI`);
                }
            }, 100);
        });
        
        bulkQueueBtn.addEventListener('click', () => {
            // Find and click the StableQueue tab's bulk queue button
            const accordionBtn = document.querySelector(`.accordion-button[aria-controls*="stablequeue"]`);
            if (accordionBtn && !accordionBtn.classList.contains('expanded')) {
                accordionBtn.click();
            }
            
            // Click the Bulk Queue button in our extension UI
            setTimeout(() => {
                const extensionBulkQueueBtn = document.querySelector('#tab_stablequeue button[aria-label="Queue Bulk Job"]');
                if (extensionBulkQueueBtn) {
                    extensionBulkQueueBtn.click();
                } else {
                    console.log(`[${EXTENSION_NAME}] Could not find Bulk Queue button in extension UI`);
                }
            }, 100);
        });
    }
    
    // Register context menu handlers
    function registerContextMenuHandlers() {
        if (typeof gradioApp === 'undefined') {
            console.log(`[${EXTENSION_NAME}] gradioApp not defined, waiting...`);
            setTimeout(registerContextMenuHandlers, 1000);
            return;
        }
        
        // Single job context menu handler
        window.stablequeue_send_single = function(params) {
            const data = JSON.parse(JSON.stringify(params));
            
            // Find the first available server in the dropdown
            const serverDropdown = gradioApp().querySelector('#tab_stablequeue select');
            if (!serverDropdown || serverDropdown.options.length === 0) {
                params.notification = { text: `No servers configured in StableQueue settings`, type: 'error' };
                return params;
            }
            
            const serverAlias = serverDropdown.options[0].value;
            
            // Send job to StableQueue via the API
            fetch(`${getStableQueueUrl()}/api/v2/generate`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-API-Key': getApiKey(),
                    'X-API-Secret': getApiSecret()
                },
                body: JSON.stringify({
                    app_type: 'forge',
                    target_server_alias: serverAlias,
                    generation_params: data,
                    source_info: `stablequeue_forge_extension_contextmenu_v${EXTENSION_VERSION}`
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    params.notification = { text: `Job sent to StableQueue: ${data.stablequeue_job_id}`, type: 'success' };
                } else {
                    params.notification = { text: `Error: ${data.error || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Error sending job:`, error);
                params.notification = { text: `Connection error: ${error.message}`, type: 'error' };
            });
            
            return params;
        };
        
        // Bulk job context menu handler
        window.stablequeue_send_bulk = function(params) {
            const data = JSON.parse(JSON.stringify(params));
            
            // Find the first available server in the dropdown
            const serverDropdown = gradioApp().querySelector('#tab_stablequeue select');
            if (!serverDropdown || serverDropdown.options.length === 0) {
                params.notification = { text: `No servers configured in StableQueue settings`, type: 'error' };
                return params;
            }
            
            const serverAlias = serverDropdown.options[0].value;
            
            // Get bulk job settings from shared opts
            const bulkQuantity = parseInt(localStorage.getItem('stablequeue_bulk_quantity') || '10');
            const seedVariation = localStorage.getItem('stablequeue_seed_variation') || 'random';
            const jobDelay = parseInt(localStorage.getItem('stablequeue_job_delay') || '5');
            
            // Send bulk job to StableQueue via the API
            fetch(`${getStableQueueUrl()}/api/v2/generate/bulk`, {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json',
                    'X-API-Key': getApiKey(),
                    'X-API-Secret': getApiSecret()
                },
                body: JSON.stringify({
                    app_type: 'forge',
                    target_server_alias: serverAlias,
                    bulk_quantity: bulkQuantity,
                    seed_variation: seedVariation,
                    job_delay: jobDelay,
                    generation_params: data,
                    source_info: `stablequeue_forge_extension_bulk_contextmenu_v${EXTENSION_VERSION}`
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    params.notification = { text: `Bulk job sent to StableQueue: ${data.total_jobs} jobs queued`, type: 'success' };
                } else {
                    params.notification = { text: `Error: ${data.error || 'Unknown error'}`, type: 'error' };
                }
            })
            .catch(error => {
                console.error(`[${EXTENSION_NAME}] Error sending bulk job:`, error);
                params.notification = { text: `Connection error: ${error.message}`, type: 'error' };
            });
            
            return params;
        };
        
        console.log(`[${EXTENSION_NAME}] Context menu handlers registered`);
    }
    
    // Helper functions to get configuration from localStorage or defaults
    function getStableQueueUrl() {
        return localStorage.getItem('stablequeue_url') || 'http://localhost:3000';
    }
    
    function getApiKey() {
        return localStorage.getItem('stablequeue_api_key') || '';
    }
    
    function getApiSecret() {
        return localStorage.getItem('stablequeue_api_secret') || '';
    }
    
    // Initialize when the DOM is fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log(`[${EXTENSION_NAME}] Extension JavaScript loaded`);
        
        // Initialize UI enhancements
        addQueueButtons();
        
        // Register context menu handlers
        registerContextMenuHandlers();
    });
})(); 