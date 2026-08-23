"""
S30: Learning Progress, Notes & Saveable Scenarios

实现学习进度追踪、笔记系统和可保存场景：
1. 学习进度追踪
2. 用户笔记
3. 场景保存与加载
"""
import json
from datetime import datetime
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
from packages.contracts.types import DeviceProfile, OperationType, DeviceState
from simulator.learning_engine import LearningScenario, PredictionResult


class UserNote(BaseModel):
    """用户笔记"""
    note_id: str
    scenario_id: str
    timestamp: str
    content: str
    tags: list[str] = []


class LearningProgress(BaseModel):
    """学习进度"""
    user_id: str
    scenarios_completed: list[str] = []
    predictions_total: int = 0
    predictions_correct: int = 0
    accuracy_history: list[dict] = []  # [{timestamp, accuracy}]
    weak_areas: list[str] = []
    last_active: str = ""
    notes: list[UserNote] = []


class SavedScenario(BaseModel):
    """保存的场景"""
    scenario_id: str
    title: str
    description: str
    initial_state: DeviceState
    target_operation: OperationType
    expected_outcome: str
    hints: list[str] = []
    difficulty: str = "beginner"
    created_by: str
    created_at: str
    custom: bool = True  # 是否为用户自定义


class LearningManager:
    """学习管理器"""
    
    def __init__(self, profile: DeviceProfile, user_id: str = "default_user"):
        self.profile = profile
        self.user_id = user_id
        self.progress = LearningProgress(user_id=user_id)
        self.saved_scenarios: list[SavedScenario] = []
        self.data_dir = Path.home() / ".rram_simulator" / "learning"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def update_progress(self, prediction_result: PredictionResult, scenario_id: str):
        """更新学习进度"""
        self.progress.predictions_total += 1
        
        if prediction_result.correct:
            self.progress.predictions_correct += 1
        
        # 添加场景到已完成列表
        if scenario_id not in self.progress.scenarios_completed:
            self.progress.scenarios_completed.append(scenario_id)
        
        # 更新准确率历史
        accuracy = (
            self.progress.predictions_correct / self.progress.predictions_total * 100
            if self.progress.predictions_total > 0 else 0.0
        )
        self.progress.accuracy_history.append({
            "timestamp": datetime.now().isoformat(),
            "accuracy": accuracy
        })
        
        # 更新薄弱领域
        if not prediction_result.correct and prediction_result.error_layer:
            error_layer = prediction_result.error_layer.value
            if error_layer not in self.progress.weak_areas:
                self.progress.weak_areas.append(error_layer)
        
        self.progress.last_active = datetime.now().isoformat()
    
    def add_note(self, scenario_id: str, content: str, tags: list[str] = None):
        """添加笔记"""
        note = UserNote(
            note_id=f"note_{len(self.progress.notes) + 1:03d}",
            scenario_id=scenario_id,
            timestamp=datetime.now().isoformat(),
            content=content,
            tags=tags or []
        )
        self.progress.notes.append(note)
        return note
    
    def get_notes_for_scenario(self, scenario_id: str) -> list[UserNote]:
        """获取场景相关笔记"""
        return [n for n in self.progress.notes if n.scenario_id == scenario_id]
    
    def save_scenario(self, scenario: LearningScenario):
        """保存场景"""
        saved = SavedScenario(
            scenario_id=scenario.scenario_id,
            title=scenario.title,
            description=scenario.description,
            initial_state=scenario.initial_state,
            target_operation=scenario.target_operation,
            expected_outcome=scenario.expected_outcome,
            hints=scenario.hints,
            difficulty=scenario.difficulty,
            created_by=self.user_id,
            created_at=datetime.now().isoformat(),
            custom=True
        )
        self.saved_scenarios.append(saved)
        return saved
    
    def load_saved_scenarios(self) -> list[LearningScenario]:
        """加载保存的场景"""
        scenarios = []
        for saved in self.saved_scenarios:
            scenario = LearningScenario(
                scenario_id=saved.scenario_id,
                title=saved.title,
                description=saved.description,
                initial_state=saved.initial_state,
                target_operation=saved.target_operation,
                expected_outcome=saved.expected_outcome,
                hints=saved.hints,
                difficulty=saved.difficulty
            )
            scenarios.append(scenario)
        return scenarios
    
    def save_to_file(self):
        """保存进度到文件"""
        data = {
            "progress": self.progress.model_dump(),
            "saved_scenarios": [s.model_dump() for s in self.saved_scenarios]
        }
        
        file_path = self.data_dir / f"{self.user_id}_progress.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_file(self):
        """从文件加载进度"""
        file_path = self.data_dir / f"{self.user_id}_progress.json"
        
        if not file_path.exists():
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.progress = LearningProgress(**data["progress"])
        self.saved_scenarios = [SavedScenario(**s) for s in data.get("saved_scenarios", [])]
    
    def get_progress_summary(self) -> dict:
        """获取进度摘要"""
        accuracy = (
            self.progress.predictions_correct / self.progress.predictions_total * 100
            if self.progress.predictions_total > 0 else 0.0
        )
        
        return {
            "user_id": self.user_id,
            "scenarios_completed": len(self.progress.scenarios_completed),
            "predictions_total": self.progress.predictions_total,
            "predictions_correct": self.progress.predictions_correct,
            "accuracy": accuracy,
            "weak_areas": self.progress.weak_areas,
            "notes_count": len(self.progress.notes),
            "saved_scenarios_count": len(self.saved_scenarios),
            "last_active": self.progress.last_active
        }
    
    def get_achievement_badges(self) -> list[str]:
        """获取成就徽章"""
        badges = []
        
        # 准确率徽章
        if self.progress.predictions_total >= 10:
            accuracy = self.progress.predictions_correct / self.progress.predictions_total
            if accuracy >= 0.9:
                badges.append("🎯 精准预测者 (90%+ 准确率)")
            elif accuracy >= 0.7:
                badges.append("👍 稳定学习者 (70%+ 准确率)")
        
        # 完成度徽章
        if len(self.progress.scenarios_completed) >= 5:
            badges.append("📚 场景探索者 (完成 5+ 场景)")
        
        # 笔记徽章
        if len(self.progress.notes) >= 3:
            badges.append("📝 勤奋记录者 (3+ 笔记)")
        
        return badges
    
    def get_weak_areas(self) -> list[str]:
        """获取薄弱领域"""
        return self.progress.weak_areas.copy()
