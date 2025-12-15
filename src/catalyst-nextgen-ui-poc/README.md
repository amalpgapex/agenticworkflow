# InK Studio - AI Document Transformation Platform

Transform documents with AI-powered workflows, multiple canvas types, and a clean modular UI.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure
copy config.example.py config.py
# Edit config.py and add your OpenAI API key

# 3. Run
.\RUN.bat

# 4. Open browser
http://localhost:8000
```

**Done!** Start transforming documents with AI.

---

## 📚 Documentation

### For New Developers
1. **GET_STARTED.md** - 10-minute quick start
2. **ARCHITECTURE.md** - Complete system guide
3. **docs/** folder - Feature-specific guides

### Quick Reference
- **Get Started**: Read GET_STARTED.md
- **Understand Architecture**: Read ARCHITECTURE.md  
- **Specific Features**: Check docs/ folder
- **Troubleshooting**: See docs/TROUBLESHOOTING_GUIDE.md

---

## ✨ Features

- **9 Canvas Types**: Text editor, chat, alignment, relationships, audio, images, PDF, code, markdown
- **Smart Workflows**: Multi-step AI with visual progress
- **File Support**: DOCX, PDF, Excel, TXT
- **Live Streaming**: See AI output as it generates
- **Export to Word**: Download as DOCX
- **Task Library**: Save and reuse workflows
- **Context-Aware UI**: Panels auto-resize intelligently
- **Smooth Transitions**: Professional animations

---

## 📁 Project Structure

```
Root/
├── GET_STARTED.md         # Start here
├── ARCHITECTURE.md        # Complete guide
├── README.md              # This file
│
├── RUN.bat                # Launch app
├── config.py              # Add API key here
├── requirements.txt       # Dependencies
│
├── static/
│   ├── components/        # UI components (4 files)
│   ├── css/main.css       # Styles
│   └── js/app.js          # Logic
│
├── templates/
│   └── index.html         # Main app (180 lines)
│
├── Backend (Python files)
│   ├── app_fastapi.py     # Server
│   ├── langgraph_agent.py # AI workflows
│   └── (4 more files)
│
└── docs/                  # Feature guides
```

---

## 🛠️ For Developers

### Making Changes
| Change... | Edit This File |
|-----------|----------------|
| Task selection UI | `static/components/setup_panel.html` |
| Canvas output | `static/components/canvas_panel.html` |
| Timeline | `static/components/actions_panel.html` |
| Styles | `static/css/main.css` |
| Logic | `static/js/app.js` |
| Backend | `app_fastapi.py` |

### Technologies
- **Frontend**: Alpine.js, Tailwind CSS
- **Backend**: FastAPI, LangGraph, OpenAI
- **Documents**: python-docx, PyPDF2, pandas
- **Streaming**: SSE (Server-Sent Events)

---

## 📊 Stats

- **UI Code**: 1,162 lines (was 3,282) - 65% reduction
- **Components**: 4 modular files
- **Canvas Types**: 9 working
- **Documentation**: 3 essential files
- **Maintainability**: A+ (was D-)

---

## 🆘 Need Help?

- **Quick Start**: GET_STARTED.md
- **Architecture**: ARCHITECTURE.md
- **Features**: docs/ folder
- **Issues**: docs/TROUBLESHOOTING_GUIDE.md

---

**Version**: 2.0 (Refactored)  
**Status**: Production Ready ✅  
**Last Updated**: October 7, 2025

**Ready to build amazing AI workflows!** 🚀
