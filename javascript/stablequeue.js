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
            
            // Get the selected server using our helper function with improved error handling
            const serverAlias = getSelectedServer();
            
            if (!serverAlias) {
                params.notification = { text: `No server selected in StableQueue tab. Please select a server first.`, type: 'error' };
                return params;
            }
            
            // Send job to StableQueue via the API
            fetch('/stablequeue/queue_job', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    generation_params: data,
                    server_alias: serverAlias,
                    job_type: 'single'
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
                    params.notification = { text: data.message, type: 'success' };
                } else {
                    params.notification = { text: `Error: ${data.message || 'Unknown error'}`, type: 'error' };
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
            
            // Get the selected server using our helper function with improved error handling
            const serverAlias = getSelectedServer();
            
            if (!serverAlias) {
                params.notification = { text: `No server selected in StableQueue tab. Please select a server first.`, type: 'error' };
                return params;
            }
            
            // Get bulk job settings - NO seed manipulation
            const bulkQuantity = parseInt(localStorage.getItem('stablequeue_bulk_quantity') || '10');
            const jobDelay = parseInt(localStorage.getItem('stablequeue_job_delay') || '5');
            
            // Send bulk job to StableQueue via Forge backend
            fetch('/stablequeue/queue_job', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    generation_params: data,
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
                
                // Get the selected server using our helper function with enhanced debugging
                const serverAlias = getSelectedServer();
                
                if (!serverAlias) {
                    showNotification('No server selected in StableQueue tab. Please select a server first.', 'error');
                    reject(new Error('No server selected'));
                    return;
                }
                
                // Prepare request data for Forge backend
                const requestData = {
                    generation_params: params,
                    server_alias: serverAlias,
                    job_type: jobType
                };
                
                console.log(`[${EXTENSION_NAME}] Sending request to Forge backend`);
                console.log(`[${EXTENSION_NAME}] Request data:`, requestData);
                
                // Send to Forge backend API
                fetch('/stablequeue/queue_job', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
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
                        showNotification(data.message, 'success');
                        resolve(data);
                    } else {
                        const errorMsg = `Error: ${data.message || 'Unknown error'}`;
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
            
            // Get basic parameters - extract exactly what's in the UI without defaults
            const widthInput = document.querySelector(`#${tabId}_width input`);
            const heightInput = document.querySelector(`#${tabId}_height input`);
            const stepsInput = document.querySelector(`#${tabId}_steps input`);
            const cfgInput = document.querySelector(`#${tabId}_cfg_scale input`);
            const seedInput = document.querySelector(`#${tabId}_seed input`);
            const batchSizeInput = document.querySelector(`#${tabId}_batch_size input`);
            const batchCountInput = document.querySelector(`#${tabId}_batch_count input`);
            
            if (widthInput && widthInput.value) params.width = parseInt(widthInput.value);
            if (heightInput && heightInput.value) params.height = parseInt(heightInput.value);
            if (stepsInput && stepsInput.value) params.steps = parseInt(stepsInput.value);
            if (cfgInput && cfgInput.value) params.cfg_scale = parseFloat(cfgInput.value);
            if (seedInput && seedInput.value) {
                const v = parseInt(seedInput.value, 10);
                if (!Number.isNaN(v)) params.seed = v;
            }
            if (batchSizeInput && batchSizeInput.value) params.batch_size = parseInt(batchSizeInput.value);
            if (batchCountInput && batchCountInput.value) params.batch_count = parseInt(batchCountInput.value);
            
            // Get sampler
            const samplerDropdown = document.querySelector(`#${tabId}_sampling select`);
            if (samplerDropdown && samplerDropdown.value) params.sampler_name = samplerDropdown.value;
            
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
    
    // Function to get selected server from StableQueue tab with enhanced Gradio support
    function getSelectedServer() {
        const serverDropdown = document.querySelector('#stablequeue_server_dropdown');
        
        if (!serverDropdown) {
            console.error(`[${EXTENSION_NAME}] Server dropdown (#stablequeue_server_dropdown) not found.`);
            return null;
        }

        // --- DETAILED LOGGING FOR DROPDOWN STATE ---
        console.log(`[${EXTENSION_NAME}] --- Debugging Dropdown State ---`);
        console.log(`[${EXTENSION_NAME}] Dropdown Element:`, serverDropdown);
        console.log(`[${EXTENSION_NAME}] Element tagName: ${serverDropdown.tagName}`);
        console.log(`[${EXTENSION_NAME}] Element className: ${serverDropdown.className}`);
        console.log(`[${EXTENSION_NAME}] Element type: ${serverDropdown.type || 'undefined'}`);
        
        // Try to get the value using multiple approaches
        let serverAlias = null;
        
        // Check if it's a standard select element
        if (serverDropdown.tagName === 'SELECT') {
            console.log(`[${EXTENSION_NAME}] Standard SELECT element found`);
            serverAlias = serverDropdown.value;
            console.log(`[${EXTENSION_NAME}] Dropdown Value: "${serverAlias}"`);
            console.log(`[${EXTENSION_NAME}] Selected Index: ${serverDropdown.selectedIndex}`);
            
            if (serverDropdown.options && serverDropdown.options.length > 0) {
                console.log(`[${EXTENSION_NAME}] Options count: ${serverDropdown.options.length}`);
                if (serverDropdown.selectedIndex >= 0) {
                    const selectedOpt = serverDropdown.options[serverDropdown.selectedIndex];
                    console.log(`[${EXTENSION_NAME}] Selected Option: "${selectedOpt.text}" (value: "${selectedOpt.value}")`);
                }
            }
        } else {
            console.log(`[${EXTENSION_NAME}] Non-standard element found (likely Gradio component)`);
            console.log(`[${EXTENSION_NAME}] Element innerHTML:`, serverDropdown.innerHTML.substring(0, 200) + '...');
            
            // Try to find nested select element within the Gradio component
            const nestedSelect = serverDropdown.querySelector('select');
            if (nestedSelect) {
                console.log(`[${EXTENSION_NAME}] Found nested SELECT element`);
                serverAlias = nestedSelect.value;
                console.log(`[${EXTENSION_NAME}] Nested select value: "${serverAlias}"`);
                console.log(`[${EXTENSION_NAME}] Nested select options count: ${nestedSelect.options ? nestedSelect.options.length : 'undefined'}`);
            } else {
                console.log(`[${EXTENSION_NAME}] No nested SELECT element found`);
                
                // Try to find input element (some Gradio dropdowns use input)
                const gradioInput = serverDropdown.querySelector('input');
                if (gradioInput) {
                    serverAlias = gradioInput.value;
                    console.log(`[${EXTENSION_NAME}] Found input element with value: "${serverAlias}"`);
                }
                
                const gradioOptions = serverDropdown.querySelectorAll('[role="option"]');
                if (gradioOptions.length > 0) {
                    console.log(`[${EXTENSION_NAME}] Found ${gradioOptions.length} role="option" elements`);
                }
            }
        }
        console.log(`[${EXTENSION_NAME}] --- End Debugging Dropdown State ---`);

        console.log(`[${EXTENSION_NAME}] Final serverAlias extracted: "${serverAlias}"`);

        // Validate the extracted server alias
        if (!serverAlias || serverAlias.trim() === "") {
            console.error(`[${EXTENSION_NAME}] Error: No server selected or dropdown value is empty. Final serverAlias: "${serverAlias}"`);
            return null;
        }
        
        // Check for the default "Configure" text
        if (serverAlias === "Configure API key in settings") {
            console.error(`[${EXTENSION_NAME}] Error: "Configure API key in settings" was the effective value.`);
            return null;
        }
        
        return serverAlias;
    }
    
    // Function to monitor and save server selection
    function monitorServerSelection() {
        // Try to find the server dropdown and add change listener
        const selectors = [
            '#stablequeue select',
            '[id*="stablequeue"] select',
            'div[id*="stablequeue"] select'
        ];
        
        for (const selector of selectors) {
            try {
                const dropdown = document.querySelector(selector);
                if (dropdown && !dropdown.hasAttribute('data-stablequeue-monitored')) {
                    dropdown.setAttribute('data-stablequeue-monitored', 'true');
                    dropdown.addEventListener('change', function() {
                        if (this.value && this.value !== "Configure API key in settings") {
                            localStorage.setItem('stablequeue_selected_server', this.value);
                            console.log(`[${EXTENSION_NAME}] Saved selected server to localStorage: ${this.value}`);
                        }
                    });
                    console.log(`[${EXTENSION_NAME}] Added change listener to server dropdown`);
                    break;
                }
            } catch (e) {
                // Continue to next selector
            }
        }
        
        // Re-run this function periodically to catch dynamically created dropdowns
        setTimeout(monitorServerSelection, 2000);
    }
    
    // Initialize when the DOM is fully loaded
    document.addEventListener('DOMContentLoaded', function() {
        console.log(`[${EXTENSION_NAME}] Extension JavaScript loaded`);
        
        // Initialize UI enhancements
        addQueueButtons();
        
        // Register context menu handlers
        registerContextMenuHandlers();
        
        // Monitor server selection
        monitorServerSelection();
    });
})();