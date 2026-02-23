""" Video network ports """
UDP_PORT = 37020
UDP_VIDEO_PORT = 8486

""" Engine control port """
CONTROL_TCP_PORT = 8600

""" Camera settings """
CAM_RESOLUTION = (1680, 1232)
CAM_FPS = 30
JPEG_QUALITY = 60

FRAME_INTERVAL = 1.0 / CAM_FPS

""" Connection timeouts """
UDP_TIMEOUT = 0.25
TCP_SEND_TIMEOUT = 0.5

""" Logging """
LOG_PREFIX = "[SERVER]"

""" Motor control pins (ApisQueen U2 Mini-S) """
REAR_LEFT_PIN  = 13
REAR_RIGHT_PIN = 21
FRONT_LEFT_PIN = 5
FRONT_RIGHT_PIN = 7

""" PWM settings """
PWM_FREQUENCY = 50
PWM_RANGE = 1000

""" Duty cycle settings """
NEUTRAL = 75
MAX_FORWARD = 100
MAX_REVERSE = 60
