"""Template manager for loading and managing memory templates."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional

from .schema import TemplateSchema, TemplateField


class TemplateManager:
    """Manages memory templates."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager.
        
        Args:
            templates_dir: Directory containing templates. 
                          Uses built-in templates if None.
        """
        if templates_dir is None:
            # Use built-in templates
            self.templates_dir = Path(__file__).parent / "builtin"
        else:
            self.templates_dir = Path(templates_dir)
        
        self._templates: Dict[str, TemplateSchema] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load all templates from directory."""
        if not self.templates_dir.exists():
            return
        
        for template_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(template_file, "r") as f:
                    data = yaml.safe_load(f)
                
                # Parse fields
                fields = []
                for field_name, field_spec in data.get("fields", {}).items():
                    if isinstance(field_spec, str):
                        # Simple format: "field_name: string (required)"
                        parts = field_spec.split()
                        field_type = parts[0]
                        required = "(required)" in field_spec
                        fields.append(TemplateField(
                            name=field_name,
                            type=field_type,
                            required=required
                        ))
                    elif isinstance(field_spec, dict):
                        # Full format with description, etc
                        fields.append(TemplateField(
                            name=field_name,
                            **field_spec
                        ))
                
                # Create template
                template = TemplateSchema(
                    name=data.get("name", template_file.stem),
                    description=data.get("description", ""),
                    memory_type=data.get("type", "long_term"),
                    tags_required=data.get("tags_required", []),
                    tags_suggested=data.get("suggested_tags", []),
                    fields=fields,
                    content_template=data.get("content_template")
                )
                
                self._templates[template.name] = template
                
            except Exception as e:
                # Skip invalid templates
                print(f"Warning: Could not load template {template_file}: {e}")
    
    def list_templates(self) -> List[str]:
        """Get list of available template names."""
        return sorted(self._templates.keys())
    
    def get_template(self, name: str) -> Optional[TemplateSchema]:
        """Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template schema or None if not found
        """
        return self._templates.get(name)
    
    def has_template(self, name: str) -> bool:
        """Check if template exists."""
        return name in self._templates
