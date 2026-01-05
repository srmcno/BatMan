"""Noise reduction for bat call recordings."""

from dataclasses import dataclass
from enum import Enum
from typing import Literal

import numpy as np

from app.config import settings


class NoiseType(str, Enum):
    """Types of noise commonly found in bat recordings."""

    INSECT = "insect"
    WIND = "wind"
    RAIN = "rain"
    MECHANICAL = "mechanical"
    TRAFFIC = "traffic"
    UNKNOWN = "unknown"


@dataclass
class NoiseProfile:
    """Estimated noise characteristics."""

    noise_type: NoiseType
    noise_floor_db: float
    snr_estimate_db: float
    spectral_profile: np.ndarray
    temporal_variance: float


@dataclass
class DenoiseResult:
    """Result of noise reduction."""

    denoised_audio: np.ndarray
    original_snr_db: float
    improved_snr_db: float
    noise_reduction_db: float
    noise_profile: NoiseProfile
    quality_score: float


class NoiseReducer:
    """
    Noise reduction system for bat call recordings.

    Implements:
    - Noise profile estimation
    - Spectral subtraction
    - Adaptive filtering
    - Quality metrics
    """

    def __init__(
        self,
        sample_rate: int = None,
        n_fft: int = 2048,
        hop_length: int = 512,
        noise_frames: int = 10,
        oversubtraction_factor: float = 1.5,
        spectral_floor: float = 0.02,
    ):
        self.sample_rate = sample_rate or settings.sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.noise_frames = noise_frames
        self.oversubtraction_factor = oversubtraction_factor
        self.spectral_floor = spectral_floor

    def reduce_noise(
        self,
        audio: np.ndarray,
        noise_profile: NoiseProfile | None = None,
        method: Literal["spectral", "wiener", "adaptive"] = "spectral",
    ) -> DenoiseResult:
        """
        Apply noise reduction to audio.

        Args:
            audio: Input audio samples
            noise_profile: Pre-computed noise profile (optional)
            method: Noise reduction method to use

        Returns:
            DenoiseResult with denoised audio and metrics
        """
        # Estimate noise profile if not provided
        if noise_profile is None:
            noise_profile = self.estimate_noise(audio)

        # Compute original SNR
        original_snr = self._estimate_snr(audio, noise_profile)

        # Apply noise reduction
        if method == "spectral":
            denoised = self._spectral_subtraction(audio, noise_profile)
        elif method == "wiener":
            denoised = self._wiener_filter(audio, noise_profile)
        elif method == "adaptive":
            denoised = self._adaptive_filter(audio, noise_profile)
        else:
            raise ValueError(f"Unknown method: {method}")

        # Compute improved SNR
        improved_snr = self._estimate_snr(denoised, noise_profile)

        # Calculate quality score
        quality_score = self._compute_quality_score(audio, denoised, noise_profile)

        return DenoiseResult(
            denoised_audio=denoised,
            original_snr_db=original_snr,
            improved_snr_db=improved_snr,
            noise_reduction_db=improved_snr - original_snr,
            noise_profile=noise_profile,
            quality_score=quality_score,
        )

    def estimate_noise(self, audio: np.ndarray) -> NoiseProfile:
        """
        Estimate noise characteristics from audio.

        Uses the first portion of audio as noise reference,
        or finds quiet regions using VAD.
        """
        # Use first N frames as noise estimate
        noise_samples = self.noise_frames * self.hop_length
        noise_audio = audio[:min(noise_samples, len(audio) // 4)]

        # Compute noise spectrum
        noise_spectrum = self._compute_spectrum(noise_audio)
        noise_floor_db = float(10 * np.log10(np.mean(noise_spectrum) + 1e-10))

        # Estimate SNR
        signal_spectrum = self._compute_spectrum(audio)
        signal_power = np.mean(signal_spectrum)
        noise_power = np.mean(noise_spectrum)
        snr_db = float(10 * np.log10(signal_power / (noise_power + 1e-10)))

        # Classify noise type based on spectral shape
        noise_type = self._classify_noise(noise_spectrum)

        # Compute temporal variance
        temporal_variance = float(np.var(audio[:noise_samples]))

        return NoiseProfile(
            noise_type=noise_type,
            noise_floor_db=noise_floor_db,
            snr_estimate_db=snr_db,
            spectral_profile=noise_spectrum,
            temporal_variance=temporal_variance,
        )

    def _compute_spectrum(self, audio: np.ndarray) -> np.ndarray:
        """Compute average power spectrum."""
        window = np.hanning(self.n_fft)
        n_frames = max(1, (len(audio) - self.n_fft) // self.hop_length)

        spectrum = np.zeros(self.n_fft // 2 + 1)

        for i in range(n_frames):
            start = i * self.hop_length
            frame = audio[start:start + self.n_fft]

            if len(frame) < self.n_fft:
                frame = np.pad(frame, (0, self.n_fft - len(frame)))

            fft = np.fft.rfft(frame * window)
            spectrum += np.abs(fft) ** 2

        return spectrum / max(n_frames, 1)

    def _classify_noise(self, noise_spectrum: np.ndarray) -> NoiseType:
        """Classify noise type from spectral shape."""
        freqs = np.linspace(0, self.sample_rate / 2, len(noise_spectrum))

        # High-frequency energy (insect noise)
        high_freq_mask = freqs > 50000
        high_freq_energy = np.mean(noise_spectrum[high_freq_mask]) if any(high_freq_mask) else 0

        # Low-frequency energy (wind, traffic)
        low_freq_mask = freqs < 5000
        low_freq_energy = np.mean(noise_spectrum[low_freq_mask]) if any(low_freq_mask) else 0

        # Mid-frequency energy
        mid_freq_mask = (freqs >= 5000) & (freqs <= 50000)
        mid_freq_energy = np.mean(noise_spectrum[mid_freq_mask]) if any(mid_freq_mask) else 0

        total_energy = high_freq_energy + low_freq_energy + mid_freq_energy + 1e-10

        # Classify based on energy distribution
        if high_freq_energy / total_energy > 0.5:
            return NoiseType.INSECT
        elif low_freq_energy / total_energy > 0.6:
            # Check for periodic patterns (mechanical)
            spectrum_diff = np.diff(noise_spectrum)
            if np.std(spectrum_diff) > np.mean(spectrum_diff) * 2:
                return NoiseType.MECHANICAL
            return NoiseType.WIND
        else:
            return NoiseType.UNKNOWN

    def _spectral_subtraction(
        self, audio: np.ndarray, noise_profile: NoiseProfile
    ) -> np.ndarray:
        """
        Apply spectral subtraction noise reduction.

        Based on Boll (1979) spectral subtraction with modifications.
        """
        window = np.hanning(self.n_fft)
        n_frames = 1 + (len(audio) - self.n_fft) // self.hop_length

        # Output buffer
        output = np.zeros(len(audio))
        window_sum = np.zeros(len(audio))

        for i in range(n_frames):
            start = i * self.hop_length
            frame = audio[start:start + self.n_fft]

            if len(frame) < self.n_fft:
                frame = np.pad(frame, (0, self.n_fft - len(frame)))

            # STFT
            fft = np.fft.rfft(frame * window)
            magnitude = np.abs(fft)
            phase = np.angle(fft)

            # Spectral subtraction
            noise_mag = np.sqrt(noise_profile.spectral_profile)

            # Apply oversubtraction
            subtracted = magnitude ** 2 - self.oversubtraction_factor * noise_profile.spectral_profile

            # Apply spectral floor
            floor = self.spectral_floor * noise_profile.spectral_profile
            subtracted = np.maximum(subtracted, floor)

            # Reconstruct
            new_magnitude = np.sqrt(subtracted)
            new_fft = new_magnitude * np.exp(1j * phase)

            # Inverse FFT
            frame_out = np.fft.irfft(new_fft)

            # Overlap-add
            end = min(start + self.n_fft, len(output))
            output[start:end] += frame_out[:end - start] * window[:end - start]
            window_sum[start:end] += window[:end - start] ** 2

        # Normalize by window sum
        window_sum = np.maximum(window_sum, 1e-10)
        output /= window_sum

        return output

    def _wiener_filter(
        self, audio: np.ndarray, noise_profile: NoiseProfile
    ) -> np.ndarray:
        """Apply Wiener filter for noise reduction."""
        window = np.hanning(self.n_fft)
        n_frames = 1 + (len(audio) - self.n_fft) // self.hop_length

        output = np.zeros(len(audio))
        window_sum = np.zeros(len(audio))

        for i in range(n_frames):
            start = i * self.hop_length
            frame = audio[start:start + self.n_fft]

            if len(frame) < self.n_fft:
                frame = np.pad(frame, (0, self.n_fft - len(frame)))

            fft = np.fft.rfft(frame * window)
            power = np.abs(fft) ** 2

            # Wiener gain
            noise_power = noise_profile.spectral_profile
            gain = np.maximum(power - noise_power, 0) / (power + 1e-10)
            gain = np.clip(gain, 0.1, 1.0)  # Prevent complete suppression

            # Apply gain
            new_fft = fft * gain
            frame_out = np.fft.irfft(new_fft)

            end = min(start + self.n_fft, len(output))
            output[start:end] += frame_out[:end - start] * window[:end - start]
            window_sum[start:end] += window[:end - start] ** 2

        window_sum = np.maximum(window_sum, 1e-10)
        output /= window_sum

        return output

    def _adaptive_filter(
        self, audio: np.ndarray, noise_profile: NoiseProfile
    ) -> np.ndarray:
        """Apply adaptive noise reduction based on noise type."""
        noise_type = noise_profile.noise_type

        if noise_type == NoiseType.INSECT:
            # Use notch filtering for tonal insect noise
            denoised = self._notch_filter(audio, noise_profile)
        elif noise_type == NoiseType.WIND:
            # High-pass filter for wind noise
            denoised = self._highpass_filter(audio, cutoff=5000)
        elif noise_type == NoiseType.MECHANICAL:
            # Comb filter for periodic mechanical noise
            denoised = self._spectral_subtraction(audio, noise_profile)
        else:
            # Default to spectral subtraction
            denoised = self._spectral_subtraction(audio, noise_profile)

        return denoised

    def _notch_filter(
        self, audio: np.ndarray, noise_profile: NoiseProfile
    ) -> np.ndarray:
        """Apply notch filter at detected tonal frequencies."""
        # Find peaks in noise spectrum (tonal components)
        spectrum = noise_profile.spectral_profile
        freqs = np.linspace(0, self.sample_rate / 2, len(spectrum))

        # Simple peak detection
        threshold = np.mean(spectrum) * 3
        peaks = np.where(spectrum > threshold)[0]

        # Apply spectral subtraction with enhanced suppression at peaks
        enhanced_noise = noise_profile.spectral_profile.copy()
        enhanced_noise[peaks] *= 2  # Increase suppression at tonal frequencies

        modified_profile = NoiseProfile(
            noise_type=noise_profile.noise_type,
            noise_floor_db=noise_profile.noise_floor_db,
            snr_estimate_db=noise_profile.snr_estimate_db,
            spectral_profile=enhanced_noise,
            temporal_variance=noise_profile.temporal_variance,
        )

        return self._spectral_subtraction(audio, modified_profile)

    def _highpass_filter(self, audio: np.ndarray, cutoff: float) -> np.ndarray:
        """Apply simple high-pass filter."""
        try:
            from scipy.signal import butter, filtfilt

            nyquist = self.sample_rate / 2
            normalized_cutoff = cutoff / nyquist
            b, a = butter(4, normalized_cutoff, btype="high")
            return filtfilt(b, a, audio)
        except ImportError:
            # FFT-based fallback
            fft = np.fft.rfft(audio)
            freqs = np.fft.rfftfreq(len(audio), 1 / self.sample_rate)
            fft[freqs < cutoff] *= 0.1
            return np.fft.irfft(fft, len(audio))

    def _estimate_snr(self, audio: np.ndarray, noise_profile: NoiseProfile) -> float:
        """Estimate SNR of audio given noise profile."""
        signal_power = np.mean(audio ** 2)
        noise_power = np.mean(noise_profile.spectral_profile)

        if noise_power > 0:
            snr = 10 * np.log10(signal_power / noise_power)
        else:
            snr = 60.0

        return float(np.clip(snr, -20, 60))

    def _compute_quality_score(
        self,
        original: np.ndarray,
        denoised: np.ndarray,
        noise_profile: NoiseProfile,
    ) -> float:
        """
        Compute quality score for denoised audio.

        Considers:
        - SNR improvement
        - Signal preservation
        - Artifact reduction
        """
        # SNR improvement (normalized)
        original_snr = self._estimate_snr(original, noise_profile)
        denoised_snr = self._estimate_snr(denoised, noise_profile)
        snr_improvement = min((denoised_snr - original_snr) / 20, 1.0)

        # Signal correlation (preservation)
        correlation = np.corrcoef(original, denoised)[0, 1]
        preservation = max(correlation, 0)

        # Spectral distortion
        orig_spec = self._compute_spectrum(original)
        denoised_spec = self._compute_spectrum(denoised)
        spectral_corr = np.corrcoef(orig_spec, denoised_spec)[0, 1]
        distortion = max(spectral_corr, 0)

        # Combined score
        score = 0.4 * snr_improvement + 0.3 * preservation + 0.3 * distortion

        return float(np.clip(score, 0, 1))
