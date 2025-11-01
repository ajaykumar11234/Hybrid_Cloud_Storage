// components/EnhancedSearch.jsx
import { useState, useEffect } from 'react';
import { Search, Filter, Tag, Calendar, FileText } from 'lucide-react';

const EnhancedSearch = ({ onSearchResults, BASE_URL }) => {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('text');
  const [tags, setTags] = useState([]);
  const [dateRange, setDateRange] = useState({ start: '', end: '' });

  useEffect(() => {
    // Debounced search
    const timeoutId = setTimeout(() => {
      performSearch();
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [query, searchType, tags, dateRange]);

  const performSearch = async () => {
    if (!query && searchType === 'text' && tags.length === 0) {
      onSearchResults([]);
      return;
    }

    try {
      let searchQuery = query;
      
      if (searchType === 'tags') {
        searchQuery = tags.join(',');
      } else if (searchType === 'date') {
        searchQuery = `${dateRange.start} to ${dateRange.end}`;
      }

      const response = await fetch(
        `${BASE_URL}/search?q=${encodeURIComponent(searchQuery)}&type=${searchType}`
      );
      const data = await response.json();
      onSearchResults(data.results || []);
    } catch (error) {
      console.error('Search error:', error);
      onSearchResults([]);
    }
  };

  return (
    <div className="bg-white p-4 rounded-lg shadow mb-6">
      <div className="flex flex-col space-y-4">
        {/* Search Type Tabs */}
        <div className="flex space-x-2 border-b">
          {[
            { id: 'text', label: 'Text Search', icon: Search },
            { id: 'tags', label: 'Tags', icon: Tag },
            { id: 'date', label: 'Date Range', icon: Calendar }
          ].map((type) => (
            <button
              key={type.id}
              onClick={() => setSearchType(type.id)}
              className={`flex items-center space-x-2 px-4 py-2 border-b-2 transition-colors ${
                searchType === type.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              <type.icon size={16} />
              <span>{type.label}</span>
            </button>
          ))}
        </div>

        {/* Search Inputs */}
        <div className="flex space-x-4">
          {searchType === 'text' && (
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
              <input
                type="text"
                placeholder="Search by filename, content, keywords..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {searchType === 'tags' && (
            <div className="flex-1">
              <input
                type="text"
                placeholder="Enter tags separated by commas..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && e.target.value.trim()) {
                    setTags([...tags, e.target.value.trim()]);
                    setQuery('');
                  }
                }}
                className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex flex-wrap gap-2 mt-2">
                {tags.map((tag, index) => (
                  <span
                    key={index}
                    className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-sm flex items-center"
                  >
                    {tag}
                    <button
                      onClick={() => setTags(tags.filter((_, i) => i !== index))}
                      className="ml-1 text-blue-600 hover:text-blue-800"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
            </div>
          )}

          {searchType === 'date' && (
            <div className="flex-1 flex space-x-4">
              <input
                type="date"
                value={dateRange.start}
                onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="date"
                value={dateRange.end}
                onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedSearch;