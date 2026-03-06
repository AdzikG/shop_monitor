from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from app.models.base import Base, now_utc

if TYPE_CHECKING:
    from app.models.suite_run import SuiteRun


class AlertStatus(str, Enum):
    OPEN                 = "open"
    IN_PROGRESS          = "in_progress"
    AWAITING_FIX         = "awaiting_fix"          # BUG, NEEDS_DEV, CONFIG
    AWAITING_TEST_UPDATE = "awaiting_test_update"   # SCRIPT_FIX, SCENARIO_FIX
    CLOSED               = "closed"                 # NAB, DUPLICATE, CANT_REPRODUCE


class ResolutionType(str, Enum):
    # → AWAITING_FIX
    BUG           = "bug"
    NEEDS_DEV     = "needs_dev"
    CONFIG        = "config"
    # → AWAITING_TEST_UPDATE
    SCRIPT_FIX    = "script_fix"
    SCENARIO_FIX  = "scenario_fix"
    # → CLOSED
    NAB           = "nab"
    DUPLICATE     = "duplicate"
    CANT_REPRODUCE = "cant_reproduce"


# Mapowanie resolution → status (używane przy zamykaniu alertu)
RESOLUTION_TO_STATUS: dict[ResolutionType, AlertStatus] = {
    ResolutionType.BUG:            AlertStatus.AWAITING_FIX,
    ResolutionType.NEEDS_DEV:      AlertStatus.AWAITING_FIX,
    ResolutionType.CONFIG:         AlertStatus.AWAITING_FIX,
    ResolutionType.SCRIPT_FIX:     AlertStatus.AWAITING_TEST_UPDATE,
    ResolutionType.SCENARIO_FIX:   AlertStatus.AWAITING_TEST_UPDATE,
    ResolutionType.NAB:            AlertStatus.CLOSED,
    ResolutionType.DUPLICATE:      AlertStatus.CLOSED,
    ResolutionType.CANT_REPRODUCE: AlertStatus.CLOSED,
}

# Statusy które "czekają cicho" — alert nie wraca do OPEN gdy pojawi się ponownie
AWAITING_STATUSES = {AlertStatus.AWAITING_FIX, AlertStatus.AWAITING_TEST_UPDATE}

# Statusy CLOSED które powodują reopen gdy alert wróci
REOPEN_ON_RETURN = {ResolutionType.NAB, ResolutionType.CANT_REPRODUCE}


class AlertGroup(Base):
    """
    Grupa alertów — deduplikacja alertów z tego samego business_rule.
    Jeśli alert powtarza się w kolejnych runach, zwiększa się repeat_count.
    """
    __tablename__ = "alert_groups"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Ostatni suite_run który zaktualizował ten alert
    last_suite_run_id: Mapped[int] = mapped_column(ForeignKey("suite_runs.id"), nullable=False)

    # Historia wszystkich suite_run_ids które ten alert wygenerowały
    suite_run_history: Mapped[Optional[str]] = mapped_column(Text, default="[]")

    # Business rule
    business_rule: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Typ alertu (slug z alert_types)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Title z alert_config (snapshot, NIE computed)
    title: Mapped[str] = mapped_column(String(255), nullable=False)

    # Ile razy wystąpił w OSTATNIM suite_run
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # IDs scenariuszy z OSTATNIEGO suite_run (JSON list)
    scenario_ids: Mapped[str] = mapped_column(Text, nullable=False)

    # Ile razy powtórzył się
    repeat_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Ile czystych runów (bez tego alertu) minęło od ostatniego wystąpienia
    clean_runs_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Status workflow
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, native_enum=False, length=25),
        default=AlertStatus.OPEN,
        nullable=False
    )

    # Resolution
    resolution_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Duplikat — wskazuje na parent AlertGroup
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("alert_groups.id"), nullable=True
    )

    # Weryfikacja — kto podjął się analizy
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)

    # Stare pole — zostawiamy dla kompatybilności, używaj resolved_at
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Workflow metadata (stare pole — notatki ogólne)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Relacje
    last_suite_run: Mapped["SuiteRun"] = relationship(back_populates="alert_groups")
    duplicate_of: Mapped[Optional["AlertGroup"]] = relationship(
        "AlertGroup", remote_side="AlertGroup.id", foreign_keys=[duplicate_of_id]
    )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @property
    def is_awaiting(self) -> bool:
        """Czy alert czeka na fix (cichy przy powrocie)."""
        return self.status in AWAITING_STATUSES

    @property
    def resolution_label(self) -> Optional[str]:
        """Czytelna etykieta resolution_type."""
        labels = {
            'bug':            '🐛 BUG',
            'needs_dev':      '🔧 NEEDS DEV',
            'config':         '⚙️ CONFIG',
            'script_fix':     '📝 SCRIPT FIX',
            'scenario_fix':   '🔄 SCENARIO FIX',
            'nab':            '⚠️ NAB',
            'duplicate':      '🔗 DUPLICATE',
            'cant_reproduce': '🔄 CANT REPRODUCE',
        }
        return labels.get(self.resolution_type) if self.resolution_type else None

    def __repr__(self) -> str:
        return f"<AlertGroup {self.business_rule} [{self.status.value}, repeat: {self.repeat_count}x]>"
