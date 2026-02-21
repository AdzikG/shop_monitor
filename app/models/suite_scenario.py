from sqlalchemy import Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class SuiteScenario(Base):
    """
    Relacja wiele-do-wielu: Suite <-> Scenario.

    Jeden scenariusz moze nalezec do wielu suite.
    Kazde przypisanie ma wlasna kolejnosc w danej suite.
    """
    __tablename__ = "suite_scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    suite_id: Mapped[int] = mapped_column(ForeignKey("suites.id"), nullable=False)
    scenario_id: Mapped[int] = mapped_column(ForeignKey("scenarios.id"), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)  # kolejnosc w suite
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relacje
    suite: Mapped["Suite"] = relationship(back_populates="suite_scenarios")
    scenario: Mapped["Scenario"] = relationship(back_populates="suite_scenarios")

    def __repr__(self) -> str:
        return f"<SuiteScenario suite={self.suite_id} scenario={self.scenario_id} order={self.order}>"
