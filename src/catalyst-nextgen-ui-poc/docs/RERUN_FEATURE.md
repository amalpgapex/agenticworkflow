# 🔄 Re-run from Step Feature

## Overview
InK Studio now supports **iterative workflow editing** - users can edit the output of any intermediate step and re-run the workflow from that point forward. This enables rapid iteration and refinement without starting from scratch.

## How It Works

### User Workflow

1. **Run Initial Workflow**
   - Upload document
   - Select direction
   - Click "✨ Begin direction"
   - Workflow executes all steps

2. **Review Intermediate Results**
   - Click any step card in the Workflow panel (right side)
   - View that step's output in the Canvas

3. **Edit Content**
   - Edit the text directly in the Canvas (WYSIWYG editor)
   - Modify headings, text, formatting
   - Make any desired changes

4. **Re-run from This Step**
   - Click "🔄 Replay from here" button next to the step
   - System will:
     - Use your edited content as input
     - Re-execute the current step
     - Execute all subsequent steps
     - Display updated results

### Visual Flow

```
Initial Run:
Step 1 → Step 2 → Step 3 → Done
  ✅      ✅      ✅

User Edits Step 2 Output → Clicks "Re-run from Step 2"

Re-run Flow:
Step 1 → Step 2 (with edited input) → Step 3 (with new input) → Done
  ✅      🔄 Processing...          🔄 Processing...
```

## Implementation Details

### Frontend Changes (`templates/index.html`)

#### 1. Re-run Button
Located in the Canvas panel, appears when:
- Not currently processing
- Viewing a step that's not the last step
- Workflow has completed at least once

```html
<button @click="rerunFromStep(currentViewingStep)">
    🔄 Re-run from Step X
</button>
```

#### 2. JavaScript Method: `rerunFromStep(stepIndex)`

**What it does:**
1. Extracts edited content from the WYSIWYG editor
2. Converts HTML back to Markdown (using Turndown.js)
3. Updates the current step's output with edited content
4. Marks subsequent steps as "pending"
5. Calls backend with re-run parameters
6. Sets up event source for streaming results

**Key Logic:**
```javascript
async rerunFromStep(stepIndex) {
    // Get edited content from canvas
    const editorDiv = document.getElementById('wysiwyg-editor');
    const editedContent = this.turndownService.turndown(editorDiv.innerHTML);
    
    // Update step output
    this.stepOutputs[stepIndex] = editedContent;
    
    // Mark future steps as pending
    for (let i = stepIndex + 1; i < this.steps.length; i++) {
        this.steps[i].status = 'pending';
        this.stepOutputs[i] = '';
    }
    
    // Call backend to re-run
    const eventSource = new EventSource(
        `/api/stream/${this.selectedTransform}?start_from_step=${stepIndex + 1}&edited_output=${encodeURIComponent(editedContent)}`
    );
}
```

#### 3. Event Source Handler Refactoring

Created `setupEventSourceHandlers(eventSource)` method to:
- Handle SSE messages (step_status, stream, complete, error)
- Reusable for both initial run and re-runs
- Single source of truth for event handling

### Backend Changes (`app_fastapi.py`)

#### 1. Updated Stream Endpoint

```python
@app.get("/api/stream/{transformation_key}")
async def stream_transformation(
    transformation_key: str, 
    request: Request,
    start_from_step: int = 0,      # NEW: Step to start from
    edited_output: str = ""        # NEW: Edited content
):
```

**New Parameters:**
- `start_from_step`: Index of step to begin execution (0 = full run)
- `edited_output`: Edited content from previous step

#### 2. Re-run Logic

**Step Result Restoration:**
```python
if start_from_step > 0 and edited_output:
    # Restore previous step results
    for i in range(start_from_step):
        if i in current_state["step_outputs"]:
            step_results.append(current_state["step_outputs"][i]['output'])
    
    # Use edited output as previous output
    step_results[start_from_step - 1] = edited_output
```

**Step Execution Control:**
```python
for i, step in enumerate(transform_info['steps']):
    # Skip already-completed steps
    if i < start_from_step:
        yield json.dumps({'type': 'step_status', 'step': i, 'status': 'completed'})
        continue
    
    # Execute from start_from_step onwards
    # ... (normal execution logic)
```

## Use Cases

### 1. Iterative Refinement
**Scenario:** Executive Summary workflow
- Step 1: Extract Key Points
- Step 2: Create Summary

**User Action:**
1. Run workflow
2. Review extracted key points (Step 1)
3. Edit to add/remove points
4. Re-run from Step 1
5. Step 2 (summary) now uses refined key points

### 2. Error Correction
**Scenario:** Podcast generation
- Step 1: Create Script
- Step 2: Generate Audio

**User Action:**
1. Run workflow
2. Notice typo in script (Step 1)
3. Fix typo in Canvas
4. Re-run from Step 1
5. New audio generated with corrected script

### 3. A/B Testing
**Scenario:** Try different phrasings
- Edit Step 1 output with variant A
- Re-run to see results
- Edit again with variant B
- Re-run to compare

### 4. Fact Correction
**Scenario:** Document with outdated info
- Step 1 extracts data
- User updates data in Canvas
- Re-run to propagate changes through workflow

## Technical Specifications

### State Management

**Frontend State:**
- `stepOutputs[]`: Array of step outputs (modified during edit)
- `steps[]`: Array of step metadata (status updated during re-run)
- `currentViewingStep`: Currently displayed step
- `processing`: Boolean flag (set during re-run)

**Backend State:**
- `current_state["step_outputs"]`: Dictionary of completed steps
- `current_state["doc_content"]`: Original document (unchanged)
- Restored during re-run for context

### Data Flow

```
1. User edits Step 2 output in Canvas
   ↓
2. Frontend: HTML → Markdown conversion (Turndown.js)
   ↓
3. Frontend: stepOutputs[2] = edited_markdown
   ↓
4. Frontend: Call /api/stream?start_from_step=3&edited_output=...
   ↓
5. Backend: Restore steps 0-2 from current_state
   ↓
6. Backend: Replace step 2 output with edited_output
   ↓
7. Backend: Execute steps 3+ with new context
   ↓
8. Frontend: Stream and display results
```

### URL Parameters

**Re-run Request:**
```
GET /api/stream/{transformation_key}?start_from_step=2&edited_output=<encoded_markdown>
```

- `transformation_key`: Workflow to execute
- `start_from_step`: First step to execute (3 = execute from step 3)
- `edited_output`: URL-encoded markdown content from previous step

**Initial Run Request:**
```
GET /api/stream/{transformation_key}
```
(Default: `start_from_step=0`, `edited_output=""`)

## UI/UX Details

### Button Visibility Logic

```javascript
x-show="currentViewingStep < steps.length && 
        steps.length > 0 && 
        currentViewingStep < steps.length - 1"
```

**Shows when:**
- ✅ Viewing a step (not empty state)
- ✅ Workflow has steps
- ✅ Not viewing the last step (re-running last step has no effect)

**Hidden when:**
- ❌ Processing (prevents concurrent runs)
- ❌ No steps loaded
- ❌ Viewing last step
- ❌ Audio content displayed (for now - could enhance later)

### Visual Indicators

**During Re-run:**
1. Current step card: Shows "⚡ Processing..."
2. Subsequent step cards: Show "⏳ Pending"
3. Previous step cards: Show "✅ Completed"
4. Canvas: Shows streaming updates with "✨ Streaming..." indicator

### Helper Text

```
"Edit content above, then re-run workflow from this step"
```

Appears below re-run button to guide users.

## Edge Cases Handled

### 1. Audio Content
- Currently preserves audio file reference
- Does not allow editing audio steps
- Could be enhanced to allow script editing + re-generation

### 2. No Editor Initialized
- Falls back to using stored `stepOutputs[stepIndex]`
- Prevents errors if editor isn't ready

### 3. Empty Edited Content
- Uses original step output as fallback
- Prevents running with empty input

### 4. Concurrent Processing
- Re-run button disabled during processing
- Prevents multiple simultaneous executions

### 5. State Restoration Failures
- Gracefully handles missing `step_outputs` in state
- Uses empty string as fallback

## Future Enhancements

### Potential Improvements

1. **Visual Diff Indicator**
   - Show what changed between original and edited
   - Highlight modified sections

2. **Version History**
   - Save multiple versions of step outputs
   - Allow rolling back to previous versions

3. **Partial Re-run Confirmation**
   - Warn user if editing early steps
   - Show which downstream steps will be affected

4. **Edit Audio Scripts**
   - For podcast steps, allow editing script
   - Auto-regenerate audio with edited script

5. **Batch Re-runs**
   - Edit multiple steps
   - Re-run all affected steps once

6. **Compare Results**
   - Side-by-side view of original vs. re-run output
   - Diff highlighting

7. **Undo/Redo**
   - Keyboard shortcuts (Ctrl+Z/Ctrl+Y)
   - Undo re-runs

## Benefits

### For Users
✅ **Faster Iteration**: Don't start from scratch  
✅ **Precise Control**: Edit exactly what you want  
✅ **Cost Efficient**: Only re-run necessary steps  
✅ **Quality Improvement**: Refine outputs iteratively  

### For Developers
✅ **Clean Architecture**: Reuses existing streaming infrastructure  
✅ **State Management**: Preserves context across re-runs  
✅ **Extensible**: Easy to add to new workflows  
✅ **No Breaking Changes**: Backward compatible with existing flows  

## Testing Scenarios

### Test Case 1: Edit and Re-run
1. Upload document
2. Run "Executive Summary" workflow
3. Click "Step 1: Extract Key Points"
4. Edit content in Canvas (add/remove bullet points)
5. Click "Re-run from Step 1"
6. Verify Step 2 summary uses edited key points

### Test Case 2: Multiple Re-runs
1. Run workflow
2. Edit Step 1, re-run
3. Edit Step 1 again (different content), re-run
4. Verify each re-run uses latest edits

### Test Case 3: Cross-Step Dependencies
1. Run 3-step workflow
2. Edit Step 1 output
3. Re-run from Step 1
4. Verify Step 2 and Step 3 receive updated context

### Test Case 4: Cancel During Re-run
1. Edit step and click re-run
2. Close connection (refresh page)
3. Verify no corruption of state
4. Re-run should work on next attempt

## Summary

The re-run feature transforms InK Studio from a one-way pipeline into an **iterative refinement tool**. Users can now:
- 🔍 Inspect intermediate outputs
- ✏️ Edit and refine content
- 🔄 Re-run from any point
- 🚀 Achieve better results faster

This feature leverages the existing LangChain/LangGraph infrastructure and extends it with smart state management and user-friendly controls, making the entire workflow system more powerful and flexible.

