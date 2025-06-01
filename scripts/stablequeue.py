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

VERSION = "1.0.0"
EXTENSION_NAME = "StableQueue Extension"
DEFAULT_SERVER_URL = "http://192.168.73.124:8083"

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
            response = requests.get(
                f"{self.stablequeue_url}/api/v1/servers",
                headers={
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret
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
        """Create the UI components for the StableQueue extension"""
        with gr.Group():
            with gr.Accordion("StableQueue", open=True):
                with FormRow():
                    server_alias = gr.Dropdown(
                        label="Target Server", 
                        choices=self.servers_list if self.servers_list else ["Configure API key in settings"],
                        interactive=True
                    )
                    priority = gr.Slider(
                        minimum=1, 
                        maximum=10, 
                        value=5, 
                        step=1, 
                        label="Priority"
                    )
                
                with FormRow():
                    refresh_btn = gr.Button("🔄 Refresh Servers")
                
                status_html = gr.HTML("<div>Not connected to StableQueue</div>")
        
        # Refresh button to update server list
        def refresh_servers():
            if self.fetch_servers():
                return gr.Dropdown.update(choices=self.servers_list), f"<div style='color:green'>Refreshed server list. Found {len(self.servers_list)} server(s).</div>"
            else:
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
        
        return [server_alias, priority, status_html]
    
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
    stablequeue_instance = StableQueue()
    
    with gr.Blocks(analytics_enabled=False) as stablequeue_interface:
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
            if stablequeue_instance.fetch_servers():
                return gr.Dropdown.update(choices=stablequeue_instance.servers_list), f"<div style='color:green'>Refreshed server list. Found {len(stablequeue_instance.servers_list)} server(s).</div>"
            else:
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
    
    return [(stablequeue_interface, "StableQueue", "stablequeue")]

# Register the tab
script_callbacks.on_ui_tabs(create_stablequeue_tab)

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

# Global function that JavaScript can call
def queue_job_from_javascript(generation_params_json, server_alias, job_type="single"):
    """
    Function that can be called from JavaScript to queue jobs
    """
    try:
        import json
        
        # Parse the JSON parameters
        generation_params = json.loads(generation_params_json)
        
        # Create a StableQueue instance to access settings and methods
        stablequeue_instance = StableQueue()
        
        # Create a mock processing object that the existing method expects
        class MockP:
            def __init__(self, params):
                # Basic parameters
                self.prompt = params.get('positive_prompt', '')
                self.negative_prompt = params.get('negative_prompt', '')
                self.width = params.get('width', 512)
                self.height = params.get('height', 512)
                self.steps = params.get('steps', 20)
                self.cfg_scale = params.get('cfg_scale', 7)
                self.sampler_name = params.get('sampler_name', 'Euler')
                self.seed = params.get('seed', -1)
                self.batch_size = params.get('batch_size', 1)
                self.n_iter = params.get('batch_count', 1)
                
                # Mock sd_model for checkpoint
                self.sd_model = type('obj', (object,), {
                    'name': params.get('checkpoint_name', '')
                })()
                
                # Optional parameters
                self.restore_faces = params.get('restore_faces', False)
                self.enable_hr = params.get('enable_hr', False)
                if self.enable_hr:
                    self.hr_scale = params.get('hr_scale', 2.0)
                    self.hr_upscaler = params.get('hr_upscaler', 'Latent')
                    self.hr_second_pass_steps = params.get('hr_second_pass_steps', 0)
                
                self.subseed = params.get('subseed', -1)
                self.subseed_strength = params.get('subseed_strength', 0)
        
        # Create mock processing object
        mock_p = MockP(generation_params)
        
        # Call the existing queue method
        success, message = stablequeue_instance.queue_in_stablequeue(
            mock_p, 
            server_alias, 
            priority=5,  # Default priority
            job_type=job_type
        )
        
        return json.dumps({
            "success": success,
            "message": message
        })
        
    except Exception as e:
        return json.dumps({
            "success": False,
            "message": f"Error: {str(e)}"
        })

# Make the function available globally for JavaScript to call
def setup_javascript_api():
    """Setup API endpoints that JavaScript can call"""
    try:
        from modules import shared
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse
        import json
        
        # Get the FastAPI app instance from shared
        if hasattr(shared, 'demo') and hasattr(shared.demo, 'app'):
            app = shared.demo.app
            
            @app.post("/stablequeue/queue_job")
            async def queue_job_api(request):
                try:
                    # Get request data
                    data = await request.json()
                    generation_params_json = json.dumps(data.get('generation_params', {}))
                    server_alias = data.get('server_alias', '')
                    job_type = data.get('job_type', 'single')
                    
                    # Call our queue function
                    result_json = queue_job_from_javascript(generation_params_json, server_alias, job_type)
                    result = json.loads(result_json)
                    
                    return JSONResponse(content=result)
                    
                except Exception as e:
                    return JSONResponse(
                        content={"success": False, "message": f"API Error: {str(e)}"}, 
                        status_code=500
                    )
                    
    except Exception as e:
        print(f"[StableQueue] Could not setup JavaScript API: {e}")

# Register the setup function
script_callbacks.on_app_started(setup_javascript_api) 