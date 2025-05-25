# StableQueue Forge Extension
import gradio as gr
from modules import script_callbacks

print("StableQueue Extension: Initializing...")

# Create a simple tab for testing
def on_ui_tabs():
    print("StableQueue Extension: on_ui_tabs callback called")
    with gr.Blocks(analytics_enabled=False) as ui_component:
        with gr.Row():
            with gr.Column():
                gr.HTML("<h1>StableQueue</h1>")
                gr.HTML("<p>Manage and monitor your StableQueue jobs</p>")
                
                with gr.Group():
                    with gr.Row():
                        server_url = gr.Textbox(
                            label="StableQueue Server URL",
                            value="http://192.168.73.124:8083",
                            interactive=True
                        )
                        test_connection_btn = gr.Button("Test Connection", variant="secondary")
                    
                    with gr.Row():
                        api_key = gr.Textbox(
                            label="API Key",
                            value="",
                            interactive=True,
                            type="password"
                        )
                        api_secret = gr.Textbox(
                            label="API Secret",
                            value="",
                            interactive=True,
                            type="password"
                        )
                
                with gr.Group():
                    with gr.Row():
                        queue_current_btn = gr.Button("Queue Current Settings", variant="primary")
                        queue_bulk_btn = gr.Button("Queue Bulk Job", variant="secondary")
                
                status_html = gr.HTML("<div>StableQueue tab is working</div>")
            
    print("StableQueue Extension: Returning tab component")
    return [(ui_component, "StableQueue", "stablequeue_tab")]

# Register context menu entries
def context_menu_entries():
    return [
        {
            "name": "Send to StableQueue",
            "function": "function() { alert('Send to StableQueue clicked'); }"
        },
        {
            "name": "Send bulk job to StableQueue",
            "function": "function() { alert('Send bulk job clicked'); }"
        }
    ]

# Register callbacks
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_context_menu_extension(context_menu_entries)

print("StableQueue Extension: All callbacks registered.") 