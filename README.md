# StableQueue-Forge-Extension

A Forge extension to queue image generation jobs to a StableQueue server. This extension allows you to:

- Send generation jobs to StableQueue from the Forge UI
- Queue bulk jobs with different seeds
- Monitor job status and progress
- Continue generations even when your browser is closed

## Installation

### Method 1: Clone Repository

1. Clone this repository into your Forge extensions directory:
   ```
   cd path/to/forge/extensions
   git clone https://github.com/kelsjon3/StableQueue-Forge-Extension.git stablequeue
   ```

2. Restart Forge to load the extension

### Method 2: Manual Installation

1. Download this repository as a ZIP file
2. Extract the ZIP to your Forge extensions directory as `stablequeue`
3. Restart Forge to load the extension

### Method 3: Using install.py

1. Download this repository anywhere on your system
2. Run `install.py` with Python:
   ```
   python install.py
   ```
3. The script will automatically locate your Forge installation and install the extension
4. Restart Forge to load the extension

## Configuration

1. Open Forge and go to the Settings tab
2. Locate the "StableQueue Integration" section
3. Configure the following settings:
   - **StableQueue Server URL**: The URL of your StableQueue server (default: http://localhost:3000)
   - **API Key** and **API Secret**: Your StableQueue API credentials
   - **Bulk Job Quantity**: Number of jobs to create when using bulk generation
   - **Seed Variation Method**: How seeds are generated for bulk jobs (Random or Incremental)
   - **Delay Between Jobs**: Time delay between bulk job submissions (seconds)

## Usage

### Using the UI Buttons

1. Set up your generation parameters in Forge as usual
2. Instead of clicking "Generate", use one of the following buttons:
   - **Queue in StableQueue**: Sends a single job to StableQueue
   - **Bulk Queue**: Sends multiple jobs with the same parameters but different seeds

### Using the Context Menu

1. Right-click on the Generate button
2. Select one of the StableQueue options:
   - **Send to StableQueue**: Sends a single job
   - **Send bulk job to StableQueue**: Sends multiple jobs

### Monitoring Jobs

1. Jobs are managed by the StableQueue server
2. Open the StableQueue web interface to monitor progress
3. Job status will be updated even if you close your browser

## Requirements

- Forge UI (A1111 WebUI fork)
- Running StableQueue server (v1.0.0 or higher)
- API key with permissions to submit jobs

## Troubleshooting

- **No servers found**: Make sure your StableQueue server is running and your API credentials are correct
- **Connection errors**: Check the StableQueue server URL and ensure the server is accessible
- **API authentication failed**: Verify your API key and secret in the settings

## License

ISC License
