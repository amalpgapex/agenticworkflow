# Get Started with InK Studio

**Welcome!** This guide will get you running in 10 minutes.

---

## Step 1: Install (2 minutes)

```bash
# Install Python dependencies
pip install -r requirements.txt
```

## Step 2: Configure (3 minutes)

```bash
# Create your config file
copy config.example.py config.py
```

Edit `config.py` and add your OpenAI API key:
```python
OPENAI_API_KEY = "sk-your-key-here"
```

## Step 3: Run (1 minute)

```bash
# Start the server
.\RUN.bat
```

Open your browser to: **http://localhost:8000**

---

## Your First Task (4 minutes)

1. **Select a task** - Click on any task card (e.g., "Transform Document")
2. **Upload a file** - Choose a DOCX or PDF file
3. **Click "Start"** - Watch the AI work!
4. **See results** - Output appears in the canvas
5. **Export** - Click "Export to Word" to download

**That's it!** You've run your first AI workflow.

---

## Understanding the UI

### Three Panel Layout

```
┌─────────────────────────────────────┐
│          Top Navigation             │
├──────────┬────────────┬─────────────┤
│  Setup   │   Canvas   │   Actions   │
│          │            │             │
│ Pick     │  Output    │  Steps      │
│ task &   │  appears   │  appear     │
│ files    │  here      │  here       │
└──────────┴────────────┴─────────────┘
```

- **Setup**: Select tasks and upload files
- **Canvas**: See AI output (9 different types)
- **Actions**: Track workflow steps, replay from any step

### Smart Behavior
- Setup panel starts at 50% (plenty of browsing room)
- When you click "Start", it shrinks to 350px and Actions panel appears
- Panels collapse smoothly with click or keyboard ([,])

---

## Next Steps

### Learn the Architecture (30 minutes)
Read **ARCHITECTURE.md** to understand:
- How components are organized
- Where to find code
- How to make changes
- All available features

### Explore Features
- Try different canvas types (chat, alignment, etc.)
- Search and filter tasks
- Create your own task in the Library
- Test the alignment viewer with Excel files

### Start Developing
- Component files are in `static/components/`
- Styles in `static/css/main.css`  
- Logic in `static/js/app.js`
- Backend in `app_fastapi.py`

---

## Quick Reference

| Need to... | File to Edit |
|------------|--------------|
| Modify task selection UI | `static/components/setup_panel.html` |
| Add a canvas type | `static/components/canvas_panel.html` |
| Change timeline | `static/components/actions_panel.html` |
| Update styles | `static/css/main.css` |
| Add functionality | `static/js/app.js` |
| Modify backend | `app_fastapi.py` |

---

## Help

**Issues?** Check `docs/TROUBLESHOOTING_GUIDE.md`  
**Questions?** Read `ARCHITECTURE.md`  
**Features?** Browse `docs/` folder

**You're ready to build!** 🚀















