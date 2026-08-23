"""
S27: Calibration Workspace

实现参数校准工作区，支持：
- 参考数据导入
- 误差指标计算
- 参数优化
- 校准报告生成
"""
from typing import Optional
from pydantic import BaseModel
from packages.contracts.types import DeviceProfile


class CalibrationTarget(BaseModel):
    """校准目标"""
    parameter_name: str  # 参数名称
    target_value: float  # 目标值
    tolerance_pct: float  # 容差百分比
    weight: float = 1.0  # 权重


class CalibrationDataPoint(BaseModel):
    """校准数据点"""
    input_value: float  # 输入值（如电压）
    expected_output: float  # 期望输出（如电流）
    actual_output: Optional[float] = None  # 实际输出
    error: Optional[float] = None  # 误差
    error_pct: Optional[float] = None  # 误差百分比


class CalibrationResult(BaseModel):
    """校准结果"""
    parameter_name: str
    initial_value: float
    calibrated_value: float
    error_before: float
    error_after: float
    improvement_pct: float
    data_points: list[CalibrationDataPoint]


class CalibrationReport(BaseModel):
    """校准报告"""
    profile_id: str
    calibration_id: str
    timestamp: str
    targets: list[CalibrationTarget]
    results: list[CalibrationResult]
    overall_error_before: float
    overall_error_after: float
    overall_improvement_pct: float
    passed: bool


class CalibrationWorkspace:
    """校准工作区"""
    
    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        self.targets: list[CalibrationTarget] = []
        self.data: dict[str, list[CalibrationDataPoint]] = {}
        self.results: list[CalibrationResult] = []
    
    def add_target(
        self,
        parameter_name: str,
        target_value: float,
        tolerance_pct: float,
        weight: float = 1.0
    ):
        """添加校准目标"""
        target = CalibrationTarget(
            parameter_name=parameter_name,
            target_value=target_value,
            tolerance_pct=tolerance_pct,
            weight=weight
        )
        self.targets.append(target)
    
    def add_data_point(
        self,
        parameter_name: str,
        input_value: float,
        expected_output: float
    ):
        """添加校准数据点"""
        if parameter_name not in self.data:
            self.data[parameter_name] = []
        
        data_point = CalibrationDataPoint(
            input_value=input_value,
            expected_output=expected_output
        )
        self.data[parameter_name].append(data_point)
    
    def calculate_error(self, expected: float, actual: float) -> tuple[float, float]:
        """计算误差"""
        error = abs(actual - expected)
        error_pct = (error / expected * 100) if expected != 0 else 0.0
        return error, error_pct
    
    def calibrate_parameter(
        self,
        parameter_name: str,
        initial_value: float,
        model_function: callable
    ) -> CalibrationResult:
        """校准单个参数"""
        if parameter_name not in self.data:
            raise ValueError(f"No data for parameter '{parameter_name}'")
        
        data_points = self.data[parameter_name]
        
        # 计算初始误差
        errors_before = []
        for dp in data_points:
            actual = model_function(dp.input_value, initial_value)
            dp.actual_output = actual
            error, error_pct = self.calculate_error(dp.expected_output, actual)
            dp.error = error
            dp.error_pct = error_pct
            errors_before.append(error)
        
        avg_error_before = sum(errors_before) / len(errors_before)
        
        # 简单优化：网格搜索（实际项目中应使用更高级的优化算法）
        best_value = initial_value
        best_error = avg_error_before
        
        # 搜索范围：±50%
        search_range = [initial_value * (1 + i * 0.1) for i in range(-5, 6)]
        
        for test_value in search_range:
            errors = []
            for dp in data_points:
                actual = model_function(dp.input_value, test_value)
                error, _ = self.calculate_error(dp.expected_output, actual)
                errors.append(error)
            
            avg_error = sum(errors) / len(errors)
            
            if avg_error < best_error:
                best_error = avg_error
                best_value = test_value
        
        # 使用最优值重新计算
        for dp in data_points:
            actual = model_function(dp.input_value, best_value)
            dp.actual_output = actual
            error, error_pct = self.calculate_error(dp.expected_output, actual)
            dp.error = error
            dp.error_pct = error_pct
        
        avg_error_after = sum(dp.error for dp in data_points) / len(data_points)
        improvement_pct = ((avg_error_before - avg_error_after) / avg_error_before * 100) if avg_error_before > 0 else 0.0
        
        result = CalibrationResult(
            parameter_name=parameter_name,
            initial_value=initial_value,
            calibrated_value=best_value,
            error_before=avg_error_before,
            error_after=avg_error_after,
            improvement_pct=improvement_pct,
            data_points=data_points
        )
        
        self.results.append(result)
        return result
    
    def calibrate_all(self, model_functions: dict[str, callable]) -> CalibrationReport:
        """校准所有参数"""
        from datetime import datetime
        
        results = []
        for target in self.targets:
            if target.parameter_name in model_functions:
                # 获取当前参数值
                current_value = getattr(self.profile, target.parameter_name, 1.0)
                
                result = self.calibrate_parameter(
                    target.parameter_name,
                    current_value,
                    model_functions[target.parameter_name]
                )
                results.append(result)
        
        # 计算总体误差
        overall_error_before = sum(r.error_before for r in results) / len(results) if results else 0.0
        overall_error_after = sum(r.error_after for r in results) / len(results) if results else 0.0
        overall_improvement = ((overall_error_before - overall_error_after) / overall_error_before * 100) if overall_error_before > 0 else 0.0
        
        # 检查是否通过
        passed = all(
            r.error_after <= r.data_points[0].expected_output * (t.tolerance_pct / 100)
            for r, t in zip(results, self.targets)
            if t.parameter_name == r.parameter_name
        )
        
        report = CalibrationReport(
            profile_id=self.profile.id,
            calibration_id=f"cal_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now().isoformat(),
            targets=self.targets,
            results=results,
            overall_error_before=overall_error_before,
            overall_error_after=overall_error_after,
            overall_improvement_pct=overall_improvement,
            passed=passed
        )
        
        return report
    
    def get_summary(self) -> dict:
        """获取校准摘要"""
        return {
            "profile_id": self.profile.id,
            "target_count": len(self.targets),
            "data_point_count": sum(len(pts) for pts in self.data.values()),
            "result_count": len(self.results),
            "targets": [t.dict() for t in self.targets],
            "results": [r.dict() for r in self.results]
        }
