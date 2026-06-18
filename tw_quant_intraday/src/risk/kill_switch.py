from __future__ import annotations

from dataclasses import dataclass


@dataclass
class KillSwitch:
    tripped: bool = False
    reason: str = ""

    def trip(self, reason: str) -> None:
        self.tripped = True
        self.reason = reason

    def reset_for_new_day(self) -> None:
        self.tripped = False
        self.reason = ""
