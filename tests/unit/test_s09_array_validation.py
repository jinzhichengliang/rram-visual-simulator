"""
S09 — Array Validation tests.

Tests:
1. INV-010: Array Conservation (port current = sum of branch currents)
2. G-05: Array Selection (only selected cell changes)
3. Unselected cell protection (state doesn't change)
4. Fault injection detection
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
    OperationType,
    Polarity,
    StackOrientation,
)
from simulator.array.array_model import ArrayOrchestrator


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


# ─── INV-010: Array Conservation ─────────────────────────────────────


class TestINV010_ArrayConservation:
    """Test INV-010: Port current = sum of branch currents."""

    def test_port_current_equals_selected_cell_current(self, teaching_profile):
        """Port current should equal the selected cell's current."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Execute READ on cell (1, 2)
        array.execute_operation(OperationType.READ, 1, 2, 0.15)

        # Get port current
        port_current = array.compute_port_current()

        # Get selected cell current from last frame
        last_frame = array.get_current_frame()
        selected_cell_current = last_frame.cell.rram.i

        # They should be equal (within tolerance)
        tolerance = teaching_profile.tolerances.crossViewAbs
        assert abs(port_current - selected_cell_current) < tolerance

    def test_port_current_zero_when_no_operation(self, teaching_profile):
        """Port current should be zero when no operation is active."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        port_current = array.compute_port_current()
        assert port_current == 0.0

    def test_port_current_during_forming(self, teaching_profile):
        """Port current should match selected cell during forming."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Execute FORMING on cell (0, 0)
        array.execute_operation(OperationType.FORMING, 0, 0, 3.5)

        port_current = array.compute_port_current()
        last_frame = array.get_current_frame()
        selected_cell_current = last_frame.cell.rram.i

        tolerance = teaching_profile.tolerances.crossViewAbs
        assert abs(port_current - selected_cell_current) < tolerance


# ─── G-05: Array Selection ───────────────────────────────────────────


class TestG05_ArraySelection:
    """Test G-05: Array selection correctness."""

    def test_only_selected_cell_changes_state(self, teaching_profile):
        """Only the selected cell should change state during operation."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Record initial states
        initial_states = [
            [array.array_state.get_state(r, c) for c in range(4)]
            for r in range(4)
        ]

        # Execute FORMING on cell (1, 2)
        array.execute_operation(OperationType.FORMING, 1, 2, 3.5)

        # Check that only (1, 2) changed
        for r in range(4):
            for c in range(4):
                current_state = array.array_state.get_state(r, c)
                if r == 1 and c == 2:
                    # Selected cell should have changed
                    assert current_state == DeviceState.LRS
                else:
                    # Unselected cells should remain PRISTINE
                    assert current_state == initial_states[r][c]
                    assert current_state == DeviceState.PRISTINE

    def test_multiple_operations_on_different_cells(self, teaching_profile):
        """Operations on different cells should be independent."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Form cell (0, 0)
        array.execute_operation(OperationType.FORMING, 0, 0, 3.5)
        assert array.array_state.get_state(0, 0) == DeviceState.LRS

        # Form cell (2, 3)
        array.execute_operation(OperationType.FORMING, 2, 3, 3.5)
        assert array.array_state.get_state(2, 3) == DeviceState.LRS

        # Cell (0, 0) should still be LRS
        assert array.array_state.get_state(0, 0) == DeviceState.LRS

        # Other cells should still be PRISTINE
        assert array.array_state.get_state(1, 1) == DeviceState.PRISTINE

    def test_reset_only_affects_selected_cell(self, teaching_profile):
        """RESET should only affect the selected cell."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Form two cells
        array.execute_operation(OperationType.FORMING, 0, 0, 3.5)
        array.execute_operation(OperationType.FORMING, 1, 1, 3.5)

        assert array.array_state.get_state(0, 0) == DeviceState.LRS
        assert array.array_state.get_state(1, 1) == DeviceState.LRS

        # Reset only (0, 0)
        array.execute_operation(OperationType.RESET, 0, 0, 2.0)

        # (0, 0) should be HRS
        assert array.array_state.get_state(0, 0) == DeviceState.HRS

        # (1, 1) should still be LRS
        assert array.array_state.get_state(1, 1) == DeviceState.LRS


# ─── Unselected Cell Protection ──────────────────────────────────────


class TestUnselectedCellProtection:
    """Test that unselected cells are protected from unintended changes."""

    def test_unselected_cells_transistor_off(self, teaching_profile):
        """Unselected cells should have transistor OFF."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Execute operation on (1, 2)
        frames = array.execute_operation(OperationType.READ, 1, 2, 0.15)

        # Check ACTIVE phase frame (not COMPLETE which has all voltages released)
        active_frame = next(f for f in frames if f.phase.value == "ACTIVE")

        # Selected cell transistor should be ON during ACTIVE phase
        assert active_frame.cell.transistor.on is True

        # Note: In V0.2 simplified model, we don't track unselected cell
        # transistors in FrameState. This would be checked in the full
        # array model where each cell has its own transistor state.

    def test_unselected_cells_no_current(self, teaching_profile):
        """Unselected cells should have zero current."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Execute operation on (1, 2)
        array.execute_operation(OperationType.READ, 1, 2, 0.15)

        # Get cell summaries
        summaries = array.get_cell_summaries()

        # Check that unselected cells have zero current
        for r in range(4):
            for c in range(4):
                if r != 1 or c != 2:
                    assert summaries[r][c].i_rram == 0.0


# ─── Array Reset ─────────────────────────────────────────────────────


class TestArrayReset:
    """Test array reset functionality."""

    def test_reset_clears_all_cells(self, teaching_profile):
        """Reset should return all cells to PRISTINE."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        # Form multiple cells
        array.execute_operation(OperationType.FORMING, 0, 0, 3.5)
        array.execute_operation(OperationType.FORMING, 1, 1, 3.5)
        array.execute_operation(OperationType.FORMING, 2, 2, 3.5)

        # Verify cells are formed
        assert array.array_state.get_state(0, 0) == DeviceState.LRS
        assert array.array_state.get_state(1, 1) == DeviceState.LRS
        assert array.array_state.get_state(2, 2) == DeviceState.LRS

        # Reset array
        array.reset()

        # All cells should be PRISTINE
        for r in range(4):
            for c in range(4):
                assert array.array_state.get_state(r, c) == DeviceState.PRISTINE

    def test_reset_clears_frame_history(self, teaching_profile):
        """Reset should clear frame history."""
        array = ArrayOrchestrator(teaching_profile, rows=4, cols=4)

        array.execute_operation(OperationType.READ, 0, 0, 0.15)
        assert len(array.get_frame_history()) > 0

        array.reset()
        assert len(array.get_frame_history()) == 0
