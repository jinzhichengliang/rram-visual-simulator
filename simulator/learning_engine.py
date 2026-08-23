"""
S29: Learning Engine — Prediction-Operation-Explanation-Self-check

实现主动学习系统：
1. 预测：在执行操作前，让用户预测结果
2. 操作：执行实际操作
3. 解释：展示为什么结果是那样
4. 自检：比较预测与实际，归因错误
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel
from packages.contracts.types import (
    DeviceProfile,
    FrameState,
    OperationType,
    DeviceState
)


class PredictionCategory(str, Enum):
    """预测类别"""
    SET = "SET"  # 预测会发生 SET
    RESET = "RESET"  # 预测会发生 RESET
    READ_NO_CHANGE = "READ_NO_CHANGE"  # 预测读取不改变状态
    NO_EFFECT = "NO_EFFECT"  # 预测没有效果


class ErrorLayer(str, Enum):
    """错误归因层"""
    POLARITY = "polarity"  # 极性判断错误
    THRESHOLD = "threshold"  # 阈值判断错误
    CURRENT_PATH = "current_path"  # 电流路径理解错误
    TRANSISTOR = "transistor"  # 晶体管状态理解错误
    SENSE = "sense"  # 感测判断错误


class Prediction(BaseModel):
    """用户预测"""
    operation: OperationType
    predicted_category: PredictionCategory
    reasoning: str  # 用户的推理过程
    confidence: float = 0.5  # 置信度 0-1


class PredictionResult(BaseModel):
    """预测结果"""
    prediction: Prediction
    actual_outcome: str  # 实际结果描述
    correct: bool
    error_layer: Optional[ErrorLayer] = None
    explanation: str  # 为什么对/错的解释
    learning_points: list[str]  # 学习要点


class LearningScenario(BaseModel):
    """学习场景"""
    scenario_id: str
    title: str
    description: str
    initial_state: DeviceState
    target_operation: OperationType
    expected_outcome: str
    hints: list[str] = []
    difficulty: str = "beginner"  # beginner, intermediate, advanced


class LearningEngine:
    """学习引擎"""
    
    def __init__(self, profile: DeviceProfile):
        self.profile = profile
        self.scenarios: list[LearningScenario] = []
        self.results: list[PredictionResult] = []
        self.current_scenario: Optional[LearningScenario] = None
    
    def add_scenario(self, scenario: LearningScenario):
        """添加学习场景"""
        self.scenarios.append(scenario)
    
    def load_default_scenarios(self):
        """加载默认学习场景"""
        scenarios = [
            LearningScenario(
                scenario_id="learn_set_001",
                title="SET 操作预测",
                description="器件处于 HRS 状态，施加正向电压，预测会发生什么？",
                initial_state=DeviceState.HRS,
                target_operation=OperationType.SET,
                expected_outcome="HRS → LRS（SET 发生）",
                hints=[
                    "检查电压极性是否符合 SET 条件",
                    "V_RRAM > 0 时，对于双极性器件会发生 SET",
                    "SET 需要电压超过阈值"
                ],
                difficulty="beginner"
            ),
            LearningScenario(
                scenario_id="learn_reset_001",
                title="RESET 操作预测",
                description="器件处于 LRS 状态，施加负向电压，预测会发生什么？",
                initial_state=DeviceState.LRS,
                target_operation=OperationType.RESET,
                expected_outcome="LRS → HRS（RESET 发生）",
                hints=[
                    "检查电压极性是否符合 RESET 条件",
                    "V_RRAM < 0 时，对于双极性器件会发生 RESET",
                    "RESET 需要电压超过阈值"
                ],
                difficulty="beginner"
            ),
            LearningScenario(
                scenario_id="learn_read_001",
                title="READ 操作预测",
                description="器件处于 LRS 状态，施加小电压读取，预测状态会改变吗？",
                initial_state=DeviceState.LRS,
                target_operation=OperationType.READ,
                expected_outcome="状态保持 LRS（非破坏性读取）",
                hints=[
                    "读取电压远低于写入阈值",
                    "READ 操作不应该改变器件状态",
                    "这是非破坏性读取的特性"
                ],
                difficulty="beginner"
            ),
            LearningScenario(
                scenario_id="learn_wrong_polarity_001",
                title="错误极性预测",
                description="器件处于 HRS 状态，施加反向电压（应该 SET 但极性反了），预测会发生什么？",
                initial_state=DeviceState.HRS,
                target_operation=OperationType.SET,
                expected_outcome="状态保持 HRS（极性错误，SET 不发生）",
                hints=[
                    "检查电压极性是否正确",
                    "SET 需要正向电压，但这里施加了反向电压",
                    "极性错误时，即使电压足够高也不会发生状态转换"
                ],
                difficulty="intermediate"
            ),
            LearningScenario(
                scenario_id="learn_below_threshold_001",
                title="阈值以下预测",
                description="器件处于 HRS 状态，施加正向电压但低于阈值，预测会发生什么？",
                initial_state=DeviceState.HRS,
                target_operation=OperationType.SET,
                expected_outcome="状态保持 HRS（电压不足）",
                hints=[
                    "虽然极性正确，但电压是否足够？",
                    "SET 需要电压超过阈值 V_set",
                    "电压不足时，即使极性正确也不会发生状态转换"
                ],
                difficulty="intermediate"
            )
        ]
        
        for scenario in scenarios:
            self.scenarios.append(scenario)
    
    def get_next_scenario(self, difficulty: Optional[str] = None) -> Optional[LearningScenario]:
        """获取下一个学习场景"""
        available = self.scenarios
        
        if difficulty:
            available = [s for s in available if s.difficulty == difficulty]
        
        # 过滤已完成的场景
        completed_ids = {r.prediction.operation for r in self.results if r.correct}
        available = [s for s in available if s.scenario_id not in 
                     [f"{s.target_operation.value}_{i}" for i in range(100)]]
        
        if not available:
            return None
        
        self.current_scenario = available[0]
        return self.current_scenario
    
    def evaluate_prediction(
        self,
        prediction: Prediction,
        actual_frame: FrameState,
        prev_frame: Optional[FrameState] = None
    ) -> PredictionResult:
        """评估预测"""
        # 确定实际结果
        actual_state = actual_frame.cell.rram.state
        prev_state = prev_frame.cell.rram.state if prev_frame else DeviceState.PRISTINE
        
        if actual_state != prev_state:
            if prev_state == DeviceState.HRS and actual_state == DeviceState.LRS:
                actual_outcome = "HRS → LRS（SET 发生）"
                actual_category = PredictionCategory.SET
            elif prev_state == DeviceState.LRS and actual_state == DeviceState.HRS:
                actual_outcome = "LRS → HRS（RESET 发生）"
                actual_category = PredictionCategory.RESET
            else:
                actual_outcome = f"{prev_state.value} → {actual_state.value}"
                actual_category = PredictionCategory.NO_EFFECT
        else:
            actual_outcome = f"状态保持 {actual_state.value}"
            actual_category = PredictionCategory.READ_NO_CHANGE
        
        # 判断预测是否正确
        correct = prediction.predicted_category == actual_category
        
        # 错误归因
        error_layer = None
        explanation = ""
        learning_points = []
        
        if not correct:
            error_layer = self._attribute_error(prediction, actual_category, actual_frame, prev_frame)
            explanation = self._generate_error_explanation(prediction, actual_category, error_layer)
            learning_points = self._generate_learning_points(error_layer, actual_frame)
        else:
            explanation = f"预测正确！{actual_outcome}"
            learning_points = [
                f"你正确理解了 {prediction.operation.value} 操作的效果",
                "继续保持对电压极性和阈值的关注"
            ]
        
        result = PredictionResult(
            prediction=prediction,
            actual_outcome=actual_outcome,
            correct=correct,
            error_layer=error_layer,
            explanation=explanation,
            learning_points=learning_points
        )
        
        self.results.append(result)
        return result
    
    def _attribute_error(
        self,
        prediction: Prediction,
        actual: PredictionCategory,
        actual_frame: FrameState,
        prev_frame: Optional[FrameState]
    ) -> ErrorLayer:
        """错误归因"""
        # 晶体管错误（优先检查）
        if not actual_frame.cell.transistor.on:
            return ErrorLayer.TRANSISTOR
        
        # 极性错误
        if prediction.predicted_category in [PredictionCategory.SET, PredictionCategory.RESET]:
            v_rram = actual_frame.cell.rram.v
            
            if prediction.predicted_category == PredictionCategory.SET and v_rram < 0:
                return ErrorLayer.POLARITY
            
            if prediction.predicted_category == PredictionCategory.RESET and v_rram > 0:
                return ErrorLayer.POLARITY
        
        # 阈值错误
        if prediction.predicted_category in [PredictionCategory.SET, PredictionCategory.RESET]:
            if actual == PredictionCategory.READ_NO_CHANGE:
                return ErrorLayer.THRESHOLD
        
        # 电流路径错误
        # 默认
        return ErrorLayer.THRESHOLD
    
    def _generate_error_explanation(
        self,
        prediction: Prediction,
        actual: PredictionCategory,
        error_layer: ErrorLayer
    ) -> str:
        """生成错误解释"""
        if error_layer == ErrorLayer.POLARITY:
            return (
                f"极性判断错误。你预测会发生 {prediction.predicted_category.value}，"
                f"但实际电压极性不满足条件。"
                f"对于双极性 RRAM，SET 需要正向电压（V_RRAM > 0），"
                f"RESET 需要负向电压（V_RRAM < 0）。"
            )
        
        elif error_layer == ErrorLayer.THRESHOLD:
            return (
                f"阈值判断错误。你预测会发生 {prediction.predicted_category.value}，"
                f"但实际电压未达到阈值。"
                f"即使极性正确，电压也必须超过阈值才能引起状态转换。"
            )
        
        elif error_layer == ErrorLayer.TRANSISTOR:
            return (
                f"晶体管状态理解错误。你预测会发生状态转换，"
                f"但实际 NMOS 晶体管未导通，电流无法流过器件。"
                f"检查 WL 电压是否足够高（> Vth ≈ 0.7V）。"
            )
        
        elif error_layer == ErrorLayer.CURRENT_PATH:
            return (
                f"电流路径理解错误。你预测会发生状态转换，"
                f"但实际电流路径不完整。"
                f"检查 BL、RRAM、NMOS、SL 的连接是否正确。"
            )
        
        else:
            return (
                f"预测错误。你预测 {prediction.predicted_category.value}，"
                f"但实际结果是 {actual.value}。"
                f"请复习电压极性、阈值和电流路径的概念。"
            )
    
    def _generate_learning_points(
        self,
        error_layer: ErrorLayer,
        frame: FrameState
    ) -> list[str]:
        """生成学习要点"""
        points = []
        
        if error_layer == ErrorLayer.POLARITY:
            points.extend([
                "双极性 RRAM：SET 需要 V_RRAM > 0，RESET 需要 V_RRAM < 0",
                "极性由 BL 和 SL 的电压差决定",
                "在操作前，先确认电压极性是否正确"
            ])
        
        elif error_layer == ErrorLayer.THRESHOLD:
            points.extend([
                f"SET 阈值电压：{self.profile.ranges.vSet}V",
                f"RESET 阈值电压：{self.profile.ranges.vReset}V",
                "电压必须超过阈值才能引起状态转换",
                "低于阈值时，即使极性正确也不会发生转换"
            ])
        
        elif error_layer == ErrorLayer.TRANSISTOR:
            points.extend([
                "NMOS 晶体管需要 Vgs > Vth（约 0.7V）才能导通",
                "WL 电压控制晶体管开关",
                "晶体管截止时，电流无法流过 RRAM"
            ])
        
        elif error_layer == ErrorLayer.CURRENT_PATH:
            points.extend([
                "1T1R 结构：BL → RRAM → NMOS → SL",
                "电流路径必须完整才能进行操作",
                "检查每个节点的连接是否正确"
            ])
        
        return points
    
    def get_progress_summary(self) -> dict:
        """获取学习进度摘要"""
        total = len(self.results)
        correct = sum(1 for r in self.results if r.correct)
        
        error_counts = {}
        for r in self.results:
            if not r.correct and r.error_layer:
                error_counts[r.error_layer.value] = error_counts.get(r.error_layer.value, 0) + 1
        
        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": (correct / total * 100) if total > 0 else 0.0,
            "error_distribution": error_counts,
            "scenarios_available": len(self.scenarios),
            "scenarios_completed": len(set(r.prediction.operation for r in self.results))
        }
    
    def get_weak_areas(self) -> list[str]:
        """获取薄弱领域"""
        error_counts = {}
        for r in self.results:
            if not r.correct and r.error_layer:
                error_counts[r.error_layer.value] = error_counts.get(r.error_layer.value, 0) + 1
        
        if not error_counts:
            return []
        
        # 返回错误最多的领域
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        return [f"{layer}: {count} 次错误" for layer, count in sorted_errors]
