// SPDX-License-Identifier: MIT
/**
 * Mock datasets for the Segel Analytics Dashboard.
 * Accurately models every data point from the visual reference.
 */

import {
  ActiveUsersData,
  ConversionRateData,
  EndedTaskData,
  JoiningUser,
  NavDockItem,
  TaskStatisticsData,
  TotalProfitData,
  TotalResponsesData,
  TotalRevenueData,
  TransactionItem,
  UserSourceItem,
} from './types';

export const mockNavDockItems: NavDockItem[] = [
  { id: 'dashboard', label: 'Dashboard', iconName: 'LayoutDashboard' },
  { id: 'profile', label: 'Profile', iconName: 'User' },
  { id: 'docs', label: 'Documents', iconName: 'FileText' },
  { id: 'calendar', label: 'Calendar', iconName: 'Calendar' },
  { id: 'analytics', label: 'Analytics', iconName: 'BarChart3' },
  { id: 'settings', label: 'Settings', iconName: 'Settings' },
  { id: 'help', label: 'Help & Support', iconName: 'HelpCircle' },
];

export const mockTaskStatistics: TaskStatisticsData = {
  count: 506,
  trendPercentage: 4.3,
  segments: {
    completed: 46,
    inProgress: 24,
    planned: 30,
  },
};

export const mockTotalResponses: TotalResponsesData = {
  rate: 98,
  label: 'Responses rate',
  totalTicks: 14,
};

export const mockTotalProfit: TotalProfitData = {
  value: '$63k',
  bars: [30, 48, 62, 40, 75, 55, 92, 70, 44, 58, 35],
};

export const mockConversionRate: ConversionRateData = {
  rate: 75,
  totalTicks: 28,
};

export const mockActiveUsers: ActiveUsersData = {
  count: 150,
  splits: {
    segmentA: 75,
    segmentB: 25,
    segmentC: 10,
  },
};

export const mockEndedTask: EndedTaskData = {
  count: 80,
  matrixCols: 12,
  matrixRows: 2,
  completedCount: 16,
};

export const mockTotalRevenue: TotalRevenueData = {
  headlineAmount: '$1240',
  subtitle: 'Last 15 days Orders',
  yAxisMarkers: ['100%', '80%', '60%', '40%', '20%'],
  points: [
    { day: '01', revenue: 45, orders: 8, curveY: 65 },
    { day: '04', revenue: 70, orders: 12, curveY: 50 },
    { day: '07', revenue: 110, orders: 18, curveY: 25 },
    { day: '9',  revenue: 95, orders: 14, curveY: 35 },
    { day: '11', revenue: 120, orders: 22, curveY: 48 }, // Featured pinpoint in reference!
    { day: '13', revenue: 65, orders: 10, curveY: 55 },
    { day: '15', revenue: 85, orders: 16, curveY: 42 },
    { day: '25', revenue: 105, orders: 19, curveY: 28 },
    { day: '30', revenue: 125, orders: 24, curveY: 20 },
  ],
};

export const mockUserSources: UserSourceItem[] = [
  {
    id: 'src-google',
    name: 'Google',
    domain: 'Google.com',
    count: 4653,
    percentageWidth: 62,
    gradient: 'linear-gradient(90deg, #7A9E6B 0%, #3B7A32 100%)',
    brand: 'google',
  },
  {
    id: 'src-x',
    name: 'X',
    domain: 'X.com',
    count: 379,
    percentageWidth: 78,
    gradient: 'linear-gradient(90deg, #C084FC 0%, #818CF8 100%)',
    brand: 'x',
  },
  {
    id: 'src-instagram',
    name: 'Instagram',
    domain: 'Instagram.com',
    count: 653,
    percentageWidth: 92,
    gradient: 'linear-gradient(90deg, #FCA5A5 0%, #FB7185 100%)',
    brand: 'instagram',
  },
];

export const mockJoiningUsers: JoiningUser[] = [
  {
    id: 'usr-1',
    name: 'Brooklyn Simmons',
    type: 'Full-time',
    location: 'Remote',
    status: 'Active',
    postedDate: 'Oct 30, 2025',
  },
  {
    id: 'usr-2',
    name: 'Jerome Bell',
    type: 'Full-time',
    location: 'New York',
    status: 'Pending',
    postedDate: 'Oct 28, 2025',
  },
  {
    id: 'usr-3',
    name: 'Jane Cooper',
    type: 'Contract',
    location: 'London',
    status: 'Active',
    postedDate: 'Oct 25, 2025',
  },
  {
    id: 'usr-4',
    name: 'Wade Warren',
    type: 'Full-time',
    location: 'Remote',
    status: 'Pending',
    postedDate: 'Oct 22, 2025',
  },
];

export const mockTransactions: TransactionItem[] = [
  {
    id: 'tx-1',
    symbol: 'NVDA',
    company: 'NVIDIA Corp.',
    amount: '+$1,980',
    date: 'Dec 28',
    isPositive: true,
  },
  {
    id: 'tx-2',
    symbol: 'AAPL',
    company: 'Apple Inc.',
    amount: '+$1,980',
    date: 'Dec 28',
    isPositive: true,
  },
  {
    id: 'tx-3',
    symbol: 'TSLA',
    company: 'Tesla Inc.',
    amount: '+$1,980',
    date: 'Dec 28',
    isPositive: true,
  },
  {
    id: 'tx-4',
    symbol: 'AMZN',
    company: 'Amazon.com Inc.',
    amount: '+$1,080',
    date: 'Dec 27',
    isPositive: true,
  },
];

