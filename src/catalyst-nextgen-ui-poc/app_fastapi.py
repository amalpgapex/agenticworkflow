"""
InK Studio - Main FastAPI Application
Modern AI-powered document transformation with multi-canvas support
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Form, APIRouter
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import asyncio, uuid
import json
import tempfile
from typing import AsyncGenerator, Dict, Any, Tuple
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import config
from config import OPENAI_API_KEY, DEFAULT_MODEL, APP_NAME, APP_DESCRIPTION, GENERATED_AUDIO_DIR
from prompt_manager import PromptManager
from document_processor import DocumentProcessor
from langgraph_agent import DocumentTransformationAgent
from agentic_tools import clear_rag_sessions

from app.utils.mcp_uri import build_mcp_uri
from app.utils.skill_descriptor_auto import build_skill_descriptor_for
from app.utils.tool_contract import build_descriptor_from_contract, CONTRACTS
from app.utils.skill_adapters import adapt_inputs

# ------------------------------
# APP INIT
# ------------------------------
# Initialize FastAPI app
app = FastAPI(title=APP_NAME, description=APP_DESCRIPTION)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")
pm = PromptManager()
dp = DocumentProcessor()

# ------------------------------
# CORRELATION & ERROR MIDDLEWARE (Azure-ready)
# ------------------------------
import time

@app.middleware("http")
async def correlation_mw(request: Request, call_next):
    """
    - Generates/propagates X-Request-ID for end-to-end correlation (APIM/clients).
    - Exposes X-Process-Time in the response.
    - JWT/roles/scopes validation is handled upstream in APIM (gateway), not here.
    """
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    request.state.request_id = request_id

    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        # Unified JSON error with correlation
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Internal Server Error",
                    "request_id": request_id
                }
            }
        )

    duration = time.perf_counter() - start
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{duration:.4f}"
    return response

# ------------------------------
# UNIFORM EXCEPTION HANDLERS (JSON)
# ------------------------------
async def _extract_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", request.headers.get("x-request-id", str(uuid.uuid4())))

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = await _extract_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.status_code,
                "message": str(exc.detail),
                "request_id": request_id
            }
        }
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = await _extract_request_id(request)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": 500,
                "message": "Internal Server Error",
                "request_id": request_id
            }
        }
    )

# ------------------------------
# CONFIG / AGENT SETUP
# ------------------------------
def load_canvas_config():
    try:
        with open(config.CANVAS_TYPES_FILE, 'r', encoding='utf-8') as f:
            cfg = json.load(f)
        print(f"✓ Loaded {len(cfg.get('canvas_types', {}))} canvas types")
        return cfg
    except Exception as e:
        print(f"Warning: Could not load canvas_types.json: {str(e)}")
        return {}


canvas_types_config = load_canvas_config()


def init_agent():
    try:
        agent_instance = DocumentTransformationAgent(api_key=OPENAI_API_KEY, model=DEFAULT_MODEL)
        print(f"✓ Agent initialized successfully with {DEFAULT_MODEL}")
        return agent_instance
    except Exception as init_error:
        print(f"Error initializing agent: {str(init_error)}")
        return None


agent = init_agent()

# Global state (in production, use proper state management)
current_state = {
    "doc_content": None,
    "doc_template": None,
    "step_outputs": {},
    "all_documents": [],
    "uploaded_excel_files": [],
    "labeled_documents": {}  # For tasks that require specific labeled file inputs
}


def reset_current_state(clear_rag: bool = True) -> None:
    """Reset server-side state between document sessions."""
    global current_state
    current_state["doc_content"] = None
    current_state["doc_template"] = None
    current_state["step_outputs"] = {}
    current_state["selected_options"] = {}
    current_state["all_documents"] = []
    current_state["uploaded_excel_files"] = []
    current_state["labeled_documents"] = {}
    for key in [
        "file1_path",
        "file2_path",
        "file1_name",
        "file2_name",
        "file_type",
        "default_canvas_type"
    ]:
        if key in current_state:
            current_state.pop(key, None)
    if clear_rag:
        try:
            clear_rag_sessions()
        except Exception as e:
            print(f"Warning: Unable to clear RAG sessions: {e}")

# ------------------------------
# PAGES
# ------------------------------
@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the landing page"""
    try:
        with open("templates/landing.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Template not found</h1><p>Please ensure templates/landing.html exists</p>")
    except UnicodeDecodeError as e:
        return HTMLResponse(content=f"<h1>Encoding Error</h1><p>Error: {str(e)}</p>")


@app.get("/studio", response_class=HTMLResponse)
async def studio():
    """Serve the main Studio application"""
    try:
        with open("templates/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Template not found</h1><p>Please ensure templates/index.html exists</p>")
    except UnicodeDecodeError as e:
        return HTMLResponse(content=f"<h1>Encoding Error</h1><p>Error: {str(e)}</p>")


@app.get("/workflow-builder", response_class=HTMLResponse)
async def workflow_builder():
    """Serve the visual workflow builder"""
    try:
        with open("templates/workflow_builder.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Template not found</h1><p>Please ensure templates/workflow_builder.html exists</p>")
    except UnicodeDecodeError as e:
        return HTMLResponse(content=f"<h1>Encoding Error</h1><p>Error: {str(e)}</p>")

# ------------------------------
# API: CANVAS TYPES & TRANSFORMATIONS
# ------------------------------
@app.get("/api/canvas-types")
async def get_canvas_types():
    """Get all available canvas types"""
    return canvas_types_config


@app.get("/api/canvas-type/{canvas_type_id}")
async def get_canvas_type(canvas_type_id: str):
    """Get specific canvas type configuration"""
    canvas_type = canvas_types_config.get('canvas_types', {}).get(canvas_type_id)
    if not canvas_type:
        raise HTTPException(status_code=404, detail="Canvas type not found")
    return canvas_type


@app.get("/api/transformations")
async def get_transformations():
    """Get available transformations with canvas type metadata"""
    transformations = pm.get_all_transformations()
    return {
        "transformations": [
            {
                "key": key,
                "name": info["name"],
                "description": info["description"],
                "steps": len(info["steps"]),
                "canvas_type": info.get("canvas_type", "text_editor"),
                "input_file_types": info.get("input_file_types", ["docx"]),
                "requires_dual_upload": info.get("requires_dual_upload", False),
                "allow_multiple_files": info.get("allow_multiple_files", False),
                "requires_labeled_files": info.get("requires_labeled_files", False),
                "labeled_file_inputs": info.get("labeled_file_inputs", []),
                "options": info.get("options", {}),
                "category": info.get("category", "update"),
                "icon": info.get("icon")
            }
            for key, info in transformations.items()
        ]
    }


@app.get("/api/transformation/{transformation_key}")
async def get_transformation_details(transformation_key: str):
    """Get detailed information about a specific transformation"""
    transformation = pm.get_transformation_by_key(transformation_key)
    if not transformation:
        return {"error": "Transformation not found"}
    return transformation


def validate_option_config(option_type: str, config: dict) -> tuple[bool, str]:
    """
    Validate option configuration based on type.
    Returns (is_valid, error_message)
    """
    # Default to 'select' type for backward compatibility
    if not option_type or option_type == 'select':
        return True, ""
    
    validators = {
        'number': lambda c: (
            ('min' in c and 'max' in c, "Number options must have 'min' and 'max' values") 
            if 'min' not in c or 'max' not in c else
            (c['min'] < c['max'], "Min value must be less than max value")
        ),
        'checkbox': lambda c: (
            'default' in c, "Checkbox options must have a 'default' value (true or false)"
        ),
        'text': lambda c: (True, ""),  # Text inputs are always valid
        'textarea': lambda c: (
            'rows' in c, "Textarea options must specify 'rows'"
        )
    }
    
    if option_type not in validators:
        return False, f"Unknown option type: {option_type}"
    
    result = validators[option_type](config)
    if isinstance(result, tuple):
        return result
    return result, ""


@app.post("/api/transformation")
async def add_transformation(data: dict):
    """Add a new transformation"""
    try:
        # Validate required fields
        if not data.get('key') or not data.get('name'):
            return {"success": False, "error": "Key and name are required"}
        
        # Check if key already exists
        if pm.get_transformation_by_key(data['key']):
            return {"success": False, "error": "Transformation with this key already exists"}
        
        # Validate options configuration if present
        options = data.get('options', {})
        for option_key, option_config in options.items():
            option_type = option_config.get('type', 'select')
            is_valid, error_msg = validate_option_config(option_type, option_config)
            if not is_valid:
                return {"success": False, "error": f"Invalid option '{option_key}': {error_msg}"}
        
        # Add transformation
        pm.add_transformation(
            key=data['key'],
            name=data['name'],
            description=data.get('description', ''),
            steps=data.get('steps', []),
            options=options
        )
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/api/transformation/{transformation_key}")
async def update_transformation(transformation_key: str, data: dict):
    """Update an existing transformation"""
    try:
        if not pm.get_transformation_by_key(transformation_key):
            return {"success": False, "error": "Transformation not found"}
        
        # Validate options configuration if present
        options = data.get('options', {})
        if options:
            for option_key, option_config in options.items():
                option_type = option_config.get('type', 'select')
                is_valid, error_msg = validate_option_config(option_type, option_config)
                if not is_valid:
                    return {"success": False, "error": f"Invalid option '{option_key}': {error_msg}"}
        
        # Update transformation
        pm.update_transformation(
            key=transformation_key,
            name=data.get('name'),
            description=data.get('description'),
            steps=data.get('steps'),
            options=options if options else None
        )
        
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/transformation/{transformation_key}")
async def delete_transformation(transformation_key: str):
    """Delete a transformation"""
    try:
        if not pm.get_transformation_by_key(transformation_key):
            return {"success": False, "error": "Transformation not found"}
        
        pm.delete_transformation(transformation_key)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/transformation/{transformation_key}/duplicate")
async def duplicate_transformation(transformation_key: str):
    """Duplicate an existing transformation"""
    try:
        original = pm.get_transformation_by_key(transformation_key)
        if not original:
            return {"success": False, "error": "Transformation not found"}
        
        # Generate new unique key
        base_key = f"{transformation_key}_copy"
        new_key = base_key
        counter = 1
        while pm.get_transformation_by_key(new_key):
            new_key = f"{base_key}_{counter}"
            counter += 1
        
        # Create duplicate with new key
        pm.add_transformation(
            key=new_key,
            name=f"{original['name']} (Copy)",
            description=original.get('description', ''),
            steps=original.get('steps', []),
            options=original.get('options', {})
        )
        
        return {
            "success": True,
            "new_key": new_key,
            "new_name": f"{original['name']} (Copy)"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/transformation/{transformation_key}/export")
async def export_transformation(transformation_key: str):
    """Export transformation as JSON"""
    try:
        transformation = pm.get_transformation_by_key(transformation_key)
        if not transformation:
            raise HTTPException(status_code=404, detail="Transformation not found")
        
        # Return as JSON with nice formatting
        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=transformation,
            headers={
                "Content-Disposition": f"attachment; filename={transformation_key}.json"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transformation/import")
async def import_transformation(data: dict):
    """Import transformation from JSON"""
    try:
        # Validate required fields
        if not data.get('key') or not data.get('name'):
            return {"success": False, "error": "Imported workflow must have 'key' and 'name' fields"}
        
        # Check if key already exists
        if pm.get_transformation_by_key(data['key']):
            # Auto-generate new key to avoid conflicts
            base_key = f"{data['key']}_imported"
            new_key = base_key
            counter = 1
            while pm.get_transformation_by_key(new_key):
                new_key = f"{base_key}_{counter}"
                counter += 1
            data['key'] = new_key
            data['name'] = f"{data['name']} (Imported)"
        
        # Validate options if present
        options = data.get('options', {})
        for option_key, option_config in options.items():
            option_type = option_config.get('type', 'select')
            is_valid, error_msg = validate_option_config(option_type, option_config)
            if not is_valid:
                return {"success": False, "error": f"Invalid option '{option_key}' in imported workflow: {error_msg}"}
        
        # Add the transformation
        pm.add_transformation(
            key=data['key'],
            name=data['name'],
            description=data.get('description', ''),
            steps=data.get('steps', []),
            options=options
        )
        
        return {
            "success": True,
            "key": data['key'],
            "name": data['name']
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# ------------------------------
# AUDIO / UPLOADS
# ------------------------------
@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files"""
    audio_path = GENERATED_AUDIO_DIR / filename
    
    # Security: prevent directory traversal
    if not audio_path.is_file() or not str(audio_path).startswith(str(GENERATED_AUDIO_DIR)):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=filename
    )


@app.post("/api/upload-labeled")
async def upload_labeled_document(file: UploadFile = File(...), label: str = Form(...)):
    """Upload a document with a specific label for workflows requiring multiple specific files"""
    global current_state
    
    if not label:
        return {"success": False, "error": "Label is required for labeled uploads"}
    
    # Read file
    content_bytes = await file.read()
    
    # Detect file type from filename
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    
    # Extract content
    if file_ext == 'docx':
        content, template = dp.extract_content_and_style(content_bytes)
    elif file_ext == 'pdf':
        content = dp.extract_pdf_content(content_bytes)
        template = None
    elif file_ext in ['txt', 'md']:
        content = content_bytes.decode('utf-8', errors='ignore')
        template = None
    else:
        try:
            content = content_bytes.decode('utf-8', errors='ignore')
        except:
            content = "Unable to extract text content from file"
        template = None
    
    # Store in labeled_documents
    current_state.setdefault("labeled_documents", {})
    current_state["labeled_documents"][label] = {
        'filename': file.filename,
        'content': content,
        'file_type': file_ext,
        'label': label
    }
    
    # Also add to all_documents for compatibility
    current_state.setdefault("all_documents", [])
    current_state['all_documents'].append({
        'filename': file.filename,
        'content': content,
        'file_type': file_ext,
        'label': label
    })
    
    # Set doc_content to a placeholder for labeled file workflows
    # This ensures compatibility with existing validation checks
    if not current_state.get("doc_content"):
        current_state["doc_content"] = f"Labeled file upload: {label}"
    
    return {
        "success": True,
        "filename": file.filename,
        "file_type": file_ext,
        "label": label,
        "word_count": len(content.split()),
        "char_count": len(content)
    }


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process document - supports multiple file types"""
    global current_state

    # Read file
    content_bytes = await file.read()
    
    # Detect file type from filename
    file_ext = Path(file.filename).suffix.lower().lstrip('.')
    
    # Map file type to default canvas type
    default_canvas_type = canvas_types_config.get('file_type_mappings', {}).get(file_ext, 'text_editor')
    
    # Ensure optional collections exist
    current_state.setdefault("selected_options", {})
    current_state.setdefault("all_documents", [])
    current_state.setdefault("uploaded_excel_files", [])
    current_state.setdefault("labeled_documents", {})

    # Handle Excel files differently
    if file_ext in ['xlsx', 'xls']:
        # Save Excel file temporarily for later processing
        import tempfile as tf
        temp_dir = Path(tf.gettempdir()) / "ink_studio_uploads"
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / f"{file.filename.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        file_path.write_bytes(content_bytes)
        
        # Read Excel to get column headers
        import pandas as pd
        try:
            df = pd.read_excel(file_path)
            column_headers = df.columns.tolist()
        except Exception:
            column_headers = []
        
        # Store file path for dual upload processing
        current_state['uploaded_excel_files'].append({
            'path': str(file_path),
            'filename': file.filename,
            'headers': column_headers
        })
        
        # If this is the second Excel file, prepare for dual processing
        if len(current_state['uploaded_excel_files']) == 2:
            current_state['file1_path'] = current_state['uploaded_excel_files'][0]['path']
            current_state['file2_path'] = current_state['uploaded_excel_files'][1]['path']
            current_state['file1_name'] = current_state['uploaded_excel_files'][0]['filename']
            current_state['file2_name'] = current_state['uploaded_excel_files'][1]['filename']
            current_state['doc_content'] = f"Dual upload: {current_state['file1_name']} and {current_state['file2_name']}"
        
        current_state["file_type"] = file_ext
        current_state["default_canvas_type"] = default_canvas_type
        
        return {
            "success": True,
            "filename": file.filename,
            "file_type": file_ext,
            "file_path": str(file_path),
            "default_canvas_type": default_canvas_type,
            "column_headers": column_headers
        }
    else:
        # Extract content for Word/text/markdown/PDF documents
        if file_ext == 'docx':
            content, template = dp.extract_content_and_style(content_bytes)
        elif file_ext == 'pdf':
            content = dp.extract_pdf_content(content_bytes)
            template = None
        elif file_ext in ['txt', 'md']:
            # Handle text and markdown files
            content = content_bytes.decode('utf-8', errors='ignore')
            template = None
        else:
            # Fallback for other file types
            try:
                content = content_bytes.decode('utf-8', errors='ignore')
            except:
                content = "Unable to extract text content from file"
            template = None
        
        current_state["doc_content"] = content
        current_state["doc_template"] = template
        current_state["file_type"] = file_ext
        current_state["default_canvas_type"] = default_canvas_type
        
        # Store in all_documents list for multi-file workflows
        current_state['all_documents'].append({
            'filename': file.filename,
            'content': content,
            'file_type': file_ext
        })
        
        return {
            "success": True,
            "filename": file.filename,
            "file_type": file_ext,
            "default_canvas_type": default_canvas_type,
            "word_count": len(content.split()),
            "char_count": len(content)
        }


@app.post("/api/upload-dual")
async def upload_dual_documents(file1: UploadFile = File(...), file2: UploadFile = File(...)):
    """Upload two Excel files for alignment"""
    global current_state
    
    # Read both files
    content_bytes1 = await file1.read()
    content_bytes2 = await file2.read()
    
    # Detect file types
    file_ext1 = Path(file1.filename).suffix.lower().lstrip('.')
    file_ext2 = Path(file2.filename).suffix.lower().lstrip('.')
    
    # Validate Excel files
    if file_ext1 not in ['xlsx', 'xls'] or file_ext2 not in ['xlsx', 'xls']:
        return {
            "success": False,
            "error": "Both files must be Excel files (.xlsx or .xls)"
        }
    
    # Save files temporarily
    import tempfile as tf
    temp_dir = Path(tf.gettempdir()) / "ink_studio_uploads"
    temp_dir.mkdir(exist_ok=True)
    
    file1_path = temp_dir / f"file1_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext1}"
    file2_path = temp_dir / f"file2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext2}"
    
    file1_path.write_bytes(content_bytes1)
    file2_path.write_bytes(content_bytes2)
    
    # Store file paths in current state
    current_state["file1_path"] = str(file1_path)
    current_state["file2_path"] = str(file2_path)
    current_state["file1_name"] = file1.filename
    current_state["file2_name"] = file2.filename
    current_state["file_type"] = "xlsx"
    current_state["default_canvas_type"] = "alignment_viewer"
    current_state["doc_content"] = f"Dual upload: {file1.filename} and {file2.filename}"
    
    return {
        "success": True,
        "file1_name": file1.filename,
        "file2_name": file2.filename,
        "file_type": "xlsx",
        "default_canvas_type": "alignment_viewer"
    }

# ------------------------------
# STREAMING (SSE) FOR TRANSFORMATIONS
# ------------------------------
@app.get("/api/stream/{transformation_key}")
async def stream_transformation(
    transformation_key: str,
    request: Request,
    start_from_step: int = 0,
    edited_output: str = "",
    options: str = ""
):
    """Stream transformation results using Server-Sent Events
    
    Args:
        transformation_key: The transformation to run
        start_from_step: Step index to start from (for re-runs). Default: 0
        edited_output: Edited content from previous step (for re-runs). Default: ""
    """
    
    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events as transformation progresses"""
        global current_state
        
        if not agent:
            yield json.dumps({'type': 'error', 'message': 'AI agent not initialized. Please check API key.'})
            return
        
        # Check if we have either traditional doc_content OR labeled documents
        has_traditional_upload = current_state.get("doc_content") is not None
        has_labeled_uploads = len(current_state.get("labeled_documents", {})) > 0
        
        if not has_traditional_upload and not has_labeled_uploads:
            yield json.dumps({'type': 'error', 'message': 'No document uploaded'})
            return
        
        current_state.setdefault("selected_options", {})
        current_state.setdefault("all_documents", [])
        
        transform_info = pm.get_transformation_by_key(transformation_key)
        if not transform_info:
            yield json.dumps({'type': 'error', 'message': 'Transformation not found'})
            return
        transformation_options = transform_info.get('options', {})

        # Parse user-selected options (if provided)
        try:
            selected_options = json.loads(options) if options else {}
        except json.JSONDecodeError:
            selected_options = {}

        # Persist selected options in global state for reference
        current_state["selected_options"] = selected_options
        
        # Send initial step status
        for i, step in enumerate(transform_info['steps']):
            yield json.dumps({
                'type': 'step_status',
                'step': i,
                'status': 'pending',
                'name': step['step_name'],
                'step_type': step.get('step_type', 'llm_prompt')
            })
            await asyncio.sleep(0.1)
        
        # Process each step using the tool registry
        step_results = []
        import time
        
        # If re-running from a specific step, restore previous results and use edited output
        if start_from_step > 0 and edited_output:
            # Restore step results up to start_from_step
            for i in range(start_from_step):
                if i in current_state.get("step_outputs", {}):
                    step_results.append(current_state["step_outputs"][i].get('output', ''))
                else:
                    step_results.append('')
            
            # Use edited output as the "previous output" for the step we're starting from
            if start_from_step > 0:
                step_results[start_from_step - 1] = edited_output
        
        for i, step in enumerate(transform_info['steps']):
            # Skip steps before start_from_step (they're already done)
            if i < start_from_step:
                yield json.dumps({
                    'type': 'step_status',
                    'step': i,
                    'status': 'completed',
                    'name': step['step_name'],
                    'step_type': step.get('step_type', 'llm_prompt')
                })
                continue
            
            # Update status to processing
            yield json.dumps({
                'type': 'step_status',
                'step': i,
                'status': 'processing',
                'name': step['step_name'],
                'step_type': step.get('step_type', 'llm_prompt')
            })
            
            # Build step history (outputs from prior steps in order)
            step_history = [
                {
                    'step_index': idx,
                    'step_name': transform_info['steps'][idx]['step_name'],
                    'step_type': transform_info['steps'][idx].get('step_type', 'llm_prompt'),
                    'output': step_results[idx]
                }
                for idx in range(len(step_results))
            ]

            # Prepare context for tool execution
            context = {
                'document_content': current_state["doc_content"],
                'previous_output': step_results[i-1] if i > 0 else "",
                'step_index': i,
                'total_steps': len(transform_info['steps']),
                'user_options': selected_options,
                'user_option_meta': transformation_options,
                'file1_path': current_state.get('file1_path'),
                'file2_path': current_state.get('file2_path'),
                'all_documents': current_state.get('all_documents', []),
                'labeled_documents': current_state.get('labeled_documents', {}),
                'parameters': step.get('parameters', {}),
                'step_history': step_history,
                'step_history_dict': {h['step_index']: h for h in step_history}
            }
            
            # Track streaming updates with timestamps
            last_update = {'text': '', 'time': time.time()}
            
            def streaming_callback(text: str):
                # Store the latest text
                last_update['text'] = text
                last_update['time'] = time.time()
            
            try:
                # Execute step using appropriate tool in a separate task
                # This allows us to periodically check for updates
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        agent.tool_registry.execute_step,
                        step=step,
                        context=context,
                        streaming_callback=streaming_callback
                    )
                    
                    # Poll for streaming updates while task is running
                    last_sent = ""
                    while not future.done():
                        current_text = last_update['text']
                        if current_text and current_text != last_sent:
                            yield json.dumps({'type': 'stream', 'step': i, 'text': current_text})
                            last_sent = current_text
                        await asyncio.sleep(0.1)  # Check every 100ms
                    
                    # Get final result
                    output = future.result()
                
                # Send final output to ensure frontend has complete text
                yield json.dumps({'type': 'stream', 'step': i, 'text': output})
                
                # Store result
                step_results.append(output)
                current_state["step_outputs"][i] = {
                    'step_name': step['step_name'],
                    'step_type': step.get('step_type', 'llm_prompt'),
                    'output': output,
                    'step_index': i
                }
                
                # Mark step complete
                yield json.dumps({
                    'type': 'step_status',
                    'step': i,
                    'status': 'completed',
                    'name': step['step_name'],
                    'step_type': step.get('step_type', 'llm_prompt')
                })
                
            except Exception as e:
                error_msg = f"Error in step '{step['step_name']}': {str(e)}"
                yield json.dumps({'type': 'error', 'message': error_msg, 'step': i})
                # Continue with error message as output
                step_results.append(error_msg)
        
        # Send completion
        yield json.dumps({'type': 'complete', 'message': 'All steps completed!'})
    
    return EventSourceResponse(event_generator())


@app.post("/api/session/reset")
async def reset_session():
    """Reset server-side state and clear RAG sessions before new workflow"""
    reset_current_state(clear_rag=True)
    return {"success": True, "message": "Session reset successfully"}


@app.post("/api/chat")
async def chat_with_documents(data: dict):
    """Handle chat queries using RAG"""
    from agentic_tools import rag_chat
    
    session_id = data.get("session_id")
    question = data.get("question", "")
    
    if not session_id:
        return {"error": "No chat session found"}
    
    if not question:
        return {"error": "No question provided"}
    
    # Get answer from RAG system
    result = rag_chat(session_id, question)
    
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "question": question
    }


@app.post("/api/export")
async def export_document(data: dict):
    """Export edited content to Word document"""
    global current_state
    
    edited_text = data.get("text", "")
    
    if not current_state["doc_template"]:
        return {"error": "No template available"}
    
    # Generate document
    doc_bytes = dp.create_document_with_style(edited_text, current_state["doc_template"])
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
    temp_file.write(doc_bytes)
    temp_file.close()
    
    return FileResponse(
        temp_file.name,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename='transformed_document.docx'
    )

# -----------------------------------------------------------------------------------
# Generic Multiplexer per tool (for any tool registered in app_host.py)
# -----------------------------------------------------------------------------------

router = APIRouter()

def _get_registry():
    try:
        if 'agent' in globals() and getattr(agent, "tool_registry", None):
            return agent.tool_registry
    except Exception:
        pass
    # If ToolRegistry is unavailable, return None
    if ToolRegistry is None:
        return None
    return ToolRegistry(api_key=OPENAI_API_KEY)

@router.get("/api/tools")
async def list_registered_tools():
    try:
        registry = _get_registry()
        if not registry or not getattr(registry, "tools", None):
            return { "success": True, "count": 0, "tools": [] }

        tools = []
        for name in getattr(registry, "tools", {}).keys():
            tools.append(build_descriptor_from_contract(name))
        return { "success": True, "count": len(tools), "tools": tools }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing tools: {e}")

def _resolve_tool_id(payload: dict) -> str:
    # Resolve tool id from root keys
    for k in ("key", "name"):
        v = payload.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

@router.get("/health", include_in_schema=False)
async def rest_health():
    # Health check for the REST app (in addition to any MCP host health)
    return {"status": "ok", "app": "REST", "message": "FastAPI REST app mounted"}


@router.post("/api/tool/execute")
async def execute_tool_generic(payload: Dict[str, Any], request: Request):

    # 0) If wrapped under "payload", unwrap the 'payload' wrapper
    # payload = _unwrap(payload)
    payload = payload.get("payload", payload)

    # 1) Resolve tool id from root / metadata / headers (simplified here to root)
    tool_id = (payload.get("key") or payload.get("name") or "").strip()
    if not tool_id:
        raise HTTPException(status_code=400, detail="Missing 'key' (skillId) or 'name' (skillName)")

    tool_args = payload.get("arguments", {}) or {}
    tool_call_id = payload.get("tool_call_id")
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))

    # 2) Look up the tool
    registry = _get_registry()
    tool = registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_id}' not found")

    # 3) Adapt inputs (files or in-memory)
    context = adapt_inputs(tool_id, tool_args)

    # 4) Execute the tool
    try:
        result = await asyncio.wait_for(asyncio.to_thread(tool.execute, context, None), timeout=90)
        return JSONResponse(status_code=200, content={
            "success": True,
            "tool_call_id": tool_call_id,
            "output": result,
            "meta": { "tool": tool_id, "request_id": request_id }
        })
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Timeout during tool execution")
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

# Register router
app.include_router(router)




