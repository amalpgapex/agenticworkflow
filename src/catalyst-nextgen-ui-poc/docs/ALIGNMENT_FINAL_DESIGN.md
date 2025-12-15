# 🎯 Alignment Viewer - Final Design

## Overview

The Alignment Viewer displays policy/requirement comparisons in **original document order** with unmatched items integrated into their respective columns.

---

## Three Key Features Implemented

### 1. ✅ **Auto-Updating Detail Panel**

**Behavior**: Click any pair → Detail panel updates immediately

**Before**: Had to close (×) before selecting another pair  
**After**: Click switches directly to new pair's details

**Implementation**:
```javascript
selectPairAndScroll(idx) {
    this.selectedPair = idx;  // Direct assignment, no toggle
    // ... scroll logic
}
```

### 2. ✅ **AI Analysis Visible**

**Display**: "Key Differences" section in detail panel

**Shows**: Natural language description of differences from GPT-4o-mini

**Conditions**:
- Only for matched pairs (`type === 'match'`)
- Only when analysis exists (`currentPair.analysis`)
- Only when task includes comparison step (`alignmentData.has_analysis`)

**Styling**: Blue accent panel, compact typography

### 3. ✅ **Unmatched Items in Their Columns**

**File 1 Orphans**: Appear in **left column** at their original positions
**File 2 Orphans**: Appear in **right column** at their original positions

**Visual Indicators**:
- 🟡 Amber background (`bg-amber-50`)
- 🟡 Amber border (`border-amber-300`)
- 🟡 Amber vertical bar on edge
- 🟡 "Unmatched" badge
- 🟡 60% opacity
- 🚫 Not clickable (no details to show)

---

## Data Structure

### Unified Pairs List

Backend creates a single list with three item types:

```javascript
[
    // Type 1: Matched pair
    {
        type: 'match',
        file1_index: 0,
        file2_index: 5,
        file1_value: 'Policy 1.1: Background Checks',
        file2_value: 'Policy 1.1: Background Checks (Updated)',
        similarity: 0.95,
        is_matched: true,
        diff: '<span class="diff-added">Updated</span>',
        analysis: 'Updated to include digital verification.'
    },
    
    // Type 2: File 1 orphan (no match in File 2)
    {
        type: 'orphan_file1',
        file1_index: 1,
        file2_index: null,
        file1_value: 'Policy 1.2: Drug Testing',
        file2_value: null,
        similarity: 0.0,
        is_matched: false
    },
    
    // Type 3: File 2 orphan (no match in File 1)
    {
        type: 'orphan_file2',
        file1_index: null,
        file2_index: 7,
        file1_value: null,
        file2_value: 'Policy 3.1: AI Usage Guidelines',
        similarity: 0.0,
        is_matched: false
    }
]
```

---

## Visual Layout

### Three-Column Design

```
┌─────────────────────────────────────────────────────────────┐
│  File 1 (Original Order)  │   Details   │   File 2          │
├─────────────────────────────────────────────────────────────┤
│  #1 Policy 1.1... [95%]◄──────────────────►Policy 1.1...[95%]│
│                           │  Similarity  │                   │
│  #2 Policy 1.2...         │  Diff        │                   │
│     [Unmatched] ⚠️        │  AI Analysis │                   │
│                           │              │                   │
│  #3 Policy 1.3... [98%]◄──────────────────►Policy 1.3...[98%]│
│                           │              │                   │
│  #4 Policy 2.1... [87%]◄──────────────────►Policy 2.1...[87%]│
│                           │              │                   │
│                           │              │  #7 Policy 3.1... │
│                           │              │     [Unmatched] ⚠️│
└─────────────────────────────────────────────────────────────┘
```

### Card States

**Matched Pairs**:
- White background
- Green/blue/amber similarity bar (height varies)
- Similarity percentage badge
- Hover: Blue ring
- Click: Blue ring + detail panel updates
- Clickable cursor

**Unmatched Items**:
- Amber background (`bg-amber-50`)
- Amber border (`border-amber-300`)
- "Unmatched" badge (amber)
- Static amber bar (fixed height)
- No hover effect
- Not clickable
- 70% opacity

---

## Interaction Flow

### Reviewing Matches

1. **Start**: See all items in original order
2. **Scan**: Identify unmatched items (amber cards)
3. **Click**: Select matched pair
4. **Auto-scroll**: Both columns align cards horizontally
5. **Review**: Detail panel shows:
   - Similarity percentage
   - Text differences (redline/greenline)
   - AI analysis ("Key Differences")
6. **Next**: Click another pair → Detail panel updates instantly

### Understanding Unmatched Items

**File 1 Orphan** (left column, amber):
- This policy existed in old version
- No match found in new version
- Possibly deleted or significantly restructured

**File 2 Orphan** (right column, amber):
- This policy exists in new version
- No match found in old version
- Likely a new addition or major reorganization

---

## Detail Panel Content

### For Matched Pairs

**1. Similarity**:
```
Similarity
─────────────────────  95.2%
████████████████████░
```
- Visual progress bar
- Color-coded (emerald/blue/amber)
- Percentage to 1 decimal

**2. Text Differences** (if enabled):
```
Text Differences
Policy 1.1: Background <removed>must</removed> <added>should</added> include...
```
- Word-level diff
- Redline for deletions
- Greenline for additions

**3. Key Differences** (if AI analysis enabled):
```
Key Differences
The updated policy adds digital verification and removes
the mandatory 30-day timeline, making it more flexible.
```
- Natural language summary
- 1-2 sentences
- Focus on meaningful changes

### For Unmatched Items

**Warning Notice**:
```
⚠️ No Match Found
This item from File 1 has no corresponding match in File 2.
```
- Amber background
- Warning icon
- Contextual message (File 1 vs File 2)

---

## Use Case: Policy Manual Comparison

### Scenario
Comparing Company Policy Manual v1.0 → v2.0

### Results View

**Left Column** (v1.0 in order):
- #1 Introduction [matched, 99%]
- #2 Background Checks [matched, 95%]
- #3 Drug Testing [unmatched] ⚠️ ← Policy removed
- #4 Confidentiality [matched, 97%]
- #5 Remote Work [matched, 82%]
- #6 Equipment [matched, 91%]

**Right Column** (v2.0 aligned):
- #1 Introduction [matched, 99%]
- #2 Background Checks (Updated) [matched, 95%]
- (empty space for #3)
- #3 Confidentiality [matched, 97%]
- #4 Remote Work (Revised) [matched, 82%]
- #5 Equipment [matched, 91%]
- #8 AI Usage [unmatched] ⚠️ ← New policy

### Analysis Workflow

1. Start at top
2. See Policy 1 matched with minor changes
3. See Policy 2 matched with significant update (82%)
4. Notice Policy 3 (Drug Testing) removed
5. Continue through document
6. Note Policy 8 (AI Usage) is new

**Insight**: One deletion, one addition, multiple updates. Structure mostly preserved.

---

## Technical Details

### Backend Algorithm

```python
# 1. Run Hungarian algorithm for optimal matching
row_indices, col_indices = linear_sum_assignment(cost_matrix)

# 2. Build match lookup
match_dict_1to2[file1_index] = file2_index

# 3. Iterate File 1 in order
for i in range(len(file1_items)):
    if i in match_dict_1to2:
        add_matched_pair()
    else:
        add_orphan_file1()

# 4. Add File 2 orphans at end
for j in unmatched_file2_indices:
    add_orphan_file2()
```

### Frontend Rendering

```javascript
// Left column: Show items with file1_value
<div x-show="pair.file1_value">
    <!-- Render file1 item -->
</div>

// Right column: Show items with file2_value
<div x-show="pair.file2_value">
    <!-- Render file2 item -->
</div>

// Detail panel: Conditional content based on type
<div x-show="currentPair.type === 'match'">
    <!-- Show similarity, diff, analysis -->
</div>
<div x-show="currentPair.type === 'orphan_file1'">
    <!-- Show "no match in File 2" -->
</div>
<div x-show="currentPair.type === 'orphan_file2'">
    <!-- Show "no match in File 1" -->
</div>
```

---

## Benefits

✅ **Preserves document structure** - Policies in original order  
✅ **Inline gap analysis** - Deletions visible in context  
✅ **Clear additions** - New policies appear at end of right column  
✅ **Efficient review** - Sequential top-to-bottom workflow  
✅ **Audit-friendly** - Track every item, identify all changes  
✅ **Auto-updating details** - Instant switching between pairs  
✅ **Comprehensive analysis** - Text diff + AI interpretation  
✅ **Professional appearance** - Clean, refined, purposeful  

---

## Files Modified

1. **`agentic_tools.py`**:
   - AlignmentTool: Creates `unified_pairs` with types
   - Adds File 2 orphans to unified list
   - CompareAnalysisTool: Handles unified format

2. **`templates/index.html`**:
   - Updated to use `unified_pairs`
   - Conditional rendering by type
   - Auto-update detail panel (no toggle)
   - Amber styling for unmatched items
   - Removed separate orphans section

3. **`docs/ALIGNMENT_FINAL_DESIGN.md`** (this file):
   - Complete design documentation
   - Use case examples
   - Technical implementation details

---

*Final Design: October 2025*  
*Purpose: Policy/requirement comparison in original order*  
*Result: Professional, audit-ready alignment viewer*
