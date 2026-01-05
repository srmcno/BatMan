import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Dialog } from '@headlessui/react';
import { PlusIcon, FolderIcon, TrashIcon } from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { projectsApi } from '../lib/api';

export default function Projects() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDescription, setNewProjectDescription] = useState('');
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(1, 100),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      projectsApi.create({
        name: newProjectName,
        description: newProjectDescription || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      setIsCreateOpen(false);
      setNewProjectName('');
      setNewProjectDescription('');
      toast.success('Project created successfully');
    },
    onError: () => {
      toast.error('Failed to create project');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => projectsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project deleted');
    },
    onError: () => {
      toast.error('Failed to delete project');
    },
  });

  const projects = data?.data?.items || [];

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (newProjectName.trim()) {
      createMutation.mutate();
    }
  };

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Are you sure you want to delete "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Projects</h1>
          <p className="mt-2 text-gray-400">Manage your bat survey projects</p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="btn-primary"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          New Project
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <div className="spinner" />
        </div>
      ) : projects.length === 0 ? (
        <div className="card text-center py-12">
          <FolderIcon className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No projects yet</h3>
          <p className="text-gray-400 mb-4">
            Create your first project to start organizing your bat survey data.
          </p>
          <button onClick={() => setIsCreateOpen(true)} className="btn-primary">
            <PlusIcon className="h-5 w-5 mr-2" />
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project: any) => (
            <div key={project.id} className="card group">
              <div className="flex items-start justify-between">
                <Link to={`/projects/${project.id}`} className="flex-1">
                  <h3 className="text-lg font-semibold text-white group-hover:text-primary-400 transition-colors">
                    {project.name}
                  </h3>
                  <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                    {project.description || 'No description'}
                  </p>
                </Link>
                <button
                  onClick={() => handleDelete(project.id, project.name)}
                  className="p-1 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </div>
              <div className="mt-4 flex items-center gap-4 text-sm text-gray-500">
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
                <span>{project.site_count || 0} sites</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      <Dialog
        open={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        className="relative z-50"
      >
        <div className="fixed inset-0 bg-black/50" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="card max-w-md w-full">
            <Dialog.Title className="text-xl font-semibold text-white mb-4">
              Create New Project
            </Dialog.Title>
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="projectName" className="label">
                  Project Name
                </label>
                <input
                  id="projectName"
                  type="text"
                  value={newProjectName}
                  onChange={(e) => setNewProjectName(e.target.value)}
                  className="input"
                  placeholder="My Bat Survey 2024"
                  required
                />
              </div>
              <div>
                <label htmlFor="projectDescription" className="label">
                  Description (optional)
                </label>
                <textarea
                  id="projectDescription"
                  value={newProjectDescription}
                  onChange={(e) => setNewProjectDescription(e.target.value)}
                  className="input"
                  rows={3}
                  placeholder="Describe your project..."
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="btn-primary"
                >
                  {createMutation.isPending ? (
                    <span className="spinner" />
                  ) : (
                    'Create Project'
                  )}
                </button>
              </div>
            </form>
          </Dialog.Panel>
        </div>
      </Dialog>
    </div>
  );
}
