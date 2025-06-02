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

- Forge UI (A1111 WebUI fork) with **`--api` flag enabled**
- Running StableQueue server (v1.0.0 or higher)
- API key with permissions to submit jobs

### Important: Enable API Mode

**CRITICAL**: You must launch Forge with the `--api` flag to enable the extension to capture complete generation parameters.

Add `--api` to your Forge launch arguments in `webui-user.sh` or `webui-user.bat`:

```bash
# In webui-user.sh (Linux/Mac)
export COMMANDLINE_ARGS="--api"
```

```batch
REM In webui-user.bat (Windows)
set COMMANDLINE_ARGS=--api
```

Without the `--api` flag, the extension will only capture incomplete parameters and may fail to queue jobs properly.

You can verify the API is enabled by visiting `http://127.0.0.1:7860/docs#/` and confirming you see the `/sdapi/v1/txt2img` endpoint.

## Troubleshooting

- **Incomplete parameters captured** or **"simple" prompts**: Enable the `--api` flag in your Forge launch configuration
- **No `/sdapi/v1/txt2img` endpoint**: The `--api` flag is not enabled - add it to `COMMANDLINE_ARGS`
- **No servers found**: Make sure your StableQueue server is running and your API credentials are correct
- **Connection errors**: Check the StableQueue server URL and ensure the server is accessible
- **API authentication failed**: Verify your API key and secret in the settings
- **Extension parameters missing**: Ensure `--api` is enabled so the full FastAPI interface is available

## License

ISC License
