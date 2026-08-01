from gpiozero import DigitalOutputDevice, PWMOutputDevice


class MotorController:
    def __init__(self):
        # Left motor
        self.ena = PWMOutputDevice(18, frequency=1000)
        self.in1 = DigitalOutputDevice(17)
        self.in2 = DigitalOutputDevice(27)

        # Right motor
        self.enb = PWMOutputDevice(13, frequency=1000)
        self.in3 = DigitalOutputDevice(22)
        self.in4 = DigitalOutputDevice(23)

    def move(self, left_speed: float, right_speed: float) -> None:
        self._set_motor(left_speed, self.ena, self.in1, self.in2)
        self._set_motor(right_speed, self.enb, self.in3, self.in4)

    def _set_motor(
        self,
        speed: float,
        enable: PWMOutputDevice,
        input_1: DigitalOutputDevice,
        input_2: DigitalOutputDevice,
    ) -> None:
        speed = max(-1.0, min(1.0, speed))

        if speed > 0:
            input_1.on()
            input_2.off()
            enable.value = speed
        elif speed < 0:
            input_1.off()
            input_2.on()
            enable.value = abs(speed)
        else:
            enable.value = 0
            input_1.off()
            input_2.off()

    def forward(self, speed: float = 0.5) -> None:
        self.move(speed, speed)

    def backward(self, speed: float = 0.5) -> None:
        self.move(-speed, -speed)

    def turn_left(self, speed: float = 0.5) -> None:
        self.move(-speed, speed)

    def turn_right(self, speed: float = 0.5) -> None:
        self.move(speed, -speed)

    def stop(self) -> None:
        self.move(0, 0)

    def cleanup(self) -> None:
        self.stop()
        self.ena.close()
        self.enb.close()
        self.in1.close()
        self.in2.close()
        self.in3.close()
        self.in4.close()

