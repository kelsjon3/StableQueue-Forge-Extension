(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] ===== EXTENSION SCRIPT LOADING =====`);
    console.log(`[${EXTENSION_NAME}] Script loaded at:`, new Date().toISOString());
    console.log(`[${EXTENSION_NAME}] Document ready state:`, document.readyState);

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

            if (queueBtn.disabled) return;
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
            
            // Send job to StableQueue via the API using the complete context menu data
            fetch('/stablequeue/queue_job', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_payload: data,  // Use complete context menu data as API payload
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
            
            // Send bulk job to StableQueue via Forge backend using complete context menu data
            fetch('/stablequeue/queue_job', {
                method: 'POST',
                headers: { 
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    api_payload: data,  // Use complete context menu data as API payload
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

    // Main function to queue current job
    function queueCurrentJob(tabId, jobType) {
        return new Promise(async (resolve, reject) => {
            try {
                console.log(`[${EXTENSION_NAME}] Starting queueCurrentJob for ${tabId}, jobType: ${jobType}`);
                
                // Get the selected server with error handling
                const serverAlias = getSelectedServer();
                
                if (!serverAlias) {
                    const message = 'No server selected in StableQueue tab. Please select a server first.';
                    showNotification(message, 'error');
                    reject(new Error(message));
                    return;
                }
                
                console.log(`[${EXTENSION_NAME}] Using server: ${serverAlias}`);
                
                // Store original fetch and XHR
                const originalFetch = window.fetch;
                const originalXHR = window.XMLHttpRequest;
                
                let intercepted = false;
                let interceptionResolve = null;
                let interceptionReject = null;
                
                // Create a promise to wait for interception
                const interceptionPromise = new Promise((res, rej) => {
                    interceptionResolve = res;
                    interceptionReject = rej;
                });
                
                // Enhanced fetch interception - SYNCHRONOUS BLOCKING
                window.fetch = async function(url, options) {
                    console.log(`[${EXTENSION_NAME}] 🌐 INTERCEPTED FETCH: ${options?.method || 'GET'} ${url}`);
                    
                    // Intercept both /sdapi/v1/ and Gradio endpoints
                    if ((url.includes('/sdapi/v1/txt2img') || 
                         url.includes('/sdapi/v1/img2img') ||
                         url.includes('/api/') || 
                         url.includes('/run/') || 
                         url.includes('/predict') ||
                         url.includes('/queue/join') ||
                         url.includes('/internal/progress')) && 
                        options?.method === 'POST') {
                        
                        console.log(`[${EXTENSION_NAME}] 🎯 API CALL INTERCEPTED: ${url}`);
                        
                        // If this is the first interception, send to StableQueue
                        if (!intercepted) {
                            intercepted = true;
                            console.log(`[${EXTENSION_NAME}] 🎯 FIRST CALL - BLOCKING FORGE EXECUTION - Processing with StableQueue...`);
                            
                            try {
                                let apiPayload;
                                
                                if (url.includes('/sdapi/v1/')) {
                                    // Direct /sdapi/v1/ call - use as-is
                                    apiPayload = JSON.parse(options.body);
                                    console.log(`[${EXTENSION_NAME}] Using /sdapi/v1/ payload directly`);
                                } else {
                                    // Gradio call - send raw payload to preserve ALL parameters
                                    const gradioPayload = JSON.parse(options.body);
                                    console.log(`[${EXTENSION_NAME}] Sending raw Gradio payload to preserve all extension parameters`);
                                    apiPayload = {
                                        type: 'gradio',
                                        raw_payload: gradioPayload,
                                        tab_id: tabId,
                                        url: url
                                    };
                                }
                                
                                const requestData = {
                                    api_payload: apiPayload,
                                    server_alias: serverAlias,
                                    job_type: jobType
                                };
                                
                                console.log(`[${EXTENSION_NAME}] 📤 Sending to StableQueue...`);
                                
                                // SYNCHRONOUS BLOCKING: Wait for StableQueue response before returning
                                const response = await originalFetch('/stablequeue/queue_job', {
                                    method: 'POST',
                                    headers: { 
                                        'Content-Type': 'application/json'
                                    },
                                    body: JSON.stringify(requestData)
                                });
                                
                                console.log(`[${EXTENSION_NAME}] 📥 StableQueue response: ${response.status}`);
                                
                                if (!response.ok) {
                                    const text = await response.text();
                                    const error = new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                                    console.log(`[${EXTENSION_NAME}] ❌ StableQueue error - will restore interceptors on timeout`);
                                    interceptionReject(error);
                                    throw error;
                                }
                                
                                const data = await response.json();
                                
                                if (data.success) {
                                    console.log(`[${EXTENSION_NAME}] ✅ StableQueue success - Job queued! Keeping interception active to block ALL Forge calls.`);
                                    showNotification(data.message, 'success');
                                    interceptionResolve(data);
                                    
                                    // Don't restore interceptors yet - keep blocking all related calls
                                    console.log(`[${EXTENSION_NAME}] 🚫 Blocking first call - will block all subsequent calls too`);
                                } else {
                                    const errorMsg = `Error: ${data.message || 'Unknown error'}`;
                                    const error = new Error(errorMsg);
                                    console.log(`[${EXTENSION_NAME}] ❌ StableQueue returned error - will restore interceptors on timeout`);
                                    showNotification(errorMsg, 'error');
                                    interceptionReject(error);
                                    throw error;
                                }
                                
                            } catch (error) {
                                console.error(`[${EXTENSION_NAME}] Error processing intercepted request:`, error);
                                const errorMsg = `Error: ${error.message}`;
                                showNotification(errorMsg, 'error');
                                
                                // Return error response to block Forge
                                console.log(`[${EXTENSION_NAME}] 🚫 Returning error response to block first call`);
                            }
                        } else {
                            // This is a subsequent call - just block it
                            console.log(`[${EXTENSION_NAME}] 🚫 BLOCKING SUBSEQUENT CALL: ${url}`);
                        }
                        
                        // Return blocked response for ALL intercepted calls
                        return new Response(JSON.stringify({ 
                            success: false, 
                            message: 'Request blocked by StableQueue - job queued remotely',
                            intercepted: true,
                            blocked: true
                        }), {
                            status: 200,  // Return 200 to avoid UI errors
                            headers: { 'Content-Type': 'application/json' }
                        });
                    }
                    
                    // Not a target URL, pass through normally
                    return originalFetch.apply(this, arguments);
                };
                
                // Enhanced XHR interception - SYNCHRONOUS BLOCKING
                window.XMLHttpRequest = function() {
                    const xhr = new originalXHR();
                    const originalOpen = xhr.open;
                    const originalSend = xhr.send;
                    let requestUrl = '';
                    
                    xhr.open = function(method, url, ...args) {
                        requestUrl = url;
                        console.log(`[${EXTENSION_NAME}] 🌐 INTERCEPTED XHR: ${method} ${url}`);
                        return originalOpen.apply(this, arguments);
                    };
                    
                    xhr.send = function(data) {
                        if ((requestUrl.includes('/sdapi/v1/txt2img') || 
                             requestUrl.includes('/sdapi/v1/img2img') ||
                             requestUrl.includes('/api/') || 
                             requestUrl.includes('/run/') || 
                             requestUrl.includes('/predict') ||
                             requestUrl.includes('/queue/join') ||
                             requestUrl.includes('/internal/progress')) && 
                            data) {
                            
                            console.log(`[${EXTENSION_NAME}] 🎯 XHR API CALL INTERCEPTED: ${requestUrl}`);
                            
                            // If this is the first interception, send to StableQueue
                            if (!intercepted) {
                                intercepted = true;
                                console.log(`[${EXTENSION_NAME}] 🎯 FIRST XHR CALL - BLOCKING FORGE XHR EXECUTION - Processing with StableQueue...`);
                                
                                // Handle XHR interception SYNCHRONOUSLY
                                (async () => {
                                    try {
                                        let apiPayload;
                                        
                                        if (requestUrl.includes('/sdapi/v1/')) {
                                            apiPayload = JSON.parse(data);
                                        } else {
                                            const gradioPayload = JSON.parse(data);
                                            console.log(`[${EXTENSION_NAME}] XHR: Sending raw Gradio payload to preserve all extension parameters`);
                                            apiPayload = {
                                                type: 'gradio',
                                                raw_payload: gradioPayload,
                                                tab_id: tabId,
                                                url: requestUrl
                                            };
                                        }
                                        
                                        const requestData = {
                                            api_payload: apiPayload,
                                            server_alias: serverAlias,
                                            job_type: jobType
                                        };
                                        
                                        console.log(`[${EXTENSION_NAME}] 📤 XHR: Sending to StableQueue...`);
                                        
                                        const response = await originalFetch('/stablequeue/queue_job', {
                                            method: 'POST',
                                            headers: { 
                                                'Content-Type': 'application/json'
                                            },
                                            body: JSON.stringify(requestData)
                                        });
                                        
                                        console.log(`[${EXTENSION_NAME}] 📥 XHR: StableQueue response: ${response.status}`);
                                        
                                        if (!response.ok) {
                                            const text = await response.text();
                                            const error = new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                                            console.log(`[${EXTENSION_NAME}] ❌ XHR: StableQueue error - will restore interceptors on timeout`);
                                            interceptionReject(error);
                                        } else {
                                            const responseData = await response.json();
                                            
                                            if (responseData.success) {
                                                console.log(`[${EXTENSION_NAME}] ✅ XHR: StableQueue success - Job queued! Keeping interception active.`);
                                                showNotification(responseData.message, 'success');
                                                interceptionResolve(responseData);
                                            } else {
                                                const errorMsg = `Error: ${responseData.message || 'Unknown error'}`;
                                                const error = new Error(errorMsg);
                                                console.log(`[${EXTENSION_NAME}] ❌ XHR: StableQueue returned error - will restore interceptors on timeout`);
                                                showNotification(errorMsg, 'error');
                                                interceptionReject(error);
                                            }
                                        }
                                        
                                    } catch (error) {
                                        console.error(`[${EXTENSION_NAME}] Error processing intercepted XHR:`, error);
                                        const errorMsg = `Error: ${error.message}`;
                                        showNotification(errorMsg, 'error');
                                        interceptionReject(error);
                                    }
                                })();
                            } else {
                                // This is a subsequent XHR call - just block it
                                console.log(`[${EXTENSION_NAME}] 🚫 BLOCKING SUBSEQUENT XHR CALL: ${requestUrl}`);
                            }
                            
                            // Set XHR to blocked state for ALL intercepted calls
                            setTimeout(() => {
                                console.log(`[${EXTENSION_NAME}] 🚫 XHR: Setting blocked response`);
                                Object.defineProperty(xhr, 'status', { value: 200 });
                                Object.defineProperty(xhr, 'responseText', { 
                                    value: JSON.stringify({ 
                                        success: false, 
                                        message: 'Request blocked by StableQueue - job queued remotely',
                                        intercepted: true,
                                        blocked: true
                                    })
                                });
                                Object.defineProperty(xhr, 'readyState', { value: 4 });
                                if (xhr.onreadystatechange) xhr.onreadystatechange();
                            }, 10);
                            
                            // Immediately block the original XHR from executing
                            console.log(`[${EXTENSION_NAME}] 🚫 XHR: Immediately blocking original XHR execution`);
                            return;
                        }
                        
                        return originalSend.apply(this, arguments);
                    };
                    
                    return xhr;
                };
                
                // Try to find and click the generate button to trigger the API call
                const generateBtn = document.querySelector(`#${tabId}_generate`);
                if (generateBtn) {
                    console.log(`[${EXTENSION_NAME}] Clicking generate button to trigger API call`);
                    generateBtn.click();
                } else {
                    // Restore fetch and XHR, then error
                    window.fetch = originalFetch;
                    window.XMLHttpRequest = originalXHR;
                    showNotification('Generate button not found', 'error');
                    reject(new Error('Generate button not found'));
                    return;
                }
                
                // Wait for interception or timeout
                try {
                    const result = await Promise.race([
                        interceptionPromise,
                        new Promise((_, rej) => setTimeout(() => {
                            rej(new Error('Timeout: No API call intercepted after 10 seconds'));
                        }, 10000)) // Increased timeout to 10 seconds
                    ]);
                    
                    // Set a timer to restore interceptors after successful interception
                    setTimeout(() => {
                        console.log(`[${EXTENSION_NAME}] ⏰ Restoring interceptors after 5 seconds to allow normal operation`);
                        window.fetch = originalFetch;
                        window.XMLHttpRequest = originalXHR;
                    }, 5000); // Restore after 5 seconds
                    
                    resolve(result);
                } catch (error) {
                    // Always restore interceptors on error or timeout
                    console.log(`[${EXTENSION_NAME}] ⏰ Restoring interceptors due to error or timeout`);
                    window.fetch = originalFetch;
                    window.XMLHttpRequest = originalXHR;
                
                    if (error.message.includes('Timeout')) {
                        console.error(`[${EXTENSION_NAME}] ${error.message}`);
                        const errorMsg = `Failed to intercept API call. This indicates Forge is not making the expected API request. Please ensure you're using Forge's standard generation process.`;
                        showNotification(errorMsg, 'error');
                    } else {
                        console.error(`[${EXTENSION_NAME}] Error in queueCurrentJob:`, error);
                        showNotification(`Error: ${error.message}`, 'error');
                    }
                    
                    reject(error);
                }
                
            } catch (error) {
                console.error(`[${EXTENSION_NAME}] Error in queueCurrentJob:`, error);
                showNotification(`Error: ${error.message}`, 'error');
                reject(error);
            }
        });
    }
    
    // Helper function to convert Gradio API payload to /sdapi/v1/ format
    async function convertGradioToSDAPI(gradioPayload, tabId) {
        console.log(`[${EXTENSION_NAME}] Converting Gradio payload:`, gradioPayload);
        
        try {
            // Gradio payloads are typically arrays with function call data
            // The structure is usually: { fn_index: number, data: [...], session_hash: string }
            
            if (!gradioPayload || !gradioPayload.data || !Array.isArray(gradioPayload.data)) {
                throw new Error("Invalid Gradio payload structure - missing data array");
            }
            
            const gradioData = gradioPayload.data;
            console.log(`[${EXTENSION_NAME}] Gradio data array length: ${gradioData.length}`);
            console.log(`[${EXTENSION_NAME}] Gradio data preview:`, gradioData.slice(0, 10));
            
            // Initialize SDAPI payload with defaults
            const sdapiPayload = {
                prompt: "",
                negative_prompt: "",
                styles: [],
                seed: -1,
                subseed: -1,
                subseed_strength: 0,
                steps: 20,
                sampler_name: "Euler a",
                width: 512,
                height: 512,
                cfg_scale: 7.0,
                batch_size: 1,
                n_iter: 1,
                restore_faces: false,
                tiling: false,
                send_images: true,
                save_images: true,
                override_settings: {},
                script_name: null,
                script_args: []
            };
            
            // Extract parameters from Gradio data array
            // Note: Gradio array positions may vary by version/extensions
            // We'll use defensive extraction with fallbacks
            
            try {
                // Common Gradio parameter positions (may need adjustment based on actual payloads)
                if (gradioData[0] && typeof gradioData[0] === 'string') {
                    sdapiPayload.prompt = gradioData[0];
                }
                
                if (gradioData[1] && typeof gradioData[1] === 'string') {
                    sdapiPayload.negative_prompt = gradioData[1];
                }
                
                // Extract numeric parameters with fallbacks
                if (gradioData[2] && typeof gradioData[2] === 'number') {
                    sdapiPayload.steps = gradioData[2];
                }
                
                if (gradioData[3] && typeof gradioData[3] === 'string') {
                    sdapiPayload.sampler_name = gradioData[3];
                }
                
                if (gradioData[4] && typeof gradioData[4] === 'number') {
                    sdapiPayload.cfg_scale = gradioData[4];
                }
                
                if (gradioData[5] && typeof gradioData[5] === 'number') {
                    sdapiPayload.width = gradioData[5];
                }
                
                if (gradioData[6] && typeof gradioData[6] === 'number') {
                    sdapiPayload.height = gradioData[6];
                }
                
                if (gradioData[7] && typeof gradioData[7] === 'number') {
                    sdapiPayload.seed = gradioData[7];
                }
                
                // Look for extension-specific data in the remaining array elements
                // Extensions like ControlNet typically add their data to the end of the array
                for (let i = 8; i < gradioData.length; i++) {
                    const item = gradioData[i];
                    
                    // Check for ControlNet data (usually objects or arrays)
                    if (item && typeof item === 'object') {
                        // If we find extension data, preserve it in script_args
                        if (sdapiPayload.script_args.length === 0) {
                            sdapiPayload.script_name = "extension_data";
                        }
                        sdapiPayload.script_args.push(item);
                    }
                    
                    // Check for style presets, models, etc.
                    if (typeof item === 'string' && (item.includes('.safetensors') || item.includes('.ckpt'))) {
                        sdapiPayload.override_settings.sd_model_checkpoint = item;
                    }
                }
                
            } catch (extractError) {
                console.warn(`[${EXTENSION_NAME}] Error extracting some parameters:`, extractError);
                // Continue with what we have - partial extraction is better than complete failure
            }
            
            console.log(`[${EXTENSION_NAME}] Converted SDAPI payload:`, sdapiPayload);
            
            // Validate required fields
            if (!sdapiPayload.prompt && !sdapiPayload.negative_prompt) {
                console.warn(`[${EXTENSION_NAME}] Warning: No prompts found in conversion. This may indicate a parsing issue.`);
            }
            
            return sdapiPayload;
            
        } catch (error) {
            console.error(`[${EXTENSION_NAME}] Error in Gradio to SDAPI conversion:`, error);
            console.error(`[${EXTENSION_NAME}] Original Gradio payload:`, gradioPayload);
            throw new Error(`Gradio conversion failed: ${error.message}. Please check console for details.`);
        }
    }
    
    // NOTE: UI extraction removed - we only accept complete API payloads
    // This ensures all extension parameters (ControlNet, etc.) are properly captured
    
    // Add "Queue in StableQueue" button next to the Generate button
    function addQueueButtons() {
        console.log(`[${EXTENSION_NAME}] addQueueButtons() called`);
        
        // Try multiple strategies to add buttons
        const strategies = [1000, 2000, 3000, 5000];
        let strategyIndex = 0;
        
        function tryAddButtons() {
            console.log(`[${EXTENSION_NAME}] Attempting to add buttons (attempt ${strategyIndex + 1})`);
            
            // Check if generate buttons exist
            const txt2imgBtn = document.querySelector('#txt2img_generate');
            const img2imgBtn = document.querySelector('#img2img_generate');
            
            console.log(`[${EXTENSION_NAME}] txt2img generate button found:`, !!txt2imgBtn);
            console.log(`[${EXTENSION_NAME}] img2img generate button found:`, !!img2imgBtn);
            
            if (txt2imgBtn) {
                console.log(`[${EXTENSION_NAME}] txt2img button element:`, txt2imgBtn);
                addButtonToTab('txt2img');
            }
            
            if (img2imgBtn) {
                console.log(`[${EXTENSION_NAME}] img2img button element:`, img2imgBtn);
                addButtonToTab('img2img');
            }
            
            // Check if we successfully added buttons
            const queueBtn1 = document.querySelector('#txt2img_queue_stablequeue');
            const queueBtn2 = document.querySelector('#img2img_queue_stablequeue');
            
            console.log(`[${EXTENSION_NAME}] Queue buttons created - txt2img:`, !!queueBtn1, 'img2img:', !!queueBtn2);
            
            if ((!txt2imgBtn || !img2imgBtn || !queueBtn1 || !queueBtn2) && strategyIndex < strategies.length - 1) {
                strategyIndex++;
                console.log(`[${EXTENSION_NAME}] Retrying in ${strategies[strategyIndex]}ms`);
                setTimeout(tryAddButtons, strategies[strategyIndex]);
            } else {
                console.log(`[${EXTENSION_NAME}] Button addition process completed`);
            }
        }
        
        // Start with immediate attempt
        tryAddButtons();
    }
    
    // Install passive HTTP logging that doesn't interfere with interception
    function installPassiveHttpLogging() {
        // Store original functions for logging only - don't replace them
        const originalFetch = window.fetch;
        const originalXHR = window.XMLHttpRequest;
        
        // Create a non-interfering logging proxy (doesn't replace global functions)
        console.log(`[${EXTENSION_NAME}] 🌐 Passive HTTP logging ready - will log API calls when interception is active`);
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