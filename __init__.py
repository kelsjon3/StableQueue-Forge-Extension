# StableQueue Forge Extension
print("\n\n==================================================")
print("STABLEQUEUE EXTENSION: LOADING")
print("==================================================\n\n")

import gradio as gr
from modules import script_callbacks

# Create a simple tab function - this is the most basic possible implementation
def on_ui_tabs():
    print("\n\n==================================================")
    print("STABLEQUEUE EXTENSION: UI_TABS CALLBACK CALLED")
    print("==================================================\n\n")
    
    with gr.Blocks() as ui_component:
        gr.HTML("<h1>StableQueue Test Tab</h1>")
    
    return [(ui_component, "StableQueue", "stablequeue_tab")]

# Register the tab
print("STABLEQUEUE: Registering on_ui_tabs callback")
script_callbacks.on_ui_tabs(on_ui_tabs)

print("\n\n==================================================")
print("STABLEQUEUE EXTENSION: LOADING COMPLETE")
print("==================================================\n\n")

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

script_callbacks.on_context_menu_extension(context_menu_entries)

print("StableQueue Extension: All callbacks registered.") 