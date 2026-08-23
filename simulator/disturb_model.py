"""
S22: Read/Write Disturb Model

实现读取干扰和写入干扰的物理模型：
- Read Disturb: 读取操作对器件状态的微小扰动
- Write Disturb: 写入操作对相邻单元的干扰
"""
from pydantic import BaseModel
from typing import Optional


class DisturbModel(BaseModel):
    """干扰模型参数"""
    # Read disturb 参数
    read_disturb_rate_per_read: float = 0.001  # 每次读取的 gap 变化率 (nm/read)
    read_disturb_voltage_threshold: float = 0.5  # 读取干扰电压阈值 (V)
    
    # Write disturb 参数
    write_disturb_coupling_factor: float = 0.1  # 写入耦合因子 (0-1)
    write_disturb_distance_factor: float = 1.0  # 距离因子 (nm)
    
    # 温度影响
    temperature_acceleration_factor: float = 1.05  # 温度加速因子 (每10°C)
    reference_temperature: float = 300.0  # 参考温度 (K)


class DisturbEffect(BaseModel):
    """干扰效应"""
    disturb_type: str  # "read" 或 "write"
    gap_change_nm: float  # gap 变化量 (nm)
    resistance_change_pct: float  # 电阻变化百分比 (%)
    state_change_risk: str  # "low", "medium", "high"
    message: str


class DisturbSimulator:
    """干扰模拟器"""
    
    def __init__(self, model: Optional[DisturbModel] = None):
        self.model = model or DisturbModel()
    
    def simulate_read_disturb(
        self,
        current_gap_nm: float,
        read_voltage: float,
        read_count: int,
        temperature_k: float = 300.0
    ) -> DisturbEffect:
        """
        模拟读取干扰
        
        Args:
            current_gap_nm: 当前 gap 大小 (nm)
            read_voltage: 读取电压 (V)
            read_count: 读取次数
            temperature_k: 温度 (K)
        
        Returns:
            DisturbEffect
        """
        # 基础 gap 变化
        base_gap_change = self.model.read_disturb_rate_per_read * read_count
        
        # 电压影响（超过阈值时加速）
        if read_voltage > self.model.read_disturb_voltage_threshold:
            voltage_factor = 1.0 + (read_voltage - self.model.read_disturb_voltage_threshold) * 0.5
        else:
            voltage_factor = 1.0
        
        # 温度影响
        temp_diff = temperature_k - self.model.reference_temperature
        temp_factor = self.model.temperature_acceleration_factor ** (temp_diff / 10.0)
        
        # 计算总 gap 变化
        gap_change = base_gap_change * voltage_factor * temp_factor
        
        # 计算电阻变化百分比
        # R = R_0 * exp(gap / gap_0)，假设 gap_0 = 1nm
        if current_gap_nm > 0:
            resistance_change_pct = (1.0 - (current_gap_nm + gap_change) / current_gap_nm) * 100
        else:
            resistance_change_pct = 0.0
        
        # 评估状态变化风险
        if abs(gap_change) > 0.5:
            risk = "high"
            message = f"高风险: 读取 {read_count} 次导致 gap 变化 {gap_change:.3f}nm，可能改变器件状态"
        elif abs(gap_change) > 0.1:
            risk = "medium"
            message = f"中风险: 读取 {read_count} 次导致 gap 变化 {gap_change:.3f}nm，状态可能漂移"
        else:
            risk = "low"
            message = f"低风险: 读取 {read_count} 次导致 gap 变化 {gap_change:.3f}nm，状态稳定"
        
        return DisturbEffect(
            disturb_type="read",
            gap_change_nm=gap_change,
            resistance_change_pct=resistance_change_pct,
            state_change_risk=risk,
            message=message
        )
    
    def simulate_write_disturb(
        self,
        adjacent_gap_nm: float,
        write_voltage: float,
        adjacent_distance_nm: float,
        temperature_k: float = 300.0
    ) -> DisturbEffect:
        """
        模拟写入干扰
        
        Args:
            adjacent_gap_nm: 相邻单元 gap 大小 (nm)
            write_voltage: 写入电压 (V)
            adjacent_distance_nm: 相邻单元距离 (nm)
            temperature_k: 温度 (K)
        
        Returns:
            DisturbEffect
        """
        # 基础耦合效应
        coupling_effect = self.model.write_disturb_coupling_factor
        
        # 距离影响（距离越近，干扰越大）
        distance_factor = self.model.write_disturb_distance_factor / max(adjacent_distance_nm, 0.1)
        
        # 电压影响
        voltage_factor = abs(write_voltage) / 2.0  # 归一化到 2V
        
        # 温度影响
        temp_diff = temperature_k - self.model.reference_temperature
        temp_factor = self.model.temperature_acceleration_factor ** (temp_diff / 10.0)
        
        # 计算总 gap 变化
        gap_change = coupling_effect * distance_factor * voltage_factor * temp_factor
        
        # 计算电阻变化百分比
        if adjacent_gap_nm > 0:
            resistance_change_pct = (1.0 - (adjacent_gap_nm + gap_change) / adjacent_gap_nm) * 100
        else:
            resistance_change_pct = 0.0
        
        # 评估状态变化风险
        if abs(gap_change) > 0.3:
            risk = "high"
            message = f"高风险: 写入干扰导致相邻单元 gap 变化 {gap_change:.3f}nm，可能改变状态"
        elif abs(gap_change) > 0.05:
            risk = "medium"
            message = f"中风险: 写入干扰导致相邻单元 gap 变化 {gap_change:.3f}nm，状态可能漂移"
        else:
            risk = "low"
            message = f"低风险: 写入干扰导致相邻单元 gap 变化 {gap_change:.3f}nm，影响可忽略"
        
        return DisturbEffect(
            disturb_type="write",
            gap_change_nm=gap_change,
            resistance_change_pct=resistance_change_pct,
            state_change_risk=risk,
            message=message
        )
    
    def estimate_read_endurance(
        self,
        initial_gap_nm: float,
        read_voltage: float,
        max_gap_change_nm: float = 0.5,
        temperature_k: float = 300.0
    ) -> int:
        """
        估算读取耐久性（最大读取次数）
        
        Args:
            initial_gap_nm: 初始 gap 大小 (nm)
            read_voltage: 读取电压 (V)
            max_gap_change_nm: 最大允许 gap 变化 (nm)
            temperature_k: 温度 (K)
        
        Returns:
            最大读取次数
        """
        # 计算每次读取的 gap 变化
        single_read_effect = self.simulate_read_disturb(
            initial_gap_nm, read_voltage, 1, temperature_k
        )
        
        if single_read_effect.gap_change_nm <= 0:
            return float('inf')  # 无干扰
        
        # 计算最大读取次数
        max_reads = int(max_gap_change_nm / single_read_effect.gap_change_nm)
        
        return max_reads
    
    def estimate_safe_write_distance(
        self,
        write_voltage: float,
        max_gap_change_nm: float = 0.1,
        temperature_k: float = 300.0
    ) -> float:
        """
        估算安全写入距离
        
        Args:
            write_voltage: 写入电压 (V)
            max_gap_change_nm: 最大允许 gap 变化 (nm)
            temperature_k: 温度 (K)
        
        Returns:
            安全距离 (nm)
        """
        # 使用二分法查找安全距离
        min_dist = 0.1
        max_dist = 100.0
        
        for _ in range(20):  # 迭代20次
            mid_dist = (min_dist + max_dist) / 2
            
            effect = self.simulate_write_disturb(
                5.0,  # 假设相邻单元 gap = 5nm
                write_voltage,
                mid_dist,
                temperature_k
            )
            
            if abs(effect.gap_change_nm) > max_gap_change_nm:
                min_dist = mid_dist
            else:
                max_dist = mid_dist
        
        return max_dist
