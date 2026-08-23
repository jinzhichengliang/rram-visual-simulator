"""
S23: Debug Console & Diagnostic System

实现调试控制台和诊断系统：
- 错误归因系统
- 调试信息收集
- 故障诊断报告
"""
from typing import Optional
from pydantic import BaseModel
from simulator.fault_injection import FaultDetector, FaultResult
from simulator.disturb_model import DisturbSimulator, DisturbEffect


class DiagnosticContext(BaseModel):
    """诊断上下文"""
    operation: str
    phase: str
    v_rram: float
    i_rram: float
    r_rram: float
    wl_voltage: float
    bl_voltage: float
    sl_voltage: float
    transistor_on: bool
    state: str
    forming_done: bool
    temperature_k: float = 300.0
    gap_nm: Optional[float] = None
    filament_proxy: Optional[float] = None


class DiagnosticReport(BaseModel):
    """诊断报告"""
    context: DiagnosticContext
    faults: list[FaultResult]
    disturb_effects: list[DisturbEffect]
    recommendations: list[str]
    overall_health: str  # "healthy", "warning", "critical"
    summary: str


class DiagnosticEngine:
    """诊断引擎"""
    
    def __init__(self):
        self.fault_detector = FaultDetector()
        self.disturb_simulator = DisturbSimulator()
        self.history: list[DiagnosticReport] = []
    
    def diagnose(
        self,
        context: DiagnosticContext,
        expected_polarity: str = "positive",
        compliance_limit: Optional[float] = None,
        read_count: int = 0,
        adjacent_distance_nm: float = 10.0
    ) -> DiagnosticReport:
        """
        执行完整诊断
        
        Args:
            context: 诊断上下文
            expected_polarity: 期望极性
            compliance_limit: 电流限制
            read_count: 读取次数
            adjacent_distance_nm: 相邻单元距离
        
        Returns:
            DiagnosticReport
        """
        # 1. 故障检测
        faults = self._detect_faults(
            context, expected_polarity, compliance_limit
        )
        
        # 2. 干扰评估
        disturb_effects = self._assess_disturb(
            context, read_count, adjacent_distance_nm
        )
        
        # 3. 生成建议
        recommendations = self._generate_recommendations(faults, disturb_effects)
        
        # 4. 评估整体健康状态
        overall_health = self._assess_overall_health(faults, disturb_effects)
        
        # 5. 生成摘要
        summary = self._generate_summary(faults, disturb_effects, overall_health)
        
        report = DiagnosticReport(
            context=context,
            faults=faults,
            disturb_effects=disturb_effects,
            recommendations=recommendations,
            overall_health=overall_health,
            summary=summary
        )
        
        self.history.append(report)
        return report
    
    def _detect_faults(
        self,
        context: DiagnosticContext,
        expected_polarity: str,
        compliance_limit: Optional[float]
    ) -> list[FaultResult]:
        """检测故障"""
        faults = []
        
        # 偏置极性检测
        if context.v_rram != 0:
            fault = self.fault_detector.detect_wrong_bias_polarity(
                context.v_rram, expected_polarity
            )
            if fault.detected:
                faults.append(fault)
        
        # 字线检测
        fault = self.fault_detector.detect_wl_not_enabled(context.wl_voltage)
        if fault.detected:
            faults.append(fault)
        
        # 电流限制检测
        if context.operation in ["FORMING", "SET"]:
            fault = self.fault_detector.detect_missing_compliance(
                context.i_rram, compliance_limit
            )
            if fault.detected:
                faults.append(fault)
        
        # 过度形成检测
        if context.operation == "FORMING":
            fault = self.fault_detector.detect_over_forming(
                abs(context.v_rram), 100.0  # 假设形成时间 100ns
            )
            if fault.detected:
                faults.append(fault)
        
        return faults
    
    def _assess_disturb(
        self,
        context: DiagnosticContext,
        read_count: int,
        adjacent_distance_nm: float
    ) -> list[DisturbEffect]:
        """评估干扰"""
        effects = []
        
        # 读取干扰评估
        if context.operation == "READ" and read_count > 0:
            effect = self.disturb_simulator.simulate_read_disturb(
                context.gap_nm or 5.0,
                abs(context.v_rram),
                read_count,
                context.temperature_k
            )
            if effect.state_change_risk in ["medium", "high"]:
                effects.append(effect)
        
        # 写入干扰评估
        if context.operation in ["SET", "RESET"]:
            effect = self.disturb_simulator.simulate_write_disturb(
                5.0,  # 假设相邻单元 gap
                abs(context.v_rram),
                adjacent_distance_nm,
                context.temperature_k
            )
            if effect.state_change_risk in ["medium", "high"]:
                effects.append(effect)
        
        return effects
    
    def _generate_recommendations(
        self,
        faults: list[FaultResult],
        disturb_effects: list[DisturbEffect]
    ) -> list[str]:
        """生成建议"""
        recommendations = []
        
        # 基于故障的建议
        for fault in faults:
            if fault.fault_type == "wrong_bias_polarity":
                recommendations.append("检查偏置配置，确保极性正确")
            elif fault.fault_type == "wl_not_enabled":
                recommendations.append("增加字线电压至阈值以上（建议 1.8V）")
            elif fault.fault_type == "missing_compliance":
                recommendations.append("配置电流限制以保护器件（建议 50µA）")
            elif fault.fault_type == "over_forming":
                recommendations.append("降低形成电压或缩短形成时间")
            elif fault.fault_type == "sense_failure":
                recommendations.append("检查感测边距，可能需要调整参考电流")
        
        # 基于干扰的建议
        for effect in disturb_effects:
            if effect.disturb_type == "read" and effect.state_change_risk == "high":
                recommendations.append("读取次数过多，建议减少读取频率或增加读取间隔")
            elif effect.disturb_type == "write" and effect.state_change_risk == "high":
                recommendations.append("写入干扰风险高，建议增加单元间距或降低写入电压")
        
        # 通用建议
        if not recommendations:
            recommendations.append("器件状态正常，继续当前操作")
        
        return recommendations
    
    def _assess_overall_health(
        self,
        faults: list[FaultResult],
        disturb_effects: list[DisturbEffect]
    ) -> str:
        """评估整体健康状态"""
        # 检查严重故障
        critical_faults = [f for f in faults if f.severity == "critical"]
        if critical_faults:
            return "critical"
        
        # 检查错误故障
        error_faults = [f for f in faults if f.severity == "error"]
        if error_faults:
            return "warning"
        
        # 检查高风险干扰
        high_risk_disturbs = [e for e in disturb_effects if e.state_change_risk == "high"]
        if high_risk_disturbs:
            return "warning"
        
        return "healthy"
    
    def _generate_summary(
        self,
        faults: list[FaultResult],
        disturb_effects: list[DisturbEffect],
        overall_health: str
    ) -> str:
        """生成摘要"""
        fault_count = len(faults)
        disturb_count = len(disturb_effects)
        
        if overall_health == "critical":
            return f"严重问题: 检测到 {fault_count} 个故障，需要立即处理"
        elif overall_health == "warning":
            return f"警告: 检测到 {fault_count} 个故障和 {disturb_count} 个干扰效应，建议调整参数"
        else:
            return f"正常: 检测到 {fault_count} 个轻微问题和 {disturb_count} 个干扰效应，器件状态健康"
    
    def get_diagnostic_history(self) -> list[DiagnosticReport]:
        """获取诊断历史"""
        return self.history
    
    def clear_history(self):
        """清除历史"""
        self.history.clear()
