'use client';

import { useCallback, useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, MusicalNoteIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { recordingsApi, projectsApi } from '@/lib/api';

export default function Recordings() {
  const params = useParams();
  const projectId = params.projectId as string;
  const siteId = params.siteId as string;
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({});
  const queryClient = useQueryClient();

  const { data: site } = useQuery({
    queryKey: ['site', projectId, siteId],
    queryFn: () => projectsApi.getSite(projectId!, siteId!),
    enabled: !!projectId && !!siteId,
  });

  const { data: recordings, isLoading } = useQuery({
    queryKey: ['recordings', siteId],
    queryFn: () => recordingsApi.list(siteId!, 1, 100),
    enabled: !!siteId,
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => recordingsApi.upload(siteId!, file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recordings', siteId] });
    },
  });

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      for (const file of acceptedFiles) {
        setUploadProgress((prev) => ({ ...prev, [file.name]: 0 }));
        try {
          await uploadMutation.mutateAsync(file);
          setUploadProgress((prev) => ({ ...prev, [file.name]: 100 }));
          toast.success(`Uploaded ${file.name}`);
        } catch {
          setUploadProgress((prev) => ({ ...prev, [file.name]: -1 }));
          toast.error(`Failed to upload ${file.name}`);
        }
      }
    },
    [siteId, uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.wav', '.wac', '.mp3', '.flac'],
    },
  });

  const recordingsData = recordings?.data?.items || [];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">
          {site?.data?.name || 'Recordings'}
        </h1>
        <p className="mt-2 text-gray-400">
          {site?.data?.latitude?.toFixed(4)}°N, {site?.data?.longitude?.toFixed(4)}°W
        </p>
      </div>

      {/* Upload area */}
      <div
        {...getRootProps()}
        className={`card mb-8 border-2 border-dashed cursor-pointer transition-colors ${
          isDragActive
            ? 'border-primary-500 bg-primary-500/10'
            : 'border-gray-700 hover:border-gray-600'
        }`}
      >
        <input {...getInputProps()} />
        <div className="text-center py-8">
          <CloudArrowUpIcon className="h-12 w-12 text-gray-500 mx-auto mb-4" />
          <p className="text-white font-medium mb-1">
            {isDragActive ? 'Drop files here...' : 'Drag and drop audio files here'}
          </p>
          <p className="text-sm text-gray-400">
            or click to select files (WAV, WAC, MP3, FLAC)
          </p>
        </div>
      </div>

      {/* Upload progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="card mb-8">
          <h3 className="text-lg font-medium text-white mb-4">Upload Progress</h3>
          <div className="space-y-2">
            {Object.entries(uploadProgress).map(([name, progress]) => (
              <div key={name} className="flex items-center gap-3">
                {progress === 100 ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-500" />
                ) : progress === -1 ? (
                  <XCircleIcon className="h-5 w-5 text-red-500" />
                ) : (
                  <div className="spinner" />
                )}
                <span className="text-sm text-gray-300 flex-1 truncate">{name}</span>
                {progress >= 0 && progress < 100 && (
                  <span className="text-sm text-gray-400">{progress}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recordings list */}
      <h2 className="text-xl font-semibold text-white mb-4">
        Recordings ({recordingsData.length})
      </h2>

      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <div className="spinner" />
        </div>
      ) : recordingsData.length === 0 ? (
        <div className="card text-center py-12">
          <MusicalNoteIcon className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No recordings yet. Upload some files to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {recordingsData.map((recording: any) => (
            <div
              key={recording.id}
              className="card flex items-center justify-between py-4"
            >
              <div className="flex items-center gap-4">
                <MusicalNoteIcon className="h-8 w-8 text-gray-500" />
                <div>
                  <p className="text-white font-medium">{recording.original_filename}</p>
                  <p className="text-sm text-gray-400">
                    {(recording.file_size_bytes / 1024 / 1024).toFixed(2)} MB
                    {' · '}
                    {recording.duration_seconds?.toFixed(1)}s
                    {' · '}
                    {recording.total_calls} calls
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span
                  className={`badge ${
                    recording.status === 'completed'
                      ? 'badge-success'
                      : recording.status === 'processing'
                      ? 'badge-warning'
                      : recording.status === 'failed'
                      ? 'badge-danger'
                      : 'badge-info'
                  }`}
                >
                  {recording.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
