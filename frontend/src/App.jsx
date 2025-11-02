import { useState, useEffect } from "react";
import { Upload, RefreshCw, Trash2, File, Cloud, CheckCircle, Clock, Search, Filter, Download, AlertCircle, X, Calendar, Link2, Server, ExternalLink, RotateCw, Brain, Sparkles, Tag, FileText, Image as ImageIcon, Zap, BarChart3 } from "lucide-react";
import Dashboard from "./components/Dashboard";
import EnhancedSearch from "./components/EnhancedSearch";

export default function App() {
  const [file, setFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [filteredFiles, setFilteredFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [dragActive, setDragActive] = useState(false);
  const [notification, setNotification] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [refreshingUrls, setRefreshingUrls] = useState({});
  const [analyzingFiles, setAnalyzingFiles] = useState({});
  const [currentView, setCurrentView] = useState("files");

  const BASE_URL = "http://localhost:5000";

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    setFilteredFiles(files);
  }, [files]);

  const showNotification = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/files`);
      if (!res.ok) throw new Error("Failed to fetch files");
      const data = await res.json();
      setFiles(data);
      setFilteredFiles(data);
    } catch (err) {
      console.error("Error fetching files:", err);
      showNotification("Failed to fetch files", "error");
    }
    setLoading(false);
  };

  const handleSearchResults = (results) => {
    setFilteredFiles(results);
  };

  const uploadFile = async () => {
    if (!file) {
      showNotification("Please select a file first", "error");
      return;
    }
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setUploadProgress(30);
      
      const res = await fetch(`${BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Upload failed");
      
      const result = await res.json();
      setUploadProgress(100);
      
      setTimeout(() => {
        setFile(null);
        setUploadProgress(0);
        fetchFiles();
        showNotification(
          result.ai_analysis_queued 
            ? "File uploaded successfully! AI analysis in progress..." 
            : "File uploaded successfully!",
          "success"
        );
      }, 500);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadProgress(0);
      showNotification("Upload failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const analyzeFile = async (filename) => {
    setAnalyzingFiles(prev => ({ ...prev, [filename]: true }));
    try {
      const res = await fetch(`${BASE_URL}/analyze/${filename}`, {
        method: "POST",
      });
      
      if (!res.ok) throw new Error("Analysis failed");
      
      const result = await res.json();
      await fetchFiles();
      showNotification("AI analysis completed!", "success");
    } catch (err) {
      console.error("Analysis error:", err);
      showNotification("AI analysis failed", "error");
    } finally {
      setAnalyzingFiles(prev => ({ ...prev, [filename]: false }));
    }
  };

  const deleteFile = async (filename) => {
    if (!window.confirm(`Delete file "${filename}"?`)) return;
    
    try {
      const res = await fetch(`${BASE_URL}/delete/${filename}`, {
        method: "DELETE",
      });
      
      if (!res.ok) throw new Error("Delete failed");
      
      if (selectedFile?.filename === filename) {
        setSelectedFile(null);
      }
      fetchFiles();
      showNotification(`${filename} deleted successfully`, "success");
    } catch (err) {
      console.error("Delete error:", err);
      showNotification("Delete failed", "error");
    }
  };

  const downloadFile = async (filename, source) => {
    try {
      const fileData = files.find(f => f.filename === filename);
      
      if (source === 'minio' && fileData?.minio_download_url) {
        window.open(fileData.minio_download_url, '_blank');
        showNotification(`Downloading ${filename} from MinIO...`, "success");
      } else if (source === 's3' && fileData?.s3_download_url) {
        window.open(fileData.s3_download_url, '_blank');
        showNotification(`Downloading ${filename} from S3...`, "success");
      } else {
        const res = await fetch(`${BASE_URL}/download/${filename}?source=${source}`);
        if (!res.ok) throw new Error("Download failed");
        
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showNotification(`Downloading ${filename}...`, "success");
      }
    } catch (err) {
      console.error("Download error:", err);
      showNotification("Download failed", "error");
    }
  };

  const previewFile = async (filename, source) => {
    try {
      const fileData = files.find(f => f.filename === filename);
      
      if (source === 'minio' && fileData?.minio_preview_url) {
        window.open(fileData.minio_preview_url, '_blank');
      } else if (source === 's3' && fileData?.s3_preview_url) {
        window.open(fileData.s3_preview_url, '_blank');
      } else {
        const previewUrl = `${BASE_URL}/preview/${filename}?source=${source}`;
        window.open(previewUrl, '_blank');
      }
    } catch (err) {
      console.error("Preview error:", err);
      showNotification("Preview failed", "error");
    }
  };

  const refreshMinioUrls = async (filename) => {
    setRefreshingUrls(prev => ({ ...prev, [filename]: true }));
    try {
      const res = await fetch(`${BASE_URL}/refresh-urls/${filename}`, {
        method: "POST",
      });
      
      if (!res.ok) throw new Error("Refresh failed");
      
      await fetchFiles();
      showNotification("URLs refreshed successfully", "success");
    } catch (err) {
      console.error("Refresh error:", err);
      showNotification("Failed to refresh URLs", "error");
    } finally {
      setRefreshingUrls(prev => ({ ...prev, [filename]: false }));
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

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
    const extension = filename.split('.').pop()?.toLowerCase();
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
      zip: <File className={`${iconClass} text-orange-500`} size={20} />,
      rar: <File className={`${iconClass} text-orange-500`} size={20} />,
      mp4: <File className={`${iconClass} text-purple-600`} size={20} />,
      mp3: <File className={`${iconClass} text-pink-500`} size={20} />,
    };
    
    return iconMap[extension] || <File className={iconClass} size={20} />;
  };

  const isFileTypeSupportedForAI = (filename) => {
    const extension = filename.split('.').pop()?.toLowerCase();
    const supportedTypes = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'csv', 'json', 'xml'];
    return supportedTypes.includes(extension);
  };

  // Navigation Component
  const Navigation = () => (
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
          <button
            onClick={fetchFiles}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>
      
      {/* View Toggle */}
      <div className="flex border-b border-slate-200 mt-4">
        <button
          onClick={() => setCurrentView("files")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
            currentView === "files" 
              ? "border-blue-500 text-blue-600" 
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <File size={18} />
          File Manager
        </button>
        <button
          onClick={() => setCurrentView("dashboard")}
          className={`flex items-center gap-2 px-4 py-2 border-b-2 transition-colors ${
            currentView === "dashboard" 
              ? "border-blue-500 text-blue-600" 
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <BarChart3 size={18} />
          Analytics Dashboard
        </button>
      </div>
    </div>
  );

  // File Manager View
  const FileManagerView = () => (
    <>
      {/* Enhanced Search */}
      <EnhancedSearch 
        onSearchResults={handleSearchResults}
        BASE_URL={BASE_URL}
        files={files}
      />

      {/* Upload Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
        <h2 className="text-xl font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <Upload size={22} />
          Upload File
        </h2>
        
        <div
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-8 text-center transition-all ${
            dragActive 
              ? "border-blue-500 bg-blue-50" 
              : "border-slate-300 bg-slate-50"
          }`}
        >
          <input
            type="file"
            id="fileInput"
            onChange={(e) => setFile(e.target.files[0])}
            className="hidden"
          />
          <label htmlFor="fileInput" className="cursor-pointer">
            <File className="mx-auto mb-3 text-slate-400" size={48} />
            <p className="text-slate-600 mb-2">
              {file ? (
                <span className="font-semibold text-blue-600">{file.name}</span>
              ) : (
                <>
                  Drag & drop your file here or <span className="text-blue-600">click to browse</span>
                </>
              )}
            </p>
            <p className="text-sm text-slate-400">
              Supports AI analysis for PDFs, images, and text files
            </p>
          </label>
        </div>

        {file && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-center gap-3">
              {getFileIcon(file.name)}
              <div className="flex-1">
                <p className="font-medium text-slate-800">{file.name}</p>
                <p className="text-sm text-slate-600">
                  Size: {formatFileSize(file.size)}
                  {isFileTypeSupportedForAI(file.name) && (
                    <span className="ml-2 text-purple-600 flex items-center gap-1">
                      <Brain size={12} />
                      AI Analysis Available
                    </span>
                  )}
                </p>
              </div>
              <button
                onClick={() => setFile(null)}
                className="p-1 hover:bg-blue-100 rounded transition-colors"
              >
                <X size={16} className="text-slate-600" />
              </button>
            </div>
          </div>
        )}

        {uploadProgress > 0 && (
          <div className="mt-4">
            <div className="flex justify-between text-sm text-slate-600 mb-2">
              <span>Uploading...</span>
              <span>{uploadProgress}%</span>
            </div>
            <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-full transition-all duration-300"
                style={{ width: `${uploadProgress}%` }}
              ></div>
            </div>
          </div>
        )}

        <button
          onClick={uploadFile}
          disabled={!file || loading}
          className="mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        >
          <Upload size={20} />
          {loading ? 'Uploading...' : 'Upload File'}
        </button>
      </div>

      {/* Files List */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-800">
            Files ({filteredFiles.length})
          </h2>
          <div className="flex items-center gap-4 text-sm text-slate-600">
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                <span>MinIO Only</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>S3 Synced</span>
              </div>
            </div>
            <div className="flex items-center gap-1 text-purple-600">
              <Brain size={16} />
              <span>AI Analyzed</span>
            </div>
          </div>
        </div>
        
        {loading ? (
          <div className="p-12 text-center">
            <RefreshCw className="animate-spin mx-auto mb-3 text-blue-600" size={32} />
            <p className="text-slate-600">Loading files...</p>
          </div>
        ) : filteredFiles.length === 0 ? (
          <div className="p-12 text-center">
            <File className="mx-auto mb-3 text-slate-300" size={48} />
            <p className="text-slate-600">No files found.</p>
            <p className="text-sm text-slate-400 mt-1">
              {files.length === 0 ? "Upload your first file to get started" : "Try adjusting your search criteria"}
            </p>
          </div>
        ) : (
          <div className="divide-y divide-slate-200">
            {filteredFiles.map((f) => (
              <div
                key={f.filename}
                onClick={() => setSelectedFile(f)}
                className="p-4 hover:bg-slate-50 transition-colors cursor-pointer group"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      {getFileIcon(f.filename)}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">
                            {f.filename}
                          </h3>
                          {f.ai_analysis && (
                            <Brain size={14} className="text-purple-500 flex-shrink-0" title="AI Analyzed" />
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-3 text-sm">
                      {f.status === "uploaded-to-s3" ? (
                        <span className="flex items-center gap-1 text-green-600 bg-green-50 px-2 py-1 rounded-full text-xs font-medium">
                          <CheckCircle size={14} />
                          Synced to S3
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-orange-600 bg-orange-50 px-2 py-1 rounded-full text-xs font-medium">
                          <Clock size={14} />
                          MinIO Only
                        </span>
                      )}
                      {f.size && (
                        <span className="text-slate-500">{formatFileSize(f.size)}</span>
                      )}
                      {f.minio_uploaded_at && (
                        <span className="text-slate-400 text-xs">
                          Uploaded: {formatDate(f.minio_uploaded_at)}
                        </span>
                      )}
                    </div>

                    {/* AI Analysis Preview */}
                    {f.ai_analysis && (
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        {f.ai_analysis.keywords && f.ai_analysis.keywords.slice(0, 3).map((keyword, index) => (
                          <span 
                            key={index}
                            className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs"
                          >
                            {keyword}
                          </span>
                        ))}
                        {f.ai_analysis.keywords && f.ai_analysis.keywords.length > 3 && (
                          <span className="text-purple-600 text-xs">
                            +{f.ai_analysis.keywords.length - 3} more
                          </span>
                        )}
                      </div>
                    )}
                    
                    <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
                      <Link2 size={12} />
                      {f.ai_analysis 
                        ? "Click to view AI insights & file options" 
                        : "Click to view file details and options"
                      }
                    </p>
                  </div>
                  
                  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    {isFileTypeSupportedForAI(f.filename) && !f.ai_analysis && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          analyzeFile(f.filename);
                        }}
                        disabled={analyzingFiles[f.filename]}
                        className="flex items-center gap-1 px-3 py-2 bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg transition-colors flex-shrink-0 text-sm"
                        title="Analyze with AI"
                      >
                        <Zap size={14} className={analyzingFiles[f.filename] ? "animate-spin" : ""} />
                        {analyzingFiles[f.filename] ? "..." : "AI"}
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        previewFile(f.filename, 'minio');
                      }}
                      className="flex items-center gap-1 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors flex-shrink-0 text-sm"
                      title="Preview file from MinIO"
                    >
                      <ExternalLink size={14} />
                      Preview
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteFile(f.filename);
                      }}
                      className="flex items-center gap-1 px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors flex-shrink-0 text-sm"
                    >
                      <Trash2 size={14} />
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Notification Toast */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg ${
          notification.type === "success" 
            ? "bg-green-500 text-white" 
            : "bg-red-500 text-white"
        }`}>
          {notification.type === "success" ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
          {notification.message}
        </div>
      )}

      {/* File Details Modal */}
      {selectedFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {getFileIcon(selectedFile.filename)}
                <div>
                  <h2 className="text-2xl font-bold text-slate-800">
                    File Details
                  </h2>
                  <p className="text-slate-600 text-sm mt-1 max-w-md truncate">
                    {selectedFile.filename}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X size={24} className="text-slate-600" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* File Name */}
              <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
                <label className="text-sm font-medium text-slate-600 mb-2 block">
                  File Name
                </label>
                <p className="text-lg font-semibold text-slate-800 break-all">
                  {selectedFile.filename}
                </p>
              </div>

              {/* File Info Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <label className="text-sm font-medium text-slate-600 mb-2 flex items-center gap-2">
                    <Server size={16} />
                    Status
                  </label>
                  {selectedFile.status === "uploaded-to-s3" ? (
                    <span className="inline-flex items-center gap-2 text-green-600 bg-green-50 px-3 py-1 rounded-full text-sm font-medium">
                      <CheckCircle size={16} />
                      Synced to S3
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-orange-600 bg-orange-50 px-3 py-1 rounded-full text-sm font-medium">
                      <Clock size={16} />
                      MinIO Only
                    </span>
                  )}
                </div>

                <div className="bg-slate-50 rounded-lg p-4">
                  <label className="text-sm font-medium text-slate-600 mb-2 block">
                    File Size
                  </label>
                  <p className="text-lg font-semibold text-slate-800">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>

                {selectedFile.content_type && (
                  <div className="bg-slate-50 rounded-lg p-4">
                    <label className="text-sm font-medium text-slate-600 mb-2 block">
                      File Type
                    </label>
                    <p className="text-lg font-semibold text-slate-800 capitalize">
                      {selectedFile.content_type.split('/')[1] || selectedFile.content_type}
                    </p>
                  </div>
                )}

                {selectedFile.minio_uploaded_at && (
                  <div className="bg-slate-50 rounded-lg p-4">
                    <label className="text-sm font-medium text-slate-600 mb-2 flex items-center gap-2">
                      <Calendar size={16} />
                      Uploaded to MinIO
                    </label>
                    <p className="text-sm font-semibold text-slate-800">
                      {formatDate(selectedFile.minio_uploaded_at)}
                    </p>
                  </div>
                )}
              </div>

              {/* AI Analysis Section */}
              {isFileTypeSupportedForAI(selectedFile.filename) && (
                <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-4">
                    <label className="text-lg font-semibold text-purple-800 flex items-center gap-2">
                      <Brain size={20} />
                      AI Analysis
                      {selectedFile.ai_analysis && (
                        <span className="text-xs bg-purple-200 text-purple-800 px-2 py-1 rounded-full">
                          Analyzed
                        </span>
                      )}
                    </label>
                    
                    {(!selectedFile.ai_analysis || selectedFile.ai_analysis_status === 'failed') && (
                      <button
                        onClick={() => analyzeFile(selectedFile.filename)}
                        disabled={analyzingFiles[selectedFile.filename]}
                        className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50"
                      >
                        <Zap size={16} className={analyzingFiles[selectedFile.filename] ? "animate-spin" : ""} />
                        {analyzingFiles[selectedFile.filename] ? "Analyzing..." : "Analyze with AI"}
                      </button>
                    )}
                  </div>

                  {selectedFile.ai_analysis ? (
                    <div className="space-y-4">
                      {/* Summary */}
                      {selectedFile.ai_analysis.summary && (
                        <div>
                          <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
                            <FileText size={16} />
                            Summary
                          </label>
                          <p className="text-sm text-slate-700 bg-white p-3 rounded-lg border border-purple-100">
                            {selectedFile.ai_analysis.summary}
                          </p>
                        </div>
                      )}

                      {/* Caption */}
                      {selectedFile.ai_analysis.caption && (
                        <div>
                          <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
                            <Sparkles size={16} />
                            Caption
                          </label>
                          <p className="text-sm text-slate-700 bg-white p-3 rounded-lg border border-purple-100">
                            {selectedFile.ai_analysis.caption}
                          </p>
                        </div>
                      )}

                      {/* Keywords */}
                      {selectedFile.ai_analysis.keywords && selectedFile.ai_analysis.keywords.length > 0 && (
                        <div>
                          <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
                            <Tag size={16} />
                            Keywords
                          </label>
                          <div className="flex flex-wrap gap-2">
                            {selectedFile.ai_analysis.keywords.map((keyword, index) => (
                              <span 
                                key={index}
                                className="bg-purple-100 text-purple-800 px-3 py-1 rounded-full text-sm"
                              >
                                {keyword}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {selectedFile.ai_analysis.analysis_date && (
                        <p className="text-xs text-purple-600 text-right">
                          Analyzed: {formatDate(selectedFile.ai_analysis.analysis_date)}
                        </p>
                      )}
                    </div>
                  ) : selectedFile.ai_analysis_status === 'pending' ? (
                    <div className="text-center py-4">
                      <Brain className="animate-pulse mx-auto mb-2 text-purple-400" size={32} />
                      <p className="text-purple-600">AI analysis in progress...</p>
                    </div>
                  ) : selectedFile.ai_analysis_status === 'failed' ? (
                    <div className="text-center py-4">
                      <AlertCircle className="mx-auto mb-2 text-red-400" size={32} />
                      <p className="text-red-600">AI analysis failed. Try again.</p>
                    </div>
                  ) : (
                    <div className="text-center py-4">
                      <Brain className="mx-auto mb-2 text-purple-300" size={32} />
                      <p className="text-purple-600">Click "Analyze with AI" to generate insights</p>
                    </div>
                  )}
                </div>
              )}

              {/* MinIO Actions */}
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <label className="text-sm font-medium text-orange-800 flex items-center gap-2">
                    <Server size={16} />
                    MinIO Storage
                    <span className="text-xs bg-orange-200 text-orange-800 px-2 py-1 rounded-full">
                      Available 
                    </span>
                  </label>
                  <button
                    onClick={() => refreshMinioUrls(selectedFile.filename)}
                    disabled={refreshingUrls[selectedFile.filename]}
                    className="flex items-center gap-1 px-2 py-1 bg-orange-100 hover:bg-orange-200 text-orange-700 rounded text-xs transition-colors disabled:opacity-50"
                  >
                    <RotateCw size={12} className={refreshingUrls[selectedFile.filename] ? "animate-spin" : ""} />
                    Refresh URLs
                  </button>
                </div>
                <div className="flex flex-col sm:flex-row gap-2">
                  <button
                    onClick={() => previewFile(selectedFile.filename, 'minio')}
                    disabled={!selectedFile.minio_preview_url}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ExternalLink size={16} />
                    Preview File
                  </button>
                  <button
                    onClick={() => downloadFile(selectedFile.filename, 'minio')}
                    disabled={!selectedFile.minio_download_url}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-100 hover:bg-orange-200 text-orange-800 rounded-lg transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Download size={16} />
                    Download
                  </button>
                </div>
                {(!selectedFile.minio_preview_url || !selectedFile.minio_download_url) && (
                  <p className="text-xs text-orange-600 mt-2">
                    URLs expired. Click "Refresh URLs" to regenerate.
                  </p>
                )}
              </div>

              {/* S3 Actions */}
              {selectedFile.status === "uploaded-to-s3" ? (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <label className="text-sm font-medium text-green-800 mb-3 flex items-center gap-2">
                    <Cloud size={16} />
                    AWS S3 Storage
                    <span className="text-xs bg-green-200 text-green-800 px-2 py-1 rounded-full">
                      Synced
                    </span>
                  </label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <button
                      onClick={() => previewFile(selectedFile.filename, 's3')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      <ExternalLink size={16} />
                      Preview File
                    </button>
                    <button
                      onClick={() => downloadFile(selectedFile.filename, 's3')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-100 hover:bg-green-200 text-green-800 rounded-lg transition-colors text-sm font-medium"
                    >
                      <Download size={16} />
                      Download
                    </button>
                  </div>
                  {selectedFile.s3_synced_at && (
                    <p className="text-xs text-green-600 mt-2">
                      Synced at: {formatDate(selectedFile.s3_synced_at)}
                    </p>
                  )}
                </div>
              ) : (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                  <Clock className="mx-auto mb-2 text-slate-400" size={32} />
                  <p className="text-slate-600 text-sm">
                    S3 sync in progress... S3 preview/download will be available automatically.
                  </p>
                  <button
                    onClick={fetchFiles}
                    className="mt-2 flex items-center justify-center gap-2 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg transition-colors text-sm font-medium"
                  >
                    <RefreshCw size={16} />
                    Check Sync Status
                  </button>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t border-slate-200">
                <button
                  onClick={() => deleteFile(selectedFile.filename)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors font-medium"
                >
                  <Trash2 size={18} />
                  Delete File
                </button>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-medium"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="max-w-7xl mx-auto p-6">
        <Navigation />
        
        {currentView === "files" ? (
          <FileManagerView />
        ) : (
          <Dashboard BASE_URL={BASE_URL} />
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-slate-500 text-sm">
          <p>AI-Powered File Storage Manager • MinIO preview/download available immediately • S3 auto-syncs • AI analysis for insights</p>
        </div>
      </div>
    </div>
  );
}