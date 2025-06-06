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
        # Removed queue_intent - we now use direct parameter capture
        
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
                # TEST BUTTON - This will show us what parameters we can capture
                test_capture_btn = gr.Button("🔍 Test Parameter Capture", variant="secondary")
            
            # Status display
            status_display = gr.HTML("")
            
            # Parameter display for testing
            with gr.Accordion("Parameter Capture Test Results", open=False):
                captured_params_display = gr.Code(
                    language="json",
                    label="Captured Parameters",
                    lines=20
                )

            # Event handlers
            def refresh_servers():
                if self.fetch_servers():
                    choices = self.servers_list if self.servers_list else ["Configure API key in settings"]
                    value = self.servers_list[0] if self.servers_list else "Configure API key in settings"
                    return gr.Dropdown.update(choices=choices, value=value), f"<span style='color:green'>✓ Found {len(self.servers_list)} server(s)</span>"
                else:
                    return gr.Dropdown.update(choices=["Configure API key in settings"], value="Configure API key in settings"), "<span style='color:red'>✗ Failed to refresh servers</span>"

            def test_parameter_capture():
                """Test parameter capture using research document approach"""
                try:
                    print(f"[StableQueue] === TESTING PARAMETER CAPTURE ===")
                    
                    # Use the research document's approach: runtime UI traversal
                    params = self.capture_ui_parameters_direct(is_img2img)
                    
                    # Format for display
                    import json
                    params_json = json.dumps(params, indent=2, default=str)
                    
                    print(f"[StableQueue] Parameter capture test completed successfully")
                    print(f"[StableQueue] Captured {len(params)} parameters")
                    
                    status_msg = f"<span style='color:green'>✓ Successfully captured {len(params)} parameters!</span>"
                    return status_msg, params_json
                    
                except Exception as e:
                    print(f"[StableQueue] ✗ Parameter capture test failed: {e}")
                    import traceback
                    print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
                    
                    error_msg = f"<span style='color:red'>✗ Parameter capture failed: {str(e)}</span>"
                    return error_msg, f"ERROR: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"

            def queue_single_job(server_alias):
                """Queue a single job using direct parameter capture"""
                if not server_alias or server_alias == "Configure API key in settings":
                    return f"<span style='color:red'>✗ Please select a valid server</span>"
                
                try:
                    print(f"[StableQueue] === SINGLE JOB QUEUE ===")
                    
                    # Capture parameters directly using research approach
                    params = self.capture_ui_parameters_direct(is_img2img)
                    params["target_server_alias"] = server_alias
                    
                    # Submit to StableQueue
                    success = self.submit_job_to_stablequeue(params)
                    
                    if success:
                        return f"<span style='color:green'>✓ Single job queued successfully to {server_alias}</span>"
                    else:
                        return f"<span style='color:red'>✗ Failed to queue job to {server_alias}</span>"
                        
                except Exception as e:
                    print(f"[StableQueue] Error in single job queue: {e}")
                    return f"<span style='color:red'>✗ Error: {str(e)}</span>"

            def queue_bulk_jobs(server_alias):
                """Queue multiple jobs using direct parameter capture"""
                if not server_alias or server_alias == "Configure API key in settings":
                    return f"<span style='color:red'>✗ Please select a valid server</span>"
                
                try:
                    print(f"[StableQueue] === BULK JOB QUEUE ===")
                    
                    # Capture base parameters
                    params = self.capture_ui_parameters_direct(is_img2img)
                    params["target_server_alias"] = server_alias
                    
                    # Submit multiple jobs with seed variation
                    bulk_quantity = shared.opts.data.get("stablequeue_bulk_quantity", 10)
                    success_count = 0
                    
                    for i in range(bulk_quantity):
                        bulk_params = params.copy()
                        if bulk_params.get('seed', -1) != -1:
                            bulk_params['seed'] = bulk_params['seed'] + i
                        
                        if self.submit_job_to_stablequeue(bulk_params):
                            success_count += 1
                    
                    return f"<span style='color:green'>✓ {success_count}/{bulk_quantity} bulk jobs queued successfully to {server_alias}</span>"
                        
                except Exception as e:
                    print(f"[StableQueue] Error in bulk job queue: {e}")
                    return f"<span style='color:red'>✗ Error: {str(e)}</span>"

            # Wire up the event handlers
            refresh_btn.click(
                fn=refresh_servers,
                outputs=[server_dropdown, status_display]
            )
            
            test_capture_btn.click(
                fn=test_parameter_capture,
                outputs=[status_display, captured_params_display]
            )
            
            queue_btn.click(
                fn=queue_single_job,
                inputs=[server_dropdown],
                outputs=[status_display]
            )
            
            bulk_queue_btn.click(
                fn=queue_bulk_jobs,
                inputs=[server_dropdown],
                outputs=[status_display]
            )
        
        return []

    def capture_ui_parameters_direct(self, is_img2img):
        """Capture UI parameters directly using research document approach"""
        try:
            print(f"[StableQueue] === DIRECT UI PARAMETER CAPTURE ===")
            print(f"[StableQueue] Target: {'img2img' if is_img2img else 'txt2img'}")
            
            # Get access to the main Gradio demo (as per research document)
            if not hasattr(shared, 'demo') or not shared.demo:
                raise Exception("shared.demo not available - cannot access Gradio UI tree")
            
            root_blocks = shared.demo
            print(f"[StableQueue] Root Gradio blocks: {type(root_blocks)}")
            
            # Find components using runtime traversal (research document Method 1)
            components = self.find_ui_components(root_blocks, is_img2img)
            
            # Extract current values from found components
            params = {}
            
            # Core generation parameters
            for param_name, component in components.items():
                try:
                    if component and hasattr(component, 'value'):
                        params[param_name] = component.value
                        print(f"[StableQueue] Captured {param_name}: {component.value}")
                    else:
                        print(f"[StableQueue] ⚠ Component {param_name} has no value attribute")
                        params[param_name] = None
                except Exception as e:
                    print(f"[StableQueue] ⚠ Error getting value for {param_name}: {e}")
                    params[param_name] = None
            
            # Add metadata
            from datetime import datetime
            params["_capture_method"] = "direct_ui_traversal"
            params["_capture_timestamp"] = str(datetime.now())
            params["_is_img2img"] = is_img2img
            
            # Add model information from shared state
            if hasattr(shared, 'sd_model') and shared.sd_model:
                checkpoint_info = getattr(shared.sd_model, 'sd_checkpoint_info', None)
                if checkpoint_info:
                    params["checkpoint_name"] = getattr(checkpoint_info, 'name', str(checkpoint_info))
                else:
                    params["checkpoint_name"] = ''
                params["model_hash"] = getattr(shared.sd_model, 'sd_model_hash', '')
            
            print(f"[StableQueue] Direct capture completed: {len(params)} parameters")
            return params
            
        except Exception as e:
            print(f"[StableQueue] Error in direct parameter capture: {e}")
            import traceback
            print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
            raise

    def find_ui_components(self, root_blocks, is_img2img):
        """Find UI components using runtime traversal (research document approach)"""
        try:
            print(f"[StableQueue] === UI COMPONENT DISCOVERY ===")
            
            # Define target elem_ids based on common A1111/Forge patterns
            if is_img2img:
                target_elem_ids = {
                    "prompt": "img2img_prompt",
                    "negative_prompt": "img2img_neg_prompt", 
                    "steps": "img2img_steps",
                    "cfg_scale": "img2img_cfg_scale",
                    "width": "img2img_width",
                    "height": "img2img_height",
                    "sampler": "img2img_sampling",
                    "seed": "img2img_seed",
                    "denoising_strength": "img2img_denoising_strength"
                }
            else:
                target_elem_ids = {
                    "prompt": "txt2img_prompt",
                    "negative_prompt": "txt2img_neg_prompt",
                    "steps": "txt2img_steps", 
                    "cfg_scale": "txt2img_cfg_scale",
                    "width": "txt2img_width",
                    "height": "txt2img_height",
                    "sampler": "txt2img_sampling",
                    "seed": "txt2img_seed"
                }
            
            # Use recursive traversal to find components
            found_components = {}
            
            for param_name, elem_id in target_elem_ids.items():
                component = self.find_component_recursive(root_blocks, elem_id=elem_id)
                found_components[param_name] = component
                
                if component:
                    print(f"[StableQueue] ✓ Found {param_name} (elem_id: {elem_id})")
                else:
                    print(f"[StableQueue] ✗ Missing {param_name} (elem_id: {elem_id})")
            
            # Count successful discoveries
            found_count = sum(1 for comp in found_components.values() if comp is not None)
            missing_count = len(target_elem_ids) - found_count
            
            print(f"[StableQueue] Discovery result: {found_count} found, {missing_count} missing")
            
            if found_count == 0:
                raise Exception("Failed to find any UI components - all target elem_ids missing")
            
            if missing_count > 0:
                missing_list = [name for name, comp in found_components.items() if comp is None]
                print(f"[StableQueue] ⚠ Missing components: {missing_list}")
                
                # FAIL FAST if critical components are missing (as user requested)
                critical_components = ["prompt", "steps", "cfg_scale", "width", "height"]
                missing_critical = [name for name in missing_list if name in critical_components]
                
                if missing_critical:
                    raise Exception(f"Critical components missing: {missing_critical}. Cannot capture parameters reliably.")
            
            return found_components
            
        except Exception as e:
            print(f"[StableQueue] Error in component discovery: {e}")
            raise

    def find_component_recursive(self, element, elem_id=None, label=None, component_type=None):
        """Recursively search for a Gradio component (research document implementation)"""
        try:
            # Check if this element matches our criteria
            if elem_id and hasattr(element, 'elem_id') and element.elem_id == elem_id:
                return element
            
            if label and hasattr(element, 'label') and element.label == label:
                if component_type is None or isinstance(element, component_type):
                    return element
            
            # Traverse children of layout blocks
            if hasattr(element, 'children'):
                for child in element.children:
                    found = self.find_component_recursive(child, elem_id, label, component_type)
                    if found:
                        return found
            
            # Handle Gradio Tabs structure
            if hasattr(element, '__class__') and 'Tab' in str(element.__class__):
                if hasattr(element, 'children'):
                    for child in element.children:
                        found = self.find_component_recursive(child, elem_id, label, component_type)
                        if found:
                            return found
            
            return None
            
        except Exception as e:
            # Don't log individual traversal errors - too noisy
            return None

    def submit_job_to_stablequeue(self, params):
        """Submit a job to StableQueue (simplified for testing)"""
        try:
            # Get StableQueue settings
            server_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
            api_key = shared.opts.data.get("stablequeue_api_key", "")
            api_secret = shared.opts.data.get("stablequeue_api_secret", "")
            
            if not all([server_url, api_key, api_secret]):
                print(f"[StableQueue] ✗ StableQueue credentials not configured in settings")
                return False
            
            return self.submit_to_stablequeue(params, server_url, api_key, api_secret)
            
        except Exception as e:
            print(f"[StableQueue] Error submitting job: {e}")
            return False

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

    def process(self, p, queue_intent_state=None):
        """Hook into the processing - simplified since we now use direct parameter capture"""
        # We no longer use the process() hook for queue operations
        # All queuing is now handled directly in the button click handlers
        # This method is kept for compatibility but does nothing special
        return None
    
    def extract_complete_parameters(self, p):
        """Extract complete parameters from StableDiffusionProcessing object (research-backed approach)"""
        try:
            print(f"[StableQueue] === PARAMETER EXTRACTION DEBUG ===")
            print(f"[StableQueue] StableDiffusionProcessing object type: {type(p)}")
            print(f"[StableQueue] Available attributes: {dir(p)}")
            
            # Debug the core parameters
            prompt = getattr(p, 'prompt', '')
            negative_prompt = getattr(p, 'negative_prompt', '')
            steps = getattr(p, 'steps', 20)
            width = getattr(p, 'width', 512)
            height = getattr(p, 'height', 512)
            
            print(f"[StableQueue] Raw parameter extraction:")
            print(f"[StableQueue] - prompt: '{prompt}' (type: {type(prompt)})")
            print(f"[StableQueue] - negative_prompt: '{negative_prompt}' (type: {type(negative_prompt)})")
            print(f"[StableQueue] - steps: {steps} (type: {type(steps)})")
            print(f"[StableQueue] - width: {width} (type: {type(width)})")
            print(f"[StableQueue] - height: {height} (type: {type(height)})")
            
            print(f"[StableQueue] Extracting parameters from StableDiffusionProcessing object")
            
            # Extract core parameters from p object (as per research document)
            params = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "steps": steps,
                "sampler_name": getattr(p, 'sampler_name', 'Euler'),
                "cfg_scale": getattr(p, 'cfg_scale', 7.0),
                "width": width,
                "height": height,
                "seed": getattr(p, 'seed', -1),
                "subseed": getattr(p, 'subseed', -1),
                "subseed_strength": getattr(p, 'subseed_strength', 0),
                "batch_size": getattr(p, 'batch_size', 1),
                "n_iter": getattr(p, 'n_iter', 1),
                "restore_faces": getattr(p, 'restore_faces', False),
                "tiling": getattr(p, 'tiling', False),
                "enable_hr": getattr(p, 'enable_hr', False),
                "hr_scale": getattr(p, 'hr_scale', 2.0),
                "hr_upscaler": getattr(p, 'hr_upscaler', 'Latent'),
                "denoising_strength": getattr(p, 'denoising_strength', 0.7),
                "override_settings": getattr(p, 'override_settings', {}),
            }
            
            # Handle img2img specific parameters
            if hasattr(p, 'init_images') and p.init_images:
                params.update({
                    "resize_mode": getattr(p, 'resize_mode', 0),
                    "mask_blur": getattr(p, 'mask_blur', 4),
                    "inpainting_fill": getattr(p, 'inpainting_fill', 1),
                    "inpaint_full_res": getattr(p, 'inpaint_full_res', True),
                    "inpaint_full_res_padding": getattr(p, 'inpaint_full_res_padding', 0),
                    "inpainting_mask_invert": getattr(p, 'inpainting_mask_invert', 0),
                })
            
            # Add model information
            if hasattr(shared, 'sd_model') and shared.sd_model:
                checkpoint_info = getattr(shared.sd_model, 'sd_checkpoint_info', None)
                if checkpoint_info:
                    if hasattr(checkpoint_info, 'name'):
                        params["checkpoint_name"] = checkpoint_info.name
                    elif hasattr(checkpoint_info, 'model_name'):
                        params["checkpoint_name"] = checkpoint_info.model_name
                    elif hasattr(checkpoint_info, 'title'):
                        params["checkpoint_name"] = checkpoint_info.title
                    else:
                        params["checkpoint_name"] = str(checkpoint_info)
                else:
                    params["checkpoint_name"] = ''
                
                params["model_hash"] = getattr(shared.sd_model, 'sd_model_hash', '')
            
            # Extract alwayson_scripts data if available (as per research document)
            alwayson_scripts = {}
            if hasattr(p, 'script_args') and p.script_args and hasattr(p, 'scripts'):
                # Process script arguments for extensions like ControlNet
                alwayson_scripts = self.extract_alwayson_scripts(p)
            
            params["alwayson_scripts"] = alwayson_scripts
            
            print(f"[StableQueue] === FINAL EXTRACTED PARAMETERS ===")
            print(f"[StableQueue] Extracted {len(params)} parameters from StableDiffusionProcessing object")
            print(f"[StableQueue] Final prompt: '{params['prompt']}'")
            print(f"[StableQueue] Final negative: '{params['negative_prompt']}'")
            print(f"[StableQueue] Final model: '{params.get('checkpoint_name', 'unknown')}'")
            print(f"[StableQueue] Final dimensions: {params['width']}x{params['height']}")
            print(f"[StableQueue] Final steps: {params['steps']}")
            print(f"[StableQueue] === END PARAMETER EXTRACTION ===")
            
            return params
            
        except Exception as e:
            print(f"[StableQueue] Error in extract_complete_parameters: {e}")
            import traceback
            print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
            raise
    
    def extract_alwayson_scripts(self, p):
        """Extract parameters from alwayson scripts like ControlNet (research-backed approach)"""
        try:
            alwayson_scripts = {}
            
            if hasattr(p, 'scripts') and hasattr(p.scripts, 'alwayson_scripts'):
                for script in p.scripts.alwayson_scripts:
                    if hasattr(script, 'args_from') and hasattr(script, 'args_to'):
                        script_args = p.script_args[script.args_from:script.args_to]
                        script_name = script.title().lower().replace(' ', '_')
                        
                        # For known extensions, parse the arguments properly
                        if 'controlnet' in script_name.lower():
                            alwayson_scripts[script_name] = self.parse_controlnet_args(script_args)
                        else:
                            # For unknown extensions, store raw args
                            alwayson_scripts[script_name] = script_args
                        
                        print(f"[StableQueue] Extracted {len(script_args)} args for {script_name}")
            
            return alwayson_scripts
            
        except Exception as e:
            print(f"[StableQueue] Error extracting alwayson scripts: {e}")
            return {}
    
    def parse_controlnet_args(self, cn_args):
        """Parse ControlNet arguments into structured data (as per research document)"""
        try:
            controlnet_units = []
            num_args_per_unit = 15  # As documented in research
            
            for i in range(0, len(cn_args), num_args_per_unit):
                unit_args = cn_args[i:i + num_args_per_unit]
                if len(unit_args) >= num_args_per_unit and unit_args[0]:  # enabled check
                    unit_data = {
                        "enabled": unit_args[0],
                        "module": unit_args[1],
                        "model": unit_args[2],
                        "weight": unit_args[3],
                        "image": unit_args[4],
                        "resize_mode": unit_args[5],
                        "low_vram": unit_args[6],
                        "processor_res": unit_args[7],
                        "threshold_a": unit_args[8],
                        "threshold_b": unit_args[9],
                        "guidance_start": unit_args[10],
                        "guidance_end": unit_args[11],
                        "control_mode": unit_args[12],
                        "pixel_perfect": unit_args[13],
                    }
                    controlnet_units.append(unit_data)
            
            return controlnet_units
            
        except Exception as e:
            print(f"[StableQueue] Error parsing ControlNet args: {e}")
            return cn_args  # Return raw args on error

    def submit_to_stablequeue(self, params, server_url, api_key, api_secret):
        """Submit job to StableQueue server using v2 API"""
        try:
            print(f"[StableQueue] Preparing to submit job with parameters:")
            print(f"[StableQueue] - Prompt: '{params.get('prompt', 'N/A')}'")
            print(f"[StableQueue] - Negative: '{params.get('negative_prompt', 'N/A')}'")
            print(f"[StableQueue] - Steps: {params.get('steps', 'N/A')}")
            print(f"[StableQueue] - CFG: {params.get('cfg_scale', 'N/A')}")
            print(f"[StableQueue] - Size: {params.get('width', 'N/A')}x{params.get('height', 'N/A')}")
            print(f"[StableQueue] - Checkpoint: '{params.get('checkpoint_name', 'N/A')}'")
            
            # Format payload according to StableQueue v2 API specification
            payload = {
                "app_type": "forge",
                "target_server_alias": params.get("target_server_alias", "default"),
                "generation_params": {
                    "positive_prompt": str(params.get("prompt", "")),
                    "negative_prompt": str(params.get("negative_prompt", "")),
                    "width": int(params.get("width", 512)),
                    "height": int(params.get("height", 512)),
                    "steps": int(params.get("steps", 20)),
                    "cfg_scale": float(params.get("cfg_scale", 7.0)),
                    "sampler_name": str(params.get("sampler_name", "Euler")),
                    "seed": int(params.get("seed", -1)),
                    "batch_size": int(params.get("batch_size", 1)),
                    "n_iter": int(params.get("n_iter", 1)),
                    "restore_faces": bool(params.get("restore_faces", False)),
                    "enable_hr": bool(params.get("enable_hr", False)),
                    "hr_scale": float(params.get("hr_scale", 2.0)),
                    "hr_upscaler": str(params.get("hr_upscaler", "Latent")),
                    "denoising_strength": float(params.get("denoising_strength", 0.7)),
                },
                "source_info": "forge_extension_v1.0.0_research_based"
            }
            
            # Add checkpoint name if available
            if params.get("checkpoint_name"):
                payload["generation_params"]["checkpoint_name"] = str(params["checkpoint_name"])
            
            # Add alwayson_scripts if available
            if params.get("alwayson_scripts"):
                payload["alwayson_scripts"] = params["alwayson_scripts"]
            
            headers = {
                "Content-Type": "application/json",
                "X-API-Key": api_key,
                "X-API-Secret": api_secret
            }
            
            url = f"{server_url.rstrip('/')}/api/v2/generate"
            
            print(f"[StableQueue] Submitting to {url}")
            print(f"[StableQueue] Target server: {payload['target_server_alias']}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            print(f"[StableQueue] Response status: {response.status_code}")
            
            if response.status_code == 202:  # StableQueue v2 returns 202 Accepted
                result = response.json()
                job_id = result.get('mobilesd_job_id', 'unknown')
                print(f"[StableQueue] ✓ Job queued with ID: {job_id}")
                return True
            else:
                print(f"[StableQueue] ✗ Failed to queue: {response.status_code}")
                print(f"[StableQueue] Response text: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"[StableQueue] ✗ Timeout connecting to StableQueue server")
            return False
        except Exception as e:
            print(f"[StableQueue] ✗ Error submitting job: {e}")
            import traceback
            print(f"[StableQueue] Full traceback: {traceback.format_exc()}")
            return False

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