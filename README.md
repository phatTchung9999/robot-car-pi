# Robot Car Backend

FastAPI backend for a Raspberry Pi robot car. The API receives movement commands from a dashboard and controls the car's motors through the Raspberry Pi GPIO pins.

## Features

- FastAPI endpoints for moving forward, backward, left, and right
- Emergency stop endpoint
- Motor status and health-check endpoints
- PWM speed control with `gpiozero`
- Command watchdog that automatically stops the motors after 400 ms unless another movement command is received
- Configurable CORS origins for a web dashboard
- GPIO cleanup when the application shuts down

## Hardware and GPIO pins

The current configuration is designed for two DC motors connected through a motor driver.

| Function | BCM GPIO pin |
| --- | ---: |
| Left motor enable (PWM) | 18 |
| Left motor input 1 | 17 |
| Left motor input 2 | 27 |
| Right motor enable (PWM) | 13 |
| Right motor input 3 | 22 |
| Right motor input 4 | 23 |

> Verify all wiring before starting the API. Incorrect wiring can damage the Raspberry Pi or motor driver. Power the motors from a suitable external supply and connect the grounds together.

## Requirements

- Raspberry Pi with GPIO access
- Python 3.10 or newer
- A compatible dual-motor driver
- FastAPI, Uvicorn, and gpiozero

## Setup

Clone the project and enter its directory, then create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install fastapi uvicorn
```

## Configuration

The `DASHBOARD_ORIGINS` environment variable accepts a comma-separated list of web origins that may call the API:

```bash
export DASHBOARD_ORIGINS="http://localhost:3000,https://robot-car.example.com"
```

To receive commands through Azure IoT Hub, configure the device connection
string and use the same movement lease as the cloud backend:

```bash
export IOTHUB_DEVICE_CONNECTION_STRING="HostName=<hub>.azure-devices.net;DeviceId=robot-car-01;SharedAccessKey=<device-key>"
export COMMAND_LEASE_MS="750"
```

Use a device connection string here, not an IoT Hub service-policy connection
string. Keep it outside Git. If the variable is omitted, the local HTTP API
continues to work without Azure IoT Hub.

## Run the API

Run this command from the project root on the Raspberry Pi:

```bash
uvicorn services.main:app --host 0.0.0.0 --port 8000
```

The interactive API documentation is available at `http://<raspberry-pi-ip>:8000/docs`.

## API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Check whether the API is running |
| `GET` | `/api/motor/status` | Get the current direction and remaining command lease |
| `POST` | `/api/motor/go-forward` | Move forward |
| `POST` | `/api/motor/go-backward` | Move backward |
| `POST` | `/api/motor/turn-left` | Turn left |
| `POST` | `/api/motor/turn-right` | Turn right |
| `POST` | `/api/motor/stop` | Stop immediately |

Movement commands use a default speed of 50%. For safety, each command has a configurable lease (750 ms by default). A controlling dashboard should send movement commands repeatedly while a button or control is held; the backend stops the motors when commands stop arriving.

Cloud commands arrive through the `setMotion` IoT Hub direct method. They are
validated for direction, speed, lease, expiration, and ordering before reaching
the motors. The local watchdog remains responsible for stopping the car when
command refreshes stop arriving.

## Example

```bash
curl -X POST http://localhost:8000/api/motor/go-forward
curl -X POST http://localhost:8000/api/motor/stop
```

## Project structure

```text
app/
├── hardware/
│   └── motor.py       # GPIO pins and low-level motor control
└── services/
    └── motion.py      # Movement state, locking, and safety lease
services/
└── main.py            # FastAPI application and routes
```
