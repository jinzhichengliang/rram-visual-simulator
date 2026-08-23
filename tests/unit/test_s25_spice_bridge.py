"""
S25: SPICE/Compact Model Bridge Tests
"""
import os
import pytest
import tempfile
import csv
from pathlib import Path
from simulator.models.spice_bridge import (
    SPICEColumnMapping,
    SPICEParser,
    SPICEModelAdapter,
    VerilogAModelAdapter
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
def sample_csv_file():
    """创建示例 CSV 文件"""
    # 创建临时文件
    fd, path = tempfile.mkstemp(suffix='.csv')
    
    try:
        # 写入 CSV 数据
        with os.fdopen(fd, 'w') as f:
            writer = csv.DictWriter(f, fieldnames=['time', 'v_rram', 'i_rram', 'gap_nm'])
            writer.writeheader()
            writer.writerow({'time': 0, 'v_rram': 0.0, 'i_rram': 0.0, 'gap_nm': 5.0})
            writer.writerow({'time': 10, 'v_rram': 3.5, 'i_rram': 50e-6, 'gap_nm': 0.5})
            writer.writerow({'time': 20, 'v_rram': 0.15, 'i_rram': 5e-6, 'gap_nm': 0.5})
            writer.writerow({'time': 30, 'v_rram': -2.0, 'i_rram': -0.5e-6, 'gap_nm': 8.0})
            writer.writerow({'time': 40, 'v_rram': 0.15, 'i_rram': 0.15e-6, 'gap_nm': 8.0})
        
        yield path
    finally:
        # 清理
        if Path(path).exists():
            Path(path).unlink()


class TestSPICEParser:
    """SPICE 解析器测试"""
    
    def test_parser_creation(self):
        """测试解析器创建"""
        parser = SPICEParser()
        assert parser.column_mapping.time_column == "time"
        assert parser.column_mapping.v_rram_column == "v_rram"
    
    def test_custom_column_mapping(self):
        """测试自定义列映射"""
        mapping = SPICEColumnMapping(
            time_column="t",
            v_rram_column="v_device",
            i_rram_column="i_device"
        )
        parser = SPICEParser(column_mapping=mapping)
        assert parser.column_mapping.time_column == "t"
        assert parser.column_mapping.v_rram_column == "v_device"
    
    def test_parse_csv(self, sample_csv_file):
        """测试 CSV 解析"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        
        assert trace_data.trace_id == Path(sample_csv_file).stem
        assert trace_data.source == "spice_csv"
        assert len(trace_data.points) == 5
        
        # 检查第一个点
        assert trace_data.points[0].time_ns == 0
        assert trace_data.points[0].v_rram == 0.0
        assert trace_data.points[0].state == DeviceState.PRISTINE or trace_data.points[0].state == DeviceState.HRS
    
    def test_parse_csv_with_gap(self, sample_csv_file):
        """测试带 gap 数据的 CSV 解析"""
        mapping = SPICEColumnMapping(gap_column="gap_nm")
        parser = SPICEParser(column_mapping=mapping)
        trace_data = parser.parse_csv(sample_csv_file)
        
        assert trace_data.points[1].gap_nm == 0.5
        assert trace_data.points[3].gap_nm == 8.0
    
    def test_infer_state_lrs(self):
        """测试 LRS 状态推断"""
        parser = SPICEParser()
        state = parser._infer_state(30000)  # 30kΩ
        assert state == DeviceState.LRS
    
    def test_infer_state_hrs(self):
        """测试 HRS 状态推断"""
        parser = SPICEParser()
        state = parser._infer_state(1000000)  # 1MΩ
        assert state == DeviceState.HRS
    
    def test_infer_state_intermediate(self):
        """测试中间状态推断"""
        parser = SPICEParser()
        state = parser._infer_state(300000)  # 300kΩ
        assert state == DeviceState.HRS  # 默认为 HRS


class TestSPICEModelAdapter:
    """SPICE 模型适配器测试"""
    
    def test_adapter_creation(self, profile, sample_csv_file):
        """测试适配器创建"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        adapter = SPICEModelAdapter(profile, trace_data)
        
        assert adapter.fidelity == FidelityLevel.F2
    
    def test_compute_frame(self, profile, sample_csv_file):
        """测试帧计算"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        adapter = SPICEModelAdapter(profile, trace_data)
        
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
    
    def test_get_adapter_info(self, profile, sample_csv_file):
        """测试获取适配器信息"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        adapter = SPICEModelAdapter(profile, trace_data)
        
        info = adapter.get_adapter_info()
        assert info["adapter_type"] == "SPICEModelAdapter"
        assert info["fidelity"] == "F2"


class TestVerilogAModelAdapter:
    """Verilog-A 模型适配器测试"""
    
    def test_adapter_creation(self, profile, sample_csv_file):
        """测试适配器创建"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        adapter = VerilogAModelAdapter(profile, trace_data)
        
        assert adapter.fidelity == FidelityLevel.F2
    
    def test_get_adapter_info(self, profile, sample_csv_file):
        """测试获取适配器信息"""
        parser = SPICEParser()
        trace_data = parser.parse_csv(sample_csv_file)
        adapter = VerilogAModelAdapter(profile, trace_data)
        
        info = adapter.get_adapter_info()
        assert info["adapter_type"] == "VerilogAModelAdapter"
        assert info["fidelity"] == "F2"


class TestSPICEColumnMapping:
    """SPICE 列映射测试"""
    
    def test_default_mapping(self):
        """测试默认映射"""
        mapping = SPICEColumnMapping()
        assert mapping.time_column == "time"
        assert mapping.v_rram_column == "v_rram"
        assert mapping.i_rram_column == "i_rram"
    
    def test_custom_mapping(self):
        """测试自定义映射"""
        mapping = SPICEColumnMapping(
            time_column="t",
            v_rram_column="v_dev",
            i_rram_column="i_dev",
            gap_column="gap"
        )
        assert mapping.time_column == "t"
        assert mapping.v_rram_column == "v_dev"
        assert mapping.gap_column == "gap"
