//src/components/FIlterBar.jsx

import { useState } from 'react';
import { Input, Button } from './UI';
import { SearchIcon, FilterX } from 'lucide-react';
export function FilterBar({ 
  filters, 
  onFiltersChange, 
  onClear 
}) {
  const [localFilters, setLocalFilters] = useState(filters);

  const handleFilterChange = (key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const handleClear = () => {
    const clearedFilters = {
      file_name: '',
    };
    setLocalFilters(clearedFilters);
    onFiltersChange(clearedFilters);
    onClear?.();
  };

  const hasActiveFilters = localFilters.file_name;

  return (
    <div className="filter-bar bg-secondary border rounded-lg p-md mb-lg">
      <div className="flex items-center gap-md">
        <div className="flex-1">
          <SearchIcon size={14}/>
          <Input
            label="Search Files"
            placeholder="Search by filename..."
            value={localFilters.file_name || ''}
            onChange={(e) => handleFilterChange('file_name', e.target.value)}
          />
        </div>
        
        {hasActiveFilters && (
          <Button
            variant="secondary"
            onClick={handleClear}
          >
            <FilterX size={14}/>
            Clear
          </Button>
        )}
      </div>
    </div>
  );
}