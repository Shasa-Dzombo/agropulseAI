# Main application for the Pi-CCTV device.
# This script captures video from the Pi camera and serves it via RTSP.

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstRtspServer', '1.0')
from gi.repository import Gst, GstRtspServer, GObject

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Pi_CCTV")

class PiRTSPServer:
    def __init__(self):
        GObject.threads_init()
        Gst.init(None)

        self.server = GstRtspServer.RTSPServer()
        self.server.set_service("8554")
        
        # Using libcamera-vid for modern Raspberry Pi OS
        # This pipeline captures H.264 encoded video directly from the camera hardware encoder.
        # This is very efficient and avoids software encoding.
        launch_string = (
            'libcamerasrc ! '
            'video/x-h264,width=1280,height=720,framerate=30/1 ! '
            'h264parse ! '
            'rtph264pay name=pay0 pt=96'
        )
        
        factory = GstRtspServer.RTSPMediaFactory()
        factory.set_launch_string(launch_string)
        factory.set_shared(True) # Allow multiple clients to connect

        mounts = self.server.get_mount_points()
        mounts.add_factory("/stream", factory)
        
        self.server.attach(None)
        logger.info("RTSP server started. Stream available at rtsp://<pi_ip>:8554/stream")

    def run(self):
        self.loop = GObject.MainLoop()
        self.loop.run()

if __name__ == '__main__':
    rtsp_server = PiRTSPServer()
    try:
        rtsp_server.run()
    except KeyboardInterrupt:
        logger.info("Shutting down RTSP server.")
