# 🎨 Visual Workflow Builder Guide

## Overview

The new Visual Workflow Builder provides an intuitive, drag-and-drop interface for creating and editing Directions in InK Studio. Inspired by the design principles of Dieter Rams, Don Norman, and Jony Ive.

## Design Philosophy

### 1. **Less, But Better** (Dieter Rams)
- Clean, uncluttered interface
- Every element serves a purpose
- Minimal chrome, maximum content
- Thoughtful use of whitespace

### 2. **Clear Affordances** (Don Norman)
- Draggable tools have visual "grab" affordances
- Immediate feedback on all interactions
- Clear visual hierarchy
- Obvious next steps at every stage

### 3. **Beautiful Simplicity** (Jony Ive)
- Smooth animations and transitions
- Carefully considered micro-interactions
- Cohesive color palette
- Elegant typography

## Key Features

### ✨ **Drag-and-Drop Interface**
- Drag tools from the toolbox into your workflow
- Reorder steps by dragging them up or down
- Visual feedback during dragging
- Drop zones clearly indicated

### 🎯 **Visual Step Builder**
- See your workflow as connected blocks
- Each step shows its type and preview
- Color-coded badges for different step types
- Clear connectors show flow direction

### ⚡ **Inline Editing**
- Click any step to edit it
- Property editor appears below canvas
- Changes are immediate
- No modal dialogs to interrupt flow

### 🔧 **Smart Toolbox**
Categories of tools:
- **AI Processing**: LLM Prompts, Web Search
- **Analysis**: Fact Check, Data Validation
- **Output**: Podcast Generator, Excel Alignment

## How to Use

### Creating a New Direction

1. **Navigate to Workflow Library**
   - Click "Workflow Library" in Studio
   - Click "✨ Create New Direction"

2. **Define Metadata**
   - Enter Direction Name (e.g., "Technical Guide to FAQs")
   - Enter Direction Key (e.g., "tech_to_faq")
   - Add a description

3. **Build Your Workflow**
   - Drag tools from the toolbox on the right
   - Drop them into the canvas
   - Arrange steps in the order you want

4. **Configure Each Step**
   - Click a step to edit it
   - Set the step name
   - Choose the step type
   - Configure the prompt or parameters

5. **Save**
   - Click "💾 Save Direction"
   - Your direction is now available in Studio!

### Editing an Existing Direction

1. Go to Workflow Library
2. Find the direction you want to edit
3. Click "✏️ Edit"
4. Make your changes
5. Save

## Step Types Explained

### 🤖 **LLM Prompt**
- Transform text using AI
- Use placeholders: `{document_content}`, `{previous_output}`
- Most flexible and powerful step type

### 🔍 **Web Search**
- Find information from the web
- Enriches content with external data

### ✅ **Fact Check**
- Verify claims automatically
- Cross-references with web sources

### 🔬 **Data Validation**
- Check for formatting errors
- Validate dates, emails, URLs

### 🎙️ **Podcast Generator**
- Convert text to audio
- Uses OpenAI TTS
- Choose from different voices

### 🔗 **Excel Alignment**
- Match rows between two Excel files
- Uses semantic similarity
- Perfect for comparisons

## Best Practices

### 1. **Start Simple**
- Begin with 2-3 steps
- Test and iterate
- Add complexity as needed

### 2. **Name Steps Clearly**
- Use descriptive names: "Extract Key Topics" not "Step 1"
- Makes workflows self-documenting

### 3. **Chain Outputs**
- Each step can use `{previous_output}`
- Build sophisticated multi-step pipelines

### 4. **Test Frequently**
- Save and test in Studio
- Iterate based on results
- Refine prompts for better output

## Keyboard Shortcuts

- **Click**: Select step
- **Drag**: Reorder steps
- **Delete**: Remove step (with confirmation)
- **Escape**: Deselect step

## Visual Design Elements

### Color Coding
- **Blue badges**: LLM/AI steps
- **Green badges**: Tool/Output steps  
- **Yellow badges**: Analysis steps

### States
- **Normal**: Gray border
- **Hover**: Blue border + shadow
- **Active/Selected**: Blue border + blue background tint
- **Dragging**: Faded + rotated

### Feedback
- Smooth transitions (200ms cubic-bezier)
- Bounce on drop
- Fade in on create
- Slide out on delete

## Technical Notes

### Libraries Used
- **Alpine.js**: Reactive state management
- **Tailwind CSS**: Utility-first styling
- **SortableJS**: Drag and drop functionality

### Data Format
Workflows are saved in the same JSON format as before, ensuring backward compatibility with existing directions.

### API Integration
- Uses existing `/api/transformation` endpoints
- No changes to backend required
- Seamless integration with Studio

## Accessibility

- Keyboard navigation support
- ARIA labels on interactive elements
- High contrast ratios
- Focus indicators on all controls

## Future Enhancements

Potential additions:
- **Visual Preview Mode**: See how workflow executes
- **Step Templates**: Pre-built step configurations
- **Branching Logic**: Conditional steps
- **Variables Panel**: Define reusable variables
- **Export/Import**: Share workflows as files
- **Version History**: Track changes over time

## Support

For questions or issues with the Workflow Builder:
1. Check this guide
2. Review example workflows in the Library
3. Consult the main README.md

---

**Remember**: The best workflows are simple, clear, and focused. Start with the basics and build from there! 🚀


