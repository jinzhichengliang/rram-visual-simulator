"""S11: Sense Margin Tests (G-06)"""
import pytest
from packages.contracts.types import DeviceProfile, OperationType
from simulator.core.peripheral import SenseAmplifier


@pytest.fixture
def profile():
    """Standard bipolar teaching profile."""
    return DeviceProfile(
        id="bipolar_teaching_v1",
        version="1.0.0",
        stackOrientation="BL-RRAM-NMOS-SL",
        vRramSignConvention="V(top)-V(bottom)",
        setPolarity="V_RRAM > 0",
        resetPolarity="V_RRAM < 0",
        logicMap={"LRS": 1, "HRS": 0},
        ranges={
            "vRead": [0.1, 0.2],
            "vSet": [1.5, 2.5],
            "vReset": [-2.5, -1.5],
            "vForm": [3.0, 4.0],
            "rLrs": [10000, 50000],
            "rHrs": [500000, 5000000],
        },
        complianceUa=50.0,
        tolerances={
            "readDisturbPct": 1.0,
            "currentConservationPct": 5.0,
            "crossViewAbs": 0.001,
        },
    )


class TestG06_SenseMargin:
    """G-06: Sense Margin verification."""

    def test_sense_lrs_high_current(self, profile):
        """LRS should produce high read current."""
        sense = SenseAmplifier(profile)

        # LRS resistance: 10k-50kΩ, read voltage: 0.1-0.2V
        # Expected current: 0.1V / 50kΩ = 2µA to 0.2V / 10kΩ = 20µA
        result = sense.sense(read_current_ua=10.0)

        assert result.decision == "LRS"
        assert result.current_ua == 10.0
        assert result.margin_ua > 0

    def test_sense_hrs_low_current(self, profile):
        """HRS should produce low read current."""
        sense = SenseAmplifier(profile)

        # HRS resistance: 500k-5MΩ, read voltage: 0.1-0.2V
        # Expected current: 0.1V / 5MΩ = 0.02µA to 0.2V / 500kΩ = 0.4µA
        result = sense.sense(read_current_ua=0.1)

        assert result.decision == "HRS"
        assert result.current_ua == 0.1
        assert result.margin_ua > 0

    def test_sense_reference_current(self, profile):
        """Reference current should be between HRS and LRS currents."""
        sense = SenseAmplifier(profile)

        # Reference should be midpoint between HRS and LRS read currents
        # HRS: ~0.02-0.4µA, LRS: ~2-20µA
        # Reference: ~1-10µA
        assert 0.5 < sense.reference_ua < 15.0

    def test_sense_margin_sufficient_for_clear_states(self, profile):
        """Clear LRS/HRS states should have sufficient margin."""
        sense = SenseAmplifier(profile)

        # Clear LRS
        lrs_result = sense.sense(read_current_ua=10.0)
        assert lrs_result.passed is True

        # Clear HRS
        hrs_result = sense.sense(read_current_ua=0.1)
        assert hrs_result.passed is True

    def test_sense_margin_insufficient_near_reference(self, profile):
        """Current near reference should have insufficient margin."""
        sense = SenseAmplifier(profile)

        # Current very close to reference
        result = sense.sense(read_current_ua=sense.reference_ua + 0.01)

        # Should still make a decision, but margin may be insufficient
        assert result.decision in ["LRS", "HRS"]
        # Margin should be very small
        assert result.margin_ua < 1.0

    def test_sense_logic_mapping(self, profile):
        """Sense decision should map to correct logic value."""
        sense = SenseAmplifier(profile)

        # LRS → logic 1
        lrs_result = sense.sense(read_current_ua=10.0)
        assert lrs_result.decision == "LRS"
        assert profile.logicMap.LRS == 1

        # HRS → logic 0
        hrs_result = sense.sense(read_current_ua=0.1)
        assert hrs_result.decision == "HRS"
        assert profile.logicMap.HRS == 0
