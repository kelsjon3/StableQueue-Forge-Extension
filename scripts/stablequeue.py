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

print("[StableQueue] All imports successful")

VERSION = "1.0.0"
EXTENSION_NAME = "StableQueue Extension"
DEFAULT_SERVER_URL = "http://192.168.73.124:8083"

print(f"[StableQueue] Extension initialized - Version {VERSION}")

# Global flag to track if API is set up
api_setup_completed = False

class StableQueue(scripts.Script):
    def __init__(self):
        super().__init__()
        # Load configuration from shared options
        self.stablequeue_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
        self.api_key = shared.opts.data.get("stablequeue_api_key", "")
        self.api_secret = shared.opts.data.get("stablequeue_api_secret", "")
        self.connection_verified = False
        self.servers_list = []
        self.bulk_job_quantity = shared.opts.data.get("stablequeue_bulk_quantity", 10)
        self.job_delay = shared.opts.data.get("stablequeue_job_delay", 5)
        
        # Initialize servers list if API key is available
        if self.api_key and self.api_secret:
            self.fetch_servers()
    
    def title(self):
        return "StableQueue"
    
    def show(self, is_img2img):
        return scripts.AlwaysVisible
    
    def fetch_servers(self):
        """Fetch available server aliases from StableQueue"""
        try:
            print(f"[StableQueue] DEBUG: Fetching servers from {self.stablequeue_url}/api/v1/servers")
            print(f"[StableQueue] DEBUG: Using API Key: {self.api_key[:8] if self.api_key else 'EMPTY'}...")
            print(f"[StableQueue] DEBUG: Using API Secret: {self.api_secret[:8] if self.api_secret else 'EMPTY'}...")
            
            response = requests.get(
                f"{self.stablequeue_url}/api/v1/servers",
                headers={
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret
                },
                timeout=5
            )
            
            print(f"[StableQueue] DEBUG: Server fetch response: {response.status_code}")
            
            if response.status_code == 200:
                self.servers_list = [server["alias"] for server in response.json()]
                return True
            else:
                print(f"[StableQueue] Failed to fetch servers: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"[StableQueue] Error fetching servers: {str(e)}")
            return False
    
    def test_connection(self, url, key, secret):
        """Test connection to StableQueue server"""
        try:
            # First test basic server connectivity
            response = requests.get(
                f"{url}/status",
                timeout=5
            )
            
            if response.status_code == 200:
                # If status is ok, test API authentication if credentials provided
                if key and secret:
                    servers_response = requests.get(
                        f"{url}/api/v1/servers",
                        headers={
                            "X-API-Key": key,
                            "X-API-Secret": secret
                        },
                        timeout=5
                    )
                    
                    if servers_response.status_code == 200:
                        self.servers_list = [server["alias"] for server in servers_response.json()]
                        self.connection_verified = True
                        return True, f"Connected to StableQueue server. Found {len(self.servers_list)} server(s)."
                    elif servers_response.status_code == 401:
                        return False, "Server is reachable, but API authentication failed. Please check your API key and secret."
                    else:
                        return False, f"Server is reachable, but API request failed: {servers_response.status_code}"
                else:
                    # No credentials provided, but server is reachable
                    return True, "Server is reachable. Please configure API credentials to access server list."
            else:
                return False, f"Failed to connect to StableQueue: {response.status_code} - {response.text}"
        except requests.exceptions.ConnectionError:
            return False, f"Cannot connect to StableQueue server at {url}. Please check the URL and ensure the server is running."
        except requests.exceptions.Timeout:
            return False, f"Connection to StableQueue server timed out. Please check the server status."
        except Exception as e:
            return False, f"Error connecting to StableQueue: {str(e)}"
    
    def create_api_key(self, url, name):
        """Create a new API key on the StableQueue server"""
        if not name:
            return False, "API key name cannot be empty"
        
        try:
            response = requests.post(
                f"{url}/api/v1/api-keys",
                json={"name": name},
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                return True, {
                    "key": data["key"],
                    "secret": data["secret"],
                    "message": f"API key '{name}' created successfully"
                }
            else:
                return False, f"Failed to create API key: {response.status_code} - {response.text}"
        except Exception as e:
            return False, f"Error creating API key: {str(e)}"
    
    def extract_parameters(self, p):
        """Extract generation parameters from the Forge UI"""
        # Basic parameters
        params = {
            "positive_prompt": p.prompt,
            "negative_prompt": p.negative_prompt,
            "width": p.width,
            "height": p.height,
            "steps": p.steps,
            "cfg_scale": p.cfg_scale,
            "sampler_name": p.sampler_name,
            "restore_faces": getattr(p, "restore_faces", False),
            "seed": p.seed,
            "batch_size": p.batch_size,
            "batch_count": p.n_iter
        }
        
        # Add checkpoint model info
        if hasattr(p, "sd_model") and p.sd_model:
            params["checkpoint_name"] = p.sd_model.name
        
        # Add additional parameters if available
        if hasattr(p, "enable_hr"):
            params["enable_hr"] = p.enable_hr
            if p.enable_hr:
                params["hr_scale"] = p.hr_scale
                params["hr_upscaler"] = p.hr_upscaler
                params["hr_second_pass_steps"] = p.hr_second_pass_steps
        
        # Add subseed if available
        if hasattr(p, "subseed") and p.subseed > -1:
            params["subseed"] = p.subseed
            params["subseed_strength"] = p.subseed_strength
        
        # Return the collected parameters
        return params
    
    def queue_in_stablequeue(self, p, server_alias, priority, job_type="single"):
        """Send job to StableQueue"""
        # Extract generation parameters
        generation_params = self.extract_parameters(p)
        
        # Prepare request body
        request_data = {
            "app_type": "forge",
            "target_server_alias": server_alias,
            "generation_params": generation_params,
            "source_info": f"stablequeue_forge_extension_v{VERSION}"
        }
        
        # Add priority if specified
        if priority and priority > 0:
            request_data["priority"] = int(priority)
        
        # Check if it's a bulk job
        if job_type == "bulk":
            # Add bulk job specific parameters
            request_data["bulk_quantity"] = self.bulk_job_quantity
            request_data["job_delay"] = self.job_delay
            request_data["source_info"] = f"stablequeue_forge_extension_bulk_v{VERSION}"
            
            endpoint = f"{self.stablequeue_url}/api/v2/generate/bulk"
        else:
            endpoint = f"{self.stablequeue_url}/api/v2/generate"
        
        # Send to StableQueue API
        try:
            print(f"[StableQueue] DEBUG: Sending request to {endpoint}")
            print(f"[StableQueue] DEBUG: API Key: {self.api_key[:8]}...")
            print(f"[StableQueue] DEBUG: API Secret: {self.api_secret[:8]}...")
            print(f"[StableQueue] DEBUG: Request data: {request_data}")
            
            response = requests.post(
                endpoint,
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret
                },
                timeout=30
            )
            
            print(f"[StableQueue] DEBUG: Response status: {response.status_code}")
            print(f"[StableQueue] DEBUG: Response headers: {response.headers}")
            print(f"[StableQueue] DEBUG: Response text: {response.text}")
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                if job_type == "bulk":
                    return True, f"Bulk job submitted successfully. {data.get('total_jobs', 0)} jobs queued."
                else:
                    job_id = data.get("stablequeue_job_id")
                    return True, f"Job queued successfully. ID: {job_id}"
            else:
                return False, f"Error: {response.status_code} - {response.json().get('error', 'Unknown error')}"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def ui(self, is_img2img):
        """This UI method is disabled - we use create_stablequeue_tab() instead"""
        # Return empty components to avoid conflicts with the standalone tab
        return []
    
    def after_component(self, component, **kwargs):
        """Add a 'Queue in StableQueue' button after the Generate button"""
        # This will be used to add buttons directly to the UI outside our tab
        pass


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
        
        stablequeue_instance = StableQueue()
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

# Global function that JavaScript can call to capture the complete API payload
def queue_job_from_javascript(api_payload_json, server_alias, job_type="single"):
    """
    Function that receives the complete API payload that would go to /sdapi/v1/txt2img
    This ensures we capture ALL parameters including extension parameters
    """
    try:
        import json
        
        # Parse the complete API payload
        api_payload = json.loads(api_payload_json)
        
        # Log received parameters for debugging
        print(f"[StableQueue] Complete API payload received: {api_payload}")
        
        # Get current settings directly (more reliable than creating new instance)
        current_url = shared.opts.data.get("stablequeue_url", DEFAULT_SERVER_URL)
        current_api_key = shared.opts.data.get("stablequeue_api_key", "")
        current_api_secret = shared.opts.data.get("stablequeue_api_secret", "")
        current_bulk_quantity = shared.opts.data.get("stablequeue_bulk_quantity", 10)
        current_job_delay = shared.opts.data.get("stablequeue_job_delay", 5)
        
        print(f"[StableQueue] Using credentials - URL: {current_url}, API Key: {'***' if current_api_key else '(empty)'}, API Secret: {'***' if current_api_secret else '(empty)'}")
        
        if not current_api_key or not current_api_secret:
            return json.dumps({
                "success": False,
                "message": "API credentials not configured. Please set API key and secret in Settings → StableQueue Integration."
            })
        
        # Prepare request body for StableQueue using the complete API payload
        request_data = {
            "app_type": "forge",
            "target_server_alias": server_alias,
            "generation_params": api_payload,  # Use the complete payload directly
            "source_info": f"stablequeue_forge_extension_v{VERSION}"
        }
        
        # Add priority
        request_data["priority"] = 5  # Default priority
        
        # Check if it's a bulk job
        if job_type == "bulk":
            # Add bulk job specific parameters
            request_data["bulk_quantity"] = current_bulk_quantity
            request_data["job_delay"] = current_job_delay
            request_data["source_info"] = f"stablequeue_forge_extension_bulk_v{VERSION}"
            
            endpoint = f"{current_url}/api/v2/generate/bulk"
        else:
            endpoint = f"{current_url}/api/v2/generate"
        
        # Send to StableQueue API directly
        try:
            print(f"[StableQueue] DEBUG: JS API sending request to {endpoint}")
            print(f"[StableQueue] DEBUG: JS API Key: {current_api_key[:8]}...")
            print(f"[StableQueue] DEBUG: JS API Secret: {current_api_secret[:8]}...")
            print(f"[StableQueue] DEBUG: JS Request data: {request_data}")
            
            response = requests.post(
                endpoint,
                json=request_data,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": current_api_key,
                    "X-API-Secret": current_api_secret
                },
                timeout=30
            )
            
            print(f"[StableQueue] DEBUG: JS Response status: {response.status_code}")
            print(f"[StableQueue] DEBUG: JS Response headers: {response.headers}")
            print(f"[StableQueue] DEBUG: JS Response text: {response.text}")
            
            if response.status_code in [200, 201, 202]:
                data = response.json()
                if job_type == "bulk":
                    message = f"Bulk job submitted successfully. {data.get('total_jobs', 0)} jobs queued."
                else:
                    job_id = data.get("mobilesd_job_id")
                    message = f"Job queued successfully. ID: {job_id}"
                
                return json.dumps({
                    "success": True,
                    "message": message
                })
            else:
                try:
                    error_msg = f"Error: {response.status_code} - {response.json().get('error', 'Unknown error')}"
                except ValueError:
                    error_msg = f"Error: {response.status_code} - response not JSON"
                return json.dumps({
                    "success": False,
                    "message": error_msg
                })
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"Connection error: {str(e)}"
            })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error: {str(e)}"
        })

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
                    
                    result_json = queue_job_from_javascript(api_payload_json, server_alias, job_type)
                    result = json.loads(result_json)
                    
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
        
        # Register the endpoint
        @app.post("/stablequeue/queue_job")
        async def queue_job_api(request: Request):
            try:
                print(f"[StableQueue] /stablequeue/queue_job endpoint called")
                
                # Get request data
                data = await request.json()
                api_payload_json = json.dumps(data.get('api_payload', {}))
                server_alias = data.get('server_alias', '')
                job_type = data.get('job_type', 'single')
                
                print(f"[StableQueue] Processing job: server={server_alias}, type={job_type}")
                
                # Call our queue function with the complete API payload
                result_json = queue_job_from_javascript(api_payload_json, server_alias, job_type)
                result = json.loads(result_json)
                
                print(f"[StableQueue] Job result: {result}")
                
                return JSONResponse(content=result)
                
            except Exception as e:
                print(f"[StableQueue] Error in queue_job_api: {e}")
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