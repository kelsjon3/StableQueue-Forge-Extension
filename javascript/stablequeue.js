// StableQueue Forge Extension - Settings UI Only
// Python AlwaysOnScript handles all parameter capture and processing

(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] JavaScript UI loading - settings management only`);

    // Add StableQueue settings tab to the interface
    function addStableQueueTab() {
        // Find the main tabs container
        const tabsContainer = document.querySelector('.tab-nav');
        if (!tabsContainer) {
            console.log(`[${EXTENSION_NAME}] Tab container not found, retrying...`);
            setTimeout(addStableQueueTab, 1000);
            return;
        }
        
        // Check if tab already exists
        if (document.querySelector('.stablequeue-tab')) {
            console.log(`[${EXTENSION_NAME}] Settings tab already exists`);
            return;
        }
        
        // Create StableQueue settings tab button
        const tabButton = document.createElement('button');
        tabButton.className = 'svelte-1ks3i5a stablequeue-tab';
        tabButton.textContent = 'StableQueue Settings';
        tabButton.onclick = () => showStableQueueSettings();

        // Add tab to container
        tabsContainer.appendChild(tabButton);
        console.log(`[${EXTENSION_NAME}] Settings tab added successfully`);
    }

    // Show StableQueue settings modal
    function showStableQueueSettings() {
        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.style.cssText = `
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.7); z-index: 10000; display: flex;
            justify-content: center; align-items: center;
        `;

        // Create modal content
        const modal = document.createElement('div');
        modal.style.cssText = `
            background: white; padding: 20px; border-radius: 8px;
            max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto;
            color: black;
        `;

        modal.innerHTML = `
            <h3>StableQueue Settings</h3>
            <p style="color: #666; margin-bottom: 20px;">
                Configure connection to your StableQueue backend. Parameter capture is handled automatically by the Python extension.
            </p>
            
            <div style="margin: 15px 0;">
                <label><strong>Server URL:</strong></label><br>
                <input type="text" id="sq-server-url" style="width: 100%; padding: 8px; margin-top: 5px;" 
                       value="${localStorage.getItem('stablequeue_server_url') || 'http://192.168.73.124:8083'}" 
                       placeholder="http://your-server:8083">
            </div>
            
            <div style="margin: 15px 0;">
                <label><strong>API Key:</strong></label><br>
                <input type="text" id="sq-api-key" style="width: 100%; padding: 8px; margin-top: 5px;" 
                       value="${localStorage.getItem('stablequeue_api_key') || ''}" 
                       placeholder="Your API key">
            </div>
            
            <div style="margin: 15px 0;">
                <label><strong>API Secret:</strong></label><br>
                <input type="password" id="sq-api-secret" style="width: 100%; padding: 8px; margin-top: 5px;" 
                       value="${localStorage.getItem('stablequeue_api_secret') || ''}" 
                       placeholder="Your API secret">
            </div>
            
            <div style="margin: 20px 0; padding: 15px; background-color: #f0f8ff; border-radius: 4px; border-left: 4px solid #007acc;">
                <h4 style="margin-top: 0;">How StableQueue Works:</h4>
                <ul style="margin: 10px 0; padding-left: 20px;">
                    <li><strong>Automatic Capture:</strong> Python extension intercepts ALL generation attempts</li>
                    <li><strong>User Choice:</strong> Configure action in txt2img/img2img tabs: Queue Only, Queue + Generate, or Generate Only</li>
                    <li><strong>Complete Parameters:</strong> Captures core settings + all extensions (ControlNet, etc.)</li>
                    <li><strong>Remote Browser Safe:</strong> No file system dependencies</li>
                </ul>
            </div>
            
            <div style="margin: 15px 0;">
                <button id="sq-test-connection" style="padding: 10px 20px; margin-right: 10px; background: #007acc; color: white; border: none; border-radius: 4px; cursor: pointer;">Test Connection</button>
                <button id="sq-save-settings" style="padding: 10px 20px; margin-right: 10px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">Save Settings</button>
                <button id="sq-close-modal" style="padding: 10px 20px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">Close</button>
            </div>
            
            <div id="sq-status" style="margin-top: 15px; padding: 10px; border-radius: 4px; display: none;"></div>
        `;

        // Event handlers
        modal.querySelector('#sq-test-connection').onclick = testConnection;
        modal.querySelector('#sq-save-settings').onclick = saveSettings;
        modal.querySelector('#sq-close-modal').onclick = () => document.body.removeChild(overlay);
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
    }

    // Test connection to StableQueue server
    async function testConnection() {
        const status = document.getElementById('sq-status');
        const serverUrl = document.getElementById('sq-server-url').value.trim();
        const apiKey = document.getElementById('sq-api-key').value.trim();
        const apiSecret = document.getElementById('sq-api-secret').value.trim();

        if (!serverUrl || !apiKey || !apiSecret) {
            showStatus('Please fill in all fields', 'error');
            return;
        }

        try {
            showStatus('Testing connection...', 'info');
            
            const response = await fetch(`${serverUrl}/api/v1/queue/servers`, {
                method: 'GET',
                headers: {
                    'X-API-Key': apiKey,
                    'X-API-Secret': apiSecret,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                const serverCount = data.servers?.length || 0;
                showStatus(`✅ Connection successful! Found ${serverCount} servers: ${data.servers?.map(s => s.alias).join(', ') || 'none'}`, 'success');
            } else {
                const errorText = await response.text();
                showStatus(`❌ Connection failed: ${response.status} ${response.statusText}\n${errorText}`, 'error');
            }
        } catch (error) {
            showStatus(`❌ Connection error: ${error.message}`, 'error');
        }
    }

    // Save settings to localStorage and Forge settings
    async function saveSettings() {
        const serverUrl = document.getElementById('sq-server-url').value.trim();
        const apiKey = document.getElementById('sq-api-key').value.trim();
        const apiSecret = document.getElementById('sq-api-secret').value.trim();

        // Save to localStorage for immediate JavaScript access
        localStorage.setItem('stablequeue_server_url', serverUrl);
        localStorage.setItem('stablequeue_api_key', apiKey);
        localStorage.setItem('stablequeue_api_secret', apiSecret);

        // Also try to save to Forge settings
        try {
            // This might work if there's a settings API available
            const settingsPayload = {
                stablequeue_url: serverUrl,
                stablequeue_api_key: apiKey,
                stablequeue_api_secret: apiSecret
            };
            
            // Try to call Forge settings API if available
            fetch('/api/v1/options', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settingsPayload)
            }).then(response => {
                if (response.ok) {
                    console.log('[StableQueue] Settings saved to Forge backend');
                } else {
                    console.log('[StableQueue] Could not save to Forge backend (use Settings tab)');
                }
            }).catch(e => {
                console.log('[StableQueue] Settings API not available (use Settings tab)');
            });
            
        } catch (error) {
            console.log('[StableQueue] Could not save to backend, use Settings tab');
        }

        showStatus('✅ Settings saved to browser storage.\nFor Python access, also configure in Settings → StableQueue Integration', 'success');
    }

    // Show status message
    function showStatus(message, type) {
        const status = document.getElementById('sq-status');
        status.style.display = 'block';
        status.textContent = message;
        status.style.whiteSpace = 'pre-line'; // Allow line breaks
        status.style.backgroundColor = type === 'success' ? '#d4edda' : 
                                    type === 'error' ? '#f8d7da' : '#d1ecf1';
        status.style.color = type === 'success' ? '#155724' : 
                           type === 'error' ? '#721c24' : '#0c5460';
        status.style.border = `1px solid ${type === 'success' ? '#c3e6cb' : 
                                        type === 'error' ? '#f5c6cb' : '#bee5eb'}`;
    }

    // Initialize extension when DOM is ready
    function init() {
        console.log(`[${EXTENSION_NAME}] Initializing settings UI...`);
        
        // Add settings tab to interface
        addStableQueueTab();
        
        console.log(`[${EXTENSION_NAME}] Settings UI initialized. Use Settings → StableQueue Integration for full configuration.`);
    }

    // Start initialization when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log(`[${EXTENSION_NAME}] Script loaded - settings management only`);
})(); 