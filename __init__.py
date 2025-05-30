# StableQueue Forge Extension
print("\n\n==================================================")
print("STABLEQUEUE EXTENSION: LOADING")
print("==================================================\n\n")

import gradio as gr
from modules import script_callbacks, shared

# Settings registration function
def register_stablequeue_settings():
    """Register StableQueue settings with Forge"""
    section = ('stablequeue', "StableQueue Integration")
    
    # Add settings
    shared.opts.add_option("stablequeue_url", shared.OptionInfo(
        "http://192.168.73.124:8083", "StableQueue Server URL", section=section
    ))
    
    shared.opts.add_option("stablequeue_api_key", shared.OptionInfo(
        "", "API Key", section=section
    ))
    
    shared.opts.add_option("stablequeue_api_secret", shared.OptionInfo(
        "", "API Secret", section=section
    ))
    
    shared.opts.add_option("stablequeue_bulk_quantity", shared.OptionInfo(
        10, "Bulk Job Quantity", section=section, gr_component=gr.Slider, minimum=1, maximum=100, step=1
    ))
    
    shared.opts.add_option("stablequeue_seed_variation", shared.OptionInfo(
        "Random", "Seed Variation Method", section=section, gr_component=gr.Radio, choices=["Random", "Incremental"]
    ))
    
    shared.opts.add_option("stablequeue_job_delay", shared.OptionInfo(
        5, "Delay Between Jobs (seconds)", section=section, gr_component=gr.Slider, minimum=0, maximum=30, step=1
    ))
    
    shared.opts.add_option("enable_stablequeue_context_menu", shared.OptionInfo(
        True, "Add StableQueue options to generation context menu", section=section
    ))

# Create a simple tab function - this is the most basic possible implementation
def on_ui_tabs():
    print("\n\n==================================================")
    print("STABLEQUEUE EXTENSION: UI_TABS CALLBACK CALLED")
    print("==================================================\n\n")
    
    with gr.Blocks() as ui_component:
        gr.HTML("<h1>StableQueue Test Tab</h1>")
    
    return [(ui_component, "StableQueue", "stablequeue_tab")]

# Register the callbacks
print("STABLEQUEUE: Registering callbacks")
script_callbacks.on_ui_tabs(on_ui_tabs)
script_callbacks.on_ui_settings(register_stablequeue_settings)

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