"""
Prompt Chain Manager
Handles loading, saving, and managing prompt chains from JSON storage
"""

import json
import os
from typing import Dict, List, Optional


class PromptManager:
    """Manages prompt chains stored in JSON format"""
    
    def __init__(self, prompts_file: str = "prompts.json"):
        self.prompts_file = prompts_file
        self.prompts = self.load_prompts()
    
    def load_prompts(self) -> Dict:
        """Load prompts from JSON file"""
        if os.path.exists(self.prompts_file):
            with open(self.prompts_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_prompts(self) -> bool:
        """Save prompts to JSON file"""
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving prompts: {e}")
            return False
    
    def get_transformation_names(self) -> List[str]:
        """Get list of available transformation names for dropdown"""
        return [info['name'] for info in self.prompts.values()]
    
    def get_transformation_by_name(self, display_name: str) -> Optional[Dict]:
        """Get transformation config by display name"""
        for key, info in self.prompts.items():
            if info['name'] == display_name:
                return {'key': key, **info}
        return None
    
    def get_transformation_by_key(self, key: str) -> Optional[Dict]:
        """Get transformation config by key"""
        if key in self.prompts:
            return {'key': key, **self.prompts[key]}
        return None
    
    def add_transformation(self, key: str, name: str, description: str, steps: List[Dict], options: Optional[Dict] = None) -> bool:
        """Add a new transformation"""
        if key in self.prompts:
            return False
        
        self.prompts[key] = {
            'name': name,
            'description': description,
            'steps': steps,
            'options': options or {}
        }
        return self.save_prompts()
    
    def update_transformation(self, key: str, name: str, description: str, steps: List[Dict], options: Optional[Dict] = None) -> bool:
        """Update an existing transformation"""
        if key not in self.prompts:
            return False
        
        updated = {
            'name': name,
            'description': description,
            'steps': steps
        }
        if options is not None:
            updated['options'] = options
        else:
            existing_options = self.prompts[key].get('options')
            if existing_options is not None:
                updated['options'] = existing_options
        self.prompts[key] = updated
        return self.save_prompts()
    
    def delete_transformation(self, key: str) -> bool:
        """Delete a transformation"""
        if key in self.prompts:
            del self.prompts[key]
            return self.save_prompts()
        return False
    
    def get_all_transformations(self) -> Dict:
        """Get all transformations"""
        return self.prompts

