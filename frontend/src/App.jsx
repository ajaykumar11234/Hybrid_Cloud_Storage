import { useState, useEffect } from "react";
import { Upload, RefreshCw, Trash2, File, Cloud, CheckCircle, Clock, Search, Filter, Download, AlertCircle, X, Calendar, Link2, Server, ExternalLink } from "lucide-react";

export default function App() {
  const [file, setFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [dragActive, setDragActive] = useState(false);
  const [notification, setNotification] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);

  const BASE_URL = "http://localhost:5000";

  useEffect(() => {
    fetchFiles();
  }, []);

  const showNotification = (message, type = "success") => {
    setNotification({ message, type });
    setTimeout(() => setNotification(null), 3000);
  };

  const fetchFiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${BASE_URL}/files`);
      const data = await res.json();
      setFiles(data);
    } catch (err) {
      console.error("Error fetching files:", err);
      showNotification("Failed to fetch files", "error");
    }
    setLoading(false);
  };

  const uploadFile = async () => {
    if (!file) {
      showNotification("Please select a file first", "error");
      return;
    }
    
    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploadProgress(50);
      const res = await fetch(`${BASE_URL}/upload`, {
        method: "POST",
        body: formData,
      });
      
      if (!res.ok) throw new Error("Upload failed");
      
      setUploadProgress(100);
      setTimeout(() => {
        setFile(null);
        setUploadProgress(0);
        fetchFiles();
        showNotification("File uploaded successfully!", "success");
      }, 500);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadProgress(0);
      showNotification("Upload failed", "error");
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
    } catch (err) {
      console.error("Download error:", err);
      showNotification("Download failed", "error");
    }
  };

  const previewFile = async (filename, source) => {
    try {
      const previewUrl = `${BASE_URL}/preview/${filename}?source=${source}`;
      window.open(previewUrl, '_blank');
    } catch (err) {
      console.error("Preview error:", err);
      showNotification("Preview failed", "error");
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
      jpg: <File className={`${iconClass} text-green-500`} size={20} />,
      jpeg: <File className={`${iconClass} text-green-500`} size={20} />,
      png: <File className={`${iconClass} text-blue-500`} size={20} />,
      gif: <File className={`${iconClass} text-purple-500`} size={20} />,
      txt: <File className={`${iconClass} text-slate-500`} size={20} />,
      doc: <File className={`${iconClass} text-blue-600`} size={20} />,
      docx: <File className={`${iconClass} text-blue-600`} size={20} />,
      xls: <File className={`${iconClass} text-green-600`} size={20} />,
      xlsx: <File className={`${iconClass} text-green-600`} size={20} />,
      zip: <File className={`${iconClass} text-orange-500`} size={20} />,
      rar: <File className={`${iconClass} text-orange-500`} size={20} />,
    };
    
    return iconMap[extension] || <File className={iconClass} size={20} />;
  };

  const filteredFiles = files.filter(f => {
    const matchesSearch = f.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === "all" || 
      (filterStatus === "s3" && f.status === "uploaded-to-s3") ||
      (filterStatus === "minio" && f.status !== "uploaded-to-s3");
    return matchesSearch && matchesFilter;
  });

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
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
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
                      Uploaded to S3
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2 text-orange-600 bg-orange-50 px-3 py-1 rounded-full text-sm font-medium">
                      <Clock size={16} />
                      Pending in MinIO
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

                {selectedFile.uploaded_at && (
                  <div className="bg-slate-50 rounded-lg p-4">
                    <label className="text-sm font-medium text-slate-600 mb-2 flex items-center gap-2">
                      <Calendar size={16} />
                      Uploaded At
                    </label>
                    <p className="text-lg font-semibold text-slate-800">
                      {formatDate(selectedFile.uploaded_at)}
                    </p>
                  </div>
                )}
              </div>

              {/* MinIO Actions */}
              {selectedFile.minio_preview_url && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <label className="text-sm font-medium text-orange-800 mb-3 flex items-center gap-2">
                    <Server size={16} />
                    MinIO Storage
                  </label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <button
                      onClick={() => window.open(selectedFile.minio_preview_url, '_blank')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      <ExternalLink size={16} />
                      Preview File
                    </button>
                    <button
                      onClick={() => previewFile(selectedFile.filename, 'minio')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      <Link2 size={16} />
                      Direct Preview
                    </button>
                    <button
                      onClick={() => downloadFile(selectedFile.filename, 'minio')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-orange-100 hover:bg-orange-200 text-orange-800 rounded-lg transition-colors text-sm font-medium"
                    >
                      <Download size={16} />
                      Download
                    </button>
                  </div>
                </div>
              )}

              {/* S3 Actions */}
              {selectedFile.s3_preview_url && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <label className="text-sm font-medium text-green-800 mb-3 flex items-center gap-2">
                    <Cloud size={16} />
                    AWS S3 Storage
                  </label>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <button
                      onClick={() => window.open(selectedFile.s3_preview_url, '_blank')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      <ExternalLink size={16} />
                      Preview File
                    </button>
                    <button
                      onClick={() => previewFile(selectedFile.filename, 's3')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors text-sm font-medium"
                    >
                      <Link2 size={16} />
                      Direct Preview
                    </button>
                    <button
                      onClick={() => downloadFile(selectedFile.filename, 's3')}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-100 hover:bg-green-200 text-green-800 rounded-lg transition-colors text-sm font-medium"
                    >
                      <Download size={16} />
                      Download
                    </button>
                  </div>
                </div>
              )}

              {/* No URLs Available */}
              {!selectedFile.minio_preview_url && !selectedFile.s3_preview_url && (
                <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
                  <Clock className="mx-auto mb-2 text-slate-400" size={32} />
                  <p className="text-slate-600 text-sm">
                    File is being processed. Preview URLs will be available once sync is complete.
                  </p>
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

      <div className="max-w-6xl mx-auto p-6">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-slate-800 flex items-center gap-3">
                <Cloud className="text-blue-600" size={32} />
                File Storage Manager
              </h1>
              <p className="text-slate-600 mt-1">MinIO & AWS S3 Integration with File Preview</p>
            </div>
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
              <p className="text-sm text-slate-400">Supports images, PDFs, text files, and more</p>
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
            disabled={!file || uploadProgress > 0}
            className="mt-4 w-full flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          >
            <Upload size={20} />
            {uploadProgress > 0 ? 'Uploading...' : 'Upload File'}
          </button>
        </div>

        {/* Search and Filter */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400" size={18} />
              <input
                type="text"
                placeholder="Search files by name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="flex items-center gap-2">
              <Filter size={18} className="text-slate-400" />
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
              >
                <option value="all">All Files</option>
                <option value="s3">AWS S3 Only</option>
                <option value="minio">MinIO Only</option>
              </select>
            </div>
          </div>
        </div>

        {/* Files List */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-slate-800">
              Files ({filteredFiles.length})
            </h2>
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                <span>MinIO Only</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>S3 Synced</span>
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
                {searchTerm || filterStatus !== "all" 
                  ? "Try adjusting your search or filter" 
                  : "Upload your first file to get started"
                }
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
                          <h3 className="font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">
                            {f.filename}
                          </h3>
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
                        {f.uploaded_at && (
                          <span className="text-slate-400 text-xs">
                            {formatDate(f.uploaded_at)}
                          </span>
                        )}
                      </div>
                      
                      <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
                        <Link2 size={12} />
                        Click to view details and preview
                      </p>
                    </div>
                    
                    <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (f.minio_preview_url) {
                            window.open(f.minio_preview_url, '_blank');
                          } else if (f.s3_preview_url) {
                            window.open(f.s3_preview_url, '_blank');
                          } else {
                            previewFile(f.filename, 'minio');
                          }
                        }}
                        className="flex items-center gap-1 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors flex-shrink-0 text-sm"
                        title="Preview file"
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

        {/* Footer */}
        <div className="mt-8 text-center text-slate-500 text-sm">
          <p>File Storage Manager • Supports preview for images, PDFs, text files, and more</p>
        </div>
      </div>
    </div>
  );
}