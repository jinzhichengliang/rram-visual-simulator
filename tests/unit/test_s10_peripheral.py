"""S10: Peripheral Circuit Tests"""
import pytest
from packages.contracts.types import DeviceProfile, OperationType
from simulator.core.peripheral import (
    RowDecoder,
    ColumnDecoder,
    WLDriver,
    BLDriver,
    SLDriver,
    SenseAmplifier,
    PeripheralCircuit,
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


class TestRowDecoder:
    """Test row decoder."""

    def test_decode_selects_correct_line(self):
        decoder = RowDecoder(rows=4, v_gate=1.8)
        output = decoder.decode(row=2)

        assert output.selected_line == 2
        assert output.voltages[2] == 1.8
        assert all(v == 0.0 for i, v in enumerate(output.voltages) if i != 2)

    def test_decode_invalid_row_raises(self):
        decoder = RowDecoder(rows=4)
        with pytest.raises(ValueError):
            decoder.decode(row=5)


class TestColumnDecoder:
    """Test column decoder."""

    def test_decode_forming(self, profile):
        decoder = ColumnDecoder(cols=4)
        bl_out, sl_out = decoder.decode(col=1, operation=OperationType.FORMING, pulse_amplitude=3.5, profile=profile)

        assert bl_out.voltages[1] == 3.5
        assert sl_out.voltages[1] == 0.0

    def test_decode_set_positive_polarity(self, profile):
        decoder = ColumnDecoder(cols=4)
        bl_out, sl_out = decoder.decode(col=0, operation=OperationType.SET, pulse_amplitude=2.0, profile=profile)

        # SET polarity is V_RRAM > 0, so BL should be positive
        assert bl_out.voltages[0] == 2.0

    def test_decode_reset_negative_polarity(self, profile):
        decoder = ColumnDecoder(cols=4)
        bl_out, sl_out = decoder.decode(col=0, operation=OperationType.RESET, pulse_amplitude=2.0, profile=profile)

        # RESET polarity is V_RRAM < 0, so BL should be negative
        assert bl_out.voltages[0] == -2.0

    def test_decode_read_small_voltage(self, profile):
        decoder = ColumnDecoder(cols=4)
        bl_out, sl_out = decoder.decode(col=0, operation=OperationType.READ, pulse_amplitude=0.15, profile=profile)

        # READ uses small voltage from profile range
        assert 0.1 <= bl_out.voltages[0] <= 0.2


class TestDrivers:
    """Test WL/BL/SL drivers."""

    def test_wl_driver_activates_selected(self):
        from simulator.core.peripheral import DecoderOutput
        driver = WLDriver(rows=4)
        output = DecoderOutput(selected_line=2, line_count=4, voltages=[0.0, 0.0, 1.8, 0.0])

        voltages = driver.drive(output)

        assert voltages == [0.0, 0.0, 1.8, 0.0]
        assert driver.states[2].is_active is True
        assert driver.states[0].is_active is False

    def test_bl_driver_with_compliance(self):
        from simulator.core.peripheral import DecoderOutput
        driver = BLDriver(cols=4, compliance_ua=50.0)
        output = DecoderOutput(selected_line=1, line_count=4, voltages=[0.0, 2.0, 0.0, 0.0])

        voltages = driver.drive(output)

        assert voltages[1] == 2.0
        assert driver.states[1].current_limit_ua == 50.0


class TestSenseAmplifier:
    """Test sense amplifier."""

    def test_sense_lrs(self, profile):
        sense = SenseAmplifier(profile)
        # LRS current should be high (e.g., 10 µA)
        result = sense.sense(read_current_ua=10.0)

        assert result.decision == "LRS"
        assert result.passed is True

    def test_sense_hrs(self, profile):
        sense = SenseAmplifier(profile)
        # HRS current should be low (e.g., 0.1 µA)
        result = sense.sense(read_current_ua=0.1)

        assert result.decision == "HRS"
        assert result.passed is True

    def test_sense_margin_calculation(self, profile):
        sense = SenseAmplifier(profile)
        result = sense.sense(read_current_ua=10.0)

        assert result.margin_ua > 0
        assert result.reference_ua > 0


class TestPeripheralCircuit:
    """Test peripheral circuit integration."""

    def test_execute_phase_prepare(self, profile):
        circuit = PeripheralCircuit(rows=4, cols=4, profile=profile)
        wl, bl, sl = circuit.execute_phase(row=1, col=2, operation=OperationType.READ, phase="PREPARE", pulse_amplitude=0.15)

        # PREPARE phase: all voltages should be 0
        assert all(v == 0.0 for v in wl)
        assert all(v == 0.0 for v in bl)
        assert all(v == 0.0 for v in sl)

    def test_execute_phase_active_read(self, profile):
        circuit = PeripheralCircuit(rows=4, cols=4, profile=profile)
        wl, bl, sl = circuit.execute_phase(row=1, col=2, operation=OperationType.READ, phase="ACTIVE", pulse_amplitude=0.15)

        # ACTIVE phase: selected WL should be high, selected BL should have read voltage
        assert wl[1] == 1.8
        assert 0.1 <= bl[2] <= 0.2
        assert sl[2] == 0.0

    def test_sense_integration(self, profile):
        circuit = PeripheralCircuit(rows=4, cols=4, profile=profile)
        result = circuit.sense(read_current_ua=10.0)

        assert result.decision == "LRS"
