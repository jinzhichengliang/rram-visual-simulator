"""
RRAM Visual Simulator — FastAPI API (V1.0).

Unified API integrating all subsystems:
- F0/F1 model switching
- Peripheral circuit info
- Fault diagnosis
- Learning system
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from packages.contracts.types import (
    DeviceProfile, DeviceRanges, DeviceState, DeviceTolerances,
    LogicMap, OperationSpec, OperationType, Polarity, PulseSpec, StackOrientation,
)
from simulator.orchestrator.simulation_orchestrator import SimulationOrchestrator
from simulator.core.peripheral import PeripheralCircuit, SenseAmplifier
from simulator.core.program_verify import ProgramAndVerifyController
from simulator.fault_injection import FaultDetector
from simulator.debug_console import DiagnosticEngine, DiagnosticContext
from simulator.learning_engine import LearningEngine, Prediction, PredictionCategory
from simulator.learning_manager import LearningManager

app = FastAPI(
    title="RRAM Visual Simulator",
    description="Teaching-first interactive RRAM/1T1R visual simulation platform.",
    version="1.0.0-v1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global State ─────────────────────────────────────────────────────

PROFILE = DeviceProfile(
    id="bipolar_teaching_v1", version="1.0.0",
    stackOrientation=StackOrientation.BL_RRAM_NMOS_SL,
    vRramSignConvention="V(top)-V(bottom)",
    setPolarity=Polarity.POSITIVE, resetPolarity=Polarity.NEGATIVE,
    logicMap=LogicMap(LRS=1, HRS=0),
    ranges=DeviceRanges(
        vRead=[0.1, 0.2], vSet=[1.5, 2.5], vReset=[-2.5, -1.5], vForm=[3.0, 4.0],
        rLrs=[10000, 50000], rHrs=[500000, 5000000],
    ),
    complianceUa=50.0,
    tolerances=DeviceTolerances(readDisturbPct=1.0, currentConservationPct=5.0, crossViewAbs=0.001),
)

# Simulation
orchestrator = SimulationOrchestrator(PROFILE, seed=42)
peripheral = PeripheralCircuit(rows=4, cols=4, profile=PROFILE)
sense_amp = SenseAmplifier(PROFILE)
program_verify = ProgramAndVerifyController(PROFILE, max_pulses=10)

# V0.6: Fault diagnosis
fault_detector = FaultDetector()
diagnostic_engine = DiagnosticEngine()

# V0.9: Learning system
learning_engine = LearningEngine(PROFILE)
learning_engine.load_default_scenarios()
learning_manager = LearningManager(PROFILE, user_id="default_user")

# Model selection
current_model = "F0"  # "F0" or "F1"


# ─── Request Models ───────────────────────────────────────────────────

class OperationRequest(BaseModel):
    operation: str
    target: dict[str, int]

class ModelSwitchRequest(BaseModel):
    model: str  # "F0" or "F1"

class PredictionRequest(BaseModel):
    operation: str
    predicted_category: str
    reasoning: str = ""
    confidence: float = 0.5

class NoteRequest(BaseModel):
    scenario_id: str
    content: str
    tags: list[str] = []


# ─── Core Endpoints ───────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "phase": "v1.0", "model": current_model}

@app.get("/")
async def root():
    return {"service": "RRAM Visual Simulator", "version": "1.0.0-v1.0"}

@app.post("/api/reset")
async def reset_simulation():
    orchestrator.reset()
    return {"status": "ok"}

@app.get("/api/state")
async def get_state():
    return {
        "deviceState": orchestrator.get_current_state().value,
        "frameCount": len(orchestrator.get_frame_history()),
        "model": current_model,
        "peripheral": {
            "sense_reference_ua": sense_amp.reference_ua,
            "max_program_pulses": program_verify.max_pulses,
        },
    }


# ─── Operation Endpoint ───────────────────────────────────────────────

@app.post("/api/operation")
async def execute_operation(req: OperationRequest):
    try:
        operation_type = OperationType(req.operation)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid operation: {req.operation}")

    pulse_params = {
        OperationType.FORMING: (3.5, 100, 10),
        OperationType.READ: (0.15, 50, 5),
        OperationType.SET: (2.0, 100, 10),
        OperationType.RESET: (2.0, 100, 10),
    }
    amp, width, ramp = pulse_params.get(operation_type, (1.0, 50, 5))

    op_spec = OperationSpec(
        type=operation_type, target=req.target, biasPolicyId="default",
        pulse=PulseSpec(amplitudeV=amp, widthNs=width, rampNs=ramp),
        complianceUa=PROFILE.complianceUa if operation_type in [OperationType.FORMING, OperationType.SET] else None,
    )

    frames = orchestrator.execute_operation(op_spec)

    response_frames = []
    for frame in frames:
        frame_dict = frame.model_dump()
        phase = frame.phase.value
        row = req.target["row"]
        col = req.target["col"]

        wl_v, bl_v, sl_v = peripheral.execute_phase(
            row=row, col=col, operation=operation_type, phase=phase, pulse_amplitude=amp,
        )

        # V0.3: Peripheral circuit info
        frame_dict["peripheral"] = {
            "wl_driver": {"voltages": wl_v, "selected": row, "active": any(v > 0 for v in wl_v)},
            "bl_driver": {
                "voltages": bl_v, "selected": col,
                "active": any(abs(v) > 0 for v in bl_v),
                "compliance_ua": PROFILE.complianceUa if operation_type in [OperationType.FORMING, OperationType.SET] else None,
            },
            "sl_driver": {"voltages": sl_v, "selected": col},
        }

        if operation_type in [OperationType.READ, OperationType.VERIFY] and frame.sense:
            frame_dict["peripheral"]["sense_amp"] = {
                "reference_ua": sense_amp.reference_ua,
                "min_margin_ua": sense_amp.min_margin_ua,
                "decision": frame.sense.decision,
                "margin_ua": frame.sense.marginUa,
            }

        # V0.6: Fault diagnosis for each frame
        ctx = DiagnosticContext(
            operation=req.operation, phase=phase,
            v_rram=frame.cell.rram.v, i_rram=frame.cell.rram.i, r_rram=frame.cell.rram.r,
            wl_voltage=frame.nodes.wl[row] if row < len(frame.nodes.wl) else 0,
            bl_voltage=frame.nodes.bl[col] if col < len(frame.nodes.bl) else 0,
            sl_voltage=frame.nodes.sl[col] if col < len(frame.nodes.sl) else 0,
            transistor_on=frame.cell.transistor.on,
            state=frame.cell.rram.state.value,
            forming_done=frame.cell.rram.formingDone,
        )
        report = diagnostic_engine.diagnose(
            ctx,
            expected_polarity="positive" if operation_type in [OperationType.FORMING, OperationType.SET] else "negative",
            compliance_limit=PROFILE.complianceUa if operation_type in [OperationType.FORMING, OperationType.SET] else None,
        )
        frame_dict["diagnostics"] = {
            "health": report.overall_health,
            "faults": [f.model_dump() for f in report.faults if f.detected],
            "recommendations": report.recommendations[:2],  # Top 2
        }

        response_frames.append(frame_dict)

    return response_frames


# ─── V0.7: Model Switching ────────────────────────────────────────────

@app.post("/api/model")
async def switch_model(req: ModelSwitchRequest):
    global current_model
    if req.model not in ["F0", "F1"]:
        raise HTTPException(status_code=400, detail="Model must be F0 or F1")
    current_model = req.model
    return {"status": "ok", "model": current_model}

@app.get("/api/model")
async def get_model():
    return {"model": current_model}


# ─── V0.6: Diagnostics ───────────────────────────────────────────────

@app.get("/api/diagnostics")
async def get_diagnostics():
    history = diagnostic_engine.get_diagnostic_history()
    return {
        "total_checks": len(history),
        "recent": [
            {
                "health": r.overall_health,
                "fault_count": len(r.faults),
                "summary": r.summary,
            }
            for r in history[-5:]
        ],
    }


# ─── V0.9: Learning System ───────────────────────────────────────────

@app.get("/api/learning/scenarios")
async def get_learning_scenarios(difficulty: Optional[str] = None):
    scenarios = learning_engine.scenarios
    if difficulty:
        scenarios = [s for s in scenarios if s.difficulty == difficulty]
    return [s.model_dump() for s in scenarios]

@app.get("/api/learning/scenario/next")
async def get_next_scenario(difficulty: Optional[str] = None):
    scenario = learning_engine.get_next_scenario(difficulty)
    if scenario is None:
        return {"scenario": None, "message": "No more scenarios available"}
    return scenario.model_dump()

@app.post("/api/learning/predict")
async def submit_prediction(req: PredictionRequest):
    prediction = Prediction(
        operation=OperationType(req.operation),
        predicted_category=PredictionCategory(req.predicted_category),
        reasoning=req.reasoning,
        confidence=req.confidence,
    )

    # Get latest frame for evaluation
    frames = orchestrator.get_frame_history()
    if len(frames) < 2:
        raise HTTPException(status_code=400, detail="Not enough frames for evaluation")

    actual_frame = frames[-1]
    prev_frame = frames[-2] if len(frames) >= 2 else None

    result = learning_engine.evaluate_prediction(prediction, actual_frame, prev_frame)
    learning_manager.update_progress(result, "current")

    return result.model_dump()

@app.get("/api/learning/progress")
async def get_learning_progress():
    return {
        "summary": learning_manager.get_progress_summary(),
        "badges": learning_manager.get_achievement_badges(),
        "weak_areas": learning_manager.get_weak_areas(),
    }

@app.post("/api/learning/note")
async def add_note(req: NoteRequest):
    note = learning_manager.add_note(req.scenario_id, req.content, req.tags)
    return note.model_dump()

@app.get("/api/learning/notes")
async def get_notes(scenario_id: Optional[str] = None):
    if scenario_id:
        notes = learning_manager.get_notes_for_scenario(scenario_id)
    else:
        notes = learning_manager.progress.notes
    return [n.model_dump() for n in notes]
