import { File, Image as ImageIcon, FileText } from "lucide-react";

export const formatFileSize = (bytes) => {
  if (!bytes) return "N/A";
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + " " + sizes[i];
};

export const formatDate = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  return date.toLocaleString();
};

export const getFileIcon = (filename) => {
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

export const isFileTypeSupportedForAI = (filename) => {
  const extension = filename.split('.').pop()?.toLowerCase();
  const supportedTypes = ['pdf', 'txt', 'jpg', 'jpeg', 'png', 'gif', 'csv', 'json', 'xml'];
  return supportedTypes.includes(extension);
};