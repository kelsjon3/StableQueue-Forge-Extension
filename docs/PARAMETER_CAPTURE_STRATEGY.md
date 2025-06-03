# StableQueue Parameter Capture Strategy Documentation

**Created:** 2024-12-19  
**Purpose:** Definitive guide to prevent getting lost in the "corn maze" of parameter capture approaches

---

## Research Foundation

Based on comprehensive research document: "Programmatic Parameter Extraction from Stable Diffusion Forge WebUI Extensions"

### Key Research Findings

**✅ Recommended Approach: AlwaysOnScript with StableDiffusionProcessing Object Interception**

> "The most idiomatic and generally robust approach is to design the capturing extension as an AlwaysOnScript. The WebUI's scripting system provides several lifecycle methods that scripts can implement. The process(self, p, *args) or before_process(self, p, *args) methods are particularly suitable"

> "At the point these methods are called, p represents the complete state that Forge is about to use for image generation. This is the ideal juncture for interception."

**Why This Works:**
- `process()` hook receives complete `StableDiffusionProcessing` object (`p`)
- `p` contains ALL parameters from UI and extensions at the perfect moment
- `p.script_args` contains data from all AlwaysOnScripts (ControlNet, IP-Adapter, etc.)
- This is the exact moment after parameter assembly but before generation starts

---

## Current Implementation Analysis

### ✅ What We Got Right

Our current `StableQueue-Forge-Extension/scripts/stablequeue.py` correctly implements:

1. **AlwaysOnScript** with `process()` hook (line 80)
2. **Complete parameter extraction** from `StableDiffusionProcessing` object (line 148)
3. **Core parameters** directly from `p` attributes (prompt, steps, cfg_scale, etc.)
4. **Extension parameters** from `p.script_args` by iterating `p.scripts.alwayson_scripts` (line 200)
5. **ControlNet-specific parsing** using research document's 15-parameter structure (line 226)
6. **Local generation prevention** via returning empty `Processed` object (line 121)

### ❌ What We Got Wrong

The JavaScript coordination system in `StableQueue-Forge-Extension/javascript/stablequeue.js`:

**Problem: Artificial Button Triggering Pattern**
```javascript
// WRONG: Complex flag coordination
await fetch('/stablequeue/trigger_queue', { /* set flag */ });
generateBtn.click(); // Artificial triggering
```

**Issues with this approach:**
- ❌ **Artificial button triggering** is not the intended pattern
- ❌ **Complex flag coordination** between JavaScript and Python  
- ❌ **User sees generation starting** even when they just want to queue
- ❌ **Multiple unnecessary steps** in the workflow
- ❌ **HTTP 404 errors** from unnecessary API endpoints

---

## Correct Implementation Strategy

### The Natural Flow Pattern

**✅ How it SHOULD work (per research document):**

1. **User clicks ANY button** (Generate OR Queue in StableQueue)
2. **Both go through normal Gradio generation flow**  
3. **AlwaysOnScript intercepts naturally** at `process()` hook with complete `p` object
4. **Python determines user intent** - was this a queue request or normal generation?
5. **If queue request**: extract parameters, send to StableQueue, prevent local generation
6. **If normal generation**: let it continue normally

### Implementation Details

**JavaScript Changes Needed:**
```javascript
// CORRECT: Direct Gradio integration
const queueBtn = gradio.Button("Queue in StableQueue");
queueBtn.click(fn=python_queue_handler, inputs=[...all_ui_components...]);
```

**Python AlwaysOnScript Logic:**
```python
def process(self, p: StableDiffusionProcessing, *args):
    # Check if this was triggered by a queue button (via component state)
    if self.is_queue_request(args):  # To be implemented
        # Extract complete parameters from p
        params = self.extract_complete_parameters(p)
        # Send to StableQueue
        success = self.submit_to_stablequeue(params)
        if success:
            # Prevent local generation
            return empty_processed_result
    
    # Continue with normal generation
    return None
```

---

## Planned Changes

### Phase 1: Remove Flag System ✅ COMPLETED
- [x] Remove `/stablequeue/trigger_queue` endpoint
- [x] Remove `pending_queue_request` global flag system  
- [x] Remove artificial `generateBtn.click()` triggering

### Phase 2: Implement Direct Gradio Integration  
- [ ] Queue buttons should use Gradio's native `fn=` parameter passing
- [ ] Pass queue intent and server selection directly to Python function
- [ ] AlwaysOnScript determines intent from function parameters, not global flags

### Phase 3: Simplify User Experience
- [ ] User clicks "Queue in StableQueue" → direct queue action (no generation UI artifacts)
- [ ] User clicks "Generate" → normal local generation
- [ ] Clean, predictable behavior with no complex coordination

---

## Technical Implementation Notes

### Parameter Extraction (Already Correct)
Our `extract_complete_parameters()` method properly extracts:
- **Core parameters** from `p` object attributes
- **Extension parameters** from `p.script_args` with specific ControlNet parsing
- **Model/VAE information** and override settings
- **High-resolution fix** and batch parameters

### Local Generation Prevention (Already Correct)
```python
return Processed(
    p,
    images_list=[],
    seed=p.seed,
    info="Job queued in StableQueue - local generation skipped",
    # ... other empty fields
)
```

---

## Success Criteria

**✅ When implementation is complete:**
1. **No artificial button triggering** - queue buttons work directly
2. **No complex flag coordination** - intent passed naturally through Gradio
3. **Clean user experience** - queue actions don't show generation UI
4. **Natural parameter capture** - leverages Forge's built-in flow
5. **Reliable operation** - no HTTP 404 errors from unnecessary endpoints

---

## Reference

- **Research Document:** "Programmatic Parameter Extraction from Stable Diffusion Forge WebUI Extensions"
- **Current Implementation:** `StableQueue-Forge-Extension/scripts/stablequeue.py` (parameter extraction ✅ correct)  
- **Needs Fixing:** `StableQueue-Forge-Extension/javascript/stablequeue.js` (button coordination ❌ wrong pattern)

**Key Insight:** Parameter extraction approach is already perfect - we just need to fix how buttons trigger it! 