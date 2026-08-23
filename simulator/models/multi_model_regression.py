"""
S26: Multi-Model Regression System

实现多模型比较和回归测试系统，支持：
- Teaching (F0) vs ParamCompact (F1) vs SPICE (F2) 模型比较
- 模型间差异分析
- 回归测试框架
"""
from typing import Optional
from pydantic import BaseModel
from packages.contracts.types import (
    DeviceProfile,
    FrameState,
    NodeVoltages,
    OperationPhase,
    OperationType,
    DeviceState
)
from simulator.models.teaching_model import TeachingModelAdapter
from simulator.models.param_compact_model import ParamCompactAdapter
from simulator.models.adapter_protocol import ModelAdapter, TraceData
from simulator.models.spice_bridge import SPICEModelAdapter


class ModelComparison(BaseModel):
    """模型比较结果"""
    frame_id: str
    time_ns: float
    models: dict[str, FrameState]  # model_name -> FrameState
    
    # 差异分析
    v_rram_diff: dict[str, float]  # model_name -> diff from reference
    i_rram_diff: dict[str, float]
    r_rram_diff: dict[str, float]
    state_match: dict[str, bool]  # model_name -> matches reference
    
    reference_model: str


class RegressionTest(BaseModel):
    """回归测试配置"""
    test_id: str
    description: str
    operation: OperationType
    pulse_params: dict
    duration_ns: float
    reference_model: str = "teaching"
    tolerance: dict = {
        "v_rram_pct": 5.0,  # 5% tolerance
        "i_rram_pct": 10.0,  # 10% tolerance
        "r_rram_pct": 20.0,  # 20% tolerance
        "state_match": True  # state must match
    }


class RegressionResult(BaseModel):
    """回归测试结果"""
    test_id: str
    passed: bool
    comparisons: list[ModelComparison]
    failed_checks: list[str]
    summary: str


class MultiModelRunner:
    """多模型运行器"""
    
    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        
        # 初始化模型
        self.models: dict[str, ModelAdapter] = {
            "teaching": TeachingModelAdapter(profile, seed),
            "param_compact": ParamCompactAdapter(profile, seed)
        }
    
    def add_spice_model(self, name: str, trace_data: TraceData):
        """添加 SPICE 模型"""
        self.models[name] = SPICEModelAdapter(self.profile, trace_data, self.seed)
    
    def run_comparison(
        self,
        frame_id: str,
        time_ns: float,
        operation: OperationType,
        phase: OperationPhase,
        nodes: NodeVoltages,
        selected_cell: dict[str, int],
        reference_model: str = "teaching"
    ) -> ModelComparison:
        """运行模型比较"""
        if reference_model not in self.models:
            raise ValueError(f"Reference model '{reference_model}' not found")
        
        # 运行所有模型
        frames = {}
        for name, model in self.models.items():
            frames[name] = model.compute_frame(
                frame_id=f"{frame_id}_{name}",
                time_ns=time_ns,
                operation=operation,
                phase=phase,
                nodes=nodes,
                selected_cell=selected_cell,
                current_state=DeviceState.PRISTINE,
                forming_done=False
            )
        
        # 计算差异
        ref_frame = frames[reference_model]
        v_diffs = {}
        i_diffs = {}
        r_diffs = {}
        state_matches = {}
        
        for name, frame in frames.items():
            if name == reference_model:
                v_diffs[name] = 0.0
                i_diffs[name] = 0.0
                r_diffs[name] = 0.0
                state_matches[name] = True
            else:
                # 计算百分比差异
                ref_v = abs(ref_frame.cell.rram.v)
                ref_i = abs(ref_frame.cell.rram.i)
                ref_r = ref_frame.cell.rram.r
                
                test_v = abs(frame.cell.rram.v)
                test_i = abs(frame.cell.rram.i)
                test_r = frame.cell.rram.r
                
                v_diffs[name] = ((test_v - ref_v) / ref_v * 100) if ref_v > 0 else 0.0
                i_diffs[name] = ((test_i - ref_i) / ref_i * 100) if ref_i > 0 else 0.0
                r_diffs[name] = ((test_r - ref_r) / ref_r * 100) if ref_r > 0 else 0.0
                
                state_matches[name] = (frame.cell.rram.state == ref_frame.cell.rram.state)
        
        return ModelComparison(
            frame_id=frame_id,
            time_ns=time_ns,
            models=frames,
            v_rram_diff=v_diffs,
            i_rram_diff=i_diffs,
            r_rram_diff=r_diffs,
            state_match=state_matches,
            reference_model=reference_model
        )
    
    def run_regression_test(self, test: RegressionTest) -> RegressionResult:
        """运行回归测试"""
        comparisons = []
        failed_checks = []
        
        # 运行多个时间点的比较
        time_points = [0, test.duration_ns / 4, test.duration_ns / 2, 3 * test.duration_ns / 4, test.duration_ns]
        
        for i, time_ns in enumerate(time_points):
            nodes = NodeVoltages(wl=[1.8], bl=[test.pulse_params.get("amplitude_v", 2.0)], sl=[0.0])
            
            comparison = self.run_comparison(
                frame_id=f"{test.test_id}_t{i}",
                time_ns=time_ns,
                operation=test.operation,
                phase=OperationPhase.ACTIVE,
                nodes=nodes,
                selected_cell={"row": 0, "col": 0},
                reference_model=test.reference_model
            )
            
            comparisons.append(comparison)
            
            # 检查容差
            for model_name in comparison.models.keys():
                if model_name == test.reference_model:
                    continue
                
                if abs(comparison.v_rram_diff[model_name]) > test.tolerance["v_rram_pct"]:
                    failed_checks.append(f"{test.test_id}_t{i}_{model_name}: V_RRAM diff {comparison.v_rram_diff[model_name]:.2f}% > {test.tolerance['v_rram_pct']}%")
                
                if abs(comparison.i_rram_diff[model_name]) > test.tolerance["i_rram_pct"]:
                    failed_checks.append(f"{test.test_id}_t{i}_{model_name}: I_RRAM diff {comparison.i_rram_diff[model_name]:.2f}% > {test.tolerance['i_rram_pct']}%")
                
                if test.tolerance["state_match"] and not comparison.state_match[model_name]:
                    failed_checks.append(f"{test.test_id}_t{i}_{model_name}: State mismatch")
        
        passed = len(failed_checks) == 0
        summary = f"Regression test '{test.test_id}': {'PASSED' if passed else 'FAILED'} ({len(failed_checks)} failures)"
        
        return RegressionResult(
            test_id=test.test_id,
            passed=passed,
            comparisons=comparisons,
            failed_checks=failed_checks,
            summary=summary
        )


class RegressionTestSuite:
    """回归测试套件"""
    
    def __init__(self, profile: DeviceProfile, seed: int = 42):
        self.profile = profile
        self.seed = seed
        self.runner = MultiModelRunner(profile, seed)
        self.tests: list[RegressionTest] = []
        self.results: list[RegressionResult] = []
    
    def add_test(self, test: RegressionTest):
        """添加测试"""
        self.tests.append(test)
    
    def run_all(self) -> list[RegressionResult]:
        """运行所有测试"""
        self.results = []
        for test in self.tests:
            result = self.runner.run_regression_test(test)
            self.results.append(result)
        return self.results
    
    def get_summary(self) -> dict:
        """获取测试摘要"""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0.0,
            "results": [r.dict() for r in self.results]
        }
