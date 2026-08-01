import asyncio
import logging
from datetime import datetime, timezone
from typing import Literal

from azure.iot.device import MethodResponse
from azure.iot.device.aio import IoTHubDeviceClient
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.motion import MotionService


logger = logging.getLogger(__name__)


class MotionCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")

    command_id: str = Field(alias="commandId", min_length=1, max_length=128)
    session_id: str = Field(alias="sessionId", min_length=1, max_length=128)
    sequence: int = Field(ge=1)
    direction: Literal["forward", "backward", "left", "right", "stopped"]
    speed: float = Field(ge=0.0, le=1.0)
    lease_ms: int = Field(alias="leaseMs", ge=0, le=2000)
    issued_at: datetime = Field(alias="issuedAt")
    expires_at: datetime = Field(alias="expiresAt")


class IoTHubDeviceService:
    def __init__(self, connection_string: str, motion: MotionService):
        self._client = IoTHubDeviceClient.create_from_connection_string(
            connection_string
        )
        self._motion = motion
        self._last_session_id: str | None = None
        self._last_sequence = 0

    async def connect(self) -> None:
        await self._client.connect()

    async def disconnect(self) -> None:
        await self._client.shutdown()

    async def receive_methods(self) -> None:
        while True:
            try:
                request = await self._client.receive_method_request()
                response = await self._handle_request(request)
                await self._client.send_method_response(response)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.to_thread(self._motion.stop)
                logger.exception(
                    "IoT Hub method listener failed; retrying in 2 seconds"
                )
                await asyncio.sleep(2)

    async def _handle_request(self, request) -> MethodResponse:
        if request.name != "setMotion":
            return MethodResponse.create_from_method_request(
                request,
                status=404,
                payload={"applied": False, "error": "Unknown direct method"},
            )

        try:
            command = MotionCommand.model_validate(request.payload)
            self._validate_freshness(command)
            await asyncio.to_thread(self._apply_command, command)
            self._last_session_id = command.session_id
            self._last_sequence = command.sequence
        except (ValidationError, ValueError) as error:
            await asyncio.to_thread(self._motion.stop)
            return MethodResponse.create_from_method_request(
                request,
                status=400,
                payload={"applied": False, "error": str(error)},
            )
        except Exception:
            await asyncio.to_thread(self._motion.stop)
            return MethodResponse.create_from_method_request(
                request,
                status=500,
                payload={"applied": False, "error": "Motor command failed"},
            )

        return MethodResponse.create_from_method_request(
            request,
            status=200,
            payload={
                "applied": True,
                "commandId": command.command_id,
                "sequence": command.sequence,
                "direction": command.direction,
            },
        )

    def _validate_freshness(self, command: MotionCommand) -> None:
        if command.issued_at.tzinfo is None:
            raise ValueError("issuedAt must include a timezone")
        if command.expires_at.tzinfo is None:
            raise ValueError("expiresAt must include a timezone")
        if command.expires_at <= datetime.now(timezone.utc):
            raise ValueError("Command has expired")
        if command.direction == "stopped" and command.lease_ms != 0:
            raise ValueError("A stop command must have a zero lease")
        if command.direction != "stopped" and command.lease_ms == 0:
            raise ValueError("A movement command must have a positive lease")
        if (
            command.session_id == self._last_session_id
            and command.sequence <= self._last_sequence
        ):
            raise ValueError("Command sequence is stale")

    def _apply_command(self, command: MotionCommand) -> None:
        if command.direction == "stopped":
            self._motion.stop()
        else:
            self._motion.move(
                command.direction,
                command.speed,
                command.lease_ms / 1000,
            )
