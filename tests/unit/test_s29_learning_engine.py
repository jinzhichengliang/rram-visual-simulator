"""
S29: Learning Engine Tests
"""
import pytest
from simulator.learning_engine import (
    LearningEngine,
    LearningScenario,
    Prediction,
    PredictionCategory,
    ErrorLayer
)
from packages.contracts.types import (
    DeviceProfile,
    DeviceRanges,
    DeviceTolerances,
    LogicMap,
    Polarity,
    StackOrientation,
    FrameState,
    CellState,
    TransistorState,
    RRAMState,
    NodeVoltages,
    ModelMetadata,
    OperationType,
    OperationPhase,
    DeviceState
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
def engine(profile):
    """学习引擎"""
    return LearningEngine(profile)


def create_frame(
    state: DeviceState,
    v_rram: float,
    i_rram: float,
    transistor_on: bool = True
) -> FrameState:
    """创建测试帧"""
    return FrameState(
        frameId="test_frame",
        timeNs=0.0,
        operation=OperationType.SET,
        phase=OperationPhase.ACTIVE,
        selectedCell={"row": 0, "col": 0},
        nodes=NodeVoltages(wl=[1.8], bl=[v_rram], sl=[0.0]),
        cell=CellState(
            transistor=TransistorState(
                vg=1.8,
                vs=0.0,
                vd=v_rram,
                on=transistor_on,
                complianceLimitUa=50.0
            ),
            rram=RRAMState(
                v=v_rram,
                i=i_rram,
                r=30000 if state == DeviceState.LRS else 1000000,
                state=state,
                formingDone=True
            )
        ),
        model=ModelMetadata(
            fidelity="F0",
            profileId="bipolar_teaching_v1",
            profileVersion="1.0.0",
            seed=42
        ),
        checks=[]
    )


class TestLearningScenario:
    """学习场景测试"""
    
    def test_scenario_creation(self):
        """测试场景创建"""
        scenario = LearningScenario(
            scenario_id="test_001",
            title="测试场景",
            description="这是一个测试场景",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS"
        )
        
        assert scenario.scenario_id == "test_001"
        assert scenario.initial_state == DeviceState.HRS
        assert scenario.target_operation == OperationType.SET
    
    def test_scenario_with_hints(self):
        """测试带提示的场景"""
        scenario = LearningScenario(
            scenario_id="test_002",
            title="带提示的场景",
            description="测试",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS",
            hints=["提示1", "提示2"],
            difficulty="intermediate"
        )
        
        assert len(scenario.hints) == 2
        assert scenario.difficulty == "intermediate"


class TestPrediction:
    """预测测试"""
    
    def test_prediction_creation(self):
        """测试预测创建"""
        prediction = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="电压极性正确，应该发生 SET",
            confidence=0.8
        )
        
        assert prediction.operation == OperationType.SET
        assert prediction.predicted_category == PredictionCategory.SET
        assert prediction.confidence == 0.8


class TestLearningEngine:
    """学习引擎测试"""
    
    def test_engine_creation(self, engine):
        """测试引擎创建"""
        assert engine.profile.id == "bipolar_teaching_v1"
        assert len(engine.scenarios) == 0
    
    def test_add_scenario(self, engine):
        """测试添加场景"""
        scenario = LearningScenario(
            scenario_id="test_001",
            title="测试",
            description="测试",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS"
        )
        
        engine.add_scenario(scenario)
        assert len(engine.scenarios) == 1
    
    def test_load_default_scenarios(self, engine):
        """测试加载默认场景"""
        engine.load_default_scenarios()
        assert len(engine.scenarios) >= 5
    
    def test_get_next_scenario(self, engine):
        """测试获取下一个场景"""
        engine.load_default_scenarios()
        scenario = engine.get_next_scenario()
        
        assert scenario is not None
        assert scenario.scenario_id is not None
    
    def test_get_next_scenario_by_difficulty(self, engine):
        """测试按难度获取场景"""
        engine.load_default_scenarios()
        scenario = engine.get_next_scenario(difficulty="beginner")
        
        assert scenario is not None
        assert scenario.difficulty == "beginner"
    
    def test_evaluate_correct_prediction(self, engine):
        """测试正确预测评估"""
        # 创建预测
        prediction = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="极性正确",
            confidence=0.9
        )
        
        # 创建实际帧（HRS → LRS）
        prev_frame = create_frame(DeviceState.HRS, 0.0, 0.0)
        actual_frame = create_frame(DeviceState.LRS, 2.0, 50.0)
        
        result = engine.evaluate_prediction(prediction, actual_frame, prev_frame)
        
        assert result.correct is True
        assert "预测正确" in result.explanation
        assert len(result.learning_points) > 0
    
    def test_evaluate_incorrect_prediction_polarity(self, engine):
        """测试极性错误预测评估"""
        # 预测会发生 SET
        prediction = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="应该发生 SET",
            confidence=0.7
        )
        
        # 实际：极性错误，状态不变
        prev_frame = create_frame(DeviceState.HRS, 0.0, 0.0)
        actual_frame = create_frame(DeviceState.HRS, -2.0, 0.0)  # 负电压
        
        result = engine.evaluate_prediction(prediction, actual_frame, prev_frame)
        
        assert result.correct is False
        assert result.error_layer == ErrorLayer.POLARITY
        assert "极性" in result.explanation
    
    def test_evaluate_incorrect_prediction_threshold(self, engine):
        """测试阈值错误预测评估"""
        # 预测会发生 SET
        prediction = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="极性正确",
            confidence=0.6
        )
        
        # 实际：电压不足，状态不变
        prev_frame = create_frame(DeviceState.HRS, 0.0, 0.0)
        actual_frame = create_frame(DeviceState.HRS, 0.5, 0.0)  # 电压低于阈值
        
        result = engine.evaluate_prediction(prediction, actual_frame, prev_frame)
        
        assert result.correct is False
        assert result.error_layer == ErrorLayer.THRESHOLD
        assert "阈值" in result.explanation
    
    def test_evaluate_incorrect_prediction_transistor(self, engine):
        """测试晶体管错误预测评估"""
        # 预测会发生 SET
        prediction = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="电压足够",
            confidence=0.8
        )
        
        # 实际：晶体管截止
        prev_frame = create_frame(DeviceState.HRS, 0.0, 0.0)
        actual_frame = create_frame(DeviceState.HRS, 2.0, 0.0, transistor_on=False)
        
        result = engine.evaluate_prediction(prediction, actual_frame, prev_frame)
        
        assert result.correct is False
        assert result.error_layer == ErrorLayer.TRANSISTOR
        assert "晶体管" in result.explanation
    
    def test_get_progress_summary(self, engine):
        """测试进度摘要"""
        # 添加一些预测结果
        prediction1 = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="正确",
            confidence=0.9
        )
        frame1_prev = create_frame(DeviceState.HRS, 0.0, 0.0)
        frame1 = create_frame(DeviceState.LRS, 2.0, 50.0)
        engine.evaluate_prediction(prediction1, frame1, frame1_prev)
        
        prediction2 = Prediction(
            operation=OperationType.SET,
            predicted_category=PredictionCategory.SET,
            reasoning="错误",
            confidence=0.5
        )
        frame2_prev = create_frame(DeviceState.HRS, 0.0, 0.0)
        frame2 = create_frame(DeviceState.HRS, -2.0, 0.0)  # 极性错误
        engine.evaluate_prediction(prediction2, frame2, frame2_prev)
        
        summary = engine.get_progress_summary()
        
        assert summary["total_predictions"] == 2
        assert summary["correct_predictions"] == 1
        assert summary["accuracy"] == 50.0
        assert "polarity" in summary["error_distribution"]
    
    def test_get_weak_areas(self, engine):
        """测试获取薄弱领域"""
        # 添加多个极性错误
        for _ in range(3):
            prediction = Prediction(
                operation=OperationType.SET,
                predicted_category=PredictionCategory.SET,
                reasoning="错误",
                confidence=0.5
            )
            prev_frame = create_frame(DeviceState.HRS, 0.0, 0.0)
            actual_frame = create_frame(DeviceState.HRS, -2.0, 0.0)
            engine.evaluate_prediction(prediction, actual_frame, prev_frame)
        
        weak_areas = engine.get_weak_areas()
        
        assert len(weak_areas) > 0
        assert "polarity" in weak_areas[0]


class TestPredictionCategory:
    """预测类别测试"""
    
    def test_category_enum(self):
        """测试类别枚举"""
        assert PredictionCategory.SET == "SET"
        assert PredictionCategory.RESET == "RESET"
        assert PredictionCategory.READ_NO_CHANGE == "READ_NO_CHANGE"
        assert PredictionCategory.NO_EFFECT == "NO_EFFECT"


class TestErrorLayer:
    """错误层测试"""
    
    def test_error_layer_enum(self):
        """测试错误层枚举"""
        assert ErrorLayer.POLARITY == "polarity"
        assert ErrorLayer.THRESHOLD == "threshold"
        assert ErrorLayer.CURRENT_PATH == "current_path"
        assert ErrorLayer.TRANSISTOR == "transistor"
        assert ErrorLayer.SENSE == "sense"
