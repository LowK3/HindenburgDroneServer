import cv2
from picamera2 import Picamera2

class Camera:
    def __init__(self, size=(1440,1080), fps=60):
        self.cam = Picamera2()
        cfg = self.cam.create_video_configuration(main={"size": size},
                                                  controls={"FrameRate": fps})
        self.cam.configure(cfg)
        self.cam.start()

    def capture_frame(self):
        frame = self.cam.capture_array()
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
