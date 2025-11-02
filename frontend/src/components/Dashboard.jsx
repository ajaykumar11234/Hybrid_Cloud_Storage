import { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';

const Dashboard = ({ BASE_URL }) => {
  const [stats, setStats] = useState({
    total_files: 0,
    total_size: 0,
    avg_file_size: 0,
    status_distribution: {},
    files_analyzed: 0
  });
  const [uploadData, setUploadData] = useState([]);
  const [tagData, setTagData] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [timeRange, setTimeRange] = useState(30);
  const [loading, setLoading] = useState({
    stats: true,
    uploads: true,
    tags: true,
    activity: true
  });
  const [errors, setErrors] = useState({
    stats: false,
    uploads: false,
    tags: false,
    activity: false
  });

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  const fetchDashboardData = async () => {
    setLoading({ stats: true, uploads: true, tags: true, activity: true });
    setErrors({ stats: false, uploads: false, tags: false, activity: false });
    
    try {
      const endpoints = [
        { key: 'stats', url: `${BASE_URL}/analytics/storage` },
        { key: 'uploads', url: `${BASE_URL}/analytics/uploads?days=${timeRange}` },
        { key: 'tags', url: `${BASE_URL}/analytics/tags?limit=10` },
        { key: 'activity', url: `${BASE_URL}/analytics/activity?hours=24` }
      ];

      const results = await Promise.allSettled(
        endpoints.map(endpoint => 
          fetch(endpoint.url)
            .then(response => {
              if (!response.ok) throw new Error(`HTTP ${response.status}`);
              return response.json();
            })
        )
      );

      // Process each result
      results.forEach((result, index) => {
        const endpoint = endpoints[index];
        
        if (result.status === 'fulfilled') {
          const data = result.value;
          switch (endpoint.key) {
            case 'stats':
              setStats(data.storage || {
                total_files: 0,
                total_size: 0,
                avg_file_size: 0,
                status_distribution: {},
                files_analyzed: 0
              });
              break;
            case 'uploads':
              setUploadData(data.daily_uploads || []);
              break;
            case 'tags':
              setTagData(data.top_tags || []);
              break;
            case 'activity':
              setRecentActivity(data.recent_activity || []);
              break;
          }
        } else {
          console.error(`Error fetching ${endpoint.key}:`, result.reason);
          setErrors(prev => ({ ...prev, [endpoint.key]: true }));
        }
      });

    } catch (error) {
      console.error('Error in dashboard data fetch:', error);
      setErrors({ stats: true, uploads: true, tags: true, activity: true });
    } finally {
      setLoading({ stats: false, uploads: false, tags: false, activity: false });
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82ca9d', '#ffc658', '#8dd1e1'];

  // Loading skeleton components
  const StatCardSkeleton = () => (
    <div className="bg-white p-4 rounded-lg shadow animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
      <div className="h-8 bg-gray-200 rounded w-3/4"></div>
    </div>
  );

  const ChartSkeleton = () => (
    <div className="bg-white p-4 rounded-lg shadow animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
      <div className="h-64 bg-gray-100 rounded"></div>
    </div>
  );

  const ErrorMessage = ({ message, onRetry }) => (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
      <div className="text-red-600 mb-2">{message}</div>
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors text-sm"
      >
        Retry
      </button>
    </div>
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Dashboard Analytics</h2>
          <p className="text-slate-600 mt-1">Monitor your file storage and AI analysis insights</p>
        </div>
        <div className="flex items-center gap-4">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(Number(e.target.value))}
            className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value={7}>Last 7 Days</option>
            <option value={30}>Last 30 Days</option>
            <option value={90}>Last 90 Days</option>
          </select>
          <button
            onClick={fetchDashboardData}
            disabled={Object.values(loading).some(l => l)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {loading.stats ? (
          <>
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
            <StatCardSkeleton />
          </>
        ) : errors.stats ? (
          <div className="col-span-4">
            <ErrorMessage 
              message="Failed to load statistics" 
              onRetry={fetchDashboardData}
            />
          </div>
        ) : (
          <>
            <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
              <h3 className="text-lg font-semibold text-slate-700">Total Files</h3>
              <p className="text-2xl font-bold text-blue-600">{stats.total_files || 0}</p>
              <div className="flex justify-between text-sm text-slate-500 mt-2">
                <span>MinIO: {stats.status_distribution?.minio || 0}</span>
                <span>S3: {stats.status_distribution?.['uploaded-to-s3'] || 0}</span>
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow border-l-4 border-green-500">
              <h3 className="text-lg font-semibold text-slate-700">Total Storage</h3>
              <p className="text-2xl font-bold text-green-600">
                {formatFileSize(stats.total_size)}
              </p>
              <div className="text-sm text-slate-500 mt-2">
                Avg: {formatFileSize(stats.avg_file_size)}
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow border-l-4 border-purple-500">
              <h3 className="text-lg font-semibold text-slate-700">AI Analyzed</h3>
              <p className="text-2xl font-bold text-purple-600">{stats.files_analyzed || 0}</p>
              <div className="text-sm text-slate-500 mt-2">
                {stats.total_files ? Math.round((stats.files_analyzed / stats.total_files) * 100) : 0}% of files
              </div>
            </div>
            
            <div className="bg-white p-4 rounded-lg shadow border-l-4 border-orange-500">
              <h3 className="text-lg font-semibold text-slate-700">Recent Activity</h3>
              <p className="text-2xl font-bold text-orange-600">{recentActivity.length}</p>
              <div className="text-sm text-slate-500 mt-2">
                Last 24 hours
              </div>
            </div>
          </>
        )}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Uploads Over Time */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Uploads Over Time</h3>
            {errors.uploads && (
              <span className="text-sm text-red-600 bg-red-50 px-2 py-1 rounded">Data unavailable</span>
            )}
          </div>
          
          {loading.uploads ? (
            <ChartSkeleton />
          ) : errors.uploads ? (
            <ErrorMessage 
              message="Failed to load upload data" 
              onRetry={fetchDashboardData}
            />
          ) : uploadData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p>No upload data available</p>
                <p className="text-sm">Upload files to see analytics</p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={uploadData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="_id" 
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(value) => {
                    const date = new Date(value);
                    return date.toLocaleDateString('en-US', { 
                      month: 'short', 
                      day: 'numeric',
                      year: 'numeric'
                    });
                  }}
                  formatter={(value) => [`${value} uploads`, 'Uploads']}
                />
                <Area 
                  type="monotone" 
                  dataKey="count" 
                  stroke="#8884d8" 
                  fill="#8884d8" 
                  fillOpacity={0.6}
                  name="Uploads"
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Top Tags */}
        <div className="bg-white p-4 rounded-lg shadow">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Top Tags</h3>
            {errors.tags && (
              <span className="text-sm text-red-600 bg-red-50 px-2 py-1 rounded">Data unavailable</span>
            )}
          </div>
          
          {loading.tags ? (
            <ChartSkeleton />
          ) : errors.tags ? (
            <ErrorMessage 
              message="Failed to load tag data" 
              onRetry={fetchDashboardData}
            />
          ) : tagData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                </svg>
                <p>No tags available</p>
                <p className="text-sm">AI analysis will generate tags</p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={tagData}
                  dataKey="count"
                  nameKey="_id"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ _id, count }) => `${_id}: ${count}`}
                >
                  {tagData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value, name) => [`${value} files`, name]} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white p-4 rounded-lg shadow">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Recent Activity</h3>
          {errors.activity && (
            <span className="text-sm text-red-600 bg-red-50 px-2 py-1 rounded">Data unavailable</span>
          )}
        </div>
        
        {loading.activity ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, index) => (
              <div key={index} className="flex items-center justify-between p-2 border-b animate-pulse">
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 rounded w-32"></div>
                  <div className="h-3 bg-gray-200 rounded w-48"></div>
                </div>
                <div className="h-3 bg-gray-200 rounded w-24"></div>
              </div>
            ))}
          </div>
        ) : errors.activity ? (
          <ErrorMessage 
            message="Failed to load activity data" 
            onRetry={fetchDashboardData}
          />
        ) : recentActivity.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <svg className="w-12 h-12 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p>No recent activity</p>
            <p className="text-sm">Upload files to see activity here</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {recentActivity.map((activity, index) => (
              <div 
                key={index} 
                className="flex items-center justify-between p-3 border-b hover:bg-gray-50 rounded transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      activity.event_type === 'file_uploaded' 
                        ? 'bg-blue-100 text-blue-800'
                        : activity.event_type === 'ai_analysis_completed'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {activity.event_type === 'file_uploaded' ? '📤 Upload' : 
                       activity.event_type === 'ai_analysis_completed' ? '🤖 AI Analysis' : 
                       '⚡ Activity'}
                    </span>
                    <span className="font-medium text-slate-800 truncate flex-1">
                      {activity.resource}
                    </span>
                  </div>
                  {activity.details && (
                    <p className="text-sm text-slate-600 mt-1">{activity.details}</p>
                  )}
                </div>
                <span className="text-sm text-slate-500 whitespace-nowrap ml-4">
                  {new Date(activity.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Connection Status */}
      <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-3 h-3 rounded-full ${
              Object.values(errors).some(e => e) ? 'bg-yellow-500' : 'bg-green-500'
            }`}></div>
            <div>
              <h4 className="font-medium text-slate-800">Connection Status</h4>
              <p className="text-sm text-slate-600">
                {Object.values(errors).some(e => e) 
                  ? 'Partial data available - some endpoints failed' 
                  : 'All systems operational'}
              </p>
            </div>
          </div>
          <button
            onClick={fetchDashboardData}
            className="flex items-center gap-2 px-3 py-1 bg-white border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-50 transition-colors text-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh Data
          </button>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;