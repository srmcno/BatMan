"""Bat call classification engine using deep learning."""

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from app.config import settings


@dataclass
class ClassificationResult:
    """Result of a bat call classification."""

    species_id: str
    species_code: str
    confidence: float
    alternatives: list[dict[str, Any]]
    call_parameters: dict[str, float]
    activity_type: str
    activity_confidence: float
    xai_data: dict[str, Any]


class ConvBlock(nn.Module):
    """Convolutional block with BatchNorm and GELU activation."""

    def __init__(self, in_channels: int, out_channels: int, kernel_size: int = 3):
        super().__init__()
        self.conv = nn.Conv2d(
            in_channels, out_channels, kernel_size, padding=kernel_size // 2
        )
        self.bn = nn.BatchNorm2d(out_channels)
        self.activation = nn.GELU()
        self.pool = nn.MaxPool2d(2, 2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.conv(x)
        x = self.bn(x)
        x = self.activation(x)
        x = self.pool(x)
        return x


class TransformerEncoderBlock(nn.Module):
    """Transformer encoder block for temporal pattern learning."""

    def __init__(self, d_model: int = 512, nhead: int = 8, dim_feedforward: int = 2048):
        super().__init__()
        self.self_attn = nn.MultiheadAttention(d_model, nhead, batch_first=True)
        self.norm1 = nn.LayerNorm(d_model)
        self.norm2 = nn.LayerNorm(d_model)
        self.ff = nn.Sequential(
            nn.Linear(d_model, dim_feedforward),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(dim_feedforward, d_model),
            nn.Dropout(0.1),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        # Self-attention with residual
        attn_out, attn_weights = self.self_attn(x, x, x)
        x = self.norm1(x + attn_out)

        # Feed-forward with residual
        x = self.norm2(x + self.ff(x))

        return x, attn_weights


class EcoEchoNet(nn.Module):
    """
    Hybrid CNN-Transformer architecture for bat call classification.

    Architecture:
    1. CNN feature extractor for spectrogram
    2. Transformer encoder for temporal patterns
    3. Multi-task heads for species, parameters, and activity
    """

    def __init__(
        self,
        num_species: int = 150,
        num_activities: int = 6,
        d_model: int = 512,
        num_transformer_layers: int = 6,
    ):
        super().__init__()

        self.num_species = num_species

        # CNN Feature Extractor
        self.cnn = nn.Sequential(
            ConvBlock(1, 64),    # 128x256 -> 64x128
            ConvBlock(64, 128),  # 64x128 -> 32x64
            ConvBlock(128, 256), # 32x64 -> 16x32
            ConvBlock(256, 512), # 16x32 -> 8x16
        )

        # Adaptive pooling to fixed size
        self.adaptive_pool = nn.AdaptiveAvgPool2d((8, 16))

        # Flatten and project to d_model
        self.flatten_proj = nn.Linear(512 * 8 * 16, d_model)

        # Positional encoding
        self.pos_encoding = nn.Parameter(torch.randn(1, 128, d_model) * 0.02)

        # Transformer encoder layers
        self.transformer_layers = nn.ModuleList([
            TransformerEncoderBlock(d_model, nhead=8, dim_feedforward=2048)
            for _ in range(num_transformer_layers)
        ])

        # Global pooling
        self.global_pool = nn.AdaptiveAvgPool1d(1)

        # Classification heads
        self.species_head = nn.Sequential(
            nn.Linear(d_model, d_model // 2),
            nn.GELU(),
            nn.Dropout(0.3),
            nn.Linear(d_model // 2, num_species),
        )

        self.activity_head = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(256, num_activities),
        )

        # Parameter regression head
        self.param_head = nn.Sequential(
            nn.Linear(d_model, 256),
            nn.GELU(),
            nn.Linear(256, 10),  # fc, fmax, fmin, duration, slope, etc.
        )

        # Confidence estimation head
        self.confidence_head = nn.Sequential(
            nn.Linear(d_model, 128),
            nn.GELU(),
            nn.Linear(128, 1),
            nn.Sigmoid(),
        )

    def forward(
        self, x: torch.Tensor, return_attention: bool = False
    ) -> dict[str, torch.Tensor]:
        batch_size = x.shape[0]

        # CNN feature extraction
        x = self.cnn(x)
        x = self.adaptive_pool(x)

        # Flatten and project
        x = x.view(batch_size, -1)
        x = self.flatten_proj(x)
        x = x.unsqueeze(1).expand(-1, 128, -1)  # Create sequence

        # Add positional encoding
        x = x + self.pos_encoding[:, :x.size(1), :]

        # Transformer encoding
        attention_weights = []
        for layer in self.transformer_layers:
            x, attn = layer(x)
            attention_weights.append(attn)

        # Global pooling
        x = x.transpose(1, 2)
        x = self.global_pool(x).squeeze(-1)

        # Multi-task outputs
        species_logits = self.species_head(x)
        activity_logits = self.activity_head(x)
        call_params = self.param_head(x)
        confidence = self.confidence_head(x)

        outputs = {
            "species_logits": species_logits,
            "species_probs": F.softmax(species_logits, dim=-1),
            "activity_logits": activity_logits,
            "activity_probs": F.softmax(activity_logits, dim=-1),
            "call_params": call_params,
            "confidence": confidence,
        }

        if return_attention:
            outputs["attention_weights"] = torch.stack(attention_weights)

        return outputs


class BatCallClassifier:
    """High-level classifier interface for bat call classification."""

    def __init__(self):
        self.model: EcoEchoNet | None = None
        self.device = torch.device(settings.model_device)
        self.species_mapping: dict[int, dict[str, str]] = {}
        self.activity_mapping = {
            0: "commuting",
            1: "foraging",
            2: "feeding_buzz",
            3: "social",
            4: "drinking",
            5: "unknown",
        }
        self._loaded = False

    async def load_model(self) -> None:
        """Load the classification model."""
        if self._loaded:
            return

        # Initialize model
        self.model = EcoEchoNet(
            num_species=settings.model_batch_size,  # Placeholder
            num_activities=6,
        )

        # Load weights if available
        model_path = Path(settings.model_path) / "ecoecho_net.pt"
        if model_path.exists():
            state_dict = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(state_dict)

        self.model.to(self.device)
        self.model.eval()

        # Load species mapping
        await self._load_species_mapping()

        self._loaded = True

    async def _load_species_mapping(self) -> None:
        """Load species ID to code mapping."""
        # In production, load from database
        # For now, use placeholder mapping
        self.species_mapping = {
            0: {"code": "EPFU", "name": "Big Brown Bat"},
            1: {"code": "LABO", "name": "Eastern Red Bat"},
            2: {"code": "MYLU", "name": "Little Brown Bat"},
            3: {"code": "LANO", "name": "Silver-haired Bat"},
            4: {"code": "PESU", "name": "Tri-colored Bat"},
            5: {"code": "LACI", "name": "Hoary Bat"},
            6: {"code": "MYSE", "name": "Northern Long-eared Bat"},
            7: {"code": "MYSO", "name": "Indiana Bat"},
            8: {"code": "NYHU", "name": "Evening Bat"},
            9: {"code": "COTO", "name": "Townsend's Big-eared Bat"},
        }

    async def classify(
        self,
        spectrogram: np.ndarray,
        return_xai: bool = True,
    ) -> ClassificationResult:
        """
        Classify a bat call from its spectrogram.

        Args:
            spectrogram: Mel spectrogram of shape (n_mels, time_frames)
            return_xai: Whether to return XAI data

        Returns:
            ClassificationResult with species, confidence, and parameters
        """
        if not self._loaded:
            await self.load_model()

        # Prepare input
        x = torch.from_numpy(spectrogram).float()
        x = x.unsqueeze(0).unsqueeze(0)  # Add batch and channel dims
        x = x.to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(x, return_attention=return_xai)

        # Get predictions
        species_probs = outputs["species_probs"][0].cpu().numpy()
        activity_probs = outputs["activity_probs"][0].cpu().numpy()
        call_params = outputs["call_params"][0].cpu().numpy()
        confidence = outputs["confidence"][0].item()

        # Get top prediction
        top_species_idx = int(np.argmax(species_probs))
        top_species_conf = float(species_probs[top_species_idx])
        top_activity_idx = int(np.argmax(activity_probs))
        top_activity_conf = float(activity_probs[top_activity_idx])

        # Get species info
        species_info = self.species_mapping.get(
            top_species_idx,
            {"code": "UNKN", "name": "Unknown"},
        )

        # Get alternatives (top 5)
        top_indices = np.argsort(species_probs)[-5:][::-1]
        alternatives = []
        for idx in top_indices[1:]:  # Skip top prediction
            alt_info = self.species_mapping.get(idx, {"code": "UNKN", "name": "Unknown"})
            alternatives.append({
                "id": str(idx),
                "code": alt_info["code"],
                "name": alt_info["name"],
                "confidence": float(species_probs[idx]),
            })

        # Parse call parameters
        param_names = [
            "fc_khz", "fmax_khz", "fmin_khz", "fmean_khz", "fknee_khz",
            "bandwidth_khz", "duration_ms", "slope_oct_per_s",
            "peak_amplitude_db", "total_energy_db",
        ]
        call_parameters = {
            name: float(call_params[i]) for i, name in enumerate(param_names)
        }

        # XAI data
        xai_data = {}
        if return_xai and "attention_weights" in outputs:
            attn = outputs["attention_weights"][-1][0].cpu().numpy()  # Last layer
            xai_data = {
                "attention_map": attn.tolist(),
                "confidence_breakdown": {
                    "call_quality": confidence,
                    "species_match": top_species_conf,
                    "parameter_consistency": 0.85,  # Placeholder
                },
                "feature_importance": {
                    "fc_khz": 0.35,
                    "slope": 0.25,
                    "duration": 0.15,
                    "bandwidth": 0.10,
                    "fmax": 0.08,
                    "fmin": 0.07,
                },
            }

        return ClassificationResult(
            species_id=str(top_species_idx),
            species_code=species_info["code"],
            confidence=top_species_conf * confidence,
            alternatives=alternatives,
            call_parameters=call_parameters,
            activity_type=self.activity_mapping[top_activity_idx],
            activity_confidence=top_activity_conf,
            xai_data=xai_data,
        )

    async def classify_batch(
        self,
        spectrograms: list[np.ndarray],
    ) -> list[ClassificationResult]:
        """Classify multiple spectrograms in a batch."""
        if not spectrograms:
            return []

        if not self._loaded:
            await self.load_model()

        # Stack spectrograms
        batch = np.stack([s for s in spectrograms])
        x = torch.from_numpy(batch).float()
        x = x.unsqueeze(1)  # Add channel dim
        x = x.to(self.device)

        # Run inference
        with torch.no_grad():
            outputs = self.model(x, return_attention=False)

        # Process each result
        results = []
        for i in range(len(spectrograms)):
            species_probs = outputs["species_probs"][i].cpu().numpy()
            activity_probs = outputs["activity_probs"][i].cpu().numpy()
            call_params = outputs["call_params"][i].cpu().numpy()
            confidence = outputs["confidence"][i].item()

            top_species_idx = int(np.argmax(species_probs))
            top_species_conf = float(species_probs[top_species_idx])
            top_activity_idx = int(np.argmax(activity_probs))
            top_activity_conf = float(activity_probs[top_activity_idx])

            species_info = self.species_mapping.get(
                top_species_idx,
                {"code": "UNKN", "name": "Unknown"},
            )

            param_names = [
                "fc_khz", "fmax_khz", "fmin_khz", "fmean_khz", "fknee_khz",
                "bandwidth_khz", "duration_ms", "slope_oct_per_s",
                "peak_amplitude_db", "total_energy_db",
            ]

            results.append(ClassificationResult(
                species_id=str(top_species_idx),
                species_code=species_info["code"],
                confidence=top_species_conf * confidence,
                alternatives=[],
                call_parameters={
                    name: float(call_params[j]) for j, name in enumerate(param_names)
                },
                activity_type=self.activity_mapping[top_activity_idx],
                activity_confidence=top_activity_conf,
                xai_data={},
            ))

        return results


# Singleton instance
_classifier: BatCallClassifier | None = None


@lru_cache
def get_classifier() -> BatCallClassifier:
    """Get the singleton classifier instance."""
    global _classifier
    if _classifier is None:
        _classifier = BatCallClassifier()
    return _classifier
