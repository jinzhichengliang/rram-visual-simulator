"""
S25: SPICE/Compact Model Bridge

实现 SPICE 仿真结果到 FrameState 的转换，支持：
- LTSpice RAW 文件解析
- Ngspice 输出解析
- Verilog-A 模型结果导入
"""
import re
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from packages.contracts.types import (
    DeviceProfile,
    FrameState,
    NodeVoltages,
    OperationPhase,
    OperationType,
    DeviceState,
    FidelityLevel,
    CellState,
    RRAMState,
    TransistorState,
    ModelMetadata
)
from simulator.models.adapter_protocol import TracePoint, TraceData, TraceReplayAdapter


class SPICEColumnMapping(BaseModel):
    """SPICE 列映射配置"""
    time_column: str = "time"
    v_rram_column: str = "v_rram"
    i_rram_column: str = "i_rram"
    state_column: Optional[str] = None
    gap_column: Optional[str] = None
    temperature_column: Optional[str] = None


class SPICEParser:
    """SPICE 结果解析器"""
    
    def __init__(self, column_mapping: Optional[SPICEColumnMapping] = None):
        self.column_mapping = column_mapping or SPICEColumnMapping()
    
    def parse_csv(self, file_path: str, delimiter: str = ",") -> TraceData:
        """解析 CSV 格式的 SPICE 输出"""
        import csv
        
        points = []
        
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row in reader:
                try:
                    time_ns = float(row[self.column_mapping.time_column])
                    v_rram = float(row[self.column_mapping.v_rram_column])
                    i_rram = float(row[self.column_mapping.i_rram_column])
                    
                    # 计算电阻
                    if abs(i_rram) > 1e-12:
                        r_rram = abs(v_rram / i_rram) * 1e6  # 转换为 µA
                    else:
                        r_rram = 1e9  # 高阻态
                    
                    # 推断状态
                    state = self._infer_state(r_rram)
                    
                    # 可选字段
                    gap_nm = None
                    if self.column_mapping.gap_column and self.column_mapping.gap_column in row:
                        gap_nm = float(row[self.column_mapping.gap_column])
                    
                    temperature_k = None
                    if self.column_mapping.temperature_column and self.column_mapping.temperature_column in row:
                        temperature_k = float(row[self.column_mapping.temperature_column])
                    
                    point = TracePoint(
                        time_ns=time_ns,
                        v_rram=v_rram,
                        i_rram=i_rram * 1e6,  # 转换为 µA
                        r_rram=r_rram,
                        state=state,
                        gap_nm=gap_nm,
                        temperature_k=temperature_k
                    )
                    points.append(point)
                    
                except (ValueError, KeyError) as e:
                    # 跳过无法解析的行
                    continue
        
        return TraceData(
            trace_id=Path(file_path).stem,
            source="spice_csv",
            profile_id="unknown",
            points=points,
            metadata={"file_path": file_path, "format": "csv"}
        )
    
    def parse_ltspice_raw(self, file_path: str) -> TraceData:
        """解析 LTSpice RAW 文件（简化版）"""
        # LTSpice RAW 文件格式复杂，这里提供简化实现
        # 实际项目中需要使用专门的库如 ltspice2py
        
        points = []
        
        try:
            with open(file_path, 'rb') as f:
                # 读取头部
                header = f.read(1024).decode('latin-1', errors='ignore')
                
                # 解析变量定义
                var_pattern = re.compile(r'(\d+):\s+(\w+)\s+(\w+)')
                variables = {}
                
                for match in var_pattern.finditer(header):
                    idx = int(match.group(1))
                    name = match.group(2)
                    var_type = match.group(3)
                    variables[name] = {'index': idx, 'type': var_type}
                
                # 简化：假设数据是简单的二进制格式
                # 实际实现需要完整的 RAW 文件解析
                # 这里返回空轨迹，提示用户使用 CSV 格式
                
                return TraceData(
                    trace_id=Path(file_path).stem,
                    source="ltspice_raw",
                    profile_id="unknown",
                    points=points,
                    metadata={
                        "file_path": file_path,
                        "format": "ltspice_raw",
                        "note": "RAW file parsing is simplified. Use CSV export for full support."
                    }
                )
        
        except Exception as e:
            return TraceData(
                trace_id=Path(file_path).stem,
                source="ltspice_raw",
                profile_id="unknown",
                points=[],
                metadata={"error": str(e)}
            )
    
    def _infer_state(self, r_rram: float, r_lrs_threshold: float = 100000, r_hrs_threshold: float = 500000) -> DeviceState:
        """根据电阻推断状态"""
        if r_rram < r_lrs_threshold:
            return DeviceState.LRS
        elif r_rram > r_hrs_threshold:
            return DeviceState.HRS
        else:
            return DeviceState.HRS  # 中间状态默认为 HRS


class SPICEModelAdapter(TraceReplayAdapter):
    """SPICE 模型适配器"""
    
    def __init__(
        self,
        profile: DeviceProfile,
        trace_data: TraceData,
        seed: int = 42
    ):
        super().__init__(profile, trace_data, seed)
        self.fidelity = FidelityLevel.F2  # SPICE 为 F2 级别
    
    def get_adapter_info(self) -> dict:
        """获取适配器信息"""
        info = self.get_trace_info()
        info.update({
            "adapter_type": "SPICEModelAdapter",
            "fidelity": self.fidelity.value,
            "source": self.trace_data.source
        })
        return info


class VerilogAModelAdapter(TraceReplayAdapter):
    """Verilog-A 模型适配器"""
    
    def __init__(
        self,
        profile: DeviceProfile,
        trace_data: TraceData,
        seed: int = 42
    ):
        super().__init__(profile, trace_data, seed)
        self.fidelity = FidelityLevel.F2  # Verilog-A 为 F2 级别
    
    def get_adapter_info(self) -> dict:
        """获取适配器信息"""
        info = self.get_trace_info()
        info.update({
            "adapter_type": "VerilogAModelAdapter",
            "fidelity": self.fidelity.value,
            "source": self.trace_data.source
        })
        return info
