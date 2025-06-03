# **Programmatic Parameter Extraction from Stable Diffusion Forge WebUI Extensions**

## **1\. Introduction: The Challenge of Comprehensive Parameter Extraction in Forge WebUI Extensions**

The objective of programmatically capturing a complete set of image generation parameters from within a Stable Diffusion Forge WebUI extension, without initiating local image generation, presents a nuanced technical challenge. This task is driven by the need to dispatch these parameters to a remote queue system for external processing. The complexity arises from the distributed nature of these parameters, which are not confined to core UI elements but also emanate from a diverse ecosystem of active extensions, each potentially possessing unique data structures and UIs. Stable Diffusion Forge, itself an evolution of the AUTOMATIC1111 Stable Diffusion WebUI 1, leverages the Gradio framework for its user interface.3 Consequently, any solution must navigate the intricacies of both Forge's backend processing and Gradio's component interaction model.  
This report aims to provide a comprehensive technical deep-dive into the internal mechanisms by which Stable Diffusion Forge aggregates generation parameters. It will explore how an extension can effectively intercept this complete parameter set—encompassing basic settings, model selections, LoRA configurations, and data from active extensions like ControlNet, IP-Adapter, and Regional Prompters—just prior to the point of image synthesis.  
The core of this endeavor lies in understanding that the WebUI, before initiating the diffusion process, must consolidate all user-specified and extension-provided parameters into a unified structure. The challenge for an extension developer is to tap into this fully formed parameter set at the precise moment after its assembly but before the computationally intensive generation begins. Simply iterating through visible Gradio components may prove insufficient or overly complex, as some components might not be easily accessible, or their values might have undergone preliminary processing or transformation by the time an extension hook is invoked. The critical aspect is capturing the parameters exactly as the generation engine would receive them.  
Furthermore, the strict requirement to avoid triggering local generation significantly influences the choice of interception strategy. The extension must not only read the parameters but also possess the capability to halt or bypass the standard image generation workflow within Forge. This necessitates a careful selection of integration points and methods that offer control over the execution flow.

## **2\. Core Parameter Collection in Stable Diffusion Forge: The StableDiffusionProcessing Object**

At the heart of Stable Diffusion Forge's image generation pipeline lies the StableDiffusionProcessing class, typically instantiated as an object named p. This object, defined within modules/processing.py 5, serves as the central repository for the majority of parameters governing the image generation process. When a user initiates generation, for instance, by clicking the "Generate" button, values from various Gradio UI components are collected and used to populate the attributes of this p object. This population occurs before any custom script's processing methods are invoked.  
Key attributes of the p object that store core generation settings include:

* **Prompts:** p.prompt (positive prompt) and p.negative\_prompt.  
* **Seed:** p.seed, p.subseed, and p.subseed\_strength for controlling randomness and variations.  
* **Sampling Parameters:** p.steps (number of sampling steps) and p.sampler\_name (or p.sampler\_index identifying the chosen sampler).  
* **Guidance Scale:** p.cfg\_scale (Classifier Free Guidance scale).  
* **Dimensions:** p.width and p.height of the output image.  
* **Models:** p.sd\_model (an object representing the loaded checkpoint) and p.sd\_vae (an object representing the loaded VAE).  
* **Overrides:** p.override\_settings is a dictionary that can hold temporary settings to override the main UI settings for a single generation run. This is particularly relevant for API-driven generations or advanced scripting scenarios.7 Capturing these overrides is essential, as they represent the actual values used if present.  
* **High-Resolution Fix:** Parameters such as p.enable\_hr, p.hr\_scale, p.hr\_upscaler, p.hr\_second\_pass\_steps, and p.denoising\_strength control the high-resolution fix pass.  
* **Batching:** p.n\_iter (number of iterations/batches) and p.batch\_size (number of images per batch).  
* **Miscellaneous:** p.restore\_faces, p.tiling, and p.extra\_generation\_params (a dictionary often used to store a string representation of parameters for image metadata).

The values for these attributes are sourced from the corresponding Gradio UI elements. For example, text input fields for prompts, sliders for steps and CFG scale, and dropdowns for samplers and models, all contribute their state to the p object. This process ensures that by the time custom scripts or extensions are engaged in the generation lifecycle, the p object represents a comprehensive snapshot of the user's intent for the core settings. This p object, therefore, becomes the primary target for an extension aiming to capture these fundamental parameters. Its state, just before the sampling process begins, is the "golden copy" of the core generation configuration.  
The handling of LoRA (Low-Rank Adaptation) and LyCORIS models adds another layer of complexity. These modifications can be specified directly within the prompt string (e.g., \<lora:my\_lora:0.8\>) or managed through dedicated extension UIs. The effect of these LoRAs—which models are active and their respective weights—must be captured. This information might be parsed from p.prompt, reflected in p.extra\_generation\_params, or, in more advanced Forge implementations or via specific extensions, potentially managed through dedicated attributes within p or by modifications to p.sd\_model itself. Forge documentation on LoRA handling, such as "How to make LoRAs more precise" , implies sophisticated internal management that the capture mechanism must account for.  
The existence and behavior of p.override\_settings and the associated API endpoint /sdapi/v1/options 7 for setting persistent options underscore a dynamic settings architecture. Parameters in override\_settings take precedence for the specific generation run, making their capture crucial for an accurate representation of the effective parameters. Discussions around API behavior, such as issues with override\_settings for model loading in Forge 9, indicate that the exact interpretation and application of these overrides can evolve and require careful verification within the target Forge version.

## **3\. Decoding Extension Parameters: The p.script\_args Deep Dive**

Beyond the core parameters held directly in the StableDiffusionProcessing object (p), Stable Diffusion Forge, like its predecessor AUTOMATIC1111 WebUI, relies heavily on a scripting system defined in modules/scripts.py 10 for extending functionality. Extensions, particularly those that are always active and influence every generation (termed AlwaysOnScripts), contribute their own sets of parameters. These are not typically individual attributes on p but are consolidated into a special list: p.script\_args.  
The Script class in modules/scripts.py provides the foundation for extensions. Its ui() method is responsible for defining the Gradio components that constitute the extension's user interface. The values from these components are then passed to the script's backend processing methods (e.g., process(), before\_process(), post\_process()). For AlwaysOnScripts such as ControlNet, IP-Adapter, or Regional Prompters, these values are collected and funneled into p.script\_args.  
p.script\_args is a flat list containing the arguments for *all* active AlwaysOnScripts, concatenated in the order that the scripts are loaded and processed by the WebUI. Each script is allocated a specific slice within this list, demarcated by script.args\_from and script.args\_to attributes, which are assigned by the ScriptRunner when scripts are prepared.10  
The primary challenge for a custom extension aiming to capture parameters from *other* extensions lies in parsing p.script\_args. This involves several steps:

1. **Identify Active Scripts:** Iterate through p.scripts.alwayson\_scripts (or p.scripts.scripts and filter by the is\_alwayson attribute).  
2. **Determine Argument Slice:** For each identified script s, retrieve its s.args\_from and s.args\_to indices.  
3. **Extract Slice:** Obtain the relevant sub-list from p.script\_args using these indices: current\_script\_args \= p.script\_args\[s.args\_from:s.args\_to\].  
4. **Interpret Slice:** This is the most complex step. The structure (order, data types, meaning) of current\_script\_args is defined by the return values of that *specific script's* ui() method. There is no standardized schema or introspection mechanism to automatically discover this structure. The capturing extension must have prior knowledge of how each target extension packages its UI values.

Consider **ControlNet** 12 as a prominent example. ControlNet allows users to enable multiple "units," each with its own UI elements: an enable checkbox, model selection dropdown, weight slider, input image area, preprocessor choice, resolution slider, and various threshold controls. The scripts/controlnet.py script defines how these UI component values are ordered when returned by its ui() method. This order dictates their arrangement within ControlNet's designated slice of p.script\_args. A discussion on GitHub regarding ControlNet's script\_args 11 confirms this structure and highlights the necessity of respecting the argument order and count, especially when multiple ControlNet units are active. Each unit's parameters are concatenated. The ControlNetUnit class, part of ControlNet's internal structure 13, likely encapsulates the parameters for a single such unit. Some Forge variants might alter ControlNet's UI presentation, for example, by moving units into gr.Tab elements 14, but the underlying principle of parameter collection into script\_args is expected to persist.  
Similarly, extensions like **IP-Adapter** 15 and **Regional Prompters** will have their own ui() methods and, consequently, their own specific data structures within their respective p.script\_args slices. IP-Adapter is often integrated as a type of ControlNet unit 16, meaning its parameters might be found within a ControlNet unit's argument block rather than as a separate top-level entry in p.script\_args.  
This "black box" nature of p.script\_args means that without specific knowledge of each target script's ui() method return signature, the extracted slice is just an opaque list of values. Robust parsing requires the capturing extension to effectively hardcode or have configurable "decoders" for the argument structures of common extensions it wishes to support.  
The order of scripts in p.scripts.alwayson\_scripts directly determines the sequence of their data blocks within p.script\_args. This order can be influenced by factors such as installation sequence or user configuration of script loading order. Therefore, relying on fixed absolute indices within p.script\_args to find a particular extension's data is highly fragile. A robust approach involves iterating p.scripts.alwayson\_scripts, identifying target scripts by their title() or another unique identifier, and then using their respective args\_from and args\_to attributes to locate their data.  
For extensions supporting multiple instances or units, like ControlNet, their slice in p.script\_args will contain a repeating pattern of arguments. If a ControlNet unit has, for example, 15 parameters, and three units are configured, ControlNet's segment in p.script\_args will be 45 elements long. The parsing logic must be aware of the number of parameters per unit and the number of active units (often configurable via shared.opts.control\_net\_max\_models\_num or by checking an 'enabled' flag for each unit within the parsed arguments).  
To provide a concrete illustration, the following table outlines a typical structure for the arguments corresponding to a *single* ControlNet unit as it might appear in its slice of p.script\_args. The exact order and content can vary with ControlNet versions, so inspecting the ui() method of the specific controlnet.py in use is always recommended.  
**Table: Example p.script\_args Slice for a Single ControlNet Unit**

| Index (Conceptual) | Parameter Name (Typical) | Data Type (Typical Python) | Gradio Component (Likely Origin) | Notes |
| :---- | :---- | :---- | :---- | :---- |
| 0 | enabled | bool | gr.Checkbox("Enable") | Whether this ControlNet unit is active. |
| 1 | module | str | gr.Dropdown("Preprocessor") | Selected preprocessor (e.g., "canny", "depth\_midas", "none"). |
| 2 | model | str | gr.Dropdown("Model") | Selected ControlNet model name (e.g., "control\_v11p\_sd15\_canny \[abcdef12\]"). |
| 3 | weight | float | gr.Slider("Control Weight") | The weight of this ControlNet unit's influence. |
| 4 | image | dict or None | gr.Image("Image") | Input image. Often a dict: {"image": "base64\_data", "mask": "base64\_data\_or\_none"} or file path. |
| 5 | resize\_mode | str or int | gr.Radio/Dropdown("Resize mode") | E.g., "Just Resize", "Scale to Fit (Inner Fit)", "Envelope (Outer Fit)". Represented by string or index. |
| 6 | low\_vram | bool | gr.Checkbox("Low VRAM") | Whether to use low VRAM mode for this unit. |
| 7 | processor\_res | int | gr.Slider("Preprocessor Resolution") | Resolution for the preprocessor. |
| 8 | threshold\_a | float | gr.Slider("Threshold A / Canny Low") | First preprocessor-specific threshold (e.g., Canny low threshold). |
| 9 | threshold\_b | float | gr.Slider("Threshold B / Canny High") | Second preprocessor-specific threshold (e.g., Canny high threshold). |
| 10 | guidance\_start | float | gr.Slider("Starting Control Step") | Timestep ratio at which ControlNet guidance begins. |
| 11 | guidance\_end | float | gr.Slider("Ending Control Step") | Timestep ratio at which ControlNet guidance ends. |
| 12 | control\_mode | str or int | gr.Radio("Control Mode") | E.g., "Balanced", "My prompt is more important", "ControlNet is more important". |
| 13 | pixel\_perfect | bool | gr.Checkbox("Pixel Perfect") | Enable pixel-perfect processing. |
| 14+ | \*args (additional) | Any | Varies | Some preprocessors or ControlNet versions might add more parameters. |

This table demystifies a segment of p.script\_args, providing a concrete example of the data structure an extension would need to parse for one of the most prevalent AlwaysOnScripts.

## **4\. Strategies for Intercepting Parameters Before Generation**

To capture the complete set of generation parameters programmatically from within a Stable Diffusion Forge WebUI extension *before* local generation occurs, several interception strategies can be considered. The choice of strategy hinges on effectiveness, robustness against WebUI updates, and the ability to prevent local generation.  
**Option 1: Leveraging Script Processing Hooks (Recommended)**  
The most idiomatic and generally robust approach is to design the capturing extension as an AlwaysOnScript. The WebUI's scripting system 10 provides several lifecycle methods that scripts can implement. The process(self, p, \*args) or before\_process(self, p, \*args) methods are particularly suitable:

* p: This argument is the fully populated StableDiffusionProcessing object, containing all core parameters and the script\_args list populated from all active AlwaysOnScripts.  
* \*args: This tuple contains the values returned from the Gradio components defined in *your capturing extension's own* ui() method. These are typically less relevant for capturing parameters from *other* parts of the UI or other extensions.

At the point these methods are called, p represents the complete state that Forge is about to use for image generation. This is the ideal juncture for interception. The capturing logic would involve:

1. Accessing core parameters directly from p's attributes (e.g., p.prompt, p.steps).  
2. Iterating through p.scripts.alwayson\_scripts. For each script s in this list, its specific arguments can be found in the slice p.script\_args\[s.args\_from:s.args\_to\].  
3. Aggregating these core and script-specific parameters.  
4. Serializing the aggregated data.  
5. Implementing a mechanism to prevent the actual image generation from proceeding (detailed in Section 7).

This method aligns with the WebUI's intended extension mechanism and is less likely to break with minor UI updates compared to direct UI manipulation. Forge, being based on AUTOMATIC1111, inherits this scripting system, making these hooks reliable integration points.1 They are invoked after the UI has populated p but before the core sampling process begins.  
**Option 2: Modifying or Tapping into Gradio Event Handlers (Highly Complex, Not Recommended)**  
The main "Generate" button in the Forge UI (likely defined in webui.py or modules/ui.py) is associated with a Gradio .click() event handler. This handler is responsible for orchestrating the collection of values from all relevant UI components and populating the p object.  
Theoretically, one could attempt to intercept or modify this core event handler. However, this approach presents significant drawbacks:

* **Fragility:** It would likely require monkey-patching core Forge or Gradio code, making the extension highly susceptible to breakage with any WebUI updates.  
* **Complexity:** Identifying the correct handler and safely injecting custom logic without disrupting normal operation is non-trivial.  
* **Access:** An extension script does not typically have direct access to modify the event handlers of core UI components defined outside of its own ui() method.

While Gradio offers mechanisms like gr.Blocks().load() or other event triggers, these are generally designed for component-specific interactions or page-level events, not for global interception of a primary action like image generation by an unrelated extension. The Gradio event model is component-centric; an extension doesn't "own" or easily subscribe to the main Generate button's comprehensive parameter collection event in a way that allows it to preemptively extract all data.  
**Option 3: Exploring Forge-Specific Internal APIs or Hooks (Research Dependent)**  
Stable Diffusion Forge introduces specific optimizations and features, such as the Unet Patcher.1 It is conceivable that the Forge codebase (lllyasviel/stable-diffusion-webui-forge ) might contain new callback systems, events, or centralized parameter handling mechanisms beyond the standard A1111 scripting system.  
A thorough examination of Forge's internal modules, particularly those involved in UI management, script running, and processing, might reveal such hooks. However, any such internal APIs are unlikely to be documented as stable interfaces for extension development and could change without notice. An example of interacting with Forge internals was seen in a workaround for API-based model loading, which called main\_entry.refresh\_model\_loading\_parameters().9 While this indicates the presence of internal functions managing parameter states, relying on such non-public functions for a critical task like parameter capture is risky.  
Unless a clearly defined and supported Forge-specific hook for pre-generation parameter access is identified, the standard script processing hooks (Option 1\) remain the most reliable approach.

## **5\. Accessing Gradio Component Values Programmatically (Beyond p.script\_args)**

While the StableDiffusionProcessing object (p) and its script\_args attribute should contain nearly all parameters required for generation by the time a script's process() method is called, it's worth considering other ways Gradio component values *could* be accessed, primarily to understand why they are generally not the preferred route for this specific task.  
The WebUI itself performs the crucial step of collecting values from the diverse Gradio UI elements and populating p. An extension should leverage this existing orchestration rather than attempting to replicate it. Trying to scrape the entire Gradio UI state live from an extension script would be complex and brittle.  
**Direct Gradio Component Tree Traversal:**  
Gradio applications built with gr.Blocks() organize components in a hierarchical structure.17 If an extension could obtain a reference to the root gr.Blocks instance (often named demo), it could theoretically traverse demo.children (and their children, recursively) to find individual components. However:

1. **Accessibility:** Obtaining a reference to the root Blocks instance from within an extension script's process() method is not a standard or straightforward operation. The script operates in a context where p is the primary data carrier.  
2. **Mapping and Preprocessing:** Even if components were accessible, mapping these raw Gradio component instances back to their meaningful parameters, in the correct format expected by the backend, would be a significant challenge. Gradio components have preprocess methods that convert frontend data (e.g., a file path from an gr.Image component) into a Python-native format (e.g., a NumPy array or PIL Image) suitable for the backend function.3 Accessing a component's raw .value attribute might bypass this crucial preprocessing, yielding data in an unusable or unexpected format. The main "Generate" button's callback logic already handles calling these preprocess methods for the inputs it's configured to receive. Replicating this for all relevant components globally would be error-prone.

**Using gr.State:**  
The gr.State component is designed for managing hidden state within a Gradio application.19 It allows data to be passed between different event listeners for a single user session without being explicitly visible in the UI. While gr.State is useful for managing complex state *within an extension's own UI*, it is not a mechanism for one extension to globally access the values of arbitrary UI components defined elsewhere (e.g., in the main UI or other extensions).  
**Accessing Global WebUI Settings via shared.opts:**  
The Stable Diffusion WebUI maintains a global object, typically shared.opts, which stores various settings configured by the user through the "Settings" tab of the UI.20 modules/shared.py is the likely origin of this object. These settings can influence aspects of the generation process.

* Some of these options might already be reflected in p.override\_settings or directly used during the initialization of p.  
* An extension can directly read values from shared.opts if it needs to capture global configuration details that are not part of the per-generation parameters in p. For instance, shared.opts.control\_net\_max\_models\_num dictates how many ControlNet units are available.

The key takeaway is that for capturing the parameters *as they are about to be used for generation*, the p object (including p.script\_args) is the most reliable source. It represents the culmination of the WebUI's own parameter collection and preprocessing logic. Attempting to bypass this by directly querying Gradio components introduces unnecessary complexity and fragility.

## **6\. Assembling and Serializing the Complete Parameter Payload**

Once the StableDiffusionProcessing object (p) is available within the extension's chosen hook (e.g., the process method of an AlwaysOnScript), the next step is to consolidate all relevant information into a structured payload and serialize it, typically to JSON, for transmission to the remote queue system.  
**Consolidation Strategy:**  
A systematic approach to assembling the payload is crucial for ensuring completeness and downstream usability.

1. **Initialize Payload:** Begin with an empty Python dictionary that will hold all parameters.  
   Python  
   payload \= {}

2. **Core Parameters from p:** Populate the payload with direct attributes from the p object. This includes:  
   * prompt, negative\_prompt, steps, sampler\_name, cfg\_scale, seed, subseed, subseed\_strength, width, height, restore\_faces, tiling, etc.  
   * High-resolution fix parameters: enable\_hr, hr\_scale, hr\_upscaler, hr\_second\_pass\_steps, denoising\_strength.  
   * Batch parameters: n\_iter, batch\_size.

Python  
payload\['prompt'\] \= p.prompt  
payload\['negative\_prompt'\] \= p.negative\_prompt  
payload\['steps'\] \= p.steps  
\#... and so on for other core attributes

3. **Override Settings:** Incorporate p.override\_settings. These settings should ideally supersede any conflicting core parameters already added. A simple dictionary update can achieve this:  
   Python  
   if hasattr(p, 'override\_settings') and p.override\_settings:  
       payload.update(p.override\_settings)

4. **Script Arguments from p.script\_args:** This is where data from other AlwaysOnScripts like ControlNet and IP-Adapter are captured.  
   * Iterate through p.scripts.alwayson\_scripts.  
   * For each script s, use its title (e.g., s.title().lower().replace(' ', '\_')) or a known unique identifier as a key in the payload.  
   * Extract the script's arguments: args\_slice \= p.script\_args\[s.args\_from:s.args\_to\].  
   * Store this args\_slice. For well-known extensions, this raw slice should be further parsed into a more structured format (e.g., a list of dictionaries for ControlNet units).

Python  
payload\['alwayson\_scripts'\] \= {}  
if hasattr(p.scripts, 'alwayson\_scripts'):  
    for script in p.scripts.alwayson\_scripts:  
        script\_key \= script.title().lower().replace(' ', '\_')  
        args\_slice \= p.script\_args\[script.args\_from:script.args\_to\]  
        \# Further parsing of args\_slice for known scripts (e.g., ControlNet)  
        \# would happen here before assignment.  
        payload\['alwayson\_scripts'\]\[script\_key\] \= args\_slice  
The structure of the API payload for /sdapi/v1/txt2img 7, which often includes an alwayson\_scripts dictionary, serves as a good model for this part of the custom payload.

5. **Essential Metadata:** Include identifiers for critical components to aid reproducibility:  
   * sd\_model\_name: p.sd\_model.model\_name (or title)  
   * sd\_model\_hash: p.sd\_model.sd\_model\_hash (or a similar attribute holding the short hash).  
   * sd\_vae\_name: Name of the VAE, if not baked in or default (e.g., shared.sd\_vae.loaded\_vae\_file or from p.override\_settings.get('sd\_vae')).  
   * sd\_vae\_hash: Hash of the VAE, if available.  
   * Active LoRAs: A list of dictionaries, each specifying name and weight. This data might need to be parsed from the prompt string or, if an extension manages LoRAs, from its specific script\_args or attributes it might add to p.  
   * Versions: Stable Diffusion Forge version, and potentially versions of key extensions if programmatically accessible.

**Serialization Format:**  
JSON is the recommended format for serialization due to its widespread compatibility, human-readability, and ease of parsing by various systems. Python's json module can be used for this:

Python

import json  
serialized\_payload \= json.dumps(payload, indent=2)

Ensure that all data types within the payload dictionary are JSON-serializable. Common culprits for non-serializability include PIL Image objects, NumPy arrays if not converted to lists, or custom Python objects.

* Gradio components, through their preprocess methods 3, generally convert complex inputs (like images) into Python-native types (e.g., base64 encoded strings for images, or dictionaries containing image data) that are often directly JSON-serializable or easily convertible. The values ending up in p.script\_args should reflect these preprocessed forms.  
* If an image from a ControlNet unit (or similar) is needed as raw pixel data by the remote system, it should be converted to a base64 string. If only a reference is needed and the image is saved, a file path could be used (though this implies shared storage or subsequent file transfer).

**Handling Complex Extension Data (Example: ControlNet):**  
The args\_slice for an extension like ControlNet will contain a flat list of concatenated arguments for all its enabled units.11 This needs to be unflattened:

1. **Determine Arguments Per Unit:** Ascertain the number of arguments returned by ControlNet's ui() method for a single unit. This usually requires inspecting scripts/controlnet.py or relying on established knowledge of its structure (see Table in Section 3). Let this be num\_args\_per\_unit.  
2. **Chunk the Slice:** Iterate through the args\_slice for ControlNet in chunks of num\_args\_per\_unit. Each chunk represents one ControlNet unit.  
   Python  
   \# Example for ControlNet args\_slice  
   controlnet\_units\_data \=  
   num\_args\_per\_cn\_unit \= 15 \# Example value, verify from ControlNet source  
   cn\_args \= payload\['alwayson\_scripts'\].get('controlnet',) \# Get the raw slice

   for i in range(0, len(cn\_args), num\_args\_per\_cn\_unit):  
       unit\_args\_list \= cn\_args\[i:i \+ num\_args\_per\_cn\_unit\]  
       if not unit\_args\_list or not unit\_args\_list: \# Assuming index 0 is 'enabled'  
           continue \# Skip if unit is not enabled or args are empty

       \# Convert list to a dictionary for better readability, using known param names  
       unit\_data \= {  
           "enabled": unit\_args\_list,  
           "module": unit\_args\_list,  
           "model": unit\_args\_list,  
           "weight": unit\_args\_list,  
           "image": unit\_args\_list, \# This might be a dict itself  
           "resize\_mode": unit\_args\_list,  
           \#... and so on for all parameters of a unit  
       }  
       controlnet\_units\_data.append(unit\_data)  
   payload\['alwayson\_scripts'\]\['controlnet'\] \= controlnet\_units\_data \# Replace raw slice with structured list

The primary difficulty in assembling a universally useful payload is the robust parsing of p.script\_args for diverse and potentially unknown extensions. While a generic approach might store raw argument slices keyed by script names, a more valuable payload requires specific parsers for known, critical extensions. This allows downstream systems to semantically understand the parameters (e.g., "ControlNet Unit 1 uses Canny model with weight 0.8").  
Capturing model and VAE hashes, rather than just their names, is paramount for ensuring reproducibility, as names can be ambiguous or user-defined, while hashes uniquely identify the file contents.7

## **7\. Preventing Local Generation Post-Capture**

A core requirement is that after the parameters are captured and serialized, the standard local image generation process within Stable Diffusion Forge must be prevented. This needs to be handled gracefully, ideally without presenting an error to the user in the WebUI. The interception occurs within an AlwaysOnScript's process (or before\_process) method.  
Several strategies can be employed:  
**Method 1: Modifying the StableDiffusionProcessing (p) Object**  
This approach involves altering attributes of the p object to signal that generation should be skipped.

* **Dedicated Skip Flag:** The most direct way would be if StableDiffusionProcessing had a built-in flag like p.do\_not\_generate\_image or p.skip\_processing. If such a flag exists and is respected by the main processing loop in modules/processing.py , setting it to True would be ideal. If not, an extension could dynamically add such an attribute (e.g., p.do\_not\_generate\_image \= True). However, for this to be effective, the core processing logic in modules/processing.py would need to check for this custom attribute. This makes the solution dependent on a modification to Forge's core code, which might not be desirable or maintainable.  
* **Manipulating Critical Parameters:** Setting p.steps \= 0 or assigning an invalid sampler name could halt generation. However, this is likely to result in an error message in the UI rather than a clean skip, and might have unintended side effects if other scripts run after the capturing script.

**Method 2: Returning a Custom Processed Object (If using the process method)**  
The Script.process() method is typically expected to return an instance of the Processed class (defined in modules.processing).10 This object usually contains the generated images, seed, prompt, and other generation info.  
The capturing script could return a specially crafted Processed object:

Python

from modules.processing import Processed  
\# Inside your script's process(self, p, \*args) method:  
\#... after capturing and serializing parameters...

\# Signal that processing is complete and parameters were captured.  
\# Provide empty images and an informative message.  
info\_text \= "Parameters captured successfully. Local generation skipped."  
return Processed(p, images\_list=, seed=p.seed, info=info\_text, subseed=p.subseed, all\_prompts=\[p.prompt\], all\_seeds=\[p.seed\], all\_subseeds=\[p.subseed\], infotexts=\[info\_text\])

If the capturing script is the *last* AlwaysOnScript to run, or if subsequent scripts respect the content of the Processed object passed to them (if they receive it), this can effectively stop the pipeline. The main image generation loop in modules/processing.py (specifically functions like process\_images\_inner ) would then conclude with this Processed object. This is generally a cleaner approach than arbitrary p modifications if the script lifecycle allows it to be the effective final step.  
**Method 3: Raising a Specific, Custom Exception (Potentially Cleanest with Minor Core Adjustment)**  
A robust method for altering control flow is to raise a custom exception from the script's process() method.

Python

class ParameterCaptureCompleteException(Exception):  
    """Custom exception to signal successful parameter capture and skip generation."""  
    pass

\# Inside your script's process(self, p, \*args) method:  
\#... after capturing and serializing parameters...  
raise ParameterCaptureCompleteException("Parameters captured, skipping local generation.")

For this to work gracefully, the calling code within modules/processing.py (specifically where script process methods are invoked) would need to be wrapped in a try...except ParameterCaptureCompleteException: block. This block would catch the specific exception and interpret it as a signal to terminate the current generation task cleanly, perhaps logging the success message and avoiding any error display in the UI.  
This approach is clean because it doesn't rely on ad-hoc flags in p or the script's position in the processing chain. It clearly signals intent. However, it typically requires a small, targeted modification to Forge's modules/processing.py to add the try...except handler if one doesn't already exist for such custom script signals. Without this modification, the exception would propagate and appear as an error to the user.  
The choice among these methods depends on the desired level of invasiveness into core Forge code and how modules/processing.py handles script outputs and exceptions. The goal is to achieve a silent, successful termination of the local generation path after parameters are secured.

## **8\. Key Forge/WebUI Modules and Data Flow for Parameter Handling**

Understanding the data flow and the roles of key modules within Stable Diffusion Forge is crucial for successfully intercepting generation parameters. The process generally follows these steps:

1. **User Interaction:** The user interacts with the Gradio-based user interface. UI elements for core parameters are primarily defined in modules/ui.py (and potentially webui.py), while extensions (like ControlNet, IP-Adapter) define their own UI components within their respective Script.ui() methods.10  
2. **Generation Trigger:** The user clicks the "Generate" button (or triggers a similar action).  
3. **Gradio Event Handling:** The .click() event handler associated with the "Generate" button (likely located in webui.py or modules/ui.py) is executed.  
4. **Parameter Collection by WebUI:** This core event handler is responsible for gathering values from all relevant Gradio input components across the main UI and active script UIs.  
5. **StableDiffusionProcessing Instantiation:** An instance of the StableDiffusionProcessing class (typically p) is created.  
6. **Population of p:** The collected values are used to populate p's attributes (e.g., p.prompt, p.steps) and the p.script\_args list. This step is the central aggregation point where the complete set of parameters, as understood by the WebUI, is formed.  
7. **Processing Initiation:** The modules.processing.process\_images(p) function (or a similar top-level processing function) is called with the populated p object.  
8. **Script Execution Loop:** Within process\_images (or its inner counterpart, process\_images\_inner), the system iterates through the scripts registered in p.scripts.scripts (often filtered for AlwaysOnScripts or the currently selected script). It calls their lifecycle methods like before\_process(), process(), and postprocess() in sequence.10  
9. **Extension Hook Execution:** The capturing extension's process() (or before\_process()) method is called as part of this loop. At this moment, the extension has access to the fully populated p object. It can then perform its parameter capture, serialization, and implement logic to halt further (local) processing.

This data flow highlights that the extension does not need to re-implement the complex logic of traversing the Gradio UI and collecting values. It can rely on the WebUI's own mechanisms to assemble the p object and then access this object at a well-defined point in the processing pipeline.  
**Key Files and Their Roles:**

* **webui.py**: The main script that launches the WebUI. It initializes the Gradio application, defines the overall UI structure (tabs, etc.), and sets up top-level event handlers, including those for the main generation buttons.22 It orchestrates the loading of modules and extensions.  
* **modules/ui.py**: Often contains functions responsible for creating major UI sections like the txt2img and img2img tabs, including their core Gradio components (prompt boxes, sliders, dropdowns).24 modules/ui\_components.py may also play a role in defining reusable UI elements.  
* **modules/processing.py**: Contains the core image generation logic. This includes the StableDiffusionProcessing class definition, functions like process\_images() and process\_images\_inner() that manage the generation pipeline, and the loop that executes script hooks.5  
* **modules/scripts.py**: Defines the Script base class, ScriptRunner (which manages script execution), and handles the loading and registration of all scripts (both built-in and from extensions).2 It's responsible for managing args\_from and args\_to for p.script\_args.  
* **modules/shared.py**: A crucial module for global state and shared objects. It typically defines shared.opts (user-configurable settings from the Settings tab), shared.cmd\_opts (command-line arguments passed at startup), shared.sd\_model (the currently loaded Stable Diffusion model), shared.sd\_vae (the currently loaded VAE), and other shared resources or utility functions.2  
* **extensions-builtin/ and extensions/**: These directories house the code for built-in and user-installed extensions, respectively. Each extension typically follows the structure mandated by modules/scripts.py, often including its own scripts/ subdirectory with a Python file defining its Script subclass (e.g., sd-webui-controlnet/scripts/controlnet.py 13).  
* **launch.py**: Handles the initial setup, environment checks, and launching of webui.py.22  
* **params.txt**: A file where current parameters are reportedly saved before generation.28 If this file is written early enough and contains a comprehensive, parseable snapshot of parameters, it could offer an alternative extraction path.

A thorough understanding of this architecture, particularly the roles of p, p.script\_args, and the script execution lifecycle, is paramount for developing a robust parameter capturing extension.

## **9\. Recommendations and Implementation Best Practices**

To programmatically capture complete image generation parameters from within a Stable Diffusion Forge WebUI extension without triggering local generation, the following recommendations and best practices should be considered:

1. **Preferred Interception Method:**  
   * Implement the capturing logic as an **AlwaysOnScript**.  
   * Utilize its **process(self, p, \*args) method** as the primary point of interception. At this stage, the StableDiffusionProcessing object p is fully populated with core parameters and p.script\_args contains data from all other active AlwaysOnScripts. This is the most stable and idiomatic approach within the WebUI extension framework.10  
2. **Parameter Parsing and Assembly:**  
   * **Core Parameters:** Directly access attributes of p (e.g., p.prompt, p.steps, p.width, p.sd\_model.sd\_model\_hash).  
   * **Override Settings:** Merge p.override\_settings into the collected core parameters.  
   * **Extension Parameters (p.script\_args):**  
     * Iterate p.scripts.alwayson\_scripts. For each script s, use s.title() (or a more robust unique identifier if available) as a key. Extract its argument slice p.script\_args\[s.args\_from:s.args\_to\].  
     * **For known, critical extensions (e.g., ControlNet, IP-Adapter):** Develop specific parsers to convert their raw argument slices into structured dictionaries or lists of objects (e.g., a list of ControlNet unit configurations). This may require inspecting the ui() method of those extensions to understand the argument order and types. This is crucial for downstream usability of the captured data.  
     * **For unknown extensions:** As a fallback, either store their script\_args slice as a raw list under the script's key or attempt a very generic interpretation. Clearly document that parsing for unknown extensions is best-effort.  
     * Consider making the list of "known" extensions (for which specific parsers are implemented) configurable by the user of your capturing extension.  
3. **Serialization:**  
   * Use **JSON** as the serialization format for its wide compatibility and readability.  
   * Ensure all data types are JSON-serializable. Convert complex objects like PIL Images (e.g., from ControlNet input) to base64 strings or save them to temporary files and include their paths if the image data itself is required by the remote system. Values in p.script\_args should generally be Python-native types due to Gradio's preprocessing.  
4. **Halting Local Generation:**  
   * **Raising a custom, documented exception** from your script's process() method (e.g., ParameterCaptureCompleteException) is a clean way to signal that processing should stop. This may require a minor, well-contained modification to Forge's modules/processing.py to catch this specific exception and handle it gracefully (i.e., stop processing without showing a UI error).  
   * Alternatively, if your script can be guaranteed to run last or if subsequent scripts do not interfere, returning a Processed object with empty image results and an informational message can also work.10 This avoids core code modification but might be less robust.  
5. **Robustness and Compatibility:**  
   * The primary point of fragility is the parsing of p.script\_args for other extensions. Their UI and argument order can change with updates, breaking your parsers.11 Clearly document this limitation.  
   * Implement comprehensive error handling, especially around parsing script\_args. Log errors clearly to aid debugging.  
   * Strive to depend on stable parts of the WebUI API (like the Script class structure and p object attributes) rather than internal implementation details.  
6. **Alternative Data Source: params.txt**  
   * Investigate the params.txt file mentioned in.28 If this file is:  
     * Written *before* your script's process() hook is called.  
     * Contains *all* parameters (core and resolved script arguments) in a reliably parseable format (e.g., JSON or a similar structured text).  
   * Then, reading and parsing this file could be a significantly simpler and more robust method than manually assembling parameters from p and p.script\_args. This would bypass the complexities of script\_args parsing for other extensions, as the WebUI would have already done that work. The viability of this approach depends entirely on the timing, content, and format of params.txt.  
7. **User Configuration:**  
   * Allow users to configure which extensions' data your capturing tool should attempt to parse in detail. This can manage expectations and reduce unnecessary processing.  
8. **Code Structure and Maintainability:**  
   * Organize parsers for different extensions into separate modules or classes within your extension for better maintainability.  
   * Keep abreast of changes in Forge and key extensions like ControlNet to update parsers as needed.

By focusing on the p object as the primary source of truth at the process hook, and by carefully managing the parsing of p.script\_args, a functional and relatively robust parameter capturing system can be developed. The potential of params.txt as a pre-aggregated source warrants thorough investigation as it could greatly simplify the implementation.

## **10\. Conclusion**

Programmatically capturing the complete set of image generation parameters from within a Stable Diffusion Forge WebUI extension, without triggering local generation, is a feasible yet intricate task. The solution hinges on leveraging the existing architecture of the WebUI, particularly the StableDiffusionProcessing object (p) and the AlwaysOnScript extension mechanism.  
The recommended approach involves creating an AlwaysOnScript that uses its process() or before\_process() hook to access the p object. At this stage, p contains the core generation parameters (prompt, steps, CFG, dimensions, model choices, etc.) and, crucially, the p.script\_args list, which holds a concatenated series of arguments from all active AlwaysOnScripts like ControlNet and IP-Adapter.  
The primary technical challenge lies in reliably parsing p.script\_args. Each script contributes a slice of arguments whose structure is defined by its own ui() method, without a standardized schema. Therefore, the capturing extension must either include specific parsers for known target extensions (requiring knowledge of their internal argument order) or handle unknown extension data more generically. Iterating p.scripts.alwayson\_scripts to identify each script and its corresponding slice in p.script\_args (via script.args\_from and script.args\_to) is essential for this process.  
Once all parameters are collected from p and p.script\_args, they should be assembled into a comprehensive dictionary and serialized, preferably to JSON. This payload can then be sent to the remote queue system. To prevent local generation, raising a custom, specific exception from the script's process() method, which is then gracefully handled by a modified modules/processing.py, offers a clean way to halt the pipeline. Alternatively, returning a specially crafted Processed object might suffice under certain conditions.  
A noteworthy alternative for parameter collection is the potential use of the params.txt file, which is reportedly saved by the WebUI before generation.28 If this file contains a complete and timely snapshot of all parameters in a parseable format, it could significantly simplify the capture process by obviating the need for manual parsing of p.script\_args.  
The developer must be mindful of the inherent fragility associated with parsing data structures from other extensions, as these can change with updates. Focusing on a core set of supported extensions and providing robust error logging are key to managing this. By understanding the WebUI's internal data flow—from Gradio UI interaction to the population of p and the execution of script hooks—an extension can effectively tap into the complete parameter set at the optimal moment for capture and remote dispatch.

#### **Works cited**

1. caojiachen1/stable-diffusion-webui-forge \- Gitee, accessed June 2, 2025, [https://gitee.com/hqsrawmelon/stable-diffusion-webui-forge](https://gitee.com/hqsrawmelon/stable-diffusion-webui-forge)  
2. lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)  
3. Gradio Components: The Key Concepts, accessed June 2, 2025, [https://www.gradio.app/guides/key-component-concepts](https://www.gradio.app/guides/key-component-concepts)  
4. Blocks And Event Listeners \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/blocks-and-event-listeners](https://www.gradio.app/guides/blocks-and-event-listeners)  
5. Getting errors with using any lora on sdxl models · Issue \#2846 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2846](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2846)  
6. Flux cannot use Lora · Issue \#2625 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2625](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2625)  
7. API · AUTOMATIC1111/stable-diffusion-webui Wiki \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/API)  
8. Guide to txt2img API | Automatic1111 \- Random Bits Software Engineering, accessed June 2, 2025, [https://randombits.dev/articles/stable-diffusion/txt2img](https://randombits.dev/articles/stable-diffusion/txt2img)  
9. API change \- Override settings not working · lllyasviel stable-diffusion-webui-forge · Discussion \#1026 \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1026](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1026)  
10. scripts.py \- AUTOMATIC1111/stable-diffusion-webui \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/modules/scripts.py](https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/modules/scripts.py)  
11. Controlling CN from within another script? · Issue \#444 · Mikubill/sd-webui-controlnet, accessed June 2, 2025, [https://github.com/Mikubill/sd-webui-controlnet/issues/444](https://github.com/Mikubill/sd-webui-controlnet/issues/444)  
12. Mikubill/sd-webui-controlnet: WebUI extension for ControlNet \- GitHub, accessed June 2, 2025, [https://github.com/Mikubill/sd-webui-controlnet](https://github.com/Mikubill/sd-webui-controlnet)  
13. sd-webui-controlnet/scripts/controlnet.py at main \- GitHub, accessed June 2, 2025, [https://github.com/Mikubill/sd-webui-controlnet/blob/main/scripts/controlnet.py](https://github.com/Mikubill/sd-webui-controlnet/blob/main/scripts/controlnet.py)  
14. README.md \- Haoming02/sd-webui-forge-classic \- GitHub, accessed June 2, 2025, [https://github.com/Haoming02/sd-webui-forge-classic/blob/classic/README.md](https://github.com/Haoming02/sd-webui-forge-classic/blob/classic/README.md)  
15. How to Install and Configure Forge: A New Stable Diffusion Web UI \- LunaNotes, accessed June 2, 2025, [https://lunanotes.io/summary/how-to-install-and-configure-forge-a-new-stable-diffusion-web-ui](https://lunanotes.io/summary/how-to-install-and-configure-forge-a-new-stable-diffusion-web-ui)  
16. High-Similarity Face Swapping: Leveraging IP-Adapter and Instant-ID for Enhanced Results, accessed June 2, 2025, [https://myaiforce.com/face-swap-with-ipadapter-and-instantid/](https://myaiforce.com/face-swap-with-ipadapter-and-instantid/)  
17. Controlling Layout \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/controlling-layout](https://www.gradio.app/guides/controlling-layout)  
18. Backend \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/backend](https://www.gradio.app/guides/backend)  
19. State In Blocks \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/state-in-blocks](https://www.gradio.app/guides/state-in-blocks)  
20. User Interface Customizations · AUTOMATIC1111/stable-diffusion-webui Wiki \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/User-Interface-Customizations](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/User-Interface-Customizations)  
21. Stable Diffusion API: \`sdapi/v1/txt2img\` \- HackMD, accessed June 2, 2025, [https://hackmd.io/@qK90-toKQ9SPvHQxXwxWFg/HkfCwzod2](https://hackmd.io/@qK90-toKQ9SPvHQxXwxWFg/HkfCwzod2)  
22. launch.py \- lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/launch.py](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/launch.py)  
23. raw.githubusercontent.com, accessed June 2, 2025, [https://raw.githubusercontent.com/ai-dock/stable-diffusion-webui-forge/main/config/provisioning/default.sh](https://raw.githubusercontent.com/ai-dock/stable-diffusion-webui-forge/main/config/provisioning/default.sh)  
24. Panchovix/stable-diffusion-webui-reForge \- GitHub, accessed June 2, 2025, [https://github.com/Panchovix/stable-diffusion-webui-reForge](https://github.com/Panchovix/stable-diffusion-webui-reForge)  
25. raw.githubusercontent.com, accessed June 2, 2025, [https://raw.githubusercontent.com/dylanhogg/crazy-awesome-python/master/README.md](https://raw.githubusercontent.com/dylanhogg/crazy-awesome-python/master/README.md)  
26. Stable Diffusion Explained with Visualization \- Polo Club of Data Science, accessed June 2, 2025, [https://poloclub.github.io/diffusion-explainer/](https://poloclub.github.io/diffusion-explainer/)  
27. stable-diffusion-webui-forge/modules/initialize.py at main \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/initialize.py](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/initialize.py)  
28. Saving text file with generation parameters \*before\* generation · AUTOMATIC1111 stable-diffusion-webui · Discussion \#14542 \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/14542](https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/14542)