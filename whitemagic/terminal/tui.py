"""TUI (Text User Interface) for approval workflow."""
from typing import Optional
from .models import ApprovalRequest, ApprovalResponse

class SimpleTUI:
    """Simple TUI approver (Rich-based TUI for future)."""
    
    def __init__(self):
        self.enabled = True
    
    def request_approval(self, request: ApprovalRequest) -> ApprovalResponse:
        """Request approval via terminal prompt."""
        print(f"\n{'='*60}")
        print(f"🔐 APPROVAL REQUIRED")
        print(f"{'='*60}")
        print(f"Command: {request.command}")
        print(f"Mode: {request.mode.value}")
        if request.cwd:
            print(f"CWD: {request.cwd}")
        if request.preview:
            print(f"\nPreview:")
            print(request.preview)
        print(f"{'='*60}")
        
        while True:
            response = input("Approve? [y/N]: ").strip().lower()
            if response in ['y', 'yes']:
                return ApprovalResponse(approved=True, reason="User approved")
            elif response in ['n', 'no', '']:
                return ApprovalResponse(approved=False, reason="User denied")
            print("Please enter 'y' or 'n'")
