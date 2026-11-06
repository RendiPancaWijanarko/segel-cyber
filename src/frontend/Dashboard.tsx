// SPDX-License-Identifier: MIT
/**
 * Zassk Modern Glassmorphic Analytics Dashboard
 * Production-ready React TypeScript component.
 * Recreates the visual reference with complete interactivity,
 * high-density curtain spline charts, radial gauges, and textured patterns.
 */

import React, { useState, useMemo, useRef, MouseEvent } from 'react';
import './Dashboard.css';
import {
  mockNavDockItems,
  mockTaskStatistics,
  mockTotalResponses,
  mockTotalProfit,
  mockConversionRate,
  mockActiveUsers,
  mockEndedTask,
  mockTotalRevenue,
  mockUserSources,
  mockJoiningUsers,
  mockTransactions,
} from './mockData';
import { ZasskDashboardProps } from './types';

// ── Lucide Icon Inline Component (Clean, typed, zero-dependency) ──
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
    LayoutDashboard: (
      <>
        <rect width="7" height="9" x="3" y="3" rx="1" />
        <rect width="7" height="5" x="14" y="3" rx="1" />
        <rect width="7" height="9" x="14" y="12" rx="1" />
        <rect width="7" height="5" x="3" y="16" rx="1" />
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
    SlidersHorizontal: (
      <>
        <line x1="21" x2="14" y1="4" y2="4" />
        <line x1="10" x2="3" y1="4" y2="4" />
        <line x1="21" x2="12" y1="12" y2="12" />
        <line x1="8" x2="3" y1="12" y2="12" />
        <line x1="21" x2="16" y1="20" y2="20" />
        <line x1="12" x2="3" y1="20" y2="20" />
        <line x1="14" x2="14" y1="2" y2="6" />
        <line x1="8" x2="8" y1="10" y2="14" />
        <line x1="16" x2="16" y1="18" y2="22" />
      </>
    ),
    MoreHorizontal: (
      <>
        <circle cx="12" cy="12" r="1" />
        <circle cx="19" cy="12" r="1" />
        <circle cx="5" cy="12" r="1" />
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

  // Total Revenue interactive scrubber
  const [activeRevIndex, setActiveRevIndex] = useState<number>(4); // Defaults to Day "11" ($120)

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

  // Handle Dock Click
  const handleDockClick = (tabId: string) => {
    setActiveTab(tabId);
    if (onNavigate) {
      onNavigate(tabId);
    }
  };

  // ── Calculation for 14-tick Radial Arch Gauge ──
  const radialTicks = useMemo(() => {
    const total = mockTotalResponses.totalTicks; // 14 ticks
    const filledCount = Math.round((mockTotalResponses.rate / 100) * total); // 14
    const ticks = [];
    const cx = 130;
    const cy = 115;
    const radius = 80;
    const tickLength = 18;

    for (let i = 0; i < total; i++) {
      // Semi-circle angle: 180 degrees (from 180° to 0°)
      const angleDeg = 180 - (i / (total - 1)) * 180;
      const angleRad = (angleDeg * Math.PI) / 180;

      const x1 = cx - radius * Math.cos(angleRad);
      const y1 = cy - radius * Math.sin(angleRad);
      const x2 = cx - (radius - tickLength) * Math.cos(angleRad);
      const y2 = cy - (radius - tickLength) * Math.sin(angleRad);

      // Color interpolation: deep blue -> light blue -> light gray
      let stroke = '#E2E8F0';
      if (i < 3) stroke = '#2563EB'; // Vibrant royal blue
      else if (i < 7) stroke = '#3B82F6';
      else if (i < 10) stroke = '#60A5FA';
      else if (i < 12) stroke = '#93C5FD';
      else stroke = '#CBD5E1';

      ticks.push({ id: i, x1, y1, x2, y2, stroke });
    }
    return ticks;
  }, []);

  // ── High-density curtain waterfall spline data ──
  const { splinePoints, curtainLines, activePointCoord } = useMemo(() => {
    const width = 460;
    const height = 150;
    const points = mockTotalRevenue.points;

    // Calculate (x, y) coordinates for spline points
    const coords = points.map((p, idx) => {
      const x = (idx / (points.length - 1)) * (width - 40) + 20;
      const y = (p.curveY / 100) * (height - 30) + 15;
      return { ...p, x, y };
    });

    // Generate smooth bezier curve path string
    let pathD = `M ${coords[0].x} ${coords[0].y}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const curr = coords[i];
      const next = coords[i + 1];
      const cpX1 = curr.x + (next.x - curr.x) / 2;
      const cpY1 = curr.y;
      const cpX2 = curr.x + (next.x - curr.x) / 2;
      const cpY2 = next.y;
      pathD += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${next.x} ${next.y}`;
    }

    // Generate 60 vertical curtain lines under the spline
    const lines = [];
    const lineCount = 65;
    for (let i = 0; i <= lineCount; i++) {
      const x = (i / lineCount) * (width - 40) + 20;
      // Approximate spline y at x using piecewise cubic interpolation
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

    // Find nearest point index
    const fraction = Math.max(0, Math.min(1, mouseX / width));
    const nearestIdx = Math.round(fraction * (mockTotalRevenue.points.length - 1));
    setActiveRevIndex(nearestIdx);
  };

  return (
    <div className={`zassk-canvas ${className}`}>
      <div className="zassk-frame">
        {/* ── TOP NAVIGATION HEADER ── */}
        <header className="zassk-header">
          {/* Brand Pill */}
          <div className="zassk-brand-pill">Zassk</div>

          {/* Segmented Floating Dock */}
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
                  <LucideIcon name={item.iconName} size={17} strokeWidth={2} />
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
              <LucideIcon name="Search" size={18} strokeWidth={2} />
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
              <div className="zassk-hello-text">{userGreeting}</div>
              <h1 className="zassk-name-text">{userName}</h1>
              <div className="zassk-welcome-sub">Welcome Back</div>
            </div>

            <div className="zassk-task-stat-widget">
              <div className="zassk-stat-header">
                <span className="zassk-stat-label">Task Statistics</span>
                <div>
                  <span className="zassk-stat-count">{mockTaskStatistics.count}</span>
                  <span className="zassk-trend-badge">↗ {mockTaskStatistics.trendPercentage}%</span>
                </div>
              </div>
              <div className="zassk-progress-capsule">
                <div className="zassk-seg-1" title="Completed Tasks" />
                <div className="zassk-seg-2" title="In Progress" />
                <div className="zassk-seg-3" title="Planned" />
              </div>
            </div>
          </div>

          {/* Col 2: Total Responses Card */}
          <div className="zassk-card zassk-radial-card">
            <div className="zassk-card-title">Total Responses</div>
            <div className="zassk-gauge-wrapper">
              <svg className="zassk-radial-gauge-svg" viewBox="0 0 260 140">
                {radialTicks.map((tick) => (
                  <line
                    key={tick.id}
                    x1={tick.x1}
                    y1={tick.y1}
                    x2={tick.x2}
                    y2={tick.y2}
                    stroke={tick.stroke}
                    strokeWidth={5}
                    strokeLinecap="round"
                  />
                ))}
              </svg>
              <div className="zassk-gauge-center-content">
                <div className="zassk-gauge-center-val">{mockTotalResponses.rate}%</div>
                <div className="zassk-gauge-center-label">{mockTotalResponses.label}</div>
              </div>
            </div>
          </div>

          {/* Col 3: Total Profit & Active Users */}
          <div className="zassk-mini-column">
            {/* Total Profit Card */}
            <div className="zassk-card zassk-mini-card">
              <div className="zassk-card-header">
                <span className="zassk-card-title">Total Profit</span>
                <button className="zassk-action-pill-btn" aria-label="View Profit">
                  <LucideIcon name="ArrowUpRight" size={15} strokeWidth={2} />
                </button>
              </div>
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
                    title={`Bar ${i + 1}: ${height}%`}
                  />
                ))}
              </div>
            </div>

            {/* Active Users Card */}
            <div className="zassk-card zassk-mini-card">
              <div className="zassk-card-header">
                <span className="zassk-card-title">Active Users</span>
              </div>
              <div className="zassk-split-labels">
                <span>{mockActiveUsers.splits.segmentA}%</span>
                <span>{mockActiveUsers.splits.segmentB}%</span>
                <span>{mockActiveUsers.splits.segmentC}%</span>
              </div>
              <div className="zassk-metric-big">{mockActiveUsers.count}</div>
              <div className="zassk-split-bar">
                <div className="zassk-split-seg-1" title="Primary users (75%)" />
                <div className="zassk-split-seg-2" title="Secondary users (25%)" />
                <div className="zassk-split-seg-3" title="Guest users (10%)" />
              </div>
            </div>
          </div>

          {/* Col 4: Conversion Rate & Ended Task */}
          <div className="zassk-mini-column">
            {/* Conversion Rate Card */}
            <div className="zassk-card zassk-mini-card">
              <div className="zassk-card-header">
                <span className="zassk-card-title">Conversion Rate</span>
                <button className="zassk-action-pill-btn" aria-label="View Conversion">
                  <LucideIcon name="ArrowUpRight" size={15} strokeWidth={2} />
                </button>
              </div>
              <div className="zassk-metric-big">{mockConversionRate.rate}%</div>
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

            {/* Ended Task Card */}
            <div className="zassk-card zassk-mini-card">
              <div className="zassk-card-header">
                <span className="zassk-card-title">Ended Task</span>
              </div>
              <div className="zassk-metric-big">{mockEndedTask.count}</div>
              <div className="zassk-dot-matrix">
                {Array.from({ length: mockEndedTask.matrixRows }).map((_, r) => (
                  <div key={r} className="zassk-dot-matrix-row">
                    {Array.from({ length: mockEndedTask.matrixCols }).map((_, c) => {
                      const dotIndex = r * mockEndedTask.matrixCols + c;
                      const isActive = dotIndex < mockEndedTask.completedCount;
                      return (
                        <div
                          key={c}
                          className={`zassk-matrix-dot ${isActive ? 'active' : 'inactive'}`}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── MIDDLE ROW: REVENUE & USER SOURCES ── */}
        <div className="zassk-mid-row">
          {/* Left: Total Revenue Line Curtain Chart */}
          <div className="zassk-card zassk-revenue-card">
            <div className="zassk-card-header">
              <span className="zassk-card-title">Total Revenue</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Revenue">
                <LucideIcon name="SlidersHorizontal" size={15} strokeWidth={2} />
              </button>
            </div>

            <div className="zassk-revenue-content">
              {/* Left Column: Big Value + Y-markers */}
              <div className="zassk-revenue-left-col">
                <div>
                  <div className="zassk-revenue-big-val">{mockTotalRevenue.headlineAmount}</div>
                  <div className="zassk-revenue-sub">{mockTotalRevenue.subtitle}</div>
                </div>
                <div className="zassk-y-markers">
                  {mockTotalRevenue.yAxisMarkers.map((m) => (
                    <span key={m}>{m}</span>
                  ))}
                </div>
              </div>

              {/* Chart Curtain Area */}
              <div className="zassk-chart-area">
                <svg
                  ref={chartSvgRef}
                  className="zassk-spline-svg"
                  viewBox="0 0 460 150"
                  onMouseMove={handleChartMouseMove}
                >
                  {/* Curtain Lines (High-density vertical lines under the spline) */}
                  {curtainLines.map((line) => (
                    <line
                      key={line.id}
                      x1={line.x}
                      y1={line.yTop}
                      x2={line.x}
                      y2={line.yBottom}
                      stroke="#DBEAFE"
                      strokeWidth={1.2}
                      strokeOpacity={0.7}
                    />
                  ))}

                  {/* Smooth Curved Spline */}
                  <path
                    d={`M ${splinePoints.map((p, i) => {
                      if (i === 0) return `${p.x} ${p.y}`;
                      const prev = splinePoints[i - 1];
                      const cpX1 = prev.x + (p.x - prev.x) / 2;
                      const cpX2 = prev.x + (p.x - prev.x) / 2;
                      return `C ${cpX1} ${prev.y}, ${cpX2} ${p.y}, ${p.x} ${p.y}`;
                    }).join(' ')}`}
                    fill="none"
                    stroke="#2563EB"
                    strokeWidth={2.5}
                  />

                  {/* Active Pinpoint Ring */}
                  {activePointCoord && (
                    <g className="zassk-pinpoint-ring">
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
                      left: `${(activePointCoord.x / 460) * 100}%`,
                      top: `${(activePointCoord.y / 150) * 100}%`,
                    }}
                  >
                    Revenue ${activePointCoord.revenue}
                  </div>
                )}
              </div>
            </div>

            {/* X-Axis Day Labels */}
            <div className="zassk-x-axis">
              {mockTotalRevenue.points.map((p, idx) => (
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

          {/* Right: User Source Card */}
          <div className="zassk-card zassk-source-card">
            <div>
              <div className="zassk-card-header">
                <div>
                  <span className="zassk-card-title">User Source</span>
                  <div style={{ fontSize: '12px', color: '#64748B', fontWeight: 500, marginTop: '2px' }}>
                    Total 12k+
                  </div>
                </div>
                <button className="zassk-action-pill-btn" aria-label="Filter Sources">
                  <LucideIcon name="SlidersHorizontal" size={15} strokeWidth={2} />
                </button>
              </div>

              <div className="zassk-source-list">
                {mockUserSources.map((source) => (
                  <div key={source.id} className="zassk-source-row">
                    {/* Brand Icon */}
                    <div className="zassk-brand-icon">
                      {source.brand === 'google' && (
                        <svg width="22" height="22" viewBox="0 0 24 24">
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
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="#0F172A">
                          <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
                        </svg>
                      )}
                      {source.brand === 'instagram' && (
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#E1306C" strokeWidth="2">
                          <rect width="20" height="20" x="2" y="2" rx="5" ry="5" />
                          <path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z" />
                          <line x1="17.5" x2="17.51" y1="6.5" y2="6.5" />
                        </svg>
                      )}
                    </div>

                    {/* Striped Track & Gradient Pill */}
                    <div className="zassk-brand-track">
                      <div
                        className="zassk-brand-capsule"
                        style={{
                          width: `${source.percentageWidth}%`,
                          background: source.gradient,
                        }}
                      >
                        <span>{source.domain}</span>
                        <div className="zassk-count-pill">{source.count}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── BOTTOM ROW: USERS TABLE & TRANSACTIONS ── */}
        <div className="zassk-bottom-row">
          {/* Left: Recent Joining User Table */}
          <div className="zassk-card zassk-table-card">
            <div className="zassk-card-header">
              <span className="zassk-card-title">Recent Joining User</span>
              <button className="zassk-action-pill-btn" aria-label="Filter Users">
                <LucideIcon name="SlidersHorizontal" size={15} strokeWidth={2} />
              </button>
            </div>

            <table className="zassk-table">
              <thead>
                <tr>
                  <th style={{ width: '40px' }}>
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

          {/* Right: Recent Transactions */}
          <div className="zassk-card zassk-trans-card">
            <div className="zassk-card-header">
              <span className="zassk-card-title">Recent Transactions</span>
            </div>

            <div className="zassk-trans-list">
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
