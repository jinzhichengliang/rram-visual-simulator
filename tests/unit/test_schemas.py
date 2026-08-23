"""S01 — Schema validation tests.

Verifies that canonical fixtures can be parsed by Python Pydantic models
and that invalid fixtures are correctly rejected.
"""
import json
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # tests/unit -> rram-visual-simulator
sys.path.insert(0, str(PROJECT_ROOT / "packages"))
sys.path.insert(0, str(PROJECT_ROOT / "apps" / "api"))

from contracts.types import (
    DeviceProfile,
    DeviceState,
    FidelityLevel,
    FrameState,
    OperationPhase,
    OperationSpec,
    OperationType,
    PulseSpec,
)

FIXTURES_DIR = PROJECT_ROOT / "packages" / "contracts" / "fixtures"


class TestValidFixtures:
    """Valid fixtures must parse successfully."""

    def test_valid_frame_pristine(self):
        """Valid pristine frame must parse."""
        with open(FIXTURES_DIR / "valid-frame-pristine.json") as f:
            data = json.load(f)
        frame = FrameState(**data)
        assert frame.frameId == "frame-001"
        assert frame.timeNs == 0
        assert frame.operation == OperationType.PRISTINE
        assert frame.phase == OperationPhase.PREPARE
        assert frame.cell.rram.state == DeviceState.PRISTINE
        assert frame.cell.rram.formingDone is False
        assert frame.model.fidelity == FidelityLevel.F0
        assert frame.model.seed == 42

    def test_valid_profile(self):
        """Valid device profile must parse."""
        with open(FIXTURES_DIR / "valid-profile.json") as f:
            data = json.load(f)
        profile = DeviceProfile(**data)
        assert profile.id == "bipolar_teaching_v1"
        assert profile.version == "1.0.0"
        assert profile.setPolarity.value == "V_RRAM > 0"
        assert profile.resetPolarity.value == "V_RRAM < 0"
        assert profile.logicMap.LRS == 1
        assert profile.logicMap.HRS == 0
        assert profile.complianceUa == 50


class TestInvalidFixtures:
    """Invalid fixtures must be rejected."""

    def test_invalid_frame_negative_time(self):
        """Frame with negative timeNs must fail validation."""
        with open(FIXTURES_DIR / "invalid-frame-negative-time.json") as f:
            data = json.load(f)
        with pytest.raises(ValidationError):
            FrameState(**data)

    def test_invalid_frame_negative_resistance(self):
        """Frame with negative resistance must fail validation."""
        with open(FIXTURES_DIR / "valid-frame-pristine.json") as f:
            data = json.load(f)
        data["cell"]["rram"]["r"] = -100
        with pytest.raises(ValidationError):
            FrameState(**data)

    def test_invalid_frame_unknown_operation(self):
        """Frame with unknown operation must fail validation."""
        with open(FIXTURES_DIR / "valid-frame-pristine.json") as f:
            data = json.load(f)
        data["operation"] = "UNKNOWN_OP"
        with pytest.raises(ValidationError):
            FrameState(**data)

    def test_invalid_frame_missing_version(self):
        """Frame with missing profile version must fail validation."""
        with open(FIXTURES_DIR / "valid-frame-pristine.json") as f:
            data = json.load(f)
        del data["model"]["profileVersion"]
        with pytest.raises(ValidationError):
            FrameState(**data)

    def test_invalid_profile_missing_required_field(self):
        """Profile with missing required field must fail validation."""
        with open(FIXTURES_DIR / "valid-profile.json") as f:
            data = json.load(f)
        del data["complianceUa"]
        with pytest.raises(ValidationError):
            DeviceProfile(**data)


class TestRoundTrip:
    """Pydantic models must round-trip through JSON."""

    def test_frame_round_trip(self):
        """FrameState must serialize and deserialize correctly."""
        with open(FIXTURES_DIR / "valid-frame-pristine.json") as f:
            data = json.load(f)
        frame = FrameState(**data)
        json_str = frame.model_dump_json()
        frame2 = FrameState.model_validate_json(json_str)
        assert frame.frameId == frame2.frameId
        assert frame.timeNs == frame2.timeNs
        assert frame.operation == frame2.operation
        assert frame.cell.rram.state == frame2.cell.rram.state

    def test_profile_round_trip(self):
        """DeviceProfile must serialize and deserialize correctly."""
        with open(FIXTURES_DIR / "valid-profile.json") as f:
            data = json.load(f)
        profile = DeviceProfile(**data)
        json_str = profile.model_dump_json()
        profile2 = DeviceProfile.model_validate_json(json_str)
        assert profile.id == profile2.id
        assert profile.version == profile2.version
        assert profile.setPolarity == profile2.setPolarity


class TestOperationSpec:
    """OperationSpec validation tests."""

    def test_valid_operation_spec(self):
        """Valid operation spec must parse."""
        spec = OperationSpec(
            type=OperationType.SET,
            target={"row": 0, "col": 0},
            biasPolicyId="default_set",
            pulse=PulseSpec(amplitudeV=2.0, widthNs=100, rampNs=10),
            complianceUa=50,
        )
        assert spec.type == OperationType.SET
        assert spec.target["row"] == 0
        assert spec.pulse.amplitudeV == 2.0

    def test_invalid_target_negative_index(self):
        """Operation with negative target index must fail."""
        with pytest.raises(ValidationError):
            OperationSpec(
                type=OperationType.READ,
                target={"row": -1, "col": 0},
                biasPolicyId="default_read",
                pulse=PulseSpec(amplitudeV=0.1, widthNs=100, rampNs=10),
            )
