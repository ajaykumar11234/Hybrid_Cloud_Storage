import { RefreshCw, File, CheckCircle, Clock, Brain, ExternalLink, Trash2, Zap, Link2 } from "lucide-react";
import { getFileIcon, formatFileSize, formatDate, isFileTypeSupportedForAI } from "../utils/fileUtils";

export default function FilesList({
  files,
  filteredFiles,
  loading,
  setSelectedFile,
  analyzeFile,
  analyzingFiles,
  previewFile,
  deleteFile
}) {
  if (loading) return <LoadingState />;
  if (filteredFiles.length === 0) return <EmptyState filesCount={files.length} />;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      <FilesHeader filteredFilesCount={filteredFiles.length} />
      <FilesGrid
        files={filteredFiles}
        setSelectedFile={setSelectedFile}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
        previewFile={previewFile}
        deleteFile={deleteFile}
      />
    </div>
  );
}

const FilesHeader = ({ filteredFilesCount }) => (
  <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
    <h2 className="text-lg font-semibold text-slate-800">
      Files ({filteredFilesCount})
    </h2>
    <FileStatusLegend />
  </div>
);

const FileStatusLegend = () => (
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
);

const FilesGrid = ({ files, setSelectedFile, analyzeFile, analyzingFiles, previewFile, deleteFile }) => (
  <div className="divide-y divide-slate-200">
    {files.map((file) => (
      <FileItem
        key={file.filename}
        file={file}
        setSelectedFile={setSelectedFile}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
        previewFile={previewFile}
        deleteFile={deleteFile}
      />
    ))}
  </div>
);

const FileItem = ({ file, setSelectedFile, analyzeFile, analyzingFiles, previewFile, deleteFile }) => (
  <div
    onClick={() => setSelectedFile(file)}
    className="p-4 hover:bg-slate-50 transition-colors cursor-pointer group"
  >
    <div className="flex items-start justify-between gap-4">
      <FileInfo file={file} />
      <FileActions
        file={file}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
        previewFile={previewFile}
        deleteFile={deleteFile}
      />
    </div>
  </div>
);

const FileInfo = ({ file }) => (
  <div className="flex-1 min-w-0">
    <div className="flex items-center gap-3 mb-2">
      {getFileIcon(file.filename)}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-slate-800 truncate group-hover:text-blue-600 transition-colors">
            {file.filename}
          </h3>
          {file.ai_analysis && (
            <Brain size={14} className="text-purple-500 flex-shrink-0" title="AI Analyzed" />
          )}
        </div>
      </div>
    </div>
    
    <FileMetadata file={file} />
    <AIPreview file={file} />
    <FileHint file={file} />
  </div>
);

const FileMetadata = ({ file }) => (
  <div className="flex flex-wrap items-center gap-3 text-sm">
    {file.status === "uploaded-to-s3" ? (
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
    {file.size && (
      <span className="text-slate-500">{formatFileSize(file.size)}</span>
    )}
    {file.minio_uploaded_at && (
      <span className="text-slate-400 text-xs">
        Uploaded: {formatDate(file.minio_uploaded_at)}
      </span>
    )}
  </div>
);

const AIPreview = ({ file }) => {
  if (!file.ai_analysis?.keywords) return null;
  
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2">
      {file.ai_analysis.keywords.slice(0, 3).map((keyword, index) => (
        <span key={index} className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-xs">
          {keyword}
        </span>
      ))}
      {file.ai_analysis.keywords.length > 3 && (
        <span className="text-purple-600 text-xs">
          +{file.ai_analysis.keywords.length - 3} more
        </span>
      )}
    </div>
  );
};

const FileHint = ({ file }) => (
  <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
    <Link2 size={12} />
    {file.ai_analysis 
      ? "Click to view AI insights & file options" 
      : "Click to view file details and options"
    }
  </p>
);

const FileActions = ({ file, analyzeFile, analyzingFiles, previewFile, deleteFile }) => (
  <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
    {isFileTypeSupportedForAI(file.filename) && !file.ai_analysis && (
      <AIAnalyzeButton
        file={file}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
      />
    )}
    <PreviewButton file={file} previewFile={previewFile} />
    <DeleteButton file={file} deleteFile={deleteFile} />
  </div>
);

const AIAnalyzeButton = ({ file, analyzeFile, analyzingFiles }) => (
  <button
    onClick={(e) => {
      e.stopPropagation();
      analyzeFile(file.filename);
    }}
    disabled={analyzingFiles[file.filename]}
    className="flex items-center gap-1 px-3 py-2 bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg transition-colors flex-shrink-0 text-sm"
    title="Analyze with AI"
  >
    <Zap size={14} className={analyzingFiles[file.filename] ? "animate-spin" : ""} />
    {analyzingFiles[file.filename] ? "..." : "AI"}
  </button>
);

const PreviewButton = ({ file, previewFile }) => (
  <button
    onClick={(e) => {
      e.stopPropagation();
      previewFile(file.filename, 'minio');
    }}
    className="flex items-center gap-1 px-3 py-2 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-lg transition-colors flex-shrink-0 text-sm"
    title="Preview file from MinIO"
  >
    <ExternalLink size={14} />
    Preview
  </button>
);

const DeleteButton = ({ file, deleteFile }) => (
  <button
    onClick={(e) => {
      e.stopPropagation();
      deleteFile(file.filename);
    }}
    className="flex items-center gap-1 px-3 py-2 bg-red-50 hover:bg-red-100 text-red-600 rounded-lg transition-colors flex-shrink-0 text-sm"
  >
    <Trash2 size={14} />
    Delete
  </button>
);

const LoadingState = () => (
  <div className="p-12 text-center">
    <RefreshCw className="animate-spin mx-auto mb-3 text-blue-600" size={32} />
    <p className="text-slate-600">Loading files...</p>
  </div>
);

const EmptyState = ({ filesCount }) => (
  <div className="p-12 text-center">
    <File className="mx-auto mb-3 text-slate-300" size={48} />
    <p className="text-slate-600">No files found.</p>
    <p className="text-sm text-slate-400 mt-1">
      {filesCount === 0 ? "Upload your first file to get started" : "Try adjusting your search criteria"}
    </p>
  </div>
);