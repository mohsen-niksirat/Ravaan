"""Cross-platform and mocked Win32 WinMM microphone capture tests (zero disk leak)."""

from __future__ import annotations

import array
import ctypes
import math
from unittest.mock import MagicMock, patch

from ravan.platform import audio as audio_mod


def _sine_pcm16(freq_hz: float = 440.0, duration_s: float = 0.05, sample_rate: int = 16000, amp: float = 0.4) -> bytes:
    n = int(sample_rate * duration_s)
    samples = array.array(
        "h",
        (int(32767 * amp * math.sin(2.0 * math.pi * freq_hz * i / sample_rate)) for i in range(n)),
    )
    return samples.tobytes()


def test_compute_pcm16_rms_bounds_and_silence() -> None:
    assert audio_mod.compute_pcm16_rms(b"") == 0.0
    assert audio_mod.compute_pcm16_rms(b"\x00") == 0.0
    assert audio_mod.compute_pcm16_rms(b"\x00\x00" * 160) == 0.0

    quiet = audio_mod.compute_pcm16_rms(_sine_pcm16(amp=0.05))
    loud = audio_mod.compute_pcm16_rms(_sine_pcm16(amp=0.80))
    assert 0.05 < quiet < loud <= 1.0


def test_non_windows_microphone_capture_safe_fallback() -> None:
    with patch.object(audio_mod.sys, "platform", "linux"):
        assert audio_mod.is_audio_capture_supported() is False
        assert audio_mod.list_input_devices() == []
        cap = audio_mod.MicrophoneCapture()
        assert cap.start() is False
        assert cap.is_recording is False
        assert cap.stop() == b""


def test_list_input_devices_mocked_winmm() -> None:
    fake_winmm = MagicMock()
    fake_winmm.waveInGetNumDevs.return_value = 2

    def _get_caps(idx, ptr_caps, _sz):
        caps = ctypes.cast(ptr_caps, ctypes.POINTER(audio_mod.WAVEINCAPSW)).contents
        caps.szPname = "USB Studio Mic" if idx == 0 else "Laptop Array"
        return audio_mod.MMSYSERR_NOERROR

    fake_winmm.waveInGetDevCapsW.side_effect = _get_caps
    with (
        patch.object(audio_mod.sys, "platform", "win32"),
        patch.object(audio_mod.ctypes, "WinDLL", return_value=fake_winmm),
    ):
        devs = audio_mod.list_input_devices()
        assert devs == [(0, "USB Studio Mic"), (1, "Laptop Array")]


def test_microphone_capture_winmm_stream_and_ram_cleanup(tmp_path) -> None:
    if audio_mod.sys.platform != "win32":
        return

    pcm_sample = _sine_pcm16(duration_s=0.02, amp=0.5)
    received: list[tuple[int, float]] = []

    fake_winmm = MagicMock()
    fake_winmm.waveInGetNumDevs.return_value = 1

    def _open(h_ptr, _dev, _wfx, _cb, _inst, _flags):
        ctypes.cast(h_ptr, ctypes.POINTER(ctypes.c_void_p)).contents.value = 0x1234
        return audio_mod.MMSYSERR_NOERROR

    queued_hdrs: list = []

    def _prep(_h, hdr_ptr, _sz):
        return audio_mod.MMSYSERR_NOERROR

    def _add(_h, hdr_ptr, _sz):
        hdr = ctypes.cast(hdr_ptr, ctypes.POINTER(audio_mod.WAVEHDR)).contents
        queued_hdrs.append(hdr)
        return audio_mod.MMSYSERR_NOERROR

    injected = {"done": False}

    def _start(_h):
        return audio_mod.MMSYSERR_NOERROR

    fake_winmm.waveInOpen.side_effect = _open
    fake_winmm.waveInPrepareHeader.side_effect = _prep
    fake_winmm.waveInAddBuffer.side_effect = _add
    fake_winmm.waveInStart.side_effect = _start
    fake_winmm.waveInStop.return_value = audio_mod.MMSYSERR_NOERROR
    fake_winmm.waveInReset.return_value = audio_mod.MMSYSERR_NOERROR
    fake_winmm.waveInUnprepareHeader.return_value = audio_mod.MMSYSERR_NOERROR
    fake_winmm.waveInClose.return_value = audio_mod.MMSYSERR_NOERROR

    fake_kernel = MagicMock()
    fake_kernel.CreateEventW.return_value = 0x5678
    fake_kernel.SetEvent.return_value = True
    fake_kernel.CloseHandle.return_value = True

    def _wait(_ev, _ms):
        if not injected["done"] and queued_hdrs:
            hdr = queued_hdrs[0]
            ctypes.memmove(hdr.lpData, pcm_sample, len(pcm_sample))
            hdr.dwBytesRecorded = len(pcm_sample)
            hdr.dwFlags |= audio_mod.WHDR_DONE
            injected["done"] = True
        return 0

    fake_kernel.WaitForSingleObject.side_effect = _wait

    def _win_dll(name, **_kwargs):
        return fake_winmm if name == "winmm" else fake_kernel

    cap = audio_mod.MicrophoneCapture(
        chunk_ms=20,
        num_buffers=2,
        on_chunk=lambda c, r: received.append((len(c), r)),
    )
    with patch.object(audio_mod.ctypes, "WinDLL", side_effect=_win_dll):
        assert cap.start() is True
        import time

        deadline = time.monotonic() + 1.0
        while not received and time.monotonic() < deadline:
            time.sleep(0.01)
        out_pcm = cap.stop()

    assert len(received) >= 1
    assert received[0][0] == len(pcm_sample)
    assert received[0][1] > 0.1
    assert out_pcm.startswith(pcm_sample)
    assert cap.latest_rms == 0.0
    assert cap.is_recording is False
    # Zero temp files written anywhere
    assert list(tmp_path.iterdir()) == []
