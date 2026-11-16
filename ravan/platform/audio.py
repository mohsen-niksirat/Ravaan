"""Zero-dependency Win32 microphone PCM capture via winmm.dll (strictly RAM-only)."""

from __future__ import annotations

import array
import ctypes
import io
import logging
import math
import sys
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)

WAVE_FORMAT_PCM = 1
WAVE_MAPPER = 0xFFFFFFFF
CALLBACK_EVENT = 0x00050000
WHDR_DONE = 0x00000001
MMSYSERR_NOERROR = 0


def compute_pcm16_rms(pcm_bytes: bytes) -> float:
    """Return normalized perceptual RMS energy in [0.0, 1.0] for 16-bit signed LE PCM."""
    if len(pcm_bytes) < 2:
        return 0.0
    usable = len(pcm_bytes) - (len(pcm_bytes) % 2)
    samples = array.array("h")
    samples.frombytes(pcm_bytes[:usable])
    if sys.byteorder != "little":
        samples.byteswap()
    count = len(samples)
    if count == 0:
        return 0.0
    mean_sq = sum(s * s for s in samples) / count
    raw_rms = math.sqrt(mean_sq) / 32768.0
    if raw_rms <= 0.0:
        return 0.0
    # Soft logarithmic boost so normal speaking levels animate cleanly in [0.05..0.95]
    return max(0.0, min(1.0, math.pow(raw_rms, 0.55) * 1.35))


def is_audio_capture_supported() -> bool:
    """Return True when real-time WinMM audio capture is available on this platform."""
    return sys.platform == "win32"


if sys.platform == "win32":
    from ctypes import wintypes

    class WAVEFORMATEX(ctypes.Structure):
        _fields_ = [
            ("wFormatTag", wintypes.WORD),
            ("nChannels", wintypes.WORD),
            ("nSamplesPerSec", wintypes.DWORD),
            ("nAvgBytesPerSec", wintypes.DWORD),
            ("nBlockAlign", wintypes.WORD),
            ("wBitsPerSample", wintypes.WORD),
            ("cbSize", wintypes.WORD),
        ]

    class WAVEHDR(ctypes.Structure):
        _fields_ = [
            ("lpData", ctypes.POINTER(ctypes.c_char)),
            ("dwBufferLength", wintypes.DWORD),
            ("dwBytesRecorded", wintypes.DWORD),
            ("dwUser", ctypes.c_size_t),
            ("dwFlags", wintypes.DWORD),
            ("dwLoops", wintypes.DWORD),
            ("lpNext", ctypes.c_void_p),
            ("reserved", ctypes.c_size_t),
        ]

    class WAVEINCAPSW(ctypes.Structure):
        _fields_ = [
            ("wMid", wintypes.WORD),
            ("wPid", wintypes.WORD),
            ("vDriverVersion", wintypes.UINT),
            ("szPname", wintypes.WCHAR * 32),
            ("dwFormats", wintypes.DWORD),
            ("wChannels", wintypes.WORD),
            ("wReserved1", wintypes.WORD),
        ]


def _configure_winmm(winmm: ctypes.WinDLL) -> None:
    """Configure explicit 64-bit safe argtypes on WinMM waveIn symbols."""
    from ctypes import wintypes

    h_type = ctypes.c_void_p
    winmm.waveInGetNumDevs.argtypes = []
    winmm.waveInGetNumDevs.restype = wintypes.UINT
    winmm.waveInGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.POINTER(WAVEINCAPSW), wintypes.UINT]
    winmm.waveInGetDevCapsW.restype = wintypes.UINT
    winmm.waveInOpen.argtypes = [
        ctypes.POINTER(h_type),
        wintypes.UINT,
        ctypes.POINTER(WAVEFORMATEX),
        ctypes.c_size_t,
        ctypes.c_size_t,
        wintypes.DWORD,
    ]
    winmm.waveInOpen.restype = wintypes.UINT
    for fn_name in ("waveInPrepareHeader", "waveInUnprepareHeader", "waveInAddBuffer"):
        fn = getattr(winmm, fn_name)
        fn.argtypes = [h_type, ctypes.POINTER(WAVEHDR), wintypes.UINT]
        fn.restype = wintypes.UINT
    for fn_name in ("waveInStart", "waveInStop", "waveInReset", "waveInClose"):
        fn = getattr(winmm, fn_name)
        fn.argtypes = [h_type]
        fn.restype = wintypes.UINT


def list_input_devices() -> list[tuple[int, str]]:
    """Enumerate available Windows audio capture devices as (device_id, name)."""
    if sys.platform != "win32":
        return []
    try:
        winmm = ctypes.WinDLL("winmm", use_last_error=True)
        _configure_winmm(winmm)
        count = int(winmm.waveInGetNumDevs())
        devices: list[tuple[int, str]] = []
        for idx in range(count):
            caps = WAVEINCAPSW()
            if winmm.waveInGetDevCapsW(idx, ctypes.byref(caps), ctypes.sizeof(WAVEINCAPSW)) == MMSYSERR_NOERROR:
                name = str(caps.szPname).strip() or f"Microphone #{idx + 1}"
                devices.append((idx, name))
        return devices
    except Exception as exc:  # noqa: BLE001
        log.debug("Failed to list input devices: %s", exc)
        return []


class MicrophoneCapture:
    """Streams 16kHz mono 16-bit PCM strictly into RAM with live RMS metering."""

    def __init__(
        self,
        device_id: int = -1,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_ms: int = 50,
        num_buffers: int = 4,
        on_chunk: Callable[[bytes, float], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.device_id = int(device_id)
        self.sample_rate = int(sample_rate)
        self.channels = int(channels)
        self.bits_per_sample = 16
        self.chunk_bytes = max(320, int(self.sample_rate * self.channels * 2 * (chunk_ms / 1000.0)))
        self.num_buffers = max(2, int(num_buffers))
        self.on_chunk = on_chunk
        self.on_error = on_error

        self._lock = threading.Lock()
        self._active = False
        self._stop_event = threading.Event()
        self._buffer = io.BytesIO()
        self._latest_rms = 0.0
        self._last_error = ""
        self._thread: threading.Thread | None = None

        self._winmm: ctypes.WinDLL | None = None
        self._kernel32: ctypes.WinDLL | None = None
        self._h_wavein: ctypes.c_void_p | None = None
        self._h_event: ctypes.c_void_p | None = None
        self._headers: list[WAVEHDR] = []
        self._raw_bufs: list[ctypes.Array[ctypes.c_char]] = []

    @property
    def is_recording(self) -> bool:
        return self._active

    @property
    def latest_rms(self) -> float:
        return self._latest_rms

    @property
    def last_error(self) -> str:
        return self._last_error

    def start(self) -> bool:
        """Open Windows audio input device and begin streaming PCM chunks in RAM."""
        with self._lock:
            if self._active:
                return True
            self._last_error = ""
            self._latest_rms = 0.0
            self._buffer = io.BytesIO()
            self._stop_event.clear()

            if sys.platform != "win32":
                self._last_error = "WinMM audio capture requires Windows"
                return False

            try:
                winmm = ctypes.WinDLL("winmm", use_last_error=True)
                _configure_winmm(winmm)
                kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
                kernel32.CreateEventW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_bool, ctypes.c_wchar_p]
                kernel32.CreateEventW.restype = ctypes.c_void_p
                kernel32.SetEvent.argtypes = [ctypes.c_void_p]
                kernel32.SetEvent.restype = ctypes.c_bool
                kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint]
                kernel32.WaitForSingleObject.restype = ctypes.c_uint
                kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
                kernel32.CloseHandle.restype = ctypes.c_bool

                if int(winmm.waveInGetNumDevs()) == 0:
                    self._last_error = "No microphone input device detected"
                    return False

                h_event = kernel32.CreateEventW(None, False, False, None)
                if not h_event:
                    self._last_error = "Could not allocate audio synchronization event"
                    return False

                block_align = self.channels * (self.bits_per_sample // 8)
                wfx = WAVEFORMATEX(
                    wFormatTag=WAVE_FORMAT_PCM,
                    nChannels=self.channels,
                    nSamplesPerSec=self.sample_rate,
                    nAvgBytesPerSec=self.sample_rate * block_align,
                    nBlockAlign=block_align,
                    wBitsPerSample=self.bits_per_sample,
                    cbSize=0,
                )
                dev = WAVE_MAPPER if self.device_id < 0 else self.device_id
                h_wave = ctypes.c_void_p()
                res = winmm.waveInOpen(
                    ctypes.byref(h_wave),
                    dev,
                    ctypes.byref(wfx),
                    ctypes.cast(h_event, ctypes.c_void_p).value or 0,
                    0,
                    CALLBACK_EVENT,
                )
                if res != MMSYSERR_NOERROR or not h_wave.value:
                    kernel32.CloseHandle(h_event)
                    self._last_error = f"waveInOpen failed (code {res})"
                    return False

                self._winmm = winmm
                self._kernel32 = kernel32
                self._h_wavein = h_wave
                self._h_event = h_event
                self._headers = []
                self._raw_bufs = []

                hdr_size = ctypes.sizeof(WAVEHDR)
                for _ in range(self.num_buffers):
                    raw = ctypes.create_string_buffer(self.chunk_bytes)
                    hdr = WAVEHDR(
                        lpData=ctypes.cast(raw, ctypes.POINTER(ctypes.c_char)),
                        dwBufferLength=self.chunk_bytes,
                    )
                    if winmm.waveInPrepareHeader(h_wave, ctypes.byref(hdr), hdr_size) != MMSYSERR_NOERROR:
                        raise RuntimeError("waveInPrepareHeader failed")
                    if winmm.waveInAddBuffer(h_wave, ctypes.byref(hdr), hdr_size) != MMSYSERR_NOERROR:
                        raise RuntimeError("waveInAddBuffer failed")
                    self._raw_bufs.append(raw)
                    self._headers.append(hdr)

                if winmm.waveInStart(h_wave) != MMSYSERR_NOERROR:
                    raise RuntimeError("waveInStart failed")

                self._active = True
                self._thread = threading.Thread(target=self._capture_loop, name="RavaanMicCapture", daemon=True)
                self._thread.start()
                log.info("WinMM microphone capture started (%d Hz, %d ch)", self.sample_rate, self.channels)
                return True
            except Exception as exc:  # noqa: BLE001
                self._last_error = str(exc)
                log.warning("Microphone capture failed to start: %s", exc)
                if self.on_error:
                    try:
                        self.on_error(self._last_error)
                    except Exception:
                        pass
                self._cleanup_handles()
                return False

    def _capture_loop(self) -> None:
        winmm = self._winmm
        kernel32 = self._kernel32
        h_wave = self._h_wavein
        h_event = self._h_event
        if winmm is None or kernel32 is None or h_wave is None or h_event is None:
            return
        hdr_size = ctypes.sizeof(WAVEHDR)
        while not self._stop_event.is_set():
            kernel32.WaitForSingleObject(h_event, 100)
            for hdr, raw in zip(self._headers, self._raw_bufs, strict=True):
                if hdr.dwFlags & WHDR_DONE:
                    recorded = int(hdr.dwBytesRecorded)
                    if recorded > 0:
                        chunk = bytes(raw.raw[:recorded])
                        rms = compute_pcm16_rms(chunk)
                        self._latest_rms = rms
                        with self._lock:
                            if self._active:
                                self._buffer.write(chunk)
                        if self.on_chunk is not None:
                            try:
                                self.on_chunk(chunk, rms)
                            except Exception:
                                pass
                    if not self._stop_event.is_set() and self._active:
                        hdr.dwBytesRecorded = 0
                        hdr.dwFlags &= ~WHDR_DONE
                        winmm.waveInAddBuffer(h_wave, ctypes.byref(hdr), hdr_size)

    def stop(self) -> bytes:
        """Stop capturing, release WinMM handles, return PCM bytes and wipe RAM buffer."""
        with self._lock:
            was_active = self._active
            self._active = False
            self._stop_event.set()
            if self._kernel32 is not None and self._h_event is not None:
                try:
                    self._kernel32.SetEvent(self._h_event)
                except Exception:
                    pass
            thread = self._thread
            self._thread = None

        if was_active and self._winmm is not None and self._h_wavein is not None:
            try:
                self._winmm.waveInStop(self._h_wavein)
                self._winmm.waveInReset(self._h_wavein)
            except Exception:
                pass

        if thread is not None and thread.is_alive():
            thread.join(timeout=1.0)

        self._cleanup_handles()
        with self._lock:
            pcm_data = self._buffer.getvalue()
            self._buffer.close()
            self._buffer = io.BytesIO()
            self._latest_rms = 0.0
            return pcm_data

    def _cleanup_handles(self) -> None:
        winmm = self._winmm
        kernel32 = self._kernel32
        h_wave = self._h_wavein
        h_event = self._h_event
        if winmm is not None and h_wave is not None:
            hdr_size = ctypes.sizeof(WAVEHDR)
            for hdr in self._headers:
                try:
                    winmm.waveInUnprepareHeader(h_wave, ctypes.byref(hdr), hdr_size)
                except Exception:
                    pass
            try:
                winmm.waveInClose(h_wave)
            except Exception:
                pass
        if kernel32 is not None and h_event is not None:
            try:
                kernel32.CloseHandle(h_event)
            except Exception:
                pass
        self._headers = []
        self._raw_bufs = []
        self._h_wavein = None
        self._h_event = None
        self._winmm = None
        self._kernel32 = None
