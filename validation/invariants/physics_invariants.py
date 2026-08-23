"""
Physics Invariants — Automated checks for every FrameState.

These invariants encode the physical and electrical rules that must hold
at every simulation step. They are the foundation of the validation system.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from packages.contracts.types import (
    CheckResult,
    DeviceProfile,
    DeviceState,
    FrameState,
    OperationType,
    SeverityLevel,
)


@dataclass
class InvariantContext:
    """Context for invariant evaluation."""
    frame: FrameState
    profile: DeviceProfile
    prev_frame: FrameState | None = None


class Invariant(Protocol):
    """Protocol for physics invariants."""

    @property
    def rule_id(self) -> str:
        """Invariant identifier (e.g., INV-001)."""
        ...

    def check(self, ctx: InvariantContext) -> CheckResult:
        """Evaluate the invariant and return a CheckResult."""
        ...


# ─── INV-001: V_RRAM Node Consistency ─────────────────────────────────

class INV001_VRramNodeConsistency:
    """
    V_RRAM must equal the actual node voltage difference.

    For BL-RRAM-NMOS-SL topology with V(top)-V(bottom) convention:
    V_RRAM = V_BL - V_NMOS_drain (when transistor ON)
    V_RRAM = 0 (when transistor OFF, no current path)
    """

    @property
    def rule_id(self) -> str:
        return "INV-001"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        transistor_on = f.cell.transistor.on

        if transistor_on:
            # When ON, V_RRAM should be BL - SL (ideal switch)
            expected_v = f.nodes.bl[f.selectedCell["col"]] - f.nodes.sl[f.selectedCell["col"]]
            actual_v = f.cell.rram.v
            diff = abs(expected_v - actual_v)
            tolerance = ctx.profile.tolerances.crossViewAbs

            passed = diff < tolerance
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
                message=f"V_RRAM consistency: expected {expected_v:.3f}V, got {actual_v:.3f}V (diff={diff:.6f}V)"
                        if not passed else f"V_RRAM = {actual_v:.3f}V matches node difference",
                details={"expected": expected_v, "actual": actual_v, "diff": diff, "tolerance": tolerance}
            )
        else:
            # When OFF, V_RRAM should be 0 (no current path)
            actual_v = f.cell.rram.v
            passed = abs(actual_v) < 0.001  # 1mV tolerance
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
                message=f"Transistor OFF but V_RRAM = {actual_v:.3f}V (should be ~0)"
                        if not passed else "Transistor OFF, V_RRAM ≈ 0V",
                details={"actual": actual_v, "transistor_on": False}
            )


# ─── INV-002: Transistor Gating ───────────────────────────────────────

class INV002_TransistorGating:
    """
    When transistor is OFF, main branch current must be near zero.

    Teaching model ignores leakage, so I_RRAM ≈ 0 when NMOS OFF.
    """

    @property
    def rule_id(self) -> str:
        return "INV-002"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        transistor_on = f.cell.transistor.on
        i_rram = f.cell.rram.i

        if not transistor_on:
            leakage_tolerance = 0.1  # 0.1 µA
            passed = abs(i_rram) < leakage_tolerance
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
                message=f"Transistor OFF but I_RRAM = {i_rram:.3f}µA (should be ~0)"
                        if not passed else "Transistor OFF, I_RRAM ≈ 0",
                details={"i_rram": i_rram, "transistor_on": False, "tolerance": leakage_tolerance}
            )
        else:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message="Transistor ON, current path active",
                details={"i_rram": i_rram, "transistor_on": True}
            )


# ─── INV-003: Current Direction ───────────────────────────────────────

class INV003_CurrentDirection:
    """
    Current direction must match voltage polarity.

    For positive V_RRAM (BL > SL), current should flow BL → SL (positive I).
    For negative V_RRAM (BL < SL), current should flow SL → BL (negative I).
    """

    @property
    def rule_id(self) -> str:
        return "INV-003"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        v_rram = f.cell.rram.v
        i_rram = f.cell.rram.i

        # Ohm's law: I = V/R, so sign(I) should match sign(V)
        if abs(v_rram) < 0.001:
            # Near zero voltage, current should also be near zero
            passed = abs(i_rram) < 0.1
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.WARNING if not passed else SeverityLevel.INFO,
                message=f"V_RRAM ≈ 0, I_RRAM = {i_rram:.3f}µA"
                        if not passed else "V_RRAM ≈ 0, I_RRAM ≈ 0",
                details={"v_rram": v_rram, "i_rram": i_rram}
            )

        expected_sign = 1 if v_rram > 0 else -1
        actual_sign = 1 if i_rram > 0 else -1 if i_rram < 0 else 0

        passed = expected_sign == actual_sign
        return CheckResult(
            ruleId=self.rule_id,
            passed=passed,
            severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
            message=f"Current direction mismatch: V_RRAM={v_rram:.3f}V (sign={expected_sign}), "
                    f"I_RRAM={i_rram:.3f}µA (sign={actual_sign})"
                    if not passed else "Current direction matches voltage polarity",
            details={"v_rram": v_rram, "i_rram": i_rram, "expected_sign": expected_sign, "actual_sign": actual_sign}
        )


# ─── INV-004: Compliance ──────────────────────────────────────────────

class INV004_Compliance:
    """
    During FORMING/SET, if compliance is configured, current must not exceed limit.
    """

    @property
    def rule_id(self) -> str:
        return "INV-004"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        op = f.operation
        i_rram = abs(f.cell.rram.i)
        compliance = ctx.profile.complianceUa

        # Only check during programming operations
        if op not in [OperationType.FORMING, OperationType.SET]:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message=f"Operation {op.value} does not require compliance check",
                details={"operation": op.value}
            )

        tolerance = 0.1  # 0.1 µA tolerance
        passed = i_rram <= compliance + tolerance
        return CheckResult(
            ruleId=self.rule_id,
            passed=passed,
            severity=SeverityLevel.CRITICAL if not passed else SeverityLevel.INFO,
            message=f"Compliance violated: |I_RRAM| = {i_rram:.3f}µA > limit {compliance}µA"
                    if not passed else f"Compliance OK: |I_RRAM| = {i_rram:.3f}µA ≤ {compliance}µA",
            details={"i_rram": i_rram, "compliance": compliance, "tolerance": tolerance}
        )


# ─── INV-005: Read Non-Destructive ────────────────────────────────────

class INV005_ReadNonDestructive:
    """
    READ operation must not change device state (R, gap, state).

    Read voltage is below write threshold, so device should remain unchanged.
    """

    @property
    def rule_id(self) -> str:
        return "INV-005"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        prev = ctx.prev_frame

        if f.operation != OperationType.READ or prev is None:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message="Not a READ operation or no previous frame",
                details={"operation": f.operation.value}
            )

        # Check state change
        prev_state = prev.cell.rram.state
        curr_state = f.cell.rram.state
        state_changed = prev_state != curr_state

        # Check resistance change
        prev_r = prev.cell.rram.r
        curr_r = f.cell.rram.r
        r_change_pct = abs(curr_r - prev_r) / prev_r * 100 if prev_r > 0 else 0
        tolerance = ctx.profile.tolerances.readDisturbPct
        r_violated = r_change_pct > tolerance

        passed = not state_changed and not r_violated
        return CheckResult(
            ruleId=self.rule_id,
            passed=passed,
            severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
            message=f"READ changed state: {prev_state} → {curr_state}"
                    if state_changed else
                    f"READ disturbed R: {r_change_pct:.2f}% > {tolerance}%"
                    if r_violated else
                    f"READ non-destructive: state={curr_state}, ΔR={r_change_pct:.2f}%",
            details={
                "prev_state": prev_state, "curr_state": curr_state,
                "prev_r": prev_r, "curr_r": curr_r,
                "r_change_pct": r_change_pct, "tolerance": tolerance
            }
        )


# ─── INV-006: State Windows ───────────────────────────────────────────

class INV006_StateWindows:
    """
    LRS/HRS resistance must fall within configured windows.
    """

    @property
    def rule_id(self) -> str:
        return "INV-006"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        state = f.cell.rram.state
        r = f.cell.rram.r

        if state == DeviceState.PRISTINE:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message="PRISTINE state, no window check",
                details={"state": state.value}
            )

        if state == DeviceState.LRS:
            r_min, r_max = ctx.profile.ranges.rLrs
            passed = r_min <= r <= r_max
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
                message=f"LRS R={r:.0f}Ω outside window [{r_min}, {r_max}]"
                        if not passed else f"LRS R={r:.0f}Ω within window",
                details={"state": state.value, "r": r, "r_min": r_min, "r_max": r_max}
            )

        if state == DeviceState.HRS:
            r_min, r_max = ctx.profile.ranges.rHrs
            passed = r_min <= r <= r_max
            return CheckResult(
                ruleId=self.rule_id,
                passed=passed,
                severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
                message=f"HRS R={r:.0f}Ω outside window [{r_min}, {r_max}]"
                        if not passed else f"HRS R={r:.0f}Ω within window",
                details={"state": state.value, "r": r, "r_min": r_min, "r_max": r_max}
            )

        return CheckResult(
            ruleId=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="Unknown state, no window check",
            details={"state": state.value}
        )


# ─── INV-007: Forming Prerequisite ────────────────────────────────────

class INV007_FormingPrerequisite:
    """
    SET/RESET should not occur before forming is complete.

    Device must be formed before normal SET/RESET operations.
    """

    @property
    def rule_id(self) -> str:
        return "INV-007"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        op = f.operation
        forming_done = f.cell.rram.formingDone

        if op in [OperationType.SET, OperationType.RESET] and not forming_done:
            return CheckResult(
                ruleId=self.rule_id,
                passed=False,
                severity=SeverityLevel.ERROR,
                message=f"{op.value} attempted before forming is complete",
                details={"operation": op.value, "forming_done": forming_done}
            )

        return CheckResult(
            ruleId=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="Forming prerequisite satisfied or not applicable",
            details={"operation": op.value, "forming_done": forming_done}
        )


# ─── INV-008: No Spontaneous Switching ────────────────────────────────

class INV008_NoSpontaneousSwitching:
    """
    Device state should not change without valid bias/operation.

    State transitions only occur during ACTIVE/HOLD phases with proper bias.
    """

    @property
    def rule_id(self) -> str:
        return "INV-008"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame
        prev = ctx.prev_frame

        if prev is None:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message="No previous frame to compare",
                details={}
            )

        prev_state = prev.cell.rram.state
        curr_state = f.cell.rram.state

        # State should only change during ACTIVE or HOLD phases
        if prev_state != curr_state and f.phase not in ["ACTIVE", "HOLD"]:
            return CheckResult(
                ruleId=self.rule_id,
                passed=False,
                severity=SeverityLevel.ERROR,
                message=f"State changed during {f.phase} phase (should only change in ACTIVE/HOLD)",
                details={"prev_state": prev_state, "curr_state": curr_state, "phase": f.phase}
            )

        return CheckResult(
            ruleId=self.rule_id,
            passed=True,
            severity=SeverityLevel.INFO,
            message="No spontaneous switching detected",
            details={"prev_state": prev_state, "curr_state": curr_state, "phase": f.phase}
        )


# ─── INV-009: Sense Consistency ───────────────────────────────────────

class INV009_SenseConsistency:
    """
    Sense decision must match I_read vs reference comparison.
    """

    @property
    def rule_id(self) -> str:
        return "INV-009"

    def check(self, ctx: InvariantContext) -> CheckResult:
        f = ctx.frame

        if f.sense is None:
            return CheckResult(
                ruleId=self.rule_id,
                passed=True,
                severity=SeverityLevel.INFO,
                message="No sense data in this frame",
                details={}
            )

        i_read = abs(f.sense.currentUa)
        i_ref = f.sense.referenceUa
        decision = f.sense.decision

        # Decision should be LRS if I_read > I_ref, else HRS
        expected_decision = "LRS" if i_read > i_ref else "HRS"
        passed = decision == expected_decision

        return CheckResult(
            ruleId=self.rule_id,
            passed=passed,
            severity=SeverityLevel.ERROR if not passed else SeverityLevel.INFO,
            message=f"Sense decision mismatch: I_read={i_read:.3f}µA, I_ref={i_ref:.3f}µA, "
                    f"expected {expected_decision}, got {decision}"
                    if not passed else f"Sense decision correct: {decision}",
            details={"i_read": i_read, "i_ref": i_ref, "expected": expected_decision, "actual": decision}
        )


# ─── Check Engine ─────────────────────────────────────────────────────

class CheckEngine:
    """
    Executes all invariants on a FrameState and returns CheckResults.
    """

    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        self.invariants: list[Invariant] = [
            INV001_VRramNodeConsistency(),
            INV002_TransistorGating(),
            INV003_CurrentDirection(),
            INV004_Compliance(),
            INV005_ReadNonDestructive(),
            INV006_StateWindows(),
            INV007_FormingPrerequisite(),
            INV008_NoSpontaneousSwitching(),
            INV009_SenseConsistency(),
        ]

    def check_frame(self, frame: FrameState, prev_frame: FrameState | None = None) -> list[CheckResult]:
        """Run all invariants on a frame and return results."""
        ctx = InvariantContext(frame=frame, profile=self.profile, prev_frame=prev_frame)
        return [inv.check(ctx) for inv in self.invariants]

    def check_all_passed(self, results: list[CheckResult]) -> bool:
        """Check if all invariants passed."""
        return all(r.passed for r in results)

    def get_failures(self, results: list[CheckResult]) -> list[CheckResult]:
        """Get only failed invariants."""
        return [r for r in results if not r.passed]
