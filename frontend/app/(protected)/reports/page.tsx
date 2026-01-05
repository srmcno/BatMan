'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  DocumentArrowDownIcon,
  ChartBarIcon,
  MapIcon,
  CalendarDaysIcon,
  FunnelIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { reportsApi, projectsApi } from '@/lib/api';

type ReportType = 'diversity' | 'activity' | 'nabat' | 'summary';

interface ReportConfig {
  project_id?: string;
  site_id?: string;
  start_date?: string;
  end_date?: string;
  species_codes?: string[];
}

export default function Reports() {
  const [activeReport, setActiveReport] = useState<ReportType>('diversity');
  const [config, setConfig] = useState<ReportConfig>({});
  const [showFilters, setShowFilters] = useState(false);

  const { data: projects } = useQuery({
    queryKey: ['projects'],
    queryFn: () => projectsApi.list(),
  });

  const { data: diversityData, isLoading: diversityLoading } = useQuery({
    queryKey: ['reports', 'diversity', config.project_id, config.site_id],
    queryFn: () => reportsApi.getDiversity(config.project_id!, config.site_id),
    enabled: activeReport === 'diversity' && !!config.project_id,
  });

  const { data: activityData, isLoading: activityLoading } = useQuery({
    queryKey: ['reports', 'activity', config.project_id, config.site_id],
    queryFn: () => reportsApi.getActivity(config.project_id!),
    enabled: activeReport === 'activity' && !!config.project_id,
  });

  const exportNabatMutation = useMutation({
    mutationFn: ({ projectId }: { projectId: string }) =>
      reportsApi.exportNabat(projectId),
    onSuccess: (response) => {
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nabat_export_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('NABat report exported');
    },
    onError: () => {
      toast.error('Failed to export NABat report');
    },
  });

  const exportSummaryMutation = useMutation({
    mutationFn: ({ projectId }: { projectId: string }) =>
      reportsApi.exportSummary(projectId),
    onSuccess: (response) => {
      const url = URL.createObjectURL(response.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = `summary_${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Summary report exported');
    },
    onError: () => {
      toast.error('Failed to export summary report');
    },
  });

  const reportTabs = [
    { id: 'diversity' as ReportType, name: 'Species Diversity', icon: ChartBarIcon },
    { id: 'activity' as ReportType, name: 'Activity Summary', icon: CalendarDaysIcon },
    { id: 'nabat' as ReportType, name: 'NABat Export', icon: DocumentArrowDownIcon },
    { id: 'summary' as ReportType, name: 'Summary Export', icon: MapIcon },
  ];

  const handleExport = () => {
    if (!config.project_id) {
      toast.error('Please select a project first');
      return;
    }

    if (activeReport === 'nabat') {
      exportNabatMutation.mutate({ projectId: config.project_id! });
    } else if (activeReport === 'summary') {
      exportSummaryMutation.mutate({ projectId: config.project_id! });
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Reports & Analytics</h1>
          <p className="mt-2 text-gray-400">Generate compliance reports and analyze bat activity data</p>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`btn-secondary ${showFilters ? 'bg-gray-700' : ''}`}
        >
          <FunnelIcon className="h-5 w-5 mr-2" />
          Filters
        </button>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="card mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Project</label>
              <select
                value={config.project_id || ''}
                onChange={(e) => setConfig({ ...config, project_id: e.target.value, site_id: undefined })}
                className="input w-full"
              >
                <option value="">Select project...</option>
                {projects?.data?.items?.map((project: { id: string; name: string }) => (
                  <option key={project.id} value={project.id}>
                    {project.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Site (optional)</label>
              <select
                value={config.site_id || ''}
                onChange={(e) => setConfig({ ...config, site_id: e.target.value || undefined })}
                className="input w-full"
                disabled={!config.project_id}
              >
                <option value="">All sites</option>
                {/* Sites would be loaded based on selected project */}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Start Date</label>
              <input
                type="date"
                value={config.start_date || ''}
                onChange={(e) => setConfig({ ...config, start_date: e.target.value || undefined })}
                className="input w-full"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">End Date</label>
              <input
                type="date"
                value={config.end_date || ''}
                onChange={(e) => setConfig({ ...config, end_date: e.target.value || undefined })}
                className="input w-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Report tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-800 pb-4">
        {reportTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveReport(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
              activeReport === tab.id
                ? 'bg-primary-600 text-white'
                : 'text-gray-400 hover:bg-gray-800 hover:text-white'
            }`}
          >
            <tab.icon className="h-5 w-5" />
            {tab.name}
          </button>
        ))}
      </div>

      {/* Report content */}
      {!config.project_id ? (
        <div className="card text-center py-12">
          <ChartBarIcon className="h-12 w-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">Select a Project</h3>
          <p className="text-gray-400">Choose a project from the filters to generate reports</p>
        </div>
      ) : activeReport === 'diversity' ? (
        <DiversityReport data={diversityData?.data} isLoading={diversityLoading} />
      ) : activeReport === 'activity' ? (
        <ActivityReport data={activityData?.data} isLoading={activityLoading} />
      ) : (
        <ExportReport
          type={activeReport}
          onExport={handleExport}
          isExporting={exportNabatMutation.isPending || exportSummaryMutation.isPending}
        />
      )}
    </div>
  );
}

function DiversityReport({
  data,
  isLoading,
}: {
  data?: {
    total_species: number;
    total_classifications: number;
    shannon_index: number;
    simpson_index: number;
    species_counts: Record<string, number>;
  };
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">No diversity data available</p>
      </div>
    );
  }

  const sortedSpecies = Object.entries(data.species_counts || {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 10);

  const maxCount = Math.max(...sortedSpecies.map(([, count]) => count), 1);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Summary cards */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Diversity Indices</h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Total Species</p>
            <p className="text-3xl font-bold text-white">{data.total_species}</p>
          </div>
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Total Classifications</p>
            <p className="text-3xl font-bold text-white">{data.total_classifications.toLocaleString()}</p>
          </div>
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Shannon Index (H')</p>
            <p className="text-3xl font-bold text-primary-400">{data.shannon_index.toFixed(3)}</p>
            <p className="text-xs text-gray-500 mt-1">Higher = more diverse</p>
          </div>
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Simpson Index (1-D)</p>
            <p className="text-3xl font-bold text-primary-400">{data.simpson_index.toFixed(3)}</p>
            <p className="text-xs text-gray-500 mt-1">Higher = more diverse</p>
          </div>
        </div>
      </div>

      {/* Species distribution */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Top 10 Species</h3>
        <div className="space-y-3">
          {sortedSpecies.map(([species, count]) => (
            <div key={species}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-gray-300">{species}</span>
                <span className="text-gray-400">{count.toLocaleString()}</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all"
                  style={{ width: `${(count / maxCount) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ActivityReport({
  data,
  isLoading,
}: {
  data?: {
    total_recordings: number;
    total_calls: number;
    date_range: { start: string; end: string };
    activity_by_type: Record<string, number>;
    activity_by_hour: Record<string, number>;
    recordings_by_date: Record<string, number>;
  };
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="spinner" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="card text-center py-12">
        <p className="text-gray-400">No activity data available</p>
      </div>
    );
  }

  const hourlyData = Object.entries(data.activity_by_hour || {}).sort(
    ([a], [b]) => parseInt(a) - parseInt(b)
  );
  const maxHourly = Math.max(...hourlyData.map(([, count]) => count), 1);

  const activityTypes = Object.entries(data.activity_by_type || {});
  const totalActivity = activityTypes.reduce((sum, [, count]) => sum + count, 0);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Summary */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Activity Summary</h3>
        <div className="grid grid-cols-2 gap-4 mb-6">
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Total Recordings</p>
            <p className="text-3xl font-bold text-white">{data.total_recordings.toLocaleString()}</p>
          </div>
          <div className="p-4 bg-gray-800 rounded-lg">
            <p className="text-sm text-gray-400">Total Calls Detected</p>
            <p className="text-3xl font-bold text-white">{data.total_calls.toLocaleString()}</p>
          </div>
        </div>

        <h4 className="text-sm font-medium text-gray-400 mb-3">Activity Types</h4>
        <div className="space-y-2">
          {activityTypes.map(([type, count]) => (
            <div key={type} className="flex items-center justify-between">
              <span className="text-gray-300 capitalize">{type.replace('_', ' ')}</span>
              <div className="flex items-center gap-2">
                <div className="w-32 bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-secondary-500 h-2 rounded-full"
                    style={{ width: `${(count / totalActivity) * 100}%` }}
                  />
                </div>
                <span className="text-gray-400 text-sm w-16 text-right">
                  {((count / totalActivity) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hourly distribution */}
      <div className="card">
        <h3 className="text-lg font-semibold text-white mb-4">Activity by Hour</h3>
        <div className="flex items-end justify-between h-48 gap-1">
          {Array.from({ length: 24 }, (_, i) => {
            const count = data.activity_by_hour?.[i.toString()] || 0;
            const height = (count / maxHourly) * 100;
            return (
              <div key={i} className="flex-1 flex flex-col items-center">
                <div
                  className="w-full bg-primary-500 rounded-t transition-all hover:bg-primary-400"
                  style={{ height: `${Math.max(height, 2)}%` }}
                  title={`${i}:00 - ${count} calls`}
                />
              </div>
            );
          })}
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-2">
          <span>00:00</span>
          <span>06:00</span>
          <span>12:00</span>
          <span>18:00</span>
          <span>23:00</span>
        </div>
        <p className="text-center text-sm text-gray-400 mt-4">
          Peak activity hours highlighted
        </p>
      </div>
    </div>
  );
}

function ExportReport({
  type,
  onExport,
  isExporting,
}: {
  type: 'nabat' | 'summary';
  onExport: () => void;
  isExporting: boolean;
}) {
  const isNabat = type === 'nabat';

  return (
    <div className="card max-w-2xl">
      <div className="flex items-start gap-4 mb-6">
        <div className="p-3 bg-primary-600/20 rounded-lg">
          <DocumentArrowDownIcon className="h-8 w-8 text-primary-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-white">
            {isNabat ? 'NABat Export' : 'Summary Export'}
          </h3>
          <p className="text-gray-400 mt-1">
            {isNabat
              ? 'Export data in NABat-compatible CSV format for compliance reporting'
              : 'Export a comprehensive summary of all classifications and metadata'}
          </p>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-4 mb-6">
        <h4 className="text-sm font-medium text-white mb-2">Export includes:</h4>
        <ul className="text-sm text-gray-400 space-y-1">
          {isNabat ? (
            <>
              <li>• Site coordinates and metadata</li>
              <li>• Species detections with confidence scores</li>
              <li>• Recording dates and times</li>
              <li>• Call parameters (frequency, duration)</li>
              <li>• NABat-compliant column formatting</li>
            </>
          ) : (
            <>
              <li>• All classification results</li>
              <li>• Recording metadata and file paths</li>
              <li>• Vetting status and reviewer notes</li>
              <li>• Call parameters and features</li>
              <li>• Activity type classifications</li>
            </>
          )}
        </ul>
      </div>

      <button onClick={onExport} disabled={isExporting} className="btn-primary w-full">
        {isExporting ? (
          <>
            <div className="spinner h-5 w-5 mr-2" />
            Generating Export...
          </>
        ) : (
          <>
            <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
            Download {isNabat ? 'NABat' : 'Summary'} CSV
          </>
        )}
      </button>
    </div>
  );
}
