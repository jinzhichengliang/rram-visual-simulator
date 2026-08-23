"""
S30: Learning Manager Tests
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from simulator.learning_manager import (
    LearningManager,
    UserNote,
    LearningProgress,
    SavedScenario
)
from simulator.learning_engine import (
    LearningScenario,
    Prediction,
    PredictionResult,
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
    OperationType,
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
def temp_dir():
    """临时目录"""
    temp = tempfile.mkdtemp()
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def manager(profile, temp_dir, monkeypatch):
    """学习管理器"""
    # 使用临时目录
    monkeypatch.setattr(Path, "home", lambda: Path(temp_dir))
    return LearningManager(profile, user_id="test_user")


def create_prediction_result(correct: bool, error_layer: ErrorLayer = None) -> PredictionResult:
    """创建预测结果"""
    prediction = Prediction(
        operation=OperationType.SET,
        predicted_category=PredictionCategory.SET,
        reasoning="测试",
        confidence=0.8
    )
    
    return PredictionResult(
        prediction=prediction,
        actual_outcome="HRS → LRS" if correct else "状态保持 HRS",
        correct=correct,
        error_layer=error_layer,
        explanation="测试解释",
        learning_points=["要点1", "要点2"]
    )


class TestUserNote:
    """用户笔记测试"""
    
    def test_note_creation(self):
        """测试笔记创建"""
        note = UserNote(
            note_id="note_001",
            scenario_id="scenario_001",
            timestamp="2026-08-23T12:00:00",
            content="这是一个测试笔记",
            tags=["重要", "SET"]
        )
        
        assert note.note_id == "note_001"
        assert note.content == "这是一个测试笔记"
        assert len(note.tags) == 2


class TestLearningProgress:
    """学习进度测试"""
    
    def test_progress_creation(self):
        """测试进度创建"""
        progress = LearningProgress(user_id="test_user")
        
        assert progress.user_id == "test_user"
        assert progress.predictions_total == 0
        assert progress.predictions_correct == 0


class TestSavedScenario:
    """保存场景测试"""
    
    def test_saved_scenario_creation(self):
        """测试保存场景创建"""
        saved = SavedScenario(
            scenario_id="custom_001",
            title="自定义场景",
            description="测试",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS",
            created_by="test_user",
            created_at="2026-08-23T12:00:00",
            custom=True
        )
        
        assert saved.scenario_id == "custom_001"
        assert saved.custom is True


class TestLearningManager:
    """学习管理器测试"""
    
    def test_manager_creation(self, manager):
        """测试管理器创建"""
        assert manager.user_id == "test_user"
        assert manager.progress.predictions_total == 0
    
    def test_update_progress_correct(self, manager):
        """测试更新正确预测进度"""
        result = create_prediction_result(correct=True)
        manager.update_progress(result, "scenario_001")
        
        assert manager.progress.predictions_total == 1
        assert manager.progress.predictions_correct == 1
        assert "scenario_001" in manager.progress.scenarios_completed
    
    def test_update_progress_incorrect(self, manager):
        """测试更新错误预测进度"""
        result = create_prediction_result(correct=False, error_layer=ErrorLayer.POLARITY)
        manager.update_progress(result, "scenario_001")
        
        assert manager.progress.predictions_total == 1
        assert manager.progress.predictions_correct == 0
        assert "polarity" in manager.progress.weak_areas
    
    def test_add_note(self, manager):
        """测试添加笔记"""
        note = manager.add_note(
            scenario_id="scenario_001",
            content="这是一个测试笔记",
            tags=["重要"]
        )
        
        assert note.note_id == "note_001"
        assert len(manager.progress.notes) == 1
    
    def test_get_notes_for_scenario(self, manager):
        """测试获取场景相关笔记"""
        manager.add_note("scenario_001", "笔记1")
        manager.add_note("scenario_001", "笔记2")
        manager.add_note("scenario_002", "笔记3")
        
        notes = manager.get_notes_for_scenario("scenario_001")
        assert len(notes) == 2
    
    def test_save_scenario(self, manager):
        """测试保存场景"""
        scenario = LearningScenario(
            scenario_id="custom_001",
            title="自定义场景",
            description="测试",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS"
        )
        
        saved = manager.save_scenario(scenario)
        
        assert saved.scenario_id == "custom_001"
        assert len(manager.saved_scenarios) == 1
    
    def test_load_saved_scenarios(self, manager):
        """测试加载保存的场景"""
        scenario = LearningScenario(
            scenario_id="custom_001",
            title="自定义场景",
            description="测试",
            initial_state=DeviceState.HRS,
            target_operation=OperationType.SET,
            expected_outcome="HRS → LRS"
        )
        
        manager.save_scenario(scenario)
        loaded = manager.load_saved_scenarios()
        
        assert len(loaded) == 1
        assert loaded[0].scenario_id == "custom_001"
    
    def test_save_and_load_from_file(self, manager):
        """测试文件保存和加载"""
        # 添加一些数据
        result = create_prediction_result(correct=True)
        manager.update_progress(result, "scenario_001")
        manager.add_note("scenario_001", "测试笔记")
        
        # 保存到文件
        manager.save_to_file()
        
        # 创建新管理器并加载
        new_manager = LearningManager(manager.profile, user_id="test_user")
        new_manager.load_from_file()
        
        assert new_manager.progress.predictions_total == 1
        assert len(new_manager.progress.notes) == 1
    
    def test_get_progress_summary(self, manager):
        """测试获取进度摘要"""
        result1 = create_prediction_result(correct=True)
        manager.update_progress(result1, "scenario_001")
        
        result2 = create_prediction_result(correct=False)
        manager.update_progress(result2, "scenario_002")
        
        summary = manager.get_progress_summary()
        
        assert summary["user_id"] == "test_user"
        assert summary["predictions_total"] == 2
        assert summary["predictions_correct"] == 1
        assert summary["accuracy"] == 50.0
    
    def test_get_achievement_badges_none(self, manager):
        """测试无成就徽章"""
        badges = manager.get_achievement_badges()
        assert len(badges) == 0
    
    def test_get_achievement_badges_accuracy(self, manager):
        """测试准确率徽章"""
        # 添加 10 个正确预测
        for _ in range(10):
            result = create_prediction_result(correct=True)
            manager.update_progress(result, f"scenario_{_}")
        
        badges = manager.get_achievement_badges()
        assert any("精准预测者" in badge for badge in badges)
    
    def test_get_achievement_badges_completion(self, manager):
        """测试完成度徽章"""
        # 完成 5 个场景
        for i in range(5):
            result = create_prediction_result(correct=True)
            manager.update_progress(result, f"scenario_{i}")
        
        badges = manager.get_achievement_badges()
        assert any("场景探索者" in badge for badge in badges)
    
    def test_get_achievement_badges_notes(self, manager):
        """测试笔记徽章"""
        # 添加 3 个笔记
        for i in range(3):
            manager.add_note(f"scenario_{i}", f"笔记{i}")
        
        badges = manager.get_achievement_badges()
        assert any("勤奋记录者" in badge for badge in badges)
