import asyncio
from contextlib import asynccontextmanager, suppress
from os import getenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.hardware.motor import MotorController
from app.services.motion import MotionService


COMMAND_LEASE_SECONDS = 0.4
WATCHDOG_INTERVAL_SECONDS = 0.05
DEFAULT_SPEED = 0.5
DASHBOARD_ORIGINS = [
    origin.strip()
    for origin in getenv(
        "DASHBOARD_ORIGINS",
        "http://localhost:3000,  https://robot-car.phatchung.dev"
    ).split(",")
    if origin.strip()
]

motor = MotorController()
motion = MotionService(motor, COMMAND_LEASE_SECONDS)


async def motor_watchdog() -> None:
    while True:
        motion.stop_if_expired()
        await asyncio.sleep(WATCHDOG_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    motion.stop()
    watchdog_task = asyncio.create_task(motor_watchdog())

    try:
        yield
    finally:
        watchdog_task.cancel()

        with suppress(asyncio.CancelledError):
            await watchdog_task

        motion.cleanup()


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=DASHBOARD_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def movement_response(direction: str) -> dict[str, str | float | int]:
    return {
        "status": "moving",
        "direction": direction,
        "speed": DEFAULT_SPEED,
        "leaseMs": int(COMMAND_LEASE_SECONDS * 1000),
    }


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


@app.get("/api/motor/status")
def motor_status():
    return motion.status()


@app.post("/api/motor/go-forward")
def go_forward():
    motion.move("forward", DEFAULT_SPEED)
    return movement_response("forward")


@app.post("/api/motor/go-backward")
def go_backward():
    motion.move("backward", DEFAULT_SPEED)
    return movement_response("backward")


@app.post("/api/motor/turn-left")
def turn_left():
    motion.move("left", DEFAULT_SPEED)
    return movement_response("left")


@app.post("/api/motor/turn-right")
def turn_right():
    motion.move("right", DEFAULT_SPEED)
    return movement_response("right")


@app.post("/api/motor/stop")
def stop_motor():
    motion.stop()
    return {
        "status": "stopped",
        "direction": "stopped",
    }
