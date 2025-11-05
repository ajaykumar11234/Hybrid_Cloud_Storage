import { useState, useEffect } from "react";
import {
  Upload, RefreshCw, Trash2, File, Cloud, CheckCircle, Clock,
  X, Calendar, Link2, Server, ExternalLink, RotateCw, Brain,
  Sparkles, Tag, FileText, Image as ImageIcon, Zap, BarChart3,
  AlertCircle, Download
} from "lucide-react";

import { useAuth } from "./hooks/useAuth";
import Dashboard from "./components/Dashboard";
import EnhancedSearch from "./components/EnhancedSearch";
import Navigation from "./components/Navigation";
import FileManagerView from "./components/FileManagerView";
import FileDetailsModal from "./components/FileDetailsModal";
import NotificationToast from "./components/NotificationToast";
import Login from "./components/Login";
import Signup from "./components/Signup";
import { useFileManagement } from "./hooks/useFileManagement";
import { useNotification } from "./hooks/useNotification";

// ✅ Utility Functions
const formatFileSize = (bytes) => {
  if (!bytes) return "N/A";
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + " " + sizes[i];
};

const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleString();
};

const getFileIcon = (filename) => {
  const extension = filename.split(".").pop()?.toLowerCase();
  const iconClass = "text-slate-400 flex-shrink-0";

  const iconMap = {
    pdf: <File className={`${iconClass} text-red-500`} size={20} />,
    jpg: <ImageIcon className={`${iconClass} text-green-500`} size={20} />,
    jpeg: <ImageIcon className={`${iconClass} text-green-500`} size={20} />,
    png: <ImageIcon className={`${iconClass} text-blue-500`} size={20} />,
    gif: <ImageIcon className={`${iconClass} text-purple-500`} size={20} />,
    txt: <FileText className={`${iconClass} text-slate-500`} size={20} />,
    doc: <File className={`${iconClass} text-blue-600`} size={20} />,
    docx: <File className={`${iconClass} text-blue-600`} size={20} />,
    xls: <File className={`${iconClass} text-green-600`} size={20} />,
    xlsx: <File className={`${iconClass} text-green-600`} size={20} />,
  };

  return iconMap[extension] || <File className={iconClass} size={20} />;
};

const isFileTypeSupportedForAI = (filename) => {
  const extension = filename.split(".").pop()?.toLowerCase();
  const supportedTypes = ["pdf", "txt", "jpg", "jpeg", "png", "gif"];
  return supportedTypes.includes(extension);
};

// ✅ Main App Component
export default function App() {
  const [currentView, setCurrentView] = useState("files");
  const [selectedFile, setSelectedFile] = useState(null);
  const [authView, setAuthView] = useState("login");

  const { notification, showNotification } = useNotification();
  const { user, isAuthenticated, loading: authLoading, login, signup, logout } = useAuth();

  const {
    file,
    setFile,
    files,
    filteredFiles,
    setFilteredFiles,
    loading,
    uploadProgress,
    dragActive,
    refreshingUrls,
    analyzingFiles,
    fetchFiles,
    uploadFile,
    analyzeFile,
    deleteFile,
    downloadFile,
    previewFile,
    refreshMinioUrls,
    handleDrag,
    handleDrop,
  } = useFileManagement(showNotification);

  const BASE_URL = "http://localhost:5000";

  // Fetch files only after authentication
  useEffect(() => {
    if (isAuthenticated) {
      fetchFiles();
    }
  }, [isAuthenticated]);

  // Update filtered files when the file list changes
  useEffect(() => {
    setFilteredFiles(files);
  }, [files]);

  const handleSearchResults = (results) => {
    setFilteredFiles(results);
  };

  // ✅ Auth Handlers
  const handleLogin = async (credentials) => {
    try {
      await login(credentials);
      showNotification("Login successful!", "success");
    } catch (error) {
      showNotification("Login failed. Please check your credentials.", "error");
      throw error;
    }
  };

  const handleSignup = async (userData) => {
    try {
      await signup(userData);
      showNotification("Account created successfully!", "success");
    } catch (error) {
      showNotification("Signup failed. Please try again.", "error");
      throw error;
    }
  };

  const handleLogout = () => {
    logout();
    showNotification("Logged out successfully", "success");
  };

  // ✅ Show Auth Views
  if (!isAuthenticated) {
    if (authLoading) {
      return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center">
          <div className="text-center">
            <Brain className="animate-spin mx-auto mb-4 text-purple-600" size={48} />
            <p className="text-slate-600">Loading...</p>
          </div>
        </div>
      );
    }

    return authView === "login" ? (
      <Login onLogin={handleLogin} switchToSignup={() => setAuthView("signup")} />
    ) : (
      <Signup onSignup={handleSignup} switchToLogin={() => setAuthView("login")} />
    );
  }

  // ✅ Authenticated Main UI
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <NotificationToast notification={notification} />

      <FileDetailsModal
        selectedFile={selectedFile}
        setSelectedFile={setSelectedFile}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
        previewFile={previewFile}
        downloadFile={downloadFile}
        deleteFile={deleteFile}
        refreshMinioUrls={refreshMinioUrls}
        refreshingUrls={refreshingUrls}
        fetchFiles={fetchFiles}
        BASE_URL={BASE_URL}
      />

      <div className="max-w-7xl mx-auto p-6">
        <Navigation
          currentView={currentView}
          setCurrentView={setCurrentView}
          loading={loading}
          fetchFiles={fetchFiles}
          user={user}
          onLogout={handleLogout}
        />

        {currentView === "files" ? (
          <FileManagerView
            onSearchResults={handleSearchResults}
            BASE_URL={BASE_URL}
            files={files}
            file={file}
            setFile={setFile}
            uploadFile={uploadFile}
            loading={loading}
            uploadProgress={uploadProgress}
            dragActive={dragActive}
            handleDrag={handleDrag}
            handleDrop={handleDrop}
            filteredFiles={filteredFiles}
            setSelectedFile={setSelectedFile}
            analyzeFile={analyzeFile}
            analyzingFiles={analyzingFiles}
            previewFile={previewFile}
            deleteFile={deleteFile}
          />
        ) : (
          <Dashboard BASE_URL={BASE_URL} />
        )}

        <Footer />
      </div>
    </div>
  );
}

// ✅ Footer Component
const Footer = () => (
  <div className="mt-8 text-center text-slate-500 text-sm">
    <p>
      AI-Powered File Storage Manager • MinIO preview/download available immediately •
      S3 auto-syncs • AI analysis for insights
    </p>
  </div>
);
