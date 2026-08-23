"""
S27: Calibration Workspace Tests
"""
import pytest
from simulator.calibration import (
    CalibrationTarget,
    CalibrationDataPoint,
    CalibrationResult,
    CalibrationReport,
    CalibrationWorkspace
)
from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceTolerances,
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


class TestCalibrationTarget:
    """校准目标测试"""
    
    def test_target_creation(self):
        """测试目标创建"""
        target = CalibrationTarget(
            parameter_name="v_set",
            target_value=2.0,
            tolerance_pct=5.0
        )
        assert target.parameter_name == "v_set"
        assert target.target_value == 2.0
        assert target.tolerance_pct == 5.0
        assert target.weight == 1.0
    
    def test_target_with_weight(self):
        """测试带权重的目标"""
        target = CalibrationTarget(
            parameter_name="r_lrs",
            target_value=30000,
            tolerance_pct=10.0,
            weight=2.0
        )
        assert target.weight == 2.0


class TestCalibrationDataPoint:
    """校准数据点测试"""
    
    def test_data_point_creation(self):
        """测试数据点创建"""
        dp = CalibrationDataPoint(
            input_value=2.0,
            expected_output=50.0
        )
        assert dp.input_value == 2.0
        assert dp.expected_output == 50.0
        assert dp.actual_output is None
        assert dp.error is None
    
    def test_data_point_with_actual(self):
        """测试带实际值的数据点"""
        dp = CalibrationDataPoint(
            input_value=2.0,
            expected_output=50.0,
            actual_output=48.0,
            error=2.0,
            error_pct=4.0
        )
        assert dp.actual_output == 48.0
        assert dp.error == 2.0
        assert dp.error_pct == 4.0


class TestCalibrationResult:
    """校准结果测试"""
    
    def test_result_creation(self):
        """测试结果创建"""
        result = CalibrationResult(
            parameter_name="v_set",
            initial_value=1.8,
            calibrated_value=2.0,
            error_before=0.5,
            error_after=0.1,
            improvement_pct=80.0,
            data_points=[]
        )
        assert result.parameter_name == "v_set"
        assert result.initial_value == 1.8
        assert result.calibrated_value == 2.0
        assert result.improvement_pct == 80.0


class TestCalibrationWorkspace:
    """校准工作区测试"""
    
    def test_workspace_creation(self, profile):
        """测试工作区创建"""
        workspace = CalibrationWorkspace(profile)
        assert workspace.profile.id == "bipolar_teaching_v1"
        assert len(workspace.targets) == 0
        assert len(workspace.data) == 0
    
    def test_add_target(self, profile):
        """测试添加目标"""
        workspace = CalibrationWorkspace(profile)
        workspace.add_target("v_set", 2.0, 5.0)
        
        assert len(workspace.targets) == 1
        assert workspace.targets[0].parameter_name == "v_set"
        assert workspace.targets[0].target_value == 2.0
    
    def test_add_data_point(self, profile):
        """测试添加数据点"""
        workspace = CalibrationWorkspace(profile)
        workspace.add_data_point("v_set", 2.0, 50.0)
        workspace.add_data_point("v_set", 2.5, 60.0)
        
        assert "v_set" in workspace.data
        assert len(workspace.data["v_set"]) == 2
    
    def test_calculate_error(self, profile):
        """测试误差计算"""
        workspace = CalibrationWorkspace(profile)
        
        error, error_pct = workspace.calculate_error(100.0, 95.0)
        assert error == 5.0
        assert error_pct == 5.0
        
        error, error_pct = workspace.calculate_error(0.0, 5.0)
        assert error == 5.0
        assert error_pct == 0.0  # 除数为 0
    
    def test_calibrate_parameter(self, profile):
        """测试参数校准"""
        workspace = CalibrationWorkspace(profile)
        
        # 添加数据点
        workspace.add_data_point("v_set", 2.0, 50.0)
        workspace.add_data_point("v_set", 2.5, 60.0)
        
        # 定义模型函数
        def model_function(v, param):
            return v * param * 10
        
        # 校准
        result = workspace.calibrate_parameter("v_set", 2.0, model_function)
        
        assert result.parameter_name == "v_set"
        assert result.initial_value == 2.0
        assert len(result.data_points) == 2
    
    def test_calibrate_parameter_no_data(self, profile):
        """测试无数据时校准"""
        workspace = CalibrationWorkspace(profile)
        
        def model_function(v, param):
            return v * param
        
        with pytest.raises(ValueError, match="No data for parameter"):
            workspace.calibrate_parameter("v_set", 2.0, model_function)
    
    def test_calibrate_all(self, profile):
        """测试校准所有参数"""
        workspace = CalibrationWorkspace(profile)
        
        # 添加目标
        workspace.add_target("v_set", 2.0, 10.0)
        
        # 添加数据点
        workspace.add_data_point("v_set", 2.0, 50.0)
        
        # 定义模型函数
        model_functions = {
            "v_set": lambda v, param: v * param * 10
        }
        
        # 校准
        report = workspace.calibrate_all(model_functions)
        
        assert report.profile_id == "bipolar_teaching_v1"
        assert len(report.results) == 1
        assert report.calibration_id.startswith("cal_")
    
    def test_get_summary(self, profile):
        """测试获取摘要"""
        workspace = CalibrationWorkspace(profile)
        workspace.add_target("v_set", 2.0, 5.0)
        workspace.add_data_point("v_set", 2.0, 50.0)
        
        summary = workspace.get_summary()
        
        assert summary["profile_id"] == "bipolar_teaching_v1"
        assert summary["target_count"] == 1
        assert summary["data_point_count"] == 1


class TestCalibrationReport:
    """校准报告测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        report = CalibrationReport(
            profile_id="test_profile",
            calibration_id="cal_001",
            timestamp="2026-08-23T12:00:00",
            targets=[],
            results=[],
            overall_error_before=1.0,
            overall_error_after=0.5,
            overall_improvement_pct=50.0,
            passed=True
        )
        
        assert report.profile_id == "test_profile"
        assert report.passed is True
        assert report.overall_improvement_pct == 50.0
