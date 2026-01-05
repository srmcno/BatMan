# Sound Profiling & Data Visualization - Technical Specification

## Overview

This module defines the advanced visualization and behavioral analysis capabilities of EcoEcho AI, replacing static spectrograms with interactive 3D visualizations and enabling sophisticated temporal pattern recognition for activity classification.

---

## 1. Dynamic 3D Spectrograms

### 1.1 Visualization Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    3D Spectrogram Rendering Pipeline                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Audio Input                                                                │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Signal Processing Layer                                            │   │
│  │                                                                      │   │
│  │  1. STFT Computation (n_fft=2048, hop=512, window=hann)            │   │
│  │  2. Mel-scale transformation (n_mels=256, fmin=10kHz, fmax=150kHz) │   │
│  │  3. Log-power spectrogram: 10 * log10(S + ε)                       │   │
│  │  4. Dynamic range compression for visualization                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  3D Mesh Generation                                                 │   │
│  │                                                                      │   │
│  │  • Convert spectrogram matrix to height-mapped 3D surface          │   │
│  │  • X-axis: Time (ms)                                                │   │
│  │  • Y-axis: Frequency (kHz)                                          │   │
│  │  • Z-axis: Amplitude (dB)                                           │   │
│  │  • Generate vertex buffer with normals for lighting                │   │
│  │  • Apply adaptive level-of-detail based on zoom level              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│       │                                                                     │
│       ▼                                                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  WebGL/Three.js Rendering                                           │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────┐    │   │
│  │  │              Interactive 3D Viewport                        │    │   │
│  │  │                                                              │    │   │
│  │  │     Frequency (kHz)                                          │    │   │
│  │  │          ▲                                                   │    │   │
│  │  │    150 ──┤    ╱╲                                             │    │   │
│  │  │          │   ╱  ╲    ╱╲                                      │    │   │
│  │  │    100 ──┤  ╱    ╲  ╱  ╲                                     │    │   │
│  │  │          │ ╱      ╲╱    ╲     ← Bat Call Surface             │    │   │
│  │  │     50 ──┤╱              ╲                                   │    │   │
│  │  │          │                ╲                                  │    │   │
│  │  │     10 ──┴─────────────────────────▶ Time (ms)              │    │   │
│  │  │               0    50   100   150                           │    │   │
│  │  │                                                              │    │   │
│  │  │  [Rotate] [Zoom] [Pan] [Reset] [Measure] [Export]           │    │   │
│  │  └─────────────────────────────────────────────────────────────┘    │   │
│  │                                                                      │   │
│  │  Controls:                                                          │   │
│  │  • Left-drag: Rotate view                                          │   │
│  │  • Scroll: Zoom in/out                                             │   │
│  │  • Right-drag: Pan view                                            │   │
│  │  • Double-click: Focus on region                                   │   │
│  │  • Ctrl+click: Place measurement markers                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Three.js Implementation

```typescript
// 3D Spectrogram Renderer Component
interface SpectrogramVisualizerProps {
  audioData: Float32Array;
  sampleRate: number;
  colormap: ColorMap;
  annotations?: CallAnnotation[];
}

class Spectrogram3DRenderer {
  private scene: THREE.Scene;
  private camera: THREE.PerspectiveCamera;
  private renderer: THREE.WebGLRenderer;
  private controls: OrbitControls;
  private spectrogramMesh: THREE.Mesh;

  constructor(container: HTMLElement, props: SpectrogramVisualizerProps) {
    this.initScene(container);
    this.initLighting();
    this.initControls();
  }

  private generateMesh(spectrogram: Float32Array[], config: MeshConfig): THREE.Mesh {
    const geometry = new THREE.BufferGeometry();
    const vertices: number[] = [];
    const colors: number[] = [];
    const indices: number[] = [];

    const timeSteps = spectrogram.length;
    const freqBins = spectrogram[0].length;

    // Generate vertices
    for (let t = 0; t < timeSteps; t++) {
      for (let f = 0; f < freqBins; f++) {
        const x = (t / timeSteps) * config.width;
        const y = (f / freqBins) * config.height;
        const z = this.normalizeAmplitude(spectrogram[t][f]) * config.depth;

        vertices.push(x, y, z);

        // Color mapping based on amplitude
        const color = this.colormap.getColor(spectrogram[t][f]);
        colors.push(color.r, color.g, color.b);
      }
    }

    // Generate triangle indices for mesh
    for (let t = 0; t < timeSteps - 1; t++) {
      for (let f = 0; f < freqBins - 1; f++) {
        const a = t * freqBins + f;
        const b = a + freqBins;
        const c = a + 1;
        const d = b + 1;

        indices.push(a, b, c);
        indices.push(b, d, c);
      }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geometry.setIndex(indices);
    geometry.computeVertexNormals();

    const material = new THREE.MeshPhongMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      shininess: 30
    });

    return new THREE.Mesh(geometry, material);
  }

  public addCallAnnotation(annotation: CallAnnotation): void {
    // Add 3D markers for detected calls
    const marker = new THREE.Group();

    // Bounding box around call
    const boxGeometry = new THREE.BoxGeometry(
      annotation.duration * this.timeScale,
      annotation.bandwidth * this.freqScale,
      annotation.maxAmplitude * this.ampScale
    );
    const boxMaterial = new THREE.MeshBasicMaterial({
      color: annotation.color,
      wireframe: true,
      opacity: 0.7,
      transparent: true
    });
    const box = new THREE.Mesh(boxGeometry, boxMaterial);

    // Label sprite
    const label = this.createTextSprite(annotation.label);

    marker.add(box);
    marker.add(label);
    marker.position.set(annotation.startTime, annotation.centerFreq, 0);

    this.scene.add(marker);
  }

  public exportView(format: 'png' | 'gltf' | 'obj'): Blob {
    switch (format) {
      case 'png':
        return this.captureScreenshot();
      case 'gltf':
        return this.exportGLTF();
      case 'obj':
        return this.exportOBJ();
    }
  }
}
```

### 1.3 Color Mapping Options

```typescript
enum ColorMapPreset {
  VIRIDIS = 'viridis',      // Perceptually uniform, colorblind-safe
  MAGMA = 'magma',          // Dark background, high contrast
  PLASMA = 'plasma',        // Warm tones
  INFERNO = 'inferno',      // High dynamic range
  TURBO = 'turbo',          // Maximum distinction
  GRAYSCALE = 'grayscale',  // Traditional spectrogram look
  CUSTOM = 'custom'         // User-defined
}

interface ColorMapConfig {
  preset: ColorMapPreset;
  minDb: number;           // -100 to 0
  maxDb: number;           // -100 to 0
  dynamicRange: boolean;   // Auto-adjust to signal
  backgroundColor: string;
  gridColor: string;
  annotationColor: string;
}
```

### 1.4 Interactive Measurement Tools

```typescript
interface MeasurementTool {
  // Frequency measurements
  measureFrequency(point: THREE.Vector3): {
    frequency_khz: number;
    db_level: number;
    time_ms: number;
  };

  // Time-domain measurements
  measureDuration(start: THREE.Vector3, end: THREE.Vector3): {
    duration_ms: number;
    start_freq_khz: number;
    end_freq_khz: number;
    slope_oct_per_s: number;
  };

  // Area measurements
  measureRegion(bounds: THREE.Box3): {
    bandwidth_khz: number;
    duration_ms: number;
    average_amplitude_db: number;
    peak_amplitude_db: number;
    energy_db: number;
  };

  // Call parameter extraction
  extractCallParameters(callRegion: THREE.Box3): CallParameters;
}
```

---

## 2. Behavioral Identification System

### 2.1 Activity Classification Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  Behavioral Activity Classification                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: Sequence of Detected Calls (1-60 seconds window)                   │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Feature Extraction: Temporal Patterns                                │  │
│  │                                                                       │  │
│  │  Per-call features:                                                  │  │
│  │  • call_duration, inter_pulse_interval, frequency_params            │  │
│  │                                                                       │  │
│  │  Sequence features:                                                  │  │
│  │  • pulse_rate (calls/second)                                        │  │
│  │  • pulse_rate_trend (accelerating/stable/decelerating)              │  │
│  │  • frequency_modulation_pattern                                     │  │
│  │  • amplitude_envelope                                               │  │
│  │  • call_type_sequence                                               │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Temporal Pattern Recognition Model (LSTM/Transformer)                │  │
│  │                                                                       │  │
│  │  Architecture:                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Input: call_sequence [B, T, F]                                 │ │  │
│  │  │            │                                                    │ │  │
│  │  │  ┌─────────▼─────────┐                                          │ │  │
│  │  │  │  Bidirectional    │                                          │ │  │
│  │  │  │  LSTM (256 units) │  × 2 layers                              │ │  │
│  │  │  └─────────┬─────────┘                                          │ │  │
│  │  │            │                                                    │ │  │
│  │  │  ┌─────────▼─────────┐                                          │ │  │
│  │  │  │  Attention Layer  │                                          │ │  │
│  │  │  └─────────┬─────────┘                                          │ │  │
│  │  │            │                                                    │ │  │
│  │  │  ┌─────────▼─────────┐                                          │ │  │
│  │  │  │  Dense (128)      │                                          │ │  │
│  │  │  │  + Softmax (6)    │ ─► Activity Class                        │ │  │
│  │  │  └───────────────────┘                                          │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Activity Classifications                                             │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  FEEDING_BUZZ                                                   │ │  │
│  │  │  • Rapidly accelerating pulse rate (10→200+ calls/sec)         │ │  │
│  │  │  • Decreasing call duration                                    │ │  │
│  │  │  • Terminal phase with shortest IPIs                           │ │  │
│  │  │                                                                 │ │  │
│  │  │  Spectrogram Pattern:                                          │ │  │
│  │  │  ║║║║║║║║║║║║║║║║║║║║║║║║║║▐▐▐▐▐▐▐▐▐▐▐▌▌▌▌▌█████████            │ │  │
│  │  │  <-- approach -->  <-- terminal buzz -->                       │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  SOCIAL_CALL                                                    │ │  │
│  │  │  • Lower frequency than echolocation (<25 kHz)                 │ │  │
│  │  │  • Complex frequency modulation                                │ │  │
│  │  │  • Multi-syllable structure                                    │ │  │
│  │  │  • Often associated with roost sites                           │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  COMMUTING_FLIGHT                                               │ │  │
│  │  │  • Steady pulse rate (5-15 calls/sec)                          │ │  │
│  │  │  • Consistent call parameters                                  │ │  │
│  │  │  • Extended duration passes                                    │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  SEARCH_PHASE                                                   │ │  │
│  │  │  • Moderate pulse rate (8-20 calls/sec)                        │ │  │
│  │  │  • Exploratory behavior indicators                             │ │  │
│  │  │  • Variable call parameters                                    │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  APPROACH_PHASE                                                 │ │  │
│  │  │  • Increasing pulse rate                                       │ │  │
│  │  │  • Precursor to feeding buzz                                   │ │  │
│  │  │  • May not result in capture attempt                          │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  DRINKING_BEHAVIOR                                              │ │  │
│  │  │  • Low flight with periodic dips                               │ │  │
│  │  │  • Characteristic approach/retreat pattern                     │ │  │
│  │  │  • Often over water bodies                                     │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Feeding Buzz Detection Algorithm

```python
class FeedingBuzzDetector:
    """
    Specialized detector for feeding buzz sequences
    """

    def __init__(self, config: BuzzDetectorConfig):
        self.min_pulse_rate_start = config.min_pulse_rate_start  # 10 Hz
        self.max_pulse_rate_terminal = config.max_pulse_rate_terminal  # 200+ Hz
        self.min_buzz_duration_ms = config.min_buzz_duration  # 100ms
        self.acceleration_threshold = config.acceleration_threshold

    def detect_buzzes(self, calls: List[DetectedCall]) -> List[FeedingBuzz]:
        """
        Identify feeding buzz sequences from detected calls
        """
        buzzes = []
        i = 0

        while i < len(calls) - 10:  # Need minimum calls for buzz
            # Calculate local pulse rate
            window = calls[i:i+20]
            ipis = [window[j+1].start_time - window[j].start_time
                    for j in range(len(window)-1)]

            pulse_rates = [1000 / ipi for ipi in ipis if ipi > 0]

            # Check for acceleration pattern
            if self._is_accelerating(pulse_rates):
                buzz_end = self._find_buzz_end(calls, i)

                if buzz_end - i >= 10:  # Minimum calls in buzz
                    buzz = FeedingBuzz(
                        start_idx=i,
                        end_idx=buzz_end,
                        calls=calls[i:buzz_end],
                        max_pulse_rate=max(pulse_rates),
                        duration_ms=calls[buzz_end-1].end_time - calls[i].start_time,
                        terminal_phase_start=self._find_terminal_phase(calls, i, buzz_end)
                    )
                    buzzes.append(buzz)
                    i = buzz_end
                else:
                    i += 1
            else:
                i += 1

        return buzzes

    def _is_accelerating(self, pulse_rates: List[float]) -> bool:
        """
        Check if pulse rate shows acceleration pattern
        """
        if len(pulse_rates) < 5:
            return False

        # Linear regression on pulse rate
        x = np.arange(len(pulse_rates))
        slope, _ = np.polyfit(x, pulse_rates, 1)

        return slope > self.acceleration_threshold

    def _find_terminal_phase(self, calls: List[DetectedCall],
                             start: int, end: int) -> int:
        """
        Find start of terminal buzz phase (highest pulse rates)
        """
        # Terminal phase typically last 20-50ms with IPI < 10ms
        for i in range(end - 1, start, -1):
            ipi = calls[i].start_time - calls[i-1].start_time
            if ipi > 10:  # IPI > 10ms indicates end of terminal phase
                return i
        return end - 5
```

### 2.3 Behavioral Metrics Output

```typescript
interface BehavioralAnalysis {
  // Recording-level summary
  recording_id: string;
  duration_seconds: number;
  total_calls: number;

  // Activity breakdown
  activity_summary: {
    feeding_buzzes: number;
    feeding_buzz_rate: number;  // buzzes per hour
    social_calls: number;
    commuting_passes: number;
    search_phases: number;
  };

  // Temporal distribution
  activity_timeline: ActivityTimelineEvent[];

  // Foraging metrics
  foraging_metrics: {
    capture_attempts: number;
    capture_rate_per_hour: number;
    avg_buzz_duration_ms: number;
    avg_approach_duration_ms: number;
    foraging_intensity_index: number;
  };

  // Social behavior
  social_metrics: {
    social_call_count: number;
    call_type_diversity: number;
    potential_interactions: number;
  };
}

interface ActivityTimelineEvent {
  timestamp_ms: number;
  activity_type: ActivityType;
  confidence: number;
  species?: string;
  call_count: number;
  details: ActivityDetails;
}
```

---

## 3. GPS-Aware Visualization

### 3.1 Geospatial Integration

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    GPS-Integrated Analysis View                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Map View                                      │   │
│  │                                                                      │   │
│  │    ┌──────────────────────────────────────────────────────────┐     │   │
│  │    │                                                          │     │   │
│  │    │         ○ Site A (245 calls)                            │     │   │
│  │    │              ╲                                          │     │   │
│  │    │               ╲                                         │     │   │
│  │    │     ● Site B   ╲____                                    │     │   │
│  │    │   (1,234 calls)     ╲                                   │     │   │
│  │    │                      ○ Site C                           │     │   │
│  │    │                      (89 calls)                         │     │   │
│  │    │                                                          │     │   │
│  │    │    [Satellite] [Terrain] [Activity Heatmap]             │     │   │
│  │    └──────────────────────────────────────────────────────────┘     │   │
│  │                                                                      │   │
│  │  Site Details: Site B                                               │   │
│  │  ├── Coordinates: 38.9072°N, 77.0369°W                             │   │
│  │  ├── Elevation: 125m                                                │   │
│  │  ├── Habitat: Mixed deciduous forest edge                          │   │
│  │  ├── Recordings: 45 nights                                         │   │
│  │  └── Species detected: 8                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                  Regional Species Context                            │   │
│  │                                                                      │   │
│  │  Based on GPS location, expected species:                           │   │
│  │                                                                      │   │
│  │  Common (>50% of sites)        │  Occasional (10-50%)              │   │
│  │  ───────────────────────────── │  ────────────────────────────────  │   │
│  │  ✓ Eptesicus fuscus           │  ◐ Lasiurus cinereus              │   │
│  │  ✓ Lasiurus borealis          │  ◐ Myotis septentrionalis         │   │
│  │  ✓ Myotis lucifugus           │  ◐ Perimyotis subflavus           │   │
│  │                                │                                    │   │
│  │  Rare/Special Interest         │  Not Expected                     │   │
│  │  ───────────────────────────── │  ────────────────────────────────  │   │
│  │  ○ Myotis sodalis (ESA)       │  ✗ Tadarida brasiliensis          │   │
│  │  ○ Myotis leibii              │  ✗ Eumops floridanus              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Map Integration Components

```typescript
// Leaflet/Mapbox integration for geospatial visualization
interface GeoVisualizationConfig {
  mapProvider: 'mapbox' | 'leaflet' | 'google';
  basemaps: {
    satellite: string;
    terrain: string;
    streets: string;
  };
  overlays: {
    species_ranges: boolean;
    habitat_classification: boolean;
    activity_heatmap: boolean;
    survey_sites: boolean;
  };
}

class BatActivityMap {
  private map: L.Map;
  private siteLayers: L.LayerGroup;
  private heatmapLayer: L.HeatLayer;
  private speciesRangeLayers: Map<string, L.GeoJSON>;

  public addSurveysite(site: SurveySite): void {
    const marker = L.circleMarker([site.lat, site.lng], {
      radius: this.scaleByActivity(site.total_calls),
      color: this.colorByDiversity(site.species_count),
      fillOpacity: 0.7
    });

    marker.bindPopup(this.createSitePopup(site));
    marker.on('click', () => this.onSiteSelect(site));

    this.siteLayers.addLayer(marker);
  }

  public generateActivityHeatmap(recordings: Recording[]): void {
    const points = recordings.flatMap(r =>
      r.calls.map(c => [r.latitude, r.longitude, c.confidence])
    );

    this.heatmapLayer.setLatLngs(points);
  }

  public showSpeciesRange(speciesId: string): void {
    fetch(`/api/species/${speciesId}/range`)
      .then(r => r.json())
      .then(geojson => {
        const layer = L.geoJSON(geojson, {
          style: {
            color: SPECIES_COLORS[speciesId],
            weight: 2,
            fillOpacity: 0.2
          }
        });
        this.speciesRangeLayers.set(speciesId, layer);
        layer.addTo(this.map);
      });
  }
}
```

### 3.3 Habitat Context Integration

```python
class HabitatContextProvider:
    """
    Provides habitat and environmental context based on GPS coordinates
    """

    def __init__(self):
        self.landcover_api = NLCDLandcoverAPI()
        self.elevation_api = USGSElevationAPI()
        self.water_features_api = NHDWaterFeaturesAPI()

    def get_habitat_context(self, lat: float, lon: float) -> HabitatContext:
        """
        Retrieve comprehensive habitat information for a location
        """
        return HabitatContext(
            landcover=self.landcover_api.get_classification(lat, lon),
            landcover_percentages=self.landcover_api.get_buffer_percentages(
                lat, lon, buffer_km=1.0
            ),
            elevation_m=self.elevation_api.get_elevation(lat, lon),
            distance_to_water_m=self.water_features_api.nearest_water(lat, lon),
            water_body_type=self.water_features_api.water_body_type(lat, lon),
            forest_edge_distance_m=self.calculate_forest_edge_distance(lat, lon),
            urban_proximity_km=self.calculate_urban_proximity(lat, lon),
            roost_potential_score=self.estimate_roost_potential(lat, lon)
        )

    def adjust_species_priors(self, base_priors: Dict[str, float],
                              habitat: HabitatContext) -> Dict[str, float]:
        """
        Adjust species classification priors based on habitat
        """
        adjusted = {}

        for species_id, prior in base_priors.items():
            species_habitat_prefs = SPECIES_HABITAT_PREFERENCES[species_id]

            # Calculate habitat suitability multiplier
            suitability = self._calculate_suitability(
                species_habitat_prefs,
                habitat
            )

            adjusted[species_id] = prior * suitability

        # Renormalize
        total = sum(adjusted.values())
        return {k: v/total for k, v in adjusted.items()}
```

---

## 4. Real-Time Visualization Features

### 4.1 Live Spectrogram Streaming

```typescript
class LiveSpectrogramViewer {
  private audioContext: AudioContext;
  private analyser: AnalyserNode;
  private canvas: HTMLCanvasElement;
  private spectrogramBuffer: Float32Array[];
  private webSocket: WebSocket;

  constructor(config: LiveViewerConfig) {
    this.initAudioPipeline(config);
    this.initVisualization(config.canvas);
    this.initWebSocket(config.streamUrl);
  }

  private async initAudioPipeline(config: LiveViewerConfig): Promise<void> {
    this.audioContext = new AudioContext({ sampleRate: 256000 });

    // Connect to ultrasonic microphone or SDR
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 256000,
        channelCount: 1,
        echoCancellation: false,
        noiseSuppression: false
      }
    });

    const source = this.audioContext.createMediaStreamSource(stream);

    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 2048;
    this.analyser.smoothingTimeConstant = 0.3;

    source.connect(this.analyser);
  }

  private renderFrame(): void {
    const freqData = new Float32Array(this.analyser.frequencyBinCount);
    this.analyser.getFloatFrequencyData(freqData);

    // Shift buffer and add new frame
    this.spectrogramBuffer.shift();
    this.spectrogramBuffer.push(freqData);

    // Render to canvas
    this.drawSpectrogram();

    // Run real-time detection
    this.detectCalls(freqData);

    requestAnimationFrame(() => this.renderFrame());
  }

  private detectCalls(freqData: Float32Array): void {
    // Simple energy-based detection for real-time feedback
    const batBandEnergy = this.calculateBandEnergy(freqData, 20000, 100000);

    if (batBandEnergy > this.detectionThreshold) {
      this.triggerCallDetected(freqData);

      // Send to server for full classification
      this.webSocket.send(JSON.stringify({
        type: 'call_detected',
        timestamp: Date.now(),
        spectrum: Array.from(freqData)
      }));
    }
  }
}
```

### 4.2 Synchronized Multi-View Display

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multi-Panel Visualization Layout                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌────────────────────────────┐  ┌────────────────────────────┐            │
│  │                            │  │                            │            │
│  │   2D Spectrogram           │  │   3D Surface View          │            │
│  │   (Traditional View)       │  │   (Rotatable)              │            │
│  │                            │  │                            │            │
│  │   ▓▓▓▓▓▓                   │  │      ╱╲                    │            │
│  │   ▓▓▓▓▓▓▓▓                 │  │     ╱  ╲                   │            │
│  │   ▓▓▓▓▓▓▓▓▓▓               │  │    ╱    ╲                  │            │
│  │                            │  │                            │            │
│  └────────────────────────────┘  └────────────────────────────┘            │
│                                                                             │
│  ┌────────────────────────────┐  ┌────────────────────────────┐            │
│  │                            │  │                            │            │
│  │   Waveform                 │  │   Call Parameter Plot      │            │
│  │   (Time Domain)            │  │   (Fc over time)           │            │
│  │                            │  │                            │            │
│  │   ∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿      │  │   •  •                     │            │
│  │                            │  │     •  •  •                │            │
│  │                            │  │          •  •  •           │            │
│  │                            │  │                            │            │
│  └────────────────────────────┘  └────────────────────────────┘            │
│                                                                             │
│  ◄─────────────────── Time Navigation ───────────────────────►            │
│  [|◄] [◄◄] [►||] [►►] [►|]   00:15.234 / 05:00.000   [🔍+] [🔍-]          │
│                                                                             │
│  All views synchronized - click/select in any panel to highlight in all    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Export & Sharing Capabilities

### 5.1 Export Formats

| Format | Use Case | Includes |
|--------|----------|----------|
| **PNG/SVG** | Publication figures | Static spectrogram with annotations |
| **MP4/WebM** | Presentations | Animated 3D rotation, time playback |
| **glTF/OBJ** | 3D printing, external tools | Full 3D mesh with textures |
| **JSON** | Data interchange | All measurements and parameters |
| **CSV** | Spreadsheet analysis | Call parameters tabular data |
| **KML/GeoJSON** | GIS integration | Georeferenced activity data |

### 5.2 Annotation & Collaboration

```typescript
interface AnnotationSystem {
  // User annotations
  addTextAnnotation(position: TimeFreqPoint, text: string): Annotation;
  addMeasurement(start: TimeFreqPoint, end: TimeFreqPoint): Measurement;
  addRegionOfInterest(bounds: TimeFreqBounds, label: string): Region;

  // Collaboration features
  shareAnnotations(projectId: string, annotations: Annotation[]): void;
  loadSharedAnnotations(projectId: string): Annotation[];

  // Version control
  saveAnnotationSnapshot(name: string): SnapshotId;
  restoreSnapshot(snapshotId: SnapshotId): void;
  compareSnapshots(a: SnapshotId, b: SnapshotId): AnnotationDiff;
}
```

---

## 6. Performance Optimization

### 6.1 WebGL Rendering Optimization

```typescript
class SpectrogramOptimizer {
  // Level-of-detail management
  private lodLevels: LODLevel[] = [
    { distance: 0, resolution: 'full' },      // < 100 pixels away
    { distance: 100, resolution: 'half' },    // 100-500 pixels
    { distance: 500, resolution: 'quarter' }, // > 500 pixels
  ];

  // Frustum culling for large spectrograms
  private cullInvisibleRegions(viewport: Viewport): void {
    const visible = this.calculateVisibleBounds(viewport);
    this.mesh.geometry.setDrawRange(visible.start, visible.count);
  }

  // Texture atlasing for multiple spectrograms
  private createTextureAtlas(spectrograms: Spectrogram[]): TextureAtlas {
    // Pack multiple spectrograms into single GPU texture
    return new TextureAtlas(spectrograms, {
      maxSize: 4096,
      padding: 2,
      format: 'RGB'
    });
  }

  // Progressive loading for long recordings
  private async loadProgressive(audioUrl: string): Promise<void> {
    const chunkSize = 60; // seconds

    for await (const chunk of this.streamAudioChunks(audioUrl, chunkSize)) {
      const spectrogram = await this.computeSpectrogram(chunk);
      this.appendToVisualization(spectrogram);
      await this.waitForIdle(); // Don't block UI
    }
  }
}
```

### 6.2 Memory Management

| Data Type | Strategy | Target Memory |
|-----------|----------|---------------|
| Raw audio | Stream from disk | 0 (not kept in RAM) |
| Spectrogram | Float16 quantization | 50% reduction |
| 3D mesh | LOD + culling | Dynamic |
| Textures | Compressed (BC1/BC3) | 75% reduction |
| Call data | IndexedDB caching | Persistent |
