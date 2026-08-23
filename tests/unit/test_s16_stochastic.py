"""S16: Stochastic Hook Tests"""
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


class TestStochasticDisabled:
    """Test that stochastic is disabled by default."""

    def test_stochastic_disabled_by_default(self, profile):
        """Stochastic should be disabled by default."""
        model = ParamCompactAdapter(profile)
        assert model.enable_stochastic is False

    def test_deterministic_when_stochastic_disabled(self, profile):
        """Same seed should produce identical results when stochastic is disabled."""
        model1 = ParamCompactAdapter(profile, seed=42, enable_stochastic=False)
        model2 = ParamCompactAdapter(profile, seed=42, enable_stochastic=False)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        # Apply same operation to both models
        for _ in range(5):
            model1.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )
            model2.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )

        # Should be identical
        assert model1.state.gap_nm == model2.state.gap_nm


class TestStochasticEnabled:
    """Test stochastic behavior when enabled."""

    def test_stochastic_can_be_enabled(self, profile):
        """Stochastic should be configurable."""
        model = ParamCompactAdapter(profile, enable_stochastic=True)
        assert model.enable_stochastic is True

    def test_different_seeds_produce_different_results(self, profile):
        """Different seeds should produce different results when stochastic is enabled."""
        model1 = ParamCompactAdapter(profile, seed=42, enable_stochastic=True)
        model2 = ParamCompactAdapter(profile, seed=123, enable_stochastic=True)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        # Apply same operation to both models
        for _ in range(10):
            model1.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )
            model2.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )

        # Should be different (with high probability)
        # Note: There's a tiny chance they could be equal, but very unlikely
        assert model1.state.gap_nm != model2.state.gap_nm

    def test_same_seed_produces_same_results(self, profile):
        """Same seed should produce identical results when stochastic is enabled."""
        model1 = ParamCompactAdapter(profile, seed=42, enable_stochastic=True)
        model2 = ParamCompactAdapter(profile, seed=42, enable_stochastic=True)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        # Apply same operation to both models
        for _ in range(10):
            model1.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )
            model2.compute_frame(
                frame_id="f1",
                time_ns=0.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                current_state=DeviceState.HRS,
                forming_done=True,
            )

        # Should be identical
        assert model1.state.gap_nm == model2.state.gap_nm

    def test_stochastic_variation_is_bounded(self, profile):
        """Stochastic variation should not cause extreme values."""
        model = ParamCompactAdapter(profile, seed=42, enable_stochastic=True)

        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])

        # Apply many operations
        for _ in range(100):
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

        # Gap should still be within bounds
        assert model.gap_min_nm <= model.state.gap_nm <= model.gap_max_nm


class TestTemperatureEffect:
    """Test temperature effects."""

    def test_temperature_increases_with_power(self, profile):
        """Temperature should increase when power is dissipated."""
        model = ParamCompactAdapter(profile)
        initial_temp = model.state.temperature_k

        # Apply voltage/current to generate power
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

        # Temperature should have increased
        assert model.state.temperature_k >= initial_temp

    def test_temperature_returns_to_ambient_when_idle(self, profile):
        """Temperature should be at ambient when no power is dissipated."""
        model = ParamCompactAdapter(profile)

        # No operations, just read at idle
        nodes = NodeVoltages(wl=[0.0], bl=[0.0], sl=[0.0])
        model.compute_frame(
            frame_id="f1",
            time_ns=0.0,
            operation=OperationType.READ,
            phase=OperationPhase.PREPARE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.PRISTINE,
            forming_done=False,
        )

        # Temperature should be at ambient
        assert model.state.temperature_k == model.t_ambient_k
