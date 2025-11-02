import { useState, useCallback } from 'react';
import { Search, Tag, FileText, X, Loader2, Filter } from 'lucide-react';

const EnhancedSearch = ({ onSearchResults, BASE_URL, files }) => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('all'); // 'all', 'filename', 'keywords', 'content'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchCount, setSearchCount] = useState(0);
  const [hasSearched, setHasSearched] = useState(false);

  // Perform search when manually triggered
  const performSearch = useCallback(async () => {
    const currentQuery = query.trim();

    if (!currentQuery) {
      // If no query, return all files
      onSearchResults(files || []);
      setSearchCount(files?.length || 0);
      setError(null);
      setHasSearched(false);
      return;
    }

    setLoading(true);
    setError(null);
    setHasSearched(true);

    try {
      let results = [];
      let endpoint = '';
      
      switch (searchType) {
        case 'filename':
          endpoint = `${BASE_URL}/search/filename?q=${encodeURIComponent(currentQuery)}`;
          break;
        case 'keywords':
          endpoint = `${BASE_URL}/search/keywords?q=${encodeURIComponent(currentQuery)}`;
          break;
        case 'content':
          endpoint = `${BASE_URL}/search/content?q=${encodeURIComponent(currentQuery)}`;
          break;
        case 'all':
        default:
          endpoint = `${BASE_URL}/search?q=${encodeURIComponent(currentQuery)}`;
          break;
      }
      
      const response = await fetch(endpoint);
      const data = await response.json();
      results = data.results || [];
      
      onSearchResults(results);
      setSearchCount(results.length);
      
    } catch (error) {
      console.error('Search API error:', error);
      setError(error.message);
      // Fallback to client-side search
      performClientSideSearch();
    } finally {
      setLoading(false);
    }
  }, [query, searchType, files, BASE_URL, onSearchResults]);

  // Client-side search fallback
  const performClientSideSearch = useCallback(() => {
    if (!files || files.length === 0) {
      onSearchResults([]);
      setSearchCount(0);
      return;
    }

    const currentQuery = query.trim().toLowerCase();
    let results = files.filter(file => {
      const filename = file.filename?.toLowerCase() || '';
      const fileKeywords = file.ai_analysis?.keywords || [];
      const summary = file.ai_analysis?.summary?.toLowerCase() || '';
      const caption = file.ai_analysis?.caption?.toLowerCase() || '';

      switch (searchType) {
        case 'filename':
          return filename.includes(currentQuery);
        
        case 'keywords':
          return fileKeywords.some(keyword => 
            keyword.toLowerCase().includes(currentQuery)
          );
        
        case 'content':
          return summary.includes(currentQuery) || caption.includes(currentQuery);
        
        case 'all':
        default:
          // Search in filename
          if (filename.includes(currentQuery)) {
            return true;
          }
          // Search in keywords
          if (fileKeywords.some(keyword => keyword.toLowerCase().includes(currentQuery))) {
            return true;
          }
          // Search in summary and caption
          return summary.includes(currentQuery) || caption.includes(currentQuery);
      }
    });

    onSearchResults(results);
    setSearchCount(results.length);
  }, [files, query, searchType, onSearchResults]);

  const handleSearch = () => {
    performSearch();
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const clearSearch = () => {
    setQuery('');
    setError(null);
    setHasSearched(false);
    onSearchResults(files || []);
    setSearchCount(files?.length || 0);
  };

  const getPlaceholderText = () => {
    switch (searchType) {
      case 'filename':
        return 'Enter filename to search...';
      case 'keywords':
        return 'Enter keywords to search...';
      case 'content':
        return 'Enter text to search in summaries and captions...';
      case 'all':
      default:
        return 'Enter text to search in filenames, keywords, summaries, or captions...';
    }
  };

  const getSearchTypeLabel = () => {
    switch (searchType) {
      case 'filename':
        return 'filename';
      case 'keywords':
        return 'keywords';
      case 'content':
        return 'summary and caption';
      case 'all':
      default:
        return 'all fields';
    }
  };

  const getSearchTypeIcon = (type) => {
    switch (type) {
      case 'filename':
        return <FileText size={16} />;
      case 'keywords':
        return <Tag size={16} />;
      case 'content':
        return <FileText size={16} />;
      case 'all':
      default:
        return <Search size={16} />;
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-lg border border-gray-200 mb-6">
      <div className="flex flex-col space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Search className="text-blue-600" size={24} />
            <div>
              <h2 className="text-xl font-bold text-gray-800">Search Files</h2>
              <p className="text-sm text-gray-600">Search by filename, keywords, or content</p>
            </div>
          </div>
          
          {(query || hasSearched) && (
            <button
              onClick={clearSearch}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X size={16} />
              Clear
            </button>
          )}
        </div>

        {/* Search Input */}
        <div className="space-y-4">
          <div className="flex gap-4">
            {/* Search Type Selector */}
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[
                { id: 'all', label: 'All', icon: Search },
                { id: 'filename', label: 'Filename', icon: FileText },
                { id: 'keywords', label: 'Keywords', icon: Tag },
                { id: 'content', label: 'Content', icon: FileText }
              ].map((type) => (
                <button
                  key={type.id}
                  onClick={() => setSearchType(type.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-all ${
                    searchType === type.id
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  <type.icon size={16} />
                  <span>{type.label}</span>
                </button>
              ))}
            </div>

            {/* Search Filter Button */}
            <button
              onClick={() => {
                // Optional: Open advanced filter modal if needed
                console.log('Open filters');
              }}
              className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <Filter size={18} />
              <span>Filters</span>
            </button>
          </div>

          {/* Search Input with Button */}
          <div className="flex gap-3">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder={getPlaceholderText()}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
              />
            </div>
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="flex items-center gap-2 px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium min-w-[120px] justify-center"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <Search size={18} />
                  <span>Search</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Quick Search Tips */}
        {!hasSearched && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="text-sm font-medium text-blue-800 mb-2">How to Search</h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-2 text-sm text-blue-700">
              <div className="flex items-center gap-2">
                <Search size={14} />
                <span>All: Search everywhere</span>
              </div>
              <div className="flex items-center gap-2">
                <FileText size={14} />
                <span>Filename: Search file names</span>
              </div>
              <div className="flex items-center gap-2">
                <Tag size={14} />
                <span>Keywords: Search AI tags</span>
              </div>
              <div className="flex items-center gap-2">
                <FileText size={14} />
                <span>Content: Search summaries</span>
              </div>
            </div>
          </div>
        )}

        {/* Status Bar */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-200">
          <div className="flex items-center gap-4">
            {loading && (
              <div className="flex items-center gap-2 text-blue-600">
                <Loader2 className="animate-spin" size={18} />
                <span className="text-sm font-medium">Searching...</span>
              </div>
            )}
            
            {!loading && hasSearched && searchCount > 0 && (
              <div className="text-sm text-gray-600">
                Found <span className="font-semibold text-green-600">{searchCount}</span> files
                <span className="text-blue-600 ml-2">
                  • Searching in {getSearchTypeLabel()}
                </span>
              </div>
            )}
            
            {!loading && hasSearched && searchCount === 0 && query && (
              <div className="text-sm text-amber-600">
                No files found matching "{query}" in {getSearchTypeLabel()}
              </div>
            )}

            {!loading && !hasSearched && (
              <div className="text-sm text-gray-500">
                Ready to search - {files?.length || 0} files available
              </div>
            )}
          </div>

          {error && (
            <div className="text-sm text-red-600">
              {error} • Using fallback search
            </div>
          )}
        </div>

        {/* Search Results Info */}
        {hasSearched && !loading && searchCount > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-3">
            <div className="text-sm text-green-800">
              <strong>Search results:</strong> Found {searchCount} files matching "{query}" in {getSearchTypeLabel()}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default EnhancedSearch;