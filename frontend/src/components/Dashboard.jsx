import { useState, useEffect } from "react";
import {
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
} from "recharts";
import { fetchWithAuth } from "../utils/fetchWithAuth"; // ✅ secure fetch with JWT

// 🔹 Shared components outside main Dashboard (so all subcomponents can use them)
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

// 🔹 Reusable chart card for upload stats
const ChartCard = ({ title, data, error, loading, onRetry }) => {
  if (loading) return <ChartSkeleton />;
  if (error) return <ErrorMessage message={`Failed to load ${title}`} onRetry={onRetry} />;
  if (!data.length)
    return (
      <div className="bg-white p-4 rounded-lg shadow h-64 flex items-center justify-center text-gray-500">
        <p>No {title.toLowerCase()} data available</p>
      </div>
    );

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">{title}</h3>
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="_id" />
          <YAxis />
          <Tooltip />
          <Area
            type="monotone"
            dataKey="count"
            stroke="#8884d8"
            fill="#8884d8"
            fillOpacity={0.6}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

// 🔹 Top Tags chart
const TagChart = ({ data, error, loading, onRetry, COLORS }) => {
  if (loading) return <ChartSkeleton />;
  if (error) return <ErrorMessage message="Failed to load tag data" onRetry={onRetry} />;
  if (!data.length)
    return (
      <div className="bg-white p-4 rounded-lg shadow h-64 flex items-center justify-center text-gray-500">
        <p>No tags available</p>
      </div>
    );

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Top Tags</h3>
      <ResponsiveContainer width="100%" height={300}>
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="_id"
            cx="50%"
            cy="50%"
            outerRadius={100}
            label={({ _id, count }) => `${_id}: ${count}`}
          >
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip formatter={(value, name) => [`${value} files`, name]} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
};

// 🔹 Recent Activity list
const ActivitySection = ({ data, error, loading, onRetry }) => {
  if (loading) return <ChartSkeleton />;
  if (error) return <ErrorMessage message="Failed to load activity data" onRetry={onRetry} />;
  if (!data.length)
    return (
      <div className="bg-white p-4 rounded-lg shadow text-center py-8 text-gray-500">
        <p>No recent activity</p>
      </div>
    );

  return (
    <div className="bg-white p-4 rounded-lg shadow">
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {data.map((activity, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-3 border-b hover:bg-gray-50 rounded transition-colors"
          >
            <div className="flex-1">
              <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  activity.event_type === "file_uploaded"
                    ? "bg-blue-100 text-blue-800"
                    : activity.event_type === "ai_analysis_completed"
                    ? "bg-purple-100 text-purple-800"
                    : "bg-gray-100 text-gray-800"
                }`}
              >
                {activity.event_type === "file_uploaded"
                  ? "📤 Upload"
                  : activity.event_type === "ai_analysis_completed"
                  ? "🤖 AI Analysis"
                  : "⚡ Activity"}
              </span>
              <p className="font-medium text-slate-800 truncate">{activity.resource}</p>
            </div>
            <span className="text-sm text-slate-500 whitespace-nowrap ml-4">
              {new Date(activity.timestamp).toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ✅ MAIN DASHBOARD COMPONENT
const Dashboard = ({ BASE_URL }) => {
  const [stats, setStats] = useState({
    total_files: 0,
    total_size: 0,
    avg_file_size: 0,
    status_distribution: {},
    files_analyzed: 0,
  });
  const [uploadData, setUploadData] = useState([]);
  const [tagData, setTagData] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [timeRange, setTimeRange] = useState(30);
  const [loading, setLoading] = useState({
    stats: true,
    uploads: true,
    tags: true,
    activity: true,
  });
  const [errors, setErrors] = useState({
    stats: false,
    uploads: false,
    tags: false,
    activity: false,
  });

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  // ✅ Fetch analytics data for current user
  const fetchDashboardData = async () => {
    setLoading({ stats: true, uploads: true, tags: true, activity: true });
    setErrors({ stats: false, uploads: false, tags: false, activity: false });

    try {
      const endpoints = [
        { key: "stats", url: `${BASE_URL}/user/analytics/storage` },
        { key: "uploads", url: `${BASE_URL}/user/analytics/uploads?days=${timeRange}` },
        { key: "tags", url: `${BASE_URL}/user/analytics/tags?limit=10` },
        { key: "activity", url: `${BASE_URL}/user/analytics/activity?hours=24` },
      ];

      const results = await Promise.allSettled(
        endpoints.map((endpoint) => fetchWithAuth(endpoint.url))
      );

      results.forEach((result, index) => {
        const endpoint = endpoints[index];
        if (result.status === "fulfilled") {
          const data = result.value;
          switch (endpoint.key) {
            case "stats":
              setStats(data.storage || {});
              break;
            case "uploads":
              setUploadData(data.daily_uploads || []);
              break;
            case "tags":
              setTagData(data.top_tags || []);
              break;
            case "activity":
              setRecentActivity(data.recent_activity || []);
              break;
          }
        } else {
          console.error(`Error fetching ${endpoint.key}:`, result.reason);
          setErrors((prev) => ({ ...prev, [endpoint.key]: true }));
        }
      });
    } catch (err) {
      console.error("Error fetching dashboard data:", err);
      setErrors({ stats: true, uploads: true, tags: true, activity: true });
    } finally {
      setLoading({ stats: false, uploads: false, tags: false, activity: false });
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes === 0) return "0 B";
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round((bytes / Math.pow(1024, i)) * 100) / 100 + " " + sizes[i];
  };

  const COLORS = [
    "#0088FE",
    "#00C49F",
    "#FFBB28",
    "#FF8042",
    "#8884D8",
    "#82ca9d",
    "#ffc658",
    "#8dd1e1",
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-800">Dashboard Analytics</h2>
          <p className="text-slate-600 mt-1">Monitor your file storage and AI insights</p>
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
            disabled={Object.values(loading).some((l) => l)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* 🔹 Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border-l-4 border-blue-500">
          <h3 className="text-lg font-semibold text-slate-700">Total Files</h3>
          <p className="text-2xl font-bold text-blue-600">{stats.total_files || 0}</p>
          <div className="flex justify-between text-sm text-slate-500 mt-2">
            <span>MinIO: {stats.status_distribution?.minio || 0}</span>
            <span>S3: {stats.status_distribution?.["uploaded-to-s3"] || 0}</span>
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
          <p className="text-2xl font-bold text-purple-600">
            {stats.files_analyzed || 0}
          </p>
          <div className="text-sm text-slate-500 mt-2">
            {stats.total_files
              ? Math.round((stats.files_analyzed / stats.total_files) * 100)
              : 0}
            % of files
          </div>
        </div>

        <div className="bg-white p-4 rounded-lg shadow border-l-4 border-orange-500">
          <h3 className="text-lg font-semibold text-slate-700">Recent Activity</h3>
          <p className="text-2xl font-bold text-orange-600">
            {recentActivity.length}
          </p>
          <div className="text-sm text-slate-500 mt-2">Last 24 hours</div>
        </div>
      </div>

      {/* 🔹 Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard
          title="Uploads Over Time"
          data={uploadData}
          error={errors.uploads}
          loading={loading.uploads}
          onRetry={fetchDashboardData}
        />

        <TagChart
          data={tagData}
          error={errors.tags}
          loading={loading.tags}
          onRetry={fetchDashboardData}
          COLORS={COLORS}
        />
      </div>

      {/* 🔹 Recent Activity */}
      <ActivitySection
        data={recentActivity}
        error={errors.activity}
        loading={loading.activity}
        onRetry={fetchDashboardData}
      />
    </div>
  );
};

export default Dashboard;
  