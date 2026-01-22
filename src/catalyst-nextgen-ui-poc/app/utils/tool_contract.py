
# app/utils/tool_contract.py
from typing import Dict, Any
from config import MCP_BASE_URL, MCP_LOGICAL_NAME
from app.utils.mcp_uri import build_mcp_uri


# Modular catalog (contracts per skill)
# NOTE:
# - inputFileRequirements describes ONLY files uploaded to THIS endpoint.
# - Non-file arguments are listed under entryCriteria.requiredInputs.
CONTRACTS: Dict[str, Dict[str, Any]] = {
    "llm_prompt": {
        "skillName": "LLM Prompt",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No file uploads; provide 'prompt' and optional context"},
        "entryCriteria": {"requiredInputs": ["prompt", "document_content", "previous_output",
                                             "template_variables", "user_options", "labeled_documents", "step_history"],
                          "inputFormats": ["txt","json"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": True
    },
    "web_search": {
        "skillName": "Web Search",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; provide 'search_query'"},
        "entryCriteria": {"requiredInputs": ["search_query", "max_results"], "inputFormats": ["txt","int"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "document_analysis": {
        "skillName": "Document Analysis",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; provide 'document_content'"},
        "entryCriteria": {"requiredInputs": ["document_content", "analysis_type"], "inputFormats": ["txt"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "fact_check": {
        "skillName": "Fact Check",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; consumes 'previous_output'"},
        "entryCriteria": {"requiredInputs": ["previous_output"], "inputFormats": ["txt"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "content_enrichment": {
        "skillName": "Content Enrichment",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; consumes 'previous_output' + 'enrichment_topic'"},
        "entryCriteria": {"requiredInputs": ["previous_output", "enrichment_topic"], "inputFormats": ["txt"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "data_validation": {
        "skillName": "Data Validation",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; consumes 'previous_output'"},
        "entryCriteria": {"requiredInputs": ["previous_output", "validation_type"], "inputFormats": ["txt"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "podcast_generator": {
        "skillName": "Podcast Generator",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "No files; consumes text and outputs mp3"},
        "entryCriteria": {"requiredInputs": ["previous_output", "document_content", "parameters"], "inputFormats": ["txt","json"]},
        "exitCriteria": {"outputFormat": "mp3", "guarantees": ["Audio file generated","Voice selection applied"]},
        "requiresPrompt": False
    },
    "alignment": {
        "skillName": "Excel Column Alignment",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "Exactly 2 Excel files (xlsx/xls)"},
        "entryCriteria": {"requiredInputs": ["file1_path","file2_path","user_options"], "inputFormats": ["xlsx","xls","json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Pairs aligned semantically","Similarity statistics"]},
        "requiresPrompt": False
    },
    "compare_analysis": {
        "skillName": "Compare Analysis",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "Consumes ALIGNMENT_RESULT"},
        "entryCriteria": {"requiredInputs": ["previous_output"], "inputFormats": ["json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Adds analysis per matched pair"]},
        "requiresPrompt": False
    },
    "rag_setup": {
        "skillName": "RAG Setup",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "Provide 'all_documents' [{content, filename}]"},
        "entryCriteria": {"requiredInputs": ["all_documents"], "inputFormats": ["json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Vectorstore ready","Session ID returned"]},
        "requiresPrompt": False
    },
    "redline_diff": {
        "skillName": "Redline Diff",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "Two plaintext documents OR provide 'labeled_documents'/'all_documents'"},
        "entryCriteria": {"requiredInputs": ["doc1_path","doc2_path","labeled_documents","all_documents","doc1_label","doc2_label"],
                          "inputFormats": ["txt","md","json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Word-level markup","Change statistics"]},
        "requiresPrompt": False
    },
    "enhanced_diff": {
        "skillName": "Enhanced Diff",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "Two plaintext documents OR provide 'labeled_documents'/'all_documents'"},
        "entryCriteria": {"requiredInputs": ["doc1_path","doc2_path","labeled_documents","all_documents"], "inputFormats": ["txt","md","json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Visual markup","Statistics","Sentence-level changes"]},
        "requiresPrompt": False
    },
    "structural_analysis": {
        "skillName": "Structural Analysis",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "Two plaintext documents OR provide 'labeled_documents'/'all_documents'"},
        "entryCriteria": {"requiredInputs": ["doc1_path","doc2_path","labeled_documents","all_documents"], "inputFormats": ["txt","md","json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Hierarchy comparison","Reordering detection"]},
        "requiresPrompt": False
    },
    "semantic_diff": {
        "skillName": "Semantic Diff",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "EITHER provide CHUNKING_RESULT OR two plaintext docs (adapter chunks on-the-fly)"},
        "entryCriteria": {"requiredInputs": ["previous_output","doc1_path","doc2_path","doc1_content","doc2_content"], "inputFormats": ["json","txt","md"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Semantic matches","Moved/paraphrased/new/removed chunks"]},
        "requiresPrompt": False
    },
    "smart_chunker": {
        "skillName": "Smart Chunker",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 2, "maxFiles": 2, "exactFiles": 2,
                                  "description": "Two plaintext documents OR provide 'labeled_documents'/'all_documents'"},
        "entryCriteria": {"requiredInputs": ["doc1_path","doc2_path","labeled_documents","all_documents"], "inputFormats": ["txt","md","json"]},
        "exitCriteria": {"outputFormat": "json", "guarantees": ["Strategy","Chunks","Embeddings"]},
        "requiresPrompt": False
    },
    "update_derivative": {
        "skillName": "Update Derivative",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "Provide labeled_documents {original_primary,current_derivative,updated_primary}"},
        "entryCriteria": {"requiredInputs": ["labeled_documents","previous_output"], "inputFormats": ["json","txt"]},
        "exitCriteria": {"outputFormat": "txt", "guarantees": ["Updated derivative consistent with transformation pattern"]},
        "requiresPrompt": False
    },
    "comparison_summary": {
        "skillName": "Comparison Summary",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "Provide 'step_history' (array of prior outputs)"},
        "entryCriteria": {"requiredInputs": ["step_history"], "inputFormats": ["json"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
    "derivative_analysis": {
        "skillName": "Derivative Analysis",
        "skillType": "processing",
        "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0,
                                  "description": "Provide labeled_documents {original_primary,current_derivative}"},
        "entryCriteria": {"requiredInputs": ["labeled_documents"], "inputFormats": ["json"]},
        "exitCriteria": {"outputFormat": "txt"},
        "requiresPrompt": False
    },
}

def build_descriptor_from_contract(skill_id: str) -> Dict[str, Any]:
    c = CONTRACTS.get(skill_id)
    if not c:
        # Minimal fallback (should not happen if CONTRACTS is kept in sync)
        c = {
            "skillName": skill_id.replace("_", " ").title(),
            "skillType": "processing",
            "inputFileRequirements": {"minFiles": 0, "maxFiles": 0, "exactFiles": 0, "description": "No files"},
            "entryCriteria": {"requiredInputs": [], "inputFormats": ["*"]},
            "exitCriteria": {"outputFormat": "txt"},
            "requiresPrompt": False
        }
    return {
        "skillId": skill_id,
        "skillName": c["skillName"],
        "skillType": c["skillType"],
        "mcpUri": build_mcp_uri(MCP_BASE_URL, skill_id, logical_name=MCP_LOGICAL_NAME),
        "inputFileRequirements": c["inputFileRequirements"],
        "entryCriteria": c["entryCriteria"],
        "exitCriteria": c["exitCriteria"],
        "requiresPrompt": c["requiresPrompt"],
        "executionEndpoint": "/api/tool/execute",
    }




