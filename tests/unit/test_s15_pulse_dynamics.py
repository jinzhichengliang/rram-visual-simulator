"""S15: Pulse Dynamics Tests"""
import pytest
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
from simulator.models.param_compact_model import ParamCompactAdapter


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


class TestPulseAmplitudeEffect:
    """Test pulse amplitude effect on gap evolution."""

    def test_higher_voltage_causes_faster_gap_change(self, profile):
        """Higher voltage should cause faster gap change."""
        model_low = ParamCompactAdapter(profile)
        model_high = ParamCompactAdapter(profile)

        # Apply low SET voltage
        nodes_low = NodeVoltages(wl=[1.8], bl=[1.6], sl=[0.0])
        model_low.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes_low,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        # Apply high SET voltage
        nodes_high = NodeVoltages(wl=[1.8], bl=[3.0], sl=[0.0])
        model_high.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes_high,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        # Higher voltage should cause more gap shrinkage
        gap_shrink_low = 5.0 - model_low.state.gap_nm
        gap_shrink_high = 5.0 - model_high.state.gap_nm
        assert gap_shrink_high > gap_shrink_low

    def test_below_threshold_no_gap_change(self, profile):
        """Voltage below threshold should not change gap."""
        model = ParamCompactAdapter(profile)
        initial_gap = model.state.gap_nm

        # Apply voltage below SET threshold
        nodes = NodeVoltages(wl=[1.8], bl=[1.0], sl=[0.0])  # 1.0V < 1.5V threshold
        model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        assert model.state.gap_nm == initial_gap


class TestPulseWidthEffect:
    """Test pulse width effect on gap evolution."""

    def test_longer_pulse_causes_more_gap_change(self, profile):
        """More pulses (longer effective width) should cause more gap change."""
        model = ParamCompactAdapter(profile)
        initial_gap = model.state.gap_nm

        # Apply multiple SET pulses
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])
        for i in range(5):
            model.compute_frame(
                frame_id=f"f{i}",
                time_ns=i * 10.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )

        # Gap should have shrunk (even if very small amount)
        assert model.state.gap_nm < initial_gap


class TestGradualSetReset:
    """Test gradual SET/RESET with multiple pulses."""

    def test_gradual_set_with_multiple_pulses(self, profile):
        """Multiple SET pulses should gradually shrink gap."""
        model = ParamCompactAdapter(profile)
        initial_gap = model.state.gap_nm

        gaps = [initial_gap]
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        # Apply multiple SET pulses
        for i in range(10):
            model.compute_frame(
                frame_id=f"f{i}",
                time_ns=i * 10.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )
            gaps.append(model.state.gap_nm)

        # Gap should monotonically decrease
        for i in range(len(gaps) - 1):
            assert gaps[i + 1] <= gaps[i]

    def test_gradual_reset_with_multiple_pulses(self, profile):
        """Multiple RESET pulses should gradually grow gap."""
        model = ParamCompactAdapter(profile)
        # Start with small gap (LRS-like)
        model.state.gap_nm = 1.0
        initial_gap = model.state.gap_nm

        gaps = [initial_gap]
        nodes = NodeVoltages(wl=[1.8], bl=[-2.0], sl=[0.0])

        # Apply multiple RESET pulses
        for i in range(10):
            model.compute_frame(
                frame_id=f"f{i}",
                time_ns=i * 10.0,
                operation=OperationType.RESET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.LRS,
                forming_done=True,
            )
            gaps.append(model.state.gap_nm)

        # Gap should monotonically increase
        for i in range(len(gaps) - 1):
            assert gaps[i + 1] >= gaps[i]


class TestResistanceEvolution:
    """Test resistance evolution with gap."""

    def test_resistance_decreases_during_set(self, profile):
        """Resistance should decrease as gap shrinks during SET."""
        model = ParamCompactAdapter(profile)
        initial_r = model._gap_to_resistance(model.state.gap_nm)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])
        model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        final_r = model._gap_to_resistance(model.state.gap_nm)
        assert final_r < initial_r

    def test_resistance_increases_during_reset(self, profile):
        """Resistance should increase as gap grows during RESET."""
        model = ParamCompactAdapter(profile)
        model.state.gap_nm = 1.0  # Start with small gap
        initial_r = model._gap_to_resistance(model.state.gap_nm)

        nodes = NodeVoltages(wl=[1.8], bl=[-2.0], sl=[0.0])
        model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.RESET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.LRS,
            forming_done=True,
        )

        final_r = model._gap_to_resistance(model.state.gap_nm)
        assert final_r > initial_r
