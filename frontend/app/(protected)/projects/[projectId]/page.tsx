'use client';
import Link from 'next/link';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Dialog } from '@headlessui/react';
import { PlusIcon, MapPinIcon, MusicalNoteIcon, ArrowUpTrayIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { projectsApi } from '@/lib/api';

export default function ProjectDetail() {
  const params = useParams()
  const projectId = params.projectId as string;
  const [isCreateSiteOpen, setIsCreateSiteOpen] = useState(false);
  const [newSite, setNewSite] = useState({
    name: '',
    latitude: '',
    longitude: '',
    description: '',
  });
  const queryClient = useQueryClient();

  const { data: project, isLoading: projectLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId!),
    enabled: !!projectId,
  });

  const { data: sites, isLoading: sitesLoading } = useQuery({
    queryKey: ['sites', projectId],
    queryFn: () => projectsApi.listSites(projectId!),
    enabled: !!projectId,
  });

  const { data: summary } = useQuery({
    queryKey: ['project-summary', projectId],
    queryFn: () => projectsApi.getSummary(projectId!),
    enabled: !!projectId,
  });

  const createSiteMutation = useMutation({
    mutationFn: () =>
      projectsApi.createSite(projectId!, {
        name: newSite.name,
        latitude: parseFloat(newSite.latitude),
        longitude: parseFloat(newSite.longitude),
        description: newSite.description || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites', projectId] });
      setIsCreateSiteOpen(false);
      setNewSite({ name: '', latitude: '', longitude: '', description: '' });
      toast.success('Site created successfully');
    },
    onError: () => {
      toast.error('Failed to create site');
    },
  });

  if (projectLoading || sitesLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  const projectData = project?.data;
  const sitesData = sites?.data || [];
  const summaryData = summary?.data;

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-2">
          <Link href="/projects" className="hover:text-white">
            Projects
          </Link>
          <span>/</span>
          <span className="text-white">{projectData?.name}</span>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">{projectData?.name}</h1>
            <p className="mt-2 text-gray-400">{projectData?.description || 'No description'}</p>
          </div>
          <button onClick={() => setIsCreateSiteOpen(true)} className="btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Add Site
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="card">
          <p className="text-sm text-gray-400">Sites</p>
          <p className="text-2xl font-bold text-white">{summaryData?.site_count || 0}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Recordings</p>
          <p className="text-2xl font-bold text-white">{summaryData?.recording_count || 0}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Total Calls</p>
          <p className="text-2xl font-bold text-white">{summaryData?.total_calls || 0}</p>
        </div>
        <div className="card">
          <p className="text-sm text-gray-400">Species</p>
          <p className="text-2xl font-bold text-white">{summaryData?.species_count || 0}</p>
        </div>
      </div>

      {/* Sites */}
      <h2 className="text-xl font-semibold text-white mb-4">Survey Sites</h2>
      {sitesData.length === 0 ? (
        <div className="card text-center py-12">
          <MapPinIcon className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No sites yet</h3>
          <p className="text-gray-400 mb-4">Add survey sites to start uploading recordings.</p>
          <button onClick={() => setIsCreateSiteOpen(true)} className="btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Add Site
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sitesData.map((site: any) => (
            <div key={site.id} className="card">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="text-lg font-semibold text-white">{site.name}</h3>
                  <p className="text-sm text-gray-400">
                    {site.latitude.toFixed(4)}°N, {site.longitude.toFixed(4)}°W
                  </p>
                </div>
                <MapPinIcon className="h-5 w-5 text-primary-500" />
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-500 mb-4">
                <span className="flex items-center gap-1">
                  <MusicalNoteIcon className="h-4 w-4" />
                  {site.total_recordings || 0} recordings
                </span>
                <span>{site.total_calls || 0} calls</span>
              </div>
              <div className="flex gap-2">
                <Link
                  to={`/projects/${projectId}/sites/${site.id}/recordings`}
                  className="btn-secondary flex-1 text-sm"
                >
                  View Recordings
                </Link>
                <Link
                  to={`/projects/${projectId}/sites/${site.id}/recordings?upload=true`}
                  className="btn-primary text-sm"
                >
                  <ArrowUpTrayIcon className="h-4 w-4" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Site Modal */}
      <Dialog
        open={isCreateSiteOpen}
        onClose={() => setIsCreateSiteOpen(false)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="card max-w-md w-full">
            <Dialog.Title className="text-xl font-semibold text-white mb-4">
              Add Survey Site
            </Dialog.Title>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                createSiteMutation.mutate();
              }}
              className="space-y-4"
            >
              <div>
                <label className="label">Site Name</label>
                <input
                  type="text"
                  value={newSite.name}
                  onChange={(e) => setNewSite({ ...newSite, name: e.target.value })}
                  className="input"
                  placeholder="Meadow North"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="label">Latitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={newSite.latitude}
                    onChange={(e) => setNewSite({ ...newSite, latitude: e.target.value })}
                    className="input"
                    placeholder="38.9072"
                    required
                  />
                </div>
                <div>
                  <label className="label">Longitude</label>
                  <input
                    type="number"
                    step="0.000001"
                    value={newSite.longitude}
                    onChange={(e) => setNewSite({ ...newSite, longitude: e.target.value })}
                    className="input"
                    placeholder="-77.0369"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="label">Description (optional)</label>
                <textarea
                  value={newSite.description}
                  onChange={(e) => setNewSite({ ...newSite, description: e.target.value })}
                  className="input"
                  rows={2}
                />
              </div>
              <div className="flex justify-end gap-3">
                <button type="button" onClick={() => setIsCreateSiteOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={createSiteMutation.isPending} className="btn-primary">
                  {createSiteMutation.isPending ? <span className="spinner" /> : 'Add Site'}
                </button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
