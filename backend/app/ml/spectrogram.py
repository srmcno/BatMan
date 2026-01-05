"""Spectrogram generation for bat call visualization and classification."""

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from app.config import settings


@dataclass
class SpectrogramResult:
    """Result of spectrogram generation."""

    spectrogram: np.ndarray  # 2D array (frequency x time)
    mel_spectrogram: np.ndarray  # Mel-scaled spectrogram
    frequencies: np.ndarray  # Frequency bins
    times: np.ndarray  # Time bins
    sample_rate: int
    n_fft: int
    hop_length: int


class SpectrogramGenerator:
    """
    Generate spectrograms from audio data for visualization and ML input.

    Supports:
    - Standard STFT spectrograms
    - Mel-scaled spectrograms
    - Log-power scaling
    - Multiple colormap options
    """

    def __init__(
        self,
        sample_rate: int = None,
        n_fft: int = None,
        hop_length: int = None,
        n_mels: int = None,
        fmin: float = None,
        fmax: float = None,
    ):
        self.sample_rate = sample_rate or settings.sample_rate
        self.n_fft = n_fft or settings.n_fft
        self.hop_length = hop_length or settings.hop_length
        self.n_mels = n_mels or settings.n_mels
        self.fmin = fmin or settings.fmin
        self.fmax = fmax or settings.fmax

    def generate(
        self,
        audio: np.ndarray,
        normalize: bool = True,
        log_scale: bool = True,
    ) -> SpectrogramResult:
        """
        Generate spectrogram from audio data.

        Args:
            audio: Audio samples
            normalize: Whether to normalize the spectrogram
            log_scale: Whether to apply log scaling

        Returns:
            SpectrogramResult with spectrogram data
        """
        # Compute STFT
        spectrogram = self._stft(audio)

        # Compute mel spectrogram
        mel_spectrogram = self._mel_spectrogram(spectrogram)

        # Apply log scaling
        if log_scale:
            spectrogram = self._power_to_db(spectrogram)
            mel_spectrogram = self._power_to_db(mel_spectrogram)

        # Normalize
        if normalize:
            spectrogram = self._normalize(spectrogram)
            mel_spectrogram = self._normalize(mel_spectrogram)

        # Compute frequency and time axes
        frequencies = np.linspace(0, self.sample_rate / 2, spectrogram.shape[0])
        n_frames = spectrogram.shape[1]
        times = np.arange(n_frames) * self.hop_length / self.sample_rate

        return SpectrogramResult(
            spectrogram=spectrogram,
            mel_spectrogram=mel_spectrogram,
            frequencies=frequencies,
            times=times,
            sample_rate=self.sample_rate,
            n_fft=self.n_fft,
            hop_length=self.hop_length,
        )

    def _stft(self, audio: np.ndarray) -> np.ndarray:
        """Compute Short-Time Fourier Transform."""
        # Pad audio to ensure full frames
        pad_length = self.n_fft // 2
        audio_padded = np.pad(audio, (pad_length, pad_length), mode="reflect")

        # Hann window
        window = np.hanning(self.n_fft)

        # Number of frames
        n_frames = 1 + (len(audio_padded) - self.n_fft) // self.hop_length

        # Initialize output
        spectrogram = np.zeros((self.n_fft // 2 + 1, n_frames), dtype=np.float32)

        # Compute STFT
        for i in range(n_frames):
            start = i * self.hop_length
            frame = audio_padded[start:start + self.n_fft] * window
            spectrum = np.fft.rfft(frame)
            spectrogram[:, i] = np.abs(spectrum) ** 2

        return spectrogram

    def _mel_spectrogram(self, spectrogram: np.ndarray) -> np.ndarray:
        """Convert power spectrogram to mel scale."""
        # Create mel filterbank
        mel_filters = self._mel_filterbank()

        # Apply filterbank
        mel_spec = np.dot(mel_filters, spectrogram)

        return mel_spec

    def _mel_filterbank(self) -> np.ndarray:
        """Create mel filterbank matrix."""
        # Convert Hz to mel
        def hz_to_mel(hz):
            return 2595 * np.log10(1 + hz / 700)

        def mel_to_hz(mel):
            return 700 * (10 ** (mel / 2595) - 1)

        # Mel points
        mel_low = hz_to_mel(self.fmin)
        mel_high = hz_to_mel(min(self.fmax, self.sample_rate / 2))
        mel_points = np.linspace(mel_low, mel_high, self.n_mels + 2)
        hz_points = mel_to_hz(mel_points)

        # FFT bin frequencies
        fft_freqs = np.linspace(0, self.sample_rate / 2, self.n_fft // 2 + 1)

        # Create filterbank
        filterbank = np.zeros((self.n_mels, self.n_fft // 2 + 1))

        for i in range(self.n_mels):
            # Left slope
            left = hz_points[i]
            center = hz_points[i + 1]
            right = hz_points[i + 2]

            for j, freq in enumerate(fft_freqs):
                if left <= freq < center:
                    filterbank[i, j] = (freq - left) / (center - left)
                elif center <= freq < right:
                    filterbank[i, j] = (right - freq) / (right - center)

        return filterbank

    def _power_to_db(
        self, spectrogram: np.ndarray, ref: float = 1.0, amin: float = 1e-10
    ) -> np.ndarray:
        """Convert power spectrogram to decibels."""
        spectrogram = np.maximum(spectrogram, amin)
        return 10 * np.log10(spectrogram / ref)

    def _normalize(self, spectrogram: np.ndarray) -> np.ndarray:
        """Normalize spectrogram to [0, 1] range."""
        min_val = np.min(spectrogram)
        max_val = np.max(spectrogram)

        if max_val > min_val:
            return (spectrogram - min_val) / (max_val - min_val)
        return np.zeros_like(spectrogram)

    def to_image(
        self,
        spectrogram: np.ndarray,
        colormap: Literal["viridis", "magma", "plasma", "inferno", "grayscale"] = "viridis",
        width: int = 800,
        height: int = 400,
    ) -> bytes:
        """
        Convert spectrogram to PNG image.

        Args:
            spectrogram: 2D spectrogram array (normalized to 0-1)
            colormap: Color scheme to use
            width: Output image width
            height: Output image height

        Returns:
            PNG image as bytes
        """
        try:
            import matplotlib.pyplot as plt
            from matplotlib.figure import Figure

            # Create figure
            fig = Figure(figsize=(width / 100, height / 100), dpi=100)
            ax = fig.add_subplot(111)

            # Plot spectrogram
            ax.imshow(
                spectrogram,
                aspect="auto",
                origin="lower",
                cmap=colormap if colormap != "grayscale" else "gray",
                interpolation="bilinear",
            )

            ax.set_xlabel("Time")
            ax.set_ylabel("Frequency (kHz)")
            ax.set_title("Spectrogram")

            # Save to bytes
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches="tight", pad_inches=0.1)
            buf.seek(0)

            plt.close(fig)
            return buf.getvalue()

        except ImportError:
            # Fallback: create simple grayscale PNG
            return self._create_simple_png(spectrogram, width, height)

    def _create_simple_png(
        self, spectrogram: np.ndarray, width: int, height: int
    ) -> bytes:
        """Create a simple grayscale PNG without matplotlib."""
        try:
            from PIL import Image

            # Resize spectrogram
            img_array = (spectrogram * 255).astype(np.uint8)

            # Flip vertically (origin at bottom)
            img_array = np.flipud(img_array)

            # Create image
            img = Image.fromarray(img_array, mode="L")
            img = img.resize((width, height), Image.Resampling.BILINEAR)

            # Apply colormap (simple grayscale to color)
            img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            return buf.getvalue()

        except ImportError:
            raise RuntimeError("Neither matplotlib nor PIL available for image generation")

    def to_base64(
        self,
        spectrogram: np.ndarray,
        colormap: str = "viridis",
    ) -> str:
        """Convert spectrogram to base64-encoded PNG."""
        img_bytes = self.to_image(spectrogram, colormap)
        return base64.b64encode(img_bytes).decode("utf-8")

    def save_image(
        self,
        spectrogram: np.ndarray,
        output_path: str | Path,
        colormap: str = "viridis",
        width: int = 800,
        height: int = 400,
    ) -> None:
        """Save spectrogram as image file."""
        img_bytes = self.to_image(spectrogram, colormap, width, height)
        Path(output_path).write_bytes(img_bytes)

    def generate_3d_data(self, spectrogram: np.ndarray) -> dict:
        """
        Generate data for 3D spectrogram visualization.

        Returns dict with vertices, colors, and indices for Three.js rendering.
        """
        freq_bins, time_bins = spectrogram.shape

        # Generate vertices
        vertices = []
        colors = []

        for t in range(time_bins):
            for f in range(freq_bins):
                # Position: x=time, y=frequency, z=amplitude
                x = t / time_bins
                y = f / freq_bins
                z = float(spectrogram[f, t])

                vertices.extend([x, y, z])

                # Color based on amplitude (viridis-like)
                r, g, b = self._viridis_color(z)
                colors.extend([r, g, b])

        # Generate indices for triangle mesh
        indices = []
        for t in range(time_bins - 1):
            for f in range(freq_bins - 1):
                # Two triangles per grid cell
                a = t * freq_bins + f
                b = a + freq_bins
                c = a + 1
                d = b + 1

                indices.extend([a, b, c, b, d, c])

        return {
            "vertices": vertices,
            "colors": colors,
            "indices": indices,
            "dimensions": {
                "time_bins": time_bins,
                "freq_bins": freq_bins,
            },
        }

    def _viridis_color(self, value: float) -> tuple[float, float, float]:
        """Get viridis colormap color for a value in [0, 1]."""
        # Simplified viridis approximation
        value = np.clip(value, 0, 1)

        if value < 0.25:
            t = value / 0.25
            r = 0.267 + t * (0.282 - 0.267)
            g = 0.005 + t * (0.140 - 0.005)
            b = 0.329 + t * (0.458 - 0.329)
        elif value < 0.5:
            t = (value - 0.25) / 0.25
            r = 0.282 + t * (0.127 - 0.282)
            g = 0.140 + t * (0.566 - 0.140)
            b = 0.458 + t * (0.551 - 0.458)
        elif value < 0.75:
            t = (value - 0.5) / 0.25
            r = 0.127 + t * (0.741 - 0.127)
            g = 0.566 + t * (0.873 - 0.566)
            b = 0.551 + t * (0.150 - 0.551)
        else:
            t = (value - 0.75) / 0.25
            r = 0.741 + t * (0.993 - 0.741)
            g = 0.873 + t * (0.906 - 0.873)
            b = 0.150 + t * (0.144 - 0.150)

        return (r, g, b)
