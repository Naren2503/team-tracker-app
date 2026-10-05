from datetime import datetime
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"))
    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    role: Mapped[Role] = relationship()


class Lookup(Base):
    __tablename__ = "lookups"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(80), index=True)
    label: Mapped[str] = mapped_column(String(160))
    normalized: Mapped[str] = mapped_column(String(160), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("kind", "normalized", name="uq_lookup_kind_normalized"),)


class TrackerRecord(Base, TimestampMixin):
    __tablename__ = "tracker_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(String(120), index=True)
    date_started: Mapped[datetime | None] = mapped_column(Date)
    date_ended: Mapped[datetime | None] = mapped_column(Date)
    tester_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    tester_name_raw: Mapped[str | None] = mapped_column(String(160), index=True)
    status: Mapped[str] = mapped_column(String(120), index=True)
    zephyr_upload: Mapped[str | None] = mapped_column(String(160))
    comments: Mapped[str | None] = mapped_column(Text)
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    source_row: Mapped[int | None] = mapped_column(Integer)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class WorkLog(Base, TimestampMixin):
    __tablename__ = "work_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    tracker_record_id: Mapped[int | None] = mapped_column(ForeignKey("tracker_records.id"), index=True)
    ticket_id_raw: Mapped[str] = mapped_column(String(160), index=True)
    workstream: Mapped[str] = mapped_column(String(40), index=True)
    tester_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    tester_name_raw: Mapped[str | None] = mapped_column(String(160), index=True)
    task: Mapped[str | None] = mapped_column(String(160), index=True)
    priority: Mapped[str | None] = mapped_column(String(80), index=True)
    work_date: Mapped[datetime | None] = mapped_column(Date, index=True)
    work_log_hours: Mapped[float | None] = mapped_column(Float)
    passed_tc: Mapped[int | None] = mapped_column(Integer)
    passed_steps: Mapped[int | None] = mapped_column(Integer)
    failed_tc: Mapped[int | None] = mapped_column(Integer)
    failed_steps: Mapped[int | None] = mapped_column(Integer)
    daily_comments: Mapped[str | None] = mapped_column(Text)
    source_sheet: Mapped[str | None] = mapped_column(String(160))
    source_row: Mapped[int | None] = mapped_column(Integer)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, default=1)


class ImportBatch(Base):
    __tablename__ = "imports"
    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    file_hash: Mapped[str] = mapped_column(String(128), index=True)
    mode: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), index=True)
    imported_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    successful_rows: Mapped[int] = mapped_column(Integer, default=0)
    rejected_rows: Mapped[int] = mapped_column(Integer, default=0)


class ImportRow(Base):
    __tablename__ = "import_rows"
    id: Mapped[int] = mapped_column(primary_key=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"), index=True)
    sheet_name: Mapped[str] = mapped_column(String(160))
    row_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40))
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str] = mapped_column(Text)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), index=True)
    old_value_json: Mapped[str | None] = mapped_column(Text)
    new_value_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class DashboardSetting(Base, TimestampMixin):
    __tablename__ = "dashboard_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    value_json: Mapped[str] = mapped_column(Text)


class TesterCapacity(Base):
    __tablename__ = "tester_capacity"
    id: Mapped[int] = mapped_column(primary_key=True)
    tester_name: Mapped[str] = mapped_column(String(160), index=True)
    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    daily_capacity_hours: Mapped[float] = mapped_column(Float, default=7.5)
    leave_days: Mapped[float] = mapped_column(Float, default=0)
    __table_args__ = (UniqueConstraint("tester_name", "year", "month", name="uq_tester_capacity_month"),)
