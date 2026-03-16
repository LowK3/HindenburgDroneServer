import cv2, traceback
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from config import CAM_RESOLUTION, CAM_FPS
from Utils.common import log

class StreamingOutput(io.BufferedIOBase):
    """ Bridges the asynchronous hardware encoder to your synchronous UDP loop """
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        # Catch the finished JPEG from the hardware and notify the main thread!
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)

class Camera:
    def __init__(self):
        self.cam = None
        self.output = StreamingOutput()

    def start(self):
        try:
            self.cam = Picamera2()
            cfg = self.cam.create_video_configuration(
                main={"size": CAM_RESOLUTION, "format": "YUV420"},
                controls={"FrameRate": CAM_FPS})
            self.cam.configure(cfg)
            self.cam.start_encoder(MJPEGEncoder(), self.output)
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
            with self.output.condition:
                if self.output.condition.wait(timeout=1.0): 
                    return self.output.frame
                else:
                    return None
        except Exception as e:
            log(f"Camera capture error: {e}\n{traceback.format_exc()}")
            return None

    def stop(self):
        if self.cam is not None:
            try:
                self.cam.stop_encoder()
                self.cam.stop()
                log("Camera stopped.")
            except Exception as e:
                log(f"Camera stop error: {e}\n{traceback.format_exc()}")
            self.cam = None
