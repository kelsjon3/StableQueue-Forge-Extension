# StableQueue Forge Extension Configuration

## Quick Setup Guide

After installing the extension and restarting Forge, follow these steps to configure it:

### 1. Open Forge Settings

1. Start Forge and wait for it to fully load
2. Click on the **Settings** tab at the top of the interface
3. In the settings search box, type: `stablequeue`
4. You should see a section called **"StableQueue Integration"**

### 2. Configure Connection Settings

Enter the following settings in the StableQueue Integration section:

- **StableQueue Server URL**: `http://192.168.73.124:8083`
- **API Key**: `mk_9a24c5006a4844e545ab8edd`
- **API Secret**: `fcb588a3-6ede-458e-8673-1bd81f35bb6b`

### 3. Configure Bulk Job Settings (Optional)

- **Bulk Job Quantity**: `10` (number of jobs to create for bulk operations)
- **Seed Variation Method**: `Random` (how seeds are generated for bulk jobs)
- **Delay Between Jobs**: `5` (seconds between bulk job submissions)
- **Add StableQueue options to generation context menu**: `✓` (enabled)

### 4. Save Settings

1. Click **"Apply settings"** at the top of the settings page
2. Wait for the settings to be saved
3. You may need to reload the UI for changes to take effect

## Using the Extension

### Method 1: Using the StableQueue Tab

1. Go to the **txt2img** or **img2img** tab
2. Set up your generation parameters as usual
3. Look for the **StableQueue** accordion section
4. Select a target server from the dropdown
5. Set priority (1-10, where 1 is highest priority)
6. Click **"Queue in StableQueue"** for single jobs or **"Queue Bulk Job"** for multiple jobs

### Method 2: Using Context Menu (if enabled)

1. Set up your generation parameters
2. Right-click on the Generate button
3. Select **"Send to StableQueue"** or **"Send bulk job to StableQueue"**

## Troubleshooting

### Settings Not Appearing

If you don't see the "StableQueue Integration" section in settings:

1. Make sure the extension is properly installed in the `extensions/stablequeue` directory
2. Restart Forge completely
3. Check the console for any error messages during startup

### Connection Issues

If you get connection errors:

1. Verify the server URL is correct: `http://192.168.73.124:8083`
2. Make sure the StableQueue server is running on the Unraid system
3. Check that your network can reach the Unraid server

### Authentication Issues

If you get authentication errors:

1. Double-check the API key and secret are entered correctly
2. Make sure there are no extra spaces in the credentials
3. Verify the API key is still active in the StableQueue server

### No Servers Available

If the server dropdown shows "Configure API key in settings":

1. Make sure you've entered valid API credentials
2. Click the refresh button (🔄) next to the server dropdown
3. Check that the StableQueue server has Forge servers configured

## Server Status

The extension connects to a StableQueue server running on Unraid at `192.168.73.124:8083`. This server manages:

- **2 Forge servers**: "Laptop" and "ArchLinux"
- **Job queue management**: Jobs are processed even when your browser is closed
- **Image generation**: Results are saved on the server and can be accessed later

## Next Steps

Once configured, you can:

1. Queue single generation jobs that will run in the background
2. Queue bulk jobs with different seeds for batch generation
3. Monitor job progress through the StableQueue web interface
4. Continue working in Forge while jobs process on the server

For bulk job functionality, the StableQueue Docker container may need to be restarted to pick up the new bulk endpoint. 