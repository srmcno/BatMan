# Reporting & Compliance - Technical Specification

## Overview

This document specifies the automated reporting capabilities and compliance features of EcoEcho AI, including one-click NABat and USFWS report generation, API integrations with enterprise systems, and comprehensive data export options.

---

## 1. One-Click Compliance Reporting

### 1.1 Supported Compliance Standards

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Compliance Report Standards                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  NABat (North American Bat Monitoring Program)                       │   │
│  │                                                                      │   │
│  │  Standards Supported:                                                │   │
│  │  • NABat Stationary Acoustic Survey Protocol v1.0                   │   │
│  │  • NABat Mobile Acoustic Survey Protocol v1.0                       │   │
│  │  • NABat Guano Data Collection Protocol                             │   │
│  │  • NABat Capture Data Protocol                                      │   │
│  │                                                                      │   │
│  │  Output Formats:                                                     │   │
│  │  • NABat Partner Portal CSV upload format                           │   │
│  │  • NABat GeoJSON spatial data                                       │   │
│  │  • NABat standardized species codes                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  USFWS (U.S. Fish & Wildlife Service)                                │   │
│  │                                                                      │   │
│  │  Standards Supported:                                                │   │
│  │  • Section 7 Consultation Documentation                             │   │
│  │  • Indiana Bat/NLEB Survey Protocols (Range-wide)                   │   │
│  │  • Habitat Conservation Plan (HCP) monitoring                       │   │
│  │  • ESA Section 10 permit compliance                                 │   │
│  │                                                                      │   │
│  │  Output Formats:                                                     │   │
│  │  • USFWS Standard Survey Report Template                            │   │
│  │  • IPaC (Information for Planning and Consultation) compatible      │   │
│  │  • Environmental Assessment appendix format                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  State Agency Formats                                                │   │
│  │                                                                      │   │
│  │  • State Natural Heritage Program formats (all 50 states)           │   │
│  │  • State-specific endangered species documentation                  │   │
│  │  • Wind energy pre-construction survey formats                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  International Standards                                             │   │
│  │                                                                      │   │
│  │  • EUROBATS guidelines (European bat surveys)                       │   │
│  │  • Bat Conservation Trust (UK) survey standards                     │   │
│  │  • IUCN Red List assessment data format                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 NABat Report Generator

```typescript
interface NABatReportConfig {
  // Survey metadata
  survey_type: 'stationary' | 'mobile' | 'mist_net' | 'roost_count';
  project_id: string;
  nabat_project_id?: string;  // If registered with NABat

  // Location data
  grts_cell_id: string;       // NABat GRTS cell identifier
  site_name: string;
  coordinates: {
    latitude: number;
    longitude: number;
    datum: 'WGS84' | 'NAD83';
  };

  // Survey details
  survey_dates: DateRange;
  detector_info: {
    make: string;
    model: string;
    microphone: string;
    settings: RecorderSettings;
  };

  // Classification settings
  classification_method: 'EcoEcho_AI' | 'manual' | 'hybrid';
  vetting_level: 'auto' | 'quick_review' | 'full_review' | 'expert_review';

  // Output preferences
  include_raw_data: boolean;
  include_spectrograms: boolean;
  include_audio_files: boolean;
}

class NABatReportGenerator {
  async generateReport(
    project: Project,
    config: NABatReportConfig
  ): Promise<NABatReportBundle> {
    // Validate data completeness
    await this.validateRequiredFields(project, config);

    // Generate core CSV files
    const csvBundle = await this.generateCSVBundle(project, config);

    // Generate spatial data
    const geoJson = await this.generateGeoJSON(project);

    // Generate summary statistics
    const summaryStats = await this.calculateSummaryStatistics(project);

    // Generate species list with NABat codes
    const speciesList = await this.generateSpeciesList(project);

    // Package for NABat Partner Portal upload
    return {
      survey_data_csv: csvBundle.surveyData,
      acoustic_data_csv: csvBundle.acousticData,
      species_detections_csv: csvBundle.speciesDetections,
      site_locations_geojson: geoJson,
      summary_report_pdf: await this.generateSummaryPDF(summaryStats),
      upload_manifest: this.generateManifest(csvBundle)
    };
  }

  private generateCSVBundle(project: Project, config: NABatReportConfig): CSVBundle {
    // NABat-compliant CSV structure
    return {
      surveyData: this.formatSurveyDataCSV({
        columns: [
          'GRTS_Cell_ID', 'Site_Name', 'Latitude', 'Longitude',
          'Survey_Start_Date', 'Survey_End_Date', 'Survey_Type',
          'Detector_Make', 'Detector_Model', 'Microphone_Type',
          'Sample_Rate_kHz', 'Trigger_Type', 'Recording_Length_s',
          'Total_Survey_Nights', 'Total_Recording_Hours'
        ],
        data: project.surveys.map(s => this.formatSurveyRow(s))
      }),

      acousticData: this.formatAcousticDataCSV({
        columns: [
          'Recording_ID', 'Site_Name', 'Night_Date', 'Recording_Time',
          'File_Name', 'Duration_s', 'Species_Code', 'Species_Common',
          'Auto_ID_Confidence', 'Manual_Vet_Status', 'Final_ID',
          'Call_Count', 'Activity_Type'
        ],
        data: project.recordings.flatMap(r =>
          r.classifications.map(c => this.formatAcousticRow(r, c))
        )
      }),

      speciesDetections: this.formatSpeciesDetectionsCSV({
        columns: [
          'Site_Name', 'Species_Code', 'Species_Common', 'Species_Scientific',
          'Total_Detections', 'Nights_Detected', 'First_Detection_Date',
          'Last_Detection_Date', 'Detection_Rate_per_Night',
          'Confidence_Category', 'ESA_Status'
        ],
        data: this.aggregateSpeciesDetections(project)
      })
    };
  }
}
```

### 1.3 USFWS Report Generator

```typescript
interface USFWSReportConfig {
  report_type: 'section_7' | 'section_10' | 'hcp_monitoring' | 'survey_summary';
  project_name: string;
  permit_number?: string;
  lead_surveyor: {
    name: string;
    permit_id: string;
    organization: string;
  };

  // Species of concern
  target_species: string[];  // e.g., ['MYSO', 'MYSE'] for Indiana/NLEB

  // Survey protocol followed
  protocol_version: string;
  protocol_deviations?: string[];

  // Weather data
  include_weather: boolean;
  weather_source: 'recorded' | 'nearby_station' | 'estimated';
}

class USFWSReportGenerator {
  async generateSection7Report(
    project: Project,
    config: USFWSReportConfig
  ): Promise<Section7Report> {
    return {
      // Executive Summary
      executive_summary: await this.generateExecutiveSummary(project, config),

      // Survey Methods
      methods_section: {
        survey_dates: this.formatSurveyDates(project),
        survey_locations: this.formatLocationDescriptions(project),
        equipment_used: this.formatEquipmentList(project),
        protocol_adherence: this.assessProtocolAdherence(project, config),
        weather_conditions: await this.getWeatherSummary(project, config),
        personnel: this.formatPersonnelCredentials(config)
      },

      // Results
      results_section: {
        species_detected: await this.generateSpeciesTable(project, config.target_species),
        activity_summary: this.generateActivitySummary(project),
        temporal_patterns: this.analyzeTemporalPatterns(project),
        spatial_distribution: await this.analyzeSpatialDistribution(project),
        endangered_species_findings: this.highlightEndangeredFindings(project, config)
      },

      // Supporting Materials
      appendices: {
        nightly_summaries: this.generateNightlySummaries(project),
        species_spectrograms: await this.compileSpeciesSpectrograms(project),
        site_photographs: project.sitePhotos,
        raw_data_tables: this.generateRawDataTables(project),
        qaqc_documentation: this.generateQAQCReport(project)
      },

      // Compliance Certification
      certification: {
        surveyor_signature_block: true,
        data_quality_statement: this.generateDataQualityStatement(project),
        limitations_disclaimer: this.generateLimitationsDisclaimer(config)
      }
    };
  }

  private highlightEndangeredFindings(
    project: Project,
    config: USFWSReportConfig
  ): EndangeredSpeciesFindings {
    const findings: EndangeredSpeciesFindings = {
      species_found: [],
      species_not_detected: [],
      inconclusive: []
    };

    for (const species of config.target_species) {
      const detections = project.getDetectionsForSpecies(species);

      if (detections.length === 0) {
        findings.species_not_detected.push({
          species_code: species,
          survey_effort: this.calculateSurveyEffort(project),
          conclusion: 'Not detected during survey period'
        });
      } else if (detections.every(d => d.confidence >= 0.90 && d.vetted)) {
        findings.species_found.push({
          species_code: species,
          detection_count: detections.length,
          nights_detected: this.countNightsDetected(detections),
          first_detection: detections[0].timestamp,
          confidence_assessment: 'High confidence - verified detections',
          supporting_evidence: this.compileEvidence(detections)
        });
      } else {
        findings.inconclusive.push({
          species_code: species,
          detection_count: detections.length,
          reason: 'Low confidence or unvetted detections require expert review',
          recommended_action: 'Additional survey effort or expert verification recommended'
        });
      }
    }

    return findings;
  }
}
```

### 1.4 Report Generation UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Generate Compliance Report                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Project: Meadow Wind Farm Pre-Construction Survey 2024                     │
│                                                                             │
│  ┌─ Report Type ───────────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  ● NABat Standard Report                                               ││
│  │    └─ For upload to NABat Partner Portal                               ││
│  │                                                                         ││
│  │  ○ USFWS Section 7 Report                                              ││
│  │    └─ For ESA consultation documentation                               ││
│  │                                                                         ││
│  │  ○ State Natural Heritage Report                                       ││
│  │    └─ State: [Pennsylvania ▼]                                          ││
│  │                                                                         ││
│  │  ○ Custom Report Template                                              ││
│  │    └─ Template: [Select template... ▼]                                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ NABat Configuration ───────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  GRTS Cell ID:     [A12B34_SW ▼]     Auto-detected from GPS ✓          ││
│  │  NABat Project ID: [PRJ-2024-1234  ]  (Optional - for linked projects) ││
│  │                                                                         ││
│  │  Survey Type:      [Stationary Acoustic ▼]                             ││
│  │                                                                         ││
│  │  Classification Method:                                                ││
│  │    ● EcoEcho AI (Auto-classified)                                      ││
│  │    ○ Hybrid (AI + Manual Vetting)                                      ││
│  │    ○ Manual Only                                                       ││
│  │                                                                         ││
│  │  Include in Report:                                                    ││
│  │    ☑ Summary Statistics PDF                                            ││
│  │    ☑ Species Detection Maps                                            ││
│  │    ☑ Nightly Activity Charts                                           ││
│  │    ☐ Representative Spectrograms (adds ~50MB)                          ││
│  │    ☐ Raw Audio Files (adds ~2GB)                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Data Quality Check ────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  ✓ All required fields complete                                        ││
│  │  ✓ GPS coordinates validated                                           ││
│  │  ✓ Species codes match NABat standards                                 ││
│  │  ⚠ 23 low-confidence detections not yet vetted                        ││
│  │    └─ [Review Now] or include as "Unconfirmed"                        ││
│  │  ✓ Survey dates within acceptable range                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Preview Report]  [Generate & Download]  [Generate & Upload to NABat]     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Activity Density Heatmaps

### 2.1 Heatmap Generation Engine

```typescript
interface HeatmapConfig {
  // Spatial configuration
  spatial_resolution: 'site' | 'grid_10m' | 'grid_50m' | 'grid_100m';
  projection: 'WGS84' | 'UTM' | 'state_plane';
  bounds?: GeoBounds;

  // Temporal configuration
  temporal_resolution: 'hourly' | 'nightly' | 'weekly' | 'monthly' | 'seasonal';
  time_range: DateRange;

  // Data configuration
  metric: 'total_calls' | 'species_richness' | 'activity_index' | 'feeding_buzzes';
  species_filter?: string[];
  normalize: boolean;

  // Visual configuration
  colormap: 'viridis' | 'magma' | 'plasma' | 'hot' | 'custom';
  opacity: number;
  interpolation: 'none' | 'bilinear' | 'idw';
}

class ActivityHeatmapGenerator {
  async generateHeatmap(
    project: Project,
    config: HeatmapConfig
  ): Promise<HeatmapResult> {
    // Aggregate data by spatial/temporal bins
    const aggregatedData = await this.aggregateActivity(project, config);

    // Calculate activity density
    const densityGrid = this.calculateDensity(aggregatedData, config);

    // Apply normalization if requested
    if (config.normalize) {
      this.normalizeByEffort(densityGrid, project.surveyEffort);
    }

    // Generate visualization layers
    return {
      raster: this.generateRasterLayer(densityGrid, config),
      contours: this.generateContourLines(densityGrid),
      geojson: this.generateGeoJSONLayer(densityGrid),
      legend: this.generateLegend(densityGrid, config),
      statistics: this.calculateStatistics(densityGrid)
    };
  }

  private calculateDensity(
    data: AggregatedActivityData,
    config: HeatmapConfig
  ): DensityGrid {
    const grid = new DensityGrid(config.bounds, config.spatial_resolution);

    for (const point of data.points) {
      const cell = grid.getCellForCoordinate(point.latitude, point.longitude);

      switch (config.metric) {
        case 'total_calls':
          cell.value += point.call_count;
          break;
        case 'species_richness':
          cell.species.add(...point.species_detected);
          cell.value = cell.species.size;
          break;
        case 'activity_index':
          // Calls per detector-night
          cell.value = point.call_count / point.survey_nights;
          break;
        case 'feeding_buzzes':
          cell.value += point.feeding_buzz_count;
          break;
      }
    }

    // Apply interpolation for smoother visualization
    if (config.interpolation !== 'none') {
      this.applyInterpolation(grid, config.interpolation);
    }

    return grid;
  }
}
```

### 2.2 Heatmap Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Activity Density Heatmap                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                                                                       │  │
│  │                    [Interactive Map with Heatmap Overlay]             │  │
│  │                                                                       │  │
│  │    ┌─────────────────────────────────────────────────────────────┐   │  │
│  │    │                                                             │   │  │
│  │    │     ░░░░░░░░░░▒▒▒▒▒▒▒▒░░░░░░░░                             │   │  │
│  │    │   ░░░░░░░▒▒▒▒▒▒▓▓▓▓▓▓▒▒▒▒░░░░░░░                           │   │  │
│  │    │  ░░░░░▒▒▒▒▓▓▓▓▓▓████▓▓▓▓▒▒▒░░░░░   ← High activity area   │   │  │
│  │    │   ░░░░░▒▒▒▒▓▓▓▓▓▓▓▓▓▓▒▒▒▒░░░░░                             │   │  │
│  │    │    ░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒░░░░░░░                               │   │  │
│  │    │      ░░░░░░░░░░░░░░░░░░                    ○ Detector      │   │  │
│  │    │                                            site           │   │  │
│  │    │                    ░░░▒▒▒░░░                               │   │  │
│  │    │                   ░▒▒▓▓▓▒▒░   ← Secondary hotspot         │   │  │
│  │    │                    ░░▒▒▒░░                                 │   │  │
│  │    │                                                             │   │  │
│  │    └─────────────────────────────────────────────────────────────┘   │  │
│  │                                                                       │  │
│  │  Legend: Calls per Detector-Night                                    │  │
│  │  ░ 0-10  ▒ 11-50  ▓ 51-100  █ >100                                  │  │
│  │                                                                       │  │
│  │  [Satellite] [Terrain] [Toggle Heatmap] [Export]                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ Temporal Slider ───────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  June 2024                                                July 2024   ││
│  │  ├────────────────────●──────────────────────────────────────────────┤ ││
│  │                       ▲                                                ││
│  │                  Week of June 15                                       ││
│  │                                                                         ││
│  │  [◄ Prev Week]  [▶ Play Animation]  [Next Week ►]                     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  Statistics for Selected Period:                                           │
│  • Total Calls: 12,456  • Active Sites: 8/12  • Peak Night: June 18       │
│  • Dominant Species: Eptesicus fuscus (45%)                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Species Diversity Indices

### 3.1 Diversity Metrics Calculator

```typescript
interface DiversityMetrics {
  // Alpha diversity (within-site)
  species_richness: number;           // S: total number of species
  shannon_index: number;              // H': -Σ(pi × ln(pi))
  simpson_index: number;              // D: 1 - Σ(pi²)
  inverse_simpson: number;            // 1/D
  pielou_evenness: number;            // J': H'/ln(S)
  chao1_estimator: number;            // Estimated true richness

  // Abundance metrics
  total_detections: number;
  detection_rate: number;             // Detections per detector-night
  dominance_index: number;            // Proportion of most common species

  // Temporal metrics
  seasonal_turnover: number;          // Beta diversity across seasons
  nightly_variation_cv: number;       // Coefficient of variation
}

class DiversityCalculator {
  calculateAlphaDiversity(detections: SpeciesDetection[]): DiversityMetrics {
    // Group by species
    const speciesCounts = this.groupBySpecies(detections);
    const totalDetections = detections.length;
    const speciesRichness = speciesCounts.size;

    // Calculate proportions
    const proportions = new Map<string, number>();
    for (const [species, count] of speciesCounts) {
      proportions.set(species, count / totalDetections);
    }

    // Shannon Index: H' = -Σ(pi × ln(pi))
    let shannonIndex = 0;
    for (const p of proportions.values()) {
      if (p > 0) {
        shannonIndex -= p * Math.log(p);
      }
    }

    // Simpson Index: D = Σ(pi²)
    let simpsonSum = 0;
    for (const p of proportions.values()) {
      simpsonSum += p * p;
    }
    const simpsonIndex = 1 - simpsonSum;  // Gini-Simpson

    // Pielou's Evenness: J' = H'/ln(S)
    const pielou = speciesRichness > 1
      ? shannonIndex / Math.log(speciesRichness)
      : 1;

    // Chao1 Estimator for true richness
    const singletons = [...speciesCounts.values()].filter(c => c === 1).length;
    const doubletons = [...speciesCounts.values()].filter(c => c === 2).length;
    const chao1 = doubletons > 0
      ? speciesRichness + (singletons * singletons) / (2 * doubletons)
      : speciesRichness + (singletons * (singletons - 1)) / 2;

    return {
      species_richness: speciesRichness,
      shannon_index: shannonIndex,
      simpson_index: simpsonIndex,
      inverse_simpson: 1 / simpsonSum,
      pielou_evenness: pielou,
      chao1_estimator: chao1,
      total_detections: totalDetections,
      detection_rate: totalDetections / this.surveyNights,
      dominance_index: Math.max(...proportions.values())
    };
  }

  calculateBetaDiversity(
    siteA: SpeciesDetection[],
    siteB: SpeciesDetection[]
  ): BetaDiversityMetrics {
    const speciesA = new Set(siteA.map(d => d.species_id));
    const speciesB = new Set(siteB.map(d => d.species_id));

    const intersection = new Set([...speciesA].filter(s => speciesB.has(s)));
    const union = new Set([...speciesA, ...speciesB]);

    // Jaccard Similarity: J = |A ∩ B| / |A ∪ B|
    const jaccard = intersection.size / union.size;

    // Sørensen-Dice: SD = 2|A ∩ B| / (|A| + |B|)
    const sorensen = (2 * intersection.size) / (speciesA.size + speciesB.size);

    // Whittaker's Beta: β = γ/α - 1
    const meanAlpha = (speciesA.size + speciesB.size) / 2;
    const gamma = union.size;
    const whittaker = gamma / meanAlpha - 1;

    return {
      jaccard_similarity: jaccard,
      jaccard_dissimilarity: 1 - jaccard,
      sorensen_dice: sorensen,
      whittaker_beta: whittaker,
      shared_species: intersection.size,
      unique_to_a: speciesA.size - intersection.size,
      unique_to_b: speciesB.size - intersection.size
    };
  }
}
```

### 3.2 Diversity Report Visualization

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Species Diversity Analysis                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Alpha Diversity by Site ───────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Site          │ Richness │ Shannon │ Simpson │ Evenness │ Detections  ││
│  │  ──────────────┼──────────┼─────────┼─────────┼──────────┼─────────────││
│  │  Meadow North  │    8     │  1.82   │  0.78   │   0.87   │   1,234     ││
│  │  Forest Edge   │   11     │  2.12   │  0.85   │   0.89   │   2,456     ││
│  │  Wetland South │    6     │  1.43   │  0.71   │   0.80   │     567     ││
│  │  Ridge Top     │    5     │  1.21   │  0.65   │   0.75   │     345     ││
│  │  ──────────────┼──────────┼─────────┼─────────┼──────────┼─────────────││
│  │  Project Total │   12     │  2.05   │  0.82   │   0.83   │   4,602     ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Species Accumulation Curve ───────────┐ ┌─ Rank Abundance ─────────────┐│
│  │                                        │ │                              ││
│  │  Species │                             │ │  E. fuscus  ████████████ 45%││
│  │    12   ─┤            ●────────────●   │ │  L. borealis ███████    28%││
│  │    10   ─┤        ●                    │ │  M. lucifugus ████      12%││
│  │     8   ─┤     ●                       │ │  L. noctivag. ██        8% ││
│  │     6   ─┤   ●                         │ │  P. subflavus █         4% ││
│  │     4   ─┤  ●                          │ │  Other (7 sp) █         3% ││
│  │     2   ─┤●                            │ │                              ││
│  │     0   ─┴─────────────────────────    │ │  Dominance Index: 0.45     ││
│  │           5   10  15  20  25  30       │ │  (Moderate - healthy)       ││
│  │              Survey Nights             │ │                              ││
│  │                                        │ │  Chao1 Est.: 14 species     ││
│  │  ● Observed  ─ Chao1 estimate          │ │  (86% detected)             ││
│  └────────────────────────────────────────┘ └──────────────────────────────┘│
│                                                                             │
│  ┌─ Beta Diversity Matrix (Jaccard Dissimilarity) ─────────────────────────┐│
│  │                                                                         ││
│  │              │ Meadow N │ Forest E │ Wetland S │ Ridge T                ││
│  │  ────────────┼──────────┼──────────┼───────────┼─────────               ││
│  │  Meadow N    │   0.00   │   0.27   │   0.42    │  0.55                  ││
│  │  Forest E    │   0.27   │   0.00   │   0.35    │  0.48                  ││
│  │  Wetland S   │   0.42   │   0.35   │   0.00    │  0.38                  ││
│  │  Ridge T     │   0.55   │   0.48   │   0.38    │  0.00                  ││
│  │                                                                         ││
│  │  Interpretation: Forest Edge and Meadow North most similar (0.27)      ││
│  │                  Meadow North and Ridge Top most different (0.55)      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Export to PDF] [Export to CSV] [Add to Report]                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. API Integration

### 4.1 REST API Specification

```yaml
openapi: 3.0.0
info:
  title: EcoEcho AI Integration API
  version: 2.0.0
  description: API for integrating EcoEcho AI with external systems

paths:
  /api/v2/reports/generate:
    post:
      summary: Generate compliance report
      tags: [Reports]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                project_id:
                  type: string
                  format: uuid
                report_type:
                  type: string
                  enum: [nabat, usfws_section7, custom]
                config:
                  $ref: '#/components/schemas/ReportConfig'
      responses:
        202:
          description: Report generation started
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status_url:
                    type: string
                  estimated_completion:
                    type: string
                    format: date-time

  /api/v2/data/export:
    post:
      summary: Export project data
      tags: [Data Export]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                project_id:
                  type: string
                format:
                  type: string
                  enum: [csv, json, geojson, shapefile, xlsx]
                filters:
                  $ref: '#/components/schemas/DataFilters'
                columns:
                  type: array
                  items:
                    type: string
      responses:
        200:
          description: Data export (for small datasets)
          content:
            application/octet-stream:
              schema:
                type: string
                format: binary
        202:
          description: Large export queued
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AsyncJobResponse'

  /api/v2/webhooks:
    post:
      summary: Register webhook for events
      tags: [Webhooks]
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                url:
                  type: string
                  format: uri
                events:
                  type: array
                  items:
                    type: string
                    enum:
                      - batch.completed
                      - classification.updated
                      - report.generated
                      - endangered_species.detected
                secret:
                  type: string
                  description: Shared secret for signature verification
      responses:
        201:
          description: Webhook registered

  /api/v2/analytics/diversity:
    get:
      summary: Get diversity metrics
      tags: [Analytics]
      parameters:
        - name: project_id
          in: query
          required: true
          schema:
            type: string
        - name: site_ids
          in: query
          schema:
            type: array
            items:
              type: string
        - name: date_range
          in: query
          schema:
            type: string
            example: "2024-06-01/2024-08-31"
      responses:
        200:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/DiversityMetrics'

components:
  schemas:
    ReportConfig:
      type: object
      properties:
        template:
          type: string
        include_spectrograms:
          type: boolean
        include_maps:
          type: boolean
        species_filter:
          type: array
          items:
            type: string

    DiversityMetrics:
      type: object
      properties:
        alpha_diversity:
          type: object
          properties:
            species_richness:
              type: integer
            shannon_index:
              type: number
            simpson_index:
              type: number
            pielou_evenness:
              type: number
        beta_diversity:
          type: object
          additionalProperties:
            type: number
```

### 4.2 SharePoint Integration

```typescript
class SharePointIntegration {
  private graphClient: GraphClient;

  constructor(config: SharePointConfig) {
    this.graphClient = new GraphClient({
      tenantId: config.tenantId,
      clientId: config.clientId,
      clientSecret: config.clientSecret
    });
  }

  async pushToList(
    siteId: string,
    listName: string,
    data: ClassificationSummary[]
  ): Promise<void> {
    const listId = await this.getOrCreateList(siteId, listName);

    // Transform data to SharePoint list item format
    const listItems = data.map(item => ({
      fields: {
        Title: item.recording_id,
        Species: item.species_name,
        Confidence: item.confidence,
        SiteLocation: item.site_name,
        RecordingDate: item.timestamp,
        Latitude: item.latitude,
        Longitude: item.longitude,
        CallCount: item.call_count,
        ActivityType: item.activity_type,
        ReviewStatus: item.review_status,
        Reviewer: item.reviewer_email
      }
    }));

    // Batch create items (max 20 per batch)
    for (const batch of this.chunkArray(listItems, 20)) {
      await this.graphClient.batchCreateListItems(siteId, listId, batch);
    }
  }

  async uploadReport(
    siteId: string,
    folderPath: string,
    report: ReportBundle
  ): Promise<DriveItem> {
    // Upload main report PDF
    const mainReport = await this.graphClient.uploadFile(
      siteId,
      `${folderPath}/${report.filename}`,
      report.content
    );

    // Upload supporting files to subfolder
    const supportingFolder = `${folderPath}/Supporting_Materials`;
    await this.graphClient.createFolder(siteId, supportingFolder);

    for (const attachment of report.attachments) {
      await this.graphClient.uploadFile(
        siteId,
        `${supportingFolder}/${attachment.filename}`,
        attachment.content
      );
    }

    return mainReport;
  }

  private async getOrCreateList(
    siteId: string,
    listName: string
  ): Promise<string> {
    try {
      const list = await this.graphClient.getList(siteId, listName);
      return list.id;
    } catch (error) {
      if (error.code === 'itemNotFound') {
        // Create list with EcoEcho schema
        const newList = await this.graphClient.createList(siteId, {
          displayName: listName,
          columns: ECOECHO_SHAREPOINT_COLUMNS,
          list: { template: 'genericList' }
        });
        return newList.id;
      }
      throw error;
    }
  }
}

const ECOECHO_SHAREPOINT_COLUMNS = [
  { name: 'Species', text: {} },
  { name: 'Confidence', number: { decimalPlaces: 2 } },
  { name: 'SiteLocation', text: {} },
  { name: 'RecordingDate', dateTime: {} },
  { name: 'Latitude', number: { decimalPlaces: 6 } },
  { name: 'Longitude', number: { decimalPlaces: 6 } },
  { name: 'CallCount', number: {} },
  { name: 'ActivityType', choice: { choices: ['Commuting', 'Foraging', 'Social', 'Unknown'] } },
  { name: 'ReviewStatus', choice: { choices: ['Pending', 'Approved', 'Rejected', 'Needs Expert'] } },
  { name: 'Reviewer', personOrGroup: {} }
];
```

### 4.3 Power BI Integration

```typescript
class PowerBIIntegration {
  private credentials: PowerBICredentials;
  private datasetId: string;

  async pushDataToDataset(
    data: AnalyticsData
  ): Promise<void> {
    // Connect to Power BI streaming dataset
    const pushUrl = `https://api.powerbi.com/v1.0/myorg/datasets/${this.datasetId}/rows`;

    // Transform to Power BI schema
    const rows = this.transformToPowerBIFormat(data);

    // Push in batches of 10,000 rows
    for (const batch of this.chunkArray(rows, 10000)) {
      await this.httpClient.post(pushUrl, {
        headers: {
          'Authorization': `Bearer ${await this.getAccessToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ rows: batch })
      });
    }
  }

  async createStreamingDataset(): Promise<string> {
    const datasetDefinition = {
      name: 'EcoEcho Real-Time Analytics',
      defaultMode: 'Streaming',
      tables: [
        {
          name: 'Detections',
          columns: [
            { name: 'Timestamp', dataType: 'DateTime' },
            { name: 'SiteName', dataType: 'String' },
            { name: 'Species', dataType: 'String' },
            { name: 'Confidence', dataType: 'Double' },
            { name: 'Latitude', dataType: 'Double' },
            { name: 'Longitude', dataType: 'Double' },
            { name: 'CallCount', dataType: 'Int64' },
            { name: 'ActivityType', dataType: 'String' }
          ]
        },
        {
          name: 'HourlySummary',
          columns: [
            { name: 'Hour', dataType: 'DateTime' },
            { name: 'SiteName', dataType: 'String' },
            { name: 'TotalCalls', dataType: 'Int64' },
            { name: 'SpeciesCount', dataType: 'Int64' },
            { name: 'FeedingBuzzes', dataType: 'Int64' },
            { name: 'DominantSpecies', dataType: 'String' }
          ]
        }
      ]
    };

    const response = await this.httpClient.post(
      'https://api.powerbi.com/v1.0/myorg/datasets',
      {
        headers: {
          'Authorization': `Bearer ${await this.getAccessToken()}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(datasetDefinition)
      }
    );

    return response.id;
  }

  // Pre-built Power BI template
  getReportTemplate(): PowerBITemplate {
    return {
      pages: [
        {
          name: 'Overview Dashboard',
          visuals: [
            { type: 'card', measure: 'Total Detections' },
            { type: 'card', measure: 'Species Richness' },
            { type: 'card', measure: 'Active Sites' },
            { type: 'lineChart', axis: 'Date', values: ['Daily Calls'] },
            { type: 'pieChart', category: 'Species', value: 'Call Count' },
            { type: 'map', latitude: 'Latitude', longitude: 'Longitude', size: 'Call Count' }
          ]
        },
        {
          name: 'Species Analysis',
          visuals: [
            { type: 'barChart', axis: 'Species', value: 'Total Detections' },
            { type: 'matrix', rows: 'Site', columns: 'Species', values: 'Detections' },
            { type: 'treemap', category: 'Species', size: 'Proportion' }
          ]
        },
        {
          name: 'Temporal Patterns',
          visuals: [
            { type: 'heatmap', xAxis: 'Hour', yAxis: 'Date', value: 'Activity' },
            { type: 'lineChart', axis: 'Night', series: 'Species', value: 'Detections' }
          ]
        }
      ]
    };
  }
}
```

### 4.4 Integration Configuration UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  External Integrations                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ SharePoint Integration ────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Status: ● Connected                                                   ││
│  │                                                                         ││
│  │  Site: https://contoso.sharepoint.com/sites/BatSurveys                 ││
│  │  List: EcoEcho_Classifications                                         ││
│  │  Last Sync: 2024-07-15 14:32:00                                        ││
│  │                                                                         ││
│  │  Auto-sync:  ☑ Enabled                                                 ││
│  │  Frequency:  [Every 1 hour ▼]                                          ││
│  │  Data:       ☑ Classifications  ☑ Summaries  ☐ Raw files              ││
│  │                                                                         ││
│  │  [Test Connection] [Sync Now] [Configure] [Disconnect]                 ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Power BI Integration ──────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Status: ● Connected                                                   ││
│  │                                                                         ││
│  │  Workspace: Wildlife Analytics                                         ││
│  │  Dataset: EcoEcho_RealTime                                             ││
│  │  Report: Bat Survey Dashboard                                          ││
│  │                                                                         ││
│  │  Streaming:  ☑ Enabled (real-time updates)                            ││
│  │                                                                         ││
│  │  [Open in Power BI] [Refresh Dataset] [Download Template]              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ NABat Partner Portal ──────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Status: ○ Not Connected                                               ││
│  │                                                                         ││
│  │  [Connect NABat Account]                                               ││
│  │                                                                         ││
│  │  Benefits:                                                             ││
│  │  • Direct data upload to NABat                                        ││
│  │  • Automatic project synchronization                                   ││
│  │  • Access to NABat reference calls                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Webhooks ──────────────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Active Webhooks: 2                                                    ││
│  │                                                                         ││
│  │  ┌───────────────────────────────────────────────────────────────────┐ ││
│  │  │  Slack Notifications                                              │ ││
│  │  │  URL: https://hooks.slack.com/services/...                       │ ││
│  │  │  Events: endangered_species.detected, batch.completed            │ ││
│  │  │  Status: ● Active                              [Edit] [Delete]   │ ││
│  │  └───────────────────────────────────────────────────────────────────┘ ││
│  │  ┌───────────────────────────────────────────────────────────────────┐ ││
│  │  │  Custom ETL Pipeline                                              │ ││
│  │  │  URL: https://api.internal.org/ecoecho-webhook                   │ ││
│  │  │  Events: classification.updated                                  │ ││
│  │  │  Status: ● Active                              [Edit] [Delete]   │ ││
│  │  └───────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │  [+ Add Webhook]                                                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Audit Trail & Data Provenance

### 5.1 Audit Log Schema

```typescript
interface AuditLogEntry {
  id: string;
  timestamp: ISO8601;
  event_type: AuditEventType;
  actor: {
    user_id: string;
    email: string;
    role: string;
    ip_address: string;
    user_agent: string;
  };
  resource: {
    type: 'project' | 'recording' | 'classification' | 'report' | 'user';
    id: string;
    name?: string;
  };
  action: string;
  details: {
    before?: any;
    after?: any;
    metadata?: Record<string, any>;
  };
  compliance_flags?: string[];  // e.g., ['esa_relevant', 'data_export']
}

enum AuditEventType {
  // Data events
  DATA_UPLOADED = 'data.uploaded',
  DATA_DELETED = 'data.deleted',
  DATA_EXPORTED = 'data.exported',

  // Classification events
  CLASSIFICATION_CREATED = 'classification.created',
  CLASSIFICATION_MODIFIED = 'classification.modified',
  CLASSIFICATION_VETTED = 'classification.vetted',
  CLASSIFICATION_OVERRIDDEN = 'classification.overridden',

  // Report events
  REPORT_GENERATED = 'report.generated',
  REPORT_EXPORTED = 'report.exported',
  REPORT_SUBMITTED = 'report.submitted',

  // Access events
  PROJECT_ACCESSED = 'project.accessed',
  SENSITIVE_DATA_VIEWED = 'sensitive.viewed',

  // Admin events
  USER_ADDED = 'user.added',
  PERMISSION_CHANGED = 'permission.changed',
  SETTINGS_MODIFIED = 'settings.modified'
}
```

### 5.2 Data Provenance Tracking

```typescript
interface DataProvenance {
  recording_id: string;

  // Original source
  source: {
    device: {
      make: string;
      model: string;
      serial_number?: string;
      firmware_version?: string;
    };
    original_filename: string;
    original_hash: string;  // SHA-256
    recorded_at: ISO8601;
    uploaded_at: ISO8601;
    uploaded_by: string;
  };

  // Processing history
  processing_history: ProcessingStep[];

  // Classification history
  classification_history: ClassificationVersion[];

  // Chain of custody
  access_log: AccessLogEntry[];
}

interface ProcessingStep {
  step_id: string;
  timestamp: ISO8601;
  operation: 'noise_reduction' | 'resampling' | 'segmentation' | 'spectrogram';
  parameters: Record<string, any>;
  software_version: string;
  input_hash: string;
  output_hash: string;
}

interface ClassificationVersion {
  version: number;
  timestamp: ISO8601;
  species_id: string;
  confidence: number;
  method: 'auto' | 'manual' | 'corrected';
  model_version?: string;
  reviewer_id?: string;
  notes?: string;
  superseded_by?: number;
}
```

---

## 6. Report Templates

### 6.1 Template Engine

```typescript
class ReportTemplateEngine {
  private templates: Map<string, ReportTemplate> = new Map();

  async generateReport(
    templateId: string,
    data: ReportData,
    options: RenderOptions
  ): Promise<RenderedReport> {
    const template = this.templates.get(templateId);

    // Render markdown/HTML content
    const content = await this.renderTemplate(template, data);

    // Generate visualizations
    const visualizations = await this.generateVisualizations(template, data);

    // Assemble final document
    switch (options.format) {
      case 'pdf':
        return this.renderToPDF(content, visualizations, template.styles);
      case 'docx':
        return this.renderToWord(content, visualizations);
      case 'html':
        return this.renderToHTML(content, visualizations);
      default:
        throw new Error(`Unsupported format: ${options.format}`);
    }
  }

  // Built-in NABat summary template
  static NABatSummaryTemplate: ReportTemplate = {
    id: 'nabat_summary',
    name: 'NABat Survey Summary',
    sections: [
      {
        title: 'Survey Information',
        content: `
## Survey Information

**Project:** {{project.name}}
**Survey Period:** {{survey.start_date}} to {{survey.end_date}}
**Total Survey Nights:** {{survey.total_nights}}
**GRTS Cell:** {{survey.grts_cell_id}}

### Site Locations
{{#each sites}}
- **{{this.name}}**: {{this.latitude}}°N, {{this.longitude}}°W
{{/each}}
`
      },
      {
        title: 'Species Summary',
        content: `
## Species Detected

| Species | Common Name | Detections | Nights | Det. Rate |
|---------|-------------|------------|--------|-----------|
{{#each species_summary}}
| {{this.code}} | {{this.common_name}} | {{this.total}} | {{this.nights}} | {{this.rate}} |
{{/each}}

**Total Species Richness:** {{diversity.species_richness}}
**Shannon Diversity Index:** {{diversity.shannon_index}}
`
      },
      {
        title: 'Activity Patterns',
        visualization: {
          type: 'temporal_heatmap',
          data: 'hourly_activity'
        }
      },
      {
        title: 'Spatial Distribution',
        visualization: {
          type: 'activity_map',
          data: 'site_activity'
        }
      }
    ],
    styles: {
      fontFamily: 'Arial, sans-serif',
      primaryColor: '#2c5282',
      tableBorders: true
    }
  };
}
```
