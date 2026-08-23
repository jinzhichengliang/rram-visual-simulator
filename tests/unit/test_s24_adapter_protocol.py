"""
S24: Model Adapter Protocol Tests
"""
import pytest
from simulator.models.adapter_protocol import (
    TracePoint,
    TraceData,
    TraceReplayAdapter
)
from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceTolerances,
    NodeVoltages,
    OperationPhase,
    OperationType,
    DeviceState,
    FidelityLevel,
    LogicMap,
    Polarity,
    StackOrientation
)


@pytest.fixture
def profile():
    """标准教学配置"""
    return DeviceProfile(
        id="bipolar_teaching_v1",
        version="1.0.0",
        stackOrientation=StackOrientation.BL_RRAM_NMOS_SL,
        vRramSignConvention="V(top)-V(bottom)",
        setPolarity=Polarity.POSITIVE,
        resetPolarity=Polarity.NEGATIVE,
        logicMap=LogicMap(LRS=1, HRS=0),
        ranges=DeviceRanges(
            vRead=[0.1, 0.2],
            vSet=[1.5, 2.5],
            vReset=[-2.5, -1.5],
            vForm=[3.0, 4.0],
            rLrs=[10000, 50000],
            rHrs=[500000, 5000000]
        ),
        complianceUa=50.0,
        tolerances=DeviceTolerances(
            readDisturbPct=1.0,
            currentConservationPct=5.0,
            crossViewAbs=0.001
        )
    )


@pytest.fixture
def sample_trace(profile):
    """示例轨迹数据"""
    points = [
        TracePoint(time_ns=0, v_rram=0.0, i_rram=0.0, r_rram=1e9, state=DeviceState.PRISTINE),
        TracePoint(time_ns=10, v_rram=3.5, i_rram=50.0, r_rram=30000, state=DeviceState.LRS, gap_nm=0.5),
        TracePoint(time_ns=20, v_rram=0.15, i_rram=5.0, r_rram=30000, state=DeviceState.LRS, gap_nm=0.5),
        TracePoint(time_ns=30, v_rram=-2.0, i_rram=-0.5, r_rram=1000000, state=DeviceState.HRS, gap_nm=8.0),
        TracePoint(time_ns=40, v_rram=0.15, i_rram=0.15, r_rram=1000000, state=DeviceState.HRS, gap_nm=8.0),
    ]
    return TraceData(
        trace_id="test_trace_001",
        source="experiment",
        profile_id=profile.id,
        points=points,
        metadata={"description": "Test trace for unit testing"}
    )


class TestTraceReplayAdapter:
    """轨迹回放适配器测试"""
    
    def test_adapter_creation(self, profile, sample_trace):
        """测试适配器创建"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        assert adapter.fidelity == FidelityLevel.F3
        assert adapter.trace_data.trace_id == "test_trace_001"
    
    def test_compute_frame_at_exact_time(self, profile, sample_trace):
        """测试在精确时间点计算帧"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        nodes = NodeVoltages(wl=[1.8], bl=[0.15], sl=[0.0])
        frame = adapter.compute_frame(
            frame_id="f1",
            time_ns=20.0,
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.LRS,
            forming_done=True
        )
        
        assert frame.timeNs == 20.0
        assert frame.cell.rram.v == 0.15
        assert frame.cell.rram.i == 5.0
        assert frame.cell.rram.state == DeviceState.LRS
    
    def test_compute_frame_interpolated(self, profile, sample_trace):
        """测试在中间时间点计算帧"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        nodes = NodeVoltages(wl=[1.8], bl=[0.15], sl=[0.0])
        frame = adapter.compute_frame(
            frame_id="f1",
            time_ns=25.0,  # 在 20ns 和 30ns 之间
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.LRS,
            forming_done=True
        )
        
        # 应该返回最接近的点（30ns）
        assert frame.cell.rram.state in [DeviceState.LRS, DeviceState.HRS]
    
    def test_compute_frame_before_trace(self, profile, sample_trace):
        """测试在轨迹开始之前计算帧"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        nodes = NodeVoltages(wl=[0.0], bl=[0.0], sl=[0.0])
        frame = adapter.compute_frame(
            frame_id="f1",
            time_ns=0.0,  # 在轨迹开始点
            operation=OperationType.READ,
            phase=OperationPhase.PREPARE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.PRISTINE,
            forming_done=False
        )
        
        # 应该返回第一个轨迹点
        assert frame.cell.rram.state == DeviceState.PRISTINE
    
    def test_compute_frame_after_trace(self, profile, sample_trace):
        """测试在轨迹结束之后计算帧"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        nodes = NodeVoltages(wl=[1.8], bl=[0.15], sl=[0.0])
        frame = adapter.compute_frame(
            frame_id="f1",
            time_ns=100.0,  # 在轨迹结束之后
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.HRS,
            forming_done=True
        )
        
        # 应该返回最后一个轨迹点
        assert frame.cell.rram.state == DeviceState.HRS
    
    def test_reset(self, profile, sample_trace):
        """测试重置"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        
        # 执行一些操作
        nodes = NodeVoltages(wl=[1.8], bl=[0.15], sl=[0.0])
        adapter.compute_frame(
            frame_id="f1",
            time_ns=20.0,
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.LRS,
            forming_done=True
        )
        
        # 重置
        adapter.reset()
        assert adapter.current_point_idx == 0
    
    def test_get_trace_info(self, profile, sample_trace):
        """测试获取轨迹信息"""
        adapter = TraceReplayAdapter(profile, sample_trace)
        info = adapter.get_trace_info()
        
        assert info["trace_id"] == "test_trace_001"
        assert info["source"] == "experiment"
        assert info["point_count"] == 5
        assert info["time_range_ns"] == (0, 40)
    
    def test_empty_trace(self, profile):
        """测试空轨迹"""
        empty_trace = TraceData(
            trace_id="empty_trace",
            source="experiment",
            profile_id=profile.id,
            points=[]
        )
        adapter = TraceReplayAdapter(profile, empty_trace)
        
        nodes = NodeVoltages(wl=[1.8], bl=[0.15], sl=[0.0])
        frame = adapter.compute_frame(
            frame_id="f1",
            time_ns=20.0,
            operation=OperationType.READ,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            current_state=DeviceState.PRISTINE,
            forming_done=False
        )
        
        # 应该返回默认帧
        assert frame.cell.rram.state == DeviceState.PRISTINE


class TestTracePoint:
    """轨迹点测试"""
    
    def test_trace_point_creation(self):
        """测试轨迹点创建"""
        point = TracePoint(
            time_ns=10.0,
            v_rram=2.0,
            i_rram=30.0,
            r_rram=30000,
            state=DeviceState.LRS
        )
        
        assert point.time_ns == 10.0
        assert point.v_rram == 2.0
        assert point.i_rram == 30.0
        assert point.state == DeviceState.LRS
    
    def test_trace_point_with_observables(self):
        """测试带可观察量的轨迹点"""
        point = TracePoint(
            time_ns=10.0,
            v_rram=2.0,
            i_rram=30.0,
            r_rram=30000,
            state=DeviceState.LRS,
            gap_nm=0.5,
            filament_proxy=0.9,
            temperature_k=350.0
        )
        
        assert point.gap_nm == 0.5
        assert point.filament_proxy == 0.9
        assert point.temperature_k == 350.0


class TestTraceData:
    """轨迹数据测试"""
    
    def test_trace_data_creation(self, profile):
        """测试轨迹数据创建"""
        points = [
            TracePoint(time_ns=0, v_rram=0.0, i_rram=0.0, r_rram=1e9, state=DeviceState.PRISTINE),
            TracePoint(time_ns=10, v_rram=2.0, i_rram=30.0, r_rram=30000, state=DeviceState.LRS),
        ]
        trace = TraceData(
            trace_id="test_trace",
            source="experiment",
            profile_id=profile.id,
            points=points
        )
        
        assert trace.trace_id == "test_trace"
        assert len(trace.points) == 2
    
    def test_trace_data_with_metadata(self, profile):
        """测试带元数据的轨迹数据"""
        trace = TraceData(
            trace_id="test_trace",
            source="spice",
            profile_id=profile.id,
            points=[],
            metadata={"simulation_tool": "LTSpice", "version": "1.0"}
        )
        
        assert trace.metadata["simulation_tool"] == "LTSpice"
