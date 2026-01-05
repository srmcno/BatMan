"""Audio processing pipeline for bat call analysis."""

from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import numpy as np

from app.config import settings


@dataclass
class AudioSegment:
    """Represents a detected audio segment (potential bat call)."""

    start_sample: int
    end_sample: int
    start_time_ms: float
    end_time_ms: float
    duration_ms: float
    peak_amplitude: float
    snr_db: float
    audio_data: np.ndarray


@dataclass
class AudioMetadata:
    """Metadata extracted from audio file."""

    duration_seconds: float
    sample_rate: int
    channels: int
    bit_depth: int
    file_size_bytes: int


class AudioProcessor:
    """
    Audio processing pipeline for bat call detection and analysis.

    Handles:
    - Audio file loading (WAV, WAC, ZC formats)
    - Resampling to target sample rate
    - Call detection using energy-based thresholding
    - Segment extraction for classification
    """

    def __init__(
        self,
        sample_rate: int = None,
        min_call_duration_ms: float = 1.0,
        max_call_duration_ms: float = 50.0,
        min_call_gap_ms: float = 5.0,
        detection_threshold_db: float = -40.0,
    ):
        self.sample_rate = sample_rate or settings.sample_rate
        self.min_call_duration_ms = min_call_duration_ms
        self.max_call_duration_ms = max_call_duration_ms
        self.min_call_gap_ms = min_call_gap_ms
        self.detection_threshold_db = detection_threshold_db

        # Pre-compute sample counts
        self.min_call_samples = int(min_call_duration_ms * self.sample_rate / 1000)
        self.max_call_samples = int(max_call_duration_ms * self.sample_rate / 1000)
        self.min_gap_samples = int(min_call_gap_ms * self.sample_rate / 1000)

    def load_audio(self, file_path: str | Path) -> tuple[np.ndarray, AudioMetadata]:
        """
        Load audio file and return samples with metadata.

        Supports WAV, WAC (Wildlife Acoustics), and ZC (zero-crossing) formats.
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        suffix = file_path.suffix.lower()

        if suffix == ".wav":
            audio, metadata = self._load_wav(file_path)
        elif suffix == ".wac":
            audio, metadata = self._load_wac(file_path)
        elif suffix == ".zc":
            audio, metadata = self._load_zc(file_path)
        else:
            raise ValueError(f"Unsupported audio format: {suffix}")

        # Resample if necessary
        if metadata.sample_rate != self.sample_rate:
            audio = self._resample(audio, metadata.sample_rate, self.sample_rate)
            metadata.sample_rate = self.sample_rate

        # Convert to mono if stereo
        if len(audio.shape) > 1 and audio.shape[1] > 1:
            audio = np.mean(audio, axis=1)

        # Normalize to [-1, 1]
        max_val = np.max(np.abs(audio))
        if max_val > 0:
            audio = audio / max_val

        metadata.duration_seconds = len(audio) / self.sample_rate

        return audio, metadata

    def _load_wav(self, file_path: Path) -> tuple[np.ndarray, AudioMetadata]:
        """Load WAV file using scipy."""
        try:
            from scipy.io import wavfile
            sample_rate, audio = wavfile.read(file_path)

            # Convert to float
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            elif audio.dtype == np.int32:
                audio = audio.astype(np.float32) / 2147483648.0
            elif audio.dtype == np.uint8:
                audio = (audio.astype(np.float32) - 128) / 128.0

            metadata = AudioMetadata(
                duration_seconds=len(audio) / sample_rate,
                sample_rate=sample_rate,
                channels=1 if len(audio.shape) == 1 else audio.shape[1],
                bit_depth=16,
                file_size_bytes=file_path.stat().st_size,
            )

            return audio, metadata

        except ImportError:
            # Fallback to basic WAV reading
            return self._load_wav_basic(file_path)

    def _load_wav_basic(self, file_path: Path) -> tuple[np.ndarray, AudioMetadata]:
        """Basic WAV loading without scipy."""
        import struct
        import wave

        with wave.open(str(file_path), "rb") as wav:
            sample_rate = wav.getframerate()
            n_channels = wav.getnchannels()
            sample_width = wav.getsampwidth()
            n_frames = wav.getnframes()

            raw_data = wav.readframes(n_frames)

            if sample_width == 2:
                audio = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32) / 32768.0
            elif sample_width == 1:
                audio = (np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128) / 128.0
            else:
                raise ValueError(f"Unsupported sample width: {sample_width}")

            if n_channels > 1:
                audio = audio.reshape(-1, n_channels)

            metadata = AudioMetadata(
                duration_seconds=n_frames / sample_rate,
                sample_rate=sample_rate,
                channels=n_channels,
                bit_depth=sample_width * 8,
                file_size_bytes=file_path.stat().st_size,
            )

            return audio, metadata

    def _load_wac(self, file_path: Path) -> tuple[np.ndarray, AudioMetadata]:
        """Load Wildlife Acoustics WAC format."""
        # WAC is a proprietary format - this is a placeholder
        # In production, would use Wildlife Acoustics SDK or kaleidoscope
        raise NotImplementedError("WAC format requires Wildlife Acoustics SDK")

    def _load_zc(self, file_path: Path) -> tuple[np.ndarray, AudioMetadata]:
        """Load Anabat zero-crossing format."""
        # ZC format contains timing of zero crossings, not raw audio
        # Would need to reconstruct approximate waveform
        raise NotImplementedError("ZC format support coming soon")

    def _resample(
        self, audio: np.ndarray, orig_sr: int, target_sr: int
    ) -> np.ndarray:
        """Resample audio to target sample rate."""
        try:
            from scipy import signal
            duration = len(audio) / orig_sr
            target_length = int(duration * target_sr)
            return signal.resample(audio, target_length)
        except ImportError:
            # Simple linear interpolation fallback
            duration = len(audio) / orig_sr
            target_length = int(duration * target_sr)
            indices = np.linspace(0, len(audio) - 1, target_length)
            return np.interp(indices, np.arange(len(audio)), audio)

    def detect_calls(self, audio: np.ndarray) -> list[AudioSegment]:
        """
        Detect bat calls in audio using energy-based thresholding.

        Uses a bandpass filter for bat frequencies and envelope detection.
        """
        # Apply bandpass filter for bat frequencies (10-150 kHz)
        filtered = self._bandpass_filter(
            audio,
            lowcut=settings.fmin,
            highcut=settings.fmax,
            sample_rate=self.sample_rate,
        )

        # Compute envelope using Hilbert transform
        envelope = self._compute_envelope(filtered)

        # Convert threshold to linear scale
        threshold = 10 ** (self.detection_threshold_db / 20)

        # Find regions above threshold
        above_threshold = envelope > threshold

        # Find call boundaries
        segments = []
        in_call = False
        call_start = 0
        last_call_end = 0

        for i, is_above in enumerate(above_threshold):
            if is_above and not in_call:
                # Check minimum gap from previous call
                if i - last_call_end >= self.min_gap_samples:
                    in_call = True
                    call_start = i
            elif not is_above and in_call:
                in_call = False
                call_end = i

                # Check duration constraints
                duration = call_end - call_start
                if self.min_call_samples <= duration <= self.max_call_samples:
                    # Extract segment with padding
                    pad = int(self.sample_rate * 0.005)  # 5ms padding
                    seg_start = max(0, call_start - pad)
                    seg_end = min(len(audio), call_end + pad)

                    segment = AudioSegment(
                        start_sample=call_start,
                        end_sample=call_end,
                        start_time_ms=call_start / self.sample_rate * 1000,
                        end_time_ms=call_end / self.sample_rate * 1000,
                        duration_ms=duration / self.sample_rate * 1000,
                        peak_amplitude=float(np.max(np.abs(audio[call_start:call_end]))),
                        snr_db=self._estimate_snr(audio, call_start, call_end),
                        audio_data=audio[seg_start:seg_end].copy(),
                    )
                    segments.append(segment)

                last_call_end = call_end

        return segments

    def _bandpass_filter(
        self,
        audio: np.ndarray,
        lowcut: float,
        highcut: float,
        sample_rate: int,
        order: int = 5,
    ) -> np.ndarray:
        """Apply bandpass filter to audio."""
        try:
            from scipy.signal import butter, filtfilt

            nyquist = sample_rate / 2
            low = lowcut / nyquist
            high = min(highcut / nyquist, 0.99)  # Avoid aliasing

            b, a = butter(order, [low, high], btype="band")
            return filtfilt(b, a, audio)

        except ImportError:
            # Simple FFT-based filter fallback
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1 / sample_rate)
            mask = (freqs >= lowcut) & (freqs <= highcut)
            fft[~mask] = 0
            return np.fft.irfft(fft, len(audio))

    def _compute_envelope(self, audio: np.ndarray) -> np.ndarray:
        """Compute amplitude envelope using Hilbert transform."""
        try:
            from scipy.signal import hilbert
            analytic = hilbert(audio)
            return np.abs(analytic)
        except ImportError:
            # Simple moving average envelope
            window = int(self.sample_rate * 0.001)  # 1ms window
            kernel = np.ones(window) / window
            return np.convolve(np.abs(audio), kernel, mode="same")

    def _estimate_snr(
        self, audio: np.ndarray, call_start: int, call_end: int
    ) -> float:
        """Estimate SNR for a detected call."""
        # Signal power (call region)
        signal = audio[call_start:call_end]
        signal_power = np.mean(signal ** 2)

        # Noise power (regions before/after call)
        noise_samples = min(len(signal), 1000)
        noise_before = audio[max(0, call_start - noise_samples):call_start]
        noise_after = audio[call_end:min(len(audio), call_end + noise_samples)]

        if len(noise_before) > 0 and len(noise_after) > 0:
            noise = np.concatenate([noise_before, noise_after])
            noise_power = np.mean(noise ** 2)
        elif len(noise_before) > 0:
            noise_power = np.mean(noise_before ** 2)
        elif len(noise_after) > 0:
            noise_power = np.mean(noise_after ** 2)
        else:
            noise_power = 1e-10

        if noise_power > 0:
            snr = 10 * np.log10(signal_power / noise_power)
        else:
            snr = 60.0  # Max reasonable SNR

        return float(np.clip(snr, -20, 60))

    def process_file(
        self, file_path: str | Path
    ) -> tuple[list[AudioSegment], AudioMetadata]:
        """
        Process an audio file: load, detect calls, and return segments.

        Returns:
            Tuple of (list of detected call segments, audio metadata)
        """
        audio, metadata = self.load_audio(file_path)
        segments = self.detect_calls(audio)
        return segments, metadata
