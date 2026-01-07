'use client';

import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Dialog } from '@headlessui/react';
import {
  ArrowLeftIcon,
  MapPinIcon,
  PlusIcon,
  CloudArrowUpIcon,
  MusicalNoteIcon,
  ArrowPathIcon,
} from '@heroicons/react/24/outline';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { projectsApi, recordingsApi } from '@/lib/api';

type SiteFormState = {
  name: string;
  description: string;
  latitude: string;
  longitude: string;
};

export default function ProjectDetail() {
  const params = useParams();
  const projectId = params.projectId as string;
  const queryClient = useQueryClient();

  const [isCreateSiteOpen, setIsCreateSiteOpen] = useState(false);
  const [siteForm, setSiteForm] = useState<SiteFormState>({
    name: '',
    description: '',
    latitude: '',
    longitude: '',
  });
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [recordedAt, setRecordedAt] = useState('');
  const [uploadLatitude, setUploadLatitude] = useState('');
  const [uploadLongitude, setUploadLongitude] = useState('');

  const { data: projectData, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
    enabled: !!projectId,
  });

  const { data: summaryData } = useQuery({
    queryKey: ['project-summary', projectId],
    queryFn: () => projectsApi.getSummary(projectId),
    enabled: !!projectId,
  });

  const { data: sitesData, isLoading: sitesLoading } = useQuery({
    queryKey: ['project-sites', projectId],
    queryFn: () => projectsApi.listSites(projectId),
    enabled: !!projectId,
  });

  const sites = useMemo(() => {
    const raw = sitesData?.data;
    if (Array.isArray(raw)) {
      return raw;
    }
    return raw?.items || [];
  }, [sitesData]);

  useEffect(() => {
    if (!selectedSiteId && sites.length > 0) {
      setSelectedSiteId(sites[0].id);
    }
  }, [selectedSiteId, sites]);

  const { data: recordingsData, isLoading: recordingsLoading } = useQuery({
    queryKey: ['recordings', selectedSiteId],
    queryFn: () => recordingsApi.list(selectedSiteId as string, 1, 10),
    enabled: !!selectedSiteId,
  });

  const recordings = recordingsData?.data?.items || [];

  const createSiteMutation = useMutation({
    mutationFn: () =>
      projectsApi.createSite(projectId, {
        name: siteForm.name.trim(),
        description: siteForm.description.trim() || undefined,
        latitude: parseFloat(siteForm.latitude),
        longitude: parseFloat(siteForm.longitude),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['project-sites', projectId] });
      setIsCreateSiteOpen(false);
      setSiteForm({ name: '', description: '', latitude: '', longitude: '' });
      toast.success('Site created');
    },
    onError: () => {
      toast.error('Failed to create site');
    },
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!selectedSiteId || !uploadFile) {
        throw new Error('Missing upload data');
      }
      return recordingsApi.upload(selectedSiteId, uploadFile, {
        recorded_at: recordedAt || undefined,
        latitude: uploadLatitude ? parseFloat(uploadLatitude) : undefined,
        longitude: uploadLongitude ? parseFloat(uploadLongitude) : undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recordings', selectedSiteId] });
      queryClient.invalidateQueries({ queryKey: ['project-summary', projectId] });
      setUploadFile(null);
      setRecordedAt('');
      setUploadLatitude('');
      setUploadLongitude('');
      toast.success('Recording uploaded');
    },
    onError: () => {
      toast.error('Failed to upload recording');
    },
  });

  const project = projectData?.data;
  const summary = summaryData?.data;
  const totalRecordings = summary?.recording_count ?? project?.recording_count ?? 0;
  const totalCalls = summary?.total_calls ?? project?.total_calls ?? 0;
  const siteCount = summary?.site_count ?? project?.site_count ?? sites.length;

  const handleCreateSite = (e: React.FormEvent) => {
    e.preventDefault();
    if (!siteForm.name.trim() || !siteForm.latitude || !siteForm.longitude) {
      toast.error('Please provide a site name and coordinates');
      return;
    }
    createSiteMutation.mutate();
  };

  const handleUpload = (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) {
      toast.error('Select a recording file to upload');
      return;
    }
    uploadMutation.mutate();
  };

  if (projectLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">Project not found.</p>
        <Link href="/projects" className="btn-primary mt-4">
          Return to Projects
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="space-y-2">
          <Link href="/projects" className="text-sm text-gray-400 hover:text-primary-400 flex items-center gap-2">
            <ArrowLeftIcon className="h-4 w-4" />
            Back to Projects
          </Link>
          <h1 className="text-3xl font-bold text-white">{project.name}</h1>
          <p className="text-gray-400 max-w-2xl">
            {project.description || 'Track sites, recordings, and AI classifications for this survey project.'}
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button onClick={() => setIsCreateSiteOpen(true)} className="btn-secondary">
            <PlusIcon className="h-5 w-5 mr-2" />
            New Site
          </button>
          <Link href="/review" className="btn-primary">
            <ArrowPathIcon className="h-5 w-5 mr-2" />
            Review Calls
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        <div className="card">
          <p className="text-sm text-gray-400">Sites</p>
          <p className="text-3xl font-bold text-white mt-2">{siteCount}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Total Recordings</p>
          <p className="text-3xl font-bold text-white mt-2">{totalRecordings.toLocaleString()}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Detected Calls</p>
          <p className="text-3xl font-bold text-white mt-2">{totalCalls.toLocaleString()}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Status</p>
          <p className="mt-2">
            <span
              className={`badge ${
                project.status === 'active'
                  ? 'badge-success'
                  : project.status === 'processing'
                  ? 'badge-warning'
                  : 'badge-info'
              }`}
            >
              {project.status}
            </span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 space-y-6">
          <div className="card">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Survey Sites</h2>
                <p className="text-sm text-gray-400">Manage recording locations and field metadata.</p>
              </div>
              <button onClick={() => setIsCreateSiteOpen(true)} className="btn-secondary">
                <PlusIcon className="h-5 w-5 mr-2" />
                Add Site
              </button>
            </div>

            {sitesLoading ? (
              <div className="flex items-center justify-center h-40">
                <div className="spinner" />
              </div>
            ) : sites.length === 0 ? (
              <div className="text-center py-10">
                <MapPinIcon className="h-12 w-12 text-gray-600 mx-auto mb-3" />
                <h3 className="text-lg font-semibold text-white">No sites yet</h3>
                <p className="text-gray-400 mt-2">
                  Add your first survey site to start uploading recordings.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {sites.map((site: any) => (
                  <button
                    key={site.id}
                    onClick={() => setSelectedSiteId(site.id)}
                    className={`text-left rounded-lg border p-4 transition-colors ${
                      selectedSiteId === site.id
                        ? 'border-primary-500 bg-primary-500/10'
                        : 'border-gray-800 bg-gray-900 hover:border-gray-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-white font-semibold">{site.name}</p>
                        <p className="text-sm text-gray-400 mt-1">
                          {site.description || 'No description provided'}
                        </p>
                      </div>
                      <span className="badge badge-info">{site.recording_count || 0} recordings</span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-500 mt-3">
                      <MapPinIcon className="h-4 w-4" />
                      <span>
                        {site.latitude?.toFixed?.(4) ?? site.latitude}, {site.longitude?.toFixed?.(4) ?? site.longitude}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="card">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-4">
              <div>
                <h2 className="text-lg font-semibold text-white">Recent Recordings</h2>
                <p className="text-sm text-gray-400">
                  Review uploads and jump into individual recording details.
                </p>
              </div>
              <select
                value={selectedSiteId || ''}
                onChange={(e) => setSelectedSiteId(e.target.value)}
                className="input w-full sm:w-auto"
              >
                {sites.length === 0 && (
                  <option value="">No sites available</option>
                )}
                {sites.map((site: any) => (
                  <option key={site.id} value={site.id}>
                    {site.name}
                  </option>
                ))}
              </select>
            </div>

            {!selectedSiteId ? (
              <p className="text-gray-400">Select a site to view recordings.</p>
            ) : recordingsLoading ? (
              <div className="flex items-center justify-center h-32">
                <div className="spinner" />
              </div>
            ) : recordings.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No recordings uploaded for this site yet.
              </div>
            ) : (
              <div className="space-y-3">
                {recordings.map((recording: any) => (
                  <Link
                    key={recording.id}
                    href={`/recordings/${recording.id}`}
                    className="flex flex-col gap-2 rounded-lg bg-gray-800 p-4 transition-colors hover:bg-gray-700 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div>
                      <p className="text-white font-medium">
                        {recording.original_filename || 'Untitled Recording'}
                      </p>
                      <p className="text-sm text-gray-400">
                        {recording.duration_seconds?.toFixed?.(1) ?? recording.duration_seconds}s ·{' '}
                        {recording.total_calls || 0} calls
                      </p>
                    </div>
                    <span className="badge badge-warning">
                      {recording.status || 'processing'}
                    </span>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Upload Recording</h2>
            <form onSubmit={handleUpload} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Recording File</label>
                <input
                  type="file"
                  accept=".wav,.flac,.mp3"
                  onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                  className="input"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-400 mb-2">Recorded At</label>
                <input
                  type="datetime-local"
                  value={recordedAt}
                  onChange={(e) => setRecordedAt(e.target.value)}
                  className="input"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={uploadLatitude}
                    onChange={(e) => setUploadLatitude(e.target.value)}
                    className="input"
                    placeholder="34.0522"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-400 mb-2">Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={uploadLongitude}
                    onChange={(e) => setUploadLongitude(e.target.value)}
                    className="input"
                    placeholder="-118.2437"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={!selectedSiteId || uploadMutation.isPending}
                className="btn-primary w-full"
              >
                {uploadMutation.isPending ? (
                  <span className="spinner" />
                ) : (
                  <>
                    <CloudArrowUpIcon className="h-5 w-5 mr-2" />
                    Upload Recording
                  </>
                )}
              </button>
              {!selectedSiteId && (
                <p className="text-xs text-gray-500 text-center">
                  Select a site to enable uploads.
                </p>
              )}
            </form>
          </div>

          <div className="card">
            <h2 className="text-lg font-semibold text-white mb-4">Quick Tips</h2>
            <ul className="space-y-3 text-sm text-gray-400">
              <li className="flex gap-2">
                <MusicalNoteIcon className="h-5 w-5 text-primary-400" />
                Upload full-spectrum WAV or FLAC recordings for best results.
              </li>
              <li className="flex gap-2">
                <MapPinIcon className="h-5 w-5 text-primary-400" />
                Add GPS coordinates to improve species filtering accuracy.
              </li>
              <li className="flex gap-2">
                <ArrowPathIcon className="h-5 w-5 text-primary-400" />
                Review AI calls daily to keep data quality high.
              </li>
            </ul>
          </div>
        </div>
      </div>

      <Dialog
        open={isCreateSiteOpen}
        onClose={() => setIsCreateSiteOpen(false)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="card max-w-lg w-full">
            <Dialog.Title className="text-xl font-semibold text-white mb-4">Add Survey Site</Dialog.Title>
            <form onSubmit={handleCreateSite} className="space-y-4">
              <div>
                <label className="label">Site Name</label>
                <input
                  type="text"
                  value={siteForm.name}
                  onChange={(e) => setSiteForm({ ...siteForm, name: e.target.value })}
                  className="input"
                  placeholder="Bear Creek Preserve"
                />
              </div>
              <div>
                <label className="label">Description</label>
                <textarea
                  value={siteForm.description}
                  onChange={(e) => setSiteForm({ ...siteForm, description: e.target.value })}
                  className="input"
                  rows={3}
                  placeholder="Notes about habitat, access, and survey details."
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="label">Latitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={siteForm.latitude}
                    onChange={(e) => setSiteForm({ ...siteForm, latitude: e.target.value })}
                    className="input"
                    placeholder="34.0522"
                  />
                </div>
                <div>
                  <label className="label">Longitude</label>
                  <input
                    type="number"
                    step="0.0001"
                    value={siteForm.longitude}
                    onChange={(e) => setSiteForm({ ...siteForm, longitude: e.target.value })}
                    className="input"
                    placeholder="-118.2437"
                  />
                </div>
              </div>
              <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setIsCreateSiteOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSiteMutation.isPending}
                  className="btn-primary"
                >
                  {createSiteMutation.isPending ? <span className="spinner" /> : 'Create Site'}
                </button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
