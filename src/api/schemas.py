from typing import Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(..., description="Identifiant de conversation (checkpointer)")
    message: str
    code_input: Optional[str] = Field(
        default=None, description="Code source à analyser, si applicable"
    )


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool = Field(..., description="Validation humaine avant rédaction finale")
    edited_scan_result: Optional[dict] = Field(
        default=None, description="Correction manuelle du résultat d'analyse avant rédaction"
    )


class ChatResponse(BaseModel):
    thread_id: str
    status: str  # "interrupted" | "completed"
    current_step: str
    scan_result: Optional[dict] = None
    final_documentation: Optional[str] = None
    last_message: Optional[str] = None
