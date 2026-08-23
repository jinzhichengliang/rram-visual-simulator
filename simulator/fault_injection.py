"""
S21: Fault Injection Framework

实现故障注入和检测机制，支持以下故障类型：
- Wrong bias polarity (错误偏置极性)
- WL not enabled (未开启字线)
- Missing compliance (缺少电流限制)
- Sense failure (感测失败)
- Over-forming (过度形成)
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class FaultType(str, Enum):
    """故障类型枚举"""
    WRONG_BIAS_POLARITY = "wrong_bias_polarity"
    WL_NOT_ENABLED = "wl_not_enabled"
    MISSING_COMPLIANCE = "missing_compliance"
    SENSE_FAILURE = "sense_failure"
    OVER_FORMING = "over_forming"
    READ_DISTURB = "read_disturb"
    WRITE_DISTURB = "write_disturb"


class FaultSeverity(str, Enum):
    """故障严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FaultConfig(BaseModel):
    """故障配置"""
    fault_type: FaultType
    enabled: bool = True
    severity: FaultSeverity = FaultSeverity.WARNING
    parameters: dict = {}


class FaultResult(BaseModel):
    """故障检测结果"""
    fault_type: FaultType
    detected: bool
    severity: FaultSeverity
    message: str
    details: dict = {}
    attribution: str = ""  # 错误归因


class FaultDetector:
    """故障检测器"""
    
    def __init__(self, config: Optional[FaultConfig] = None):
        self.config = config
        self.detected_faults: list[FaultResult] = []
    
    def detect_wrong_bias_polarity(self, v_rram: float, expected_polarity: str) -> FaultResult:
        """
        检测错误偏置极性
        
        Args:
            v_rram: RRAM 两端电压
            expected_polarity: 期望极性 ("positive" 或 "negative")
        
        Returns:
            FaultResult
        """
        actual_polarity = "positive" if v_rram > 0 else "negative" if v_rram < 0 else "zero"
        detected = actual_polarity != expected_polarity
        
        return FaultResult(
            fault_type=FaultType.WRONG_BIAS_POLARITY,
            detected=detected,
            severity=FaultSeverity.ERROR if detected else FaultSeverity.INFO,
            message=f"偏置极性错误: 期望 {expected_polarity}, 实际 {actual_polarity}" if detected else "偏置极性正确",
            details={
                "v_rram": v_rram,
                "expected_polarity": expected_polarity,
                "actual_polarity": actual_polarity
            },
            attribution="偏置配置错误" if detected else ""
        )
    
    def detect_wl_not_enabled(self, wl_voltage: float, vth: float = 0.7) -> FaultResult:
        """
        检测字线未开启
        
        Args:
            wl_voltage: 字线电压
            vth: 晶体管阈值电压
        
        Returns:
            FaultResult
        """
        detected = wl_voltage < vth
        
        return FaultResult(
            fault_type=FaultType.WL_NOT_ENABLED,
            detected=detected,
            severity=FaultSeverity.ERROR if detected else FaultSeverity.INFO,
            message=f"字线未开启: WL={wl_voltage:.2f}V < Vth={vth:.2f}V" if detected else "字线已开启",
            details={
                "wl_voltage": wl_voltage,
                "vth": vth
            },
            attribution="字线驱动故障" if detected else ""
        )
    
    def detect_missing_compliance(self, i_rram: float, compliance_limit: Optional[float]) -> FaultResult:
        """
        检测缺少电流限制
        
        Args:
            i_rram: RRAM 电流
            compliance_limit: 电流限制值
        
        Returns:
            FaultResult
        """
        detected = compliance_limit is None or abs(i_rram) > compliance_limit
        
        return FaultResult(
            fault_type=FaultType.MISSING_COMPLIANCE,
            detected=detected,
            severity=FaultSeverity.CRITICAL if detected else FaultSeverity.INFO,
            message=f"缺少电流限制: I={abs(i_rram):.2f}µA > limit={compliance_limit}µA" if detected else "电流限制正常",
            details={
                "i_rram": i_rram,
                "compliance_limit": compliance_limit
            },
            attribution="电流限制未配置或失效" if detected else ""
        )
    
    def detect_sense_failure(self, sense_current: float, reference_current: float, margin: float) -> FaultResult:
        """
        检测感测失败
        
        Args:
            sense_current: 感测电流
            reference_current: 参考电流
            margin: 感测边距
        
        Returns:
            FaultResult
        """
        min_margin = 0.1  # 最小边距 0.1µA
        detected = abs(margin) < min_margin
        
        return FaultResult(
            fault_type=FaultType.SENSE_FAILURE,
            detected=detected,
            severity=FaultSeverity.WARNING if detected else FaultSeverity.INFO,
            message=f"感测边距不足: margin={abs(margin):.3f}µA < min={min_margin}µA" if detected else "感测正常",
            details={
                "sense_current": sense_current,
                "reference_current": reference_current,
                "margin": margin,
                "min_margin": min_margin
            },
            attribution="感测边距不足，可能导致误判" if detected else ""
        )
    
    def detect_over_forming(self, forming_voltage: float, forming_time: float, 
                           max_voltage: float = 5.0, max_time: float = 1000.0) -> FaultResult:
        """
        检测过度形成
        
        Args:
            forming_voltage: 形成电压
            forming_time: 形成时间 (ns)
            max_voltage: 最大允许电压
            max_time: 最大允许时间
        
        Returns:
            FaultResult
        """
        voltage_exceeded = forming_voltage > max_voltage
        time_exceeded = forming_time > max_time
        detected = voltage_exceeded or time_exceeded
        
        message = ""
        if voltage_exceeded and time_exceeded:
            message = f"过度形成: V={forming_voltage:.2f}V > {max_voltage}V 且 t={forming_time:.0f}ns > {max_time}ns"
        elif voltage_exceeded:
            message = f"过度形成: V={forming_voltage:.2f}V > {max_voltage}V"
        elif time_exceeded:
            message = f"过度形成: t={forming_time:.0f}ns > {max_time}ns"
        else:
            message = "形成参数正常"
        
        return FaultResult(
            fault_type=FaultType.OVER_FORMING,
            detected=detected,
            severity=FaultSeverity.CRITICAL if detected else FaultSeverity.INFO,
            message=message,
            details={
                "forming_voltage": forming_voltage,
                "forming_time": forming_time,
                "max_voltage": max_voltage,
                "max_time": max_time,
                "voltage_exceeded": voltage_exceeded,
                "time_exceeded": time_exceeded
            },
            attribution="形成条件过于激进，可能损坏器件" if detected else ""
        )
    
    def detect_read_disturb(self, read_count: int, read_voltage: float, 
                           max_count: int = 1000, max_voltage: float = 0.5) -> FaultResult:
        """
        检测读取干扰
        
        Args:
            read_count: 读取次数
            read_voltage: 读取电压
            max_count: 最大允许读取次数
            max_voltage: 最大允许读取电压
        
        Returns:
            FaultResult
        """
        count_exceeded = read_count > max_count
        voltage_exceeded = read_voltage > max_voltage
        detected = count_exceeded or voltage_exceeded
        
        message = ""
        if count_exceeded and voltage_exceeded:
            message = f"读取干扰: 次数={read_count} > {max_count} 且 V={read_voltage:.2f}V > {max_voltage}V"
        elif count_exceeded:
            message = f"读取干扰: 次数={read_count} > {max_count}"
        elif voltage_exceeded:
            message = f"读取干扰: V={read_voltage:.2f}V > {max_voltage}V"
        else:
            message = "读取参数正常"
        
        return FaultResult(
            fault_type=FaultType.READ_DISTURB,
            detected=detected,
            severity=FaultSeverity.WARNING if detected else FaultSeverity.INFO,
            message=message,
            details={
                "read_count": read_count,
                "read_voltage": read_voltage,
                "max_count": max_count,
                "max_voltage": max_voltage
            },
            attribution="读取条件可能导致状态扰动" if detected else ""
        )
    
    def detect_write_disturb(self, write_voltage: float, adjacent_cell_distance: float,
                            max_voltage: float = 3.0, min_distance: float = 1.0) -> FaultResult:
        """
        检测写入干扰
        
        Args:
            write_voltage: 写入电压
            adjacent_cell_distance: 相邻单元距离
            max_voltage: 最大允许写入电压
            min_distance: 最小安全距离
        
        Returns:
            FaultResult
        """
        voltage_exceeded = write_voltage > max_voltage
        distance_insufficient = adjacent_cell_distance < min_distance
        detected = voltage_exceeded or distance_insufficient
        
        message = ""
        if voltage_exceeded and distance_insufficient:
            message = f"写入干扰: V={write_voltage:.2f}V > {max_voltage}V 且 距离={adjacent_cell_distance:.2f} < {min_distance}"
        elif voltage_exceeded:
            message = f"写入干扰: V={write_voltage:.2f}V > {max_voltage}V"
        elif distance_insufficient:
            message = f"写入干扰: 距离={adjacent_cell_distance:.2f} < {min_distance}"
        else:
            message = "写入参数正常"
        
        return FaultResult(
            fault_type=FaultType.WRITE_DISTURB,
            detected=detected,
            severity=FaultSeverity.WARNING if detected else FaultSeverity.INFO,
            message=message,
            details={
                "write_voltage": write_voltage,
                "adjacent_cell_distance": adjacent_cell_distance,
                "max_voltage": max_voltage,
                "min_distance": min_distance
            },
            attribution="写入条件可能影响相邻单元" if detected else ""
        )
    
    def run_all_detections(self, **kwargs) -> list[FaultResult]:
        """
        运行所有故障检测
        
        Args:
            **kwargs: 各种检测所需的参数
        
        Returns:
            故障检测结果列表
        """
        results = []
        
        # 根据提供的参数运行相应的检测
        if "v_rram" in kwargs and "expected_polarity" in kwargs:
            results.append(self.detect_wrong_bias_polarity(kwargs["v_rram"], kwargs["expected_polarity"]))
        
        if "wl_voltage" in kwargs:
            results.append(self.detect_wl_not_enabled(kwargs["wl_voltage"]))
        
        if "i_rram" in kwargs and "compliance_limit" in kwargs:
            results.append(self.detect_missing_compliance(kwargs["i_rram"], kwargs["compliance_limit"]))
        
        if "sense_current" in kwargs and "reference_current" in kwargs and "margin" in kwargs:
            results.append(self.detect_sense_failure(
                kwargs["sense_current"], 
                kwargs["reference_current"],
                kwargs["margin"]
            ))
        
        if "forming_voltage" in kwargs and "forming_time" in kwargs:
            results.append(self.detect_over_forming(
                kwargs["forming_voltage"],
                kwargs["forming_time"]
            ))
        
        if "read_count" in kwargs and "read_voltage" in kwargs:
            results.append(self.detect_read_disturb(
                kwargs["read_count"],
                kwargs["read_voltage"]
            ))
        
        if "write_voltage" in kwargs and "adjacent_cell_distance" in kwargs:
            results.append(self.detect_write_disturb(
                kwargs["write_voltage"],
                kwargs["adjacent_cell_distance"]
            ))
        
        self.detected_faults = results
        return results
    
    def get_fault_summary(self) -> dict:
        """
        获取故障摘要
        
        Returns:
            故障摘要字典
        """
        total = len(self.detected_faults)
        detected = sum(1 for f in self.detected_faults if f.detected)
        
        severity_counts = {
            FaultSeverity.INFO: 0,
            FaultSeverity.WARNING: 0,
            FaultSeverity.ERROR: 0,
            FaultSeverity.CRITICAL: 0
        }
        
        for fault in self.detected_faults:
            if fault.detected:
                severity_counts[fault.severity] += 1
        
        return {
            "total_checks": total,
            "faults_detected": detected,
            "severity_counts": severity_counts,
            "faults": [f.dict() for f in self.detected_faults if f.detected]
        }
