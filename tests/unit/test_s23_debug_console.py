"""
S23: Debug Console Tests
"""
import pytest
from simulator.debug_console import (
    DiagnosticContext,
    DiagnosticReport,
    DiagnosticEngine
)


class TestDiagnosticEngine:
    """诊断引擎测试"""
    
    def test_diagnose_healthy_state(self):
        """测试健康状态诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.15,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True,
            temperature_k=300.0,
            gap_nm=2.0,
            filament_proxy=0.8
        )
        
        report = engine.diagnose(context, expected_polarity="positive", compliance_limit=50.0)
        
        assert report.overall_health == "healthy"
        assert len(report.faults) == 0
        assert len(report.recommendations) > 0
        assert "正常" in report.summary
    
    def test_diagnose_wrong_polarity(self):
        """测试错误极性诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="SET",
            phase="ACTIVE",
            v_rram=-2.0,  # 错误极性
            i_rram=30.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=-2.0,
            sl_voltage=0.0,
            transistor_on=True,
            state="HRS",
            forming_done=True,
            temperature_k=300.0
        )
        
        report = engine.diagnose(context, expected_polarity="positive", compliance_limit=50.0)
        
        assert report.overall_health in ["warning", "critical"]
        assert len(report.faults) > 0
        assert any(f.fault_type == "wrong_bias_polarity" for f in report.faults)
        assert any("极性" in r for r in report.recommendations)
    
    def test_diagnose_wl_not_enabled(self):
        """测试字线未开启诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.0,
            i_rram=0.0,
            r_rram=1000000,
            wl_voltage=0.5,  # 低于阈值
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=False,
            state="HRS",
            forming_done=True,
            temperature_k=300.0
        )
        
        report = engine.diagnose(context, expected_polarity="positive", compliance_limit=50.0)
        
        assert report.overall_health in ["warning", "critical"]
        assert len(report.faults) > 0
        assert any(f.fault_type == "wl_not_enabled" for f in report.faults)
        assert any("字线" in r for r in report.recommendations)
    
    def test_diagnose_missing_compliance(self):
        """测试缺少电流限制诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="SET",
            phase="ACTIVE",
            v_rram=2.0,
            i_rram=100.0,  # 超过限制
            r_rram=20000,
            wl_voltage=1.8,
            bl_voltage=2.0,
            sl_voltage=0.0,
            transistor_on=True,
            state="HRS",
            forming_done=True,
            temperature_k=300.0
        )
        
        report = engine.diagnose(context, expected_polarity="positive", compliance_limit=50.0)
        
        assert report.overall_health == "critical"
        assert len(report.faults) > 0
        assert any(f.fault_type == "missing_compliance" for f in report.faults)
        assert any("电流限制" in r for r in report.recommendations)
    
    def test_diagnose_over_forming(self):
        """测试过度形成诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="FORMING",
            phase="ACTIVE",
            v_rram=6.0,  # 过高电压
            i_rram=50.0,
            r_rram=1000000,
            wl_voltage=1.8,
            bl_voltage=6.0,
            sl_voltage=0.0,
            transistor_on=True,
            state="PRISTINE",
            forming_done=False,
            temperature_k=300.0
        )
        
        report = engine.diagnose(context, expected_polarity="positive", compliance_limit=50.0)
        
        assert report.overall_health == "critical"
        assert len(report.faults) > 0
        assert any(f.fault_type == "over_forming" for f in report.faults)
        assert any("形成" in r for r in report.recommendations)
    
    def test_diagnose_read_disturb(self):
        """测试读取干扰诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.3,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.3,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True,
            temperature_k=300.0,
            gap_nm=2.0
        )
        
        report = engine.diagnose(
            context,
            expected_polarity="positive",
            compliance_limit=50.0,
            read_count=10000  # 高读取次数
        )
        
        assert len(report.disturb_effects) > 0
        assert any(e.disturb_type == "read" for e in report.disturb_effects)
    
    def test_diagnose_write_disturb(self):
        """测试写入干扰诊断"""
        engine = DiagnosticEngine()
        context = DiagnosticContext(
            operation="SET",
            phase="ACTIVE",
            v_rram=3.0,
            i_rram=30.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=3.0,
            sl_voltage=0.0,
            transistor_on=True,
            state="HRS",
            forming_done=True,
            temperature_k=300.0
        )
        
        report = engine.diagnose(
            context,
            expected_polarity="positive",
            compliance_limit=50.0,
            adjacent_distance_nm=0.5  # 近距离
        )
        
        assert len(report.disturb_effects) > 0
        assert any(e.disturb_type == "write" for e in report.disturb_effects)
    
    def test_diagnostic_history(self):
        """测试诊断历史"""
        engine = DiagnosticEngine()
        
        # 执行多次诊断
        for i in range(3):
            context = DiagnosticContext(
                operation="READ",
                phase="ACTIVE",
                v_rram=0.15,
                i_rram=5.0,
                r_rram=30000,
                wl_voltage=1.8,
                bl_voltage=0.15,
                sl_voltage=0.0,
                transistor_on=True,
                state="LRS",
                forming_done=True,
                temperature_k=300.0
            )
            engine.diagnose(context)
        
        history = engine.get_diagnostic_history()
        assert len(history) == 3
    
    def test_clear_history(self):
        """测试清除历史"""
        engine = DiagnosticEngine()
        
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.15,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True,
            temperature_k=300.0
        )
        engine.diagnose(context)
        
        assert len(engine.get_diagnostic_history()) == 1
        engine.clear_history()
        assert len(engine.get_diagnostic_history()) == 0


class TestDiagnosticContext:
    """诊断上下文测试"""
    
    def test_context_creation(self):
        """测试上下文创建"""
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.15,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True
        )
        
        assert context.operation == "READ"
        assert context.phase == "ACTIVE"
        assert context.v_rram == 0.15
        assert context.transistor_on is True
    
    def test_context_with_optional_fields(self):
        """测试带可选字段的上下文"""
        context = DiagnosticContext(
            operation="SET",
            phase="ACTIVE",
            v_rram=2.0,
            i_rram=30.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=2.0,
            sl_voltage=0.0,
            transistor_on=True,
            state="HRS",
            forming_done=True,
            temperature_k=350.0,
            gap_nm=5.0,
            filament_proxy=0.3
        )
        
        assert context.temperature_k == 350.0
        assert context.gap_nm == 5.0
        assert context.filament_proxy == 0.3


class TestDiagnosticReport:
    """诊断报告测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.15,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True
        )
        
        report = DiagnosticReport(
            context=context,
            faults=[],
            disturb_effects=[],
            recommendations=["器件状态正常"],
            overall_health="healthy",
            summary="正常: 器件状态健康"
        )
        
        assert report.overall_health == "healthy"
        assert len(report.faults) == 0
        assert len(report.recommendations) == 1
    
    def test_report_health_levels(self):
        """测试不同健康级别"""
        context = DiagnosticContext(
            operation="READ",
            phase="ACTIVE",
            v_rram=0.15,
            i_rram=5.0,
            r_rram=30000,
            wl_voltage=1.8,
            bl_voltage=0.15,
            sl_voltage=0.0,
            transistor_on=True,
            state="LRS",
            forming_done=True
        )
        
        for health in ["healthy", "warning", "critical"]:
            report = DiagnosticReport(
                context=context,
                faults=[],
                disturb_effects=[],
                recommendations=[],
                overall_health=health,
                summary=f"健康级别: {health}"
            )
            assert report.overall_health == health
