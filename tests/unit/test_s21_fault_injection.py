"""
S21: Fault Injection Tests
"""
import pytest
from simulator.fault_injection import (
    FaultDetector,
    FaultType,
    FaultSeverity,
    FaultConfig
)


class TestFaultDetector:
    """故障检测器测试"""
    
    def test_detect_wrong_bias_polarity_correct(self):
        """测试正确偏置极性"""
        detector = FaultDetector()
        result = detector.detect_wrong_bias_polarity(2.0, "positive")
        
        assert result.fault_type == FaultType.WRONG_BIAS_POLARITY
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_wrong_bias_polarity_wrong(self):
        """测试错误偏置极性"""
        detector = FaultDetector()
        result = detector.detect_wrong_bias_polarity(-2.0, "positive")
        
        assert result.fault_type == FaultType.WRONG_BIAS_POLARITY
        assert result.detected is True
        assert result.severity == FaultSeverity.ERROR
        assert "偏置极性错误" in result.message
    
    def test_detect_wl_not_enabled_off(self):
        """测试字线未开启"""
        detector = FaultDetector()
        result = detector.detect_wl_not_enabled(0.5, vth=0.7)
        
        assert result.fault_type == FaultType.WL_NOT_ENABLED
        assert result.detected is True
        assert result.severity == FaultSeverity.ERROR
        assert "字线未开启" in result.message
    
    def test_detect_wl_not_enabled_on(self):
        """测试字线已开启"""
        detector = FaultDetector()
        result = detector.detect_wl_not_enabled(1.8, vth=0.7)
        
        assert result.fault_type == FaultType.WL_NOT_ENABLED
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_missing_compliance_none(self):
        """测试缺少电流限制（未配置）"""
        detector = FaultDetector()
        result = detector.detect_missing_compliance(100.0, None)
        
        assert result.fault_type == FaultType.MISSING_COMPLIANCE
        assert result.detected is True
        assert result.severity == FaultSeverity.CRITICAL
        assert "缺少电流限制" in result.message
    
    def test_detect_missing_compliance_exceeded(self):
        """测试电流超过限制"""
        detector = FaultDetector()
        result = detector.detect_missing_compliance(100.0, 50.0)
        
        assert result.fault_type == FaultType.MISSING_COMPLIANCE
        assert result.detected is True
        assert result.severity == FaultSeverity.CRITICAL
    
    def test_detect_missing_compliance_ok(self):
        """测试电流在限制内"""
        detector = FaultDetector()
        result = detector.detect_missing_compliance(30.0, 50.0)
        
        assert result.fault_type == FaultType.MISSING_COMPLIANCE
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_sense_failure_small_margin(self):
        """测试感测边距不足"""
        detector = FaultDetector()
        result = detector.detect_sense_failure(10.0, 10.05, 0.05)
        
        assert result.fault_type == FaultType.SENSE_FAILURE
        assert result.detected is True
        assert result.severity == FaultSeverity.WARNING
        assert "感测边距不足" in result.message
    
    def test_detect_sense_failure_ok(self):
        """测试感测正常"""
        detector = FaultDetector()
        result = detector.detect_sense_failure(10.0, 5.0, 5.0)
        
        assert result.fault_type == FaultType.SENSE_FAILURE
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_over_forming_voltage_exceeded(self):
        """测试过度形成（电压超限）"""
        detector = FaultDetector()
        result = detector.detect_over_forming(6.0, 500.0, max_voltage=5.0, max_time=1000.0)
        
        assert result.fault_type == FaultType.OVER_FORMING
        assert result.detected is True
        assert result.severity == FaultSeverity.CRITICAL
        assert "过度形成" in result.message
    
    def test_detect_over_forming_time_exceeded(self):
        """测试过度形成（时间超限）"""
        detector = FaultDetector()
        result = detector.detect_over_forming(3.0, 1500.0, max_voltage=5.0, max_time=1000.0)
        
        assert result.fault_type == FaultType.OVER_FORMING
        assert result.detected is True
        assert result.severity == FaultSeverity.CRITICAL
    
    def test_detect_over_forming_ok(self):
        """测试形成参数正常"""
        detector = FaultDetector()
        result = detector.detect_over_forming(3.0, 500.0, max_voltage=5.0, max_time=1000.0)
        
        assert result.fault_type == FaultType.OVER_FORMING
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_read_disturb_count_exceeded(self):
        """测试读取干扰（次数超限）"""
        detector = FaultDetector()
        result = detector.detect_read_disturb(1500, 0.3, max_count=1000, max_voltage=0.5)
        
        assert result.fault_type == FaultType.READ_DISTURB
        assert result.detected is True
        assert result.severity == FaultSeverity.WARNING
        assert "读取干扰" in result.message
    
    def test_detect_read_disturb_voltage_exceeded(self):
        """测试读取干扰（电压超限）"""
        detector = FaultDetector()
        result = detector.detect_read_disturb(500, 0.6, max_count=1000, max_voltage=0.5)
        
        assert result.fault_type == FaultType.READ_DISTURB
        assert result.detected is True
        assert result.severity == FaultSeverity.WARNING
    
    def test_detect_read_disturb_ok(self):
        """测试读取参数正常"""
        detector = FaultDetector()
        result = detector.detect_read_disturb(500, 0.3, max_count=1000, max_voltage=0.5)
        
        assert result.fault_type == FaultType.READ_DISTURB
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_detect_write_disturb_voltage_exceeded(self):
        """测试写入干扰（电压超限）"""
        detector = FaultDetector()
        result = detector.detect_write_disturb(4.0, 2.0, max_voltage=3.0, min_distance=1.0)
        
        assert result.fault_type == FaultType.WRITE_DISTURB
        assert result.detected is True
        assert result.severity == FaultSeverity.WARNING
        assert "写入干扰" in result.message
    
    def test_detect_write_disturb_distance_insufficient(self):
        """测试写入干扰（距离不足）"""
        detector = FaultDetector()
        result = detector.detect_write_disturb(2.0, 0.5, max_voltage=3.0, min_distance=1.0)
        
        assert result.fault_type == FaultType.WRITE_DISTURB
        assert result.detected is True
        assert result.severity == FaultSeverity.WARNING
    
    def test_detect_write_disturb_ok(self):
        """测试写入参数正常"""
        detector = FaultDetector()
        result = detector.detect_write_disturb(2.0, 2.0, max_voltage=3.0, min_distance=1.0)
        
        assert result.fault_type == FaultType.WRITE_DISTURB
        assert result.detected is False
        assert result.severity == FaultSeverity.INFO
    
    def test_run_all_detections(self):
        """测试运行所有检测"""
        detector = FaultDetector()
        results = detector.run_all_detections(
            v_rram=-2.0,
            expected_polarity="positive",
            wl_voltage=0.5,
            i_rram=100.0,
            compliance_limit=50.0
        )
        
        assert len(results) == 3
        assert all(r.detected for r in results)
    
    def test_get_fault_summary(self):
        """测试获取故障摘要"""
        detector = FaultDetector()
        detector.run_all_detections(
            v_rram=-2.0,
            expected_polarity="positive",
            wl_voltage=0.5,
            i_rram=30.0,
            compliance_limit=50.0
        )
        
        summary = detector.get_fault_summary()
        
        assert summary["total_checks"] == 3
        assert summary["faults_detected"] == 2  # wrong polarity + WL not enabled
        assert summary["severity_counts"][FaultSeverity.ERROR] == 2
        assert len(summary["faults"]) == 2


class TestFaultTypes:
    """故障类型测试"""
    
    def test_fault_type_enum(self):
        """测试故障类型枚举"""
        assert FaultType.WRONG_BIAS_POLARITY == "wrong_bias_polarity"
        assert FaultType.WL_NOT_ENABLED == "wl_not_enabled"
        assert FaultType.MISSING_COMPLIANCE == "missing_compliance"
        assert FaultType.SENSE_FAILURE == "sense_failure"
        assert FaultType.OVER_FORMING == "over_forming"
        assert FaultType.READ_DISTURB == "read_disturb"
        assert FaultType.WRITE_DISTURB == "write_disturb"
    
    def test_fault_severity_enum(self):
        """测试故障严重程度枚举"""
        assert FaultSeverity.INFO == "info"
        assert FaultSeverity.WARNING == "warning"
        assert FaultSeverity.ERROR == "error"
        assert FaultSeverity.CRITICAL == "critical"
