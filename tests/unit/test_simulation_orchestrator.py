"""S02 — Simulation Orchestrator unit tests.

Tests the orchestrator for:
- Complete operation lifecycle
- Phase sequence
- Frame generation
- Event emission
- State persistence
- Causal ordering
"""
import sys
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "packages"))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))
sys.path.insert(0, str(PROJECT_ROOT))

from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceState,
    DeviceTolerances,
    LogicMap,
    OperationPhase,
    OperationSpec,
    OperationType,
    Polarity,
    PulseSpec,
    StackOrientation,
)
from simulator.orchestrator.simulation_orchestrator import SimulationOrchestrator


@pytest.fixture
def teaching_profile() -> DeviceProfile:
    """Standard bipolar teaching profile."""
    return DeviceProfile(
        id="bipolar_teaching_v1",
        version="1.0.0",
        stackOrientation=StackOrientation.BL_RRAM_NMOS_SL,
        vRramSignConvention="V(top)-V(bottom)",
        setPolarity=Polarity.POSITIVE,
        resetPolarity=Polarity.NEGATIVE,
        logicMap=LogicMap(LRS=1, HRS=0),
        ranges=DeviceRanges(
            vRead=[0.1, 0.2],
            vSet=[1.5, 2.5],
            vReset=[-2.5, -1.5],
            vForm=[3.0, 4.0],
            rLrs=[10000, 50000],
            rHrs=[500000, 5000000],
        ),
        complianceUa=50.0,
        tolerances=DeviceTolerances(
            readDisturbPct=1.0,
            currentConservationPct=5.0,
            crossViewAbs=0.001,
        ),
    )


@pytest.fixture
def orchestrator(teaching_profile) -> SimulationOrchestrator:
    """Create orchestrator with teaching profile."""
    return SimulationOrchestrator(teaching_profile, seed=42)


class TestOperationLifecycle:
    """Test complete operation lifecycle."""

    def test_forming_operation_generates_frames(self, orchestrator):
        """FORMING operation should generate frames for all phases."""
        operation = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
            complianceUa=50.0,
        )

        frames = orchestrator.execute_operation(operation)

        assert len(frames) > 0
        # Should have PREPARE, BIAS_RAMP, ACTIVE, HOLD, RELEASE, COMPLETE
        phases = [f.phase for f in frames]
        assert OperationPhase.PREPARE in phases
        assert OperationPhase.ACTIVE in phases
        assert OperationPhase.COMPLETE in phases

    def test_read_operation_includes_sense_phase(self, orchestrator):
        """READ operation should include SENSE phase."""
        # First form the device
        form_op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(form_op)

        # Now read
        read_op = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default_read",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )
        frames = orchestrator.execute_operation(read_op)

        phases = [f.phase for f in frames]
        assert OperationPhase.SENSE in phases

        # Check that sense was computed
        sense_frames = [f for f in frames if f.sense is not None]
        assert len(sense_frames) > 0


class TestCausalOrdering:
    """Test that causal order is maintained."""

    def test_bias_before_state_change(self, orchestrator):
        """State change should only happen after bias is applied."""
        operation = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )

        frames = orchestrator.execute_operation(operation)

        # Find when state changed
        state_change_idx = None
        for i, frame in enumerate(frames):
            if frame.cell.rram.state != DeviceState.PRISTINE:
                state_change_idx = i
                break

        if state_change_idx is not None:
            # State change should happen after PREPARE
            assert state_change_idx > 0
            # Bias should be applied before or at state change
            prepare_frame = frames[0]
            assert prepare_frame.phase == OperationPhase.PREPARE


class TestStatePersistence:
    """Test that state persists across operations."""

    def test_forming_persists_to_read(self, orchestrator):
        """After FORMING, device should remain formed for READ."""
        # Form the device
        form_op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(form_op)

        assert orchestrator.get_current_state() == DeviceState.LRS

        # Read should see LRS
        read_op = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default_read",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )
        frames = orchestrator.execute_operation(read_op)

        # Final frame should still be LRS
        assert frames[-1].cell.rram.state == DeviceState.LRS

    def test_set_reset_cycle(self, orchestrator):
        """SET/RESET cycle should toggle state correctly."""
        # Form first
        form_op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(form_op)
        assert orchestrator.get_current_state() == DeviceState.LRS

        # RESET to HRS (amplitude is absolute value, polarity from profile)
        reset_op = OperationSpec(
            type=OperationType.RESET,
            target={"row": 0, "col": 0},
            biasPolicyId="default_reset",
            pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),  # Will be -2.0V due to profile
        )
        orchestrator.execute_operation(reset_op)
        assert orchestrator.get_current_state() == DeviceState.HRS

        # SET back to LRS
        set_op = OperationSpec(
            type=OperationType.SET,
            target={"row": 0, "col": 0},
            biasPolicyId="default_set",
            pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(set_op)
        assert orchestrator.get_current_state() == DeviceState.LRS


class TestEventEmission:
    """Test that events are emitted correctly."""

    def test_operation_emits_events(self, orchestrator):
        """Operation should emit semantic events."""
        operation = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default_read",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )

        orchestrator.execute_operation(operation)
        events = orchestrator.get_event_history()

        assert len(events) > 0
        # Should have OPERATION_STARTED and OPERATION_COMPLETED
        event_types = [e.eventType for e in events]
        assert "OPERATION_STARTED" in event_types
        assert "OPERATION_COMPLETED" in event_types


class TestReset:
    """Test reset functionality."""

    def test_reset_clears_state(self, orchestrator):
        """Reset should return to initial state."""
        # Perform some operations
        form_op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(form_op)

        assert orchestrator.get_current_state() == DeviceState.LRS
        assert len(orchestrator.get_frame_history()) > 0

        # Reset
        orchestrator.reset()

        assert orchestrator.get_current_state() == DeviceState.PRISTINE
        assert len(orchestrator.get_frame_history()) == 0


class TestDeterminism:
    """Test that orchestrator is deterministic."""

    def test_same_seed_same_results(self, teaching_profile):
        """Same seed should produce identical results."""
        orch1 = SimulationOrchestrator(teaching_profile, seed=42)
        orch2 = SimulationOrchestrator(teaching_profile, seed=42)

        operation = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default_forming",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )

        frames1 = orch1.execute_operation(operation)
        frames2 = orch2.execute_operation(operation)

        assert len(frames1) == len(frames2)
        for f1, f2 in zip(frames1, frames2):
            assert f1.cell.rram.v == f2.cell.rram.v
            assert f1.cell.rram.i == f2.cell.rram.i
            assert f1.cell.rram.state == f2.cell.rram.state
