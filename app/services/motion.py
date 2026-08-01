from threading import Lock
from time import monotonic
from typing import Literal

from app.hardware.motor import MotorController


Direction = Literal["forward", "backward", "left", "right", "stopped"]


class MotionService:
    def __init__(
        self,
        motor: MotorController,
        command_lease_seconds: float = 0.4,
    ):
        self._motor = motor
        self._command_lease_seconds = command_lease_seconds
        self._lock = Lock()
        self._stop_deadline: float | None = None
        self._direction: Direction = "stopped"

    @property
    def command_lease_seconds(self) -> float:
        return self._command_lease_seconds

    def move(
        self,
        direction: Direction,
        speed: float,
        command_lease_seconds: float | None = None,
    ) -> None:
        actions = {
            "forward": self._motor.forward,
            "backward": self._motor.backward,
            "left": self._motor.turn_left,
            "right": self._motor.turn_right,
        }
        action = actions.get(direction)

        if action is None:
            raise ValueError(f"Unsupported movement direction: {direction}")

        speed = max(0.0, min(1.0, speed))
        lease_seconds = (
            self._command_lease_seconds
            if command_lease_seconds is None
            else max(0.0, command_lease_seconds)
        )

        with self._lock:
            action(speed)
            self._direction = direction
            self._stop_deadline = monotonic() + lease_seconds

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def stop_if_expired(self) -> None:
        with self._lock:
            if (
                self._stop_deadline is not None
                and monotonic() >= self._stop_deadline
            ):
                self._stop_locked()

    def status(self) -> dict[str, str | int]:
        with self._lock:
            remaining_ms = 0

            if self._stop_deadline is not None:
                remaining_ms = max(
                    0,
                    int((self._stop_deadline - monotonic()) * 1000),
                )

            return {
                "direction": self._direction,
                "leaseRemainingMs": remaining_ms,
            }

    def cleanup(self) -> None:
        with self._lock:
            self._stop_deadline = None
            self._direction = "stopped"
            self._motor.cleanup()

    def _stop_locked(self) -> None:
        self._motor.stop()
        self._direction = "stopped"
        self._stop_deadline = None

