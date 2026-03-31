import cv2
import traceback
import threading
from picamera2 import Picamera2
from config import NATIVE_RESOLUTION, CAM_RESOLUTION, CAM_FPS
from Utils.common import log

class Camera:
    def __init__(self):
        self.cam = None

    def start(self):
        try:
            self.cam = Picamera2()
            cfg = self.cam.create_video_configuration(
                sensor={"output_size": NATIVE_RESOLUTION},
                main={"size": CAM_RESOLUTION, "format": "RGB888"},
                controls={"FrameRate": CAM_FPS})
            self.cam.configure(cfg)
            self.cam.start()
            log(f"Camera started with res={CAM_RESOLUTION}, fps={CAM_FPS}")
        except Exception as e:
            log(f"Camera init/start failed: {e}\n{traceback.format_exc()}")
            self.cam = None
            raise

    def capture_frame(self):
        if self.cam is None:
            return None
        try:
            frame = self.cam.capture_array()
            return frame
        except Exception as e:
            log(f"Camera capture error: {e}\n{traceback.format_exc()}")
            return None

    def stop(self):
        if self.cam is not None:
            try:
                stop_thread = threading.Thread(target=self.cam.stop)
                stop_thread.start()
                stop_thread.join(timeout=2.0)

                if stop_thread.is_alive():
                    log("WARNING: Camera stop timed out (Hardware likely disconnected!). Abandoning camera.")
                else:
                    log("Camera stopped cleanly.")
            except Exception as e:
                log(f"Camera stop error: {e}\n{traceback.format_exc()}")
            finally:
                self.cam = None
