// SPDX-License-Identifier: MIT
/**
 * Zassk Precision Pixel-Exact Analytics Dashboard
 * Reverse-engineered production-grade React TypeScript component.
 * Features:
 * - Frameless canvas sitting directly on ambient sky wash.
 * - Split Total Profit and Active Users into two separate cards.
 * - Balanced padding and bottom-aligned "98% Responses rate" on Total Responses.
 * - Performance Trend card redesigned with interactive 60-column cellular heatmap.
 */

import React, { useState, useMemo, useRef, MouseEvent } from 'react';
import './Dashboard.css';
import {
  mockTaskStatistics,
  mockActiveUsers,
  mockJoiningUsers,
  mockTransactions,
} from './mockData';
import { ZasskDashboardProps } from './types';
import { PerformanceTrend } from '../components/performance-trend/performance-trend';
import { TooltipProvider } from '../components/ui/tooltip';
import { WebGPUShaderBackground } from './WebGPUShaderBackground';

// ── Tailored Minimalist Icon Component ──
interface IconProps {
  name: string;
  size?: number;
  strokeWidth?: number;
  className?: string;
  color?: string;
}

export const LucideIcon: React.FC<IconProps> = ({
  name,
  size = 18,
  strokeWidth = 2,
  className = '',
  color = 'currentColor',
}) => {
  const iconPaths: Record<string, React.ReactNode> = {
    Home: (
      <>
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" />
        <path d="M9 17h6" />
      </>
    ),
    User: (
      <>
        <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>
    ),
    FileText: (
      <>
        <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
        <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        <path d="M10 9H8" />
        <path d="M16 13H8" />
        <path d="M16 17H8" />
      </>
    ),
    Calendar: (
      <>
        <path d="M8 2v4" />
        <path d="M16 2v4" />
        <rect width="18" height="18" x="3" y="4" rx="2" />
        <path d="M3 10h18" />
      </>
    ),
    BarChart3: (
      <>
        <path d="M3 3v18h18" />
        <path d="M18 17V9" />
        <path d="M13 17V5" />
        <path d="M8 17v-3" />
      </>
    ),
    Settings: (
      <>
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    HelpCircle: (
      <>
        <circle cx="12" cy="12" r="10" />
        <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
        <path d="M12 17h.01" />
      </>
    ),
    Search: (
      <>
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </>
    ),
    ArrowUpRight: (
      <>
        <path d="M7 7h10v10" />
        <path d="M7 17 17 7" />
      </>
    ),
    FunnelFilter: (
      <>
        <line x1="4" y1="6" x2="20" y2="6" />
        <line x1="7" y1="12" x2="17" y2="12" />
        <line x1="10" y1="18" x2="14" y2="18" />
      </>
    ),
    Briefcase: (
      <>
        <rect width="20" height="14" x="2" y="7" rx="2" ry="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </>
    ),
    Info: (
      <>
        <circle cx="12" cy="12" r="10" />
        <path d="M12 16v-4" />
        <path d="M12 8h.01" />
      </>
    ),
    MoreHorizontal: (
      <>
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="19" cy="12" r="1.5" />
        <circle cx="5" cy="12" r="1.5" />
      </>
    ),
    Check: <path d="M20 6 9 17l-5-5" />,
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {iconPaths[name] || <circle cx="12" cy="12" r="10" />}
    </svg>
  );
};

export const Dashboard: React.FC<ZasskDashboardProps> = ({
  userName = 'Keren nix',
  userGreeting = 'Hello,',
  brandingText = 'PUSSIBERAD',
  logoUrl = '/static/images/pussiberad-logo.png',
  tniLogoUrl = '/static/images/logo-tni.svg',
  tniAdLogoUrl = '/static/images/logo-tni-ad.svg',
  onNavigate,
  onSearch,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<string>('dashboard');
  const [activeRevIndex, setActiveRevIndex] = useState<number>(3);
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(new Set());

  const chartSvgRef = useRef<SVGSVGElement | null>(null);

  const dockItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'Home' },
    { id: 'profile', label: 'Profile', icon: 'User' },
    { id: 'docs', label: 'Documents', icon: 'FileText' },
    { id: 'calendar', label: 'Calendar', icon: 'Calendar' },
    { id: 'analytics', label: 'Analytics', icon: 'BarChart3' },
    { id: 'settings', label: 'Settings', icon: 'Settings' },
    { id: 'help', label: 'Help', icon: 'HelpCircle' },
  ];

  const handleDockClick = (tabId: string) => {
    setActiveTab(tabId);
    if (onNavigate) onNavigate(tabId);
  };

  const toggleUserSelection = (userId: string) => {
    setSelectedUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId);
      else next.add(userId);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedUserIds.size === mockJoiningUsers.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(mockJoiningUsers.map((u) => u.id)));
    }
  };

  const isAllSelected = selectedUserIds.size === mockJoiningUsers.length && mockJoiningUsers.length > 0;

  // 14 Thick Radial Pill Ticks Arc Gauge (Left-to-Right Clockwise Fill)
  const radialTicks = useMemo(() => {
    const total = 14;
    const ticks = [];
    const cx = 120;
    const cy = 118;
    const rOuter = 92;
    const rInner = 68;

    // Ticks 1-5: Royal Blue, 6-8: Bright Sky Blue, 9-11: Pale Ice Blue, 12-14: Cool Gray
    const colorProgression = [
      '#1D4ED8', '#2563EB', '#2563EB', '#2563EB', '#2563EB',
      '#3B82F6', '#3B82F6', '#60A5FA',
      '#93C5FD', '#BFDBFE', '#DBEAFE',
      '#E2E8F0', '#E2E8F0', '#E2E8F0',
    ];

    for (let i = 0; i < total; i++) {
      const angleDeg = 180 - (i / (total - 1)) * 180;
      const rad = (angleDeg * Math.PI) / 180;

      // x = cx + R * cos(rad) ensures i=0 is on the LEFT (-1) and i=13 is on the RIGHT (+1)
      const x1 = cx + rOuter * Math.cos(rad);
      const y1 = cy - rOuter * Math.sin(rad);
      const x2 = cx + rInner * Math.cos(rad);
      const y2 = cy - rInner * Math.sin(rad);

      ticks.push({
        id: i,
        x1,
        y1,
        x2,
        y2,
        stroke: colorProgression[i],
      });
    }
    return ticks;
  }, []);

  // Full-Width Bezier Spline & Needle Waterfall Lines
  const { splinePoints, needleLines, activePointCoord, splinePathD } = useMemo(() => {
    const width = 530;
    const height = 145;

    const pointsData = [
      { day: '01', xPerc: 0, yHeight: 35, rev: 45 },
      { day: '04', xPerc: 15, yHeight: 48, rev: 72 },
      { day: '07', xPerc: 28, yHeight: 88, rev: 110 },
      { day: '11', xPerc: 42, yHeight: 54, rev: 120 },
      { day: '14', xPerc: 55, yHeight: 38, rev: 68 },
      { day: '20', xPerc: 70, yHeight: 45, rev: 86 },
      { day: '30', xPerc: 100, yHeight: 65, rev: 125 },
    ];

    const coords = pointsData.map((p) => {
      const x = (p.xPerc / 100) * (width - 32) + 16;
      const y = (1 - p.yHeight / 100) * (height - 24) + 12;
      return { ...p, x, y };
    });

    let pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const p0 = coords[i];
      const p1 = coords[i + 1];
      const cpX1 = p0.x + (p1.x - p0.x) / 2;
      const cpY1 = p0.y;
      const cpX2 = p0.x + (p1.x - p0.x) / 2;
      const cpY2 = p1.y;
      pathD += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${p1.x} ${p1.y}`;
    }

    const lines = [];
    const lineSpacing = 2.2;
    const totalLines = Math.floor((width - 32) / lineSpacing);

    for (let i = 0; i <= totalLines; i++) {
      const x = 16 + i * lineSpacing;
      const tGlobal = (i / totalLines) * (coords.length - 1);
      const segIndex = Math.min(Math.floor(tGlobal), coords.length - 2);
      const t = tGlobal - segIndex;

      const p0 = coords[segIndex];
      const p1 = coords[segIndex + 1];

      const y =
        (1 - t) ** 3 * p0.y +
        3 * (1 - t) ** 2 * t * p0.y +
        3 * (1 - t) * t ** 2 * p1.y +
        t ** 3 * p1.y;

      const isPeakOrScrubber = Math.abs(x - 210) < 80;
      const opacity = isPeakOrScrubber ? 0.45 : 0.22;

      lines.push({ id: i, x, yTop: y, yBottom: height, opacity });
    }

    const activeCoord = coords[activeRevIndex] || coords[3];

    return {
      splinePoints: coords,
      needleLines: lines,
      activePointCoord: activeCoord,
      splinePathD: pathD,
    };
  }, [activeRevIndex]);

  const handleChartMouseMove = (e: MouseEvent<SVGSVGElement>) => {
    if (!chartSvgRef.current) return;
    const rect = chartSvgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const width = rect.width;
    const fraction = Math.max(0, Math.min(1, mouseX / width));
    const nearestIdx = Math.round(fraction * 6);
    setActiveRevIndex(nearestIdx);
  };

  // Mini Vertical Histogram Heights in px for Total Profit (10 bars on lower shelf)
  const profitBars = [8, 14, 12, 18, 26, 22, 14, 10, 16, 10];

  // 4-Row x 12-Column Ended Task Dot Matrix (Matching Reference Streak)
  const endedTaskMatrix = useMemo(() => {
    const activeIndices: Record<number, number[]> = {
      0: [9, 10, 11],       // Row 0 (top): Active at 9, 10, 11
      1: [8, 9, 10],        // Row 1: Active at 8, 9, 10
      2: [6, 7],            // Row 2: Active at 6, 7
      3: [4, 5],            // Row 3 (bottom): Active at 4, 5
    };

    return Array.from({ length: 4 }, (_, r) =>
      Array.from({ length: 12 }, (_, c) => ({
        active: activeIndices[r]?.includes(c) ?? false,
      }))
    );
  }, []);

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden">
      {/* 1. WebGPU / TypeGPU Background Layer */}
      <WebGPUShaderBackground />

      {/* 2. Interactive Dashboard Layer */}
      <main className={`relative z-10 mx-auto max-w-[1440px] p-6 zassk-canvas ${className}`}>
        {/* ── 1. TOP NAVIGATION HEADER ── */}
        <header className="zassk-header">
          {/* Brand Pill */}
          <a href="/" className="zassk-brand-pill" title="PUSSIBERAD">
            <img src={logoUrl} alt="PUSSIBERAD Logo" className="zassk-brand-logo" />
            <span className="zassk-brand-text">{brandingText}</span>
            <span className="zassk-brand-tag">Zassk</span>
          </a>

          {/* Center Segmented Floating Dock */}
          <nav className="zassk-dock">
            {dockItems.map((item) => {
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleDockClick(item.id)}
                  className={`zassk-dock-btn ${isActive ? 'active' : 'inactive'}`}
                  aria-label={item.label}
                  title={item.label}
                >
                  <LucideIcon
                    name={item.icon}
                    size={item.id === 'dashboard' ? 15 : 17}
                    strokeWidth={2}
                    color={isActive ? '#FFFFFF' : '#4B5565'}
                  />
                  {isActive && <span>{item.label}</span>}
                </button>
              );
            })}
          </nav>

          {/* Right Header Insignias: TNI & TNI AD Logos (Static Visual Elements) */}
          <div className="zassk-header-utilities">
            <div
              className="zassk-header-logo-badge"
              title="Tentara Nasional Indonesia (TNI)"
              role="img"
              aria-label="Logo TNI"
            >
              <img
                src={tniLogoUrl}
                alt="Logo TNI"
                className="zassk-header-insignia"
              />
            </div>
            <div
              className="zassk-header-logo-badge"
              title="TNI Angkatan Darat (TNI AD)"
              role="img"
              aria-label="Logo TNI AD"
            >
              <img
                src={tniAdLogoUrl}
                alt="Logo TNI AD"
                className="zassk-header-insignia"
              />
            </div>
          </div>
        </header>

        {/* ── 2. TOP ROW METRICS ── */}
        <div className="zassk-top-row">
          {/* Col 1: Greeting & Task Statistics */}
          <div className="zassk-greeting-box">
            <div>
              <div className="zassk-hello-lead">{userGreeting}</div>
              <h1 className="zassk-hello-name">{userName}</h1>
              <div className="zassk-welcome-sub">Welcome Back</div>
            </div>

            <div className="zassk-task-stat-widget">
              <div className="zassk-stat-header">
                <span className="zassk-stat-label">Task Statistics</span>
                <div className="zassk-stat-value-group">
                  <span className="zassk-stat-count">{mockTaskStatistics.count}</span>
                  <span className="zassk-trend-badge">↗ {mockTaskStatistics.trendPercentage}%</span>
                </div>
              </div>
              <div className="zassk-progress-capsule">
                <div className="zassk-seg-1" title="Completed Tasks" />
                <div className="zassk-seg-2" title="In Progress" />
                <div className="zassk-seg-3" title="Planned Tasks" />
              </div>
            </div>
          </div>

          {/* Col 2: Total Responses Card with Folder Tab Notch Silhouette & Left-to-Right Radial Arc */}
          <div className="zassk-card-tabbed-notch">
            <svg className="zassk-card-svg-bg" viewBox="0 0 300 220" preserveAspectRatio="none">
              <path
                d="M 0,22 C 0,9.8 9.8,0 22,0 L 190,0 C 200,0 208,4 214,8 C 220,12 225,14 234,14 L 278,14 C 290.2,14 300,23.8 300,36 L 300,198 C 300,210.2 290.2,220 278,220 L 22,220 C 9.8,220 0,210.2 0,198 Z"
                fill="#FFFFFF"
              />
            </svg>

            <div className="zassk-tabbed-header">
              <span className="zassk-card-title">Total Responses</span>
            </div>

            <div className="zassk-gauge-wrapper-centered">
              <svg className="zassk-radial-gauge-svg" viewBox="0 0 240 135">
                {radialTicks.map((tick) => (
                  <line
                    key={tick.id}
                    x1={tick.x1.toFixed(1)}
                    y1={tick.y1.toFixed(1)}
                    x2={tick.x2.toFixed(1)}
                    y2={tick.y2.toFixed(1)}
                    stroke={tick.stroke}
                    strokeWidth={7.5}
                    strokeLinecap="round"
                  />
                ))}
              </svg>
              {/* Bottom edge aligns flush with bottom edge of arc vector graphic */}
              <div className="zassk-gauge-center-content">
                <div className="zassk-gauge-center-val">98%</div>
                <div className="zassk-gauge-center-label">Responses rate</div>
              </div>
            </div>
          </div>

          {/* Col 3: Interlocking "Total Profit" & "Active Users" Cards */}
          <div className="zassk-interlock-col">
            {/* Top Card: Total Profit */}
            <div className="zassk-interlock-card zassk-tp-card">
              <svg className="zassk-card-svg-bg" viewBox="0 0 300 110" preserveAspectRatio="none">
                <path
                  d="M 0,22 C 0,9.8 9.8,0 22,0 L 278,0 C 290.2,0 300,9.8 300,22 L 300,96 C 300,103.7 293.7,110 286,110 L 250,110 C 240,110 234,105 228,100 C 222,96 216,96 208,96 L 14,96 C 6.3,96 0,89.7 0,82 Z"
                  fill="#FFFFFF"
                />
              </svg>
              <div className="zassk-tp-inner">
                <div className="zassk-tp-header">
                  <span className="zassk-card-title">Total Profit</span>
                  <button className="zassk-tp-arrow-btn" aria-label="View Profit">
                    <LucideIcon name="ArrowUpRight" size={15} strokeWidth={2.2} color="#475569" />
                  </button>
                </div>
                <div className="zassk-tp-body">
                  <div className="zassk-metric-big">$63k</div>
                  {/* 10 vertical rounded mini histogram bars on lower shelf */}
                  <div className="zassk-mini-barchart">
                    {profitBars.map((heightPx, i) => (
                      <div
                        key={i}
                        className="zassk-mini-bar"
                        style={{
                          height: `${heightPx}px`,
                          backgroundColor: i >= 3 && i <= 5 ? '#2563EB' : '#93C5FD',
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Card: Active Users */}
            <div className="zassk-interlock-card zassk-au-card">
              <svg className="zassk-card-svg-bg" viewBox="0 0 300 118" preserveAspectRatio="none">
                <path
                  d="M 0,14 C 0,6.3 6.3,0 14,0 L 208,0 C 216,0 222,0 228,4 C 234,9 240,14 250,14 L 286,14 C 293.7,14 300,20.3 300,28 L 300,96 C 300,108.2 290.2,118 278,118 L 22,118 C 9.8,118 0,108.2 0,96 Z"
                  fill="#FFFFFF"
                />
              </svg>
              <div className="zassk-au-inner">
                <div className="zassk-au-header">
                  <span className="zassk-card-title">Active Users</span>
                  <div className="zassk-au-split-labels">
                    <span>75%</span>
                    <span className="zassk-au-sep">|</span>
                    <span>25%</span>
                    <span className="zassk-au-sep">|</span>
                    <span>10%</span>
                  </div>
                </div>
                <div className="zassk-au-body">
                  <div className="zassk-metric-big">150</div>
                  <div className="zassk-split-bar">
                    <div className="zassk-split-seg-1" title="Primary users (75%)" />
                    <div className="zassk-split-seg-2" title="Secondary users (25%)" />
                    <div className="zassk-split-seg-3" title="Guest users (10%)" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Col 4: Interlocking "Conversion Rate" & "Ended Task" Cards */}
          <div className="zassk-interlock-col">
            {/* Top Card: Conversion Rate */}
            <div className="zassk-interlock-card zassk-cr-card">
              <svg className="zassk-card-svg-bg" viewBox="0 0 300 110" preserveAspectRatio="none">
                <path
                  d="M 0,22 C 0,9.8 9.8,0 22,0 L 278,0 C 290.2,0 300,9.8 300,22 L 300,82 C 300,89.7 293.7,96 286,96 L 92,96 C 84,96 78,96 72,100 C 66,105 60,110 50,110 L 14,110 C 6.3,110 0,103.7 0,96 Z"
                  fill="#FFFFFF"
                />
              </svg>
              <div className="zassk-cr-inner">
                <div className="zassk-cr-header">
                  <span className="zassk-card-title">Conversion Rate</span>
                  <button className="zassk-tp-arrow-btn" aria-label="View Conversion">
                    <LucideIcon name="ArrowUpRight" size={15} strokeWidth={2.2} color="#475569" />
                  </button>
                </div>
                <div className="zassk-metric-big" style={{ margin: '2px 0 4px 0' }}>
                  75%
                </div>
                {/* 32 micro vertical tick bars */}
                <div className="zassk-dense-ticks-32">
                  {Array.from({ length: 32 }).map((_, i) => (
                    <div
                      key={i}
                      className={`zassk-tick-bar-32 ${i < 24 ? 'filled' : 'unfilled'}`}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom Card: Ended Task (Restored Reference Design) */}
            <div className="zassk-interlock-card zassk-et-card">
              <svg className="zassk-card-svg-bg" viewBox="0 0 300 118" preserveAspectRatio="none">
                <path
                  d="M 0,28 C 0,20.3 6.3,14 14,14 L 50,14 C 60,14 66,9 72,4 C 78,0 84,0 92,0 L 286,0 C 293.7,0 300,6.3 300,14 L 300,96 C 300,108.2 290.2,118 278,118 L 22,118 C 9.8,118 0,108.2 0,96 Z"
                  fill="#FFFFFF"
                />
              </svg>
              <div className="zassk-et-inner">
                <div className="zassk-et-title">Ended Task</div>
                <div className="zassk-et-body">
                  <div className="zassk-et-val">80</div>
                  {/* 4-Row x 12-Column Dot Matrix Grid */}
                  <div className="zassk-et-matrix" role="img" aria-label="Ended Task Matrix">
                    {endedTaskMatrix.map((row, rIdx) => (
                      <div key={rIdx} className="zassk-et-matrix-row">
                        {row.map((dot, cIdx) => (
                          <div key={cIdx} className="zassk-et-cell">
                            <div
                              className={`zassk-et-dot-pip ${dot.active ? 'active' : 'inactive'}`}
                            />
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 3. MIDDLE ROW: WATERFALL NEEDLE CHART & USER SOURCES ── */}
        <div className="zassk-mid-row">
          {/* Full-Width Total Revenue Card */}
          <div className="zassk-card zassk-revenue-card">
            <div className="zassk-revenue-top-bar">
              <span className="zassk-card-title">Total Revenue</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Revenue">
                <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} color="#4B5565" />
              </button>
            </div>

            <div className="zassk-revenue-layout">
              {/* Left Metric Column */}
              <div className="zassk-revenue-side-metric">
                <div>
                  <div className="zassk-revenue-amount">$1240</div>
                  <div className="zassk-revenue-sub">Last 15 days Orders</div>
                </div>
                <div className="zassk-y-markers">
                  <span>100%</span>
                  <span>80%</span>
                  <span>60%</span>
                  <span>40%</span>
                  <span>20%</span>
                </div>
              </div>

              {/* Spectral Waterfall Needle Chart Container */}
              <div className="zassk-waveform-container">
                <svg
                  ref={chartSvgRef}
                  className="zassk-waveform-svg"
                  viewBox="0 0 530 145"
                  onMouseMove={handleChartMouseMove}
                >
                  {needleLines.map((line) => (
                    <line
                      key={line.id}
                      x1={line.x}
                      y1={line.yTop}
                      x2={line.x}
                      y2={line.yBottom}
                      stroke="#3B82F6"
                      strokeWidth={1}
                      strokeOpacity={line.opacity}
                    />
                  ))}

                  <path
                    d={splinePathD}
                    fill="none"
                    stroke="#3B82F6"
                    strokeWidth={2.5}
                    strokeLinecap="round"
                  />

                  {activePointCoord && (
                    <circle
                      cx={activePointCoord.x}
                      cy={activePointCoord.y}
                      r={5}
                      fill="#FFFFFF"
                      stroke="#2563EB"
                      strokeWidth={3}
                      style={{ cursor: 'pointer' }}
                    />
                  )}
                </svg>

                {activePointCoord && (
                  <div
                    className="zassk-floating-tooltip"
                    style={{
                      left: `${(activePointCoord.x / 530) * 100}%`,
                      top: `${(activePointCoord.y / 145) * 100}%`,
                    }}
                  >
                    Revenue ${activePointCoord.rev}
                  </div>
                )}
              </div>
            </div>

            <div className="zassk-timeline-slider-track">
              <div
                className="zassk-timeline-slider-thumb"
                style={{ left: '26%', width: '28%' }}
              />
            </div>

            <div className="zassk-x-axis-full">
              {['01', '04', '07', '9', '11', '13', '15', '25', '30'].map((d, idx) => (
                <span
                  key={idx}
                  style={{
                    color: d === '11' ? '#0F172A' : '#94A3B8',
                    fontWeight: d === '11' ? 800 : 600,
                  }}
                >
                  {d}
                </span>
              ))}
            </div>
          </div>

          {/* User Source Card with Multi-Layered Progress Tracks */}
          <div className="zassk-card zassk-source-card">
            <div>
              <div className="zassk-revenue-top-bar">
                <div>
                  <span className="zassk-card-title">User Source</span>
                  <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 500, marginTop: '2px' }}>
                    Total 12k+
                  </div>
                </div>
                <button className="zassk-action-pill-btn" aria-label="Filter Sources">
                  <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} color="#4B5565" />
                </button>
              </div>

              <div className="zassk-source-list">
                {/* 1. Google (68%) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.05h3.9c2.28-2.1 3.64-5.2 3.64-9.14z" />
                      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.9-3.05c-1.08.72-2.45 1.16-4.03 1.16-3.1 0-5.74-2.1-6.68-4.91H1.21v3.13C3.25 21.43 7.31 24 12 24z" />
                      <path fill="#FBBC05" d="M5.32 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.58H1.21C.44 8.11 0 9.99 0 12s.44 3.89 1.21 5.42l4.11-3.13z" />
                      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.57 1.21 6.58l4.11 3.13c.94-2.81 3.58-4.96 6.68-4.96z" />
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-frosted-pod">
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                    </div>
                    <div
                      className="zassk-brand-capsule"
                      style={{ width: '68%', background: 'linear-gradient(90deg, #3B82F6 0%, #60A5FA 100%)' }}
                    >
                      <span>Google.com</span>
                      <div className="zassk-count-pill-seam">4653</div>
                    </div>
                  </div>
                </div>

                {/* 2. X (78%) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#0F172A">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-frosted-pod">
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                    </div>
                    <div
                      className="zassk-brand-capsule"
                      style={{ width: '78%', background: 'linear-gradient(90deg, #8B5CF6 0%, #A78BFA 100%)' }}
                    >
                      <span>X.com</span>
                      <div className="zassk-count-pill-seam">379</div>
                    </div>
                  </div>
                </div>

                {/* 3. Instagram (88%) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E1306C" strokeWidth="2">
                      <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
                      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-frosted-pod">
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                      <span className="zassk-pod-dot" />
                    </div>
                    <div
                      className="zassk-brand-capsule"
                      style={{ width: '88%', background: 'linear-gradient(90deg, #FB7185 0%, #F43F5E 100%)' }}
                    >
                      <span>Instagram.com</span>
                      <div className="zassk-count-pill-seam">653</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 4. BOTTOM ROW: TABLE & NOTCHED TRANSACTIONS ── */}
        <div className="zassk-bottom-row">
          <div className="zassk-card zassk-table-card">
            <div className="zassk-revenue-top-bar" style={{ marginBottom: '14px' }}>
              <span className="zassk-card-title">Recent Joining User</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Users">
                <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} color="#4B5565" />
              </button>
            </div>

            <table className="zassk-table">
              <thead>
                <tr>
                  <th style={{ width: '42px' }}>
                    <div
                      className={`zassk-checkbox ${isAllSelected ? 'checked' : ''}`}
                      onClick={toggleSelectAll}
                      role="checkbox"
                      aria-checked={isAllSelected}
                    >
                      {isAllSelected && <LucideIcon name="Check" size={13} strokeWidth={3} color="#FFFFFF" />}
                    </div>
                  </th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Location</th>
                  <th>Status</th>
                  <th>Posted Date</th>
                  <th style={{ width: '40px' }}></th>
                </tr>
              </thead>
              <tbody>
                {mockJoiningUsers.map((user) => {
                  const isChecked = selectedUserIds.has(user.id);
                  return (
                    <tr key={user.id}>
                      <td>
                        <div
                          className={`zassk-checkbox ${isChecked ? 'checked' : ''}`}
                          onClick={() => toggleUserSelection(user.id)}
                          role="checkbox"
                          aria-checked={isChecked}
                        >
                          {isChecked && <LucideIcon name="Check" size={13} strokeWidth={3} color="#FFFFFF" />}
                        </div>
                      </td>
                      <td style={{ fontWeight: 700 }}>{user.name}</td>
                      <td style={{ color: '#64748B' }}>{user.type}</td>
                      <td style={{ color: '#64748B' }}>{user.location}</td>
                      <td>
                        <span
                          className={`zassk-status-pill ${user.status === 'Active' ? 'zassk-status-active' : 'zassk-status-pending'
                            }`}
                        >
                          <span style={{ fontSize: '8px' }}>●</span>
                          {user.status}
                        </span>
                      </td>
                      <td style={{ color: '#64748B' }}>{user.postedDate}</td>
                      <td>
                        <button
                          className="zassk-action-pill-btn"
                          style={{ width: '28px', height: '28px', border: 'none', background: 'transparent' }}
                          aria-label="Actions"
                        >
                          <LucideIcon name="MoreHorizontal" size={16} strokeWidth={2} color="#64748B" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Right: Recent Transactions Card with S-Curved File-Folder Tab Notch Silhouette */}
          <div className="zassk-trans-tabbed-notch">
            <svg className="zassk-card-svg-bg" viewBox="0 0 324 280" preserveAspectRatio="none">
              <path
                d="M0,24 C0,10.7 10.7,0 24,0 L160,0 C170,0 178,6 182,14 L186,22 C190,30 198,36 208,36 L300,36 C313.3,36 324,46.7 324,60 L324,256 C324,269.3 313.3,280 300,280 L24,280 C10.7,280 0,269.3 0,256 Z"
                fill="#FFFFFF"
              />
            </svg>

            <div className="zassk-tabbed-header">
              <span className="zassk-card-title">Recent Transactions</span>
            </div>

            <div className="zassk-trans-list-pad">
              {mockTransactions.map((tx) => (
                <div key={tx.id} className="zassk-trans-item">
                  <div className="zassk-trans-left">
                    <div className="zassk-trans-icon">
                      <LucideIcon name="Briefcase" size={18} strokeWidth={2} color="#3B82F6" />
                    </div>
                    <div>
                      <div className="zassk-trans-symbol">{tx.symbol}</div>
                      <div className="zassk-trans-company">{tx.company}</div>
                    </div>
                  </div>
                  <div className="zassk-trans-right">
                    <div className="zassk-trans-amount">{tx.amount}</div>
                    <div className="zassk-trans-date">{tx.date}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── 5. BOTTOM PERFORMANCE TREND CARD (AlignUI v1.2 Integration) ── */}
        <div className="zassk-bottom-performance-card">
          <TooltipProvider>
            <PerformanceTrend />
          </TooltipProvider>
        </div>
      </main>
    </div>
  );
};

export default Dashboard;
