# -*- coding: utf-8 -*-

from pibooth.utils import LOGGER
from pibooth.camera.gphoto import GpCamera, get_gp_camera_proxy
from pibooth.camera.opencv import CvCamera, get_cv_camera_proxy
from pibooth.camera.hybrid import HybridCvCamera


def find_camera(cv_port=None):
    """Initialize the camera depending of the connected one. The priority order
    is chosen in order to have best rendering during preview and to take captures.
    The gPhoto2 camera is first (drivers most restrictive) to avoid connection
    concurence in case of DSLR compatible with OpenCV.

    :param cv_port: port of the OpenCV camera or a part of its name (None to use the first one found)
    :type cv_port: int or str
    """
    gp_cam_proxy = get_gp_camera_proxy()
    cv_cam_proxy = get_cv_camera_proxy(cv_port)

    if cv_cam_proxy and gp_cam_proxy:
        LOGGER.info("Configuring hybrid camera (OpenCV + gPhoto2) ...")
        return HybridCvCamera(cv_cam_proxy, gp_cam_proxy)
    elif gp_cam_proxy:
        LOGGER.info("Configuring gPhoto2 camera ...")
        return GpCamera(gp_cam_proxy)
    elif cv_cam_proxy:
        LOGGER.info("Configuring OpenCV camera ...")
        return CvCamera(cv_cam_proxy)

    raise EnvironmentError("Neither gPhoto2 nor OpenCV camera detected")
