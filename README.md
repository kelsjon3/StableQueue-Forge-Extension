# StableQueue Forge Extension

A research-backed queue management extension for Forge that integrates with StableQueue servers. This extension provides seamless job queuing with complete parameter capture using Forge's native AlwaysOnScript system.

## Features

- **Research-Backed Architecture**: Built following the findings in `/docs/Forge Parameter Capture Research_.md`
- **Complete Parameter Capture**: Intercepts full generation parameters via `StableDiffusionProcessing` object
- **Native Gradio Integration**: Queue buttons work through Forge's natural generation pipeline
- **Headless Operation**: No browser dependencies for job dispatching 
- **ControlNet Support**: Proper handling of ControlNet's 15-parameter structure
- **Server Management**: Automatic server discovery via StableQueue API
- **Single & Bulk Queuing**: Support for both individual and batch job submissions

## How It Works

### Core Architecture (Research-Backed)

1. **AlwaysOnScript with `process()` Hook**: The extension registers as an AlwaysOnScript that intercepts all generation requests
2. **Queue Intent Detection**: Queue buttons set intent flags and trigger the normal generation pipeline
3. **Parameter Interception**: The `process()` hook captures complete parameters from the `StableDiffusionProcessing` object
4. **Local Generation Prevention**: Returns empty `Processed` object to prevent local generation when queuing
5. **API Submission**: Extracted parameters are submitted to StableQueue via v2 API

### User Workflow

1. Configure generation parameters in Forge UI (prompt, model, ControlNet, etc.)
2. Select target server from dropdown (auto-populated from StableQueue)
3. Click "Queue in StableQueue" or "Bulk Queue" button
4. Extension intercepts generation, extracts parameters, and submits to queue
5. Job appears in StableQueue dashboard for processing

## Installation

1. Clone this repository into your Forge `extensions` directory:
   ```bash
   cd /path/to/forge/extensions
   git clone https://github.com/yourusername/StableQueue-Forge-Extension.git
   ```

2. Restart Forge

3. Configure StableQueue API credentials in Settings > StableQueue

## Configuration

### StableQueue Settings

Access via Settings > StableQueue in Forge:

- **StableQueue API URL**: Base URL of your StableQueue server (e.g., `http://localhost:8000`)
- **API Key**: Your StableQueue API key  
- **API Secret**: Your StableQueue API secret

The extension will automatically discover available servers once credentials are configured.

## Technical Implementation

### Key Components

- **`scripts/stablequeue.py`**: Main AlwaysOnScript implementation with `process()` hook
- **`javascript/stablequeue.js`**: Minimal UI-only JavaScript (no generation triggers)
- **Parameter Extraction**: Research-backed approach using `StableDiffusionProcessing` object
- **ControlNet Integration**: Proper 15-parameter parsing for ControlNet units

### Research Insights Applied

This extension implements the findings from extensive research into Forge's parameter capture mechanisms:

- ✅ **AlwaysOnScript `process()` hook**: The only reliable interception point
- ✅ **StableDiffusionProcessing object**: Contains complete parameter state
- ✅ **Native Gradio flow**: Queue buttons work through normal generation pipeline
- ❌ **Artificial button triggering**: Explicitly avoided (causes instability)
- ❌ **JavaScript parameter extraction**: Unreliable and incomplete

## API Integration

The extension uses StableQueue's v2 API format:

```json
{
  "app_type": "forge",
  "target_server_alias": "server_alias",
  "generation_params": {
    "positive_prompt": "...",
    "negative_prompt": "...",
    "width": 512,
    "height": 512,
    "steps": 20,
    "cfg_scale": 7.0,
    // ... complete parameter set
  },
  "alwayson_scripts": {
    "controlnet": [...],
    // ... other extensions
  }
}
```

## Troubleshooting

### Queue Button Not Working

1. **Check Forge logs** for StableQueue messages
2. **Verify API credentials** in Settings > StableQueue  
3. **Refresh servers list** using 🔄 button
4. **Check StableQueue server** is running and accessible

### Empty Parameters in Queue

This indicates the `process()` hook isn't being triggered:
- Ensure extension is properly installed in `extensions/StableQueue-Forge-Extension/`
- Restart Forge to reload extensions
- Check for conflicts with other queue-related extensions

### ControlNet Parameters Missing

- Verify ControlNet extension is installed and enabled
- Check that ControlNet units are configured before queuing
- Review logs for ControlNet parsing errors

## Development

### Research Documentation

See `/docs/Forge Parameter Capture Research_.md` for detailed technical research that informed this implementation.

### Architecture Principles

1. **Follow Forge's Natural Flow**: Work with Gradio's event system, not against it
2. **Minimal JavaScript**: Keep browser-side code simple and focused on UI only
3. **Complete Parameter Capture**: Use the `StableDiffusionProcessing` object as the authoritative source
4. **Error Handling**: Graceful degradation when parameters can't be extracted

## License

This project is licensed under the MIT License - see the LICENSE file for details.
