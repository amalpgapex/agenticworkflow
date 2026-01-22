
# app/utils/skill_adapters.py
from typing import Dict, Any, Optional
from tools.registry import ToolRegistry
from config import OPENAI_API_KEY

def _read_text(path: Optional[str]) -> str:
    if not path: return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def adapt_inputs(tool_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a context ready to be passed to tool.execute(...) according to each skill.
    Does not modify legacy logic; it only prepares the appropriate data for the modular mode.
    """
    ctx: Dict[str, Any] = {}

    if tool_id == "llm_prompt":
        # Prompt is required; the rest is optional.
        ctx.update({
            "prompt": args.get("prompt", ""),
            "document_content": args.get("document_content", _read_text(args.get("document_path"))),
            "previous_output": args.get("previous_output", ""),
            "template_variables": args.get("template_variables", []),
            "user_options": args.get("user_options", {}),
            "labeled_documents": args.get("labeled_documents", {}),
            "step_history": args.get("step_history", []),
        })

    elif tool_id == "web_search":
        ctx.update({
            "search_query": args.get("search_query", ""),
            "max_results": args.get("max_results", 5),
        })

    elif tool_id == "document_analysis":
        doc = args.get("document_content", _read_text(args.get("document_path")))
        ctx.update({"document_content": doc, "analysis_type": args.get("analysis_type", "summary")})

    elif tool_id in ("fact_check", "content_enrichment", "data_validation"):
        # All consume previous_output
        ctx.update({
            "previous_output": args.get("previous_output", ""),
            "enrichment_topic": args.get("enrichment_topic"),
            "validation_type": args.get("validation_type", "all"),
        })

    elif tool_id == "podcast_generator":
        ctx.update({
            "previous_output": args.get("previous_output", ""),
            "document_content": args.get("document_content", _read_text(args.get("document_path"))),
            "parameters": args.get("parameters", {"voice": "alloy"}),
        })

    elif tool_id == "alignment":
        ctx.update({
            "file1_path": args.get("file1_path"),
            "file2_path": args.get("file2_path"),
            "user_options": args.get("user_options", {"column1": "0", "column2": "0", "include_diff": "no"}),
        })

    elif tool_id in ("redline_diff", "enhanced_diff", "structural_analysis"):
        # Modular: accepts doc1/doc2 by path or by in-memory content; builds labeled_documents / all_documents
        doc1 = args.get("doc1_content", _read_text(args.get("doc1_path")))
        doc2 = args.get("doc2_content", _read_text(args.get("doc2_path")))
        labeled = args.get("labeled_documents")
        all_docs = args.get("all_documents")
        if not labeled and doc1 and doc2:
            labeled = {
                "document1": {"content": doc1},
                "document2": {"content": doc2}
            }
        if not all_docs and doc1 and doc2:
            all_docs = [
                {"content": doc1, "filename": args.get("doc1_name", "Document 1")},
                {"content": doc2, "filename": args.get("doc2_name", "Document 2")},
            ]
        ctx.update({
            "labeled_documents": labeled or {},
            "all_documents": all_docs or [],
            "doc1_label": args.get("doc1_label", "document1"),
            "doc2_label": args.get("doc2_label", "document2"),
        })

    elif tool_id == "smart_chunker":
        doc1 = args.get("doc1_content", _read_text(args.get("doc1_path")))
        doc2 = args.get("doc2_content", _read_text(args.get("doc2_path")))
        labeled = args.get("labeled_documents")
        all_docs = args.get("all_documents")
        if not all_docs and doc1 and doc2:
            all_docs = [
                {"content": doc1, "filename": args.get("doc1_name", "Document 1")},
                {"content": doc2, "filename": args.get("doc2_name", "Document 2")},
            ]
        ctx.update({"labeled_documents": labeled or {}, "all_documents": all_docs or []})

    elif tool_id == "semantic_diff":
        # Preference: use previous_output when it contains CHUNKING_RESULT
        prev = args.get("previous_output")
        if prev and str(prev).startswith("CHUNKING_RESULT:"):
            ctx.update({"previous_output": prev})
        else:
            # Modular mode: if doc1/doc2 are provided, run smart_chunker internally to generate CHUNKING_RESULT
            doc1 = args.get("doc1_content", _read_text(args.get("doc1_path")))
            doc2 = args.get("doc2_content", _read_text(args.get("doc2_path")))
            if doc1 and doc2:
                reg = ToolRegistry(api_key=OPENAI_API_KEY)
                chunker = reg.get_tool("smart_chunker")
                chunk_ctx = {"all_documents": [
                    {"content": doc1, "filename": args.get("doc1_name", "Document 1")},
                    {"content": doc2, "filename": args.get("doc2_name", "Document 2")},
                ]}
                chunk_res = chunker.execute(chunk_ctx, None)
                ctx.update({"previous_output": chunk_res})
            else:
                ctx.update({"previous_output": ""})

    elif tool_id == "compare_analysis":
        # Requires ALIGNMENT_RESULT in previous_output
        ctx.update({"previous_output": args.get("previous_output", "")})

    elif tool_id == "rag_setup":
        # If all_documents is not provided, attempt to build it from doc_paths (array)
        all_docs = args.get("all_documents")
        if not all_docs and args.get("doc_paths"):
            docs = []
            for p in args.get("doc_paths", []):
                docs.append({"content": _read_text(p), "filename": p})
            all_docs = docs
        ctx.update({"all_documents": all_docs or []})

    elif tool_id == "update_derivative":
        ctx.update({
            "labeled_documents": args.get("labeled_documents", {}),
            "previous_output": args.get("previous_output", ""),
        })

    elif tool_id == "comparison_summary":
        ctx.update({"step_history": args.get("step_history", [])})

    elif tool_id == "derivative_analysis":
        ctx.update({"labeled_documents": args.get("labeled_documents", {})})

    else:
        # Default: passthrough as-is
        ctx.update(args)

    return ctx



    
