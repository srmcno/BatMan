import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  FolderIcon,
  MusicalNoteIcon,
  BeakerIcon,
  ClipboardDocumentCheckIcon,
  ArrowTrendingUpIcon,
} from '@heroicons/react/24/outline';
import { projectsApi, classificationsApi } from '../lib/api';

interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ElementType;
  change?: string;
  changeType?: 'increase' | 'decrease';
}

function StatCard({ title, value, icon: Icon, change, changeType }: StatCardProps) {
  return (
    <div className="card">
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <Icon className="h-8 w-8 text-primary-500" />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-400">{title}</p>
          <p className="text-2xl font-semibold text-white">{value}</p>
          {change && (
            <p
              className={`text-sm ${
                changeType === 'increase' ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {change}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data: projectsData } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(1, 100),
  });

  const { data: pendingReview } = useQuery({
    queryKey: ['pending-review'],
    queryFn: () => classificationsApi.getPendingReview(undefined, 1, 1),
  });

  const projects = projectsData?.data?.items || [];
  const totalProjects = projectsData?.data?.total || 0;
  const pendingCount = pendingReview?.data?.total || 0;

  // Calculate totals
  const totalRecordings = projects.reduce(
    (sum: number, p: any) => sum + (p.recording_count || 0),
    0
  );
  const totalCalls = projects.reduce(
    (sum: number, p: any) => sum + (p.total_calls || 0),
    0
  );

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        <p className="mt-2 text-gray-400">
          Welcome to EcoEcho AI. Here's an overview of your bat monitoring data.
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Active Projects"
          value={totalProjects}
          icon={FolderIcon}
        />
        <StatCard
          title="Total Recordings"
          value={totalRecordings.toLocaleString()}
          icon={MusicalNoteIcon}
        />
        <StatCard
          title="Detected Calls"
          value={totalCalls.toLocaleString()}
          icon={BeakerIcon}
        />
        <StatCard
          title="Pending Review"
          value={pendingCount}
          icon={ClipboardDocumentCheckIcon}
        />
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-4">
            <Link to="/projects" className="btn-secondary">
              <FolderIcon className="h-5 w-5 mr-2" />
              View Projects
            </Link>
            <Link to="/review" className="btn-primary">
              <ClipboardDocumentCheckIcon className="h-5 w-5 mr-2" />
              Review Calls ({pendingCount})
            </Link>
          </div>
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
          <div className="space-y-3">
            {projects.slice(0, 3).map((project: any) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-800 hover:bg-gray-700 transition-colors"
              >
                <div>
                  <p className="text-white font-medium">{project.name}</p>
                  <p className="text-sm text-gray-400">
                    {project.site_count || 0} sites
                  </p>
                </div>
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
              </Link>
            ))}
            {projects.length === 0 && (
              <p className="text-gray-500 text-center py-4">
                No projects yet. Create your first project to get started.
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Species chart placeholder */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Species Distribution</h2>
          <ArrowTrendingUpIcon className="h-5 w-5 text-gray-400" />
        </div>
        <div className="h-64 flex items-center justify-center text-gray-500">
          <p>Species distribution chart will appear here once data is available</p>
        </div>
      </div>
    </div>
  );
}
