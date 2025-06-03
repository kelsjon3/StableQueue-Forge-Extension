# **Forge Extension Parameter Capture: Version Compatibility and Alternative UI Access Methods**

## **1\. Introduction: The Challenge of Version-Specific UI Access in Forge Extensions**

The development of extensions for rapidly evolving platforms like Stable Diffusion Forge presents unique challenges, particularly in maintaining compatibility across different versions. A critical aspect of many extensions, such as the "StableQueue" system, involves the accurate capture of user interface (UI) parameters at the moment a user initiates an action, like adding a generation task to a queue. The reported failure of StableQueue due to the absence of modules.ui.txt2img\_inputs and modules.ui.img2img\_inputs in the target Forge version underscores the inherent risks of relying on hardcoded paths to internal UI component aggregations. These internal structures are subject to change as Forge, which builds upon the foundation of AUTOMATIC1111's Stable Diffusion WebUI 1, introduces optimizations, new features, and refactors its codebase.  
The primary goal of this report is to provide developers with a comprehensive set of robust, version-agnostic strategies for capturing the complete UI state within a Forge extension. The emphasis will be on dynamic discovery and access techniques that are suitable for implementation within an AlwaysOnScript and its process() hook. This approach is vital for ensuring that extensions like StableQueue can function reliably across diverse Forge installations and updates.  
Robust parameter capture is paramount for several reasons. Firstly, it ensures **extension stability**, minimizing the likelihood of the extension breaking when users update their Forge environment. Secondly, it contributes to a positive **user experience**, as users expect queued generation tasks to precisely reflect the UI settings they configured at the time of queuing. Lastly, it enhances **developer efficiency** by reducing the need for frequent, version-specific patches and maintenance efforts.  
It is important to understand that the "missing" attributes (modules.ui.txt2img\_inputs, etc.) do not necessarily mean that the fundamental UI components themselves—such as the prompt text area, CFG scale slider, or steps input—have been removed from Forge. These components are integral to the WebUI's functionality and are rendered using the Gradio library. What has likely changed is the specific Python variable or internal API within the modules.ui namespace that previously served to aggregate these Gradio components into a directly accessible list or dictionary. The underlying Gradio components persist within the rendered UI tree; the challenge lies in finding a new, more resilient method to access them or their current values, bypassing these now-absent intermediary aggregations.

## **2\. Understanding Forge's UI Structure and Gradio Integration**

Stable Diffusion Forge, much like its predecessor AUTOMATIC1111, constructs its web interface using the Gradio Python library, specifically leveraging the Blocks API.2 The Blocks API provides a flexible way to define complex UIs by arranging components within layout containers such as gr.Row, gr.Column, gr.Tab, and gr.Accordion.6 Interactivity is managed through event listeners attached to components, such as button clicks or value changes. The entire UI is defined in Python scripts, traditionally located in files like webui.py (the main application entry point) and various files within the modules/ directory, particularly modules/ui.py and associated modules/ui\_\*.py files that handle specific UI tabs like txt2img and img2img.2  
Once the Gradio application is launched, these Python-defined components are rendered in the user's web browser. Backend Python code, including extensions, interacts with these components. Typically, the values of input components are passed to backend functions when an event is triggered. For instance, when a "Generate" button is clicked, the inputs argument of its .click() event listener specifies which UI components' values should be collected and passed as arguments to the designated Python callback function.20 For an extension like StableQueue, which needs to capture the state of arbitrary UI components (many of which are not part of its own UI definition) at the moment its "Queue" button is pressed, a mechanism is required to obtain references to these external components or their current values outside of their direct event flow.  
Several key modules within the Forge/A1111 architecture are relevant:

* webui.py: This script typically initializes the main gr.Blocks() application instance and orchestrates the overall UI construction.  
* modules/ui.py (and related ui\_\*.py files): These are responsible for creating the Gradio components for the main txt2img, img2img, and other tabs. The problem statement directly indicates changes within this layer of Forge.  
* modules/scripts.py: This module is crucial as it defines the base Script class, the ScriptRunner that manages script execution, and the AlwaysOnScript behavior. It dictates how UI elements defined by scripts are rendered and, importantly, how their values are collected (often into p.script\_args) and passed to their processing functions.21  
* modules/shared.py: This module serves as a repository for globally accessible objects, such as shared.opts (which holds persistent settings configured in the "Settings" tab) and shared.cmd\_opts (command-line arguments passed at startup).2 It is also a likely candidate for exposing the root gr.Blocks() instance of the application, often referred to as shared.demo.

The entire Forge UI can be conceptualized as a tree structure, with the root gr.Blocks() instance at its apex. Layout elements like rows and columns form the branches, while interactive components such as textboxes, sliders, and dropdowns are the leaves or nodes within these branches. Gradio components can be assigned an elem\_id attribute, which provides a unique identifier for the component in the HTML Document Object Model (DOM) and can be used for backend referencing. They also have a label attribute, which is the visible text descriptor for the component.6 Both elem\_id and label are vital for programmatically identifying and locating specific components within the UI tree.  
The disappearance of aggregated lists like modules.ui.txt2img\_inputs signifies a shift. Extensions can no longer rely on such convenient, pre-packaged abstractions. Instead, they must adopt strategies to interact more directly with the Gradio component tree itself. This means an extension needing the value of, for example, the main prompt textbox must now determine: "Within the overall UI structure, which specific Gradio component instance represents the prompt textbox, and how can I access its current value?" This necessitates an understanding of how gr.Blocks organizes components and the methods available to traverse or query this dynamically constructed UI structure.  
The internal restructuring within Forge that leads to such changes can be attributed to its ongoing development goals. Forge aims for significant optimizations, the introduction of new features (such as support for SVD, Z123, Photomaker, and advanced model types like Flux), and an improved U-Net patching system (UnetPatcher) for greater flexibility and reduced extension conflicts.1 These advancements, particularly those affecting core processing pipelines or requiring new UI paradigms to support different parameter sets, can naturally lead to refactoring of the UI definition code in modules/ui.py or related files. During such refactoring, the precise manner in which component lists were previously created and exposed might be altered or removed if a new internal organization is deemed more suitable or efficient by the Forge developers. This evolutionary nature of the platform makes dynamic UI discovery methods not just beneficial, but essential for extensions striving for broad and lasting compatibility.

## **3\. Strategies for Discovering Core UI Components (txt2img/img2img)**

To reliably capture parameters from core UI elements such as the prompt, negative prompt, steps, CFG scale, width, height, and sampler selection, extensions must move beyond hardcoded paths to specific variables like modules.ui.txt2img\_inputs. The following methods offer more robust alternatives by interacting with the Gradio UI structure at runtime.

### **Method 1: Runtime Traversal of the Gradio Blocks Tree (Primary Recommended)**

This strategy involves programmatically navigating the hierarchical structure of the main Gradio Blocks instance to locate desired UI components.

* **Accessing the Root gr.Blocks Instance**: The foundation of the Forge UI is a gr.Blocks() instance. This instance, often named demo during its creation in webui.py, is typically made globally accessible, often via modules.shared.demo. This shared.demo object serves as the entry point for any UI traversal.6  
* **Traversal Logic**: Gradio layout elements (gr.Row, gr.Column, gr.Tab, gr.Accordion) usually expose their child components through an attribute like children, which is iterable. A recursive Python function can effectively walk this component tree.  
  Python  
  \# Conceptual Python snippet for UI traversal  
  import gradio as gr  
  \# Assume 'modules.shared.demo' holds the root gr.Blocks() instance

  def find\_component\_recursive(layout\_element, elem\_id\_to\_find=None, label\_to\_find=None, component\_type\_to\_find=None):  
      """  
      Recursively searches for a Gradio component.  
      Prioritizes elem\_id, then label, then component\_type if others fail or are not specific enough.  
      """  
      if hasattr(layout\_element, 'elem\_id') and layout\_element.elem\_id \== elem\_id\_to\_find:  
          return layout\_element  
      if label\_to\_find and hasattr(layout\_element, 'label') and layout\_element.label \== label\_to\_find:  
          \# Further check type if label is not unique enough  
          if component\_type\_to\_find is None or isinstance(layout\_element, component\_type\_to\_find):  
              return layout\_element

      \# Fallback to type if elem\_id and label are not primary search criteria or failed  
      if component\_type\_to\_find and elem\_id\_to\_find is None and label\_to\_find is None and isinstance(layout\_element, component\_type\_to\_find):  
          \# This branch is tricky as it might return the first matching type.  
          \# It's better used within a more specific parent, or with additional heuristics.  
          pass \# Needs careful application

      \# Traverse children of layout blocks  
      if hasattr(layout\_element, 'children'):  
          for child in layout\_element.children:  
              found \= find\_component\_recursive(child, elem\_id\_to\_find, label\_to\_find, component\_type\_to\_find)  
              if found:  
                  return found

      \# Handle specific Gradio container types like Tabs and Accordions  
      if isinstance(layout\_element, gr.Tabs) and hasattr(layout\_element, 'tabs'):  
          for tab\_item in layout\_element.tabs:  \# These are gr.Tab items  
              \# gr.Tab is a BlockContext, so it has children  
              if hasattr(tab\_item, 'children'):  
                  for child\_in\_tab in tab\_item.children:  
                      found \= find\_component\_recursive(child\_in\_tab, elem\_id\_to\_find, label\_to\_find, component\_type\_to\_find)  
                      if found:  
                          return found  
      elif isinstance(layout\_element, gr.Accordion) and hasattr(layout\_element, 'children'): \# Accordion is also a Block  
           for child\_in\_accordion in layout\_element.children:  
              found \= find\_component\_recursive(child\_in\_accordion, elem\_id\_to\_find, label\_to\_find, component\_type\_to\_find)  
              if found:  
                  return found  
      return None

  \# Example usage (conceptual, actual elem\_id/label names need verification for Forge):  
  \# root\_block \= modules.shared.demo  
  \# prompt\_textbox \= find\_component\_recursive(root\_block, elem\_id\_to\_find="txt2img\_prompt")  
  \# if not prompt\_textbox:  
  \#     prompt\_textbox \= find\_component\_recursive(root\_block, label\_to\_find="Prompt", component\_type\_to\_find=gr.Textbox)

* **Component Identification**:  
  * **Using elem\_id**: This is the most reliable identification method if Forge assigns consistent and unique elem\_id attributes to its core UI components (e.g., txt2img\_prompt, txt2img\_steps\_slider, img2img\_cfg\_scale\_slider). AUTOMATIC1111's WebUI often uses elem\_ids such as txt2img\_prompt, txt2img\_negative\_prompt, txt2img\_width, txt2img\_height, txt2img\_sampling\_steps, txt2img\_sampling\_method, and txt2img\_cfg\_scale.6 An extension would maintain a list of these target elem\_ids. The stability of this approach is directly proportional to the consistency of elem\_id usage by Forge developers. If these identifiers are auto-generated or change frequently, this method's robustness diminishes.  
  * **Using label**: If elem\_ids are unavailable or unreliable, the component's visible label can be used as a fallback identifier. However, this method is susceptible to breakages if UI text is altered or if the application supports localization, as labels would change across languages.24  
  * **Using Component Type and Position**: Identifying a component based on its type (e.g., gr.Textbox) and its ordinal position within a known parent container (e.g., "the first gr.Textbox child of the gr.Row with elem\_id='txt2img\_prompt\_row') is extremely brittle and should only be considered as a last resort due to its high sensitivity to minor layout changes.  
* **Value Retrieval**: Once a reference to the Gradio component object is obtained, its current value can typically be accessed via its .value attribute.20

The consistent assignment of stable elem\_ids by the Forge developers is crucial. Without such identifiers, the process of locating the correct component becomes significantly more complex and less reliable, forcing a dependency on labels or structural heuristics which are inherently more fragile.

### **Method 2: Using Script.after\_component Hook (Targeted Reference Grabbing)**

The Script base class, part of modules/scripts.py in AUTOMATIC1111's WebUI and presumably a similar structure in Forge 21, offers an after\_component method. This hook is invoked by the WebUI framework immediately after each Gradio component is instantiated and added to the UI.

* **Mechanism**: An extension, by subclassing Script and overriding after\_component, can inspect each component as it's being created. The after\_component method receives the component instance itself and \*\*kwargs, which typically include the elem\_id and label of the component that was just processed.  
* The extension can then check if kwargs.get('elem\_id') matches a predefined list of elem\_ids corresponding to the core UI components it needs to access (e.g., 'txt2img\_prompt', 'txt2img\_steps\_slider'). If a match is found, the extension can store a direct reference to this component object (e.g., by assigning it to an instance variable like self.txt2img\_prompt\_component\_ref \= component).  
* Subsequently, within the extension's process() method (or any other method executed after the UI is built), the current value of the targeted core component can be accessed directly, for example, current\_prompt \= self.txt2img\_prompt\_component\_ref.value.  
  Python  
  \# Conceptual Python snippet using after\_component  
  from modules import scripts \# Assuming scripts.Script is available  
  import gradio as gr

  class StableQueueScript(scripts.Script):  
      def \_\_init\_\_(self):  
          super().\_\_init\_\_()  
          self.core\_ui\_references \= {}  
          \# Define elem\_ids of core UI components your extension needs to access  
          self.target\_core\_elem\_ids \= {  
              "txt2img\_prompt\_textbox": "txt2img\_prompt", \# Hypothetical elem\_id for prompt  
              "txt2img\_steps\_slider": "txt2img\_steps",    \# Hypothetical elem\_id for steps  
              "txt2img\_cfg\_scale\_slider": "txt2img\_cfg\_scale", \# Hypothetical elem\_id for CFG  
              \# Add other necessary elem\_ids for width, height, sampler, negative\_prompt, etc.  
          }

      def title(self):  
          return "StableQueue"

      def show(self, is\_img2img):  
          return scripts.AlwaysVisible \# Makes it an AlwaysOnScript

      def after\_component(self, component, \*\*kwargs):  
          elem\_id \= kwargs.get('elem\_id')  
          if elem\_id in self.target\_core\_elem\_ids.values():  
              \# Store a reference to the component, keyed by a logical name or its elem\_id  
              for key, id\_val in self.target\_core\_elem\_ids.items():  
                  if id\_val \== elem\_id:  
                      self.core\_ui\_references\[key\] \= component  
                      \# print(f" Captured reference to '{elem\_id}' as '{key}'") \# For debugging  
                      break

      def ui(self, is\_img2img):  
          \# Define StableQueue's own UI elements here (e.g., Queue button)  
          \# For this example, we'll just make a button that tries to print captured values  
          with gr.Blocks(): \# Use a local block for the script's own UI  
              btn\_capture\_test \= gr.Button("Test Capture Core UI (StableQueue)")

              \# This click handler demonstrates accessing the stored references  
              \# It would collect all inputs needed for the queue  
              \# The actual 'inputs' for this click should be the components themselves if we want their live values  
              \# However, for demonstration, we'll just access self.core\_ui\_references

              \# To pass the actual components to the fn, they must be in scope here.  
              \# This is where the challenge lies if after\_component is the \*only\* source.  
              \# A better approach for the button's click is to use the references gathered by after\_component.

          \# This is tricky: the click handler needs access to the components.  
          \# A common pattern is to pass component references to the click handler's 'inputs'.  
          \# However, self.core\_ui\_references is populated \*during\* UI build.  
          \# The click handler's 'inputs' list is defined \*before\* all components are built.

          \# A more robust way for the button's action:  
          \# The button's click function will directly use \`self.core\_ui\_references\`  
          \# which are populated by \`after\_component\`.

          \# Let's define a function that will be called on button click  
          def on\_capture\_test\_click():  
              captured\_values \= {}  
              for name, component\_ref in self.core\_ui\_references.items():  
                  if hasattr(component\_ref, 'value'):  
                      captured\_values\[name\] \= component\_ref.value  
                  else:  
                      captured\_values\[name\] \= f"Component {name} (elem\_id: {getattr(component\_ref, 'elem\_id', 'N/A')}) has no.value"  
              print(f" Test Capture Values: {captured\_values}")  
              return f"Captured: {captured\_values}" \# Can output to a Gradio component if desired

          output\_info \= gr.Textbox(label="Capture Test Output", interactive=False)  
          btn\_capture\_test.click(fn=on\_capture\_test\_click, inputs=None, outputs=\[output\_info\])

          return \[btn\_capture\_test, output\_info\] \# Return UI elements for this script

      def process(self, p, \*args):  
          \# This is the main processing hook.  
          \# args contains values from UI elements returned by this script's ui() method.  
          \# To capture main UI state when a queue button (defined in ui()) is clicked,  
          \# the click handler of that button should perform the capture using self.core\_ui\_references.

          \# Example: if StableQueue's "Add to Queue" button's click handler is 'add\_to\_queue\_fn'  
          \# 'add\_to\_queue\_fn' would look like:  
          \#   prompt\_val \= self.core\_ui\_references.get("txt2img\_prompt\_textbox").value  
          \#   steps\_val \= self.core\_ui\_references.get("txt2img\_steps\_slider").value  
          \#   \#... and so on  
          \#   \# Then, these values are stored in the queue.  
          pass  
  An example of using after\_component to grab a reference to the txt2img\_prompt can be found in discussions related to AUTOMATIC1111 WebUI extensions.30  
* **Advantages**: This method is more direct and potentially more performant than a full UI tree traversal if the elem\_ids of the target components are known and stable. It allows an extension to cleanly "hook into" the UI creation process and cherry-pick references to the components it cares about.  
* The use of elem\_ids in this manner effectively establishes them as part of an implicit contract between the core WebUI and its extensions. If Forge developers alter these elem\_ids, extensions relying on them for component identification will break. This highlights a dependency: either the elem\_ids must remain stable across Forge versions, or extensions need to implement fallback mechanisms or discovery routines for these identifiers themselves.

### **Method 3: Inspecting ui-config.json (Limited Utility for Live State)**

Stable Diffusion WebUI (and by extension, Forge) utilizes a ui-config.json file. This file stores user-defined customizations to the UI, such as default values for input fields, the range and step for sliders, and the visibility state of certain components.23 While ui-config.json can provide insights into the default configuration or structure of some UI elements, it does **not** reflect the live, current values entered by the user during an active session (e.g., the specific text a user has just typed into the prompt textbox). Therefore, it is not suitable for capturing the dynamic state of the UI required for queuing a generation job. Its utility is primarily for understanding default UI parameters or the names and structural properties of configurable elements.

### **Method 4: Using gr.Request (Generally Inapplicable for this process() Use Case)**

Gradio event handlers can be defined to accept a gr.Request object as an argument. This object encapsulates information about the HTTP request that triggered the event, including form data if the event originated from a form submission.35 However, the AlwaysOnScript.process() hook, which is central to the StableQueue extension's operation, is not a direct Gradio UI event callback in the same way as a button's .click() handler. Instead, process() is invoked as part of a larger backend processing pipeline. By the time process() is called, the relevant UI data has typically already been gathered by the WebUI framework and marshalled into the StableDiffusionProcessing object (p) or passed as \*args to the script's methods. Thus, relying on gr.Request within the process() hook is not an appropriate strategy for capturing the general state of the main txt2img or img2img UI.

## **4\. Capturing Parameters from AlwaysOnScript Extensions (e.g., ControlNet)**

A crucial requirement for StableQueue is to capture parameters not only from the core UI but also from other active AlwaysOnScript extensions, such as ControlNet, which contribute their own UI elements and significantly influence the generation process.

### **The p.script\_args Mechanism and ScriptRunner**

In the AUTOMATIC1111 and Forge architecture, AlwaysOnScripts (scripts that are persistently active and can add their own UI elements via their ui() method) have their UI component values collected by the system's ScriptRunner.21 These collected values are then passed as a flat tuple (denoted as \*args) to that specific script's process(self, p, \*args) and run(self, p, \*args) methods.  
More importantly for inter-extension communication, the StableDiffusionProcessing object (commonly referred to as p) contains an attribute p.script\_args. This attribute holds a single, concatenated tuple containing *all* arguments from *all* active AlwaysOnScripts. The arguments are ordered based on the load order or definition order of the scripts.37

### **Structure of p.script\_args and args\_from/args\_to**

To disentangle the parameters belonging to a specific script from the global p.script\_args tuple, each Script instance (accessible via p.scripts.alwayson\_scripts, which is a list of active script objects) possesses two vital integer attributes: args\_from and args\_to. These attributes define the start index (inclusive) and end index (exclusive) of that particular script's parameters within the p.script\_args tuple.  
Thus, for any given script\_instance obtained from iterating p.scripts.alwayson\_scripts, its specific set of UI argument values can be extracted as a slice: p.script\_args\[script\_instance.args\_from : script\_instance.args\_to\]. This slicing mechanism is fundamental for an extension like StableQueue to access the parameters of another extension like ControlNet.37

### **Identifying and Parsing a Specific Extension's Parameters**

To capture and correctly interpret the parameters of a specific AlwaysOnScript (e.g., ControlNet), the StableQueue extension must perform the following steps:

1. **Iterate p.scripts.alwayson\_scripts**: This list is an attribute of the StableDiffusionProcessing object p passed to the process() hook.  
2. **Identify the Target Script**: The target script can be identified by comparing its script.title().lower() against a known title (e.g., "controlnet") or by using isinstance(script, ExpectedScriptClassModule.ExpectedScriptClass) if the class type of the target extension is known.  
3. **Extract the Parameter Slice**: Once the target script\_instance is found, use its args\_from and args\_to attributes to retrieve its specific parameter slice from p.script\_args.  
4. **Parse the Slice**: The structure and meaning of the values within this extracted slice are defined entirely by the target extension's ui() method (i.e., the order and type of Gradio components it returns).  
   * **ControlNet Example**: ControlNet is a prominent example. Its slice of p.script\_args typically represents one or more ControlNetUnit objects (or a flattened representation of their attributes). Each ControlNetUnit encapsulates settings like whether the unit is enabled, the selected preprocessor module, the model, control weight, input image, mask, etc..37 Forge's own ControlNet integration likely follows a similar pattern, possibly using its own ControlNetUnit structure.41 The external\_code.ControlNetUnit class from Mikubill's widely used ControlNet extension serves as a common structural reference.42 StableQueue would need to be programmed with knowledge of this structure to correctly interpret ControlNet's parameters (e.g., knowing how many arguments constitute a single unit and what each argument signifies).

### **Generic Capture of All Extension Data**

For StableQueue to comprehensively store the state for a queued job, it should ideally capture parameters from *all* active AlwaysOnScripts. This can be achieved with the following logic:

Python

\# Conceptual Python snippet for capturing all AlwaysOnScript parameters  
\# Assume 'p' is the StableDiffusionProcessing object

all\_extension\_parameters \= {}  
if hasattr(p, 'scripts') and hasattr(p.scripts, 'alwayson\_scripts') and p.script\_args is not None:  
    for script\_object in p.scripts.alwayson\_scripts:  
        \# Ensure the script object has the necessary attributes  
        if hasattr(script\_object, 'title') and callable(script\_object.title) and \\  
           hasattr(script\_object, 'args\_from') and isinstance(script\_object.args\_from, int) and \\  
           hasattr(script\_object, 'args\_to') and isinstance(script\_object.args\_to, int):  
              
            script\_title\_str \= script\_object.title()  
            \# Ensure args\_from and args\_to are valid indices for p.script\_args  
            if 0 \<= script\_object.args\_from \<= script\_object.args\_to \<= len(p.script\_args):  
                args\_slice \= p.script\_args\[script\_object.args\_from:script\_object.args\_to\]  
                all\_extension\_parameters\[script\_title\_str\] \= args\_slice  
            else:  
                \# Log an error or handle invalid slice indices  
                print(f"Warning: Invalid args\_from/args\_to for script '{script\_title\_str}'")  
                all\_extension\_parameters\[script\_title\_str\] \= tuple() \# Store empty tuple or handle error  
        else:  
            \# Log or handle script objects missing necessary attributes  
            \# This might happen with non-standard script objects  
            pass   
\# 'all\_extension\_parameters' now holds a dictionary where keys are script titles  
\# and values are tuples of their respective raw arguments.

### **Illustrative Structure of p.script\_args**

The following table provides a conceptual illustration of how p.script\_args might be structured, consolidating arguments from multiple AlwaysOnScripts, and how args\_from/args\_to are used for delineation:

| Script Load Order | Script Title | args\_from | args\_to | Example Slice from p.script\_args (Conceptual) |
| :---- | :---- | :---- | :---- | :---- |
| 1 | "ControlNet" | 0 | 12 | (True, \<img\_data\_cn1\_dict\>, 'canny', 'control\_canny\_model\_v11p\_sd15 \[safetensors\]', 1.0, 'Balanced',..., False, None, 'depth', 'control\_depth\_model\_v11p\_sd15 \[safetensors\]', 0.5, 'Balanced',...) (assuming 2 active units, each contributing multiple arguments like enabled, image, module, model, weight, guidance\_balance) |
| 2 | "StableQueue (Self)" | 12 | 15 | ('High Priority', True, 5\) (example arguments from StableQueue's own UI, e.g., queue priority, enable\_feature\_X, numeric\_setting\_Y) |
| 3 | "Dynamic Prompts" | 15 | 17 | \`(True, 'A {cat |

This table is crucial for visualizing p.script\_args as a consolidated list. It demonstrates the ordered concatenation of arguments, the indispensable role of args\_from and args\_to in demarcating each script's contribution, and the script-specific internal structure of each slice. This clarifies how to isolate and subsequently parse parameters for specific extensions that StableQueue aims to support.  
A significant consideration arises from this: StableQueue, by attempting to capture and reapply parameters for other extensions like ControlNet, establishes a form of inter-extension dependency. If ControlNet (or any other targeted extension) modifies its UI in a way that changes the number, order, or meaning of arguments it contributes to p.script\_args, StableQueue's parsing logic for that extension's slice will require corresponding updates. This presents a version compatibility challenge, not just with Forge itself, but also between extensions.  
Furthermore, when observing the WebUI's API (e.g., for /sdapi/v1/txt2img), parameters for AlwaysOnScripts are frequently structured within a JSON object, typically under an alwayson\_scripts key. This object often maps script titles (or unique API identifiers for scripts) to their respective arguments, for example, {"ControlNet": {"args": \[...\]}}.50 This dictionary-like structure is inherently more robust for API communication than a flat list, as it's not dependent on the absolute order of script loading. While p.script\_args remains a flat tuple during internal Python execution within the WebUI, if StableQueue needs to store these captured parameters (e.g., in its internal queue data structure), adopting a similar dictionary format (keyed by script title, with values being the argument tuples) would be a prudent design choice. This makes the stored data more manageable and aligns with established API patterns, even if it requires flattening back into the p.script\_args format when a queued job is eventually processed.

## **5\. Alternative Gradio Integration and Runtime UI Discovery (Consolidated)**

To achieve version-agnostic parameter capture, extensions must dynamically understand the UI's current layout rather than assuming fixed structures. This section consolidates strategies for such runtime discovery and integration with Gradio.

### **Gradio Native Parameter Access**

The most direct and "Gradio-native" method by which backend Python functions receive values from UI components is through the inputs list specified in an event listener's definition. For example, gr.Button(...).click(fn=my\_callback, inputs=\[ui\_component1, ui\_component2\],...) will pass the current values of ui\_component1 and ui\_component2 to my\_callback. For an AlwaysOnScript, the values from its own UI elements (defined in its ui() method) are automatically passed as \*args to its process() or run() methods.21 The primary challenge this report addresses is accessing UI elements that are *external* to the script's own UI definition, such as the main txt2img prompt or components from other extensions.

### **Runtime UI Mapping (Central Strategy)**

The cornerstone of a version-agnostic approach is to perform runtime mapping of the UI. This involves conducting a scan of the entire Gradio UI tree upon script initialization (e.g., within the Script.setup() method, which is called once when the processing object is set up, or during the first invocation of Script.process()) to locate and cache references or unique identifiers (like elem\_id) to all essential UI components.

* **Implementation Steps**:  
  1. **Obtain Root Access**: Secure a reference to the root gr.Blocks() instance of the application. This is often exposed as modules.shared.demo.  
  2. **Recursive Traversal**: Implement a function to recursively navigate the children attribute of layout blocks (e.g., gr.Row, gr.Column) and specialized containers like gr.Tabs (which have a tabs attribute containing gr.Tab objects, themselves being BlockContext with children) and gr.Accordion items.  
  3. **Component Identification**: Within the traversal, identify target components using a prioritized strategy:  
     * **Exact elem\_id Match**: This is the most preferred method if target components have stable, known elem\_ids.  
     * **label Match**: Use as a fallback. This requires caution due to potential UI text changes and the impact of localization. It's often necessary to combine a label match with a type check (e.g., find a gr.Textbox with label="Prompt").  
     * **Component Type within an Identified Parent**: As a less robust fallback, look for a component of a specific type (e.g., gr.Slider) within a uniquely identifiable parent container (e.g., a gr.Tab or gr.Row that itself was found by elem\_id or a unique label).  
  4. **Cache References/Identifiers**: Store the located component objects or, more robustly, their elem\_id strings in a dictionary within your script's instance (e.g., self.ui\_component\_map \= {'txt2img\_prompt\_elem\_id': "txt2img\_prompt\_actual\_id",...}).  
  5. **Value Retrieval**: When parameters need to be captured (e.g., in the process() method when StableQueue is triggered to add a new job to its queue), iterate this map. For each entry, resolve the elem\_id back to a component instance (if elem\_ids were stored) and then retrieve its current .value.  
* **Handling Dynamic UI Sections (e.g., ControlNet Units)**: Extensions like ControlNet can dynamically add or remove UI units, often managed within gr.Accordion or gr.Tabs structures for each unit.41 The UI traversal logic must be sophisticated enough to identify all currently active units and their respective child components (e.g., enabled checkbox, model dropdown, weight slider for each ControlNet unit). This might involve searching for repeated elem\_id patterns (e.g., controlnet\_unit\_0\_model, controlnet\_unit\_1\_model) or identifying parent blocks associated with each unit.

A refined approach to managing these discovered components involves creating a "UI Element Handle" abstraction. Instead of directly storing the live Gradio component objects in the cache or queue (which could lead to issues with Python's pickling mechanism if queue items are serialized, or result in stale references if Gradio internally recreates components), the mapping process should primarily store the elem\_id (a string, which is easily serializable) of each target component. Then, a helper function within the extension can be responsible for resolving this elem\_id back to a live component instance by traversing the current shared.demo tree at the precise moment the value is needed. This decouples the stored representation of the UI target from the live Gradio objects. For instance, the UI map might store {'txt2img\_prompt\_ref': "actual\_txt2img\_prompt\_elem\_id"}. When capturing parameters, the extension would call an internal get\_component\_value\_by\_elem\_id("actual\_txt2img\_prompt\_elem\_id"), which in turn finds the component in shared.demo and returns its .value. This makes the data stored for queued items lighter and potentially more resilient to internal Gradio UI updates, provided the elem\_ids and the shared.demo instance remain consistently accessible.

## **6\. Creating StableDiffusionProcessing Objects and Triggering process()**

The StableDiffusionProcessing object, conventionally aliased as p, is the central data structure in the AUTOMATIC1111/Forge image generation pipeline. It encapsulates all parameters and state information for a single generation task. This includes the prompt, negative prompt, generation steps, CFG scale, seed, sampler name, image dimensions (width and height), and, critically for extension compatibility, the script\_args tuple and a reference to the scripts runner object that manages AlwaysOnScripts.54 The AlwaysOnScript.process(self, p, \*args) hook, which is fundamental to StableQueue's operation, receives an already populated p object pertinent to the ongoing generation task.

### **Populating p for Queued Jobs by StableQueue**

When the user interacts with StableQueue's UI to add a new job (e.g., by clicking an "Add to Queue" button), the extension's event handler for that action must meticulously construct a new StableDiffusionProcessing object that accurately reflects the entire UI state at that moment. This involves several steps:

1. **Instantiate p**: A new StableDiffusionProcessing object must be created. It is generally safer and cleaner to instantiate a new object for each queued job rather than attempting to clone an existing p object, which might carry unintended state or references. The most robust method for creating a correctly initialized p object is to leverage Forge's own internal factory functions if they are accessible. For example, Forge contains functions like txt2img\_create\_processing (referenced in profile logs of txt2img.py 22), which are responsible for creating and populating p based on the arguments received from the UI. If StableQueue can gather all the necessary raw arguments (from both the core UI and all active scripts) in the precise order and format expected by such a factory function, invoking it programmatically would yield a perfectly configured p object. This approach delegates the complexities of p's initialization (e.g., setting up p.sd\_model, p.sampler\_name, p.scripts runner) to Forge's own maintained code, making the extension more resilient to changes in the StableDiffusionProcessing class structure or initialization logic.  
2. **Populate Core Parameters**: Using the dynamic UI discovery methods detailed in Sections 3 and 5, the extension must fetch the current values for all core generation parameters: prompt, negative prompt, steps, CFG scale, width, height, sampler name, seed, etc. These captured values are then assigned to the corresponding attributes of the newly created p object (e.g., new\_p.prompt \= captured\_prompt\_value, new\_p.steps \= captured\_steps\_value).  
3. **Populate Script Parameters (p.script\_args, p.scripts)**: This is a critical step for ensuring that other AlwaysOnScripts (like ControlNet) behave correctly when the queued job is processed.  
   * The extension needs to iterate through all currently active AlwaysOnScripts. These can typically be found in a list like shared.scripts\_data (which often holds metadata about loaded scripts including their UI component creation functions) or by inspecting the p.scripts.alwayson\_scripts list of the *current* generation's p object if the queuing action happens in a context where one is available (though for a fresh queue action, iterating a global list of scripts might be more appropriate).  
   * For each active script, its UI values must be captured. This involves understanding the order and type of components returned by its ui() method, or by implementing specific parsing logic for known, critical extensions like ControlNet (as detailed in Section 4).  
   * These captured values from all scripts must be assembled into a single, flat tuple in the correct order, which will then be assigned to new\_p.script\_args.  
   * It's also essential to ensure that new\_p.scripts (the ScriptRunner instance associated with new\_p) is correctly initialized. This runner needs to be aware of all relevant AlwaysOnScript instances, and these script instances within new\_p.scripts.alwayson\_scripts must have their args\_from and args\_to attributes correctly set to point to their respective slices within new\_p.script\_args. If a Forge internal function like txt2img\_create\_processing is used to create new\_p, it is likely to handle the correct setup of new\_p.scripts and the associated args\_from/args\_to indices automatically.

When considering how StableQueue should internally store the captured parameters for each extension before they are potentially flattened into new\_p.script\_args at processing time, the JSON structure used for alwayson\_scripts in WebUI API calls provides a useful model.50 This structure typically involves a dictionary where keys are script names (or unique identifiers) and values are objects or lists representing their arguments (e.g., {"ControlNet": {"args": \[...\]}}). Adopting a similar dictionary-based representation within StableQueue for storing extension parameters would make the queued data more organized and less susceptible to errors arising from shifts in script loading order compared to managing a complex flat list directly.

### **Interacting with the process() Hook**

The user query specifies that the StableQueue extension must operate in conjunction with the AlwaysOnScript.process() hook. This implies that when StableQueue eventually decides to execute a job from its internal queue, it will do so by invoking a standard generation function, such as modules.processing.process\_images(p\_from\_queue), where p\_from\_queue is the meticulously constructed StableDiffusionProcessing object for that queued task.  
This invocation will, in turn, trigger the process() method of all registered AlwaysOnScripts, including StableQueue itself and others like ControlNet. Each of these scripts will receive p\_from\_queue as their processing context. Consequently, StableQueue's own process() method needs to be designed with awareness of this re-entrancy. If its process() method is called as part of processing one of *its own* queued items, it should likely perform minimal work related to queue management or simply allow the generation to proceed, rather than attempting to re-capture UI state or re-queue the item. A flag or state variable within p\_from\_queue or the StableQueue instance itself could be used to indicate that the current processing task originated from the queue.

## **7\. Fallback Methods and Best Practices**

To build a truly resilient Forge extension capable of adapting to UI changes across different versions, a multi-layered approach to component discovery, coupled with robust error handling and best practices, is essential.

### **Prioritized Discovery Strategy for UI Components**

When attempting to locate core UI components or elements from other extensions, a prioritized strategy should be employed:

1. **elem\_id Identification**:  
   * **Via after\_component Hook**: For components with known and historically stable elem\_ids, using the Script.after\_component hook to capture direct references during UI construction is efficient and clean.  
   * **Via Runtime Traversal**: If elem\_ids are not captured via the hook (e.g., for components from other extensions or if elem\_ids are less stable), perform a runtime traversal of the shared.demo Gradio tree, searching for components matching target elem\_ids. These target elem\_ids might be predefined based on common A1111/Forge patterns or discovered through heuristic analysis of component labels and types.  
2. **label Identification (Fallback)**: If elem\_id-based searches fail or are not applicable (e.g., elem\_ids are dynamic or missing), attempt to locate components by their label string during UI traversal. This method is less robust due to potential UI text modifications by users, Forge updates, or localization. A label search should ideally be combined with a component type check (e.g., find gr.Textbox with label="Prompt").  
3. **Component Type and Relative Position (Last Resort)**: As a final fallback, identify components based on their Gradio type (e.g., gr.Slider, gr.Dropdown) and their relative position within a known parent container (e.g., a gr.Tab or gr.Row that was itself identified by a more stable elem\_id or unique label). This approach is highly susceptible to breakage from minor layout adjustments and should be used sparingly and with extensive commenting.

### **Graceful Degradation and Error Handling**

* **Missing Components**: If a critical UI component (e.g., the main prompt textbox) cannot be found using any of the above methods, the extension should log a detailed error message specifying which component is missing and why it's needed.  
* **Default Values/Disabled Functionality**: Instead of crashing, if a non-critical parameter cannot be captured, the extension could attempt to proceed with a sensible default value or, if necessary, disable the specific feature of the extension that relies on the missing parameter.  
* **User Feedback**: Provide clear feedback to the user, either via the UI (e.g., a status message in the extension's accordion) or the console, if some parameters could not be captured, potentially impacting the fidelity of queued jobs.

### **Comprehensive Logging for UI Discovery**

Implement verbose logging, especially during the UI traversal and component mapping phase. This logging should be conditional (e.g., enabled by a debug flag in the extension's settings).

* Log the elem\_id, label, Gradio type, and (if applicable and safe) the current value of discovered components.  
* When a targeted component is not found, log the identifiers that were attempted.  
* This detailed logging is invaluable for developers when diagnosing why the extension might be failing to capture parameters after a Forge update.  
* Consider an optional "debug mode" for the extension that prints all captured parameters (core UI and all script arguments) before they are stored in the queue or used to initiate a generation.

### **User Configuration for Key Identifiers**

For UI elements or script argument structures that prove to be particularly volatile or vary significantly across Forge forks or custom user setups, consider providing an advanced configuration section within the StableQueue extension's settings. Here, users could manually specify the elem\_ids for certain core components or provide hints about the structure of arguments for specific, problematic third-party extensions. This offers a manual override path if automatic discovery fails.

### **Adherence to User Requirements**

The developed solution must strictly adhere to the constraints specified in the initial query:

* The core logic for parameter capture and queue processing should integrate with the AlwaysOnScript.process() hook.  
* Artificial button triggering (programmatically clicking the main "Generate" button) is not an acceptable solution and must be avoided. The focus is on direct, backend state capture and programmatic invocation of the generation pipeline.

### **Self-Diagnostic Capability**

An advanced best practice for enhancing robustness and maintainability is to incorporate a "compatibility check" or "UI diagnostic" feature within the StableQueue extension.

* This feature, runnable on startup or on user demand (e.g., via a button in the extension's settings), would proactively attempt to locate all critical UI elements (both core Forge components and key elements from important extensions like ControlNet) using its configured discovery strategies.  
* It would then report its success or failure for each targeted element, potentially highlighting which elem\_ids it couldn't find or which script argument structures appear unexpected based on its parsing rules.  
* Such a diagnostic tool can provide immediate feedback to the user or developer about potential compatibility issues with the current Forge version or other installed extensions. It could even suggest potential new elem\_ids if it finds components with similar labels or types in expected locations, thereby aiding in the adaptation process after a Forge update. This proactive approach can significantly reduce debugging time and improve the user's ability to resolve compatibility problems.

## **8\. Conclusions and Actionable Recommendations**

The challenge of reliably capturing UI parameters in a Stable Diffusion Forge extension, particularly when faced with the absence of previously available internal aggregations like modules.ui.txt2img\_inputs, necessitates a shift towards more dynamic and resilient techniques. Relying on hardcoded paths to internal module variables is inherently fragile in an actively developed ecosystem.  
**Summary of Robust Techniques:**  
The investigation has identified several robust strategies:

1. **Runtime UI Traversal with Prioritized Identifiers**: Programmatically navigating the Gradio Blocks tree (e.g., starting from shared.demo) is the most fundamental approach. Components should be identified using a priority system:  
   * **elem\_id**: The most reliable, whether captured via Script.after\_component hooks for known elements or found during traversal.  
   * **label**: A viable fallback, used cautiously due to potential changes and localization.  
   * **Component Type/Position**: A last resort for ambiguous cases.  
2. **Systematic Parsing of p.script\_args**: For capturing parameters from AlwaysOnScript extensions (including critical ones like ControlNet and the StableQueue extension itself), iterating p.scripts.alwayson\_scripts and using each script's args\_from and args\_to attributes to slice p.script\_args is the standard mechanism. This requires script-specific knowledge to parse the content of each slice correctly.  
3. **Dynamic UI Map**: Building a map (e.g., a dictionary) of references or elem\_ids to essential UI components during script initialization (e.g., in setup()) allows for efficient and centralized access to these components' values later in the process() hook or other event handlers.  
4. **Leveraging Forge's Internal StableDiffusionProcessing Creation**: When creating StableDiffusionProcessing objects for queued jobs, the most robust method is to utilize Forge's own internal factory functions (e.g., txt2img\_create\_processing) if they can be programmatically invoked with the full set of captured UI arguments. This delegates the complex task of correctly initializing the p object.

**Key Recommendation:**  
The central recommendation is to **transition away from dependencies on specific module-level variables** (like modules.ui.txt2img\_inputs) for UI component access. Instead, extensions should implement **dynamic, runtime discovery and mapping of Gradio components**. This involves directly interacting with the Gradio Blocks structure and the ScriptRunner mechanisms.  
**Future-Proofing and Maintenance:**  
While these dynamic methods significantly enhance robustness against version changes, no solution can be entirely immune to major architectural shifts in Forge. Therefore:

* **Vigilance with Forge Updates**: Developers of extensions like StableQueue must remain vigilant. After significant Forge updates, it is prudent to test the extension's parameter capture logic.  
* **Adaptable Discovery Logic**: The UI discovery and mapping logic within the extension should be designed to be as adaptable as possible. Clear logging and potential user-configurable overrides for key elem\_ids can aid in maintenance.  
* **Community Engagement**: Monitoring Forge development discussions and community forums can provide early warnings about upcoming changes that might impact UI structure or script argument handling.

**Call to Action:**  
For the StableQueue extension, the immediate path forward involves refactoring its parameter capture system to:

1. Implement runtime UI traversal (starting from shared.demo or similar root) to locate core txt2img/img2img components, prioritizing elem\_id identification and falling back to labels if necessary. The Script.after\_component hook can be a valuable tool for grabbing references to components with known elem\_ids during UI setup.  
2. Develop robust parsing for p.script\_args by iterating p.scripts.alwayson\_scripts and using args\_from/args\_to to extract parameters for each active script. This will require specific parsing logic for ControlNet and any other critical extensions StableQueue aims to fully support.  
3. Construct StableDiffusionProcessing objects for queued jobs by first capturing all core and script parameters using the above methods, and then, ideally, passing these to a Forge internal factory function (like txt2img\_create\_processing) to ensure complete and correct initialization.  
4. Incorporate comprehensive error logging and consider a self-diagnostic feature to aid in troubleshooting compatibility issues with new Forge versions.

By adopting these strategies, the StableQueue extension can achieve a higher degree of version compatibility, providing a more stable and reliable experience for its users within the evolving Stable Diffusion Forge ecosystem.

#### **Works cited**

1. caojiachen1/stable-diffusion-webui-forge \- Gitee, accessed June 2, 2025, [https://gitee.com/hqsrawmelon/stable-diffusion-webui-forge](https://gitee.com/hqsrawmelon/stable-diffusion-webui-forge)  
2. lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge](https://github.com/lllyasviel/stable-diffusion-webui-forge)  
3. README.md \- Haoming02/sd-webui-forge-classic \- GitHub, accessed June 2, 2025, [https://github.com/Haoming02/sd-webui-forge-classic/blob/classic/README.md](https://github.com/Haoming02/sd-webui-forge-classic/blob/classic/README.md)  
4. What is WebUI Forge? \- MimicPC, accessed June 2, 2025, [https://www.mimicpc.com/learn/what-is-webui-forge](https://www.mimicpc.com/learn/what-is-webui-forge)  
5. Forge UI: The Superior Alternative to Automatic1111 Stable Diffusion \- Toolify.ai, accessed June 2, 2025, [https://www.toolify.ai/ai-news/forge-ui-the-superior-alternative-to-automatic1111-stable-diffusion-3302220](https://www.toolify.ai/ai-news/forge-ui-the-superior-alternative-to-automatic1111-stable-diffusion-3302220)  
6. Blocks And Event Listeners \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/blocks-and-event-listeners](https://www.gradio.app/guides/blocks-and-event-listeners)  
7. Controlling Layout \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/controlling-layout](https://www.gradio.app/guides/controlling-layout)  
8. launch.py \- lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/launch.py](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/launch.py)  
9. stable-diffusion-webui-forge/modules/initialize.py at main \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/initialize.py](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/initialize.py)  
10. stable-diffusion-webui-forge/webui.bat at main \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/webui.bat](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/webui.bat)  
11. stable-diffusion-webui-forge/modules/cmd\_args.py at main \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/cmd\_args.py](https://github.com/lllyasviel/stable-diffusion-webui-forge/blob/main/modules/cmd_args.py)  
12. Forge Ui txt2img+canny : not well defined/ non consistent results : r/StableDiffusion \- Reddit, accessed June 3, 2025, [https://www.reddit.com/r/StableDiffusion/comments/1klg0of/forge\_ui\_txt2imgcanny\_not\_well\_defined\_non/](https://www.reddit.com/r/StableDiffusion/comments/1klg0of/forge_ui_txt2imgcanny_not_well_defined_non/)  
13. Stable (Forge) Returning Blank Images : r/StableDiffusion \- Reddit, accessed June 3, 2025, [https://www.reddit.com/r/StableDiffusion/comments/1kkp54k/stable\_forge\_returning\_blank\_images/](https://www.reddit.com/r/StableDiffusion/comments/1kkp54k/stable_forge_returning_blank_images/)  
14. Stable Diffusion IMG2IMG: EVERYTHING you need to know IN ONE PLACE\! \- YouTube, accessed June 3, 2025, [https://www.youtube.com/watch?v=inW3l-DpA7U](https://www.youtube.com/watch?v=inW3l-DpA7U)  
15. Installing Stable Diffusion Forge \- YouTube, accessed June 3, 2025, [https://www.youtube.com/watch?v=cinGiiNvL7A](https://www.youtube.com/watch?v=cinGiiNvL7A)  
16. Support for Multi-Diffusion Upscaler · Issue \#672 · lllyasviel/stable-diffusion-webui-forge, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/672](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/672)  
17. Calling the API /sdapi/v1/txt2img for text-to-image · Issue \#1151 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/1151](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/1151)  
18. \[Bug\]: Fix IMG2IMG Alternative Test Script to Work with SDXL · Issue \#589 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/589](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/589)  
19. TypeError: 'NoneType' object is not iterable ... and other things · Issue \#181 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/181](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/181)  
20. Gradio Components: The Key Concepts, accessed June 2, 2025, [https://www.gradio.app/guides/key-component-concepts](https://www.gradio.app/guides/key-component-concepts)  
21. scripts.py \- AUTOMATIC1111/stable-diffusion-webui \- GitHub, accessed June 3, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/modules/scripts.py](https://github.com/AUTOMATIC1111/stable-diffusion-webui/blob/master/modules/scripts.py)  
22. Performance Profiling Report (Forge/A1111/ComfyUI) · lllyasviel stable-diffusion-webui-forge · Discussion \#716 \- GitHub, accessed June 3, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/716](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/716)  
23. User Interface Customizations · AUTOMATIC1111/stable-diffusion-webui Wiki \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/User-Interface-Customizations](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/User-Interface-Customizations)  
24. The Interface Class \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/the-interface-class](https://www.gradio.app/guides/the-interface-class)  
25. Install and Use Flux in Forge: A Comprehensive Guide \- Toolify.ai, accessed June 2, 2025, [https://www.toolify.ai/ai-news/install-and-use-flux-in-forge-a-comprehensive-guide-3372237](https://www.toolify.ai/ai-news/install-and-use-flux-in-forge-a-comprehensive-guide-3372237)  
26. Introduction to Gradio for Building Interactive Applications \- PyImageSearch, accessed June 3, 2025, [https://pyimagesearch.com/2025/02/03/introduction-to-gradio-for-building-interactive-applications/](https://pyimagesearch.com/2025/02/03/introduction-to-gradio-for-building-interactive-applications/)  
27. How can I find a compent by elem\_id? · Issue \#5882 · gradio-app/gradio \- GitHub, accessed June 3, 2025, [https://github.com/gradio-app/gradio/issues/5882](https://github.com/gradio-app/gradio/issues/5882)  
28. update supports updating the elem\_id or elem\_classes of a component · Issue \#4590 · gradio-app/gradio \- GitHub, accessed June 3, 2025, [https://github.com/gradio-app/gradio/issues/4590](https://github.com/gradio-app/gradio/issues/4590)  
29. GradioDeprecationWarning · Issue \#259 · s0md3v/sd-webui-roop \- GitHub, accessed June 3, 2025, [https://github.com/s0md3v/sd-webui-roop/issues/259](https://github.com/s0md3v/sd-webui-roop/issues/259)  
30. \[Newby Script question\] How do I insert values into several entry fields at once when a button is clicked? · AUTOMATIC1111 stable-diffusion-webui · Discussion \#9495 \- GitHub, accessed June 3, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/9495](https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/9495)  
31. Stable Diffusion webUI, accessed June 3, 2025, [https://profaneservitor.github.io/sdwui-docs/](https://profaneservitor.github.io/sdwui-docs/)  
32. Dynamic Apps With Render Decorator \- Gradio, accessed June 3, 2025, [https://www.gradio.app/guides/dynamic-apps-with-render-decorator](https://www.gradio.app/guides/dynamic-apps-with-render-decorator)  
33. How to toggle visibility of a Gradio component based on radio button? \- Stack Overflow, accessed June 3, 2025, [https://stackoverflow.com/questions/77976715/how-to-toggle-visibility-of-a-gradio-component-based-on-radio-button](https://stackoverflow.com/questions/77976715/how-to-toggle-visibility-of-a-gradio-component-based-on-radio-button)  
34. Backend \- Gradio, accessed June 2, 2025, [https://www.gradio.app/guides/backend](https://www.gradio.app/guides/backend)  
35. Request \- Gradio Docs, accessed June 3, 2025, [https://www.gradio.app/docs/gradio/request](https://www.gradio.app/docs/gradio/request)  
36. File \- Gradio Docs, accessed June 3, 2025, [https://www.gradio.app/docs/gradio/file](https://www.gradio.app/docs/gradio/file)  
37. Controlling CN from within another script? · Issue \#444 · Mikubill/sd-webui-controlnet, accessed June 3, 2025, [https://github.com/Mikubill/sd-webui-controlnet/issues/444](https://github.com/Mikubill/sd-webui-controlnet/issues/444)  
38. \[Vlad/Deforum\] If you have problems with Vlad/Deforum · Issue \#1027 · Mikubill/sd-webui-controlnet \- GitHub, accessed June 3, 2025, [https://github.com/Mikubill/sd-webui-controlnet/issues/1027](https://github.com/Mikubill/sd-webui-controlnet/issues/1027)  
39. API: Script order on \`alwayson\_scripts\` matters · AUTOMATIC1111 stable-diffusion-webui · Discussion \#8885 \- GitHub, accessed June 3, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/8885](https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/8885)  
40. How do I use scripts on AUTOMATIC1111 Webui ? : r/StableDiffusion \- Reddit, accessed June 3, 2025, [https://www.reddit.com/r/StableDiffusion/comments/y7xwtl/how\_do\_i\_use\_scripts\_on\_automatic1111\_webui/](https://www.reddit.com/r/StableDiffusion/comments/y7xwtl/how_do_i_use_scripts_on_automatic1111_webui/)  
41. Mikubill/sd-webui-controlnet: WebUI extension for ControlNet \- GitHub, accessed June 2, 2025, [https://github.com/Mikubill/sd-webui-controlnet](https://github.com/Mikubill/sd-webui-controlnet)  
42. sd-webui-controlnet/scripts/controlnet.py at main \- GitHub, accessed June 2, 2025, [https://github.com/Mikubill/sd-webui-controlnet/blob/main/scripts/controlnet.py](https://github.com/Mikubill/sd-webui-controlnet/blob/main/scripts/controlnet.py)  
43. High-Similarity Face Swapping: Leveraging IP-Adapter and Instant-ID for Enhanced Results, accessed June 2, 2025, [https://myaiforce.com/face-swap-with-ipadapter-and-instantid/](https://myaiforce.com/face-swap-with-ipadapter-and-instantid/)  
44. Stable Diffusion Webui ControlNet \- La Vivien Post, accessed June 2, 2025, [https://www.lavivienpost.com/stable-diffusion-webui-controlnet/](https://www.lavivienpost.com/stable-diffusion-webui-controlnet/)  
45. A Comprehensive Guide to Using Stable Diffusion Forge UI | Video Summary by LunaNotes, accessed June 2, 2025, [https://lunanotes.io/summary/a-comprehensive-guide-to-using-stable-diffusion-forge-ui](https://lunanotes.io/summary/a-comprehensive-guide-to-using-stable-diffusion-forge-ui)  
46. ControlNet Stable Diffusion UPDATED FULL Tutorial \- YouTube, accessed June 2, 2025, [https://m.youtube.com/watch?v=mmZSOBSg2E4\&pp=ygUJI2FpZ2VuaW1n](https://m.youtube.com/watch?v=mmZSOBSg2E4&pp=ygUJI2FpZ2VuaW1n)  
47. Controlnet Stable Diffusion Tutorial In 8 Minutes (Automatic1111) \- YouTube, accessed June 2, 2025, [https://m.youtube.com/watch?v=DWvcLggvWcQ](https://m.youtube.com/watch?v=DWvcLggvWcQ)  
48. Thank you sd-webui-controlnet team\! : r/StableDiffusion \- Reddit, accessed June 2, 2025, [https://www.reddit.com/r/StableDiffusion/comments/18wa7tv/thank\_you\_sdwebuicontrolnet\_team/](https://www.reddit.com/r/StableDiffusion/comments/18wa7tv/thank_you_sdwebuicontrolnet_team/)  
49. anapnoe/stable-diffusion-webui-ux-forge \- GitHub, accessed June 2, 2025, [https://github.com/anapnoe/stable-diffusion-webui-ux-forge](https://github.com/anapnoe/stable-diffusion-webui-ux-forge)  
50. Guide to txt2img API | Automatic1111 \- Random Bits Software Engineering, accessed June 3, 2025, [https://randombits.dev/articles/stable-diffusion/txt2img](https://randombits.dev/articles/stable-diffusion/txt2img)  
51. Stable Diffusion API: \`sdapi/v1/txt2img\` \- HackMD, accessed June 3, 2025, [https://hackmd.io/@qK90-toKQ9SPvHQxXwxWFg/HkfCwzod2](https://hackmd.io/@qK90-toKQ9SPvHQxXwxWFg/HkfCwzod2)  
52. Automatic1111 Stable Diffusion Web API: FAQ \- Generative Labs, accessed June 3, 2025, [https://www.generativelabs.co/post/automatic1111-stable-diffusion-web-api-overview](https://www.generativelabs.co/post/automatic1111-stable-diffusion-web-api-overview)  
53. How to properly set the settings of the Reactor face swapping extension for Stable Diffusion through a POST api call? \- Stack Overflow, accessed June 3, 2025, [https://stackoverflow.com/questions/77660340/how-to-properly-set-the-settings-of-the-reactor-face-swapping-extension-for-stab](https://stackoverflow.com/questions/77660340/how-to-properly-set-the-settings-of-the-reactor-face-swapping-extension-for-stab)  
54. Getting errors with using any lora on sdxl models · Issue \#2846 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2846](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2846)  
55. Flux cannot use Lora · Issue \#2625 · lllyasviel/stable-diffusion-webui-forge \- GitHub, accessed June 2, 2025, [https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2625](https://github.com/lllyasviel/stable-diffusion-webui-forge/issues/2625)  
56. Stable Diffusion Explained with Visualization \- Polo Club of Data Science, accessed June 2, 2025, [https://poloclub.github.io/diffusion-explainer/](https://poloclub.github.io/diffusion-explainer/)  
57. Saving text file with generation parameters \*before\* generation · AUTOMATIC1111 stable-diffusion-webui · Discussion \#14542 \- GitHub, accessed June 2, 2025, [https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/14542](https://github.com/AUTOMATIC1111/stable-diffusion-webui/discussions/14542)  
58. Automatic1111, but a python package : r/StableDiffusion \- Reddit, accessed June 2, 2025, [https://www.reddit.com/r/StableDiffusion/comments/1af90fz/automatic1111\_but\_a\_python\_package/](https://www.reddit.com/r/StableDiffusion/comments/1af90fz/automatic1111_but_a_python_package/)  
59. AUTOMATIC1111: Complete Guide to Stable Diffusion WebUI \- Weam AI, accessed June 2, 2025, [https://weam.ai/blog/guide/stable-diffusion/automatic1111-stable-diffusion-webui-guide/](https://weam.ai/blog/guide/stable-diffusion/automatic1111-stable-diffusion-webui-guide/)  
60. Platform For AI:Use Stable Diffusion web UI to deploy an AI painting service \- Alibaba Cloud, accessed June 2, 2025, [https://www.alibabacloud.com/help/en/pai/user-guide/ai-painting-sdwebui-deployment](https://www.alibabacloud.com/help/en/pai/user-guide/ai-painting-sdwebui-deployment)  
61. Stable Diffusion WebUI AUTOMATIC1111: A Beginner's Guide, accessed June 2, 2025, [https://stable-diffusion-art.com/automatic1111/](https://stable-diffusion-art.com/automatic1111/)  
62. AI Deploy \- Tutorial \- Deploy Stable Diffusion WebUI \- OVHcloud, accessed June 2, 2025, [https://help.ovhcloud.com/csm/es-public-cloud-ai-deploy-stable-diffusion-webui?id=kb\_article\_view\&sysparm\_article=KB0061159](https://help.ovhcloud.com/csm/es-public-cloud-ai-deploy-stable-diffusion-webui?id=kb_article_view&sysparm_article=KB0061159)