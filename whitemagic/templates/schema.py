"""Template schema definitions using Pydantic."""

from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field


class TemplateField(BaseModel):
    """Definition of a template field."""
    
    name: str
    type: Literal["string", "list", "dict", "text", "date"]
    required: bool = False
    description: Optional[str] = None
    default: Optional[Any] = None
    placeholder: Optional[str] = None


class TemplateSchema(BaseModel):
    """Schema for memory templates."""
    
    name: str = Field(description="Template name (e.g., 'architecture')")
    description: str = Field(description="What this template is for")
    memory_type: Literal["short_term", "long_term"] = Field(
        default="long_term",
        description="Default memory type"
    )
    tags_required: List[str] = Field(
        default_factory=list,
        description="Tags that must be present"
    )
    tags_suggested: List[str] = Field(
        default_factory=list,
        description="Tags to suggest"
    )
    fields: List[TemplateField] = Field(
        default_factory=list,
        description="Structured fields for this template"
    )
    content_template: Optional[str] = Field(
        default=None,
        description="Markdown template with placeholders"
    )
    
    def validate_content(self, content: Dict[str, Any]) -> List[str]:
        """Validate content against required fields.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        for field in self.fields:
            if field.required and field.name not in content:
                errors.append(f"Missing required field: {field.name}")
        
        return errors
    
    def generate_content(self, fields: Dict[str, Any]) -> str:
        """Generate markdown content from field values.
        
        Args:
            fields: Field name → value mapping
            
        Returns:
            Formatted markdown content
        """
        if self.content_template:
            # Use template with placeholders
            content = self.content_template
            for key, value in fields.items():
                placeholder = f"{{{key}}}"
                if isinstance(value, list):
                    value = "\n".join(f"- {item}" for item in value)
                content = content.replace(placeholder, str(value))
            return content
        else:
            # Generate basic markdown from fields
            lines = []
            for field in self.fields:
                if field.name in fields:
                    value = fields[field.name]
                    lines.append(f"## {field.name.replace('_', ' ').title()}")
                    if isinstance(value, list):
                        for item in value:
                            lines.append(f"- {item}")
                    else:
                        lines.append(str(value))
                    lines.append("")
            return "\n".join(lines)
