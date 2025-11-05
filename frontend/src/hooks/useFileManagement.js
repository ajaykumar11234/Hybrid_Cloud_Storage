import { useState, useEffect } from "react";
import { fetchWithAuth } from "../utils/fetchWithAuth";

export function useFileManagement(showNotification) {
  const [file, setFile] = useState(null);
  const [files, setFiles] = useState([]);
  const [filteredFiles, setFilteredFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [refreshingUrls, setRefreshingUrls] = useState({});
  const [analyzingFiles, setAnalyzingFiles] = useState({});

  const BASE_URL = "http://localhost:5000";

  // ✅ Helper: check if URLs are older than 23 hours (safety margin)
  const isUrlExpired = (file) => {
    if (!file.lastRefreshedAt) return true;
    const lastRefresh = new Date(file.lastRefreshedAt).getTime();
    const now = Date.now();
    const hoursElapsed = (now - lastRefresh) / (1000 * 60 * 60);
    return hoursElapsed > 23;
  };

  // ✅ Fetch all files (user-specific)
  const fetchFiles = async () => {
    setLoading(true);
    try {
      const data = await fetchWithAuth(`${BASE_URL}/user/files`);
      const validData = Array.isArray(data) ? data : [];
      // Add timestamps if missing
      const withTimestamps = validData.map((f) => ({
        ...f,
        lastRefreshedAt: f.lastRefreshedAt || new Date().toISOString(),
      }));
      setFiles(withTimestamps);
      setFilteredFiles(withTimestamps);
    } catch (err) {
      console.error("Error fetching files:", err);
      showNotification(
        err.message.includes("Failed to fetch")
          ? "Cannot connect to server. Make sure the backend is running."
          : "Failed to fetch files",
        "error"
      );
    } finally {
      setLoading(false);
    }
  };

  // ✅ Upload file
  const uploadFile = async () => {
    if (!file) {
      showNotification("Please select a file first", "error");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setLoading(true);
      setUploadProgress(40);

      const res = await fetchWithAuth(`${BASE_URL}/user/upload`, {
        method: "POST",
        body: formData,
      });

      setUploadProgress(100);

      setTimeout(async () => {
        setFile(null);
        setUploadProgress(0);
        await fetchFiles();
        showNotification(
          res?.ai_analysis_queued
            ? "File uploaded successfully! AI analysis in progress..."
            : "File uploaded successfully!",
          "success"
        );
      }, 300);
    } catch (err) {
      console.error("Upload error:", err);
      setUploadProgress(0);
      showNotification("Upload failed", "error");
    } finally {
      setLoading(false);
    }
  };

  // ✅ Analyze file
  const analyzeFile = async (filename) => {
    if (!filename) return;
    setAnalyzingFiles((prev) => ({ ...prev, [filename]: true }));
    try {
      await fetchWithAuth(`${BASE_URL}/analyze/${filename}`, { method: "POST" });
      await fetchFiles();
      showNotification("AI analysis completed!", "success");
    } catch (err) {
      console.error("Analysis error:", err);
      showNotification("AI analysis failed", "error");
    } finally {
      setAnalyzingFiles((prev) => ({ ...prev, [filename]: false }));
    }
  };

  // ✅ Delete file
  const deleteFile = async (filename) => {
    if (!filename) return;
    if (!window.confirm(`Delete file "${filename}"?`)) return;

    try {
      await fetchWithAuth(`${BASE_URL}/user/delete/${filename}`, {
        method: "DELETE",
      });
      await fetchFiles();
      showNotification(`${filename} deleted successfully`, "success");
    } catch (err) {
      console.error("Delete error:", err);
      showNotification("Delete failed", "error");
    }
  };

  // ✅ Universal refresh for both MinIO and S3
  const refreshFileUrls = async (filename, source = "minio") => {
    setRefreshingUrls((prev) => ({ ...prev, [filename]: true }));
    try {
      const data = await fetchWithAuth(`${BASE_URL}/user/refresh-urls/${filename}`, {
        method: "POST",
      });
      if (data?.minio_preview_url || data?.s3_preview_url) {
        const refreshedAt = new Date().toISOString();
        setFiles((prev) =>
          prev.map((f) =>
            f.filename === filename
              ? {
                  ...f,
                  ...data,
                  lastRefreshedAt: refreshedAt,
                }
              : f
          )
        );
        showNotification(
          `${source.toUpperCase()} URLs refreshed successfully`,
          "success"
        );
        return data;
      }
    } catch (err) {
      console.error("Refresh error:", err);
      showNotification("Failed to refresh URLs", "error");
    } finally {
      setRefreshingUrls((prev) => ({ ...prev, [filename]: false }));
    }
    return null;
  };

  // ✅ Unified Preview Handler
  const previewFile = async (filename, source) => {
    try {
      const fileData = files.find((f) => f.filename === filename);
      if (!fileData) {
        showNotification("File not found", "error");
        return;
      }

      if (isUrlExpired(fileData)) {
        console.warn("🔁 URL expired, refreshing...");
        await refreshFileUrls(filename, source);
      }

      const previewUrl =
        source === "minio"
          ? fileData.minio_preview_url
          : source === "s3"
          ? fileData.s3_preview_url
          : "";

      if (previewUrl) {
        window.open(previewUrl, "_blank");
      } else {
        showNotification("Preview URL not available", "error");
      }
    } catch (err) {
      console.error("Preview error:", err);
      showNotification("Preview failed", "error");
    }
  };

  // ✅ Unified Download Handler
  const downloadFile = async (filename, source) => {
    try {
      const fileData = files.find((f) => f.filename === filename);
      if (!fileData) {
        showNotification("File not found", "error");
        return;
      }

      if (isUrlExpired(fileData)) {
        console.warn("🔁 URL expired, refreshing...");
        await refreshFileUrls(filename, source);
      }

      const downloadUrl =
        source === "minio"
          ? fileData.minio_download_url
          : source === "s3"
          ? fileData.s3_download_url
          : "";

      if (downloadUrl) {
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = filename;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        showNotification("Download URL not available", "error");
      }
    } catch (err) {
      console.error("Download error:", err);
      showNotification("Download failed", "error");
    }
  };

  // ✅ Search files
  const searchFiles = async (query) => {
    try {
      const res = await fetchWithAuth(`${BASE_URL}/user/search?q=${query}`);
      setFilteredFiles(res.results || []);
    } catch (err) {
      console.error("Search error:", err);
      showNotification("Search failed", "error");
    }
  };

  // ✅ Drag and Drop Handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (["dragenter", "dragover"].includes(e.type)) setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) setFile(droppedFile);
  };

  // ✅ Background Auto-Refresh (every 6 hours)
  useEffect(() => {
    if (!files.length) return;
    const interval = setInterval(async () => {
      console.log("⏰ Auto-refreshing MinIO/S3 URLs...");
      for (const file of files) {
        if (isUrlExpired(file)) {
          await refreshFileUrls(file.filename, "minio");
          if (file.status === "uploaded-to-s3") {
            await refreshFileUrls(file.filename, "s3");
          }
        }
      }
    }, 6 * 60 * 60 * 1000); // every 6 hours

    return () => clearInterval(interval);
  }, [files]);

  return {
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
    refreshFileUrls,
    searchFiles,
    handleDrag,
    handleDrop,
  };
}
