"""
S24: Model Adapter Protocol

定义统一的模型适配器接口，支持多种模型后端：
- TeachingModelAdapter (F0)
- ParamCompactAdapter (F1)
- SPICE/Verilog-A adapters (F2)
- TraceReplayAdapter (实验数据回放)
"""
from typing import Protocol, runtime_checkable
from pydantic import BaseModel
from packages.contracts.types import (
    DeviceProfile,
    FrameState,
    NodeVoltages,
    OperationPhase,
    OperationType,
    DeviceState,
    FidelityLevel
)


@runtime_checkable
class ModelAdapter(Protocol):
    """模型适配器协议"""
    
    @property
    def fidelity(self) -> FidelityLevel:
        """返回模型保真度级别"""
        ...
    
    def compute_frame(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: dict[str, int],
        current_state: DeviceState,
        forming_done: bool
    ) -> FrameState:
        """计算帧状态"""
        ...
    
    def reset(self):
        """重置模型状态"""
        ...


class TracePoint(BaseModel):
    """轨迹点"""
    time_ns: float
    v_rram: float
    i_rram: float
    r_rram: float
    state: DeviceState
    gap_nm: float | None = None
    filament_proxy: float | None = None
    temperature_k: float | None = None


class TraceData(BaseModel):
    """轨迹数据"""
    trace_id: str
    source: str  # "experiment", "spice", "verilog_a", etc.
    profile_id: str
    points: list[TracePoint]
    metadata: dict = {}


class TraceReplayAdapter:
    """
    轨迹回放适配器
    
    从预记录的轨迹数据回放器件行为，用于：
    - 验证仿真器与实验数据的一致性
    - 教学演示真实器件行为
    - 模型校准参考
    """
    
    def __init__(self, profile: DeviceProfile, trace_data: TraceData, seed: int = 42):
        self.profile = profile
        self.trace_data = trace_data
        self.seed = seed
        self.fidelity = FidelityLevel.F3  # 实验数据为最高保真度
        self.current_point_idx = 0
    
    def compute_frame(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: dict[str, int],
        current_state: DeviceState,
        forming_done: bool
    ) -> FrameState:
        """从轨迹数据回放帧状态"""
        # 找到最接近的轨迹点
        target_point = self._find_nearest_point(time_ns)
        
        if target_point is None:
            # 如果没有轨迹点，返回默认状态
            return self._create_default_frame(
                frame_id, time_ns, operation, phase, nodes, selected_cell
            )
        
        # 从轨迹点构建帧状态
        from packages.contracts.types import (
            CellState, RRAMState, TransistorState, ModelMetadata
        )
        
        # 推断晶体管状态
        wl_voltage = nodes.wl[selected_cell["row"]] if selected_cell["row"] < len(nodes.wl) else 0.0
        transistor_on = wl_voltage > 0.7  # Vth
        
        transistor = TransistorState(
            vg=wl_voltage,
            vs=0.0,
            vd=target_point.v_rram if transistor_on else 0.0,
            on=transistor_on,
            complianceLimitUa=self.profile.complianceUa
        )
        
        rram = RRAMState(
            v=target_point.v_rram,
            i=target_point.i_rram,
            r=target_point.r_rram,
            state=target_point.state,
            formingDone=forming_done or target_point.state != DeviceState.PRISTINE,
            gapNm=target_point.gap_nm,
            filamentProxy=target_point.filament_proxy,
            temperatureK=target_point.temperature_k
        )
        
        cell = CellState(transistor=transistor, rram=rram)
        
        model = ModelMetadata(
            fidelity=self.fidelity,
            profileId=self.profile.id,
            profileVersion=self.profile.version,
            seed=self.seed
        )
        
        return FrameState(
            frameId=frame_id,
            timeNs=time_ns,
            operation=operation,
            phase=phase,
            selectedCell=selected_cell,
            nodes=nodes,
            cell=cell,
            sense=None,
            model=model,
            checks=[]
        )
    
    def _find_nearest_point(self, time_ns: float) -> TracePoint | None:
        """找到最接近指定时间的轨迹点"""
        if not self.trace_data.points:
            return None
        
        # 二分查找最接近的点
        left, right = 0, len(self.trace_data.points) - 1
        
        while left <= right:
            mid = (left + right) // 2
            mid_time = self.trace_data.points[mid].time_ns
            
            if mid_time == time_ns:
                return self.trace_data.points[mid]
            elif mid_time < time_ns:
                left = mid + 1
            else:
                right = mid - 1
        
        # 返回最接近的点
        if left >= len(self.trace_data.points):
            return self.trace_data.points[-1]
        elif right < 0:
            return self.trace_data.points[0]
        else:
            # 比较左右两个点哪个更接近
            left_diff = abs(self.trace_data.points[left].time_ns - time_ns)
            right_diff = abs(self.trace_data.points[right].time_ns - time_ns)
            return self.trace_data.points[left] if left_diff <= right_diff else self.trace_data.points[right]
    
    def _create_default_frame(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: dict[str, int]
    ) -> FrameState:
        """创建默认帧状态"""
        from packages.contracts.types import (
            CellState, RRAMState, TransistorState, ModelMetadata
        )
        
        transistor = TransistorState(vg=0.0, vs=0.0, vd=0.0, on=False)
        rram = RRAMState(v=0.0, i=0.0, r=1e9, state=DeviceState.PRISTINE, formingDone=False)
        cell = CellState(transistor=transistor, rram=rram)
        
        model = ModelMetadata(
            fidelity=self.fidelity,
            profileId=self.profile.id,
            profileVersion=self.profile.version,
            seed=self.seed
        )
        
        return FrameState(
            frameId=frame_id,
            timeNs=time_ns,
            operation=operation,
            phase=phase,
            selectedCell=selected_cell,
            nodes=nodes,
            cell=cell,
            sense=None,
            model=model,
            checks=[]
        )
    
    def reset(self):
        """重置适配器状态"""
        self.current_point_idx = 0
    
    def get_trace_info(self) -> dict:
        """获取轨迹信息"""
        return {
            "trace_id": self.trace_data.trace_id,
            "source": self.trace_data.source,
            "profile_id": self.trace_data.profile_id,
            "point_count": len(self.trace_data.points),
            "time_range_ns": (
                self.trace_data.points[0].time_ns if self.trace_data.points else 0,
                self.trace_data.points[-1].time_ns if self.trace_data.points else 0
            ),
            "metadata": self.trace_data.metadata
        }
