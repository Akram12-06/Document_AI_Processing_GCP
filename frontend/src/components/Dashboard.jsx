//src/components/Dashboard.jsx
import { StatsCard } from './UI';
import {
  GitGraphIcon,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock
} from 'lucide-react';


export function Dashboard({ stats, loading = false }) {
  const statsData = [
    {
      icon: GitGraphIcon,
      value: stats?.total_documents || 0,
      label: 'Total',
      color: 'accent'
    },
    {
      icon: CheckCircle2,
      value: stats?.successful || 0,
      label: 'Success',
      color: 'success'
    },
    {
      icon: XCircle,
      value: stats?.failed || 0,
      label: 'Failed',
      color: 'error'
    },
    {
      icon: AlertTriangle,
      value: stats?.pending_review || 0,
      label: 'Warnings',
      color: 'warning'
    },
    {
      icon: Clock,
      value: stats?.recent_uploads || 0,
      label: 'Recent',
      color: 'secondary'
    }
  ];

  if (loading) {
    return (
      <div className="dashboard-stats mb-md">
        <div className="flex gap-md">
          {[...Array(5)].map((_, index) => (
            <div key={index} className="compact-stats-card animate-pulse">
              <div className="stats-value bg-surface rounded mb-xs"></div>
              <div className="stats-label bg-surface rounded"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-stats mb-md">
      <div className="flex gap-md">
        {statsData.map((stat, index) => {
          const Icon=stat.icon;
          return(
          <div key={index} className="compact-stats-card">
            <div className={`stats-icon icon-${stat.color}`}>
            <Icon size={18} strokeWidth={1.5}/>
            </div>
            <div className="stats-value">{stat.value?.toLocaleString() || 0}</div>
            <div className="stats-label ">{stat.label}</div>
          </div>
          );
})}
      </div>
    </div>
  );
}