"""
S28: Profile Versioning Tests
"""
import pytest
from simulator.profile_versioning import (
    ProfileStatus,
    ProfileVersion,
    ProfileChange,
    ProfileRepository
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


@pytest.fixture
def repository():
    """配置仓库"""
    return ProfileRepository()


class TestProfileStatus:
    """配置状态测试"""
    
    def test_status_enum(self):
        """测试状态枚举"""
        assert ProfileStatus.DRAFT == "draft"
        assert ProfileStatus.CANDIDATE == "candidate"
        assert ProfileStatus.PUBLISHED == "published"
        assert ProfileStatus.DEPRECATED == "deprecated"


class TestProfileVersion:
    """配置版本测试"""
    
    def test_version_creation(self, profile):
        """测试版本创建"""
        version = ProfileVersion(
            version_id="v001",
            profile=profile,
            status=ProfileStatus.DRAFT,
            created_at="2026-08-23T12:00:00",
            updated_at="2026-08-23T12:00:00",
            created_by="test_user"
        )
        
        assert version.version_id == "v001"
        assert version.status == ProfileStatus.DRAFT
        assert version.created_by == "test_user"
    
    def test_version_with_parent(self, profile):
        """测试带父版本的版本"""
        version = ProfileVersion(
            version_id="v002",
            profile=profile,
            status=ProfileStatus.DRAFT,
            created_at="2026-08-23T12:00:00",
            updated_at="2026-08-23T12:00:00",
            created_by="test_user",
            parent_version="v001"
        )
        
        assert version.parent_version == "v001"


class TestProfileRepository:
    """配置仓库测试"""
    
    def test_repository_creation(self):
        """测试仓库创建"""
        repo = ProfileRepository()
        assert len(repo.versions) == 0
        assert repo.current_version_id is None
    
    def test_create_version(self, repository, profile):
        """测试创建版本"""
        version = repository.create_version(
            profile=profile,
            created_by="test_user",
            change_reason="Initial version"
        )
        
        assert version.version_id == "v001"
        assert version.status == ProfileStatus.DRAFT
        assert repository.current_version_id == "v001"
        assert len(repository.versions) == 1
    
    def test_update_version(self, repository, profile):
        """测试更新版本"""
        version = repository.create_version(profile, "test_user")
        
        # 修改配置
        new_profile = profile.model_copy()
        new_profile.complianceUa = 60.0
        
        updated = repository.update_version(
            version_id=version.version_id,
            profile=new_profile,
            updated_by="test_user",
            change_reason="Updated compliance"
        )
        
        assert updated.profile.complianceUa == 60.0
        assert len(repository.changes) == 2  # create + update
    
    def test_update_published_version_fails(self, repository, profile):
        """测试更新已发布版本失败"""
        version = repository.create_version(profile, "test_user")
        repository.promote_version(version.version_id, "test_user", ProfileStatus.CANDIDATE)
        repository.promote_version(version.version_id, "test_user", ProfileStatus.PUBLISHED)
        
        new_profile = profile.model_copy()
        new_profile.complianceUa = 60.0
        
        with pytest.raises(ValueError, match="Cannot update published version"):
            repository.update_version(version.version_id, new_profile, "test_user", "Update")
    
    def test_promote_version(self, repository, profile):
        """测试提升版本状态"""
        version = repository.create_version(profile, "test_user")
        
        # Draft -> Candidate
        candidate = repository.promote_version(
            version.version_id,
            "test_user",
            ProfileStatus.CANDIDATE
        )
        assert candidate.status == ProfileStatus.CANDIDATE
        
        # Candidate -> Published
        published = repository.promote_version(
            version.version_id,
            "test_user",
            ProfileStatus.PUBLISHED
        )
        assert published.status == ProfileStatus.PUBLISHED
        assert repository.current_version_id == version.version_id
    
    def test_promote_invalid_transition(self, repository, profile):
        """测试无效的状态转换"""
        version = repository.create_version(profile, "test_user")
        
        # 不能直接从 Draft 到 Published
        with pytest.raises(ValueError, match="Cannot promote from draft to published"):
            repository.promote_version(version.version_id, "test_user", ProfileStatus.PUBLISHED)
    
    def test_get_version(self, repository, profile):
        """测试获取版本"""
        version = repository.create_version(profile, "test_user")
        
        retrieved = repository.get_version(version.version_id)
        assert retrieved.version_id == version.version_id
    
    def test_get_version_not_found(self, repository):
        """测试获取不存在的版本"""
        with pytest.raises(ValueError, match="Version 'v999' not found"):
            repository.get_version("v999")
    
    def test_get_current_version(self, repository, profile):
        """测试获取当前版本"""
        assert repository.get_current_version() is None
        
        version = repository.create_version(profile, "test_user")
        current = repository.get_current_version()
        assert current.version_id == version.version_id
    
    def test_get_published_version(self, repository, profile):
        """测试获取已发布版本"""
        assert repository.get_published_version() is None
        
        version = repository.create_version(profile, "test_user")
        repository.promote_version(version.version_id, "test_user", ProfileStatus.CANDIDATE)
        repository.promote_version(version.version_id, "test_user", ProfileStatus.PUBLISHED)
        
        published = repository.get_published_version()
        assert published.version_id == version.version_id
    
    def test_list_versions(self, repository, profile):
        """测试列出版本"""
        repository.create_version(profile, "test_user")
        repository.create_version(profile, "test_user")
        repository.create_version(profile, "test_user")
        
        all_versions = repository.list_versions()
        assert len(all_versions) == 3
        
        draft_versions = repository.list_versions(ProfileStatus.DRAFT)
        assert len(draft_versions) == 3
    
    def test_get_change_history(self, repository, profile):
        """测试获取变更历史"""
        version = repository.create_version(profile, "test_user", "Initial")
        repository.promote_version(version.version_id, "test_user", ProfileStatus.CANDIDATE)
        
        history = repository.get_change_history()
        assert len(history) == 2
        
        version_history = repository.get_change_history(version.version_id)
        assert len(version_history) == 2
    
    def test_rollback_to_version(self, repository, profile):
        """测试回滚到指定版本"""
        v1 = repository.create_version(profile, "test_user", "Version 1")
        repository.promote_version(v1.version_id, "test_user", ProfileStatus.CANDIDATE)
        repository.promote_version(v1.version_id, "test_user", ProfileStatus.PUBLISHED)
        
        # 创建新版本
        new_profile = profile.model_copy()
        new_profile.complianceUa = 60.0
        v2 = repository.create_version(new_profile, "test_user", "Version 2")
        
        # 回滚到 v1
        rolled_back = repository.rollback_to_version(v1.version_id, "test_user")
        
        assert rolled_back.profile.complianceUa == 50.0  # v1 的值
        assert rolled_back.parent_version == v1.version_id
    
    def test_get_summary(self, repository, profile):
        """测试获取摘要"""
        repository.create_version(profile, "test_user")
        repository.create_version(profile, "test_user")
        
        summary = repository.get_summary()
        
        assert summary["total_versions"] == 2
        assert summary["current_version_id"] == "v002"
        assert summary["versions_by_status"]["draft"] == 2


class TestProfileChange:
    """配置变更测试"""
    
    def test_change_creation(self):
        """测试变更创建"""
        change = ProfileChange(
            version_id="v001",
            timestamp="2026-08-23T12:00:00",
            changed_by="test_user",
            change_type="create",
            description="Created version",
            field_changes={}
        )
        
        assert change.version_id == "v001"
        assert change.change_type == "create"
