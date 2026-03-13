"""
GStreamer webrtcbin 管理器（后端发起 offer）。

职责边界：
- 启动 GStreamer 管线并管理 webrtcbin
- 生成 offer / 处理 answer
- 转发 ICE candidate
"""

from __future__ import annotations

import asyncio
import threading
from typing import Callable, Optional

from .logging_config import logger
from .config import settings

import gi

gi.require_version("Gst", "1.0")
gi.require_version("GstWebRTC", "1.0")
gi.require_version("GstSdp", "1.0")
from gi.repository import Gst, GstWebRTC, GstSdp, GLib


class GstWebRTCSession:
    def __init__(
        self,
        on_offer: Callable[[str, str], None],
        on_ice_candidate: Callable[[int, str], None],
    ) -> None:
        self._on_offer = on_offer
        self._on_ice_candidate = on_ice_candidate
        self._pipeline: Optional[Gst.Pipeline] = None
        self._webrtcbin: Optional[Gst.Element] = None
        self._loop: Optional[GLib.MainLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return

        Gst.init(None)

        pipeline_str = (
            f"rtspsrc location={settings.CAMERA_RTSP_URL} protocols=tcp latency=100 "
            "! rtph265depay "
            "! h265parse "
            "! qsvh265dec "
            "! queue max-size-buffers=1 leaky=downstream "
            "! videoconvert "
            "! video/x-raw,format=NV12 "
            "! qsvh264enc bitrate=3000 gop-size=15 rate-control=cbr "
            "! h264parse config-interval=1 "
            "! rtph264pay name=pay0 aggregate-mode=zero-latency config-interval=1 pt=96"
        )

        logger.info("启动 GStreamer webrtcbin 管线")
        logger.info(pipeline_str)

        self._pipeline = Gst.parse_launch(pipeline_str)
        if not self._pipeline:
            raise RuntimeError("GStreamer.parse_launch 失败")

        payloader = self._pipeline.get_by_name("pay0")
        if not payloader:
            raise RuntimeError("未找到 payloader: pay0")

        self._webrtcbin = Gst.ElementFactory.make("webrtcbin", "sendrecv")
        if not self._webrtcbin:
            raise RuntimeError("未能创建 webrtcbin 元素")

        self._webrtcbin.set_property("bundle-policy", 3)
        self._webrtcbin.set_property("latency", 0)

        self._pipeline.add(self._webrtcbin)

        src_pad = payloader.get_static_pad("src")
        sink_pad = self._webrtcbin.get_request_pad("sink_%u")
        if not src_pad or not sink_pad:
            raise RuntimeError("无法获取 payloader 或 webrtcbin pad")

        if src_pad.link(sink_pad) != Gst.PadLinkReturn.OK:
            raise RuntimeError("payloader 无法连接到 webrtcbin")

        self._webrtcbin.connect("on-negotiation-needed", self._on_negotiation_needed)
        self._webrtcbin.connect("on-ice-candidate", self._on_ice_candidate_cb)

        bus = self._pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)

        self._loop = GLib.MainLoop()
        self._loop_thread = threading.Thread(target=self._loop.run, daemon=True)
        self._loop_thread.start()

        self._pipeline.set_state(Gst.State.PLAYING)
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        if self._pipeline:
            self._pipeline.set_state(Gst.State.NULL)
        if self._loop:
            self._loop.quit()
        self._pipeline = None
        self._webrtcbin = None
        self._loop = None
        self._loop_thread = None
        self._started = False

    def set_answer(self, sdp: str) -> None:
        if not self._webrtcbin:
            raise RuntimeError("webrtcbin 未初始化")

        sdp_msg = GstSdp.SDPMessage.new()
        GstSdp.sdp_message_parse_buffer(bytes(sdp.encode("utf-8")), sdp_msg)
        answer = GstWebRTC.WebRTCSessionDescription.new(
            GstWebRTC.WebRTCSDPType.ANSWER, sdp_msg
        )
        promise = Gst.Promise.new()
        self._webrtcbin.emit("set-remote-description", answer, promise)

    def add_ice_candidate(self, sdp_mline_index: int, candidate: str) -> None:
        if not self._webrtcbin:
            raise RuntimeError("webrtcbin 未初始化")
        self._webrtcbin.emit("add-ice-candidate", sdp_mline_index, candidate)

    def _on_negotiation_needed(self, element: Gst.Element) -> None:
        if not self._webrtcbin:
            return
        promise = Gst.Promise.new_with_change_func(self._on_offer_created, None, None)
        self._webrtcbin.emit("create-offer", None, promise)

    def _on_offer_created(self, promise: Gst.Promise, _user_data) -> None:
        if not self._webrtcbin:
            return

        reply = promise.get_reply()
        offer = reply.get_value("offer")
        self._webrtcbin.emit("set-local-description", offer, Gst.Promise.new())

        sdp_text = offer.sdp.as_text()
        sdp_type = "offer"

        asyncio.get_event_loop().call_soon_threadsafe(self._on_offer, sdp_type, sdp_text)

    def _on_ice_candidate_cb(self, element: Gst.Element, mlineindex: int, candidate: str) -> None:
        asyncio.get_event_loop().call_soon_threadsafe(self._on_ice_candidate, mlineindex, candidate)

    def _on_bus_message(self, bus: Gst.Bus, message: Gst.Message) -> None:
        msg_type = message.type
        if msg_type == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            logger.error(f"GStreamer 错误: {err}, {debug}")
        elif msg_type == Gst.MessageType.EOS:
            logger.warning("GStreamer 管线结束 (EOS)")
