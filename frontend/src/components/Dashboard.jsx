// components/Dashboard.jsx
import { useState, useEffect } from 'react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, AreaChart, Area
} from 'recharts';

const Dashboard = ({ BASE_URL }) => {
  const [stats, setStats] = useState({});
  const [uploadData, setUploadData] = useState([]);
  const [tagData, setTagData] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [timeRange, setTimeRange] = useState(30);

  useEffect(() => {
    fetchDashboardData();
  }, [timeRange]);

  const fetchDashboardData = async () => {
    try {
      // Fetch all analytics data
      const [storageRes, uploadsRes, tagsRes, activityRes] = await Promise.all([
        fetch(`${BASE_URL}/analytics/storage`),
        fetch(`${BASE_URL}/analytics/uploads?days=${timeRange}`),
        fetch(`${BASE_URL}/analytics/tags?limit=10`),
        fetch(`${BASE_URL}/analytics/activity?hours=24`)
      ]);

      const storageData = await storageRes.json();
      const uploadsData = await uploadsRes.json();
      const tagsData = await tagsRes.json();
      const activityData = await activityRes.json();

      setStats(storageData.storage || {});
      setUploadData(uploadsData.daily_uploads || []);
      setTagData(tagsData.top_tags || []);
      setRecentActivity(activityData.recent_activity || []);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <div className="p-6 space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold">Total Files</h3>
          <p className="text-2xl font-bold text-blue-600">{stats.total_files || 0}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold">Total Storage</h3>
          <p className="text-2xl font-bold text-green-600">
            {formatFileSize(stats.total_size)}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold">Avg File Size</h3>
          <p className="text-2xl font-bold text-purple-600">
            {formatFileSize(stats.avg_file_size)}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold">Recent Activity</h3>
          <p className="text-2xl font-bold text-orange-600">{recentActivity.length}</p>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Uploads Over Time */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Uploads Over Time</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={uploadData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="_id" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="count" stroke="#8884d8" fill="#8884d8" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Top Tags */}
        <div className="bg-white p-4 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">Top Tags</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={tagData}
                dataKey="count"
                nameKey="_id"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label
              >
                {tagData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white p-4 rounded-lg shadow">
        <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
        <div className="space-y-2">
          {recentActivity.slice(0, 10).map((activity, index) => (
            <div key={index} className="flex items-center justify-between p-2 border-b">
              <div>
                <span className="font-medium">{activity.event_type}</span>
                <span className="text-gray-600 ml-2">{activity.resource}</span>
              </div>
              <span className="text-sm text-gray-500">
                {new Date(activity.timestamp).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;