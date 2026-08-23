"""
S22: Read/Write Disturb Model Tests
"""
import pytest
from simulator.disturb_model import (
    DisturbModel,
    DisturbSimulator,
    DisturbEffect
)


class TestDisturbSimulator:
    """干扰模拟器测试"""
    
    def test_read_disturb_low_risk(self):
        """测试低风险读取干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_read_disturb(
            current_gap_nm=5.0,
            read_voltage=0.3,
            read_count=100,
            temperature_k=300.0
        )
        
        assert effect.disturb_type == "read"
        assert effect.gap_change_nm > 0
        assert effect.state_change_risk in ["low", "medium", "high"]
        assert "读取" in effect.message
    
    def test_read_disturb_high_count(self):
        """测试高次数读取干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_read_disturb(
            current_gap_nm=5.0,
            read_voltage=0.3,
            read_count=10000,
            temperature_k=300.0
        )
        
        assert effect.gap_change_nm > 0.1
        assert effect.state_change_risk in ["medium", "high"]
    
    def test_read_disturb_high_voltage(self):
        """测试高电压读取干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_read_disturb(
            current_gap_nm=5.0,
            read_voltage=0.8,  # 超过阈值
            read_count=100,
            temperature_k=300.0
        )
        
        assert effect.gap_change_nm > 0
        assert "读取" in effect.message
    
    def test_read_disturb_temperature_effect(self):
        """测试温度对读取干扰的影响"""
        simulator = DisturbSimulator()
        
        # 低温
        effect_low_temp = simulator.simulate_read_disturb(
            current_gap_nm=5.0,
            read_voltage=0.3,
            read_count=100,
            temperature_k=280.0
        )
        
        # 高温
        effect_high_temp = simulator.simulate_read_disturb(
            current_gap_nm=5.0,
            read_voltage=0.3,
            read_count=100,
            temperature_k=350.0
        )
        
        # 高温应该有更大的干扰
        assert effect_high_temp.gap_change_nm > effect_low_temp.gap_change_nm
    
    def test_write_disturb_low_risk(self):
        """测试低风险写入干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_write_disturb(
            adjacent_gap_nm=5.0,
            write_voltage=2.0,
            adjacent_distance_nm=10.0,
            temperature_k=300.0
        )
        
        assert effect.disturb_type == "write"
        assert effect.gap_change_nm > 0
        assert effect.state_change_risk in ["low", "medium", "high"]
        assert "写入干扰" in effect.message
    
    def test_write_disturb_close_distance(self):
        """测试近距离写入干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_write_disturb(
            adjacent_gap_nm=5.0,
            write_voltage=3.0,
            adjacent_distance_nm=0.5,  # 很近
            temperature_k=300.0
        )
        
        assert effect.gap_change_nm > 0.1
        assert effect.state_change_risk in ["medium", "high"]
    
    def test_write_disturb_high_voltage(self):
        """测试高电压写入干扰"""
        simulator = DisturbSimulator()
        effect = simulator.simulate_write_disturb(
            adjacent_gap_nm=5.0,
            write_voltage=5.0,
            adjacent_distance_nm=5.0,
            temperature_k=300.0
        )
        
        assert effect.gap_change_nm > 0
    
    def test_estimate_read_endurance(self):
        """测试读取耐久性估算"""
        simulator = DisturbSimulator()
        max_reads = simulator.estimate_read_endurance(
            initial_gap_nm=5.0,
            read_voltage=0.3,
            max_gap_change_nm=0.5,
            temperature_k=300.0
        )
        
        assert max_reads > 0
        assert max_reads < 1000000  # 合理范围内
    
    def test_estimate_read_endurance_high_voltage(self):
        """测试高电压下的读取耐久性"""
        simulator = DisturbSimulator()
        
        # 低电压
        max_reads_low = simulator.estimate_read_endurance(
            initial_gap_nm=5.0,
            read_voltage=0.2,
            max_gap_change_nm=0.5,
            temperature_k=300.0
        )
        
        # 高电压
        max_reads_high = simulator.estimate_read_endurance(
            initial_gap_nm=5.0,
            read_voltage=0.6,
            max_gap_change_nm=0.5,
            temperature_k=300.0
        )
        
        # 高电压应该有更低的耐久性
        assert max_reads_high < max_reads_low
    
    def test_estimate_safe_write_distance(self):
        """测试安全写入距离估算"""
        simulator = DisturbSimulator()
        safe_distance = simulator.estimate_safe_write_distance(
            write_voltage=3.0,
            max_gap_change_nm=0.1,
            temperature_k=300.0
        )
        
        assert safe_distance > 0
        assert safe_distance < 100.0  # 合理范围内
    
    def test_estimate_safe_write_distance_high_voltage(self):
        """测试高电压下的安全写入距离"""
        simulator = DisturbSimulator()
        
        # 低电压
        safe_dist_low = simulator.estimate_safe_write_distance(
            write_voltage=2.0,
            max_gap_change_nm=0.1,
            temperature_k=300.0
        )
        
        # 高电压
        safe_dist_high = simulator.estimate_safe_write_distance(
            write_voltage=4.0,
            max_gap_change_nm=0.1,
            temperature_k=300.0
        )
        
        # 高电压应该需要更大的安全距离
        assert safe_dist_high > safe_dist_low


class TestDisturbModel:
    """干扰模型参数测试"""
    
    def test_default_model(self):
        """测试默认模型参数"""
        model = DisturbModel()
        
        assert model.read_disturb_rate_per_read > 0
        assert model.read_disturb_voltage_threshold > 0
        assert model.write_disturb_coupling_factor > 0
        assert model.temperature_acceleration_factor > 1.0
    
    def test_custom_model(self):
        """测试自定义模型参数"""
        model = DisturbModel(
            read_disturb_rate_per_read=0.002,
            read_disturb_voltage_threshold=0.6,
            write_disturb_coupling_factor=0.15
        )
        
        assert model.read_disturb_rate_per_read == 0.002
        assert model.read_disturb_voltage_threshold == 0.6
        assert model.write_disturb_coupling_factor == 0.15


class TestDisturbEffect:
    """干扰效应测试"""
    
    def test_disturb_effect_creation(self):
        """测试干扰效应创建"""
        effect = DisturbEffect(
            disturb_type="read",
            gap_change_nm=0.05,
            resistance_change_pct=1.0,
            state_change_risk="low",
            message="测试消息"
        )
        
        assert effect.disturb_type == "read"
        assert effect.gap_change_nm == 0.05
        assert effect.resistance_change_pct == 1.0
        assert effect.state_change_risk == "low"
        assert effect.message == "测试消息"
    
    def test_disturb_effect_risk_levels(self):
        """测试不同风险级别"""
        for risk in ["low", "medium", "high"]:
            effect = DisturbEffect(
                disturb_type="read",
                gap_change_nm=0.05,
                resistance_change_pct=1.0,
                state_change_risk=risk,
                message=f"{risk} risk"
            )
            assert effect.state_change_risk == risk
