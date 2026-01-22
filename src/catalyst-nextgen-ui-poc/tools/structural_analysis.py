
from typing import Dict, Any, Optional, Callable, List
from tools.base import AgenticTool
import re
import json

class StructuralAnalysisTool(AgenticTool):
    """Analyze and compare document structure"""

    def __init__(self):
        super().__init__("structural_analysis", "Compare document outlines and hierarchies")

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Analyze structural differences between documents"""
        try:
            labeled_docs = context.get('labeled_documents', {})
            all_docs = context.get('all_documents', [])

            if labeled_docs and len(labeled_docs) >= 2:
                doc1_content = list(labeled_docs.values())[0].get('content', '')
                doc2_content = list(labeled_docs.values())[1].get('content', '')
                doc1_name = list(labeled_docs.keys())[0]
                doc2_name = list(labeled_docs.keys())[1]
            elif all_docs and len(all_docs) >= 2:
                doc1_content = all_docs[0].get('content', '')
                doc2_content = all_docs[1].get('content', '')
                doc1_name = all_docs[0].get('filename', 'Document 1')
                doc2_name = all_docs[1].get('filename', 'Document 2')
            else:
                return "Error: Two documents required"

            if streaming_callback:
                streaming_callback("🏗️ Analyzing document structures...")

            structure1 = self._extract_structure(doc1_content)
            structure2 = self._extract_structure(doc2_content)

            if streaming_callback:
                streaming_callback("🏗️ Comparing hierarchies...")

            structural_changes = self._compare_structures(structure1, structure2)
            reordered_sections = self._detect_reordering(structure1, structure2)

            result = {
                'doc1_structure': structure1,
                'doc2_structure': structure2,
                'doc1_name': doc1_name,
                'doc2_name': doc2_name,
                'added_sections': structural_changes['added'],
                'removed_sections': structural_changes['removed'],
                'modified_sections': structural_changes['modified'],
                'reordered_sections': reordered_sections,
                'hierarchy_changes': structural_changes['hierarchy_changes'],
                'summary': {
                    'total_sections_doc1': len(structure1),
                    'total_sections_doc2': len(structure2),
                    'sections_added': len(structural_changes['added']),
                    'sections_removed': len(structural_changes['removed']),
                    'sections_modified': len(structural_changes['modified']),
                    'sections_reordered': len(reordered_sections)
                }
            }

            output = f"STRUCTURAL_ANALYSIS:{json.dumps(result)}"

            if streaming_callback:
                streaming_callback(f"✅ Structural analysis complete!\n\n**Summary:**\n- {len(structural_changes['added'])} sections added\n- {len(structural_changes['removed'])} sections removed\n- {len(structural_changes['modified'])} sections modified\n- {len(reordered_sections)} sections reordered")

            return output

        except Exception as e:
            error_msg = f"**Structural analysis error:** {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg

    def _extract_structure(self, content: str) -> List[Dict]:
        """Extract hierarchical structure from document"""
        structure = []
        lines = content.split('\n')

        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue

            level = self._detect_heading_level(line_stripped)
            if level > 0:
                structure.append({
                    'line_number': i,
                    'level': level,
                    'text': line_stripped,
                    'type': 'heading',
                    'normalized': self._normalize_heading(line_stripped)
                })

        return structure

    def _detect_heading_level(self, text: str) -> int:
        """Detect heading level (0 = not a heading)"""
        match = re.match(r'^(#{1,6})\s+', text)
        if match:
            return len(match.group(1))
        match = re.match(r'^((\d+\.)+)\s+', text)
        if match:
            return match.group(1).count('.')
        if text.isupper() and len(text) < 100:
            return 1
        if text.istitle() and len(text) < 80 and not text.endswith(('.', '!', '?', ',')):
            return 2
        return 0

    def _normalize_heading(self, text: str) -> str:
        """Normalize heading text for comparison"""
        text = re.sub(r'^#{1,6}\s+', '', text)
        text = re.sub(r'^(\d+\.)+\s+', '', text)
        return text.lower().strip()

    def _compare_structures(self, struct1: List[Dict], struct2: List[Dict]) -> Dict:
        """Compare two document structures"""
        map1 = {s['normalized']: s for s in struct1}
        map2 = {s['normalized']: s for s in struct2}

        keys1 = set(map1.keys())
        keys2 = set(map2.keys())

        added = [map2[k] for k in keys2 - keys1]
        removed = [map1[k] for k in keys1 - keys2]

        modified = []
        hierarchy_changes = []

        for key in keys1 & keys2:
            if map1[key]['level'] != map2[key]['level']:
                hierarchy_changes.append({
                    'heading': key,
                    'old_level': map1[key]['level'],
                    'new_level': map2[key]['level'],
                    'change': 'promoted' if map2[key]['level'] < map1[key]['level'] else 'demoted'
                })
                modified.append(map2[key])

        return {
            'added': added, 
            'removed': removed, 
            'modified': modified, 
            'hierarchy_changes': hierarchy_changes
        }

    def _detect_reordering(self, struct1: List[Dict], struct2: List[Dict]) -> List[Dict]:
        """Detect sections that were reordered"""
        norm1 = [s['normalized'] for s in struct1]
        norm2 = [s['normalized'] for s in struct2]

        reordered = []
        for norm in set(norm1) & set(norm2):
            idx1 = norm1.index(norm)
            idx2 = norm2.index(norm)
            if abs(idx1 - idx2) > 1:
                reordered.append({
                    'heading': norm, 
                    'old_position': idx1, 
                    'new_position': idx2, 
                    'moved_by': idx2 - idx1
                })

        return reordered
