"""
Demo Session API Routes
Provides REST endpoints to control live demo recording sessions,
log user & agent events, and generate & download session PDF audit reports.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Form, Header, Request, Body
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from demo_session_engine import demo_session_manager, SESSIONS_DIR

router = APIRouter(prefix="/api/demo-session", tags=["Live Demo Session"])


class LogEventModel(BaseModel):
    actor: str
    action_type: str
    step: str = "General"
    level: str = "INFO"
    message: str
    details: Optional[Any] = None


@router.post("/start")
async def start_demo_session(
    session_name: str = Form("Live Demo Session"),
    api_key: Optional[str] = Form(None),
    brand_url: Optional[str] = Form(""),
    x_api_key: Optional[str] = Header(None),
):
    """Start recording a new live demo session."""
    effective_key = api_key or x_api_key
    session = demo_session_manager.start_session(
        session_name=session_name,
        api_key=effective_key,
        brand_url=brand_url,
    )
    return {
        "status": "active",
        "session_id": session["session_id"],
        "session_name": session["session_name"],
        "api_key_masked": session["api_key_masked"],
        "started_at": session["start_time_iso"],
    }


@router.get("/status")
async def get_demo_session_status():
    """Retrieve active session status, duration, and event counts."""
    return demo_session_manager.get_session_status()


@router.post("/log")
async def log_demo_event(req: LogEventModel):
    """Log an interaction step taken by the user or an agent."""
    if not demo_session_manager.is_active():
        return {"logged": False, "reason": "No active demo session"}

    ev = demo_session_manager.log_event(
        actor=req.actor,
        action_type=req.action_type,
        step=req.step,
        level=req.level,
        message=req.message,
        details=req.details,
    )
    return {"logged": True, "event": ev}


@router.post("/end")
async def end_demo_session():
    """End the active demo session, compile all events, and generate a PDF audit report."""
    if not demo_session_manager.is_active():
        raise HTTPException(status_code=400, detail="No active demo session is currently running.")

    result = await demo_session_manager.end_session()
    return result


@router.get("/download/{session_id}")
async def download_session_pdf(session_id: str):
    """Download the generated PDF audit report for a completed session."""
    pdf_path = SESSIONS_DIR / f"Live_Demo_Session_{session_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Session PDF report not found.")

    return FileResponse(
        path=str(pdf_path),
        filename=f"Live_Demo_Session_{session_id}.pdf",
        media_type="application/pdf",
    )


# ---------------------------------------------------------------------------
# Granular Backend & Prompt Telemetry Routes (Tech Team Inspection)
# ---------------------------------------------------------------------------
from backend_tracer import backend_tracer


@router.get("/tech-trace/events")
async def get_tech_trace_events(category: Optional[str] = None, limit: int = 100):
    """Retrieve granular backend trace events including exact prompts, model responses, and tool calls."""
    events = backend_tracer.get_events(limit=limit, category=category)
    return {
        "status": "success",
        "count": len(events),
        "events": events,
    }


@router.get("/tech-trace/export-json")
async def export_tech_trace_json():
    """Export complete backend telemetry and prompt traces as JSON for engineering teams."""
    events = backend_tracer.get_events(limit=500)
    return JSONResponse(
        content={"telemetry_version": "2.4", "exported_at": str(datetime.now()), "events": events},
        headers={"Content-Disposition": "attachment; filename=backend_telemetry_traces.json"},
    )


@router.get("/tech-trace/export-pdf")
async def export_tech_trace_pdf():
    """Generate and download the complete Technical Architecture & Prompt Trace Audit PDF."""
    pdf_path = await backend_tracer.generate_tech_audit_pdf()
    return FileResponse(
        path=str(pdf_path),
        filename=pdf_path.name,
        media_type="application/pdf",
    )
