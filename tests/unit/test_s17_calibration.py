"""S17: F1 Calibration Gate Tests"""
import pytest
from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceState,
    DeviceTolerances,
    LogicMap,
    Polarity,
    StackOrientation,
)
from simulator.models.calibration import F1CalibrationGate


@pytest.fixture
def profile():
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


class TestCalibrationGate:
    """Test F1 calibration gate."""

    def test_calibration_r_lrs(self, profile):
        """Calibration should achieve target R_LRS."""
        gate = F1CalibrationGate(profile)
        r_lrs_actual = gate.calibrate_r_lrs()

        target_r_lrs = (profile.ranges.rLrs[0] + profile.ranges.rLrs[1]) / 2
        error_pct = abs(r_lrs_actual - target_r_lrs) / target_r_lrs * 100

        # Should be within 1% (calibration precision)
        assert error_pct < 1.0

    def test_calibration_r_hrs(self, profile):
        """Calibration should achieve target R_HRS."""
        gate = F1CalibrationGate(profile)
        r_hrs_actual = gate.calibrate_r_hrs()

        target_r_hrs = (profile.ranges.rHrs[0] + profile.ranges.rHrs[1]) / 2
        error_pct = abs(r_hrs_actual - target_r_hrs) / target_r_hrs * 100

        # Should be within 1% (calibration precision)
        assert error_pct < 1.0

    def test_calibration_v_set(self, profile):
        """Calibration should achieve target V_SET."""
        gate = F1CalibrationGate(profile)
        v_set_actual = gate.calibrate_v_set()

        target_v_set = (profile.ranges.vSet[0] + profile.ranges.vSet[1]) / 2

        # Should match exactly (direct assignment)
        assert abs(v_set_actual - target_v_set) < 0.01

    def test_calibration_v_reset(self, profile):
        """Calibration should achieve target V_RESET."""
        gate = F1CalibrationGate(profile)
        v_reset_actual = gate.calibrate_v_reset()

        target_v_reset = (profile.ranges.vReset[0] + profile.ranges.vReset[1]) / 2

        # Should match exactly (direct assignment)
        assert abs(abs(v_reset_actual) - abs(target_v_reset)) < 0.01

    def test_full_calibration_passes(self, profile):
        """Full calibration should pass with default tolerances."""
        gate = F1CalibrationGate(profile)
        result = gate.run_calibration()

        assert result.passed is True
        assert result.r_lrs_error_pct < gate.r_tolerance_pct
        assert result.r_hrs_error_pct < gate.r_tolerance_pct
        assert result.v_set_error_pct < gate.v_tolerance_pct
        assert result.v_reset_error_pct < gate.v_tolerance_pct

    def test_calibration_report_generation(self, profile):
        """Calibration should generate readable report."""
        gate = F1CalibrationGate(profile)
        result = gate.run_calibration()
        report = gate.generate_report(result)

        assert "F1 Calibration Report" in report
        assert "R_LRS" in report
        assert "R_HRS" in report
        assert "V_SET" in report
        assert "V_RESET" in report
        assert "PASSED" in report or "FAILED" in report

    def test_calibration_result_contains_all_fields(self, profile):
        """Calibration result should contain all required fields."""
        gate = F1CalibrationGate(profile)
        result = gate.run_calibration()

        assert hasattr(result, "r_lrs_target")
        assert hasattr(result, "r_lrs_actual")
        assert hasattr(result, "r_lrs_error_pct")
        assert hasattr(result, "r_hrs_target")
        assert hasattr(result, "r_hrs_actual")
        assert hasattr(result, "r_hrs_error_pct")
        assert hasattr(result, "v_set_target")
        assert hasattr(result, "v_set_actual")
        assert hasattr(result, "v_set_error_pct")
        assert hasattr(result, "v_reset_target")
        assert hasattr(result, "v_reset_actual")
        assert hasattr(result, "v_reset_error_pct")
        assert hasattr(result, "passed")

    def test_calibration_updates_model_parameters(self, profile):
        """Calibration should update model parameters."""
        gate = F1CalibrationGate(profile)

        # Store initial parameters
        initial_gap_min = gate.model.gap_min_nm
        initial_gap_max = gate.model.gap_max_nm

        # Run calibration
        gate.run_calibration()

        # Parameters should have changed
        assert gate.model.gap_min_nm != initial_gap_min or gate.model.gap_max_nm != initial_gap_max
