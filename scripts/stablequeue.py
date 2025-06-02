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
        
    def title(self):
        return "StableQueue"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        return []

    def process(self, p: StableDiffusionProcessing, *args):
        """
        This hook is called with the complete StableDiffusionProcessing object
        containing all parameters from UI and extensions.
        """
        global pending_queue_request
        
        try:
            # Get StableQueue settings
            server_url = shared.opts.data.get("stablequeue_server_url", "")
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")
            auto_queue = shared.opts.data.get("stablequeue_auto_queue", False)
            
            # Check if there's a pending manual queue request
            manual_queue = pending_queue_request.get("enabled", False)
            
            if not (auto_queue or manual_queue) or not all([server_url, api_key, api_secret]):
                # Neither auto-queueing nor manual queue enabled, or credentials not configured
                return
                
            print(f"[StableQueue] Intercepting generation with {len(p.script_args)} script args")
            
            # Extract complete parameters
            params = self.extract_complete_parameters(p)
            
            # Use server alias from pending request if manual queue, otherwise default
            target_server = pending_queue_request.get("server_alias", "") if manual_queue else ""
            job_type = pending_queue_request.get("job_type", "single") if manual_queue else "single"
            
            # Submit to StableQueue
            success = self.submit_to_stablequeue(params, server_url, api_key, api_secret)
            
            # Clear pending request after processing
            if manual_queue:
                pending_queue_request["enabled"] = False
                pending_queue_request["server_alias"] = ""
                pending_queue_request["job_type"] = "single"
            
            if success:
                queue_type = "Manual" if manual_queue else "Auto"
                print(f"[StableQueue] ✓ {queue_type} job queued successfully, preventing local generation")
                
                # Prevent local generation by returning empty result
                return Processed(
                    p,
                    images_list=[],
                    seed=p.seed,
                    info=f"Job queued in StableQueue ({queue_type.lower()}) - local generation skipped",
                    subseed=p.subseed,
                    all_prompts=[p.prompt],
                    all_seeds=[p.seed],
                    all_subseeds=[p.subseed],
                    infotexts=[f"Job queued in StableQueue ({queue_type.lower()})"]
                )
            else:
                print(f"[StableQueue] ✗ Failed to queue job, allowing local generation")
                
        except Exception as e:
            print(f"[StableQueue] Error in process hook: {e}")
            # Continue with local generation on error
            
        return None  # Continue with normal processing

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
            params["checkpoint_name"] = getattr(p.sd_model, 'sd_checkpoint_info', {}).get('name', '')
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
        """Submit job to StableQueue server"""
        try:
            payload = {
                "payload": params,
                "api_key": api_key,
                "api_secret": api_secret
            }
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-API-Secret": api_secret
            }
            
            url = f"{server_url.rstrip('/')}/api/v2/generation/enqueue"
            
            print(f"[StableQueue] Submitting to {url}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                print(f"[StableQueue] ✓ Job queued with ID: {result.get('job_id', 'unknown')}")
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
        """Extract current UI parameters by creating a StableDiffusionProcessing object"""
        try:
            from modules import txt2img, img2img
            from modules.processing import StableDiffusionProcessingTxt2Img, StableDiffusionProcessingImg2Img
            from modules import shared
            
            print(f"[StableQueue] Extracting parameters from {tab_id} tab")
            
            # Get current UI values from shared state
            if tab_id == 'txt2img':
                # Create a StableDiffusionProcessing object like txt2img would
                p = StableDiffusionProcessingTxt2Img(
                    sd_model=shared.sd_model,
                    outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_txt2img_samples,
                    outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_txt2img_grids,
                    prompt="",  # Will be filled from UI
                    negative_prompt="",
                    steps=20,
                    sampler_name="Euler",
                    cfg_scale=7.0,
                    width=512,
                    height=512,
                    # These will be populated from actual UI values
                )
            else:  # img2img
                p = StableDiffusionProcessingImg2Img(
                    sd_model=shared.sd_model,
                    outpath_samples=shared.opts.outdir_samples or shared.opts.outdir_img2img_samples,
                    outpath_grids=shared.opts.outdir_grids or shared.opts.outdir_img2img_grids,
                    prompt="",
                    negative_prompt="",
                    steps=20,
                    sampler_name="Euler", 
                    cfg_scale=7.0,
                    width=512,
                    height=512,
                    init_images=[],
                    denoising_strength=0.75,
                )
            
            # TODO: Populate p with actual current UI values
            # For now, extract what we can from the processing object
            params = self.extract_complete_parameters(p)
            
            print(f"[StableQueue] Extracted {len(params)} parameters from {tab_id}")
            return params
            
        except Exception as e:
            print(f"[StableQueue] Error in extract_current_ui_parameters: {e}")
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

# Global state for manual queue triggers
pending_queue_request = {
    "enabled": False,
    "server_alias": "",
    "job_type": "single"
}

# Create global instance
stablequeue_instance = StableQueueScript()

def on_ui_settings():
    """Add StableQueue settings to the Settings tab"""
    section = ("stablequeue", "StableQueue")
    
    shared.opts.add_option(
        "stablequeue_server_url",
        shared.OptionInfo(
            "http://192.168.73.124:8083",
            "StableQueue Server URL",
            section=section
        )
    )
    
    shared.opts.add_option(
        "stablequeue_api_key", 
        shared.OptionInfo(
            "",
            "StableQueue API Key",
            section=section
        )
    )
    
    shared.opts.add_option(
        "stablequeue_api_secret",
        shared.OptionInfo(
            "",
            "StableQueue API Secret", 
            section=section
        )
    )
    
    shared.opts.add_option(
        "stablequeue_auto_queue",
        shared.OptionInfo(
            False,
            "Auto-queue generations to StableQueue (prevents local generation)",
            section=section
        )
    )

# Register settings
script_callbacks.on_ui_settings(on_ui_settings)

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
        
        # Register the endpoints
        @app.post("/stablequeue/trigger_queue")
        async def trigger_queue_api(request: Request):
            try:
                print(f"[StableQueue] /stablequeue/trigger_queue endpoint called")
                
                # Get request data
                data = await request.json()
                tab_id = data.get('tab_id', '')
                job_type = data.get('job_type', 'single')
                server_alias = data.get('server_alias', '')
                
                print(f"[StableQueue] Setting queue flag: tab={tab_id}, type={job_type}, server={server_alias}")
                
                # Set the pending queue request - AlwaysOnScript will intercept next generation
                global pending_queue_request
                pending_queue_request["enabled"] = True
                pending_queue_request["server_alias"] = server_alias
                pending_queue_request["job_type"] = job_type
                
                print(f"[StableQueue] Queue flag set - ready to intercept StableDiffusionProcessing object")
                
                return JSONResponse(content={
                    "success": True,
                    "message": f"Queue flag set for {job_type} job on {server_alias}"
                })
                
            except Exception as e:
                print(f"[StableQueue] Error in trigger_queue_api: {e}")
                return JSONResponse(
                    content={"success": False, "message": f"API Error: {str(e)}"}, 
                    status_code=500
                )

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