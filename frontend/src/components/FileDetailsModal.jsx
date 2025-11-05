import { 
  X, 
  Server, 
  Calendar, 
  Cloud,
  Clock, 
  Download, 
  ExternalLink, 
  Trash2, 
  RefreshCw, 
  RotateCw, 
  Brain, 
  Zap, 
  Sparkles, 
  Tag, 
  FileText, 
  AlertCircle, 
  CheckCircle 
} from "lucide-react";
import { getFileIcon, formatFileSize, formatDate, isFileTypeSupportedForAI } from "../utils/fileUtils";

export default function FileDetailsModal({
  selectedFile,
  setSelectedFile,
  analyzeFile,
  analyzingFiles,
  previewFile,
  downloadFile,
  deleteFile,
  refreshMinioUrls,
  refreshingUrls,
  fetchFiles,
  BASE_URL
}) {
  if (!selectedFile) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-40 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <ModalHeader selectedFile={selectedFile} setSelectedFile={setSelectedFile} />
        <ModalContent
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
        />
      </div>
    </div>
  );
}

const ModalHeader = ({ selectedFile, setSelectedFile }) => (
  <div className="sticky top-0 bg-white border-b border-slate-200 p-6 flex items-center justify-between">
    <div className="flex items-center gap-3">
      {getFileIcon(selectedFile.filename)}
      <div>
        <h2 className="text-2xl font-bold text-slate-800">File Details</h2>
        <p className="text-slate-600 text-sm mt-1 max-w-md truncate">{selectedFile.filename}</p>
      </div>
    </div>
    <button
      onClick={() => setSelectedFile(null)}
      className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
    >
      <X size={24} className="text-slate-600" />
    </button>
  </div>
);

const ModalContent = ({
  selectedFile,
  setSelectedFile,
  analyzeFile,
  analyzingFiles,
  previewFile,
  downloadFile,
  deleteFile,
  refreshMinioUrls,
  refreshingUrls,
  fetchFiles
}) => (
  <div className="p-6 space-y-6">
    <FileNameSection selectedFile={selectedFile} />
    <FileInfoGrid selectedFile={selectedFile} />

    {/* 🦠 Virus Warning */}
    {["infected", "infected-skip"].includes(selectedFile.status) && (
      <div className="bg-red-50 border border-red-300 text-red-700 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle size={20} className="mt-0.5 text-red-600" />
        <div>
          <p className="font-semibold text-red-800">Virus Detected</p>
          <p className="text-sm mt-1">
            This file contains a potential threat and <strong>S3 sync has been stopped</strong>.
          </p>
          {selectedFile.virus_name && (
            <p className="text-xs mt-1 text-red-600">
              ⚠️ Detected: <strong>{selectedFile.virus_name}</strong>
            </p>
          )}
        </div>
      </div>
    )}

    {/* ✅ Always show AI Analysis, even for infected files */}
    {isFileTypeSupportedForAI(selectedFile.filename) && (
      <AIAnalysisSection
        selectedFile={selectedFile}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
      />
    )}

    <MinIOActions
      selectedFile={selectedFile}
      previewFile={previewFile}
      downloadFile={downloadFile}
      refreshMinioUrls={refreshMinioUrls}
      refreshingUrls={refreshingUrls}
    />

    {/* ⛔ Disable S3 for infected files */}
    {["infected", "infected-skip"].includes(selectedFile.status) ? (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
        <Cloud className="mx-auto mb-2 text-red-400" size={32} />
        <p className="text-red-600 text-sm font-medium">
          File not synced to S3 due to detected infection.
        </p>
        <p className="text-xs text-red-500 mt-1">
          Please remove or replace this file if needed.
        </p>
      </div>
    ) : (
      <S3Actions
        selectedFile={selectedFile}
        previewFile={previewFile}
        downloadFile={downloadFile}
        fetchFiles={fetchFiles}
      />
    )}

    <ActionButtons
      selectedFile={selectedFile}
      deleteFile={deleteFile}
      setSelectedFile={setSelectedFile}
    />
  </div>
);

const FileNameSection = ({ selectedFile }) => (
  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4">
    <label className="text-sm font-medium text-slate-600 mb-2 block">File Name</label>
    <p className="text-lg font-semibold text-slate-800 break-all">{selectedFile.filename}</p>
  </div>
);

const FileInfoGrid = ({ selectedFile }) => (
  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
    <div className="bg-slate-50 rounded-lg p-4">
      <label className="text-sm font-medium text-slate-600 mb-2 flex items-center gap-2">
        <Server size={16} /> Status
      </label>

      {selectedFile.status === "infected" || selectedFile.status === "infected-skip" ? (
        <span className="inline-flex items-center gap-2 text-red-600 bg-red-50 px-3 py-1 rounded-full text-sm font-medium">
          <AlertCircle size={16} />
          Infected
        </span>
      ) : selectedFile.status === "uploaded-to-s3" ? (
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
      <label className="text-sm font-medium text-slate-600 mb-2 block">File Size</label>
      <p className="text-lg font-semibold text-slate-800">
        {formatFileSize(selectedFile.size)}
      </p>
    </div>

    {selectedFile.content_type && (
      <div className="bg-slate-50 rounded-lg p-4">
        <label className="text-sm font-medium text-slate-600 mb-2 block">File Type</label>
        <p className="text-lg font-semibold text-slate-800 capitalize">
          {selectedFile.content_type.split('/')[1] || selectedFile.content_type}
        </p>
      </div>
    )}

    {selectedFile.minio_uploaded_at && (
      <div className="bg-slate-50 rounded-lg p-4">
        <label className="text-sm font-medium text-slate-600 mb-2 flex items-center gap-2">
          <Calendar size={16} /> Uploaded to MinIO
        </label>
        <p className="text-sm font-semibold text-slate-800">
          {formatDate(selectedFile.minio_uploaded_at)}
        </p>
      </div>
    )}
  </div>
);

const AIAnalysisSection = ({ selectedFile, analyzeFile, analyzingFiles }) => {
  if (!isFileTypeSupportedForAI(selectedFile.filename)) return null;

  return (
    <div className="bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-4">
        <label className="text-lg font-semibold text-purple-800 flex items-center gap-2">
          <Brain size={20} /> AI Analysis
          {selectedFile.ai_analysis && (
            <span className="text-xs bg-purple-200 text-purple-800 px-2 py-1 rounded-full">
              Analyzed
            </span>
          )}
        </label>

        {(!selectedFile.ai_analysis || selectedFile.ai_analysis_status === "failed") && (
          <button
            onClick={() => analyzeFile(selectedFile.filename)}
            disabled={analyzingFiles[selectedFile.filename]}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50"
          >
            <Zap
              size={16}
              className={analyzingFiles[selectedFile.filename] ? "animate-spin" : ""}
            />
            {analyzingFiles[selectedFile.filename] ? "Analyzing..." : "Analyze with AI"}
          </button>
        )}
      </div>

      <AIAnalysisContent selectedFile={selectedFile} />
    </div>
  );
};

const AIAnalysisContent = ({ selectedFile }) => {
  if (selectedFile.ai_analysis) {
    return (
      <div className="space-y-4">
        {selectedFile.ai_analysis.summary && (
          <div>
            <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
              <FileText size={16} /> Summary
            </label>
            <p className="text-sm text-slate-700 bg-white p-3 rounded-lg border border-purple-100">
              {selectedFile.ai_analysis.summary}
            </p>
          </div>
        )}

        {selectedFile.ai_analysis.caption && (
          <div>
            <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
              <Sparkles size={16} /> Caption
            </label>
            <p className="text-sm text-slate-700 bg-white p-3 rounded-lg border border-purple-100">
              {selectedFile.ai_analysis.caption}
            </p>
          </div>
        )}

        {selectedFile.ai_analysis.keywords?.length > 0 && (
          <div>
            <label className="text-sm font-medium text-purple-700 mb-2 flex items-center gap-2">
              <Tag size={16} /> Keywords
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
    );
  }

  return (
    <div className="text-center py-4">
      <Brain className="mx-auto mb-2 text-purple-300" size={32} />
      <p className="text-purple-600">Click "Analyze with AI" to generate insights</p>
    </div>
  );
};

const MinIOActions = ({ selectedFile, previewFile, downloadFile, refreshMinioUrls, refreshingUrls }) => (
  <div className="bg-gradient-to-r from-teal-50 to-green-50 border border-teal-200 rounded-lg p-4 shadow-sm">
    <div className="flex items-center justify-between mb-3">
      <label className="text-sm font-medium text-teal-800 flex items-center gap-2">
        <Server size={16} /> MinIO Storage
        <span className="text-xs bg-teal-200 text-teal-800 px-2 py-1 rounded-full">Available</span>
      </label>
      <button
        onClick={() => refreshMinioUrls(selectedFile.filename)}
        disabled={refreshingUrls[selectedFile.filename]}
        className="flex items-center gap-1 px-2 py-1 bg-teal-100 hover:bg-teal-200 text-teal-700 rounded text-xs transition-colors disabled:opacity-50"
      >
        <RotateCw
          size={12}
          className={refreshingUrls[selectedFile.filename] ? "animate-spin" : ""}
        />
        Refresh URLs
      </button>
    </div>

    <div className="flex flex-col sm:flex-row gap-2">
      <button
        onClick={() => previewFile(selectedFile.filename, "minio")}
        disabled={!selectedFile.minio_preview_url}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-gradient-to-r from-teal-500 to-green-500 hover:from-teal-600 hover:to-green-600 text-white rounded-lg transition-all text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ExternalLink size={16} /> Preview File
      </button>

      <button
        onClick={() => downloadFile(selectedFile.filename, "minio")}
        disabled={!selectedFile.minio_download_url}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-teal-100 hover:bg-teal-200 text-teal-800 rounded-lg transition-colors text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <Download size={16} /> Download
      </button>
    </div>
  </div>
);

const S3Actions = ({ selectedFile, previewFile, downloadFile, fetchFiles }) => {
  if (selectedFile.status === "uploaded-to-s3") {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <label className="text-sm font-medium text-green-800 mb-3 flex items-center gap-2">
          <Cloud size={16} /> AWS S3 Storage
          <span className="text-xs bg-green-200 text-green-800 px-2 py-1 rounded-full">Synced</span>
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <button
            onClick={() => previewFile(selectedFile.filename, "s3")}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors text-sm font-medium"
          >
            <ExternalLink size={16} /> Preview File
          </button>
          <button
            onClick={() => downloadFile(selectedFile.filename, "s3")}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-green-100 hover:bg-green-200 text-green-800 rounded-lg transition-colors text-sm font-medium"
          >
            <Download size={16} /> Download
          </button>
        </div>
        {selectedFile.s3_synced_at && (
          <p className="text-xs text-green-600 mt-2">
            Synced at: {formatDate(selectedFile.s3_synced_at)}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 text-center">
      <Clock className="mx-auto mb-2 text-slate-400" size={32} />
      <p className="text-slate-600 text-sm">
        S3 sync in progress... S3 preview/download will be available automatically.
      </p>
      <button
        onClick={fetchFiles}
        className="mt-2 flex items-center justify-center gap-2 px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-700 rounded-lg transition-colors text-sm font-medium"
      >
        <RefreshCw size={16} /> Check Sync Status
      </button>
    </div>
  );
};

const ActionButtons = ({ selectedFile, deleteFile, setSelectedFile }) => (
  <div className="flex gap-3 pt-4 border-t border-slate-200">
    <button
      onClick={() => deleteFile(selectedFile.filename)}
      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors font-medium"
    >
      <Trash2 size={18} /> Delete File
    </button>
    <button
      onClick={() => setSelectedFile(null)}
      className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg transition-colors font-medium"
    >
      Close
    </button>
  </div>
);
