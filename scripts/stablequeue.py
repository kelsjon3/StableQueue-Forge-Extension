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
        self.last_params_content = ""
        self.monitoring_thread = None
        self.monitoring_active = False
        self.params_file_path = "params.txt"
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
        """Create Gradio UI components for StableQueue integration"""
        
        # Refresh servers list on UI load
        if not self.servers_list:
            self.fetch_servers()
        
        with gr.Accordion("StableQueue", open=False):
            with gr.Row():
                # Server selection dropdown
                server_dropdown = gr.Dropdown(
                    label="Target Server",
                    choices=self.servers_list if self.servers_list else ["Configure API key in settings"],
                    value=self.servers_list[0] if self.servers_list else "Configure API key in settings",
                    elem_id=f"stablequeue_server_{'img2img' if is_img2img else 'txt2img'}"
                )
                
                # Refresh servers button
                refresh_btn = gr.Button("🔄", scale=0, min_width=40)
            
            with gr.Row():
                # Queue buttons
                queue_btn = gr.Button("Queue in StableQueue", variant="primary")
                bulk_queue_btn = gr.Button("Bulk Queue", variant="secondary")
            
            # Status display
            status_display = gr.HTML("")
            
            # Queue intent flags (hidden from user)
            queue_intent = gr.State(False)
            bulk_intent = gr.State(False)
            selected_server = gr.State("")
            
            # Event handlers
            def refresh_servers():
                if self.fetch_servers():
                    choices = self.servers_list if self.servers_list else ["Configure API key in settings"]
                    value = self.servers_list[0] if self.servers_list else "Configure API key in settings"
                    return gr.Dropdown.update(choices=choices, value=value), f"<span style='color:green'>✓ Found {len(self.servers_list)} server(s)</span>"
                else:
                    return gr.Dropdown.update(choices=["Configure API key in settings"], value="Configure API key in settings"), "<span style='color:red'>✗ Failed to refresh servers</span>"
            
            def queue_job_now(server_alias):
                """Queue job immediately by extracting current UI parameters"""
                if not server_alias or server_alias == "Configure API key in settings":
                    return False, "", "<span style='color:red'>✗ Please select a valid server</span>"
                
                print(f"[StableQueue] Queue button clicked for server: {server_alias}")
                
                try:
                    # Get StableQueue settings
                    server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
                    api_key = shared.opts.data.get("stablequeue_api_key", "")
                    api_secret = shared.opts.data.get("stablequeue_api_secret", "")
                    
                    if not all([server_url, api_key, api_secret]):
                        return False, "", "<span style='color:red'>✗ StableQueue credentials not configured in settings</span>"
                    
                    # Extract current UI parameters
                    tab_id = 'img2img' if is_img2img else 'txt2img'
                    params = self.extract_current_ui_parameters(tab_id)
                    
                    # Set the target server alias
                    params["target_server_alias"] = server_alias
                    
                    # Submit to StableQueue
                    success = self.submit_to_stablequeue(params, server_url, api_key, api_secret)
                    
                    if success:
                        return True, server_alias, f"<span style='color:green'>✓ Job queued successfully on {server_alias}</span>"
                    else:
                        return False, "", f"<span style='color:red'>✗ Failed to queue job on {server_alias}</span>"
                        
                except Exception as e:
                    print(f"[StableQueue] Error in queue_job_now: {e}")
                    return False, "", f"<span style='color:red'>✗ Error: {str(e)}</span>"
            
            def bulk_queue_job_now(server_alias):
                """Bulk queue job immediately by extracting current UI parameters"""
                if not server_alias or server_alias == "Configure API key in settings":
                    return False, "", "<span style='color:red'>✗ Please select a valid server</span>"
                
                print(f"[StableQueue] Bulk queue button clicked for server: {server_alias}")
                
                try:
                    # Get StableQueue settings
                    server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
                    api_key = shared.opts.data.get("stablequeue_api_key", "")
                    api_secret = shared.opts.data.get("stablequeue_api_secret", "")
                    
                    if not all([server_url, api_key, api_secret]):
                        return False, "", "<span style='color:red'>✗ StableQueue credentials not configured in settings</span>"
                    
                    # Extract current UI parameters
                    tab_id = 'img2img' if is_img2img else 'txt2img'
                    params = self.extract_current_ui_parameters(tab_id)
                    
                    # Set the target server alias
                    params["target_server_alias"] = server_alias
                    
                    # Get bulk quantity from settings
                    bulk_quantity = shared.opts.data.get("stablequeue_bulk_quantity", 10)
                    
                    # Submit multiple jobs
                    success_count = 0
                    for i in range(bulk_quantity):
                        # Vary the seed for each job
                        bulk_params = params.copy()
                        if bulk_params.get('seed', -1) != -1:
                            bulk_params['seed'] = bulk_params['seed'] + i
                        
                        success = self.submit_to_stablequeue(bulk_params, server_url, api_key, api_secret)
                        if success:
                            success_count += 1
                    
                    if success_count > 0:
                        return True, server_alias, f"<span style='color:green'>✓ {success_count}/{bulk_quantity} bulk jobs queued on {server_alias}</span>"
                    else:
                        return False, "", f"<span style='color:red'>✗ Failed to queue bulk jobs on {server_alias}</span>"
                        
                except Exception as e:
                    print(f"[StableQueue] Error in bulk_queue_job_now: {e}")
                    return False, "", f"<span style='color:red'>✗ Error: {str(e)}</span>"
            
            # Wire up the event handlers
            refresh_btn.click(
                fn=refresh_servers,
                outputs=[server_dropdown, status_display]
            )
            
            # Wire up queue buttons to set intent and trigger generation
            def queue_and_generate(server_alias):
                """Set queue intent and trigger generation in one action"""
                # First set the intent
                queue_intent_val, selected_server_val, status_msg = queue_job_now(server_alias)
                
                # Return the values that will be used by the next generation
                return queue_intent_val, selected_server_val, status_msg
            
            def bulk_queue_and_generate(server_alias):
                """Set bulk queue intent and trigger generation in one action"""
                # First set the intent
                bulk_intent_val, selected_server_val, status_msg = bulk_queue_job_now(server_alias)
                
                # Return the values that will be used by the next generation
                return bulk_intent_val, selected_server_val, status_msg
            
            queue_btn.click(
                fn=queue_and_generate,
                inputs=[server_dropdown],
                outputs=[queue_intent, selected_server, status_display]
            )
            
            bulk_queue_btn.click(
                fn=bulk_queue_and_generate,
                inputs=[server_dropdown], 
                outputs=[bulk_intent, selected_server, status_display]
            )
        
        # Return the components in the order expected by script_args
        return [queue_intent, bulk_intent, selected_server]
    
    def fetch_servers(self):
        """Fetch available server aliases from StableQueue"""
        try:
            server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")
            
            response = requests.get(
                f"{server_url}/api/v1/servers",
                headers={
                    "X-API-Key": api_key,
                    "X-API-Secret": api_secret
                },
                timeout=5
            )
            
            if response.status_code == 200:
                self.servers_list = [server["alias"] for server in response.json()]
                return True
            else:
                print(f"[StableQueue] Failed to fetch servers: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[StableQueue] Error fetching servers: {str(e)}")
            return False

    def process(self, p: StableDiffusionProcessing, *args):
        """
        This hook is called with the complete StableDiffusionProcessing object
        containing all parameters from UI and extensions.
        
        Uses both direct Gradio integration and global flags to detect queue intent.
        """
        try:
            # Extract our UI component values from args
            # args order: [queue_intent, bulk_intent, selected_server]
            if len(args) >= 3:
                queue_intent = args[0] if args[0] is not None else False
                bulk_intent = args[1] if args[1] is not None else False
                selected_server = args[2] if args[2] is not None else ""
                
                print(f"[StableQueue] Process hook - queue_intent: {queue_intent}, bulk_intent: {bulk_intent}, server: {selected_server}")
                
                # Check if this is a queue request
                if queue_intent or bulk_intent:
                    job_type = "bulk" if bulk_intent else "single"
                    
                    # Validate server selection
                    if not selected_server or selected_server == "Configure API key in settings":
                        print(f"[StableQueue] ✗ No valid server selected, allowing local generation")
                        return None
                    
                    # Get StableQueue settings
                    server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
                    api_key = shared.opts.data.get("stablequeue_api_key", "")
                    api_secret = shared.opts.data.get("stablequeue_api_secret", "")
                    
                    if not all([server_url, api_key, api_secret]):
                        print(f"[StableQueue] ✗ Credentials not configured, allowing local generation")
                        return None
                    
                    print(f"[StableQueue] ✓ Intercepting generation for {job_type} queue on server: {selected_server}")
                    
                    # Extract complete parameters using our proven method
                    params = self.extract_complete_parameters(p)
                    
                    # Submit to StableQueue
                    success = self.submit_to_stablequeue(params, server_url, api_key, api_secret)
                    
                    if success:
                        print(f"[StableQueue] ✓ {job_type.title()} job queued successfully, preventing local generation")
                        
                        # Prevent local generation by returning empty result
                        return Processed(
                            p,
                            images_list=[],
                            seed=p.seed,
                            info=f"Job queued in StableQueue ({job_type}) - local generation skipped",
                            subseed=p.subseed,
                            all_prompts=[p.prompt],
                            all_seeds=[p.seed],
                            all_subseeds=[p.subseed],
                            infotexts=[f"Job queued in StableQueue ({job_type}) on {selected_server}"]
                        )
                    else:
                        print(f"[StableQueue] ✗ Failed to queue {job_type} job, allowing local generation")
                        return None
            
            # No queue intent - continue with normal processing
            return None
                
        except Exception as e:
            print(f"[StableQueue] Error in process hook: {e}")
            import traceback
            print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
            return None  # Continue with normal processing on error

    def extract_complete_parameters(self, p: StableDiffusionProcessing):
        """Extract all parameters from the StableDiffusionProcessing object"""
        
        # Core parameters
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
            "override_settings": p.override_settings if hasattr(p, 'override_settings') else {},
        }
        
        # High-res fix parameters
        if hasattr(p, 'enable_hr'):
            params.update({
                "enable_hr": p.enable_hr,
                "hr_scale": getattr(p, 'hr_scale', 2.0),
                "hr_upscaler": getattr(p, 'hr_upscaler', 'Latent'),
                "hr_second_pass_steps": getattr(p, 'hr_second_pass_steps', 0),
                "denoising_strength": getattr(p, 'denoising_strength', 0.7),
            })
        
        # Model information
        if hasattr(p, 'sd_model') and p.sd_model:
            # Handle CheckpointInfo object properly
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
                params["checkpoint_name"] = ''
            
            params["model_hash"] = getattr(p.sd_model, 'sd_model_hash', '')
        
        # Extension parameters from script_args
        if hasattr(p, 'scripts') and hasattr(p.scripts, 'alwayson_scripts') and p.script_args:
            params["alwayson_scripts"] = {}
            
            try:
                for script in p.scripts.alwayson_scripts:
                    if hasattr(script, 'args_from') and hasattr(script, 'args_to'):
                        script_name = script.title().lower().replace(' ', '_')
                        script_args = p.script_args[script.args_from:script.args_to]
                        
                        # Special handling for known extensions
                        if 'controlnet' in script_name.lower():
                            params["alwayson_scripts"][script_name] = self.parse_controlnet_args(script_args)
                        else:
                            # Generic handling for unknown extensions
                            params["alwayson_scripts"][script_name] = script_args
                            
                print(f"[StableQueue] Captured {len(params['alwayson_scripts'])} extension(s)")
                        
            except Exception as e:
                print(f"[StableQueue] Warning: Could not parse script_args: {e}")
                params["alwayson_scripts"] = {}
        
        return params

    def parse_controlnet_args(self, args):
        """Parse ControlNet arguments into structured format"""
        try:
            # ControlNet typically has 15-20 args per unit
            # This is a basic parser - may need adjustment based on ControlNet version
            units = []
            args_per_unit = 15  # Adjust based on actual ControlNet structure
            
            for i in range(0, len(args), args_per_unit):
                unit_args = args[i:i + args_per_unit]
                if len(unit_args) >= args_per_unit and unit_args[0]:  # Check if enabled
                    unit = {
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
                    units.append(unit)
            
            return {"units": units}
            
        except Exception as e:
            print(f"[StableQueue] Warning: Could not parse ControlNet args: {e}")
            return {"raw_args": args}

    def submit_to_stablequeue(self, params, server_url, api_key, api_secret):
        """Submit job to StableQueue server using v2 API"""
        try:
            # Format payload according to StableQueue v2 API specification
            payload = {
                "app_type": "forge",
                "target_server_alias": params.get("target_server_alias", "default"),
                "generation_params": {
                    "positive_prompt": params.get("prompt", ""),
                    "negative_prompt": params.get("negative_prompt", ""),
                    "width": params.get("width", 512),
                    "height": params.get("height", 512),
                    "steps": params.get("steps", 20),
                    "cfg_scale": params.get("cfg_scale", 7.0),
                    "sampler_name": params.get("sampler_name", "Euler"),
                    "seed": params.get("seed", -1),
                    "batch_size": params.get("batch_size", 1),
                    "n_iter": params.get("n_iter", 1),
                    "restore_faces": params.get("restore_faces", False),
                    "checkpoint_name": params.get("checkpoint_name", ""),
                    "enable_hr": params.get("enable_hr", False),
                    "hr_scale": params.get("hr_scale", 2.0),
                    "hr_upscaler": params.get("hr_upscaler", "Latent"),
                    "denoising_strength": params.get("denoising_strength", 0.7),
                },
                "source_info": "forge_extension_v1.0.0"
            }
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            url = f"{server_url.rstrip('/')}/api/v2/generate"
            
            print(f"[StableQueue] Submitting to {url}")
            print(f"[StableQueue] Target server: {payload['target_server_alias']}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 202:  # StableQueue v2 returns 202 Accepted
                result = response.json()
                job_id = result.get('mobilesd_job_id', 'unknown')
                print(f"[StableQueue] ✓ Job queued with ID: {job_id}")
                return True
            else:
                print(f"[StableQueue] ✗ Failed to queue: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"[StableQueue] ✗ Timeout connecting to StableQueue server")
            return False
        except Exception as e:
            print(f"[StableQueue] ✗ Error submitting job: {e}")
            return False

    def extract_current_ui_parameters(self, tab_id):
        """Extract current UI parameters using a simplified approach"""
        try:
            print(f"[StableQueue] Extracting parameters from {tab_id} tab")
            
            # Create basic parameters with default values
            # This is a simplified approach - in a real implementation, 
            # we would need to access the actual Gradio component values
            params = {
                "prompt": "A beautiful landscape",  # Default prompt
                "negative_prompt": "",
                "steps": 20,
                "sampler_name": "Euler",
                "cfg_scale": 7.0,
                "width": 512,
                "height": 512,
                "seed": -1,
                "subseed": -1,
                "subseed_strength": 0,
                "batch_size": 1,
                "n_iter": 1,
                "restore_faces": False,
                "tiling": False,
                "send_images": True,
                "save_images": True,
                "override_settings": {},
                "alwayson_scripts": {}
            }
            
            # Add tab-specific parameters
            if tab_id == 'img2img':
                params.update({
                    "init_images": [],
                    "denoising_strength": 0.75,
                    "resize_mode": 0,
                    "mask": None,
                    "mask_blur": 4,
                    "inpainting_fill": 1,
                    "inpaint_full_res": True,
                    "inpaint_full_res_padding": 0,
                    "inpainting_mask_invert": 0,
                })
            
            # Add model information if available
            if hasattr(shared, 'sd_model') and shared.sd_model:
                checkpoint_info = getattr(shared.sd_model, 'sd_checkpoint_info', None)
                if checkpoint_info:
                    if hasattr(checkpoint_info, 'name'):
                        params["checkpoint_name"] = checkpoint_info.name
                    elif hasattr(checkpoint_info, 'model_name'):
                        params["checkpoint_name"] = checkpoint_info.model_name
                    else:
                        params["checkpoint_name"] = str(checkpoint_info)
                else:
                    params["checkpoint_name"] = ''
                
                params["model_hash"] = getattr(shared.sd_model, 'sd_model_hash', '')
            
            print(f"[StableQueue] Extracted {len(params)} parameters from {tab_id}")
            print(f"[StableQueue] Note: Using default values - actual UI parameter extraction would require more complex implementation")
            
            return params
            
        except Exception as e:
            print(f"[StableQueue] Error in extract_current_ui_parameters: {e}")
            import traceback
            print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
            raise

    def queue_job_from_javascript(self, payload_data, server_alias, job_type="single"):
        """Queue job from JavaScript frontend"""
        try:
            # Get StableQueue settings
            server_url = shared.opts.data.get("stablequeue_server_url", DEFAULT_SERVER_URL)
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")
            
            if not all([server_url, api_key, api_secret]):
                return {"success": False, "message": "StableQueue credentials not configured in Settings"}
            
            print(f"[StableQueue] Processing JavaScript job: {job_type} for server {server_alias}")
            
            # For context menu data, use payload directly
            if isinstance(payload_data, dict) and 'prompt' in payload_data:
                # This looks like complete generation parameters
                params = payload_data
            else:
                # This might be incomplete - for now just pass through
                params = payload_data
            
            # Submit to StableQueue
            success = self.submit_to_stablequeue(params, server_url, api_key, api_secret)
            
            if success:
                return {"success": True, "message": f"{job_type.title()} job queued successfully on {server_alias}"}
            else:
                return {"success": False, "message": "Failed to queue job in StableQueue"}
                
        except Exception as e:
            print(f"[StableQueue] Error in queue_job_from_javascript: {e}")
            return {"success": False, "message": f"Error: {str(e)}"}

# TODO: Phase 2 - Remove this global state approach entirely
# Global state for manual queue triggers (TO BE REMOVED)
# pending_queue_request = {
#     "enabled": False,
#     "server_alias": "",
#     "job_type": "single"
# }

# Create global instance
stablequeue_instance = StableQueueScript()



print("[StableQueue] Extension loaded - Python AlwaysOnScript approach")

# Register context menu items if enabled
def context_menu_entries():
    if shared.opts.data.get("enable_stablequeue_context_menu", True):
        return [
            {"label": "Send to StableQueue", "action": "stablequeue_send_single", "tooltip": "Send current generation to StableQueue queue"},
            {"label": "Send bulk job to StableQueue", "action": "stablequeue_send_bulk", "tooltip": "Send multiple jobs with current settings to StableQueue queue"}
        ]
    return []

# This list will hold JavaScript callbacks for context menu actions
js_callbacks = []

# Create StableQueue tab
def create_stablequeue_tab():
    """Create the StableQueue tab in the main interface"""
    try:
        print(f"[StableQueue] create_stablequeue_tab() called - Creating tab interface...")
        
        stablequeue_instance = StableQueueScript()
        print(f"[StableQueue] StableQueue instance created successfully")
        
        with gr.Blocks(analytics_enabled=False) as stablequeue_interface:
            print(f"[StableQueue] Creating gradio interface...")
            
            with gr.Row():
                with gr.Column():
                    server_alias = gr.Dropdown(
                        label="Target Server", 
                        choices=stablequeue_instance.servers_list if stablequeue_instance.servers_list else ["Configure API key in settings"],
                        interactive=True,
                        elem_id="stablequeue_server_dropdown"
                    )
                    priority = gr.Slider(
                        minimum=1, 
                        maximum=10, 
                        value=5, 
                        step=1, 
                        label="Priority"
                    )
            
            with gr.Row():
                refresh_btn = gr.Button("🔄 Refresh Servers")
            
            status_html = gr.HTML("<div>Not connected to StableQueue</div>")
            
            # Refresh button to update server list
            def refresh_servers():
                print(f"[StableQueue] Refresh servers button clicked")
                if stablequeue_instance.fetch_servers():
                    print(f"[StableQueue] Server refresh successful: {len(stablequeue_instance.servers_list)} servers")
                    return gr.Dropdown.update(choices=stablequeue_instance.servers_list), f"<div style='color:green'>Refreshed server list. Found {len(stablequeue_instance.servers_list)} server(s).</div>"
                else:
                    print(f"[StableQueue] Server refresh failed")
                    return gr.Dropdown.update(choices=["Configure API key in settings"]), "<div style='color:red'>Failed to refresh server list. Check API key in settings.</div>"
            
            refresh_btn.click(
                fn=refresh_servers,
                inputs=[],
                outputs=[server_alias, status_html]
            )
            
            # Information about how to use the extension
            gr.HTML("""
            <div style='margin-top: 20px; padding: 15px; background-color: rgba(0,100,200,0.1); border-radius: 8px;'>
                <h3>How to Use StableQueue:</h3>
                <ul>
                    <li><strong>Queue Jobs:</strong> Use the 'Queue in StableQueue' buttons next to the Generate buttons in txt2img/img2img tabs</li>
                    <li><strong>Bulk Jobs:</strong> Use the 'Bulk Queue' buttons for multiple job submission</li>
                    <li><strong>Context Menu:</strong> Right-click on generation results to send to StableQueue</li>
                    <li><strong>Settings:</strong> Configure API credentials in Settings → StableQueue Integration</li>
                </ul>
            </div>
            """)
        
        print(f"[StableQueue] Gradio interface created successfully - Returning tab tuple")
        return [(stablequeue_interface, "StableQueue", "stablequeue")]
        
    except Exception as e:
        print(f"[StableQueue] ERROR in create_stablequeue_tab: {e}")
        import traceback
        print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
        return []

# Register the tab
print(f"[StableQueue] Registering StableQueue tab with script_callbacks.on_ui_tabs...")
script_callbacks.on_ui_tabs(create_stablequeue_tab)
print(f"[StableQueue] Tab registration completed")

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

# Alternative approach: Use Forge's API system instead of direct FastAPI access
def setup_javascript_api(demo=None, app=None):
    """Setup API endpoints using Forge's API system"""
    global api_setup_completed
    
    print(f"[StableQueue] setup_javascript_api called with demo={demo}, app={app}")
    
    if api_setup_completed:
        print(f"[StableQueue] API already set up, skipping...")
        return
        
    print(f"[StableQueue] Setting up JavaScript API endpoints...")
    
    try:
        # Try to use modules.api if available (newer Forge versions)
        try:
            from modules import api
            print(f"[StableQueue] Found modules.api, attempting to register endpoint...")
            
            # Register our endpoint with the API
            def queue_job_endpoint():
                from flask import request, jsonify
                try:
                    print(f"[StableQueue] queue_job_endpoint called via modules.api")
                    
                    data = request.get_json()
                    api_payload_json = json.dumps(data.get('api_payload', {}))
                    server_alias = data.get('server_alias', '')
                    job_type = data.get('job_type', 'single')
                    
                    print(f"[StableQueue] Processing job: server={server_alias}, type={job_type}")
                    
                    result = stablequeue_instance.queue_job_from_javascript(api_payload, server_alias, job_type)
                    
                    print(f"[StableQueue] Job result: {result}")
                    
                    return jsonify(result)
                    
                except Exception as e:
                    print(f"[StableQueue] Error in queue_job_endpoint: {e}")
                    return jsonify({"success": False, "message": f"API Error: {str(e)}"}), 500
            
            # Try to register the endpoint
            if hasattr(api, 'app') and hasattr(api.app, 'route'):
                api.app.route('/stablequeue/queue_job', methods=['POST'])(queue_job_endpoint)
                print(f"[StableQueue] Successfully registered endpoint via modules.api")
                api_setup_completed = True
                return
                
        except ImportError:
            print(f"[StableQueue] modules.api not available, trying FastAPI approach...")
        
        # Fallback to FastAPI approach
        from modules import shared
        import json
        
        print(f"[StableQueue] Checking for FastAPI app...")
        
        # First check if we got the app passed as parameter
        if app is not None:
            print(f"[StableQueue] Using FastAPI app passed as parameter: {type(app)}")
        else:
            # Try multiple ways to get the FastAPI app
            print(f"[StableQueue] No app parameter, searching for FastAPI app...")
            
            # Method 1: Check shared.demo.app
            if hasattr(shared, 'demo') and hasattr(shared.demo, 'app'):
                app = shared.demo.app
                print(f"[StableQueue] Found FastAPI app via shared.demo.app")
            
            # Method 2: Check if there's a direct app reference
            elif hasattr(shared, 'app'):
                app = shared.app
                print(f"[StableQueue] Found FastAPI app via shared.app")
            
            # Method 3: Try to get from gradio app
            elif hasattr(shared, 'demo') and hasattr(shared.demo, 'fastapi_app'):
                app = shared.demo.fastapi_app
                print(f"[StableQueue] Found FastAPI app via shared.demo.fastapi_app")
        
        if app is None:
            print(f"[StableQueue] Could not find FastAPI app. Available shared attributes:")
            if hasattr(shared, 'demo'):
                print(f"[StableQueue] shared.demo attributes: {dir(shared.demo)}")
            else:
                print(f"[StableQueue] shared attributes: {dir(shared)}")
            
            # Try one more time after a delay
            def retry_setup():
                print(f"[StableQueue] Retrying API setup after delay...")
                setup_javascript_api()
            
            # Schedule retry in 5 seconds
            import threading
            timer = threading.Timer(5.0, retry_setup)
            timer.start()
            return
        
        print(f"[StableQueue] FastAPI app found: {type(app)}")
        
        # Import FastAPI components
        try:
            from fastapi import Request
            from fastapi.responses import JSONResponse
        except ImportError:
            print(f"[StableQueue] FastAPI not available")
            return
        
        # TODO: Phase 1 - REMOVED /stablequeue/trigger_queue endpoint
        # This endpoint was part of the complex flag coordination system
        # that we're replacing with direct Gradio integration

        @app.post("/stablequeue/context_menu_queue")
        async def context_menu_queue_api(request: Request):
            try:
                print(f"[StableQueue] /stablequeue/context_menu_queue endpoint called")
                
                # Get request data
                data = await request.json()
                context_data = data.get('context_data', {})
                server_alias = data.get('server_alias', '')
                job_type = data.get('job_type', 'single')
                
                print(f"[StableQueue] Context menu queue: type={job_type}, server={server_alias}")
                
                # Process context menu data directly
                result = stablequeue_instance.queue_job_from_javascript(context_data, server_alias, job_type)
                
                print(f"[StableQueue] Context menu result: {result}")
                
                return JSONResponse(content=result)
                
            except Exception as e:
                print(f"[StableQueue] Error in context_menu_queue_api: {e}")
                return JSONResponse(
                    content={"success": False, "message": f"API Error: {str(e)}"}, 
                    status_code=500
                )
        
        print(f"[StableQueue] Successfully registered /stablequeue/queue_job endpoint")
        api_setup_completed = True
                    
    except Exception as e:
        print(f"[StableQueue] Could not setup JavaScript API: {e}")
        import traceback
        print(f"[StableQueue] Full error trace: {traceback.format_exc()}")

# Register the setup function with multiple callbacks to ensure it runs
print(f"[StableQueue] Registering API setup callbacks...")
script_callbacks.on_app_started(setup_javascript_api) 

# Remove on_ui_started as it doesn't exist in this Forge version
# def setup_api_on_ui_start():
#     """Alternative setup method when UI starts"""
#     print(f"[StableQueue] Attempting API setup on UI start...")
#     setup_javascript_api()
# 
# script_callbacks.on_ui_started(setup_api_on_ui_start)

# Also try immediate setup
print(f"[StableQueue] Attempting immediate API setup...")
setup_javascript_api() 