"""
Program-and-Verify Controller — Iterative programming with verification.

V0.3 S12: Implements program-and-verify loop:
  Programming Pulse → Relax → Read Verify → Compare Window → Continue / Stop
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from packages.contracts.types import (
    DeviceProfile,
    DeviceState,
    OperationType,
)
from simulator.core.peripheral import SenseAmplifier


class VerifyStatus(Enum):
    """Status of verify operation."""
    PASS = "pass"
    FAIL = "fail"
    INCOMPLETE = "incomplete"


@dataclass
class VerifyResult:
    """Result of a verify operation."""
    status: VerifyStatus
    sensed_state: str  # "HRS" or "LRS"
    target_state: str  # What we're trying to achieve
    margin_ua: float
    pulse_count: int


class ProgramAndVerifyController:
    """
    Program-and-Verify Controller — iterative programming with verification.

    Manages the loop:
      1. Apply programming pulse (SET or RESET)
      2. Relax (optional)
      3. Read verify
      4. Compare with target window
      5. If pass → stop
      6. If fail and pulse_count < max → go to 1
      7. If fail and pulse_count >= max → report failure
    """

    def __init__(
        self,
        profile: DeviceProfile,
        max_pulses: int = 10,
        verify_margin_ua: Optional[float] = None,
    ):
        self.profile = profile
        self.max_pulses = max_pulses
        self.sense_amp = SenseAmplifier(profile)

        # Use sense amplifier's min margin if not specified
        self.verify_margin_ua = verify_margin_ua or self.sense_amp.min_margin_ua

    def verify(
        self,
        read_current_ua: float,
        target_state: str,
        pulse_count: int,
    ) -> VerifyResult:
        """
        Verify the current state after a programming pulse.

        Args:
            read_current_ua: Current from read operation
            target_state: Target state ("HRS" or "LRS")
            pulse_count: Number of pulses applied so far

        Returns:
            VerifyResult with status and details
        """
        # Sense the current state
        sense_result = self.sense_amp.sense(read_current_ua)
        sensed_state = sense_result.decision

        # Check if we reached target
        if sensed_state == target_state:
            # Check if margin is sufficient
            if sense_result.margin_ua >= self.verify_margin_ua:
                status = VerifyStatus.PASS
            else:
                # Reached target but margin insufficient
                status = VerifyStatus.INCOMPLETE
        else:
            # Wrong state
            status = VerifyStatus.FAIL

        return VerifyResult(
            status=status,
            sensed_state=sensed_state,
            target_state=target_state,
            margin_ua=sense_result.margin_ua,
            pulse_count=pulse_count,
        )

    def should_continue(self, verify_result: VerifyResult) -> bool:
        """
        Determine if programming should continue.

        Returns True if:
          - Status is FAIL and pulse_count < max_pulses
          - Status is INCOMPLETE and pulse_count < max_pulses

        Returns False if:
          - Status is PASS
          - pulse_count >= max_pulses
        """
        if verify_result.status == VerifyStatus.PASS:
            return False

        if verify_result.pulse_count >= self.max_pulses:
            return False

        return True

    def get_target_state_for_operation(self, operation: OperationType) -> str:
        """
        Get the target state for a programming operation.

        Args:
            operation: SET or RESET

        Returns:
            Target state ("LRS" for SET, "HRS" for RESET)
        """
        if operation == OperationType.SET:
            return "LRS"
        elif operation == OperationType.RESET:
            return "HRS"
        else:
            raise ValueError(f"Operation {operation} is not a programming operation")


@dataclass
class ProgrammingSession:
    """Tracks a complete programming session."""
    operation: OperationType
    target_state: str
    pulses_applied: int
    final_status: VerifyStatus
    final_sensed_state: str
    final_margin_ua: float
    success: bool


class ProgrammingSessionManager:
    """
    Manages complete programming sessions with history.
    """

    def __init__(self, profile: DeviceProfile, max_pulses: int = 10):
        self.profile = profile
        self.controller = ProgramAndVerifyController(profile, max_pulses)
        self.sessions: list[ProgrammingSession] = []

    def run_session(
        self,
        operation: OperationType,
        read_currents_ua: list[float],
    ) -> ProgrammingSession:
        """
        Run a complete programming session.

        Args:
            operation: SET or RESET
            read_currents_ua: List of read currents after each pulse

        Returns:
            ProgrammingSession with complete history
        """
        target_state = self.controller.get_target_state_for_operation(operation)

        pulse_count = 0
        final_result = None

        for read_current in read_currents_ua:
            pulse_count += 1
            result = self.controller.verify(read_current, target_state, pulse_count)
            final_result = result

            if not self.controller.should_continue(result):
                break

        if final_result is None:
            # No pulses applied
            final_result = VerifyResult(
                status=VerifyStatus.FAIL,
                sensed_state="UNKNOWN",
                target_state=target_state,
                margin_ua=0.0,
                pulse_count=0,
            )

        session = ProgrammingSession(
            operation=operation,
            target_state=target_state,
            pulses_applied=final_result.pulse_count,
            final_status=final_result.status,
            final_sensed_state=final_result.sensed_state,
            final_margin_ua=final_result.margin_ua,
            success=(final_result.status == VerifyStatus.PASS),
        )

        self.sessions.append(session)
        return session

    def get_success_rate(self) -> float:
        """Calculate success rate across all sessions."""
        if not self.sessions:
            return 0.0

        success_count = sum(1 for s in self.sessions if s.success)
        return success_count / len(self.sessions)

    def get_average_pulses(self) -> float:
        """Calculate average pulses to success."""
        success_sessions = [s for s in self.sessions if s.success]
        if not success_sessions:
            return 0.0

        return sum(s.pulses_applied for s in success_sessions) / len(success_sessions)
