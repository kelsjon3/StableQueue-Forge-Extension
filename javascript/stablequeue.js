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
queueBtn.addEventListener('click', async (e) => {
   e.preventDefault();
   e.stopPropagation();

  if (queueBtn.disabled) return;            // guard
  queueBtn.disabled = true;
   console.log(`[${EXTENSION_NAME}] Queue button clicked for ${tabId}`);
  await queueCurrentJob(tabId, 'single')
        .finally(() => (queueBtn.disabled = false));
 });
        
        bulkQueueBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            if (bulkQueueBtn.disabled) return;
            bulkQueueBtn.disabled = true;
            console.log(`[${EXTENSION_NAME}] Bulk queue button clicked for ${tabId}`);
            
            await queueCurrentJob(tabId, 'bulk')
                .finally(() => (bulkQueueBtn.disabled = false));
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
            
            const serverDropdown = document.querySelector('#stablequeue_server_dropdown');

            if (!serverDropdown) {
                params.notification = { text: `Server dropdown not found. UI might not be loaded.`, type: 'error' };
                console.error(`[${EXTENSION_NAME}] ContextMenu: Server dropdown (#stablequeue_server_dropdown) not found.`);
                return params;
            }
            
            const serverAlias = serverDropdown.value;
            const selectedOptionText = serverDropdown.options[serverDropdown.selectedIndex]?.text;

            if (!serverAlias || serverAlias.trim() === "") {
                if (serverDropdown.options.length > 0 && selectedOptionText === "Configure API key in settings") {
                    params.notification = { text: `Please configure API credentials in Settings → StableQueue Integration`, type: 'error' };
                    return params;
                }
                params.notification = { text: `No server selected or invalid server value. Value: "${serverAlias}". Selected: "${selectedOptionText}"`, type: 'error' };
                console.error(`[${EXTENSION_NAME}] ContextMenu: No server selected. Value: "${serverAlias}", Options: ${serverDropdown.options.length}, Selected Text: "${selectedOptionText}"`);
                return params;
            }
            
            if (serverAlias === "Configure API key in settings") {
                params.notification = { text: `Please configure API credentials in Settings → StableQueue Integration`, type: 'error' };
                return params;
            }
            
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
            .then(async (response) => {
                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                }
                return response.json();
            })
            .then((data) => {
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
            
            const serverDropdown = document.querySelector('#stablequeue_server_dropdown');

            if (!serverDropdown) {
                params.notification = { text: `Server dropdown not found. UI might not be loaded.`, type: 'error' };
                console.error(`[${EXTENSION_NAME}] ContextMenu Bulk: Server dropdown (#stablequeue_server_dropdown) not found.`);
                return params;
            }
            
            const serverAlias = serverDropdown.value;
            const selectedOptionText = serverDropdown.options[serverDropdown.selectedIndex]?.text;

            if (!serverAlias || serverAlias.trim() === "") {
                if (serverDropdown.options.length > 0 && selectedOptionText === "Configure API key in settings") {
                    params.notification = { text: `Please configure API credentials in Settings → StableQueue Integration`, type: 'error' };
                    return params;
                }
                params.notification = { text: `No server selected or invalid server value. Value: "${serverAlias}". Selected: "${selectedOptionText}"`, type: 'error' };
                console.error(`[${EXTENSION_NAME}] ContextMenu Bulk: No server selected. Value: "${serverAlias}", Options: ${serverDropdown.options.length}, Selected Text: "${selectedOptionText}"`);
                return params;
            }
            
            if (serverAlias === "Configure API key in settings") {
                params.notification = { text: `Please configure API credentials in Settings → StableQueue Integration`, type: 'error' };
                return params;
            }
            
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
    
    // Function to queue current job directly via API
    function queueCurrentJob(tabId, jobType) {
        return new Promise((resolve, reject) => {
            try {
                // Get current generation parameters from the UI
                const params = extractGenerationParams(tabId);
                if (!params) {
                    showNotification('Failed to extract generation parameters', 'error');
                    reject(new Error('Failed to extract generation parameters'));
                    return;
                }
                
                const serverDropdown = document.querySelector('#stablequeue_server_dropdown');
                
                if (!serverDropdown) {
                    showNotification('Server dropdown not found in StableQueue tab. UI might not be loaded.', 'error');
                    console.error(`[${EXTENSION_NAME}] Server dropdown (#stablequeue_server_dropdown) not found.`);
                    reject(new Error('Server dropdown not found'));
                    return;
                }

                // --- DETAILED LOGGING FOR DROPDOWN STATE ---
                console.log(`[${EXTENSION_NAME}] --- Debugging Dropdown State ---`);
                console.log(`[${EXTENSION_NAME}] Dropdown Element:`, serverDropdown);
                console.log(`[${EXTENSION_NAME}] Dropdown Value (serverDropdown.value): "${serverDropdown.value}"`);
                console.log(`[${EXTENSION_NAME}] Selected Index (serverDropdown.selectedIndex): ${serverDropdown.selectedIndex}`);
                
                if (serverDropdown.options && serverDropdown.selectedIndex >= 0 && serverDropdown.selectedIndex < serverDropdown.options.length) {
                    const selectedOpt = serverDropdown.options[serverDropdown.selectedIndex];
                    console.log(`[${EXTENSION_NAME}] Selected Option Element:`, selectedOpt);
                    console.log(`[${EXTENSION_NAME}] Selected Option Text (selectedOpt.text): "${selectedOpt.text}"`);
                    console.log(`[${EXTENSION_NAME}] Selected Option Value (selectedOpt.value): "${selectedOpt.value}"`);
                } else {
                    console.log(`[${EXTENSION_NAME}] No option selected or index out of bounds. Options count: ${serverDropdown.options ? serverDropdown.options.length : 'N/A'}`);
                }
                // console.log(`[${EXTENSION_NAME}] Dropdown outerHTML:`, serverDropdown.outerHTML); // Potentially very long, enable if needed
                console.log(`[${EXTENSION_NAME}] --- End Debugging Dropdown State ---`);

                const serverAlias = serverDropdown.value;
                // const selectedOptionText = serverDropdown.options[serverDropdown.selectedIndex]?.text; // Already logged above more safely

                // It's crucial to check serverAlias after attempting to read it.
                // The user confirms a server IS selected, so serverAlias should ideally be non-empty.
                if (!serverAlias || serverAlias.trim() === "") {
                    let errorDetail = `Dropdown value is "${serverAlias}". `;
                    errorDetail += `Selected index: ${serverDropdown.selectedIndex}. `;
                    if (serverDropdown.options && serverDropdown.selectedIndex >= 0 && serverDropdown.selectedIndex < serverDropdown.options.length) {
                        errorDetail += `Selected option text: "${serverDropdown.options[serverDropdown.selectedIndex].text}". `;
                        errorDetail += `Selected option value: "${serverDropdown.options[serverDropdown.selectedIndex].value}". `;
                    } else {
                        errorDetail += `Could not get selected option details. Options count: ${serverDropdown.options ? serverDropdown.options.length : 'N/A'}. `;
                    }
                    
                    // Check if it's the default "Configure" text, which implies credentials are not set or servers not fetched
                    // This check might be redundant if "Refresh Servers" works and populates real servers.
                    if (serverDropdown.options.length > 0 && serverDropdown.options[serverDropdown.selectedIndex]?.text === "Configure API key in settings") {
                        showNotification('Please configure API credentials in Settings → StableQueue Integration and refresh servers.', 'error');
                        console.error(`[${EXTENSION_NAME}] Error: API credentials not configured or servers not fetched. Details: ${errorDetail}`);
                        reject(new Error('API credentials not configured or servers not fetched.'));
                        return;
                    }

                    showNotification(`No server selected or dropdown returned an empty value. Please re-select from the StableQueue tab. Details: ${errorDetail}`, 'error');
                    console.error(`[${EXTENSION_NAME}] Error: No server selected or dropdown value is empty. Details: ${errorDetail}`);
                    reject(new Error('No server selected or dropdown returned an empty value.'));
                    return;
                }
                
                // This specific check should ideally not be hit if the above handles empty serverAlias
                if (serverAlias === "Configure API key in settings") {
                    showNotification('Please configure API credentials in Settings → StableQueue Integration and refresh servers.', 'error');
                    console.error(`[${EXTENSION_NAME}] Error: "Configure API key in settings" was the effective value.`);
                    reject(new Error('API credentials not configured - "Configure" message was value.'));
                    return;
                }
                
                // Prepare request data
                const requestData = {
                    app_type: 'forge',
                    target_server_alias: serverAlias,
                    generation_params: params,
                    source_info: `stablequeue_forge_extension_${jobType}_v${EXTENSION_VERSION}`
                };
                
                let endpoint = `${getStableQueueUrl()}/api/v2/generate`;
                
                if (jobType === 'bulk') {
                    // Add bulk job specific parameters
                    requestData.bulk_quantity = parseInt(localStorage.getItem('stablequeue_bulk_quantity') || '10');
                    requestData.seed_variation = localStorage.getItem('stablequeue_seed_variation') || 'random';
                    requestData.job_delay = parseInt(localStorage.getItem('stablequeue_job_delay') || '5');
                    endpoint = `${getStableQueueUrl()}/api/v2/generate/bulk`;
                }
                
                // Send to StableQueue API
                fetch(endpoint, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-API-Key': getApiKey(),
                        'X-API-Secret': getApiSecret()
                    },
                    body: JSON.stringify(requestData)
                })
                .then(async (response) => {
                    if (!response.ok) {
                        const text = await response.text();
                        throw new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                    }
                    return response.json();
                })
                .then(data => {
                    if (data.success) {
                        if (jobType === 'bulk') {
                            showNotification(`Bulk job sent to StableQueue: ${data.total_jobs} jobs queued`, 'success');
                        } else {
                            showNotification(`Job sent to StableQueue: ${data.stablequeue_job_id}`, 'success');
                        }
                        resolve(data);
                    } else {
                        const errorMsg = `Error: ${data.error || 'Unknown error'}`;
                        showNotification(errorMsg, 'error');
                        reject(new Error(errorMsg));
                    }
                })
                .catch(error => {
                    console.error(`[${EXTENSION_NAME}] Error sending ${jobType} job:`, error);
                    const errorMsg = `Connection error: ${error.message}`;
                    showNotification(errorMsg, 'error');
                    reject(error);
                });
                
            } catch (error) {
                console.error(`[${EXTENSION_NAME}] Error in queueCurrentJob:`, error);
                showNotification(`Error: ${error.message}`, 'error');
                reject(error);
            }
        });
    }
    
    // Function to extract generation parameters from the current UI
    function extractGenerationParams(tabId) {
        try {
            const params = {};
            
            // Get prompt fields
            const promptTextarea = document.querySelector(`#${tabId}_prompt textarea`);
            const negativePromptTextarea = document.querySelector(`#${tabId}_neg_prompt textarea`);
            
            if (promptTextarea) params.positive_prompt = promptTextarea.value;
            if (negativePromptTextarea) params.negative_prompt = negativePromptTextarea.value;
            
            // Get basic parameters
            const widthInput = document.querySelector(`#${tabId}_width input`);
            const heightInput = document.querySelector(`#${tabId}_height input`);
            const stepsInput = document.querySelector(`#${tabId}_steps input`);
            const cfgInput = document.querySelector(`#${tabId}_cfg_scale input`);
            const seedInput = document.querySelector(`#${tabId}_seed input`);
            const batchSizeInput = document.querySelector(`#${tabId}_batch_size input`);
            const batchCountInput = document.querySelector(`#${tabId}_batch_count input`);
            
            if (widthInput) params.width = parseInt(widthInput.value) || 512;
            if (heightInput) params.height = parseInt(heightInput.value) || 512;
            if (stepsInput) params.steps = parseInt(stepsInput.value) || 20;
            if (cfgInput) params.cfg_scale = parseFloat(cfgInput.value) || 7.0;
            if (seedInput) {
    const v = parseInt(seedInput.value, 10);
    params.seed = Number.isNaN(v) ? -1 : v;
}
            if (batchSizeInput) params.batch_size = parseInt(batchSizeInput.value) || 1;
            if (batchCountInput) params.batch_count = parseInt(batchCountInput.value) || 1;
            
            // Get sampler
            const samplerDropdown = document.querySelector(`#${tabId}_sampling select`);
            if (samplerDropdown) params.sampler_name = samplerDropdown.value;
            
            return params;
        } catch (error) {
            console.error(`[${EXTENSION_NAME}] Error extracting parameters:`, error);
            return null;
        }
    }
    
    // Function to show notifications in the UI
    function showNotification(message, type) {
        // Try to find an existing notification area or create one
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
        
        // Create notification element
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
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    // Helper functions to get configuration from localStorage or defaults
    function getStableQueueUrl() {
        return localStorage.getItem('stablequeue_url') || 'http://192.168.73.124:8083';
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