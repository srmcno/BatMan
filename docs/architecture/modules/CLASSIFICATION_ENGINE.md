# Classification Engine - Technical Specification

## Overview

The Classification Engine is the AI-powered core of EcoEcho AI, responsible for automated species identification with >95% accuracy. This document details the deep learning architecture, noise immunity systems, and Explainable AI (XAI) components.

---

## 1. Deep Learning Architecture

### 1.1 Model Architecture: EcoEchoNet

We employ a hybrid **CNN-Transformer** architecture optimized for bioacoustic signal classification:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        EcoEchoNet Architecture                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: Raw Audio (384kHz Full-Spectrum) or Pre-computed Spectrogram        │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Audio Preprocessing Pipeline                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ Resample to │  │ Bandpass    │  │ Short-Time  │  │   Mel       │   │  │
│  │  │   256kHz    │─►│ Filter      │─►│  Fourier    │─►│ Spectrogram │   │  │
│  │  │             │  │ (10-150kHz) │  │ Transform   │  │ (128 bins)  │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                   Convolutional Feature Extractor                     │  │
│  │                                                                       │  │
│  │  Stage 1: Conv2D(64) → BatchNorm → GELU → MaxPool                    │  │
│  │  Stage 2: Conv2D(128) → BatchNorm → GELU → MaxPool                   │  │
│  │  Stage 3: Conv2D(256) → BatchNorm → GELU → MaxPool                   │  │
│  │  Stage 4: Conv2D(512) → BatchNorm → GELU → AdaptivePool              │  │
│  │                                                                       │  │
│  │  Output: Feature Map [B, 512, T', F']                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Transformer Encoder Block                          │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Positional Encoding (Learnable 2D)                             │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Multi-Head Self-Attention (8 heads, d_model=512)               │  │  │
│  │  │  ├── Q, K, V Projections                                        │  │  │
│  │  │  ├── Scaled Dot-Product Attention                               │  │  │
│  │  │  └── Attention Weights Stored for XAI                           │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Feed-Forward Network (2048 hidden, GELU)                       │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                        │  │
│  │  × 6 Transformer Layers with Residual Connections                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      Classification Heads                             │  │
│  │                                                                       │  │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────┐  │  │
│  │  │ Species Head  │  │ Confidence    │  │ Call Parameter            │  │  │
│  │  │ (Softmax)     │  │ Estimator     │  │ Regression                │  │  │
│  │  │ 150 classes   │  │ (Sigmoid)     │  │ (freq, slope, duration)   │  │  │
│  │  └───────────────┘  └───────────────┘  └───────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Outputs:                                                                   │
│  - species_id: int (0-149)                                                 │
│  - confidence: float (0.0-1.0)                                             │
│  - call_params: {fc, fmax, fmin, slope, duration, bandwidth}               │
│  - attention_maps: Tensor for XAI visualization                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Model Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Input Size | 128×256 (mel bins × time frames) | ~1 second window |
| Parameters | ~45M | Optimized for edge deployment |
| Inference Time | <50ms | NVIDIA T4 GPU |
| Supported Species | 150+ | North American focus, expandable |
| Minimum Confidence | 0.70 | Below triggers manual review |

### 1.3 Training Pipeline

```python
# Training Configuration
training_config = {
    "dataset": {
        "sources": [
            "NABat_National_Dataset",
            "BatLibrary_v3",
            "EcoEcho_Internal_Verified",
            "iNaturalist_Acoustic"
        ],
        "total_samples": 2_500_000,
        "species_count": 150,
        "augmentation": {
            "time_stretch": [0.8, 1.2],
            "pitch_shift": [-2, 2],  # semitones
            "noise_injection": ["gaussian", "environmental"],
            "mixup_alpha": 0.4
        }
    },
    "model": {
        "architecture": "EcoEchoNet_v2",
        "pretrained_backbone": "AudioMAE_base",
        "freeze_backbone_epochs": 5
    },
    "training": {
        "optimizer": "AdamW",
        "learning_rate": 1e-4,
        "weight_decay": 0.05,
        "scheduler": "CosineAnnealingWarmRestarts",
        "epochs": 100,
        "batch_size": 64,
        "gradient_accumulation": 4,
        "mixed_precision": "fp16"
    },
    "validation": {
        "strategy": "stratified_kfold",
        "folds": 5,
        "holdout_percentage": 0.1
    }
}
```

### 1.4 Multi-Task Learning Objectives

```
Total Loss = λ₁·L_species + λ₂·L_confidence + λ₃·L_params + λ₄·L_contrastive

Where:
- L_species: Cross-entropy loss for species classification
- L_confidence: Binary cross-entropy for out-of-distribution detection
- L_params: MSE loss for call parameter regression
- L_contrastive: SimCLR-style contrastive loss for embedding quality

Weights: λ₁=1.0, λ₂=0.3, λ₃=0.2, λ₄=0.5
```

---

## 2. Noise Immunity System

### 2.1 Spectral Subtraction Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Noise Immunity Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: Raw Audio with Environmental Noise                                  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 1: Noise Profile Estimation                                    │  │
│  │                                                                       │  │
│  │  • Analyze first 500ms as potential noise-only segment                │  │
│  │  • Use Voice Activity Detection (VAD) to find noise frames            │  │
│  │  • Compute noise power spectral density (PSD)                        │  │
│  │  • Apply exponential smoothing: N(f) = α·N_new(f) + (1-α)·N_old(f)   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 2: Adaptive Spectral Subtraction                               │  │
│  │                                                                       │  │
│  │  For each frame:                                                      │  │
│  │    |Y(f)|² = max(|X(f)|² - α·|N(f)|², β·|N(f)|²)                     │  │
│  │                                                                       │  │
│  │  Where:                                                               │  │
│  │    α = over-subtraction factor (1.0-2.0, adaptive)                   │  │
│  │    β = spectral floor (0.01-0.1)                                     │  │
│  │    |N(f)|² = estimated noise spectrum                                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 3: Deep Learning Denoiser (Optional Enhancement)               │  │
│  │                                                                       │  │
│  │  • U-Net architecture trained on bat calls + noise                   │  │
│  │  • Input: Noisy spectrogram                                          │  │
│  │  • Output: Clean spectrogram mask                                    │  │
│  │  • Training data: 50,000 clean calls + synthetic noise combos        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 4: Post-Processing Filters                                     │  │
│  │                                                                       │  │
│  │  • Morphological opening to remove isolated noise pixels             │  │
│  │  • Harmonic enhancement for echolocation harmonics                   │  │
│  │  • Temporal smoothing across adjacent frames                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Output: Clean Spectrogram + Noise Confidence Score                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Noise Type Classifiers

| Noise Type | Detection Method | Mitigation Strategy |
|------------|-----------------|---------------------|
| **Insect Noise** | Continuous high-freq energy (>50kHz) | Notch filtering, temporal masking |
| **Wind Noise** | Low-freq broadband (<5kHz) | High-pass filter, spectral subtraction |
| **Rain** | Impulse detector + spectral spread | Frame rejection, interpolation |
| **Mechanical** | Periodic harmonic detector | Comb filtering |
| **Traffic** | Low-freq rumble detection | Adaptive high-pass |
| **Other Bats** | Overlapping call detector | Separation network |

### 2.3 Noise Immunity Metrics

```python
class NoiseImmunityMetrics:
    """
    Quality metrics computed for each processed file
    """

    def compute_metrics(self, original: np.ndarray, processed: np.ndarray) -> dict:
        return {
            "snr_improvement_db": self.calculate_snr_improvement(original, processed),
            "noise_reduction_ratio": self.calculate_nrr(original, processed),
            "signal_distortion_index": self.calculate_sdi(original, processed),
            "perceptual_quality_score": self.pesq_estimate(original, processed),
            "bat_call_preservation": self.call_preservation_score(original, processed)
        }
```

---

## 3. Explainable AI (XAI) System

### 3.1 Explanation Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Explainable AI Pipeline                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Classification Result: "Myotis lucifugus" (95.2% confidence)              │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Component 1: Attention Visualization                                 │  │
│  │                                                                       │  │
│  │  • Extract attention weights from transformer layers                  │  │
│  │  • Generate attention heatmap overlaid on spectrogram                │  │
│  │  • Highlight regions most influential for classification             │  │
│  │                                                                       │  │
│  │  Output: attention_heatmap.png                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Component 2: Call Parameter Extraction                               │  │
│  │                                                                       │  │
│  │  Measured Parameters:                                                │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Fc (Characteristic Freq):  42.3 kHz  [Expected: 40-45 kHz] ✓   │ │  │
│  │  │  Fmax (Maximum Freq):       78.2 kHz  [Expected: 75-85 kHz] ✓   │ │  │
│  │  │  Fmin (Minimum Freq):       38.1 kHz  [Expected: 35-42 kHz] ✓   │ │  │
│  │  │  Duration:                  3.2 ms    [Expected: 2-5 ms]    ✓   │ │  │
│  │  │  Slope:                    -82 oct/s  [Expected: -90±15]    ✓   │ │  │
│  │  │  Bandwidth:                40.1 kHz   [Expected: 35-50 kHz] ✓   │ │  │
│  │  │  Knee Frequency:           52.4 kHz   [Expected: 50-55 kHz] ✓   │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Component 3: Feature Importance Ranking                              │  │
│  │                                                                       │  │
│  │  SHAP Analysis Results:                                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  1. Characteristic Frequency ████████████████████ 0.42          │ │  │
│  │  │  2. Call Slope              ██████████████       0.28          │ │  │
│  │  │  3. Knee Shape              ████████             0.15          │ │  │
│  │  │  4. Duration                █████                0.09          │ │  │
│  │  │  5. Bandwidth               ███                  0.06          │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Component 4: Counterfactual Explanation                              │  │
│  │                                                                       │  │
│  │  "This call was classified as M. lucifugus instead of M. sodalis     │  │
│  │   because:                                                            │  │
│  │   • Fc is 42.3 kHz (M. sodalis typically 48-52 kHz)                 │  │
│  │   • Knee is more rounded (M. sodalis has sharper knee)              │  │
│  │   • Slope is less steep (-82 vs -95 for M. sodalis)"                │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Component 5: Reference Call Comparison                               │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │  │
│  │  │  Query Call     │    │ Reference #1    │    │ Reference #2    │   │  │
│  │  │  [spectrogram]  │    │ M. lucifugus    │    │ M. lucifugus    │   │  │
│  │  │                 │    │ Similarity: 94% │    │ Similarity: 91% │   │  │
│  │  └─────────────────┘    └─────────────────┘    └─────────────────┘   │  │
│  │                                                                       │  │
│  │  Nearest non-match: M. sodalis (Similarity: 72%)                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 XAI Data Schema

```typescript
interface ClassificationExplanation {
  // Core identification
  species_id: string;
  common_name: string;
  scientific_name: string;
  confidence: number;

  // Call parameters with expected ranges
  call_parameters: {
    fc_khz: MeasuredParameter;
    fmax_khz: MeasuredParameter;
    fmin_khz: MeasuredParameter;
    duration_ms: MeasuredParameter;
    slope_oct_per_s: MeasuredParameter;
    bandwidth_khz: MeasuredParameter;
    knee_freq_khz: MeasuredParameter;
  };

  // Visual explanations
  visualizations: {
    attention_heatmap: Base64Image;
    spectrogram_annotated: Base64Image;
    call_trace_overlay: Base64Image;
  };

  // Feature importance
  shap_values: FeatureImportance[];

  // Comparative analysis
  similar_species: SimilarSpeciesComparison[];
  reference_calls: ReferenceCall[];

  // Confidence factors
  confidence_breakdown: {
    call_quality_score: number;
    noise_level: number;
    regional_likelihood: number;
    temporal_pattern_match: number;
  };
}

interface MeasuredParameter {
  value: number;
  expected_range: [number, number];
  within_range: boolean;
  importance_rank: number;
}

interface FeatureImportance {
  feature_name: string;
  shap_value: number;
  contribution: 'positive' | 'negative';
  magnitude: number;
}
```

### 3.3 Confidence Calibration

```python
class ConfidenceCalibrator:
    """
    Temperature scaling for calibrated confidence scores
    """

    def __init__(self, temperature: float = 1.5):
        self.temperature = temperature

    def calibrate(self, logits: torch.Tensor) -> torch.Tensor:
        """
        Apply temperature scaling to produce calibrated probabilities
        """
        return F.softmax(logits / self.temperature, dim=-1)

    def compute_ece(self, probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
        """
        Expected Calibration Error - measures reliability of confidence scores
        Target: ECE < 0.05
        """
        bin_boundaries = np.linspace(0, 1, n_bins + 1)
        ece = 0.0

        for i in range(n_bins):
            in_bin = (probs > bin_boundaries[i]) & (probs <= bin_boundaries[i + 1])
            prop_in_bin = in_bin.mean()

            if prop_in_bin > 0:
                avg_confidence = probs[in_bin].mean()
                avg_accuracy = labels[in_bin].mean()
                ece += np.abs(avg_confidence - avg_accuracy) * prop_in_bin

        return ece
```

---

## 4. Regional Species Filtering

### 4.1 GPS-Aware Species Library

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Regional Species Filtering                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Recording Metadata:                                                        │
│  • GPS: 38.9072° N, 77.0369° W (Washington, DC)                            │
│  • Date: July 15, 2024                                                     │
│  • Time: 22:45 local                                                       │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 1: Geographic Range Query                                       │  │
│  │                                                                       │  │
│  │  Query: SELECT species FROM species_ranges                            │  │
│  │         WHERE ST_Contains(range_polygon, GPS_POINT)                  │  │
│  │                                                                       │  │
│  │  Result: 22 species have ranges overlapping this location            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 2: Seasonal Filtering                                           │  │
│  │                                                                       │  │
│  │  Query: Filter by seasonal_presence[month='July']                    │  │
│  │                                                                       │  │
│  │  Result: 18 species expected in July (4 migratory species excluded)  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Step 3: Habitat Probability Weighting                                │  │
│  │                                                                       │  │
│  │  Cross-reference with land cover data:                               │  │
│  │  • Location is urban/suburban                                        │  │
│  │  • Weight forest specialists lower, generalists higher               │  │
│  │                                                                       │  │
│  │  Result: Prior probabilities adjusted per species                    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Final Species Library for Classification:                            │  │
│  │                                                                       │  │
│  │  High Prior (common urban species):                                  │  │
│  │  • Eptesicus fuscus (Big Brown Bat) - 0.25                          │  │
│  │  • Lasiurus borealis (Eastern Red Bat) - 0.18                       │  │
│  │  • Lasionycteris noctivagans (Silver-haired) - 0.12                 │  │
│  │                                                                       │  │
│  │  Medium Prior:                                                       │  │
│  │  • Myotis lucifugus - 0.10                                          │  │
│  │  • Perimyotis subflavus - 0.08                                      │  │
│  │  • ... (8 more species)                                             │  │
│  │                                                                       │  │
│  │  Low Prior (rare/unlikely):                                          │  │
│  │  • Myotis sodalis - 0.02 (endangered, rare)                         │  │
│  │  • ... (5 more species)                                             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Species Range Database Schema

```sql
CREATE TABLE species_ranges (
    species_id UUID PRIMARY KEY,
    scientific_name VARCHAR(100) NOT NULL,
    common_name VARCHAR(100) NOT NULL,

    -- Geographic range as PostGIS geometry
    range_polygon GEOMETRY(MULTIPOLYGON, 4326),

    -- Seasonal presence matrix (1-12 months)
    seasonal_presence BOOLEAN[12],

    -- Habitat preferences (0-1 probability weights)
    habitat_weights JSONB,
    -- Example: {"forest": 0.9, "urban": 0.2, "wetland": 0.7}

    -- Conservation status
    iucn_status VARCHAR(20),
    esa_listing VARCHAR(20),

    -- Data quality
    range_confidence DECIMAL(3,2),
    last_updated TIMESTAMP,
    data_source VARCHAR(100)
);

CREATE INDEX idx_species_range_gist ON species_ranges USING GIST(range_polygon);
```

---

## 5. Model Versioning & Deployment

### 5.1 MLflow Model Registry

```yaml
# Model Registry Structure
models:
  ecoecho_classifier:
    latest_version: "3.2.1"
    production_version: "3.1.0"
    staging_version: "3.2.1"

    versions:
      - version: "3.2.1"
        metrics:
          accuracy: 0.962
          f1_macro: 0.948
          ece: 0.031
        training_date: "2024-07-01"
        dataset_version: "nabat_2024q2"
        status: "staging"

      - version: "3.1.0"
        metrics:
          accuracy: 0.958
          f1_macro: 0.941
          ece: 0.038
        training_date: "2024-04-15"
        dataset_version: "nabat_2024q1"
        status: "production"

  noise_denoiser:
    latest_version: "2.0.0"
    production_version: "2.0.0"
```

### 5.2 A/B Testing Framework

```python
class ModelABTest:
    """
    Framework for comparing model versions in production
    """

    def __init__(self, control_model: str, treatment_model: str, traffic_split: float = 0.1):
        self.control = load_model(control_model)
        self.treatment = load_model(treatment_model)
        self.traffic_split = traffic_split
        self.metrics_tracker = MetricsTracker()

    def classify(self, audio: np.ndarray, metadata: dict) -> ClassificationResult:
        if random.random() < self.traffic_split:
            result = self.treatment.classify(audio, metadata)
            self.metrics_tracker.log("treatment", result)
        else:
            result = self.control.classify(audio, metadata)
            self.metrics_tracker.log("control", result)

        return result

    def get_experiment_results(self) -> ExperimentReport:
        """
        Statistical comparison of control vs treatment
        """
        return self.metrics_tracker.compute_significance()
```

---

## 6. Performance Benchmarks

### 6.1 Accuracy Targets by Species Group

| Species Group | Target Accuracy | Current Performance |
|---------------|-----------------|---------------------|
| **Myotis complex** | >92% | 93.4% |
| **Lasiurus spp.** | >96% | 97.1% |
| **Eptesicus fuscus** | >98% | 98.5% |
| **Tadarida brasiliensis** | >97% | 97.8% |
| **Rare/Endangered** | >95% | 95.2% |
| **Overall (macro avg)** | >95% | 96.2% |

### 6.2 Inference Performance

| Metric | Target | Achieved |
|--------|--------|----------|
| Single file inference | <50ms | 42ms |
| Batch (100 files) | <2s | 1.7s |
| Batch (1000 files) | <15s | 12.3s |
| Memory usage | <4GB VRAM | 3.2GB |
| Model load time | <5s | 3.8s |

---

## 7. API Specification

### 7.1 Classification Endpoint

```yaml
openapi: 3.0.0
paths:
  /api/v1/classify:
    post:
      summary: Classify bat call recording
      requestBody:
        content:
          multipart/form-data:
            schema:
              type: object
              properties:
                audio_file:
                  type: string
                  format: binary
                metadata:
                  type: object
                  properties:
                    latitude: number
                    longitude: number
                    timestamp: string
                    recorder_model: string
                options:
                  type: object
                  properties:
                    enable_xai: boolean
                    regional_filter: boolean
                    noise_reduction: string
                    confidence_threshold: number
      responses:
        200:
          description: Classification result
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ClassificationResult'
```

### 7.2 Batch Processing Endpoint

```yaml
  /api/v1/classify/batch:
    post:
      summary: Process multiple files asynchronously
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                file_urls:
                  type: array
                  items:
                    type: string
                project_id:
                  type: string
                options:
                  $ref: '#/components/schemas/BatchOptions'
      responses:
        202:
          description: Batch job accepted
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id: string
                  status_url: string
                  estimated_completion: string
```

---

## 8. Future Enhancements

### 8.1 Planned Capabilities

1. **Multi-Species Call Detection**: Separate overlapping calls from multiple bats
2. **Real-Time Streaming**: WebSocket-based live classification
3. **Federated Learning**: Train on distributed datasets without data sharing
4. **Active Learning**: Smart sampling of uncertain calls for labeling
5. **Transfer Learning**: Adapt to new regions/species with minimal data

### 8.2 Research Roadmap

- Q3 2024: Transformer-only architecture (AudioMAE fine-tuning)
- Q4 2024: Self-supervised pre-training on 10M+ unlabeled recordings
- Q1 2025: Few-shot learning for rare species (5-shot accuracy >80%)
- Q2 2025: Multimodal integration (call + thermal + radar)
