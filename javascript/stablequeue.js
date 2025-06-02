// StableQueue Forge Extension - Settings UI Only
// Parameter capture and job submission handled by Python AlwaysOnScript

(function() {
    'use strict';
    
    const EXTENSION_NAME = 'StableQueue';
    
    console.log(`[${EXTENSION_NAME}] JavaScript UI loaded - Python handles parameter capture`);

    // Add StableQueue tab to the interface
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
            console.log(`[${EXTENSION_NAME}] Tab already exists`);
            return;
        }

        // Create StableQueue tab button
        const tabButton = document.createElement('button');
        tabButton.className = 'svelte-1ks3i5a stablequeue-tab';
        tabButton.textContent = 'StableQueue';
        tabButton.onclick = () => showStableQueueInfo();

        // Add tab to container
        tabsContainer.appendChild(tabButton);
        console.log(`[${EXTENSION_NAME}] Tab added successfully`);
    }

    // Show StableQueue information modal
    function showStableQueueInfo() {
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
        `;

        modal.innerHTML = `
            <h3>StableQueue Extension</h3>
            <div style="margin: 15px 0;">
                <h4>✅ Python Extension Active</h4>
                <p>StableQueue is now running as a Python AlwaysOnScript that captures complete generation parameters including all extension data (ControlNet, IP-Adapter, etc.).</p>
                
                <h4>📝 Configuration</h4>
                <p>Configure StableQueue settings in the <strong>Settings > StableQueue</strong> tab:</p>
                <ul style="margin-left: 20px;">
                    <li><strong>Server URL:</strong> Your StableQueue server address</li>
                    <li><strong>API Key & Secret:</strong> Your StableQueue API credentials</li>
                    <li><strong>Auto-queue:</strong> Enable to automatically queue generations to StableQueue (prevents local generation)</li>
                </ul>
                
                <h4>🚀 How It Works</h4>
                <ol style="margin-left: 20px;">
                    <li>Enter your prompt and configure generation settings</li>
                    <li>If auto-queue is enabled, click "Generate" to queue the job</li>
                    <li>The Python extension captures ALL parameters (including extensions)</li>
                    <li>Job is sent to StableQueue and local generation is prevented</li>
                    <li>Monitor job progress in your StableQueue web interface</li>
                </ol>
                
                <h4>🔧 Settings Location</h4>
                <p>Go to: <strong>Settings tab > StableQueue section</strong> to configure the extension.</p>
                
                <div style="background: #f0f8ff; padding: 10px; border-radius: 4px; margin: 15px 0;">
                    <strong>💡 Tip:</strong> This approach captures complete extension parameters (ControlNet, IP-Adapter, etc.) 
                    that were previously missed with the network interception method.
                </div>
            </div>
            <div style="margin: 15px 0;">
                <button id="sq-open-settings" style="padding: 8px 16px; margin-right: 10px;">Open Settings</button>
                <button id="sq-close-modal" style="padding: 8px 16px;">Close</button>
            </div>
        `;

        // Event handlers
        modal.querySelector('#sq-open-settings').onclick = () => {
            // Try to navigate to settings
            const settingsTab = document.querySelector('button[id="settings"]') || 
                              document.querySelector('button:contains("Settings")') ||
                              document.querySelector('[data-tab="settings"]');
            if (settingsTab) {
                settingsTab.click();
                document.body.removeChild(overlay);
            } else {
                alert('Please manually navigate to Settings > StableQueue to configure the extension.');
            }
        };
        
        modal.querySelector('#sq-close-modal').onclick = () => document.body.removeChild(overlay);
        
        overlay.appendChild(modal);
        document.body.appendChild(overlay);
    }

    // Initialize extension when DOM is ready
    function init() {
        console.log(`[${EXTENSION_NAME}] Initializing JavaScript UI...`);
        
        // Add info tab to interface
        addStableQueueTab();
        
        console.log(`[${EXTENSION_NAME}] JavaScript UI initialized - Python extension handles the rest`);
    }

    // Start initialization when page loads
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    console.log(`[${EXTENSION_NAME}] JavaScript loaded successfully`);
})(); 