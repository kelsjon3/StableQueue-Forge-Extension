# Add at the very beginning after imports
print("=" * 50)
print("[StableQueue] Python extension is loading...")
print("[StableQueue] Extension file path:", __file__)
print("=" * 50)

import json
import modules.scripts as scripts
import gradio as gr
import requests
import os
import time
import uuid
from modules import shared
from modules.ui_components import FormRow, FormGroup, ToolButton
from modules import script_callbacks
from modules.processing import StableDiffusionProcessing, Processed

print("[StableQueue] All imports successful")

VERSION = "1.0.0"
EXTENSION_NAME = "StableQueue Extension"
DEFAULT_SERVER_URL = "http://192.168.73.124:8083"

print(f"[StableQueue] Extension initialized - Version {VERSION}")

# Global flag to track if API is set up
api_setup_completed = False

class StableQueueScript(scripts.Script):
    def __init__(self):
        self.servers_list = []
        
        # Initialize servers list if API key is available
        server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
        api_key = shared.opts.data.get("stablequeue_api_key", "")
        api_secret = shared.opts.data.get("stablequeue_api_secret", "")
        if api_key and api_secret:
            self.fetch_servers()
        
    def title(self):
        return "StableQueue"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        """UI for the StableQueue extension in the main interface"""
        with gr.Group():
            with gr.Row():
                enabled = gr.Checkbox(
                    label="Enable StableQueue Auto-Capture", 
                    value=False,
                    elem_id=f"stablequeue_enabled_{'img2img' if is_img2img else 'txt2img'}"
                )
                
                server_dropdown = gr.Dropdown(
                    label="Target Server",
                    choices=self.servers_list if self.servers_list else ["Configure API credentials in Settings"],
                    value=self.servers_list[0] if self.servers_list else "Configure API credentials in Settings",
                    elem_id=f"stablequeue_server_{'img2img' if is_img2img else 'txt2img'}"
                )
                
                action_dropdown = gr.Dropdown(
                    label="Action",
                    choices=["Queue Only", "Queue + Generate Locally", "Generate Locally Only"],
                    value="Generate Locally Only",
                    elem_id=f"stablequeue_action_{'img2img' if is_img2img else 'txt2img'}"
                )
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Servers", size="sm")
                priority_slider = gr.Slider(
                    minimum=1, maximum=10, value=5, step=1,
                    label="Queue Priority"
                )
            
            status_display = gr.HTML("<div style='color: gray;'>StableQueue ready</div>")
            
            # Refresh servers functionality
            def refresh_servers():
                if self.fetch_servers():
                    new_choices = self.servers_list if self.servers_list else ["Configure API credentials in Settings"]
                    return gr.Dropdown.update(choices=new_choices, value=new_choices[0])
                return gr.Dropdown.update()
            
            refresh_btn.click(refresh_servers, outputs=[server_dropdown])
        
        return [enabled, server_dropdown, action_dropdown, priority_slider]
    
    def fetch_servers(self):
        """Fetch available server aliases from StableQueue"""
        try:
            server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")
            
            response = requests.get(
                f"{server_url}/api/v1/queue/servers",
                headers={
                    "X-API-Key": api_key,
                    "X-API-Secret": api_secret
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                self.servers_list = [server["alias"] for server in data.get("servers", [])]
                print(f"[StableQueue] Fetched {len(self.servers_list)} servers: {self.servers_list}")
                return True
            else:
                print(f"[StableQueue] Failed to fetch servers: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[StableQueue] Error fetching servers: {str(e)}")
            return False

    def process(self, p: StableDiffusionProcessing, enabled, server_alias, action, priority):
        """
        Intercept every generation attempt and handle according to user's choice.
        This is called with the complete StableDiffusionProcessing object.
        """
        try:
            print(f"[StableQueue] Process hook called - enabled: {enabled}, action: {action}")
            
            # If StableQueue is not enabled, continue with normal generation
            if not enabled:
                print("[StableQueue] Not enabled, allowing normal generation")
                return None
            
            # Validate server selection  
            if not server_alias or server_alias == "Configure API credentials in Settings":
                print("[StableQueue] ✗ No valid server selected")
                return Processed(
                    p, images_list=[], seed=p.seed,
                    info="❌ StableQueue Error: No server selected. Please configure servers in Settings.",
                    subseed=p.subseed, all_prompts=[p.prompt], all_seeds=[p.seed], 
                    all_subseeds=[p.subseed], infotexts=["StableQueue: No server selected"]
                )
            
            # Extract complete parameters using research-recommended approach
            print(f"[StableQueue] Extracting complete parameters from StableDiffusionProcessing object")
            params = self.extract_complete_parameters(p)
            
            # Handle based on user's selected action
            if action == "Generate Locally Only":
                print("[StableQueue] User selected local generation only")
                return None  # Continue with normal generation
                
            elif action == "Queue Only":
                print(f"[StableQueue] Queuing job to {server_alias}, preventing local generation")
                success = self.submit_to_stablequeue(params, server_alias, priority)
                
                if success:
                    return Processed(
                        p, images_list=[], seed=p.seed,
                        info=f"✅ Job queued successfully to {server_alias}. Local generation skipped.",
                        subseed=p.subseed, all_prompts=[p.prompt], all_seeds=[p.seed],
                        all_subseeds=[p.subseed], infotexts=[f"Queued to StableQueue: {server_alias}"]
                    )
                else:
                    return Processed(
                        p, images_list=[], seed=p.seed,
                        info="❌ Failed to queue job. Check server connection and try again.",
                        subseed=p.subseed, all_prompts=[p.prompt], all_seeds=[p.seed],
                        all_subseeds=[p.subseed], infotexts=["StableQueue: Queue failed"]
                    )
                    
            elif action == "Queue + Generate Locally":
                print(f"[StableQueue] Queuing job to {server_alias} AND allowing local generation")
                # Queue job but don't prevent local generation
                self.submit_to_stablequeue(params, server_alias, priority)
                return None  # Continue with normal generation
                
        except Exception as e:
            print(f"[StableQueue] Error in process hook: {e}")
            import traceback
            print(f"[StableQueue] Traceback: {traceback.format_exc()}")
            return None  # Continue with normal generation on error

    def extract_complete_parameters(self, p: StableDiffusionProcessing):
        """
        Extract all parameters from StableDiffusionProcessing object following research recommendations.
        This includes core parameters and extension data from script_args.
        """
        
        # Core parameters - direct from p object
        params = {
            "prompt": p.prompt,
            "negative_prompt": p.negative_prompt,
            "steps": p.steps,
            "sampler_name": p.sampler_name,
            "cfg_scale": p.cfg_scale,
            "width": p.width,
            "height": p.height,
            "seed": p.seed,
            "subseed": p.subseed,
            "subseed_strength": p.subseed_strength,
            "batch_size": p.batch_size,
            "n_iter": p.n_iter,
            "restore_faces": p.restore_faces,
            "tiling": p.tiling,
            "send_images": True,
            "save_images": True,
        }
        
        # Override settings (critical per research document)
        if hasattr(p, 'override_settings') and p.override_settings:
            params["override_settings"] = p.override_settings
            # Research suggests these should supersede core parameters
            params.update(p.override_settings)
        
        # High-res fix parameters
        if hasattr(p, 'enable_hr'):
            params.update({
                "enable_hr": p.enable_hr,
                "hr_scale": getattr(p, 'hr_scale', 2.0),
                "hr_upscaler": getattr(p, 'hr_upscaler', 'Latent'),
                "hr_second_pass_steps": getattr(p, 'hr_second_pass_steps', 0),
                "denoising_strength": getattr(p, 'denoising_strength', 0.7),
            })
        
        # Model information (essential for reproducibility per research)
        if hasattr(p, 'sd_model') and p.sd_model:
            checkpoint_info = getattr(p.sd_model, 'sd_checkpoint_info', None)
            if checkpoint_info:
                if hasattr(checkpoint_info, 'name'):
                    params["checkpoint_name"] = checkpoint_info.name
                elif hasattr(checkpoint_info, 'model_name'):
                    params["checkpoint_name"] = checkpoint_info.model_name
                elif hasattr(checkpoint_info, 'filename'):
                    import os
                    params["checkpoint_name"] = os.path.basename(checkpoint_info.filename)
                else:
                    params["checkpoint_name"] = str(checkpoint_info)
            else:
                params["checkpoint_name"] = getattr(p.sd_model, 'model_name', '')
            
            params["model_hash"] = getattr(p.sd_model, 'sd_model_hash', '')
        
        # Extension parameters from script_args (following research methodology)
        params["alwayson_scripts"] = {}
        
        if hasattr(p, 'scripts') and hasattr(p.scripts, 'alwayson_scripts') and hasattr(p, 'script_args'):
            print(f"[StableQueue] Processing {len(p.scripts.alwayson_scripts)} AlwaysOnScripts")
            
            for script in p.scripts.alwayson_scripts:
                try:
                    script_key = script.title().lower().replace(' ', '_').replace('-', '_')
                    
                    # Get script's argument slice using research-recommended method
                    if hasattr(script, 'args_from') and hasattr(script, 'args_to'):
                        args_slice = p.script_args[script.args_from:script.args_to]
                        print(f"[StableQueue] {script_key}: {len(args_slice)} args from {script.args_from} to {script.args_to}")
                        
                        # For known extensions, parse into structured format
                        if 'controlnet' in script_key:
                            params["alwayson_scripts"][script_key] = self.parse_controlnet_args(args_slice)
                        else:
                            # Generic handling for unknown extensions (as recommended by research)
                            params["alwayson_scripts"][script_key] = args_slice
                    else:
                        print(f"[StableQueue] Warning: {script_key} missing args_from/args_to")
                        
                except Exception as e:
                    print(f"[StableQueue] Error processing script {script.title()}: {e}")
        
        print(f"[StableQueue] Extracted parameters for {len(params.get('alwayson_scripts', {}))} extensions")
        return params
    
    def parse_controlnet_args(self, args):
        """
        Parse ControlNet script_args slice following research document Table structure.
        Each ControlNet unit has approximately 15 parameters.
        """
        controlnet_units = []
        
        # Research suggests ~15 args per ControlNet unit, but let's detect dynamically
        # by looking for the pattern of enabled flags
        args_per_unit = 15  # Default from research, but could be different
        
        try:
            # Process in chunks of args_per_unit
            for i in range(0, len(args), args_per_unit):
                unit_args = args[i:i + args_per_unit]
                
                if len(unit_args) < args_per_unit:
                    break  # Incomplete unit
                
                # Parse according to research document table structure
                unit_data = {
                    "enabled": unit_args[0] if len(unit_args) > 0 else False,
                    "module": unit_args[1] if len(unit_args) > 1 else "",
                    "model": unit_args[2] if len(unit_args) > 2 else "",
                    "weight": unit_args[3] if len(unit_args) > 3 else 1.0,
                    "image": unit_args[4] if len(unit_args) > 4 else None,
                    "resize_mode": unit_args[5] if len(unit_args) > 5 else 0,
                    "low_vram": unit_args[6] if len(unit_args) > 6 else False,
                    "processor_res": unit_args[7] if len(unit_args) > 7 else 512,
                    "threshold_a": unit_args[8] if len(unit_args) > 8 else 0.5,
                    "threshold_b": unit_args[9] if len(unit_args) > 9 else 0.5,
                    "guidance_start": unit_args[10] if len(unit_args) > 10 else 0.0,
                    "guidance_end": unit_args[11] if len(unit_args) > 11 else 1.0,
                    "control_mode": unit_args[12] if len(unit_args) > 12 else 0,
                    "pixel_perfect": unit_args[13] if len(unit_args) > 13 else False,
                }
                
                # Only include enabled units
                if unit_data["enabled"]:
                    controlnet_units.append(unit_data)
                    
        except Exception as e:
            print(f"[StableQueue] Error parsing ControlNet args: {e}")
            # Fallback to raw args if parsing fails
            return args
            
        return controlnet_units

    def submit_to_stablequeue(self, params, server_alias, priority=5):
        """Submit job to StableQueue API"""
        try:
            server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")

            if not all([server_url, api_key, api_secret]):
                print(f"[StableQueue] ✗ Missing credentials")
                return False

            payload = {
                "payload": params,
                "api_key": api_key,
                "api_secret": api_secret,
                "priority": priority,
                "server_alias": server_alias
            }

            print(f"[StableQueue] Submitting to {server_url}/api/v2/generation/enqueue")
            
            response = requests.post(
                f"{server_url}/api/v2/generation/enqueue",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": api_key,
                    "X-API-Secret": api_secret
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                print(f"[StableQueue] ✓ Job queued successfully: {result}")
                return True
            else:
                print(f"[StableQueue] ✗ Queue failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"[StableQueue] ✗ Error submitting job: {e}")
            return False

# Create global instance
stablequeue_instance = StableQueueScript()

print("[StableQueue] Extension loaded - Python AlwaysOnScript with research-recommended approach")

# Register settings
def register_stablequeue_settings():
    """Register StableQueue settings with Forge"""
    section = ('stablequeue', "StableQueue Integration")
    
    # Add settings
    shared.opts.add_option("stablequeue_url", shared.OptionInfo(
        DEFAULT_SERVER_URL, "StableQueue Server URL", section=section
    ))
    
    shared.opts.add_option("stablequeue_api_key", shared.OptionInfo(
        "", "API Key", section=section
    ))
    
    shared.opts.add_option("stablequeue_api_secret", shared.OptionInfo(
        "", "API Secret", section=section
    ))
    
    shared.opts.add_option("stablequeue_bulk_quantity", shared.OptionInfo(
        10, "Bulk Job Quantity", section=section
    ))
    
    shared.opts.add_option("stablequeue_job_delay", shared.OptionInfo(
        5, "Delay Between Jobs (seconds)", section=section
    ))
    
    shared.opts.add_option("enable_stablequeue_context_menu", shared.OptionInfo(
        True, "Add StableQueue options to generation context menu", section=section
    ))

# Register settings callback
script_callbacks.on_ui_settings(register_stablequeue_settings)

print(f"[StableQueue] Extension setup complete - ready to intercept generation parameters automatically") 