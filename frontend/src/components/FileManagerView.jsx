import EnhancedSearch from "./EnhancedSearch";
import UploadSection from "./UploadSection";
import FilesList from "./FilesList";

export default function FileManagerView({
  onSearchResults,
  BASE_URL,
  files,
  file,
  setFile,
  uploadFile,
  loading,
  uploadProgress,
  dragActive,
  handleDrag,
  handleDrop,
  filteredFiles,
  setSelectedFile,
  analyzeFile,
  analyzingFiles,
  previewFile,
  deleteFile
}) {
  return (
    <>
      <EnhancedSearch 
        onSearchResults={onSearchResults}
        BASE_URL={BASE_URL}
        files={files}
      />

      <UploadSection
        file={file}
        setFile={setFile}
        uploadFile={uploadFile}
        loading={loading}
        uploadProgress={uploadProgress}
        dragActive={dragActive}
        handleDrag={handleDrag}
        handleDrop={handleDrop}
      />

      <FilesList
        files={files}
        filteredFiles={filteredFiles}
        loading={loading}
        setSelectedFile={setSelectedFile}
        analyzeFile={analyzeFile}
        analyzingFiles={analyzingFiles}
        previewFile={previewFile}
        deleteFile={deleteFile}
      />
    </>
  );
}