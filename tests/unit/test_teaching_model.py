"""S02 — Teaching Model (F0) unit tests.

Tests the deterministic teaching model for:
- Transistor state computation
- V_RRAM / I_RRAM computation
- Compliance limiting
- State transitions (FORMING, SET, RESET)
- READ non-destructive invariant
- Polarity parametrization
- Determinism
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
    NodeVoltages,
    OperationPhase,
    OperationType,
    Polarity,
    StackOrientation,
)
from simulator.models.teaching_model import TeachingModelAdapter


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


class TestTransistorState:
    """Test access transistor state computation."""

    def test_transistor_on_when_wl_high(self, teaching_profile):
        """Transistor should turn ON when WL > Vth."""
        model = TeachingModelAdapter(teaching_profile)
        transistor = model.compute_transistor_state(
            wl_voltage=1.8,  # Above Vth (0.7V)
            bl_voltage=2.0,
            sl_voltage=0.0,
        )
        assert transistor.on is True
        assert transistor.vg == 1.8

    def test_transistor_off_when_wl_low(self, teaching_profile):
        """Transistor should stay OFF when WL < Vth."""
        model = TeachingModelAdapter(teaching_profile)
        transistor = model.compute_transistor_state(
            wl_voltage=0.0,  # Below Vth
            bl_voltage=2.0,
            sl_voltage=0.0,
        )
        assert transistor.on is False


class TestVRRAMComputation:
    """Test V_RRAM computation."""

    def test_v_rram_positive_when_bl_high(self, teaching_profile):
        """V_RRAM should be positive when BL > SL (for positive polarity)."""
        model = TeachingModelAdapter(teaching_profile)
        transistor = model.compute_transistor_state(1.8, 2.0, 0.0)
        v_rram = model.compute_v_rram(2.0, transistor, 0.0)
        assert v_rram > 0

    def test_v_rram_zero_when_bl_equals_sl(self, teaching_profile):
        """V_RRAM should be zero when BL = SL."""
        model = TeachingModelAdapter(teaching_profile)
        transistor = model.compute_transistor_state(1.8, 0.0, 0.0)
        v_rram = model.compute_v_rram(0.0, transistor, 0.0)
        assert v_rram == 0.0


class TestIRRAMComputation:
    """Test I_RRAM computation."""

    def test_i_rram_zero_when_transistor_off(self, teaching_profile):
        """Current should be zero when transistor is OFF."""
        model = TeachingModelAdapter(teaching_profile)
        i_rram = model.compute_i_rram(
            v_rram=2.0,
            r_rram=10000,
            transistor_on=False,
        )
        assert i_rram == 0.0

    def test_i_rram_follows_ohms_law(self, teaching_profile):
        """Current should follow I = V/R when transistor is ON."""
        model = TeachingModelAdapter(teaching_profile)
        i_rram = model.compute_i_rram(
            v_rram=2.0,  # 2V
            r_rram=100000,  # 100kΩ
            transistor_on=True,
        )
        # I = 2V / 100kΩ = 20µA
        assert abs(i_rram - 20.0) < 0.001


class TestCompliance:
    """Test compliance current limiting."""

    def test_compliance_limits_current(self, teaching_profile):
        """Current should be limited to compliance value."""
        model = TeachingModelAdapter(teaching_profile)
        limited, active = model.apply_compliance(100.0)  # 100µA > 50µA limit
        assert limited == 50.0
        assert active is True

    def test_compliance_passes_when_below_limit(self, teaching_profile):
        """Current should pass through when below limit."""
        model = TeachingModelAdapter(teaching_profile)
        limited, active = model.apply_compliance(30.0)  # 30µA < 50µA limit
        assert limited == 30.0
        assert active is False


class TestStateTransitions:
    """Test device state transitions."""

    def test_pristine_to_lrs_on_forming(self, teaching_profile):
        """PRISTINE should transition to LRS after successful forming."""
        model = TeachingModelAdapter(teaching_profile)
        new_state, forming_done = model.determine_state_transition(
            current_state=DeviceState.PRISTINE,
            v_rram=3.5,  # Within forming range [3.0, 4.0]
            i_rram=40.0,
            operation=OperationType.FORMING,
            forming_done=False,
        )
        assert new_state == DeviceState.LRS
        assert forming_done is True

    def test_pristine_stays_on_insufficient_forming(self, teaching_profile):
        """PRISTINE should not transition if forming voltage insufficient."""
        model = TeachingModelAdapter(teaching_profile)
        new_state, forming_done = model.determine_state_transition(
            current_state=DeviceState.PRISTINE,
            v_rram=1.0,  # Below forming range
            i_rram=10.0,
            operation=OperationType.FORMING,
            forming_done=False,
        )
        assert new_state == DeviceState.PRISTINE
        assert forming_done is False

    def test_hrs_to_lrs_on_set(self, teaching_profile):
        """HRS should transition to LRS on SET with correct polarity."""
        model = TeachingModelAdapter(teaching_profile)
        new_state, _ = model.determine_state_transition(
            current_state=DeviceState.HRS,
            v_rram=2.0,  # Within SET range [1.5, 2.5]
            i_rram=30.0,
            operation=OperationType.SET,
            forming_done=True,
        )
        assert new_state == DeviceState.LRS

    def test_lrs_to_hrs_on_reset(self, teaching_profile):
        """LRS should transition to HRS on RESET with correct polarity."""
        model = TeachingModelAdapter(teaching_profile)
        new_state, _ = model.determine_state_transition(
            current_state=DeviceState.LRS,
            v_rram=-2.0,  # Within RESET range [-2.5, -1.5]
            i_rram=-30.0,
            operation=OperationType.RESET,
            forming_done=True,
        )
        assert new_state == DeviceState.HRS

    def test_read_does_not_change_state(self, teaching_profile):
        """READ should not change device state (non-destructive)."""
        model = TeachingModelAdapter(teaching_profile)
        new_state, _ = model.determine_state_transition(
            current_state=DeviceState.HRS,
            v_rram=0.15,  # Within READ range
            i_rram=1.0,
            operation=OperationType.READ,
            forming_done=True,
        )
        assert new_state == DeviceState.HRS


class TestPolarityParametrization:
    """Test that polarity is configurable from profile."""

    def test_reversed_set_polarity(self, teaching_profile):
        """SET should work with reversed polarity profile."""
        # Create profile with reversed SET polarity
        reversed_profile = teaching_profile.model_copy()
        reversed_profile.setPolarity = Polarity.NEGATIVE
        reversed_profile.resetPolarity = Polarity.POSITIVE

        model = TeachingModelAdapter(reversed_profile)

        # SET should now require negative voltage
        new_state, _ = model.determine_state_transition(
            current_state=DeviceState.HRS,
            v_rram=-2.0,  # Negative voltage for SET
            i_rram=30.0,
            operation=OperationType.SET,
            forming_done=True,
        )
        assert new_state == DeviceState.LRS


class TestDeterminism:
    """Test that model is deterministic."""

    def test_same_input_same_output(self, teaching_profile):
        """Same input should always produce same output."""
        model1 = TeachingModelAdapter(teaching_profile, seed=42)
        model2 = TeachingModelAdapter(teaching_profile, seed=42)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        frame1 = model1.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        frame2 = model2.compute_frame(
            frame_id="f2",
            time_ns=0.0,
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        assert frame1.cell.rram.v == frame2.cell.rram.v
        assert frame1.cell.rram.i == frame2.cell.rram.i
        assert frame1.cell.rram.r == frame2.cell.rram.r


class TestSenseComputation:
    """Test sense amplifier logic."""

    def test_sense_correctly_identifies_lrs(self, teaching_profile):
        """Sense should identify LRS when current is high."""
        model = TeachingModelAdapter(teaching_profile)
        sense = model.compute_sense(
            i_rram=15.0,  # High current (LRS)
            state=DeviceState.LRS,
        )
        assert sense.decision == "LRS"
        assert sense.currentUa == 15.0

    def test_sense_correctly_identifies_hrs(self, teaching_profile):
        """Sense should identify HRS when current is low."""
        model = TeachingModelAdapter(teaching_profile)
        sense = model.compute_sense(
            i_rram=0.5,  # Low current (HRS)
            state=DeviceState.HRS,
        )
        assert sense.decision == "HRS"
        assert sense.currentUa == 0.5
