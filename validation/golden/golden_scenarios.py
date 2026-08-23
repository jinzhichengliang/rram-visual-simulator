"""
Golden Scenarios — Canonical test cases that must pass for every release.

These scenarios represent the fundamental operations that the simulator
must handle correctly. They are the acceptance criteria for each version.
"""
from __future__ import annotations

from dataclasses import dataclass

from packages.contracts.types import (
    DeviceProfile,
    DeviceState,
    OperationSpec,
    OperationType,
    Polarity,
    PulseSpec,
)
from simulator.orchestrator.simulation_orchestrator import SimulationOrchestrator
from validation.invariants.physics_invariants import CheckEngine


@dataclass
class GoldenResult:
    """Result of a golden scenario test."""
    scenario_id: str
    passed: bool
    message: str
    failed_invariants: list[str]
    frame_count: int


class GoldenScenarios:
    """
    Collection of golden scenarios that must pass for every release.
    """

    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        self.check_engine = CheckEngine(profile)

    def run_all(self) -> list[GoldenResult]:
        """Run all golden scenarios and return results."""
        return [
            self.g01_basic_1t1r_cycle(),
            self.g02_read_non_destructive(),
            self.g03_compliance_protection(),
            self.g04_polarity_reversal(),
        ]

    # ─── G-01: Basic 1T1R Cycle ───────────────────────────────────────

    def g01_basic_1t1r_cycle(self) -> GoldenResult:
        """
        G-01: Complete 1T1R operation cycle.

        Pristine → Forming → HRS (init reset) → Read 0 → Set → Read 1 → Reset → Read 0

        All invariants must pass throughout the cycle.
        """
        scenario_id = "G-01"
        orchestrator = SimulationOrchestrator(self.profile, seed=42)

        try:
            # Step 1: Forming (Pristine → LRS)
            forming_op = OperationSpec(
                type=OperationType.FORMING,
                target={"row": 0, "col": 0},
                biasPolicyId="default_forming",
                pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
                complianceUa=self.profile.complianceUa,
            )
            forming_frames = orchestrator.execute_operation(forming_op)

            # Check forming succeeded
            if orchestrator.get_current_state() != DeviceState.LRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"Forming failed: expected LRS, got {orchestrator.get_current_state()}",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Step 2: Init RESET (LRS → HRS)
            reset_op = OperationSpec(
                type=OperationType.RESET,
                target={"row": 0, "col": 0},
                biasPolicyId="default_reset",
                pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),
            )
            orchestrator.execute_operation(reset_op)

            if orchestrator.get_current_state() != DeviceState.HRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"Init RESET failed: expected HRS, got {orchestrator.get_current_state()}",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Step 3: READ 0 (HRS)
            read0_op = OperationSpec(
                type=OperationType.READ,
                target={"row": 0, "col": 0},
                biasPolicyId="default_read",
                pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
            )
            orchestrator.execute_operation(read0_op)

            # Step 4: SET (HRS → LRS)
            set_op = OperationSpec(
                type=OperationType.SET,
                target={"row": 0, "col": 0},
                biasPolicyId="default_set",
                pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),
                complianceUa=self.profile.complianceUa,
            )
            orchestrator.execute_operation(set_op)

            if orchestrator.get_current_state() != DeviceState.LRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"SET failed: expected LRS, got {orchestrator.get_current_state()}",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Step 5: READ 1 (LRS)
            orchestrator.execute_operation(read0_op)

            # Step 6: RESET (LRS → HRS)
            orchestrator.execute_operation(reset_op)

            if orchestrator.get_current_state() != DeviceState.HRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"RESET failed: expected HRS, got {orchestrator.get_current_state()}",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Step 7: READ 0 (HRS)
            orchestrator.execute_operation(read0_op)

            # Check all invariants on all frames
            all_frames = orchestrator.get_frame_history()
            failed_invariants = []

            for i, frame in enumerate(all_frames):
                prev_frame = all_frames[i - 1] if i > 0 else None
                results = self.check_engine.check_frame(frame, prev_frame)
                failures = self.check_engine.get_failures(results)
                for f in failures:
                    failed_invariants.append(f"{f.ruleId}@frame{i}: {f.message}")

            if failed_invariants:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"G-01 failed with {len(failed_invariants)} invariant violations",
                    failed_invariants=failed_invariants[:10],  # Limit output
                    frame_count=len(all_frames),
                )

            return GoldenResult(
                scenario_id=scenario_id,
                passed=True,
                message=f"G-01 passed: complete cycle with {len(all_frames)} frames, all invariants OK",
                failed_invariants=[],
                frame_count=len(all_frames),
            )

        except Exception as e:
            return GoldenResult(
                scenario_id=scenario_id,
                passed=False,
                message=f"G-01 exception: {e!s}",
                failed_invariants=[],
                frame_count=len(orchestrator.get_frame_history()),
            )

    # ─── G-02: Read Non-Destructive ───────────────────────────────────

    def g02_read_non_destructive(self, num_reads: int = 10) -> GoldenResult:
        """
        G-02: Multiple READ operations must not change device state.

        Read HRS or LRS multiple times; R/gap drift must be below tolerance.
        """
        scenario_id = "G-02"
        orchestrator = SimulationOrchestrator(self.profile, seed=42)

        try:
            # Form and set to LRS
            forming_op = OperationSpec(
                type=OperationType.FORMING,
                target={"row": 0, "col": 0},
                biasPolicyId="default_forming",
                pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
            )
            orchestrator.execute_operation(forming_op)

            read_op = OperationSpec(
                type=OperationType.READ,
                target={"row": 0, "col": 0},
                biasPolicyId="default_read",
                pulse=PulseSpec(amplitudeV=0.15, widthNs=50, rampNs=5),
            )

            # Read multiple times
            initial_r = orchestrator.get_frame_history()[-1].cell.rram.r
            initial_state = orchestrator.get_current_state()

            for _ in range(num_reads):
                orchestrator.execute_operation(read_op)

            final_r = orchestrator.get_frame_history()[-1].cell.rram.r
            final_state = orchestrator.get_current_state()

            # Check state unchanged
            if final_state != initial_state:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"State changed after {num_reads} reads: {initial_state} → {final_state}",
                    failed_invariants=["INV-005"],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Check R drift
            r_change_pct = abs(final_r - initial_r) / initial_r * 100
            tolerance = self.profile.tolerances.readDisturbPct

            if r_change_pct > tolerance:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"R drifted {r_change_pct:.2f}% > {tolerance}% after {num_reads} reads",
                    failed_invariants=["INV-005"],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            return GoldenResult(
                scenario_id=scenario_id,
                passed=True,
                message=f"G-02 passed: {num_reads} reads, state={final_state}, ΔR={r_change_pct:.4f}%",
                failed_invariants=[],
                frame_count=len(orchestrator.get_frame_history()),
            )

        except Exception as e:
            return GoldenResult(
                scenario_id=scenario_id,
                passed=False,
                message=f"G-02 exception: {e!s}",
                failed_invariants=[],
                frame_count=len(orchestrator.get_frame_history()),
            )

    # ─── G-03: Compliance Protection ──────────────────────────────────

    def g03_compliance_protection(self) -> GoldenResult:
        """
        G-03: Compliance must limit current during forming/SET.

        Even with high drive, current must not exceed compliance limit.
        """
        scenario_id = "G-03"
        orchestrator = SimulationOrchestrator(self.profile, seed=42)

        try:
            # Try forming with very high voltage (should be limited by compliance)
            forming_op = OperationSpec(
                type=OperationType.FORMING,
                target={"row": 0, "col": 0},
                biasPolicyId="default_forming",
                pulse=PulseSpec(amplitudeV=10.0, widthNs=100, rampNs=10),  # Very high
                complianceUa=self.profile.complianceUa,
            )
            frames = orchestrator.execute_operation(forming_op)

            # Check that current never exceeded compliance
            max_current = max(abs(f.cell.rram.i) for f in frames)
            compliance = self.profile.complianceUa
            tolerance = 0.1  # 0.1 µA

            if max_current > compliance + tolerance:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"Compliance violated: max |I| = {max_current:.3f}µA > {compliance}µA",
                    failed_invariants=["INV-004"],
                    frame_count=len(frames),
                )

            return GoldenResult(
                scenario_id=scenario_id,
                passed=True,
                message=f"G-03 passed: max |I| = {max_current:.3f}µA ≤ {compliance}µA",
                failed_invariants=[],
                frame_count=len(frames),
            )

        except Exception as e:
            return GoldenResult(
                scenario_id=scenario_id,
                passed=False,
                message=f"G-03 exception: {e!s}",
                failed_invariants=[],
                frame_count=len(orchestrator.get_frame_history()),
            )

    # ─── G-04: Polarity Reversal ──────────────────────────────────────

    def g04_polarity_reversal(self) -> GoldenResult:
        """
        G-04: Simulator must work with reversed polarity profile.

        Create a profile with reversed SET/RESET polarity and verify
        that all operations still work correctly.
        """
        scenario_id = "G-04"

        try:
            # Create reversed polarity profile
            reversed_profile = self.profile.model_copy()
            reversed_profile.setPolarity = Polarity.NEGATIVE  # Reversed
            reversed_profile.resetPolarity = Polarity.POSITIVE  # Reversed

            orchestrator = SimulationOrchestrator(reversed_profile, seed=42)
            check_engine = CheckEngine(reversed_profile)

            # Forming (still positive for teaching model)
            forming_op = OperationSpec(
                type=OperationType.FORMING,
                target={"row": 0, "col": 0},
                biasPolicyId="default_forming",
                pulse=PulseSpec(amplitudeV=3.5, widthNs=100, rampNs=10),
            )
            orchestrator.execute_operation(forming_op)

            if orchestrator.get_current_state() != DeviceState.LRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message="Forming failed with reversed profile",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # RESET with reversed polarity (now positive voltage)
            reset_op = OperationSpec(
                type=OperationType.RESET,
                target={"row": 0, "col": 0},
                biasPolicyId="default_reset",
                pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),  # Positive for reversed
            )
            orchestrator.execute_operation(reset_op)

            if orchestrator.get_current_state() != DeviceState.HRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message="RESET failed with reversed polarity",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # SET with reversed polarity (now negative voltage)
            set_op = OperationSpec(
                type=OperationType.SET,
                target={"row": 0, "col": 0},
                biasPolicyId="default_set",
                pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),  # Negative for reversed
            )
            orchestrator.execute_operation(set_op)

            if orchestrator.get_current_state() != DeviceState.LRS:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message="SET failed with reversed polarity",
                    failed_invariants=[],
                    frame_count=len(orchestrator.get_frame_history()),
                )

            # Check invariants
            all_frames = orchestrator.get_frame_history()
            failed_invariants = []

            for i, frame in enumerate(all_frames):
                prev_frame = all_frames[i - 1] if i > 0 else None
                results = check_engine.check_frame(frame, prev_frame)
                failures = check_engine.get_failures(results)
                for f in failures:
                    failed_invariants.append(f"{f.ruleId}@frame{i}")

            if failed_invariants:
                return GoldenResult(
                    scenario_id=scenario_id,
                    passed=False,
                    message=f"G-04 failed with reversed polarity: {len(failed_invariants)} violations",
                    failed_invariants=failed_invariants[:10],
                    frame_count=len(all_frames),
                )

            return GoldenResult(
                scenario_id=scenario_id,
                passed=True,
                message="G-04 passed: reversed polarity works correctly",
                failed_invariants=[],
                frame_count=len(all_frames),
            )

        except Exception as e:
            return GoldenResult(
                scenario_id=scenario_id,
                passed=False,
                message=f"G-04 exception: {e!s}",
                failed_invariants=[],
                frame_count=0,
            )
