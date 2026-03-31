""" Video network ports """
UDP_PORT = 37020
UDP_VIDEO_PORT = 8486

MAGIC_BYTE = 0xAA

""" Engine control port """
CONTROL_TCP_PORT = 8600

""" Camera settings """
NATIVE_RESOLUTION = (1680, 1232)
CAM_RESOLUTION = (840, 616)
CAM_FPS = 40
JPEG_QUALITY = 60

""" Connection timeouts """
UDP_TIMEOUT = 0.25
TCP_SEND_TIMEOUT = 0.5
CONNECTION_TIMEOUT = 1.0
RECONNECT_COOLDOWN = 5.0

""" Logging """
LOG_PREFIX = "[SERVER]"

""" Motor control pins (ApisQueen U2 Mini) """
REAR_LEFT_PIN  = 13
REAR_RIGHT_PIN = 21
FRONT_LEFT_PIN = 5
FRONT_RIGHT_PIN = 7

""" Default motor power """
DEFAULT_POWER = 9

""" Sensors """
WATER_DETECTION_PIN = 4
I2C_PORT = 1
GYRO_ADDRESS = 0x68
BME280_ADDRESS = 0x76

""" PWM settings """
PWM_FREQUENCY = 50
PWM_RANGE = 1000

""" Duty cycle settings """
NEUTRAL = 75
MAX_FORWARD = 100
MAX_REVERSE = 60
