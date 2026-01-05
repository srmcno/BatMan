import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import {
  UserCircleIcon,
  BellIcon,
  CogIcon,
  ShieldCheckIcon,
  PaintBrushIcon,
  CloudArrowUpIcon,
} from '@heroicons/react/24/outline';
import toast from 'react-hot-toast';
import { useAuthStore } from '../stores/authStore';

type SettingsTab = 'profile' | 'notifications' | 'processing' | 'appearance' | 'security' | 'sync';

export default function Settings() {
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const { user } = useAuthStore();

  const tabs = [
    { id: 'profile' as SettingsTab, name: 'Profile', icon: UserCircleIcon },
    { id: 'notifications' as SettingsTab, name: 'Notifications', icon: BellIcon },
    { id: 'processing' as SettingsTab, name: 'Processing', icon: CogIcon },
    { id: 'appearance' as SettingsTab, name: 'Appearance', icon: PaintBrushIcon },
    { id: 'security' as SettingsTab, name: 'Security', icon: ShieldCheckIcon },
    { id: 'sync' as SettingsTab, name: 'Cloud Sync', icon: CloudArrowUpIcon },
  ];

  return (
    <div>
      <h1 className="text-3xl font-bold text-white mb-8">Settings</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
        {/* Sidebar */}
        <div className="lg:col-span-1">
          <nav className="space-y-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-primary-600 text-white'
                    : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                {tab.name}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="lg:col-span-3">
          {activeTab === 'profile' && <ProfileSettings user={user} />}
          {activeTab === 'notifications' && <NotificationSettings />}
          {activeTab === 'processing' && <ProcessingSettings />}
          {activeTab === 'appearance' && <AppearanceSettings />}
          {activeTab === 'security' && <SecuritySettings />}
          {activeTab === 'sync' && <SyncSettings />}
        </div>
      </div>
    </div>
  );
}

function ProfileSettings({ user }: { user: { email: string; role: string } | null }) {
  const [formData, setFormData] = useState({
    full_name: '',
    organization: '',
    email: user?.email || '',
  });

  const handleSave = () => {
    toast.success('Profile updated');
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Profile Settings</h2>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Full Name</label>
          <input
            type="text"
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            className="input w-full max-w-md"
            placeholder="Enter your name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Email Address</label>
          <input
            type="email"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="input w-full max-w-md"
            placeholder="email@example.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Organization</label>
          <input
            type="text"
            value={formData.organization}
            onChange={(e) => setFormData({ ...formData, organization: e.target.value })}
            className="input w-full max-w-md"
            placeholder="Your organization name"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Role</label>
          <p className="text-white capitalize">{user?.role || 'User'}</p>
        </div>

        <button onClick={handleSave} className="btn-primary">
          Save Changes
        </button>
      </div>
    </div>
  );
}

function NotificationSettings() {
  const [settings, setSettings] = useState({
    email_processing_complete: true,
    email_review_ready: true,
    email_weekly_summary: false,
    push_processing: true,
    push_review: true,
  });

  const handleToggle = (key: keyof typeof settings) => {
    setSettings({ ...settings, [key]: !settings[key] });
    toast.success('Notification settings updated');
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Notification Preferences</h2>

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-white mb-4">Email Notifications</h3>
          <div className="space-y-4">
            <Toggle
              label="Processing Complete"
              description="Receive an email when batch processing finishes"
              enabled={settings.email_processing_complete}
              onToggle={() => handleToggle('email_processing_complete')}
            />
            <Toggle
              label="Review Ready"
              description="Get notified when new classifications are ready for review"
              enabled={settings.email_review_ready}
              onToggle={() => handleToggle('email_review_ready')}
            />
            <Toggle
              label="Weekly Summary"
              description="Receive a weekly summary of activity across all projects"
              enabled={settings.email_weekly_summary}
              onToggle={() => handleToggle('email_weekly_summary')}
            />
          </div>
        </div>

        <div className="border-t border-gray-800 pt-6">
          <h3 className="text-lg font-medium text-white mb-4">Push Notifications</h3>
          <div className="space-y-4">
            <Toggle
              label="Processing Updates"
              description="Real-time updates on processing progress"
              enabled={settings.push_processing}
              onToggle={() => handleToggle('push_processing')}
            />
            <Toggle
              label="Review Alerts"
              description="Instant alerts for high-priority review items"
              enabled={settings.push_review}
              onToggle={() => handleToggle('push_review')}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

function ProcessingSettings() {
  const [settings, setSettings] = useState({
    default_confidence_threshold: 0.7,
    auto_vetting_enabled: false,
    auto_vetting_threshold: 0.95,
    noise_reduction_method: 'spectral',
    parallel_processing: true,
    gpu_acceleration: true,
  });

  const handleSave = () => {
    toast.success('Processing settings saved');
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Processing Settings</h2>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Default Confidence Threshold
          </label>
          <div className="flex items-center gap-4">
            <input
              type="range"
              min="0.5"
              max="0.99"
              step="0.01"
              value={settings.default_confidence_threshold}
              onChange={(e) =>
                setSettings({ ...settings, default_confidence_threshold: parseFloat(e.target.value) })
              }
              className="flex-1 max-w-md"
            />
            <span className="text-white w-16">
              {(settings.default_confidence_threshold * 100).toFixed(0)}%
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Classifications below this threshold require manual review
          </p>
        </div>

        <div className="border-t border-gray-800 pt-6">
          <Toggle
            label="Auto-Vetting"
            description="Automatically approve high-confidence classifications"
            enabled={settings.auto_vetting_enabled}
            onToggle={() => setSettings({ ...settings, auto_vetting_enabled: !settings.auto_vetting_enabled })}
          />

          {settings.auto_vetting_enabled && (
            <div className="mt-4 ml-6">
              <label className="block text-sm font-medium text-gray-400 mb-2">
                Auto-Vetting Threshold
              </label>
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="0.9"
                  max="0.99"
                  step="0.01"
                  value={settings.auto_vetting_threshold}
                  onChange={(e) =>
                    setSettings({ ...settings, auto_vetting_threshold: parseFloat(e.target.value) })
                  }
                  className="flex-1 max-w-xs"
                />
                <span className="text-white w-16">
                  {(settings.auto_vetting_threshold * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-gray-800 pt-6">
          <label className="block text-sm font-medium text-gray-400 mb-2">Noise Reduction Method</label>
          <select
            value={settings.noise_reduction_method}
            onChange={(e) => setSettings({ ...settings, noise_reduction_method: e.target.value })}
            className="input w-full max-w-md"
          >
            <option value="spectral">Spectral Subtraction (Recommended)</option>
            <option value="wiener">Wiener Filter</option>
            <option value="adaptive">Adaptive (Auto-detect noise type)</option>
            <option value="none">None</option>
          </select>
        </div>

        <div className="border-t border-gray-800 pt-6 space-y-4">
          <Toggle
            label="Parallel Processing"
            description="Process multiple files simultaneously"
            enabled={settings.parallel_processing}
            onToggle={() => setSettings({ ...settings, parallel_processing: !settings.parallel_processing })}
          />
          <Toggle
            label="GPU Acceleration"
            description="Use GPU for faster inference (requires compatible hardware)"
            enabled={settings.gpu_acceleration}
            onToggle={() => setSettings({ ...settings, gpu_acceleration: !settings.gpu_acceleration })}
          />
        </div>

        <button onClick={handleSave} className="btn-primary">
          Save Settings
        </button>
      </div>
    </div>
  );
}

function AppearanceSettings() {
  const [settings, setSettings] = useState({
    theme: 'dark',
    spectrogram_colormap: 'viridis',
    compact_view: false,
  });

  const handleSave = () => {
    toast.success('Appearance settings saved');
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Appearance</h2>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Theme</label>
          <div className="flex gap-4">
            {['dark', 'light', 'system'].map((theme) => (
              <button
                key={theme}
                onClick={() => setSettings({ ...settings, theme })}
                className={`px-4 py-2 rounded-lg capitalize ${
                  settings.theme === theme
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {theme}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Spectrogram Color Map</label>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {['viridis', 'plasma', 'inferno', 'magma'].map((colormap) => (
              <button
                key={colormap}
                onClick={() => setSettings({ ...settings, spectrogram_colormap: colormap })}
                className={`p-4 rounded-lg capitalize ${
                  settings.spectrogram_colormap === colormap
                    ? 'ring-2 ring-primary-500'
                    : 'ring-1 ring-gray-700'
                }`}
              >
                <div
                  className="h-4 rounded mb-2"
                  style={{
                    background:
                      colormap === 'viridis'
                        ? 'linear-gradient(to right, #440154, #21918c, #fde725)'
                        : colormap === 'plasma'
                        ? 'linear-gradient(to right, #0d0887, #cc4778, #f0f921)'
                        : colormap === 'inferno'
                        ? 'linear-gradient(to right, #000004, #bc3754, #fcffa4)'
                        : 'linear-gradient(to right, #000004, #b63679, #fcfdbf)',
                  }}
                />
                <span className="text-sm text-gray-300">{colormap}</span>
              </button>
            ))}
          </div>
        </div>

        <Toggle
          label="Compact View"
          description="Use a more compact layout for tables and lists"
          enabled={settings.compact_view}
          onToggle={() => setSettings({ ...settings, compact_view: !settings.compact_view })}
        />

        <button onClick={handleSave} className="btn-primary">
          Save Settings
        </button>
      </div>
    </div>
  );
}

function SecuritySettings() {
  const [showChangePassword, setShowChangePassword] = useState(false);
  const { logout } = useAuthStore();

  const handleChangePassword = () => {
    toast.success('Password changed successfully');
    setShowChangePassword(false);
  };

  const handleLogoutAll = () => {
    toast.success('Logged out of all devices');
    logout();
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Security</h2>

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium text-white mb-2">Password</h3>
          {showChangePassword ? (
            <div className="space-y-4 max-w-md">
              <input type="password" placeholder="Current password" className="input w-full" />
              <input type="password" placeholder="New password" className="input w-full" />
              <input type="password" placeholder="Confirm new password" className="input w-full" />
              <div className="flex gap-2">
                <button onClick={handleChangePassword} className="btn-primary">
                  Update Password
                </button>
                <button onClick={() => setShowChangePassword(false)} className="btn-secondary">
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button onClick={() => setShowChangePassword(true)} className="btn-secondary">
              Change Password
            </button>
          )}
        </div>

        <div className="border-t border-gray-800 pt-6">
          <h3 className="text-lg font-medium text-white mb-2">Sessions</h3>
          <p className="text-gray-400 mb-4">Manage your active sessions across devices</p>
          <button onClick={handleLogoutAll} className="btn-secondary text-red-400 hover:text-red-300">
            Log Out of All Devices
          </button>
        </div>

        <div className="border-t border-gray-800 pt-6">
          <h3 className="text-lg font-medium text-white mb-2">Two-Factor Authentication</h3>
          <p className="text-gray-400 mb-4">Add an extra layer of security to your account</p>
          <button className="btn-secondary">Enable 2FA</button>
        </div>
      </div>
    </div>
  );
}

function SyncSettings() {
  const [settings, setSettings] = useState({
    auto_sync: true,
    sync_on_wifi_only: true,
    sync_interval: 15,
    cloud_provider: 'aws',
  });

  const handleSave = () => {
    toast.success('Sync settings saved');
  };

  return (
    <div className="card">
      <h2 className="text-xl font-semibold text-white mb-6">Cloud Sync</h2>

      <div className="space-y-6">
        <Toggle
          label="Automatic Sync"
          description="Automatically sync data with cloud storage"
          enabled={settings.auto_sync}
          onToggle={() => setSettings({ ...settings, auto_sync: !settings.auto_sync })}
        />

        {settings.auto_sync && (
          <>
            <Toggle
              label="WiFi Only"
              description="Only sync when connected to WiFi"
              enabled={settings.sync_on_wifi_only}
              onToggle={() => setSettings({ ...settings, sync_on_wifi_only: !settings.sync_on_wifi_only })}
            />

            <div>
              <label className="block text-sm font-medium text-gray-400 mb-2">Sync Interval</label>
              <select
                value={settings.sync_interval}
                onChange={(e) => setSettings({ ...settings, sync_interval: parseInt(e.target.value) })}
                className="input w-full max-w-md"
              >
                <option value={5}>Every 5 minutes</option>
                <option value={15}>Every 15 minutes</option>
                <option value={30}>Every 30 minutes</option>
                <option value={60}>Every hour</option>
              </select>
            </div>
          </>
        )}

        <div className="border-t border-gray-800 pt-6">
          <label className="block text-sm font-medium text-gray-400 mb-2">Cloud Provider</label>
          <select
            value={settings.cloud_provider}
            onChange={(e) => setSettings({ ...settings, cloud_provider: e.target.value })}
            className="input w-full max-w-md"
          >
            <option value="aws">Amazon S3</option>
            <option value="azure">Azure Blob Storage</option>
            <option value="gcp">Google Cloud Storage</option>
          </select>
        </div>

        <div className="border-t border-gray-800 pt-6">
          <h3 className="text-lg font-medium text-white mb-2">Storage Usage</h3>
          <div className="max-w-md">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Used</span>
              <span className="text-white">12.5 GB / 50 GB</span>
            </div>
            <div className="w-full bg-gray-800 rounded-full h-2">
              <div className="bg-primary-500 h-2 rounded-full" style={{ width: '25%' }} />
            </div>
          </div>
        </div>

        <button onClick={handleSave} className="btn-primary">
          Save Settings
        </button>
      </div>
    </div>
  );
}

function Toggle({
  label,
  description,
  enabled,
  onToggle,
}: {
  label: string;
  description: string;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-white font-medium">{label}</p>
        <p className="text-sm text-gray-400">{description}</p>
      </div>
      <button
        onClick={onToggle}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          enabled ? 'bg-primary-600' : 'bg-gray-700'
        }`}
      >
        <span
          className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
            enabled ? 'left-7' : 'left-1'
          }`}
        />
      </button>
    </div>
  );
}
