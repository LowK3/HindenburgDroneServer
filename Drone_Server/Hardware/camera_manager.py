import cv2
from picamera2 import Picamera2
from config import CAM_RESOLUTION, CAM_FPS
from Utils.common import log

class Camera:
    def __init__(self):
        self.cam = None

    def start(self):
        try:
            self.cam = Picamera2()
            cfg = self.cam.create_video_configuration(
                main={"size": CAM_RESOLUTION},
                #raw={"size": (3280, 2464)},
                controls={"FrameRate": CAM_FPS})
            self.cam.configure(cfg)
            self.cam.start()
            log(f"Camera started with res={CAM_RESOLUTION}, fps={CAM_FPS}")
        except Exception as e:
            log(f"Camera init/start failed: {e}")
            self.cam = None
            raise

    def capture_frame(self):
        if self.cam is None:
            return None
        try:
            frame = self.cam.capture_array()
            return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        except Exception as e:
            log(f"Camera capture error: {e}")
            return None

    def stop(self):
        if self.cam is not None:
            try:
                self.cam.stop()
                log("Camera stopped")
            except Exception as e:
                log(f"Camera stop error: {e}")
            self.cam = None
