""" Video network ports """
TCP_PORT = 8485
UDP_PORT = 37020

""" Engine control port """
CONTROL_TCP_PORT = 8600

""" Camera settings """
CAM_RESOLUTION = (1280, 720)
CAM_FULL_RES = (3280, 2464)
CAM_FPS = 30
JPEG_QUALITY = 90
FORMAT = ".jpeg"

FRAME_INTERVAL = 1.0 / CAM_FPS

""" Connection timeouts """
UDP_TIMEOUT = 0.25
TCP_ACCEPT_TIMEOUT = 2.0
TCP_SEND_TIMEOUT = 15.0
MAX_TCP_WAIT = 10.0

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
NEUTRAL = 75         # 7.5%
MAX_FORWARD = 100    # 10%
MAX_REVERSE = 60     # 6%
