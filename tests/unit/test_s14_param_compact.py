"""S14: ParamCompactAdapter (F1) Tests"""
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


class TestF1ModelInitialization:
    """Test F1 model initialization."""

    def test_initial_gap_is_midrange(self, profile):
        """Initial gap should be between min and max."""
        model = ParamCompactAdapter(profile)
        assert model.gap_min_nm < model.state.gap_nm < model.gap_max_nm

    def test_initial_filament_proxy_is_valid(self, profile):
        """Initial filament proxy should be in [0, 1]."""
        model = ParamCompactAdapter(profile)
        assert 0.0 <= model.state.filament_proxy <= 1.0

    def test_initial_temperature_is_ambient(self, profile):
        """Initial temperature should be ambient."""
        model = ParamCompactAdapter(profile)
        assert model.state.temperature_k == model.t_ambient_k


class TestF1GapEvolution:
    """Test gap evolution during operations."""

    def test_gap_shrinks_during_set(self, profile):
        """Gap should shrink during SET operation."""
        model = ParamCompactAdapter(profile)
        initial_gap = model.state.gap_nm

        # Apply SET voltage
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

        assert model.state.gap_nm < initial_gap

    def test_gap_grows_during_reset(self, profile):
        """Gap should grow during RESET operation."""
        model = ParamCompactAdapter(profile)
        # Start with small gap (LRS-like)
        model.state.gap_nm = 1.0
        initial_gap = model.state.gap_nm

        # Apply RESET voltage
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

        assert model.state.gap_nm > initial_gap

    def test_gap_bounded_by_min_max(self, profile):
        """Gap should stay within [gap_min, gap_max]."""
        model = ParamCompactAdapter(profile)

        # Try to shrink gap below min
        for _ in range(100):
            nodes = NodeVoltages(wl=[1.8], bl=[5.0], sl=[0.0])
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

        assert model.state.gap_nm >= model.gap_min_nm

        # Try to grow gap above max
        for _ in range(100):
            nodes = NodeVoltages(wl=[1.8], bl=[-5.0], sl=[0.0])
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

        assert model.state.gap_nm <= model.gap_max_nm


class TestF1ResistanceMapping:
    """Test resistance mapping from gap."""

    def test_resistance_increases_with_gap(self, profile):
        """Resistance should increase monotonically with gap."""
        model = ParamCompactAdapter(profile)

        r_small = model._gap_to_resistance(1.0)
        r_large = model._gap_to_resistance(5.0)

        assert r_large > r_small

    def test_filament_proxy_decreases_with_gap(self, profile):
        """Filament proxy should decrease with gap."""
        model = ParamCompactAdapter(profile)

        f_small = model._gap_to_filament(1.0)
        f_large = model._gap_to_filament(5.0)

        assert f_small > f_large


class TestF1FrameOutput:
    """Test F1 frame output includes observables."""

    def test_frame_includes_gap_nm(self, profile):
        """Frame should include gap_nm observable."""
        model = ParamCompactAdapter(profile)
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        frame = model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        assert frame.cell.rram.gapNm is not None
        assert frame.cell.rram.gapNm > 0

    def test_frame_includes_filament_proxy(self, profile):
        """Frame should include filament_proxy observable."""
        model = ParamCompactAdapter(profile)
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        frame = model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        assert frame.cell.rram.filamentProxy is not None
        assert 0.0 <= frame.cell.rram.filamentProxy <= 1.0

    def test_frame_includes_temperature(self, profile):
        """Frame should include temperature observable."""
        model = ParamCompactAdapter(profile)
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        frame = model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True,
        )

        assert frame.cell.rram.temperatureK is not None
        assert frame.cell.rram.temperatureK >= model.t_ambient_k

    def test_fidelity_is_f1(self, profile):
        """Frame should report F1 fidelity."""
        model = ParamCompactAdapter(profile)
        nodes = NodeVoltages(wl=[0.0], bl=[0.0], sl=[0.0])

        frame = model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.READ,
            phase=OperationPhase.PREPARE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.PRISTINE,
            forming_done=False,
        )

        assert frame.model.fidelity == "F1"


class TestF1Reset:
    """Test F1 model reset."""

    def test_reset_restores_initial_state(self, profile):
        """Reset should restore initial gap and temperature."""
        model = ParamCompactAdapter(profile)
        initial_gap = model.state.gap_nm
        initial_temp = model.state.temperature_k

        # Modify state
        model.state.gap_nm = 1.0
        model.state.temperature_k = 400.0

        model.reset()

        assert model.state.gap_nm == initial_gap
        assert model.state.temperature_k == initial_temp
