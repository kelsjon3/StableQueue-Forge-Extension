# StableQueue Forge Extension
import gradio as gr
from modules import script_callbacks

print("StableQueue Extension: Initializing...")

# Create a simple tab for testing
def ui_tab():
    with gr.Blocks() as ui_component:
        with gr.Row():
            gr.HTML("<h1>StableQueue</h1>")
        
        with gr.Row():
            gr.HTML("<p>This is the StableQueue tab</p>")
            gr.Button("Test Button")
            
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
script_callbacks.on_ui_tabs(ui_tab)
script_callbacks.on_context_menu_extension(context_menu_entries)

print("StableQueue Extension: All callbacks registered.") 