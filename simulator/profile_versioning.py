"""
S28: Profile Versioning & Promotion Workflow

实现配置版本管理，支持：
- 草稿/候选/发布状态
- 版本追踪
- 回滚支持
- 变更历史
"""
from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel
from packages.contracts.types import DeviceProfile


class ProfileStatus(str, Enum):
    """配置状态"""
    DRAFT = "draft"  # 草稿
    CANDIDATE = "candidate"  # 候选
    PUBLISHED = "published"  # 已发布
    DEPRECATED = "deprecated"  # 已弃用


class ProfileVersion(BaseModel):
    """配置版本"""
    version_id: str
    profile: DeviceProfile
    status: ProfileStatus
    created_at: str
    updated_at: str
    created_by: str
    change_reason: Optional[str] = None
    parent_version: Optional[str] = None
    calibration_report_id: Optional[str] = None


class ProfileChange(BaseModel):
    """配置变更"""
    version_id: str
    timestamp: str
    changed_by: str
    change_type: str  # "create", "update", "promote", "deprecate"
    description: str
    field_changes: dict  # 字段变更详情


class ProfileRepository:
    """配置仓库"""
    
    def __init__(self):
        self.versions: dict[str, ProfileVersion] = {}
        self.changes: list[ProfileChange] = []
        self.current_version_id: Optional[str] = None
    
    def create_version(
        self,
        profile: DeviceProfile,
        created_by: str,
        change_reason: Optional[str] = None,
        parent_version: Optional[str] = None
    ) -> ProfileVersion:
        """创建新版本"""
        version_id = f"v{len(self.versions) + 1:03d}"
        now = datetime.now().isoformat()
        
        version = ProfileVersion(
            version_id=version_id,
            profile=profile,
            status=ProfileStatus.DRAFT,
            created_at=now,
            updated_at=now,
            created_by=created_by,
            change_reason=change_reason,
            parent_version=parent_version
        )
        
        self.versions[version_id] = version
        self.current_version_id = version_id
        
        # 记录变更
        change = ProfileChange(
            version_id=version_id,
            timestamp=now,
            changed_by=created_by,
            change_type="create",
            description=f"Created version {version_id}",
            field_changes={}
        )
        self.changes.append(change)
        
        return version
    
    def update_version(
        self,
        version_id: str,
        profile: DeviceProfile,
        updated_by: str,
        change_reason: str
    ) -> ProfileVersion:
        """更新版本"""
        if version_id not in self.versions:
            raise ValueError(f"Version '{version_id}' not found")
        
        version = self.versions[version_id]
        
        if version.status == ProfileStatus.PUBLISHED:
            raise ValueError(f"Cannot update published version '{version_id}'")
        
        # 记录字段变更
        field_changes = self._compare_profiles(version.profile, profile)
        
        now = datetime.now().isoformat()
        version.profile = profile
        version.updated_at = now
        version.change_reason = change_reason
        
        # 记录变更
        change = ProfileChange(
            version_id=version_id,
            timestamp=now,
            changed_by=updated_by,
            change_type="update",
            description=change_reason,
            field_changes=field_changes
        )
        self.changes.append(change)
        
        return version
    
    def promote_version(
        self,
        version_id: str,
        promoted_by: str,
        target_status: ProfileStatus
    ) -> ProfileVersion:
        """提升版本状态"""
        if version_id not in self.versions:
            raise ValueError(f"Version '{version_id}' not found")
        
        version = self.versions[version_id]
        
        # 验证状态转换
        valid_transitions = {
            ProfileStatus.DRAFT: [ProfileStatus.CANDIDATE],
            ProfileStatus.CANDIDATE: [ProfileStatus.PUBLISHED, ProfileStatus.DRAFT],
            ProfileStatus.PUBLISHED: [ProfileStatus.DEPRECATED],
            ProfileStatus.DEPRECATED: []
        }
        
        if target_status not in valid_transitions[version.status]:
            raise ValueError(
                f"Cannot promote from {version.status.value} to {target_status.value}"
            )
        
        now = datetime.now().isoformat()
        old_status = version.status
        version.status = target_status
        version.updated_at = now
        
        # 记录变更
        change = ProfileChange(
            version_id=version_id,
            timestamp=now,
            changed_by=promoted_by,
            change_type="promote",
            description=f"Promoted from {old_status} to {target_status}",
            field_changes={"status": {"old": old_status, "new": target_status}}
        )
        self.changes.append(change)
        
        # 如果是发布，设置为当前版本
        if target_status == ProfileStatus.PUBLISHED:
            self.current_version_id = version_id
        
        return version
    
    def get_version(self, version_id: str) -> ProfileVersion:
        """获取版本"""
        if version_id not in self.versions:
            raise ValueError(f"Version '{version_id}' not found")
        return self.versions[version_id]
    
    def get_current_version(self) -> Optional[ProfileVersion]:
        """获取当前版本"""
        if self.current_version_id is None:
            return None
        return self.versions.get(self.current_version_id)
    
    def get_published_version(self) -> Optional[ProfileVersion]:
        """获取已发布版本"""
        for version in self.versions.values():
            if version.status == ProfileStatus.PUBLISHED:
                return version
        return None
    
    def list_versions(self, status: Optional[ProfileStatus] = None) -> list[ProfileVersion]:
        """列出所有版本"""
        versions = list(self.versions.values())
        if status is not None:
            versions = [v for v in versions if v.status == status]
        return sorted(versions, key=lambda v: v.created_at, reverse=True)
    
    def get_change_history(self, version_id: Optional[str] = None) -> list[ProfileChange]:
        """获取变更历史"""
        if version_id is None:
            return self.changes
        return [c for c in self.changes if c.version_id == version_id]
    
    def rollback_to_version(
        self,
        version_id: str,
        rolled_back_by: str
    ) -> ProfileVersion:
        """回滚到指定版本"""
        if version_id not in self.versions:
            raise ValueError(f"Version '{version_id}' not found")
        
        target_version = self.versions[version_id]
        
        # 创建新版本，复制目标版本的内容
        new_version = self.create_version(
            profile=target_version.profile.model_copy(),
            created_by=rolled_back_by,
            change_reason=f"Rolled back to version {version_id}",
            parent_version=version_id
        )
        
        return new_version
    
    def _compare_profiles(
        self,
        old_profile: DeviceProfile,
        new_profile: DeviceProfile
    ) -> dict:
        """比较两个配置的差异"""
        changes = {}
        
        old_dict = old_profile.model_dump()
        new_dict = new_profile.model_dump()
        
        for key in old_dict.keys():
            if old_dict[key] != new_dict[key]:
                changes[key] = {
                    "old": old_dict[key],
                    "new": new_dict[key]
                }
        
        return changes
    
    def get_summary(self) -> dict:
        """获取仓库摘要"""
        return {
            "total_versions": len(self.versions),
            "current_version_id": self.current_version_id,
            "published_version_id": self.get_published_version().version_id if self.get_published_version() else None,
            "versions_by_status": {
                status.value: len([v for v in self.versions.values() if v.status == status])
                for status in ProfileStatus
            },
            "total_changes": len(self.changes)
        }
