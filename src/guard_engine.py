"""Guard Engine for Access Control & Status Determination."""

from datetime import datetime, timedelta
from typing import Optional

from loguru import logger


class GuardStatus:
    """Represents the result of a status check."""
    NORMAL = "normal"
    LATE = "late"
    EARLY_LEAVE = "early_leave"
    EXEMPTED = "exempted"
    COOLDOWN = "cooldown"
    LUNCH = "lunch"

    def __init__(self, status: str, message: str, color: tuple[int, int, int]) -> None:
        self.status = status
        self.message = message
        self.color = color  # RGB tuple

    @property
    def is_abnormal(self) -> bool:
        return self.status not in (self.NORMAL, self.EXEMPTED, self.COOLDOWN)


class GuardEngine:
    """Determines access status based on time rules and exceptions."""

    def __init__(self, config: dict) -> None:
        self.enabled = config.get("guard_mode", {}).get("enabled", False)
        if not self.enabled:
            logger.info("Guard Mode is disabled.")
            return

        self.start_hour, self.start_min = map(int, config["guard_mode"]["work_hours"]["start"].split(":"))
        self.end_hour, self.end_min = map(int, config["guard_mode"]["work_hours"]["end"].split(":"))
        self.grace_minutes = config["guard_mode"].get("grace_period_minutes", 15)

        # Lunch Break Configuration
        self.lunch = config.get("lunch_break", {})
        self.lunch_enabled = self.lunch.get("enabled", False)
        if self.lunch_enabled:
            self.lunch_start = datetime.strptime(self.lunch["start"], "%H:%M").time()
            self.lunch_end = datetime.strptime(self.lunch["end"], "%H:%M").time()

        logger.info(
            f"Guard Mode enabled: {self.start_hour:02d}:{self.start_min:02d} - {self.end_hour:02d}:{self.end_min:02d}"
        )

    def get_status(
        self,
        name: str,
        current_time: Optional[datetime] = None,
        is_cooldown: bool = False,
        is_exempted: bool = False,
    ) -> GuardStatus:
        """Determine the access status for a person."""
        if not self.enabled:
            # If guard mode is off, just return generic success
            if is_cooldown:
                return GuardStatus(GuardStatus.COOLDOWN, f"{name} - 偵測中 (冷卻中)", (255, 165, 0))
            return GuardStatus(GuardStatus.NORMAL, f"{name} - 打卡成功!", (0, 255, 0))

        if is_cooldown:
            return GuardStatus(GuardStatus.COOLDOWN, f"{name} - 偵測中 (冷卻中)", (255, 165, 0))

        if is_exempted:
            return GuardStatus(GuardStatus.EXEMPTED, f"{name} - 已核准 (請假/公出)", (0, 128, 255))

        now = current_time or datetime.now()
        now_time = now.time()

        # Check Lunch Break first
        if self.lunch_enabled and self.lunch_start <= now_time <= self.lunch_end:
            return GuardStatus(GuardStatus.LUNCH, f"{name} - 午休時間", (0, 191, 255))

        start_time = now.replace(hour=self.start_hour, minute=self.start_min, second=0, microsecond=0)
        end_time = now.replace(hour=self.end_hour, minute=self.end_min, second=0, microsecond=0)

        # Check if late
        if now < start_time:
            if (start_time - now).total_seconds() <= self.grace_minutes * 60:
                return GuardStatus(GuardStatus.NORMAL, f"{name} - 打卡成功 (允許)", (0, 255, 0))
            else:
                return GuardStatus(GuardStatus.LATE, f"{name} - 異常 (遲到/早到)", (255, 0, 0))

        # Check if early leave (before end time but significantly early)
        # For simplicity, if they check in during work hours, it's normal.
        # If they check out, that's a different flow, but for single check-in point:
        # Let's assume "Check-in" means entering. If entering after work hours:
        if now > end_time:
            return GuardStatus(GuardStatus.LATE, f"{name} - 異常 (非工作時間)", (255, 0, 0))

        # Within work hours
        return GuardStatus(GuardStatus.NORMAL, f"{name} - 打卡成功!", (0, 255, 0))
