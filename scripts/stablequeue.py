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
        self.seed_variation = shared.opts.data.get("stablequeue_seed_variation", "Random")
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
            request_data["seed_variation"] = self.seed_variation.lower()
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
                    queue_btn = gr.Button("Queue in StableQueue", variant="primary")
                    queue_bulk_btn = gr.Button("Queue Bulk Job", variant="secondary")
                    refresh_btn = ToolButton("🔄")
                
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
        
        # We need to create wrapper functions that can access the 'p' parameter
        # which contains all the generation parameters from the Forge UI
        def queue_wrapper(p, server, priority):
            success, message = self.queue_in_stablequeue(p, server, priority)
            if success:
                return f"<div style='color:green'>{message}</div>"
            else:
                return f"<div style='color:red'>{message}</div>"
        
        def queue_bulk_wrapper(p, server, priority):
            success, message = self.queue_in_stablequeue(p, server, priority, job_type="bulk")
            if success:
                return f"<div style='color:green'>{message}</div>"
            else:
                return f"<div style='color:red'>{message}</div>"
        
        # Connect the queue button to the wrapper function
        queue_btn.click(
            fn=queue_wrapper,
            inputs=[
                # This will be filled with the 'p' object by Forge
                gr.State(None),
                server_alias,
                priority
            ],
            outputs=[status_html]
        )
        
        # Connect the bulk queue button
        queue_bulk_btn.click(
            fn=queue_bulk_wrapper,
            inputs=[
                # This will be filled with the 'p' object by Forge
                gr.State(None),
                server_alias,
                priority
            ],
            outputs=[status_html]
        )
        
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
                    interactive=True
                )
                priority = gr.Slider(
                    minimum=1, 
                    maximum=10, 
                    value=5, 
                    step=1, 
                    label="Priority"
                )
        
        with gr.Row():
            queue_btn = gr.Button("Queue in StableQueue", variant="primary")
            queue_bulk_btn = gr.Button("Queue Bulk Job", variant="secondary")
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
        
        # Note: The queue buttons won't work in this tab format because we don't have access to the 'p' parameter
        # The main functionality will come from the JavaScript buttons and context menu
        
        def show_info():
            return "<div style='color:blue'>Use the 'Queue in StableQueue' buttons next to the Generate buttons in txt2img/img2img tabs, or use the context menu options.</div>"
        
        queue_btn.click(fn=show_info, outputs=[status_html])
        queue_bulk_btn.click(fn=show_info, outputs=[status_html])
    
    return [(stablequeue_interface, "StableQueue", "stablequeue")]

# Register the tab
script_callbacks.on_ui_tabs(create_stablequeue_tab) 