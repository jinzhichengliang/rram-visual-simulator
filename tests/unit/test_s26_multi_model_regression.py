"""
S26: Multi-Model Regression Tests
"""
import pytest
from simulator.models.multi_model_regression import (
    ModelComparison,
    RegressionTest,
    RegressionResult,
    MultiModelRunner,
    RegressionTestSuite
)
from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceTolerances,
    NodeVoltages,
    OperationPhase,
    OperationType,
    DeviceState,
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


class TestMultiModelRunner:
    """多模型运行器测试"""
    
    def test_runner_creation(self, profile):
        """测试运行器创建"""
        runner = MultiModelRunner(profile)
        assert "teaching" in runner.models
        assert "param_compact" in runner.models
    
    def test_run_comparison(self, profile):
        """测试模型比较"""
        runner = MultiModelRunner(profile)
        
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])
        comparison = runner.run_comparison(
            frame_id="test_001",
            time_ns=10.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0},
            reference_model="teaching"
        )
        
        assert comparison.frame_id == "test_001"
        assert comparison.time_ns == 10.0
        assert len(comparison.models) == 2
        assert "teaching" in comparison.models
        assert "param_compact" in comparison.models
        
        # 参考模型差异应为 0
        assert comparison.v_rram_diff["teaching"] == 0.0
        assert comparison.i_rram_diff["teaching"] == 0.0
        assert comparison.state_match["teaching"] is True
    
    def test_run_comparison_with_invalid_reference(self, profile):
        """测试使用无效参考模型"""
        runner = MultiModelRunner(profile)
        
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])
        
        with pytest.raises(ValueError, match="Reference model 'invalid' not found"):
            runner.run_comparison(
                frame_id="test_001",
                time_ns=10.0,
                operation=OperationType.SET,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                reference_model="invalid"
            )


class TestRegressionTest:
    """回归测试配置测试"""
    
    def test_regression_test_creation(self):
        """测试回归测试创建"""
        test = RegressionTest(
            test_id="test_set_001",
            description="SET operation regression test",
            operation=OperationType.SET,
            pulse_params={"amplitude_v": 2.0, "width_ns": 100},
            duration_ns=100.0
        )
        
        assert test.test_id == "test_set_001"
        assert test.operation == OperationType.SET
        assert test.reference_model == "teaching"
        assert test.tolerance["v_rram_pct"] == 5.0
    
    def test_custom_tolerance(self):
        """测试自定义容差"""
        test = RegressionTest(
            test_id="test_custom",
            description="Custom tolerance test",
            operation=OperationType.READ,
            pulse_params={"amplitude_v": 0.15},
            duration_ns=50.0,
            tolerance={
                "v_rram_pct": 1.0,
                "i_rram_pct": 2.0,
                "r_rram_pct": 5.0,
                "state_match": True
            }
        )
        
        assert test.tolerance["v_rram_pct"] == 1.0
        assert test.tolerance["i_rram_pct"] == 2.0


class TestRegressionResult:
    """回归测试结果测试"""
    
    def test_regression_result_passed(self):
        """测试通过的回归结果"""
        result = RegressionResult(
            test_id="test_001",
            passed=True,
            comparisons=[],
            failed_checks=[],
            summary="Test passed"
        )
        
        assert result.passed is True
        assert len(result.failed_checks) == 0
    
    def test_regression_result_failed(self):
        """测试失败的回归结果"""
        result = RegressionResult(
            test_id="test_001",
            passed=False,
            comparisons=[],
            failed_checks=["V_RRAM diff 10% > 5%"],
            summary="Test failed"
        )
        
        assert result.passed is False
        assert len(result.failed_checks) == 1


class TestRegressionTestSuite:
    """回归测试套件测试"""
    
    def test_suite_creation(self, profile):
        """测试套件创建"""
        suite = RegressionTestSuite(profile)
        assert len(suite.tests) == 0
        assert len(suite.results) == 0
    
    def test_add_test(self, profile):
        """测试添加测试"""
        suite = RegressionTestSuite(profile)
        
        test = RegressionTest(
            test_id="test_001",
            description="Test 1",
            operation=OperationType.SET,
            pulse_params={"amplitude_v": 2.0},
            duration_ns=100.0
        )
        
        suite.add_test(test)
        assert len(suite.tests) == 1
    
    def test_run_all(self, profile):
        """测试运行所有测试"""
        suite = RegressionTestSuite(profile)
        
        # 添加两个测试
        test1 = RegressionTest(
            test_id="test_set",
            description="SET test",
            operation=OperationType.SET,
            pulse_params={"amplitude_v": 2.0},
            duration_ns=100.0
        )
        
        test2 = RegressionTest(
            test_id="test_read",
            description="READ test",
            operation=OperationType.READ,
            pulse_params={"amplitude_v": 0.15},
            duration_ns=50.0
        )
        
        suite.add_test(test1)
        suite.add_test(test2)
        
        results = suite.run_all()
        assert len(results) == 2
    
    def test_get_summary(self, profile):
        """测试获取摘要"""
        suite = RegressionTestSuite(profile)
        
        test = RegressionTest(
            test_id="test_001",
            description="Test",
            operation=OperationType.SET,
            pulse_params={"amplitude_v": 2.0},
            duration_ns=100.0
        )
        
        suite.add_test(test)
        suite.run_all()
        
        summary = suite.get_summary()
        assert summary["total_tests"] == 1
        assert "passed" in summary
        assert "failed" in summary
        assert "pass_rate" in summary


class TestModelComparison:
    """模型比较测试"""
    
    def test_model_comparison_creation(self, profile):
        """测试模型比较创建"""
        runner = MultiModelRunner(profile)
        
        nodes = NodeVoltages(wl=[1.8], bl=[2.0], sl=[0.0])
        comparison = runner.run_comparison(
            frame_id="test_001",
            time_ns=10.0,
            operation=OperationType.SET,
            phase=OperationPhase.ACTIVE,
            nodes=nodes,
            selected_cell={"row": 0, "col": 0}
        )
        
        assert comparison.reference_model == "teaching"
        assert len(comparison.v_rram_diff) == 2
        assert len(comparison.i_rram_diff) == 2
        assert len(comparison.state_match) == 2
