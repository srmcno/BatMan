'use client';

import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { recordingsApi, classificationsApi } from '@/lib/api';
import Spectrogram3D from '@/components/Spectrogram3D';

export default function RecordingDetail() {
  const params = useParams()
  const recordingId = params.recordingId as string;

  const { data: recording } = useQuery({
    queryKey: ['recording', recordingId],
    queryFn: () => recordingsApi.get(recordingId!),
    enabled: !!recordingId,
  });

  const { data: classifications } = useQuery({
    queryKey: ['classifications', recordingId],
    queryFn: () => classificationsApi.list({ recording_id: recordingId }),
    enabled: !!recordingId,
  });

  const recordingData = recording?.data;
  const classificationsData = classifications?.data?.items || [];

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-2">
        {recordingData?.original_filename || 'Recording'}
      </h1>
      <p className="text-gray-400 mb-8">
        {recordingData?.duration_seconds?.toFixed(2)}s · {recordingData?.sample_rate} Hz · {recordingData?.total_calls} calls
      </p>

      {/* 3D Spectrogram */}
      <div className="card mb-8">
        <h2 className="text-lg font-semibold text-white mb-4">Spectrogram</h2>
        <Spectrogram3D data={null} />
      </div>

      {/* Classifications */}
      <div className="card">
        <h2 className="text-lg font-semibold text-white mb-4">
          Detected Calls ({classificationsData.length})
        </h2>
        {classificationsData.length === 0 ? (
          <p className="text-gray-400">No calls detected in this recording.</p>
        ) : (
          <div className="space-y-3">
            {classificationsData.map((c: any) => (
              <div key={c.id} className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
                <div>
                  <p className="text-white font-medium">
                    {c.species_name || c.species_code || 'Unknown'}
                  </p>
                  <p className="text-sm text-gray-400">
                    {c.start_time_ms?.toFixed(1)} - {c.end_time_ms?.toFixed(1)} ms
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-white">{(c.confidence * 100).toFixed(1)}%</p>
                  <span className={`badge ${
                    c.vetting_status === 'approved' ? 'badge-success' :
                    c.vetting_status === 'rejected' ? 'badge-danger' :
                    'badge-warning'
                  }`}>
                    {c.vetting_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
