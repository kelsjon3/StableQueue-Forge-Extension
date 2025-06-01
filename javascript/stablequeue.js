    // Configuration
    const EXTENSION_NAME = "StableQueue";
    const EXTENSION_VERSION = "1.0.0";
    
    // Enhanced with comprehensive API interception for Gradio + FastAPI endpoints
    
    // Function to queue current job by intercepting the complete API payload
    function queueCurrentJob(tabId, jobType) {
        return new Promise((resolve, reject) => {
            try {
                // Get the selected server first
                const serverAlias = getSelectedServer();
                
                if (!serverAlias) {
                    showNotification('No server selected in StableQueue tab. Please select a server first.', 'error');
                    reject(new Error('No server selected'));
                    return;
                }
                
                console.log(`[${EXTENSION_NAME}] Intercepting ${tabId} API call to capture complete parameters...`);
                
                // Create a temporary interceptor for the next API call
                const originalFetch = window.fetch;
                const originalXHR = window.XMLHttpRequest;
                let intercepted = false;
                
                window.fetch = async function(url, options) {
                    // Log all fetch calls for debugging
                    console.log(`[${EXTENSION_NAME}] FETCH INTERCEPTOR: ${url}`, options);
                    
                    // Broader interception - catch any POST request that might be generation-related
                    const method = (options && options.method ? options.method : 'GET').toUpperCase();
                    const isPostRequest = method === 'POST';
                    
                    // Look for any generation-related endpoints (including Gradio)
                    const isGenerationCall = isPostRequest && (
                        url.includes('/sdapi/v1/txt2img') ||
                        url.includes('/sdapi/v1/img2img') ||
                        url.includes('txt2img') ||
                        url.includes('img2img') ||
                        (url.includes('/api/') && options && options.body) ||
                        (url.includes('/run/') && options && options.body) ||  // Gradio endpoints often use /run/
                        (url.includes('/predict') && options && options.body)   // Gradio predict endpoints
                    );
                    
                    console.log(`[${EXTENSION_NAME}] URL: ${url}, Method: ${method}, IsPost: ${isPostRequest}, IsGeneration: ${isGenerationCall}, Intercepted: ${intercepted}`);
                    
                    if (!intercepted && isGenerationCall && options && options.body) {
                        intercepted = true;
                        
                        // Restore original fetch immediately
                        window.fetch = originalFetch;
                        window.XMLHttpRequest = originalXHR;
                        
                        try {
                            console.log(`[${EXTENSION_NAME}] Intercepted generation call to: ${url}`);
                            console.log(`[${EXTENSION_NAME}] Raw body:`, options.body);
                            
                            let apiPayload;
                            
                            // Handle different body formats
                            if (typeof options.body === 'string') {
                                try {
                                    apiPayload = JSON.parse(options.body);
                                } catch (e) {
                                    // If not JSON, it might be FormData or other format
                                    console.log(`[${EXTENSION_NAME}] Non-JSON body detected, falling back to UI extraction`);
                                    apiPayload = await extractParametersFromUI(tabId);
                                }
                            } else {
                                // Handle FormData or other types
                                console.log(`[${EXTENSION_NAME}] Non-string body type: ${typeof options.body}, falling back to UI extraction`);
                                apiPayload = await extractParametersFromUI(tabId);
                            }
                            
                            // If we got a Gradio-style payload, convert it to /sdapi/v1/ format
                            if (url.includes('/api/') || url.includes('/run/') || url.includes('/predict')) {
                                console.log(`[${EXTENSION_NAME}] Detected Gradio API call, converting to /sdapi/v1/ format`);
                                apiPayload = await convertGradioToSDAPI(apiPayload, tabId);
                            }
                            
                            console.log(`[${EXTENSION_NAME}] Final API payload:`, apiPayload);
                            
                            // Send to our backend with the complete payload
                            const requestData = {
                                api_payload: apiPayload,
                                server_alias: serverAlias,
                                job_type: jobType
                            };
                            
                            const response = await originalFetch('/stablequeue/queue_job', {
                                method: 'POST',
                                headers: { 
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(requestData)
                            });
                            
                            if (!response.ok) {
                                const text = await response.text();
                                throw new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                            }
                            
                            const data = await response.json();
                            
                            if (data.success) {
                                showNotification(data.message, 'success');
                                resolve(data);
                            } else {
                                const errorMsg = `Error: ${data.message || 'Unknown error'}`;
                                showNotification(errorMsg, 'error');
                                reject(new Error(errorMsg));
                            }
                            
                            // Don't actually send the original request - we're queuing instead
            const msg = `Queued in StableQueue: ${data.message}`;
            const stub = url.includes('/api/') 
                ? { data: [null], is_generating: false } 
                : { images: [], info: msg };
            return new Response(JSON.stringify(stub), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            });

                        } catch (error) {
                            console.error(`[${EXTENSION_NAME}] Error processing intercepted payload:`, error);
                            const errorMsg = `Connection error: ${error.message}`;
                            showNotification(errorMsg, 'error');
                            reject(error);
                            
                            // Return original call if our queuing fails
                            return originalFetch(url, options);
                        }
                    }
                    
                    // For all other requests, use original fetch
                    return originalFetch(url, options);
                };
                
                // Trigger the generation by clicking the actual generate button
                const generateBtn = document.querySelector(`#${tabId}_generate`);
                if (generateBtn) {
                    console.log(`[${EXTENSION_NAME}] Found generate button, clicking...`, generateBtn);
                    generateBtn.click();
                    console.log(`[${EXTENSION_NAME}] Generate button clicked, waiting for interception...`);
                } else {
                    // Restore fetch and XHR, then error
                    window.fetch = originalFetch;
                    window.XMLHttpRequest = originalXHR;
                    showNotification('Generate button not found', 'error');
                    reject(new Error('Generate button not found'));
                }
                
                // Timeout with fallback to UI extraction
                setTimeout(async () => {
                    if (!intercepted) {
                        window.fetch = originalFetch;
                        window.XMLHttpRequest = originalXHR;
                        console.log(`[${EXTENSION_NAME}] Timeout: No API call intercepted, using UI extraction fallback`);
                        
                        try {
                            // Fallback: extract parameters directly from UI
                            const apiPayload = await extractParametersFromUI(tabId);
                            const requestData = {
                                api_payload: apiPayload,
                                server_alias: serverAlias,
                                job_type: jobType
                            };
                            
                            const response = await originalFetch('/stablequeue/queue_job', {
                                method: 'POST',
                                headers: { 
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(requestData)
                            });
                            
                            if (!response.ok) {
                                const text = await response.text();
                                throw new Error(`HTTP ${response.status}: ${text.slice(0,120)}`);
                            }
                            
                            const data = await response.json();
                            
                            if (data.success) {
                                showNotification(`${data.message} (using UI extraction)`, 'success');
                                resolve(data);
                            } else {
                                const errorMsg = `Error: ${data.message || 'Unknown error'}`;
                                showNotification(errorMsg, 'error');
                                reject(new Error(errorMsg));
                            }
                        } catch (error) {
                            console.error(`[${EXTENSION_NAME}] Error with UI extraction fallback:`, error);
                            const errorMsg = `Connection error: ${error.message}`;
                            showNotification(errorMsg, 'error');
                            reject(error);
                        }
                    }
                }, 5000);
                
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
        
        // For now, fall back to UI extraction since Gradio payloads are complex
        // In the future, we could add specific conversion logic here
        return await extractParametersFromUI(tabId);
    }
    
    // Fallback function to extract parameters from UI elements
    async function extractParametersFromUI(tabId) {
        console.log(`[${EXTENSION_NAME}] Extracting parameters from UI for ${tabId}`);
        
        try {
            // Basic parameters that we can extract from UI
            const prompt = document.querySelector(`#${tabId}_prompt textarea`)?.value || '';
            const negativePrompt = document.querySelector(`#${tabId}_neg_prompt textarea`)?.value || '';
            
            // Try to get steps, cfg, width, height with multiple selector strategies
            const steps = parseInt(
                document.querySelector(`#${tabId}_steps input`)?.value ||
                document.querySelector(`[data-testid="${tabId}_steps"] input`)?.value ||
                '20'
            );
            const cfgScale = parseFloat(
                document.querySelector(`#${tabId}_cfg_scale input`)?.value ||
                document.querySelector(`[data-testid="${tabId}_cfg_scale"] input`)?.value ||
                '7.0'
            );
            const width = parseInt(
                document.querySelector(`#${tabId}_width input`)?.value ||
                document.querySelector(`[data-testid="${tabId}_width"] input`)?.value ||
                '512'
            );
            const height = parseInt(
                document.querySelector(`#${tabId}_height input`)?.value ||
                document.querySelector(`[data-testid="${tabId}_height"] input`)?.value ||
                '512'
            );
            
            // Try to get sampler
            const samplerDropdown = document.querySelector(`#${tabId}_sampling select`) ||
                                  document.querySelector(`[data-testid="${tabId}_sampling"] select`);
            const samplerName = samplerDropdown?.value || 'Euler a';
            
            // Basic payload structure for /sdapi/v1/txt2img
            const apiPayload = {
                prompt: prompt,
                negative_prompt: negativePrompt,
                steps: steps,
                cfg_scale: cfgScale,
                width: width,
                height: height,
                sampler_name: samplerName,
                batch_size: 1,
                n_iter: 1,
                seed: -1,
                subseed: -1,
                subseed_strength: 0,
                restore_faces: false,
                tiling: false,
                send_images: true,
                save_images: true
            };
            
            console.log(`[${EXTENSION_NAME}] Extracted basic UI parameters:`, apiPayload);
            
            // TODO: Add extraction for extension parameters
            // This is where we'd need to add logic to capture ControlNet, regional prompting, etc.
            
            return apiPayload;
            
        } catch (error) {
            console.error(`[${EXTENSION_NAME}] Error extracting parameters from UI:`, error);
            throw error;
        }
    }
    
    // Add "Queue in StableQueue" button next to the Generate button
    function addQueueButtons() {
        // Install comprehensive HTTP logging first to debug API calls
        installHttpLogging();
        
        // Wait for UI to be fully loaded
        setTimeout(() => {
            // Add to txt2img tab
            addButtonToTab('txt2img');
            
            // Add to img2img tab
            addButtonToTab('img2img');
            
            console.log(`[${EXTENSION_NAME}] Queue buttons added successfully`);
        }, 1000);
    }
    
    // Install comprehensive HTTP logging to debug what Forge actually does
    function installHttpLogging() {
        const originalFetch = window.fetch;
        const originalXHR = window.XMLHttpRequest;
        
        // Log all fetch calls
        window.fetch = async function(url, options) {
            console.log(`[${EXTENSION_NAME}] 🌐 FETCH: ${options?.method || 'GET'} ${url}`, {
                headers: options?.headers,
                bodyType: typeof options?.body,
                bodyPreview: typeof options?.body === 'string' ? options.body.substring(0, 200) + '...' : options?.body
            });
            return originalFetch.apply(this, arguments);
        };
        
        // Log all XHR calls  
        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            const originalSend = xhr.send;
            
            xhr.open = function(method, url, ...args) {
                console.log(`[${EXTENSION_NAME}] 🌐 XHR: ${method} ${url}`);
                return originalOpen.apply(this, arguments);
            };
            
            xhr.send = function(data) {
                if (data) {
                    console.log(`[${EXTENSION_NAME}] 🌐 XHR DATA:`, {
                        type: typeof data,
                        preview: typeof data === 'string' ? data.substring(0, 200) + '...' : data
                    });
                }
                return originalSend.apply(this, arguments);
            };
            
            return xhr;
        };
        
        console.log(`[${EXTENSION_NAME}] 🌐 HTTP logging installed - all requests will be logged`);
    } 