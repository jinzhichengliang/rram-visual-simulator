"""
F1 Calibration Gate — Calibrate F1 model parameters to match targets.

V0.4 S17: Provides calibration tools to tune F1 model parameters.
- Calibrate R_LRS/R_HRS windows
- Calibrate V_SET/V_RESET thresholds
- Generate calibration report
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from packages.contracts.types import (
    DeviceProfile,
    DeviceState,
    NodeVoltages,
    OperationPhase,
    OperationType,
)
from simulator.models.param_compact_model import ParamCompactAdapter


@dataclass
class CalibrationResult:
    """Result of calibration."""
    r_lrs_target: tuple[float, float]
    r_lrs_actual: float
    r_lrs_error_pct: float

    r_hrs_target: tuple[float, float]
    r_hrs_actual: float
    r_hrs_error_pct: float

    v_set_target: tuple[float, float]
    v_set_actual: float
    v_set_error_pct: float

    v_reset_target: tuple[float, float]
    v_reset_actual: float
    v_reset_error_pct: float

    passed: bool


class F1CalibrationGate:
    """
    F1 Calibration Gate — calibrates F1 model to match target specifications.
    """

    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        self.model = ParamCompactAdapter(profile, seed=seed)

        # Calibration tolerances
        self.r_tolerance_pct = 20.0  # 20% tolerance for resistance
        self.v_tolerance_pct = 15.0  # 15% tolerance for voltage

    def calibrate_r_lrs(self) -> float:
        """
        Calibrate R_LRS by adjusting gap_min_nm.

        Returns actual R_LRS achieved.
        """
        target_r_lrs = (self.profile.ranges.rLrs[0] + self.profile.ranges.rLrs[1]) / 2

        # Binary search for gap_min that gives target R_LRS
        # R = R_0 * exp(gap / gap_0), so gap = gap_0 * ln(R / R_0)
        # For R_LRS = 30kΩ, R_0 = 1kΩ, gap_0 = 1nm: gap ≈ 3.4nm
        gap_low = 0.01
        gap_high = 5.0  # Increased from 1.0

        for _ in range(50):  # Max iterations
            gap_mid = (gap_low + gap_high) / 2
            r_actual = self.model._gap_to_resistance(gap_mid)

            if abs(r_actual - target_r_lrs) / target_r_lrs < 0.01:  # 1% tolerance
                break

            if r_actual < target_r_lrs:
                gap_low = gap_mid
            else:
                gap_high = gap_mid

        # Update model parameter
        self.model.gap_min_nm = gap_mid

        return self.model._gap_to_resistance(self.model.gap_min_nm)

    def calibrate_r_hrs(self) -> float:
        """
        Calibrate R_HRS by adjusting gap_max_nm.

        Returns actual R_HRS achieved.
        """
        target_r_hrs = (self.profile.ranges.rHrs[0] + self.profile.ranges.rHrs[1]) / 2

        # Binary search for gap_max that gives target R_HRS
        gap_low = 5.0
        gap_high = 20.0

        for _ in range(50):  # Max iterations
            gap_mid = (gap_low + gap_high) / 2
            r_actual = self.model._gap_to_resistance(gap_mid)

            if abs(r_actual - target_r_hrs) / target_r_hrs < 0.01:  # 1% tolerance
                break

            if r_actual < target_r_hrs:
                gap_low = gap_mid
            else:
                gap_high = gap_mid

        # Update model parameter
        self.model.gap_max_nm = gap_mid

        return self.model._gap_to_resistance(self.model.gap_max_nm)

    def calibrate_v_set(self) -> float:
        """
        Calibrate V_SET threshold.

        Returns actual V_SET achieved.
        """
        target_v_set = (self.profile.ranges.vSet[0] + self.profile.ranges.vSet[1]) / 2

        # Adjust v_set_threshold_v to match target
        self.model.v_set_threshold_v = target_v_set

        return self.model.v_set_threshold_v

    def calibrate_v_reset(self) -> float:
        """
        Calibrate V_RESET threshold.

        Returns actual V_RESET achieved.
        """
        target_v_reset = (self.profile.ranges.vReset[0] + self.profile.ranges.vReset[1]) / 2

        # Adjust v_reset_threshold_v to match target
        self.model.v_reset_threshold_v = target_v_reset

        return self.model.v_reset_threshold_v

    def run_calibration(self) -> CalibrationResult:
        """
        Run full calibration and return results.
        """
        # Calibrate R_LRS
        r_lrs_actual = self.calibrate_r_lrs()
        r_lrs_target = self.profile.ranges.rLrs
        r_lrs_mid = (r_lrs_target[0] + r_lrs_target[1]) / 2
        r_lrs_error_pct = abs(r_lrs_actual - r_lrs_mid) / r_lrs_mid * 100

        # Calibrate R_HRS
        r_hrs_actual = self.calibrate_r_hrs()
        r_hrs_target = self.profile.ranges.rHrs
        r_hrs_mid = (r_hrs_target[0] + r_hrs_target[1]) / 2
        r_hrs_error_pct = abs(r_hrs_actual - r_hrs_mid) / r_hrs_mid * 100

        # Calibrate V_SET
        v_set_actual = self.calibrate_v_set()
        v_set_target = self.profile.ranges.vSet
        v_set_mid = (v_set_target[0] + v_set_target[1]) / 2
        v_set_error_pct = abs(v_set_actual - v_set_mid) / v_set_mid * 100

        # Calibrate V_RESET
        v_reset_actual = self.calibrate_v_reset()
        v_reset_target = self.profile.ranges.vReset
        v_reset_mid = (abs(v_reset_target[0]) + abs(v_reset_target[1])) / 2
        v_reset_error_pct = abs(abs(v_reset_actual) - v_reset_mid) / v_reset_mid * 100

        # Check if calibration passed
        passed = (
            r_lrs_error_pct < self.r_tolerance_pct
            and r_hrs_error_pct < self.r_tolerance_pct
            and v_set_error_pct < self.v_tolerance_pct
            and v_reset_error_pct < self.v_tolerance_pct
        )

        return CalibrationResult(
            r_lrs_target=r_lrs_target,
            r_lrs_actual=r_lrs_actual,
            r_lrs_error_pct=r_lrs_error_pct,
            r_hrs_target=r_hrs_target,
            r_hrs_actual=r_hrs_actual,
            r_hrs_error_pct=r_hrs_error_pct,
            v_set_target=v_set_target,
            v_set_actual=v_set_actual,
            v_set_error_pct=v_set_error_pct,
            v_reset_target=v_reset_target,
            v_reset_actual=v_reset_actual,
            v_reset_error_pct=v_reset_error_pct,
            passed=passed,
        )

    def generate_report(self, result: CalibrationResult) -> str:
        """Generate calibration report."""
        lines = [
            "=" * 60,
            "F1 Calibration Report",
            "=" * 60,
            "",
            f"R_LRS Target: {result.r_lrs_target[0]:.0f} - {result.r_lrs_target[1]:.0f} Ω",
            f"R_LRS Actual: {result.r_lrs_actual:.0f} Ω",
            f"R_LRS Error:  {result.r_lrs_error_pct:.1f}% (tolerance: {self.r_tolerance_pct}%)",
            "",
            f"R_HRS Target: {result.r_hrs_target[0]:.0f} - {result.r_hrs_target[1]:.0f} Ω",
            f"R_HRS Actual: {result.r_hrs_actual:.0f} Ω",
            f"R_HRS Error:  {result.r_hrs_error_pct:.1f}% (tolerance: {self.r_tolerance_pct}%)",
            "",
            f"V_SET Target: {result.v_set_target[0]:.1f} - {result.v_set_target[1]:.1f} V",
            f"V_SET Actual: {result.v_set_actual:.2f} V",
            f"V_SET Error:  {result.v_set_error_pct:.1f}% (tolerance: {self.v_tolerance_pct}%)",
            "",
            f"V_RESET Target: {result.v_reset_target[0]:.1f} - {result.v_reset_target[1]:.1f} V",
            f"V_RESET Actual: {result.v_reset_actual:.2f} V",
            f"V_RESET Error:  {result.v_reset_error_pct:.1f}% (tolerance: {self.v_tolerance_pct}%)",
            "",
            "=" * 60,
            f"Calibration: {'PASSED' if result.passed else 'FAILED'}",
            "=" * 60,
        ]
        return "\n".join(lines)
