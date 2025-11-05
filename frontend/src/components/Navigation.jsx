import { Brain, RefreshCw, File, BarChart3, LogOut, User } from 'lucide-react';

export default function Navigation({ currentView, setCurrentView, loading, fetchFiles, user, onLogout }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
            <Brain className="text-purple-600" size={32} />
            AI-Powered File Storage Manager
          </h1>
          <p className="text-slate-600 mt-1">
            MinIO & AWS S3 Integration • AI-Powered Analysis • Instant Preview & Download
          </p>
        </div>
        <div className="flex items-center gap-4">
          {user && (
            <div className="flex items-center gap-3 bg-slate-100 px-4 py-2 rounded-lg">
              <User size={18} className="text-slate-600" />
              <span className="text-slate-700 font-medium">{user.name}</span>
            </div>
          )}
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
          {user && (
            <button
              onClick={onLogout}
              className="flex items-center gap-2 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors"
            >
              <LogOut size={18} />
              Logout
            </button>
          )}
        </div>
      </div>
      
      <ViewToggle currentView={currentView} setCurrentView={setCurrentView} />
    </div>
  );
}

const ViewToggle = ({ currentView, setCurrentView }) => (
  <div className="flex border-b border-slate-200 mt-4">
    <ViewToggleButton
      view="files"
      currentView={currentView}
      setCurrentView={setCurrentView}
      icon={File}
      label="File Manager"
    />
    <ViewToggleButton
      view="dashboard"
      currentView={currentView}
      setCurrentView={setCurrentView}
      icon={BarChart3}
      label="Analytics Dashboard"
    />
  </div>
);

const ViewToggleButton = ({ view, currentView, setCurrentView, icon: Icon, label }) => (
  <button
    onClick={() => setCurrentView(view)}
    className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
      currentView === view 
        ? "border-blue-500 text-blue-600" 
        : "border-transparent text-slate-500 hover:text-slate-700"
    }`}
  >
    <Icon size={18} />
    {label}
  </button>
);