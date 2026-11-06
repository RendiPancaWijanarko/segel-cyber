// SPDX-License-Identifier: MIT
/**
 * Zassk Precision Pixel-Exact Analytics Dashboard
 * Production-ready React TypeScript component.
 * Features:
 * - Clean Home icon navigation dock with Dashboard active and inactive circular buttons (Help is inactive).
 * - Single physical interlocking geometry for Total Profit and Active Users.
 * - Top-tab notches on Total Responses and Recent Transactions.
 * - Full-width audio-spectrum / needle waterfall line chart across days 01 to 30.
 * - 14-thick-tick radial arc gauge with royal blue -> sky blue -> pale ice blue -> muted gray.
 * - Boundary-seam pill badges on User Source progress tracks.
 * - 28-tick conversion bar and 2-row prominent/pip dot grid.
 */

import React, { useState, useMemo, useRef, MouseEvent } from 'react';
import './Dashboard.css';
import {
  mockTaskStatistics,
  mockTotalProfit,
  mockActiveUsers,
  mockJoiningUsers,
  mockTransactions,
} from './mockData';
import { ZasskDashboardProps } from './types';

// ── Tailored Icon Component ──
interface IconProps {
  name: string;
  size?: number;
  strokeWidth?: number;
  className?: string;
}

export const LucideIcon: React.FC<IconProps> = ({
  name,
  size = 18,
  strokeWidth = 2,
  className = '',
}) => {
  const iconPaths: Record<string, React.ReactNode> = {
    // Minimalist house/home icon (outline with a floor dash)
    Home: (
      <>
        <path d="M3 10.2L12 3l9 7.2V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1v-9.8z" />
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
    // Funnel filter icon
    FunnelFilter: (
      <>
        <line x1="4" y1="7" x2="20" y2="7" />
        <line x1="7" y1="12" x2="17" y2="12" />
        <line x1="10" y1="17" x2="14" y2="17" />
      </>
    ),
    MoreHorizontal: (
      <>
        <circle cx="12" cy="12" r="1.5" />
        <circle cx="19" cy="12" r="1.5" />
        <circle cx="5" cy="12" r="1.5" />
      </>
    ),
    Folder: (
      <>
        <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
      </>
    ),
    Check: (
      <path d="M20 6 9 17l-5-5" />
    ),
  };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      {iconPaths[name] || <circle cx="12" cy="12" r="10" />}
    </svg>
  );
};

// ── Main Dashboard Component ──
export const Dashboard: React.FC<ZasskDashboardProps> = ({
  userName = 'Keren nix',
  userGreeting = 'Hello,',
  onNavigate,
  onSearch,
  className = '',
}) => {
  // Navigation dock state: defaults to 'dashboard'
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  // Total Revenue interactive scrubber (Defaults to Day 11 @ $120)
  const [activeRevIndex, setActiveRevIndex] = useState<number>(4);

  // Table row checkbox selections
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(
    new Set(['usr-1']) // Preselect Brooklyn Simmons
  );

  const chartSvgRef = useRef<SVGSVGElement | null>(null);

  // Navigation dock items strictly ordered
  const dockItems = [
    { id: 'dashboard', label: 'Dashboard', icon: 'Home' },
    { id: 'profile', label: 'Profile', icon: 'User' },
    { id: 'docs', label: 'Documents', icon: 'FileText' },
    { id: 'calendar', label: 'Calendar', icon: 'Calendar' },
    { id: 'analytics', label: 'Analytics', icon: 'BarChart3' },
    { id: 'settings', label: 'Settings', icon: 'Settings' },
    { id: 'help', label: 'Help', icon: 'HelpCircle' }, // Strictly inactive icon button
  ];

  const handleDockClick = (tabId: string) => {
    setActiveTab(tabId);
    if (onNavigate) onNavigate(tabId);
  };

  // Toggle single user row
  const toggleUserSelection = (userId: string) => {
    setSelectedUserIds((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  };

  // Toggle select-all
  const toggleSelectAll = () => {
    if (selectedUserIds.size === mockJoiningUsers.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(mockJoiningUsers.map((u) => u.id)));
    }
  };

  const isAllSelected = selectedUserIds.size === mockJoiningUsers.length;

  // ── 14 Thick Rounded-Cap Pill Bars Arc Gauge ──
  const radialTicks = useMemo(() => {
    const total = 14;
    const ticks = [];
    const cx = 130;
    const cy = 118;
    const rOuter = 88;
    const rInner = 65; // 23px tick length

    // Color progression: Royal blue (#2563EB) -> sky blue (#38BDF8) -> pale ice blue (#BAE6FD) -> muted gray (#E2E8F0)
    const colorProgression = [
      '#2563EB', '#2563EB', '#2563EB', '#2563EB', // Royal blue
      '#38BDF8', '#38BDF8', '#38BDF8',            // Sky blue
      '#BAE6FD', '#BAE6FD', '#BAE6FD', '#BAE6FD', // Pale ice blue
      '#E2E8F0', '#E2E8F0', '#E2E8F0',            // Muted gray
    ];

    for (let i = 0; i < total; i++) {
      const angleDeg = 180 - (i / (total - 1)) * 180;
      const rad = (angleDeg * Math.PI) / 180;

      const x1 = cx - rOuter * Math.cos(rad);
      const y1 = cy - rOuter * Math.sin(rad);
      const x2 = cx - rInner * Math.cos(rad);
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

  // ── Full-Width Audio-Spectrum / Needle Waterfall Spline Chart ──
  const { splinePoints, needleLines, activePointCoord, splinePathD } = useMemo(() => {
    const width = 530;
    const height = 145;

    // Days: 01, 04, 07, 9, 11, 13, 15, 25, 30
    // Starts at ~35% height (y=94), rises smoothly, crests at ~85% height (y=22) across days 07-10,
    // dips around day 14 (~45% height, y=80), recovers toward day 30 (~60% height, y=58).
    const pointsData = [
      { day: '01', rev: 45, curveY: 65 },  // 35% height from bottom -> y=65%
      { day: '04', rev: 72, curveY: 42 },
      { day: '07', rev: 110, curveY: 15 }, // Broad crest (~85% height)
      { day: '9',  rev: 115, curveY: 16 },
      { day: '11', rev: 120, curveY: 44 }, // Active scrubber point
      { day: '13', rev: 68, curveY: 55 },  // Gentle dip ~45% height
      { day: '15', rev: 86, curveY: 52 },
      { day: '25', rev: 104, curveY: 45 },
      { day: '30', rev: 125, curveY: 38 }, // Recovers toward day 30
    ];

    const coords = pointsData.map((p, idx) => {
      const x = (idx / (pointsData.length - 1)) * (width - 32) + 16;
      const y = (p.curveY / 100) * (height - 24) + 12;
      return { ...p, x, y };
    });

    // Smooth cubic bezier spline
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

    // High-density vertical needle lines spaced every 2.5px across the entire width
    const lines = [];
    const lineSpacing = 2.5;
    const totalLines = Math.floor((width - 32) / lineSpacing);

    for (let i = 0; i <= totalLines; i++) {
      const x = 16 + i * lineSpacing;
      const tGlobal = (i / totalLines) * (coords.length - 1);
      const segIndex = Math.min(Math.floor(tGlobal), coords.length - 2);
      const t = tGlobal - segIndex;

      const p0 = coords[segIndex];
      const p1 = coords[segIndex + 1];

      // Cubic hermite spline interpolation
      const y =
        (1 - t) ** 3 * p0.y +
        3 * (1 - t) ** 2 * t * p0.y +
        3 * (1 - t) * t ** 2 * p1.y +
        t ** 3 * p1.y;

      // Vibrant near crest & scrubber (x between 120 and 300)
      const isNearScrubberOrCrest = Math.abs(x - 240) < 90;
      const opacity = isNearScrubberOrCrest ? 0.38 : 0.22;

      lines.push({ id: i, x, yTop: y, yBottom: height, opacity });
    }

    const activeCoord = coords[activeRevIndex] || coords[4];

    return {
      splinePoints: coords,
      needleLines: lines,
      activePointCoord: activeCoord,
      splinePathD: pathD,
    };
  }, [activeRevIndex]);

  // Handle revenue chart hover scrubbing
  const handleChartMouseMove = (e: MouseEvent<SVGSVGElement>) => {
    if (!chartSvgRef.current) return;
    const rect = chartSvgRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const width = rect.width;
    const fraction = Math.max(0, Math.min(1, mouseX / width));
    const nearestIdx = Math.round(fraction * 8);
    setActiveRevIndex(nearestIdx);
  };

  return (
    <div className={`zassk-canvas ${className}`}>
      <div className="zassk-frame">
        {/* ── 1. TOP NAVIGATION HEADER ── */}
        <header className="zassk-header">
          {/* Brand Pill */}
          <div className="zassk-brand-pill">Zassk</div>

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
                  />
                  {isActive && <span>{item.label}</span>}
                </button>
              );
            })}
          </nav>

          {/* Right Utilities */}
          <div className="zassk-header-utilities">
            <button
              className="zassk-circle-btn"
              onClick={() => onSearch && onSearch('')}
              aria-label="Search"
              title="Search"
            >
              <LucideIcon name="Search" size={17} strokeWidth={2} />
            </button>
            <button className="zassk-avatar-btn" aria-label="Profile Avatar" title="Keren nix">
              <img
                src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=150"
                alt="User Profile"
              />
            </button>
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

          {/* Col 2: Total Responses Card with True File-Folder Tab Notch */}
          <div className="zassk-card-notched-container">
            {/* Elevated Tab */}
            <div className="zassk-notched-tab">
              <span className="zassk-notched-tab-title">Total Responses</span>
            </div>
            {/* Concave transition scoop */}
            <svg className="zassk-notched-scoop" viewBox="0 0 20 20" fill="none">
              <path d="M 0 0 C 0 11, 9 20, 20 20 L 0 20 Z" fill="#FFFFFF" />
            </svg>

            {/* Main Body */}
            <div className="zassk-notched-body">
              <div className="zassk-gauge-wrapper-centered">
                <svg className="zassk-radial-gauge-svg" viewBox="0 0 260 145">
                  {radialTicks.map((tick) => (
                    <line
                      key={tick.id}
                      x1={tick.x1}
                      y1={tick.y1}
                      x2={tick.x2}
                      y2={tick.y2}
                      stroke={tick.stroke}
                      strokeWidth={8}
                      strokeLinecap="round"
                    />
                  ))}
                </svg>
                <div className="zassk-gauge-center-content">
                  <div className="zassk-gauge-center-val">98%</div>
                  <div className="zassk-gauge-center-label">Responses rate</div>
                </div>
              </div>
            </div>
          </div>

          {/* Col 3: Physical Interlocking "Total Profit" & "Active Users" */}
          <div className="zassk-interlocking-card">
            {/* Upper Tier: Total Profit with Stepped Contour */}
            <div className="zassk-interlock-top-tier">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Total Profit</span>
                <button className="zassk-action-pill-btn" aria-label="View Profit">
                  <LucideIcon name="ArrowUpRight" size={14} strokeWidth={2} />
                </button>
              </div>
              <div className="zassk-profit-row">
                <div className="zassk-metric-big">{mockTotalProfit.value}</div>
                <div className="zassk-mini-barchart">
                  {mockTotalProfit.bars.map((height, i) => (
                    <div
                      key={i}
                      className="zassk-mini-bar"
                      style={{
                        height: `${height}%`,
                        backgroundColor: i === 6 ? '#2563EB' : '#93C5FD',
                      }}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Stepped contour shelf divider */}
            <div className="zassk-stepped-shelf-divider" />

            {/* Lower Tier: Active Users nestled flush */}
            <div className="zassk-interlock-bottom-tier">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Active Users</span>
                <div className="zassk-split-labels">
                  <span>{mockActiveUsers.splits.segmentA}%</span>
                  <span>{mockActiveUsers.splits.segmentB}%</span>
                  <span>{mockActiveUsers.splits.segmentC}%</span>
                </div>
              </div>
              <div className="zassk-metric-big" style={{ margin: '2px 0 6px 0' }}>
                {mockActiveUsers.count}
              </div>
              <div className="zassk-split-bar">
                <div className="zassk-split-seg-1" title="Primary users (75%)" />
                <div className="zassk-split-seg-2" title="Secondary users (25%)" />
                <div className="zassk-split-seg-3" title="Guest users (10%)" />
              </div>
            </div>
          </div>

          {/* Col 4: Conversion Rate (28 thin ticks) & Ended Task (alternating dot grid) */}
          <div className="zassk-col4-column">
            {/* Conversion Rate */}
            <div className="zassk-col4-card">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Conversion Rate</span>
                <button className="zassk-action-pill-btn" aria-label="View Conversion">
                  <LucideIcon name="ArrowUpRight" size={14} strokeWidth={2} />
                </button>
              </div>
              <div className="zassk-metric-big" style={{ margin: '4px 0 8px 0' }}>
                75%
              </div>
              {/* 28 thin vertical tick bars (width: 3px, height: 18px, gap: 3px) */}
              <div className="zassk-dense-ticks-28">
                {Array.from({ length: 28 }).map((_, i) => (
                  <div
                    key={i}
                    className={`zassk-tick-bar-28 ${i < 21 ? 'filled' : 'unfilled'}`}
                  />
                ))}
              </div>
            </div>

            {/* Ended Task with 4-Row Ascending Wave Dot Grid */}
            <div className="zassk-col4-card">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Ended Task</span>
              </div>
              <div className="zassk-metric-big" style={{ margin: '4px 0 8px 0' }}>
                80
              </div>
              <div className="zassk-dot-matrix">
                {/* Row 1: Top row with blue dots at right */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                </div>
                {/* Row 2: Mid-high row */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                </div>
                {/* Row 3: Mid-low row */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                </div>
                {/* Row 4: Bottom row starting from left */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-prominent" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                  <div className="zassk-dot-muted-pip" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── 3. MIDDLE ROW: WATERFALL LINE-NEEDLE CHART & USER SOURCES ── */}
        <div className="zassk-mid-row">
          {/* Full-Width Total Revenue Card with Vertical Needle Texture */}
          <div className="zassk-card zassk-revenue-card">
            <div className="zassk-revenue-top-bar">
              <span className="zassk-card-title">Total Revenue</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Revenue">
                <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} />
              </button>
            </div>

            <div className="zassk-revenue-layout">
              {/* Left Metric Column */}
              <div className="zassk-revenue-side-metric">
                <div>
                  <div className="zassk-revenue-amount">$1240</div>
                  <div className="zassk-revenue-sub">Last 15 days</div>
                  <div className="zassk-revenue-sub" style={{ marginTop: '0px' }}>Ordars</div>
                </div>
                <div className="zassk-y-markers">
                  <span>100%</span>
                  <span>80%</span>
                  <span>60%</span>
                  <span>40%</span>
                  <span>20%</span>
                </div>
              </div>

              {/* Full-Width Waterfall Needle Container */}
              <div className="zassk-waveform-container">
                <svg
                  ref={chartSvgRef}
                  className="zassk-waveform-svg"
                  viewBox="0 0 530 145"
                  onMouseMove={handleChartMouseMove}
                >
                  {/* Vertical Needle Waterfall Texture lines */}
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

                  {/* Full-Width Bezier Spline Line */}
                  <path
                    d={splinePathD}
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth={2.8}
                    strokeLinecap="round"
                  />

                  {/* Active Scrubber Point Ring */}
                  {activePointCoord && (
                    <g style={{ cursor: 'pointer' }}>
                      <circle
                        cx={activePointCoord.x}
                        cy={activePointCoord.y}
                        r={5}
                        fill="#FFFFFF"
                        stroke="#2563EB"
                        strokeWidth={2.5}
                      />
                    </g>
                  )}
                </svg>

                {/* Floating Tooltip Pill */}
                {activePointCoord && (
                  <div
                    className="zassk-floating-tooltip"
                    style={{
                      left: `${(activePointCoord.x / 530) * 100}%`,
                      top: `${(activePointCoord.y / 145) * 100}%`,
                    }}
                  >
                    Revenue ${activePointCoord.revenue}
                  </div>
                )}
              </div>
            </div>

            {/* Timeline Range Scrubber Bar */}
            <div className="zassk-timeline-slider-track">
              <div
                className="zassk-timeline-slider-thumb"
                style={{ left: '26%', width: '28%' }}
              />
            </div>

            {/* Full-Width X-Axis Days */}
            <div className="zassk-x-axis-full">
              {splinePoints.map((p, idx) => (
                <span
                  key={idx}
                  style={{
                    color: idx === activeRevIndex ? '#0F172A' : '#94A3B8',
                    fontWeight: idx === activeRevIndex ? 800 : 600,
                  }}
                >
                  {p.day}
                </span>
              ))}
            </div>
          </div>

          {/* User Source Card with Seam-Aligned Pill Badges */}
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
                  <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} />
                </button>
              </div>

              <div className="zassk-source-list">
                {/* 1. Google (Blue #3B82F6) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24">
                      <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.05h3.9c2.28-2.1 3.64-5.2 3.64-9.14z"/>
                      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.9-3.05c-1.08.72-2.45 1.16-4.03 1.16-3.1 0-5.74-2.1-6.68-4.91H1.21v3.13C3.25 21.43 7.31 24 12 24z"/>
                      <path fill="#FBBC05" d="M5.32 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.58H1.21C.44 8.11 0 9.99 0 12s.44 3.89 1.21 5.42l4.11-3.13z"/>
                      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.57 1.21 6.58l4.11 3.13c.94-2.81 3.58-4.96 6.68-4.96z"/>
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-brand-capsule" style={{ width: '62%', backgroundColor: '#3B82F6' }}>
                      <span>Google.com</span>
                      <div className="zassk-count-pill-seam">4653</div>
                    </div>
                  </div>
                </div>

                {/* 2. X (Purple #8B5CF6) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="#0F172A">
                      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-brand-capsule" style={{ width: '78%', backgroundColor: '#8B5CF6' }}>
                      <span>X.com</span>
                      <div className="zassk-count-pill-seam">379</div>
                    </div>
                  </div>
                </div>

                {/* 3. Instagram (Coral/Salmon #FB7185) */}
                <div className="zassk-source-row">
                  <div className="zassk-brand-icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E1306C" strokeWidth="2">
                      <rect width="20" height="20" x="2" y="2" rx="5" ry="5"/>
                      <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/>
                      <line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/>
                    </svg>
                  </div>
                  <div className="zassk-brand-track">
                    <div className="zassk-brand-capsule" style={{ width: '92%', backgroundColor: '#FB7185' }}>
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
          {/* Left: Recent Joining User Table */}
          <div className="zassk-card zassk-table-card">
            <div className="zassk-revenue-top-bar" style={{ marginBottom: '14px' }}>
              <span className="zassk-card-title">Recent Joining User</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Users">
                <LucideIcon name="FunnelFilter" size={15} strokeWidth={2} />
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
                      {isAllSelected && <LucideIcon name="Check" size={13} strokeWidth={3} />}
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
                          {isChecked && <LucideIcon name="Check" size={13} strokeWidth={3} />}
                        </div>
                      </td>
                      <td style={{ fontWeight: 700 }}>{user.name}</td>
                      <td style={{ color: '#64748B' }}>{user.type}</td>
                      <td style={{ color: '#64748B' }}>{user.location}</td>
                      <td>
                        <span
                          className={`zassk-status-pill ${
                            user.status === 'Active' ? 'zassk-status-active' : 'zassk-status-pending'
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
                          <LucideIcon name="MoreHorizontal" size={16} strokeWidth={2} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Right: Recent Transactions Card with True File-Folder Tab Notch */}
          <div className="zassk-trans-notched-container">
            {/* Elevated Tab */}
            <div className="zassk-trans-tab">
              <span className="zassk-card-title">Recent Transactions</span>
            </div>
            {/* Concave transition scoop */}
            <svg className="zassk-trans-scoop" viewBox="0 0 20 20" fill="none">
              <path d="M 0 0 C 0 11, 9 20, 20 20 L 0 20 Z" fill="#FFFFFF" />
            </svg>

            <div className="zassk-trans-body">
              <div className="zassk-trans-list-pad" style={{ padding: '24px 0 0 0' }}>
                {mockTransactions.map((tx) => (
                  <div key={tx.id} className="zassk-trans-item">
                    <div className="zassk-trans-left">
                      <div className="zassk-trans-icon">
                        <LucideIcon name="Folder" size={18} strokeWidth={2} />
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
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
