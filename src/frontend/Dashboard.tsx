// SPDX-License-Identifier: MIT
/**
 * Zassk Modern Glassmorphic Analytics Dashboard
 * Visual correction build matching exact geometry, notched folder tabs,
 * interlocking cards, 14-tick radial gauge, and full-width needle curtain spline.
 */

import React, { useState, useMemo, useRef, MouseEvent } from 'react';
import './Dashboard.css';
import {
  mockNavDockItems,
  mockTaskStatistics,
  mockTotalProfit,
  mockConversionRate,
  mockActiveUsers,
  mockTotalRevenue,
  mockUserSources,
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
    // Minimalist house/home icon (roof outline + floor/door)
    Home: (
      <>
        <path d="M3 10.2L12 3l9 7.2V20a1 1 0 0 1-1 1h-5v-6h-6v6H4a1 1 0 0 1-1-1v-9.8z" />
      </>
    ),
    LayoutDashboard: (
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
    // Authentic Funnel Filter Icon (three horizontal lines centered & tapering downward)
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
  // Navigation dock state
  const [activeTab, setActiveTab] = useState<string>('dashboard');

  // Total Revenue interactive scrubber (Defaults to Day 11 @ $120)
  const [activeRevIndex, setActiveRevIndex] = useState<number>(4);

  // Table row checkbox selections
  const [selectedUserIds, setSelectedUserIds] = useState<Set<string>>(
    new Set(['usr-1']) // Preselect Brooklyn Simmons
  );

  const chartSvgRef = useRef<SVGSVGElement | null>(null);

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

  const handleDockClick = (tabId: string) => {
    setActiveTab(tabId);
    if (onNavigate) onNavigate(tabId);
  };

  // ── Calculation for 14 Thick Pill-Shaped Radial Tick Bars ──
  const radialTicks = useMemo(() => {
    const total = 14;
    const ticks = [];
    const cx = 130;
    const cy = 118;
    const rOuter = 88;
    const rInner = 66; // 22px bar length

    // Color progression from royal blue (#2563EB) to cyan (#38BDF8) to soft cool gray (#E2E8F0)
    const colorStops = [
      '#2563EB', '#2563EB', '#2563EB',
      '#38BDF8', '#38BDF8', '#60A5FA',
      '#93C5FD', '#93C5FD', '#BFDBFE',
      '#CBD5E1', '#E2E8F0', '#E2E8F0',
      '#E2E8F0', '#E2E8F0',
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
        stroke: colorStops[i] || '#E2E8F0',
      });
    }
    return ticks;
  }, []);

  // ── Full-Width Waveform Spline & Needle Curtain Calculation ──
  const { splinePoints, curtainLines, activePointCoord, splinePathD } = useMemo(() => {
    const width = 530;
    const height = 145;

    // Days: 01, 04, 07, 9, 11, 13, 15, 25, 30
    // Exact curve geometry: starts ~40% height, crests to ~90% around 07-11, dips in mid, rises toward 30
    const pointsData = [
      { day: '01', rev: 45, curveY: 58 },
      { day: '04', rev: 72, curveY: 42 },
      { day: '07', rev: 110, curveY: 16 }, // Pronounced high crest
      { day: '9',  rev: 95, curveY: 20 },
      { day: '11', rev: 120, curveY: 46 }, // Featured scrubber point
      { day: '13', rev: 68, curveY: 72 }, // Mid dip
      { day: '15', rev: 86, curveY: 65 },
      { day: '25', rev: 104, curveY: 42 },
      { day: '30', rev: 125, curveY: 34 }, // Rises toward day 30
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

    // High-density vertical needle curtain (spaced ~4px apart)
    const lines = [];
    const lineCount = 110;
    for (let i = 0; i <= lineCount; i++) {
      const x = (i / lineCount) * (width - 32) + 16;
      const tGlobal = (i / lineCount) * (coords.length - 1);
      const segIndex = Math.min(Math.floor(tGlobal), coords.length - 2);
      const t = tGlobal - segIndex;

      const p0 = coords[segIndex];
      const p1 = coords[segIndex + 1];

      // Cubic hermite interpolation
      const y =
        (1 - t) ** 3 * p0.y +
        3 * (1 - t) ** 2 * t * p0.y +
        3 * (1 - t) * t ** 2 * p1.y +
        t ** 3 * p1.y;

      lines.push({ id: i, x, yTop: y, yBottom: height });
    }

    const activeCoord = coords[activeRevIndex] || coords[4];

    return {
      splinePoints: coords,
      curtainLines: lines,
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
        {/* ── TOP NAVIGATION HEADER ── */}
        <header className="zassk-header">
          {/* Brand Pill */}
          <div className="zassk-brand-pill">Zassk</div>

          {/* Center Segmented Floating Dock */}
          <nav className="zassk-dock">
            {mockNavDockItems.map((item) => {
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
                    name={item.id === 'dashboard' ? 'Home' : item.iconName}
                    size={item.id === 'dashboard' ? 16 : 17}
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

        {/* ── TOP ROW METRICS ── */}
        <div className="zassk-top-row">
          {/* Col 1: Greeting & Task Statistics */}
          <div className="zassk-greeting-box">
            <div>
              <h1 className="zassk-hello-text">
                {userGreeting}<br />
                {userName}
              </h1>
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

          {/* Col 2: Total Responses Card with File-Folder Tab Notch */}
          <div className="zassk-card-notched-responses">
            <div className="zassk-notched-header">
              <div className="zassk-notched-tab-pill">Total Responses</div>
              <svg className="zassk-notch-bg-svg" viewBox="0 0 110 38" fill="none">
                <path
                  d="M0 0 C20 0, 30 18, 50 18 L110 18"
                  stroke="#E2E8F0"
                  strokeWidth="1"
                />
              </svg>
            </div>

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
                    strokeWidth={7.5}
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

          {/* Col 3: Interlocking "Total Profit" & "Active Users" */}
          <div className="zassk-interlocking-card">
            {/* Upper Tier: Total Profit */}
            <div className="zassk-interlock-top">
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

            {/* Lower Tier: Active Users */}
            <div className="zassk-interlock-bottom">
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

          {/* Col 4: Conversion Rate & Ended Task */}
          <div className="zassk-col4-column">
            {/* Conversion Rate */}
            <div className="zassk-col4-card">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Conversion Rate</span>
                <button className="zassk-action-pill-btn" aria-label="View Conversion">
                  <LucideIcon name="ArrowUpRight" size={14} strokeWidth={2} />
                </button>
              </div>
              <div className="zassk-metric-big" style={{ margin: '4px 0 10px 0' }}>
                {mockConversionRate.rate}%
              </div>
              <div className="zassk-dense-ticks">
                {Array.from({ length: mockConversionRate.totalTicks }).map((_, i) => {
                  const isFilled = i < Math.round((mockConversionRate.rate / 100) * mockConversionRate.totalTicks);
                  return (
                    <div
                      key={i}
                      className={`zassk-tick-line ${isFilled ? 'filled' : 'unfilled'}`}
                    />
                  );
                })}
              </div>
            </div>

            {/* Ended Task with Alternating Dot Matrix */}
            <div className="zassk-col4-card">
              <div className="zassk-interlock-header">
                <span className="zassk-card-title">Ended Task</span>
              </div>
              <div className="zassk-metric-big" style={{ margin: '4px 0 8px 0' }}>
                80
              </div>
              <div className="zassk-dot-matrix">
                {/* Row 1 */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-bold" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-bold" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-bold" />
                </div>
                {/* Row 2 */}
                <div className="zassk-dot-matrix-row">
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-bold" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-bold" />
                  <div className="zassk-matrix-dot-bold" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                  <div className="zassk-matrix-dot-pip" />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── MIDDLE ROW: REVENUE WAVEFORM & USER SOURCES ── */}
        <div className="zassk-mid-row">
          {/* Full-Width Total Revenue Card */}
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
                  <div className="zassk-revenue-amount">{mockTotalRevenue.headlineAmount}</div>
                  <div className="zassk-revenue-sub">{mockTotalRevenue.subtitle}</div>
                </div>
                <div className="zassk-y-markers">
                  {mockTotalRevenue.yAxisMarkers.map((m) => (
                    <span key={m}>{m}</span>
                  ))}
                </div>
              </div>

              {/* Full-Width Waveform Curtain Area */}
              <div className="zassk-waveform-container">
                <svg
                  ref={chartSvgRef}
                  className="zassk-waveform-svg"
                  viewBox="0 0 530 145"
                  onMouseMove={handleChartMouseMove}
                >
                  <defs>
                    <linearGradient id="needleFadeGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#93C5FD" stopOpacity="0.85" />
                      <stop offset="100%" stopColor="#EFF6FF" stopOpacity="0.05" />
                    </linearGradient>
                  </defs>

                  {/* Vertical Needle Curtain (Fine lines fading to 0% opacity) */}
                  {curtainLines.map((line) => (
                    <line
                      key={line.id}
                      x1={line.x}
                      y1={line.yTop}
                      x2={line.x}
                      y2={line.yBottom}
                      stroke="url(#needleFadeGrad)"
                      strokeWidth={1.2}
                    />
                  ))}

                  {/* High-fidelity continuous spline path */}
                  <path
                    d={splinePathD}
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth={2.8}
                    strokeLinecap="round"
                  />

                  {/* Target Scrubber Ring Pinpoint */}
                  {activePointCoord && (
                    <g style={{ cursor: 'pointer' }}>
                      <circle
                        cx={activePointCoord.x}
                        cy={activePointCoord.y}
                        r={8}
                        fill="#FFFFFF"
                        stroke="#2563EB"
                        strokeWidth={2.5}
                      />
                      <circle
                        cx={activePointCoord.x}
                        cy={activePointCoord.y}
                        r={3.5}
                        fill="#2563EB"
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

          {/* User Source Card with Floating Pill Counts */}
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
                {mockUserSources.map((source) => (
                  <div key={source.id} className="zassk-source-row">
                    {/* Brand Icon */}
                    <div className="zassk-brand-icon">
                      {source.brand === 'google' && (
                        <svg width="20" height="20" viewBox="0 0 24 24">
                          <path
                            fill="#4285F4"
                            d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.65v3.05h3.9c2.28-2.1 3.64-5.2 3.64-9.14z"
                          />
                          <path
                            fill="#34A853"
                            d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.9-3.05c-1.08.72-2.45 1.16-4.03 1.16-3.1 0-5.74-2.1-6.68-4.91H1.21v3.13C3.25 21.43 7.31 24 12 24z"
                          />
                          <path
                            fill="#FBBC05"
                            d="M5.32 14.29c-.25-.72-.38-1.49-.38-2.29s.13-1.57.38-2.29V6.58H1.21C.44 8.11 0 9.99 0 12s.44 3.89 1.21 5.42l4.11-3.13z"
                          />
                          <path
                            fill="#EA4335"
                            d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.57 1.21 6.58l4.11 3.13c.94-2.81 3.58-4.96 6.68-4.96z"
                          />
                        </svg>
                      )}
                      {source.brand === 'x' && (
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="#0F172A">
                          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                        </svg>
                      )}
                      {source.brand === 'instagram' && (
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E1306C" strokeWidth="2">
                          <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
                          <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                          <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
                        </svg>
                      )}
                    </div>

                    {/* Striped Track & Progress Capsule */}
                    <div className="zassk-brand-track">
                      <div
                        className="zassk-brand-capsule"
                        style={{
                          width: `${source.percentageWidth}%`,
                          backgroundColor:
                            source.brand === 'google'
                              ? '#3B82F6'
                              : source.brand === 'x'
                              ? '#8B5CF6'
                              : '#FB7185',
                        }}
                      >
                        <span>{source.domain}</span>
                        {/* Floating Pill Count Badge on Right Tip */}
                        <div className="zassk-count-pill">{source.count}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── BOTTOM ROW: USERS TABLE & NOTCHED TRANSACTIONS ── */}
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

          {/* Right: Recent Transactions Card with Stepped Top Tab */}
          <div className="zassk-trans-notched-card">
            <div className="zassk-trans-header-notch">
              <span className="zassk-card-title">Recent Transactions</span>
            </div>

            <div className="zassk-trans-list-pad">
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
  );
};

export default Dashboard;
