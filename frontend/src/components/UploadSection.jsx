import { useState } from 'react';
import { Upload, File, X, Brain, Zap } from 'lucide-react';
import { getFileIcon, formatFileSize, isFileTypeSupportedForAI } from '../utils/fileUtils.jsx';

export default function UploadSection({ 
  file, 
  setFile, 
  uploadFile, 
  loading, 
  uploadProgress, 
  dragActive, 
  setDragActive, 
  handleDrag, 
  handleDrop 
}) {
  return (
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
  );
}