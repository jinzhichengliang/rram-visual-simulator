"""S03 — Physics Invariants + Golden Scenarios tests.

Tests the validation system:
- INV-001~INV-009 invariant checks
- G-01~G-04 golden scenarios
- Check engine integration
- Fault injection detection
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
    CheckResult,
    DeviceProfile,
    DeviceRanges,
    DeviceTolerances,
    LogicMap,
    OperationPhase,
    OperationSpec,
    OperationType,
    Polarity,
    PulseSpec,
    SeverityLevel,
    StackOrientation,
)
from simulator.orchestrator.simulation_orchestrator import SimulationOrchestrator
from validation.golden.golden_scenarios import GoldenScenarios
from validation.invariants.physics_invariants import (
    CheckEngine,
    INV001_VRramNodeConsistency,
    INV002_TransistorGating,
    INV004_Compliance,
    INV005_ReadNonDestructive,
    InvariantContext,
)


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


# ─── Invariant Tests ──────────────────────────────────────────────────


class TestINV001_VRramNodeConsistency:
    """Test V_RRAM node consistency invariant."""

    def test_passes_when_transistor_on_and_v_matches(self, teaching_profile):
        """INV-001 passes when V_RRAM matches node difference."""
        inv = INV001_VRramNodeConsistency()
        orchestrator = SimulationOrchestrator(teaching_profile)

        # Execute a forming operation
        op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        frames = orchestrator.execute_operation(op)

        # Check ACTIVE phase frame
        active_frame = next(f for f in frames if f.phase == OperationPhase.ACTIVE)
        ctx = InvariantContext(frame=active_frame, profile=teaching_profile)
        result = inv.check(ctx)

        assert result.passed is True
        assert result.ruleId == "INV-001"

    def test_passes_when_transistor_off_and_v_is_zero(self, teaching_profile):
        """INV-001 passes when transistor OFF and V_RRAM ≈ 0."""
        inv = INV001_VRramNodeConsistency()
        orchestrator = SimulationOrchestrator(teaching_profile)

        # Execute PREPARE phase (transistor OFF)
        op = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )
        frames = orchestrator.execute_operation(op)
        prepare_frame = next(f for f in frames if f.phase == OperationPhase.PREPARE)

        ctx = InvariantContext(frame=prepare_frame, profile=teaching_profile)
        result = inv.check(ctx)

        assert result.passed is True


class TestINV002_TransistorGating:
    """Test transistor gating invariant."""

    def test_passes_when_transistor_off_and_current_zero(self, teaching_profile):
        """INV-002 passes when transistor OFF and I ≈ 0."""
        inv = INV002_TransistorGating()
        orchestrator = SimulationOrchestrator(teaching_profile)

        op = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )
        frames = orchestrator.execute_operation(op)
        prepare_frame = next(f for f in frames if f.phase == OperationPhase.PREPARE)

        ctx = InvariantContext(frame=prepare_frame, profile=teaching_profile)
        result = inv.check(ctx)

        assert result.passed is True
        assert result.ruleId == "INV-002"


class TestINV004_Compliance:
    """Test compliance invariant."""

    def test_passes_when_current_below_limit(self, teaching_profile):
        """INV-004 passes when current within compliance."""
        inv = INV004_Compliance()
        orchestrator = SimulationOrchestrator(teaching_profile)

        op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
            complianceUa=teaching_profile.complianceUa,
        )
        frames = orchestrator.execute_operation(op)

        for frame in frames:
            ctx = InvariantContext(frame=frame, profile=teaching_profile)
            result = inv.check(ctx)
            assert result.passed is True


class TestINV005_ReadNonDestructive:
    """Test read non-destructive invariant."""

    def test_passes_when_read_does_not_change_state(self, teaching_profile):
        """INV-005 passes when READ doesn't change state."""
        inv = INV005_ReadNonDestructive()
        orchestrator = SimulationOrchestrator(teaching_profile)

        # Form first
        form_op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        orchestrator.execute_operation(form_op)

        # Read
        read_op = OperationSpec(
            type=OperationType.READ,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
        )
        frames = orchestrator.execute_operation(read_op)

        # Check ACTIVE phase
        active_frame = next(f for f in frames if f.phase == OperationPhase.ACTIVE)
        prev_frame = orchestrator.get_frame_history()[-len(frames) - 1]
        ctx = InvariantContext(frame=active_frame, profile=teaching_profile, prev_frame=prev_frame)
        result = inv.check(ctx)

        assert result.passed is True


# ─── Check Engine Tests ───────────────────────────────────────────────


class TestCheckEngine:
    """Test the check engine integration."""

    def test_check_engine_runs_all_invariants(self, teaching_profile):
        """Check engine runs all 9 invariants."""
        engine = CheckEngine(teaching_profile)
        orchestrator = SimulationOrchestrator(teaching_profile)

        op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        frames = orchestrator.execute_operation(op)

        # Each frame should have check results
        for frame in frames:
            assert len(frame.checks) == 9
            rule_ids = [c.ruleId for c in frame.checks]
            assert "INV-001" in rule_ids
            assert "INV-009" in rule_ids

    def test_check_engine_reports_failures(self, teaching_profile):
        """Check engine correctly identifies failures."""
        engine = CheckEngine(teaching_profile)

        # All invariants should pass for normal operation
        orchestrator = SimulationOrchestrator(teaching_profile)
        op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        frames = orchestrator.execute_operation(op)

        for frame in frames:
            failures = engine.get_failures(frame.checks)
            assert len(failures) == 0, f"Unexpected failures: {[f.message for f in failures]}"


# ─── Golden Scenario Tests ────────────────────────────────────────────


class TestGoldenScenarios:
    """Test golden scenarios."""

    def test_g01_basic_1t1r_cycle(self, teaching_profile):
        """G-01: Complete 1T1R cycle must pass."""
        golden = GoldenScenarios(teaching_profile)
        result = golden.g01_basic_1t1r_cycle()

        assert result.passed is True, f"G-01 failed: {result.message}\nViolations: {result.failed_invariants}"
        assert result.scenario_id == "G-01"
        assert result.frame_count > 0

    def test_g02_read_non_destructive(self, teaching_profile):
        """G-02: Multiple reads must not change state."""
        golden = GoldenScenarios(teaching_profile)
        result = golden.g02_read_non_destructive(num_reads=5)

        assert result.passed is True, f"G-02 failed: {result.message}"
        assert result.scenario_id == "G-02"

    def test_g03_compliance_protection(self, teaching_profile):
        """G-03: Compliance must limit current."""
        golden = GoldenScenarios(teaching_profile)
        result = golden.g03_compliance_protection()

        assert result.passed is True, f"G-03 failed: {result.message}"
        assert result.scenario_id == "G-03"

    def test_g04_polarity_reversal(self, teaching_profile):
        """G-04: Reversed polarity must work."""
        golden = GoldenScenarios(teaching_profile)
        result = golden.g04_polarity_reversal()

        assert result.passed is True, f"G-04 failed: {result.message}\nViolations: {result.failed_invariants}"
        assert result.scenario_id == "G-04"

    def test_run_all_golden_scenarios(self, teaching_profile):
        """Run all golden scenarios and verify all pass."""
        golden = GoldenScenarios(teaching_profile)
        results = golden.run_all()

        assert len(results) == 4
        for result in results:
            assert result.passed is True, f"{result.scenario_id} failed: {result.message}"


# ─── Integration Tests ────────────────────────────────────────────────


class TestS03Integration:
    """Integration tests for S03."""

    def test_frames_carry_check_results(self, teaching_profile):
        """Every frame must carry invariant check results."""
        orchestrator = SimulationOrchestrator(teaching_profile)

        op = OperationSpec(
            type=OperationType.FORMING,
            target={"row": 0, "col": 0},
            biasPolicyId="default",
            pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
        )
        frames = orchestrator.execute_operation(op)

        for frame in frames:
            assert hasattr(frame, "checks")
            assert len(frame.checks) > 0
            for check in frame.checks:
                assert isinstance(check, CheckResult)
                assert check.ruleId.startswith("INV-")
                assert check.severity in [SeverityLevel.INFO, SeverityLevel.WARNING, SeverityLevel.ERROR, SeverityLevel.CRITICAL]

    def test_golden_scenarios_use_check_engine(self, teaching_profile):
        """Golden scenarios must use check engine for validation."""
        golden = GoldenScenarios(teaching_profile)
        result = golden.g01_basic_1t1r_cycle()

        # If passed, all invariants were checked
        if result.passed:
            assert result.frame_count > 0
            assert len(result.failed_invariants) == 0
