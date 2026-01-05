# User Experience & Workflow - Technical Specification

## Overview

This document specifies the modern user experience design for EcoEcho AI, including high-speed batch processing, the smart-vetting "Human-in-the-Loop" interface, and multi-platform cloud synchronization.

---

## 1. High-Speed Batch Processing

### 1.1 GPU-Accelerated Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Batch Processing Architecture                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  User uploads folder: "Survey_July_2024" (1,247 files, 48GB)               │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 1: Parallel Upload & Preprocessing                             │  │
│  │                                                                       │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐       ┌─────────┐             │  │
│  │  │ Upload  │  │ Upload  │  │ Upload  │  ...  │ Upload  │             │  │
│  │  │ Worker 1│  │ Worker 2│  │ Worker 3│       │ Worker N│             │  │
│  │  └────┬────┘  └────┬────┘  └────┬────┘       └────┬────┘             │  │
│  │       │            │            │                 │                   │  │
│  │       └────────────┴────────────┴─────────────────┘                   │  │
│  │                              │                                        │  │
│  │                              ▼                                        │  │
│  │              Multipart Upload to Object Storage (S3)                  │  │
│  │              Throughput: 500 MB/s sustained                           │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 2: Job Queue Distribution                                      │  │
│  │                                                                       │  │
│  │                    ┌────────────────┐                                 │  │
│  │                    │  Kafka Topic   │                                 │  │
│  │                    │ "processing"   │                                 │  │
│  │                    └───────┬────────┘                                 │  │
│  │                            │                                          │  │
│  │        ┌───────────────────┼───────────────────┐                     │  │
│  │        │                   │                   │                      │  │
│  │        ▼                   ▼                   ▼                      │  │
│  │  ┌──────────┐       ┌──────────┐       ┌──────────┐                  │  │
│  │  │Consumer 1│       │Consumer 2│       │Consumer N│                  │  │
│  │  │(Preproc) │       │(Preproc) │       │(Preproc) │                  │  │
│  │  └──────────┘       └──────────┘       └──────────┘                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 3: GPU Inference Cluster                                       │  │
│  │                                                                       │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  GPU Node 1 (NVIDIA A100)                                       │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────┐ │  │  │
│  │  │  │ Batch: 64 spectrograms                                     │ │  │  │
│  │  │  │ Model: EcoEchoNet v3.2                                     │ │  │  │
│  │  │  │ Throughput: 800 files/second                               │ │  │  │
│  │  │  │ VRAM: 40GB → 32GB used                                     │ │  │  │
│  │  │  └────────────────────────────────────────────────────────────┘ │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  GPU Node 2 (NVIDIA A100)                                       │  │  │
│  │  │  └─ [Same configuration]                                        │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐  │  │
│  │  │  GPU Node 3 (NVIDIA T4 - Spot Instance)                         │  │  │
│  │  │  └─ Throughput: 200 files/second (overflow capacity)           │  │  │
│  │  └─────────────────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  Stage 4: Results Aggregation                                         │  │
│  │                                                                       │  │
│  │  • Write classifications to PostgreSQL                               │  │
│  │  • Generate summary statistics                                       │  │
│  │  • Trigger notification webhooks                                     │  │
│  │  • Update real-time dashboard via WebSocket                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Total Processing Time: 1,247 files → 12.3 seconds                         │
│  (Avg: 101 files/second including upload)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Processing Dashboard UI

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EcoEcho AI                                    [🔔] [👤 Dr. Smith] [⚙️]    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Batch Processing ──────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Project: Meadow Survey July 2024                                       ││
│  │  Status: ████████████████████░░░░░░░░░░ 68% Complete                   ││
│  │                                                                         ││
│  │  ┌──────────────────────────────────────────────────────────────────┐  ││
│  │  │  Files Processed    848 / 1,247                                  │  ││
│  │  │  Processing Rate    ~102 files/sec                               │  ││
│  │  │  ETA                ~4 seconds                                   │  ││
│  │  │  GPU Utilization    94%                                          │  ││
│  │  └──────────────────────────────────────────────────────────────────┘  ││
│  │                                                                         ││
│  │  Live Results Feed:                                                     ││
│  │  ┌──────────────────────────────────────────────────────────────────┐  ││
│  │  │  12:45:23  file_0847.wav  Eptesicus fuscus    98.2%  ✓          │  ││
│  │  │  12:45:23  file_0846.wav  Lasiurus borealis   94.1%  ✓          │  ││
│  │  │  12:45:23  file_0845.wav  Myotis lucifugus    72.3%  ⚠️ Review   │  ││
│  │  │  12:45:22  file_0844.wav  No bat detected     --     ○          │  ││
│  │  │  12:45:22  file_0843.wav  Eptesicus fuscus    99.1%  ✓          │  ││
│  │  │  ... (scrolling)                                                 │  ││
│  │  └──────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Quick Stats (Updating Live) ───────────────────────────────────────────┐│
│  │                                                                         ││
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐        ││
│  │  │   848      │  │    612     │  │     8      │  │    47      │        ││
│  │  │  Files     │  │  With Bats │  │  Species   │  │  Need      │        ││
│  │  │  Processed │  │  Detected  │  │  Found     │  │  Review    │        ││
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘        ││
│  │                                                                         ││
│  │  Species Distribution (So Far):                                         ││
│  │  Eptesicus fuscus      ████████████████████████████████  312 (51%)     ││
│  │  Lasiurus borealis     ██████████████████                148 (24%)     ││
│  │  Myotis lucifugus      ████████                           82 (13%)     ││
│  │  Lasionycteris noct.   ████                               41 (7%)      ││
│  │  Other (4 species)     ███                                29 (5%)      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [Cancel Batch] [Pause] [View Completed] [Export Partial Results]          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Batch Processing API

```typescript
// Batch processing job submission
interface BatchJobRequest {
  project_id: string;
  files: FileReference[];  // S3 URLs or local paths
  options: ProcessingOptions;
  callbacks: {
    webhook_url?: string;
    email_on_complete?: string;
    slack_channel?: string;
  };
}

interface ProcessingOptions {
  classification_model: string;      // "ecoecho_v3.2" | "regional_eastern"
  confidence_threshold: number;      // 0.0 - 1.0
  enable_behavioral_analysis: boolean;
  enable_xai_explanations: boolean;
  noise_reduction: 'auto' | 'aggressive' | 'minimal' | 'none';
  regional_filtering: {
    enabled: boolean;
    latitude?: number;
    longitude?: number;
    radius_km?: number;
  };
  output_format: 'json' | 'csv' | 'nabat';
}

interface BatchJobStatus {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: {
    total_files: number;
    processed_files: number;
    failed_files: number;
    percentage: number;
  };
  performance: {
    start_time: ISO8601;
    current_rate: number;  // files per second
    estimated_completion: ISO8601;
  };
  results_url?: string;  // Available when completed
  errors?: ProcessingError[];
}
```

---

## 2. Smart-Vetting Interface (Human-in-the-Loop)

### 2.1 Confidence-Based Routing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Classification Confidence Router                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Model Output: Species X, Confidence 0.XX                                  │
│                              │                                              │
│                              ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Confidence Threshold Logic                         │  │
│  │                                                                       │  │
│  │   Confidence ≥ 0.90                                                  │  │
│  │   ──────────────────►  AUTO-ACCEPT                                   │  │
│  │                        (No human review needed)                       │  │
│  │                        ~65% of classifications                        │  │
│  │                                                                       │  │
│  │   0.70 ≤ Confidence < 0.90                                           │  │
│  │   ──────────────────►  QUICK REVIEW                                  │  │
│  │                        (Swipe interface)                              │  │
│  │                        ~25% of classifications                        │  │
│  │                                                                       │  │
│  │   0.50 ≤ Confidence < 0.70                                           │  │
│  │   ──────────────────►  DETAILED REVIEW                               │  │
│  │                        (Full analysis view)                           │  │
│  │                        ~8% of classifications                         │  │
│  │                                                                       │  │
│  │   Confidence < 0.50                                                  │  │
│  │   ──────────────────►  UNCERTAIN                                     │  │
│  │                        (May require expert)                           │  │
│  │                        ~2% of classifications                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Special Cases:                                                            │
│  • Endangered species detection → Always requires human confirmation       │
│  • First detection of species at site → Flagged for review                │
│  • Unusual behavioral pattern → Flagged for expert review                 │
│  • Conflicting regional data → Flagged with context                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Swipe-to-Confirm Interface (Mobile & Desktop)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  EcoEcho AI - Quick Vetting                    47 calls to review          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                    ┌─────────────────────────────────────┐                  │
│                    │                                     │                  │
│   ┌──────────┐     │      [SPECTROGRAM IMAGE]           │     ┌──────────┐ │
│   │          │     │                                     │     │          │ │
│   │    ✗     │ ◄── │   ════════════════════════         │ ──► │    ✓     │ │
│   │ DISAGREE │     │   ════════════════                 │     │  AGREE   │ │
│   │          │     │   ════════════                     │     │          │ │
│   └──────────┘     │                                     │     └──────────┘ │
│                    │                                     │                  │
│                    │   AI Prediction:                    │                  │
│                    │   ┌───────────────────────────────┐ │                  │
│                    │   │  Myotis lucifugus             │ │                  │
│                    │   │  Confidence: 78%              │ │                  │
│                    │   │                               │ │                  │
│                    │   │  Key Features:                │ │                  │
│                    │   │  • Fc: 42.3 kHz ✓             │ │                  │
│                    │   │  • Duration: 3.1 ms ✓         │ │                  │
│                    │   │  • Slope: -85 oct/s ⚠️        │ │                  │
│                    │   └───────────────────────────────┘ │                  │
│                    │                                     │                  │
│                    │   Alternatives:                     │                  │
│                    │   • M. septentrionalis (15%)       │                  │
│                    │   • M. sodalis (5%)                │                  │
│                    │                                     │                  │
│                    └─────────────────────────────────────┘                  │
│                                                                             │
│    ← Swipe Left: DISAGREE          Swipe Right: AGREE →                    │
│                                                                             │
│    Keyboard: [A] Agree  [D] Disagree  [S] Skip  [E] Expand View            │
│                                                                             │
│  ┌─ Progress ───────────────────────────────────────────────────────────┐  │
│  │  ████████████████████████░░░░░░░░░░░░░░░░  24/47 reviewed            │  │
│  │  Agreement rate: 92%  |  Avg time: 2.3s/call  |  Est. remaining: 53s │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  [🔊 Play Audio] [📐 Measure] [🔍 Expand] [⏭️ Skip to Difficult]           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Detailed Review Mode

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Detailed Call Review                                   Call 3 of 47       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─ Spectrogram ───────────────────────────┐ ┌─ AI Analysis ─────────────┐ │
│  │                                         │ │                           │ │
│  │     [Interactive 3D Spectrogram]        │ │  Prediction:              │ │
│  │                                         │ │  ┌───────────────────────┐│ │
│  │     150kHz ─┬─────────────────────      │ │  │ Myotis lucifugus     ││ │
│  │             │ ╲                         │ │  │ Confidence: 68%      ││ │
│  │     100kHz ─┤  ╲                        │ │  └───────────────────────┘│ │
│  │             │   ╲    ← Call trace       │ │                           │ │
│  │      50kHz ─┤    ╲___                   │ │  Why this prediction:     │ │
│  │             │        ╲                  │ │  • Fc 42.3kHz matches    │ │
│  │      10kHz ─┴─────────────────────      │ │  • Curve shape typical   │ │
│  │             0    50   100   150 ms      │ │  • Duration in range     │ │
│  │                                         │ │                           │ │
│  │  [Zoom+] [Zoom-] [Rotate] [Measure]     │ │  Concerns:               │ │
│  └─────────────────────────────────────────┘ │  ⚠️ Slope steeper than   │ │
│                                              │     typical (-95 vs -85) │ │
│  ┌─ Waveform ──────────────────────────────┐ │  ⚠️ Low SNR (12dB)       │ │
│  │  ∿∿∿∿∿▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿∿    │ │                           │ │
│  │       └──── detected call ────┘          │ └───────────────────────────┘ │
│  │  [🔊 Play] [🔊 Play Slow] [🔊 Time-exp]  │                              │
│  └──────────────────────────────────────────┘ ┌─ Reference Calls ─────────┐ │
│                                              │                           │ │
│  ┌─ Measurement Panel ─────────────────────┐ │  M. lucifugus (verified): │ │
│  │                                         │ │  [mini spectrogram 1]    │ │
│  │  Parameter    │ Measured │ Expected     │ │  Similarity: 87%         │ │
│  │  ─────────────┼──────────┼────────────  │ │                           │ │
│  │  Fc (kHz)     │  42.3    │  40-45   ✓   │ │  [mini spectrogram 2]    │ │
│  │  Fmax (kHz)   │  78.1    │  75-85   ✓   │ │  Similarity: 82%         │ │
│  │  Fmin (kHz)   │  38.2    │  35-42   ✓   │ │                           │ │
│  │  Duration(ms) │   3.1    │  2-5     ✓   │ │  Nearest non-match:      │ │
│  │  Slope (o/s)  │  -95     │  -90±15  ⚠️  │ │  M. septentrionalis      │ │
│  │  Bandwidth    │  39.9    │  35-50   ✓   │ │  Similarity: 61%         │ │
│  └─────────────────────────────────────────┘ └───────────────────────────┘ │
│                                                                             │
│  ┌─ Your Decision ─────────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  ○ Agree: Myotis lucifugus                                             ││
│  │  ○ Change to: [Species Dropdown ▼]                                     ││
│  │  ○ Unknown/Unidentifiable                                              ││
│  │  ○ Not a bat call                                                      ││
│  │                                                                         ││
│  │  Notes: [                                                    ]         ││
│  │                                                                         ││
│  │  [◄ Previous]  [Submit & Next ►]  [Flag for Expert]  [Skip]           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Vetting Workflow State Machine

```typescript
enum VettingState {
  PENDING = 'pending',
  QUICK_REVIEW = 'quick_review',
  DETAILED_REVIEW = 'detailed_review',
  EXPERT_REVIEW = 'expert_review',
  APPROVED = 'approved',
  REJECTED = 'rejected',
  CORRECTED = 'corrected'
}

interface VettingWorkflow {
  call_id: string;
  current_state: VettingState;
  ai_prediction: Classification;
  reviews: Review[];
  final_classification?: Classification;

  transitions: {
    [VettingState.PENDING]: ['quick_review', 'detailed_review', 'approved'];
    [VettingState.QUICK_REVIEW]: ['approved', 'corrected', 'detailed_review'];
    [VettingState.DETAILED_REVIEW]: ['approved', 'corrected', 'expert_review'];
    [VettingState.EXPERT_REVIEW]: ['approved', 'corrected', 'rejected'];
  };
}

interface Review {
  reviewer_id: string;
  reviewer_role: 'technician' | 'biologist' | 'expert';
  action: 'agree' | 'disagree' | 'correct' | 'escalate' | 'skip';
  corrected_species?: string;
  notes?: string;
  timestamp: ISO8601;
  time_spent_seconds: number;
}
```

### 2.5 Gamification & Quality Metrics

```typescript
interface ReviewerMetrics {
  reviewer_id: string;

  // Performance metrics
  total_reviews: number;
  reviews_today: number;
  average_time_per_review: number;
  agreement_with_ai: number;       // 0-1
  agreement_with_experts: number;  // 0-1

  // Quality scoring
  accuracy_score: number;          // Validated against expert reviews
  consistency_score: number;       // Same call, same answer

  // Achievements
  badges: Badge[];
  leaderboard_rank: number;
  streak_days: number;
}

interface ReviewQualityControl {
  // Insert known-answer calls periodically
  insertQualityControlCall(queue: ReviewQueue): void;

  // Measure inter-rater reliability
  calculateKappaScore(reviews: Review[]): number;

  // Detect reviewer fatigue
  detectFatiguePatterns(reviewer: Reviewer): FatigueAlert | null;

  // Calibration sessions
  scheduleCalibration(reviewer: Reviewer, difficulty: 'easy' | 'medium' | 'hard'): void;
}
```

---

## 3. Multi-Platform Cloud Sync

### 3.1 Sync Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Multi-Platform Cloud Sync                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐│
│  │   Field     │  │   Office    │  │   Mobile    │  │    Remote Expert    ││
│  │  Laptop     │  │   Desktop   │  │    App      │  │    (Web Browser)    ││
│  │             │  │             │  │             │  │                     ││
│  │ ┌─────────┐ │  │ ┌─────────┐ │  │ ┌─────────┐ │  │    ┌─────────┐     ││
│  │ │ Local   │ │  │ │ Local   │ │  │ │ Local   │ │  │    │ Browser │     ││
│  │ │ Cache   │ │  │ │ Cache   │ │  │ │ Cache   │ │  │    │ Session │     ││
│  │ └────┬────┘ │  │ └────┬────┘ │  │ └────┬────┘ │  │    └────┬────┘     ││
│  └──────┼──────┘  └──────┼──────┘  └──────┼──────┘  └─────────┼──────────┘│
│         │                │                │                   │            │
│         └────────────────┴────────────────┴───────────────────┘            │
│                                    │                                        │
│                          ┌─────────▼─────────┐                              │
│                          │   Sync Gateway    │                              │
│                          │   (WebSocket +    │                              │
│                          │    REST API)      │                              │
│                          └─────────┬─────────┘                              │
│                                    │                                        │
│  ┌─────────────────────────────────┴─────────────────────────────────────┐  │
│  │                        Cloud Backend                                  │  │
│  │                                                                       │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │  │
│  │  │   Project    │  │    Audio     │  │Classification│                │  │
│  │  │   Database   │  │   Storage    │  │   Results    │                │  │
│  │  │ (PostgreSQL) │  │    (S3)      │  │  (MongoDB)   │                │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                │  │
│  │                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐│  │
│  │  │                   Conflict Resolution Engine                      ││  │
│  │  │                                                                   ││  │
│  │  │  • Last-Write-Wins for metadata                                  ││  │
│  │  │  • Vector clocks for classification decisions                    ││  │
│  │  │  • Manual resolution UI for true conflicts                       ││  │
│  │  └──────────────────────────────────────────────────────────────────┘│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Offline-First Architecture

```typescript
// Service Worker for offline capability
class OfflineSyncManager {
  private db: IndexedDB;
  private syncQueue: SyncQueue;
  private conflictResolver: ConflictResolver;

  // Queue changes when offline
  async queueChange(change: DataChange): Promise<void> {
    await this.db.put('pending_changes', {
      id: uuid(),
      change,
      timestamp: Date.now(),
      retries: 0
    });

    // Register for background sync
    await registration.sync.register('sync-changes');
  }

  // Sync when connection restored
  async syncPendingChanges(): Promise<SyncResult> {
    const pending = await this.db.getAll('pending_changes');
    const results: SyncResult[] = [];

    for (const item of pending) {
      try {
        const result = await this.pushChange(item.change);

        if (result.conflict) {
          await this.conflictResolver.resolve(item.change, result.serverData);
        } else {
          await this.db.delete('pending_changes', item.id);
        }

        results.push(result);
      } catch (error) {
        item.retries++;
        await this.db.put('pending_changes', item);
      }
    }

    return this.aggregateResults(results);
  }

  // Real-time sync via WebSocket
  connectRealtimeSync(projectId: string): void {
    const ws = new WebSocket(`wss://api.ecoecho.ai/sync/${projectId}`);

    ws.onmessage = async (event) => {
      const update = JSON.parse(event.data);

      switch (update.type) {
        case 'classification_updated':
          await this.applyRemoteUpdate(update.data);
          this.notifyUI(update);
          break;

        case 'review_completed':
          await this.mergeReview(update.data);
          this.updateReviewQueue();
          break;

        case 'file_uploaded':
          await this.downloadMetadata(update.data.file_id);
          break;
      }
    };
  }
}
```

### 3.3 Collaborative Features

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Real-Time Collaboration View                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Project: Meadow Survey 2024                           3 users online 🟢    │
│                                                                             │
│  ┌─ Activity Feed ─────────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  🟢 Dr. Johnson just now                                               ││
│  │     Reviewed 12 calls in Site B batch                                  ││
│  │     [View Changes]                                                      ││
│  │                                                                         ││
│  │  🟢 Sarah K. 2 min ago                                                 ││
│  │     Uploaded 234 new files from Site C                                 ││
│  │     Processing: ████████████░░░░ 78%                                   ││
│  │                                                                         ││
│  │  🟢 Mike T. 5 min ago                                                  ││
│  │     Changed classification: file_234.wav                               ││
│  │     M. septentrionalis → M. lucifugus                                  ││
│  │     "Knee shape clearly indicates lucifugus"                           ││
│  │     [View | Discuss]                                                    ││
│  │                                                                         ││
│  │  🔵 System 15 min ago                                                  ││
│  │     Batch processing completed: Site A                                 ││
│  │     847 files processed, 23 need review                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  ┌─ Team Review Queue ─────────────────────────────────────────────────────┐│
│  │                                                                         ││
│  │  Unassigned:  156 calls   [Take 20] [Auto-assign]                      ││
│  │                                                                         ││
│  │  ┌──────────────────────────────────────────────────────────────────┐  ││
│  │  │  Reviewer        │ Assigned │ Completed │ Rate    │ Accuracy    │  ││
│  │  │  ────────────────┼──────────┼───────────┼─────────┼─────────────│  ││
│  │  │  Dr. Johnson 🟢  │    45    │    33     │ 8/min   │   96%       │  ││
│  │  │  Sarah K. 🟢     │    30    │    12     │ 5/min   │   92%       │  ││
│  │  │  Mike T. 🟢      │    20    │    20     │ 6/min   │   94%       │  ││
│  │  │  Emma R. 🔴      │    25    │     0     │ --      │   --        │  ││
│  │  └──────────────────────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│  [📝 Add Comment] [📊 View Statistics] [⬇️ Export Progress] [🔔 Notify Team]│
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Permission & Access Control

```typescript
interface ProjectPermissions {
  roles: {
    owner: Permission[];      // Full access
    manager: Permission[];    // Edit, assign, export
    reviewer: Permission[];   // Review assigned calls
    viewer: Permission[];     // Read-only access
  };

  permissions: {
    'project.delete': ['owner'];
    'project.settings': ['owner', 'manager'];
    'data.upload': ['owner', 'manager', 'reviewer'];
    'data.delete': ['owner', 'manager'];
    'classification.review': ['owner', 'manager', 'reviewer'];
    'classification.override': ['owner', 'manager'];
    'export.full': ['owner', 'manager'];
    'export.summary': ['owner', 'manager', 'reviewer', 'viewer'];
  };
}

interface TeamMember {
  user_id: string;
  email: string;
  role: keyof ProjectPermissions['roles'];
  sites_assigned: string[];
  notification_preferences: NotificationPrefs;
  joined_at: ISO8601;
  last_active: ISO8601;
}
```

---

## 4. Cross-Platform Applications

### 4.1 Platform-Specific Features

| Feature | Web App | Desktop (Electron) | Mobile (React Native) |
|---------|---------|-------------------|----------------------|
| Batch upload | ✓ (drag & drop) | ✓ (folder watch) | ✓ (photos/files) |
| Offline mode | Limited (PWA) | Full | Full |
| GPU processing | Cloud only | Local + Cloud | Cloud only |
| Audio playback | Web Audio API | Native audio | Native audio |
| 3D visualization | WebGL | WebGL + native | Limited |
| Background sync | Service Worker | Native process | Background fetch |
| Push notifications | Web Push | Native | Native |
| File system access | Limited | Full | Sandboxed |

### 4.2 Desktop Application Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Desktop Application (Electron)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Main Process                                  │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │   File       │  │    Local     │  │   Native     │               │   │
│  │  │   Watcher    │  │   GPU Proc   │  │   Menus      │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │   Auto       │  │   Offline    │  │   System     │               │   │
│  │  │   Updater    │  │   Database   │  │   Tray       │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                              │ IPC                                         │
│                              ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Renderer Process                                │   │
│  │                                                                      │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐│   │
│  │  │                     React Application                           ││   │
│  │  │                                                                  ││   │
│  │  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        ││   │
│  │  │  │ Project  │  │ Analysis │  │  Review  │  │  Report  │        ││   │
│  │  │  │  View    │  │   View   │  │   View   │  │   View   │        ││   │
│  │  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        ││   │
│  │  │                                                                  ││   │
│  │  │  ┌────────────────────────────────────────────────────────────┐ ││   │
│  │  │  │              Three.js 3D Visualization                     │ ││   │
│  │  │  └────────────────────────────────────────────────────────────┘ ││   │
│  │  └─────────────────────────────────────────────────────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Local Resources:                                                          │
│  • Model cache: ~/.ecoecho/models/                                         │
│  • Project data: ~/.ecoecho/projects/                                      │
│  • Settings: ~/.ecoecho/config.json                                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.3 Mobile Application Screens

```
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│  📱 Field Recording │  │  📱 Quick Review    │  │  📱 Project Map     │
├─────────────────────┤  ├─────────────────────┤  ├─────────────────────┤
│                     │  │                     │  │                     │
│  ┌─────────────────┐│  │  ┌─────────────────┐│  │  ┌─────────────────┐│
│  │   Live Audio    ││  │  │  [Spectrogram]  ││  │  │                 ││
│  │   ∿∿∿∿∿∿∿∿∿∿∿∿  ││  │  │                 ││  │  │    ○ Site A    ││
│  │                 ││  │  │                 ││  │  │        ╲        ││
│  │   ● Recording   ││  │  └─────────────────┘│  │  │    ● Site B    ││
│  └─────────────────┘│  │                     │  │  │         ╲       ││
│                     │  │  AI: M. lucifugus  │  │  │      ○ Site C   ││
│  ┌───────────────┐  │  │  Confidence: 82%   │  │  │                 ││
│  │ GPS: 38.9°N   │  │  │                     │  │  └─────────────────┘│
│  │      77.0°W   │  │  │  ┌───────┐ ┌───────┐│  │                     │
│  │ Elevation: 45m│  │  │  │  ✗    │ │   ✓   ││  │  Sites: 3          │
│  └───────────────┘  │  │  │Reject │ │Accept ││  │  Total calls: 1,234│
│                     │  │  └───────┘ └───────┘│  │  Species: 8        │
│  [⏹ Stop] [📤 Sync]│  │                     │  │                     │
│                     │  │  ← Swipe to review →│  │  [Filter] [Export] │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
```

---

## 5. Accessibility & Internationalization

### 5.1 Accessibility Features

```typescript
interface AccessibilityConfig {
  // Visual accessibility
  highContrastMode: boolean;
  colorBlindMode: 'none' | 'deuteranopia' | 'protanopia' | 'tritanopia';
  textScaling: number;  // 1.0 - 2.0
  reducedMotion: boolean;

  // Audio accessibility
  spectrogramSonification: boolean;  // Convert visual to audio
  screenReaderOptimized: boolean;

  // Motor accessibility
  keyboardNavigation: 'standard' | 'enhanced';
  dwellClick: boolean;
  dwellTime: number;  // ms

  // Cognitive accessibility
  simplifiedInterface: boolean;
  progressiveDisclosure: boolean;
}

// ARIA labels for spectrogram
const SpectrogramAriaLabels = {
  container: "Interactive spectrogram visualization showing bat call at {frequency} kilohertz",
  callRegion: "Bat call detected, species {species}, confidence {confidence} percent",
  measurement: "Frequency measurement at {freq} kilohertz, amplitude {amp} decibels"
};
```

### 5.2 Internationalization

```typescript
// Supported languages
type SupportedLocale = 'en-US' | 'es-ES' | 'fr-FR' | 'de-DE' | 'pt-BR' | 'zh-CN' | 'ja-JP';

interface i18nConfig {
  defaultLocale: SupportedLocale;
  fallbackLocale: 'en-US';

  // Species names in multiple languages
  speciesNames: {
    [speciesId: string]: {
      scientific: string;
      common: { [locale in SupportedLocale]: string };
    };
  };

  // Measurement unit preferences
  units: {
    frequency: 'kHz' | 'Hz';
    time: 'ms' | 's';
    distance: 'km' | 'mi';
    temperature: 'C' | 'F';
  };

  // Date/time formatting
  dateFormat: 'ISO' | 'US' | 'EU';
}
```

---

## 6. Performance Requirements

### 6.1 Frontend Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| First Contentful Paint | < 1.5s | Lighthouse |
| Time to Interactive | < 3.0s | Lighthouse |
| Largest Contentful Paint | < 2.5s | Lighthouse |
| Cumulative Layout Shift | < 0.1 | Lighthouse |
| Spectrogram render | < 100ms | Custom metric |
| 3D rotation FPS | 60 fps | Custom metric |
| Review action response | < 200ms | Custom metric |

### 6.2 Optimization Strategies

```typescript
// Code splitting for route-based loading
const routes = {
  '/dashboard': () => import('./pages/Dashboard'),
  '/analysis': () => import('./pages/Analysis'),
  '/review': () => import('./pages/Review'),
  '/reports': () => import('./pages/Reports'),
};

// Virtual scrolling for large lists
const VirtualizedCallList: FC<Props> = ({ calls }) => (
  <FixedSizeList
    height={600}
    itemCount={calls.length}
    itemSize={80}
    width="100%"
  >
    {({ index, style }) => (
      <CallListItem call={calls[index]} style={style} />
    )}
  </FixedSizeList>
);

// WebWorker for heavy computation
const spectrogramWorker = new Worker('./spectrogram.worker.ts');

spectrogramWorker.postMessage({
  type: 'compute',
  audio: audioBuffer,
  config: spectrogramConfig
});

spectrogramWorker.onmessage = (event) => {
  renderSpectrogram(event.data.spectrogram);
};
```
