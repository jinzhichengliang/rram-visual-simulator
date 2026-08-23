"""S12: Program-and-Verify Tests (G-07)"""
import pytest
from packages.contracts.types import DeviceProfile, OperationType
from simulator.core.program_verify import (
    ProgramAndVerifyController,
    ProgrammingSessionManager,
    VerifyStatus,
)


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


class TestProgramAndVerifyController:
    """Test program-and-verify controller."""

    def test_verify_pass_when_target_reached(self, profile):
        """Verify should pass when target state is reached with sufficient margin."""
        controller = ProgramAndVerifyController(profile, max_pulses=10)

        # Simulate reading LRS current (high current)
        result = controller.verify(read_current_ua=10.0, target_state="LRS", pulse_count=1)

        assert result.status == VerifyStatus.PASS
        assert result.sensed_state == "LRS"
        assert result.target_state == "LRS"

    def test_verify_fail_when_wrong_state(self, profile):
        """Verify should fail when wrong state is sensed."""
        controller = ProgramAndVerifyController(profile, max_pulses=10)

        # Trying to SET to LRS, but still reading HRS current (low current)
        result = controller.verify(read_current_ua=0.1, target_state="LRS", pulse_count=1)

        assert result.status == VerifyStatus.FAIL
        assert result.sensed_state == "HRS"
        assert result.target_state == "LRS"

    def test_should_continue_when_fail(self, profile):
        """Should continue when verify fails and under max pulses."""
        controller = ProgramAndVerifyController(profile, max_pulses=10)

        result = controller.verify(read_current_ua=0.1, target_state="LRS", pulse_count=1)
        assert controller.should_continue(result) is True

    def test_should_stop_when_pass(self, profile):
        """Should stop when verify passes."""
        controller = ProgramAndVerifyController(profile, max_pulses=10)

        result = controller.verify(read_current_ua=10.0, target_state="LRS", pulse_count=1)
        assert controller.should_continue(result) is False

    def test_should_stop_when_max_pulses_reached(self, profile):
        """Should stop when max pulses reached even if failed."""
        controller = ProgramAndVerifyController(profile, max_pulses=3)

        result = controller.verify(read_current_ua=0.1, target_state="LRS", pulse_count=3)
        assert controller.should_continue(result) is False

    def test_get_target_state_for_set(self, profile):
        """SET operation should target LRS."""
        controller = ProgramAndVerifyController(profile)
        assert controller.get_target_state_for_operation(OperationType.SET) == "LRS"

    def test_get_target_state_for_reset(self, profile):
        """RESET operation should target HRS."""
        controller = ProgramAndVerifyController(profile)
        assert controller.get_target_state_for_operation(OperationType.RESET) == "HRS"


class TestG07_ProgramVerifyRetry:
    """G-07: Program-Verify-Retry verification."""

    def test_successful_set_after_retry(self, profile):
        """SET should succeed after multiple pulses."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # Simulate: first 2 pulses fail (still HRS), 3rd pulse succeeds (LRS)
        read_currents = [0.1, 0.2, 10.0]  # HRS, HRS, LRS
        session = manager.run_session(OperationType.SET, read_currents)

        assert session.success is True
        assert session.pulses_applied == 3
        assert session.final_sensed_state == "LRS"

    def test_successful_reset_after_retry(self, profile):
        """RESET should succeed after multiple pulses."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # Simulate: first pulse fails (still LRS), 2nd pulse succeeds (HRS)
        read_currents = [10.0, 0.1]  # LRS, HRS
        session = manager.run_session(OperationType.RESET, read_currents)

        assert session.success is True
        assert session.pulses_applied == 2
        assert session.final_sensed_state == "HRS"

    def test_failed_programming_after_max_pulses(self, profile):
        """Programming should fail after max pulses."""
        manager = ProgrammingSessionManager(profile, max_pulses=3)

        # All pulses fail to change state
        read_currents = [0.1, 0.1, 0.1]  # All HRS
        session = manager.run_session(OperationType.SET, read_currents)

        assert session.success is False
        assert session.pulses_applied == 3
        assert session.final_sensed_state == "HRS"

    def test_immediate_success(self, profile):
        """Programming can succeed on first pulse."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # First pulse succeeds
        read_currents = [10.0]  # LRS
        session = manager.run_session(OperationType.SET, read_currents)

        assert session.success is True
        assert session.pulses_applied == 1

    def test_session_history_tracking(self, profile):
        """Session manager should track all sessions."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # Run multiple sessions
        manager.run_session(OperationType.SET, [10.0])
        manager.run_session(OperationType.RESET, [0.1])
        manager.run_session(OperationType.SET, [0.1, 10.0])

        assert len(manager.sessions) == 3
        assert manager.sessions[0].operation == OperationType.SET
        assert manager.sessions[1].operation == OperationType.RESET

    def test_success_rate_calculation(self, profile):
        """Success rate should be calculated correctly."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # 2 successes, 1 failure
        manager.run_session(OperationType.SET, [10.0])  # Success
        manager.run_session(OperationType.RESET, [10.0])  # Fail (still LRS)
        manager.run_session(OperationType.SET, [0.1, 10.0])  # Success

        assert manager.get_success_rate() == pytest.approx(2.0 / 3.0)

    def test_average_pulses_calculation(self, profile):
        """Average pulses should be calculated for successful sessions only."""
        manager = ProgrammingSessionManager(profile, max_pulses=10)

        # Success after 1 pulse
        manager.run_session(OperationType.SET, [10.0])
        # Success after 2 pulses
        manager.run_session(OperationType.SET, [0.1, 10.0])
        # Failure (should not count)
        manager.run_session(OperationType.SET, [0.1, 0.1, 0.1])

        # Average of successful sessions: (1 + 2) / 2 = 1.5
        assert manager.get_average_pulses() == pytest.approx(1.5)
