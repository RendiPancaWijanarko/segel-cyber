// SPDX-License-Identifier: MIT
/**
 * Type definitions for the Zassk Analytics Dashboard component.
 * Production-ready interface types for data models, state, and UI props.
 */

export interface NavDockItem {
  id: string;
  label: string;
  iconName: 'LayoutDashboard' | 'User' | 'FileText' | 'Calendar' | 'BarChart3' | 'Settings' | 'HelpCircle';
}

export interface TaskStatisticsData {
  count: number;
  trendPercentage: number;
  segments: {
    completed: number;   // percentage (e.g. 50%)
    inProgress: number;  // percentage (e.g. 25%)
    planned: number;     // percentage (e.g. 25%)
  };
}

export interface TotalResponsesData {
  rate: number;          // percentage (e.g. 98)
  label: string;         // e.g. "Responses rate"
  totalTicks: number;    // e.g. 14
}

export interface TotalProfitData {
  value: string;         // e.g. "$63k"
  bars: number[];        // array of relative heights 0-100
}

export interface ConversionRateData {
  rate: number;          // e.g. 75
  totalTicks: number;    // e.g. 28
}

export interface ActiveUsersData {
  count: number;         // e.g. 150
  splits: {
    segmentA: number;    // e.g. 75%
    segmentB: number;    // e.g. 25%
    segmentC: number;    // e.g. 10%
  };
}

export interface EndedTaskData {
  count: number;         // e.g. 80
  matrixCols: number;    // e.g. 12
  matrixRows: number;    // e.g. 2
  completedCount: number;// e.g. 16
}

export interface RevenuePoint {
  day: string;           // e.g. "01", "04", "07", "9", "11", "13", "15", "25", "30"
  revenue: number;       // e.g. 120
  orders: number;        // e.g. 15
  curveY: number;        // coordinate percentage 0-100
}

export interface TotalRevenueData {
  headlineAmount: string;// e.g. "$1240"
  subtitle: string;      // e.g. "Last 15 days Orders"
  yAxisMarkers: string[];// ["100%", "80%", "60%", "40%", "20%"]
  points: RevenuePoint[];
}

export interface UserSourceItem {
  id: string;
  name: string;
  domain: string;
  count: number;
  percentageWidth: number; // percentage of capsule fill
  gradient: string;
  brand: 'google' | 'x' | 'instagram';
}

export interface JoiningUser {
  id: string;
  name: string;
  type: string;          // e.g. "Full-time" | "Part-time" | "Contract"
  location: string;      // e.g. "Remote" | "New York" | "London"
  status: 'Active' | 'Pending' | 'Inactive';
  postedDate: string;    // e.g. "Oct 30, 2025"
  avatarUrl?: string;
}

export interface TransactionItem {
  id: string;
  symbol: string;        // e.g. "NVDA"
  company: string;       // e.g. "NVIDIA Corp."
  amount: string;        // e.g. "+$1,980"
  date: string;          // e.g. "Dec 28"
  isPositive: boolean;
  categoryIcon?: 'folder' | 'briefcase';
}

export interface ZasskDashboardProps {
  userName?: string;
  userGreeting?: string;
  onNavigate?: (tabId: string) => void;
  onSearch?: (query: string) => void;
  className?: string;
}

