'use client';

import { useRef, useMemo, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Line } from '@react-three/drei';
import * as THREE from 'three';

interface SpectrogramData {
  frequencies: number[];
  times: number[];
  magnitudes: number[][];
  sample_rate: number;
  duration: number;
}

interface Spectrogram3DProps {
  data: SpectrogramData | null;
  colorScheme?: 'viridis' | 'plasma' | 'inferno' | 'magma';
  showAxes?: boolean;
  autoRotate?: boolean;
}

// Color maps for spectrogram visualization
const colorMaps = {
  viridis: [
    [0.267, 0.004, 0.329],
    [0.282, 0.140, 0.458],
    [0.253, 0.265, 0.530],
    [0.206, 0.372, 0.553],
    [0.163, 0.471, 0.558],
    [0.127, 0.566, 0.551],
    [0.134, 0.658, 0.518],
    [0.266, 0.749, 0.441],
    [0.478, 0.821, 0.318],
    [0.741, 0.873, 0.150],
    [0.993, 0.906, 0.144],
  ],
  plasma: [
    [0.050, 0.030, 0.528],
    [0.294, 0.012, 0.615],
    [0.492, 0.012, 0.658],
    [0.658, 0.084, 0.620],
    [0.797, 0.213, 0.518],
    [0.894, 0.350, 0.390],
    [0.956, 0.498, 0.263],
    [0.988, 0.652, 0.164],
    [0.988, 0.810, 0.165],
    [0.940, 0.975, 0.131],
  ],
  inferno: [
    [0.001, 0.000, 0.014],
    [0.122, 0.047, 0.226],
    [0.281, 0.074, 0.367],
    [0.443, 0.106, 0.398],
    [0.591, 0.153, 0.377],
    [0.736, 0.215, 0.330],
    [0.858, 0.318, 0.237],
    [0.938, 0.465, 0.126],
    [0.973, 0.647, 0.038],
    [0.988, 0.998, 0.645],
  ],
  magma: [
    [0.001, 0.000, 0.014],
    [0.086, 0.046, 0.188],
    [0.210, 0.066, 0.358],
    [0.352, 0.089, 0.453],
    [0.493, 0.131, 0.485],
    [0.638, 0.195, 0.468],
    [0.785, 0.295, 0.416],
    [0.899, 0.437, 0.356],
    [0.967, 0.609, 0.421],
    [0.987, 0.991, 0.750],
  ],
};

function interpolateColor(value: number, colorMap: number[][]): THREE.Color {
  const clampedValue = Math.max(0, Math.min(1, value));
  const scaledIndex = clampedValue * (colorMap.length - 1);
  const lowerIndex = Math.floor(scaledIndex);
  const upperIndex = Math.min(lowerIndex + 1, colorMap.length - 1);
  const fraction = scaledIndex - lowerIndex;

  const r = colorMap[lowerIndex][0] + fraction * (colorMap[upperIndex][0] - colorMap[lowerIndex][0]);
  const g = colorMap[lowerIndex][1] + fraction * (colorMap[upperIndex][1] - colorMap[lowerIndex][1]);
  const b = colorMap[lowerIndex][2] + fraction * (colorMap[upperIndex][2] - colorMap[lowerIndex][2]);

  return new THREE.Color(r, g, b);
}

function SpectrogramMesh({
  data,
  colorScheme,
}: {
  data: SpectrogramData;
  colorScheme: 'viridis' | 'plasma' | 'inferno' | 'magma';
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const colorMap = colorMaps[colorScheme];

  const { geometry } = useMemo(() => {
    const { frequencies, times, magnitudes } = data;
    const numFreqs = frequencies.length;
    const numTimes = times.length;

    // Create geometry
    const geom = new THREE.BufferGeometry();

    // Calculate vertices and colors
    const vertices: number[] = [];
    const colors: number[] = [];
    const indices: number[] = [];

    // Find min/max for normalization
    let min = Infinity;
    let max = -Infinity;
    for (let i = 0; i < numTimes; i++) {
      for (let j = 0; j < numFreqs; j++) {
        const val = magnitudes[i]?.[j] ?? 0;
        if (val < min) min = val;
        if (val > max) max = val;
      }
    }

    // Scale factors
    const xScale = 10 / numTimes;
    const yScale = 5 / numFreqs;
    const zScale = 3;

    // Create vertices
    for (let i = 0; i < numTimes; i++) {
      for (let j = 0; j < numFreqs; j++) {
        const x = i * xScale - 5;
        const z = j * yScale - 2.5;
        const rawValue = magnitudes[i]?.[j] ?? 0;
        const normalizedValue = max > min ? (rawValue - min) / (max - min) : 0;
        const y = normalizedValue * zScale;

        vertices.push(x, y, z);

        // Color based on magnitude
        const color = interpolateColor(normalizedValue, colorMap);
        colors.push(color.r, color.g, color.b);
      }
    }

    // Create indices for triangles
    for (let i = 0; i < numTimes - 1; i++) {
      for (let j = 0; j < numFreqs - 1; j++) {
        const a = i * numFreqs + j;
        const b = (i + 1) * numFreqs + j;
        const c = (i + 1) * numFreqs + (j + 1);
        const d = i * numFreqs + (j + 1);

        indices.push(a, b, d);
        indices.push(b, c, d);
      }
    }

    geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
    geom.setIndex(indices);
    geom.computeVertexNormals();

    return { geometry: geom, minMag: min, maxMag: max };
  }, [data, colorMap]);

  return (
    <mesh ref={meshRef} geometry={geometry}>
      <meshStandardMaterial vertexColors side={THREE.DoubleSide} />
    </mesh>
  );
}

function Axes({ data }: { data: SpectrogramData }) {
  const maxFreq = Math.max(...data.frequencies) / 1000; // Convert to kHz
  const duration = data.duration;

  return (
    <group>
      {/* X axis - Time */}
      <Line
        points={[
          [-5, 0, -2.5],
          [5, 0, -2.5],
        ]}
        color="white"
        lineWidth={1}
      />
      <Text position={[0, -0.5, -3]} fontSize={0.3} color="white">
        Time (s)
      </Text>
      {/* Time tick marks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <group key={t}>
          <Line
            points={[
              [-5 + t * 10, 0, -2.5],
              [-5 + t * 10, 0, -2.7],
            ]}
            color="white"
            lineWidth={1}
          />
          <Text position={[-5 + t * 10, -0.2, -2.9]} fontSize={0.2} color="gray">
            {(t * duration).toFixed(2)}
          </Text>
        </group>
      ))}

      {/* Y axis - Amplitude */}
      <Line
        points={[
          [-5, 0, -2.5],
          [-5, 3, -2.5],
        ]}
        color="white"
        lineWidth={1}
      />
      <Text position={[-5.8, 1.5, -2.5]} fontSize={0.3} color="white" rotation={[0, 0, Math.PI / 2]}>
        Amplitude
      </Text>

      {/* Z axis - Frequency */}
      <Line
        points={[
          [-5, 0, -2.5],
          [-5, 0, 2.5],
        ]}
        color="white"
        lineWidth={1}
      />
      <Text position={[-5.5, -0.5, 0]} fontSize={0.3} color="white" rotation={[0, Math.PI / 2, 0]}>
        Frequency (kHz)
      </Text>
      {/* Frequency tick marks */}
      {[0, 0.25, 0.5, 0.75, 1].map((f) => (
        <group key={f}>
          <Line
            points={[
              [-5, 0, -2.5 + f * 5],
              [-5.2, 0, -2.5 + f * 5],
            ]}
            color="white"
            lineWidth={1}
          />
          <Text position={[-5.5, 0, -2.5 + f * 5]} fontSize={0.2} color="gray">
            {(f * maxFreq).toFixed(0)}
          </Text>
        </group>
      ))}
    </group>
  );
}

function Scene({
  data,
  colorScheme,
  showAxes,
  autoRotate,
}: {
  data: SpectrogramData;
  colorScheme: 'viridis' | 'plasma' | 'inferno' | 'magma';
  showAxes: boolean;
  autoRotate: boolean;
}) {
  return (
    <>
      <ambientLight intensity={0.5} />
      <directionalLight position={[10, 10, 5]} intensity={1} />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />

      <SpectrogramMesh data={data} colorScheme={colorScheme} />

      {showAxes && <Axes data={data} />}

      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        autoRotate={autoRotate}
        autoRotateSpeed={0.5}
        minDistance={5}
        maxDistance={30}
      />
    </>
  );
}

function LoadingPlaceholder() {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y = state.clock.getElapsedTime() * 0.5;
    }
  });

  return (
    <>
      <ambientLight intensity={0.5} />
      <mesh ref={meshRef}>
        <boxGeometry args={[2, 2, 2]} />
        <meshStandardMaterial color="#4f46e5" wireframe />
      </mesh>
      <OrbitControls enableDamping dampingFactor={0.05} />
    </>
  );
}

export default function Spectrogram3D({
  data,
  colorScheme = 'viridis',
  showAxes = true,
  autoRotate = false,
}: Spectrogram3DProps) {
  const [selectedScheme, setSelectedScheme] = useState(colorScheme);

  return (
    <div className="relative w-full h-full min-h-[400px]">
      {/* Controls overlay */}
      <div className="absolute top-4 right-4 z-10 flex gap-2">
        <select
          value={selectedScheme}
          onChange={(e) => setSelectedScheme(e.target.value as typeof colorScheme)}
          className="bg-gray-800 text-white text-sm px-2 py-1 rounded border border-gray-700"
        >
          <option value="viridis">Viridis</option>
          <option value="plasma">Plasma</option>
          <option value="inferno">Inferno</option>
          <option value="magma">Magma</option>
        </select>
      </div>

      {/* Canvas */}
      <Canvas camera={{ position: [8, 6, 8], fov: 60 }}>
        {data ? (
          <Scene
            data={data}
            colorScheme={selectedScheme}
            showAxes={showAxes}
            autoRotate={autoRotate}
          />
        ) : (
          <LoadingPlaceholder />
        )}
      </Canvas>

      {/* Legend */}
      {data && (
        <div className="absolute bottom-4 left-4 bg-gray-900/80 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-2">Amplitude</p>
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Low</span>
            <div
              className="w-24 h-3 rounded"
              style={{
                background: `linear-gradient(to right, ${colorMaps[selectedScheme]
                  .map((c) => `rgb(${c[0] * 255}, ${c[1] * 255}, ${c[2] * 255})`)
                  .join(', ')})`,
              }}
            />
            <span className="text-xs text-gray-500">High</span>
          </div>
        </div>
      )}

      {/* Instructions */}
      <div className="absolute bottom-4 right-4 text-xs text-gray-500">
        <p>🖱️ Drag to rotate • Scroll to zoom • Right-click to pan</p>
      </div>
    </div>
  );
}
