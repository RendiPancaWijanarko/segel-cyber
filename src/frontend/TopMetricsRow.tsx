import React from 'react';
import { ArrowUpRight } from 'lucide-react';

export const TopMetricsRow: React.FC = () => {
  return (
    <div className="w-full flex items-stretch gap-4 max-w-[1020px] mx-auto select-none">
      
      {/* ========================================================
          COLUMN 1: TOTAL RESPONSES (Full Height 256px)
          ======================================================== */}
      <div 
        className="relative bg-white rounded-b-[24px] rounded-tl-[24px] shadow-[0_12px_32px_-4px_rgba(70,100,60,0.08),0_4px_12px_rgba(0,0,0,0.02)] w-[310px] h-[256px] flex flex-col justify-between p-5 flex-shrink-0"
        style={{
          /* Folder tab on top-left */
          clipPath: 'polygon(0 0, 130px 0, 146px 14px, 100% 14px, 100% 100%, 0 100%)'
        }}
      >
        <span className="text-[14px] font-semibold text-[#0F172A] mt-1">Total Responses</span>

        {/* Centered Symmetrical 14-Tick Arc Gauge */}
        <div className="relative w-[220px] h-[140px] mx-auto mb-2 flex items-center justify-center">
          <svg className="w-full h-full overflow-visible" viewBox="0 0 220 140">
            {Array.from({ length: 14 }).map((_, i) => {
              // Clockwise from 180° (Left) to 0° (Right)
              const angleDeg = 180 - i * (180 / 13);
              const angleRad = (angleDeg * Math.PI) / 180;
              const cx = 110;
              const cy = 120;
              const rInner = 68;
              const rOuter = 92;

              const x1 = cx + rInner * Math.cos(angleRad);
              const y1 = cy - rInner * Math.sin(angleRad);
              const x2 = cx + rOuter * Math.cos(angleRad);
              const y2 = cy - rOuter * Math.sin(angleRad);

              // Strict Left-to-Right Color Sequence
              let strokeColor = '#E2E8F0';
              if (i < 5) strokeColor = '#2563EB';       // Deep Royal Blue
              else if (i < 8) strokeColor = '#3B82F6';  // Bright Sky Blue
              else if (i < 10) strokeColor = '#60A5FA'; // Light Blue
              else if (i < 12) strokeColor = '#BAE6FD'; // Pale Ice Blue

              return (
                <line
                  key={i}
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={strokeColor}
                  strokeWidth="7"
                  strokeLinecap="round"
                />
              );
            })}
          </svg>

          {/* Center Readout */}
          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 text-center pointer-events-none">
            <div className="text-[28px] font-bold text-[#0F172A] leading-none">98%</div>
            <div className="text-[12.5px] font-medium text-[#64748B] mt-1 whitespace-nowrap">Responses rate</div>
          </div>
        </div>
      </div>

      {/* ========================================================
          COLUMN 2: INTERLOCKING TOTAL PROFIT + ACTIVE USERS (256px)
          ======================================================== */}
      <div className="relative bg-white rounded-[24px] shadow-[0_12px_32px_-4px_rgba(70,100,60,0.08),0_4px_12px_rgba(0,0,0,0.02)] w-[330px] h-[256px] flex flex-col justify-between p-5 flex-shrink-0 overflow-hidden">
        
        {/* Top Half: Total Profit */}
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[14px] font-semibold text-[#0F172A]">Total Profit</span>
            <button className="w-8 h-8 rounded-full bg-[#F8FAFC] flex items-center justify-center text-[#475569] hover:bg-slate-100 transition-colors">
              <ArrowUpRight className="w-4 h-4"/>
            </button>
          </div>

          <div className="flex items-end justify-between mt-2">
            <div className="text-[28px] font-bold text-[#0F172A] leading-none">$63k</div>
            {/* 9-bar Mini Histogram */}
            <div className="flex items-end gap-[3px] mb-1 pr-1">
              {[8, 14, 12, 18, 26, 12, 10, 15, 10].map((h, i) => (
                <span
                  key={i}
                  className="w-[4px] rounded-[2px]"
                  style={{
                    height: `${h}px`,
                    backgroundColor: i >= 3 && i <= 5 ? '#2563EB' : '#93C5FD'
                  }}
                />
              ))}
            </div>
          </div>
        </div>

        {/* The Stepped Contour Bridge (Decorative Sub-Surface) */}
        <div className="w-full flex items-center justify-end my-1">
          <div className="w-[55%] h-[2px] bg-slate-100 rounded-full" />
        </div>

        {/* Bottom Half: Active Users */}
        <div>
          <div className="flex items-center justify-between">
            <span className="text-[14px] font-semibold text-[#0F172A]">Active Users</span>
            <div className="flex items-center gap-2 text-[12px] font-semibold text-[#64748B]">
              <span>75%</span>
              <span className="text-slate-300">|</span>
              <span>25%</span>
              <span className="text-slate-300">|</span>
              <span>10%</span>
            </div>
          </div>

          <div className="text-[28px] font-bold text-[#0F172A] leading-none mt-2">150</div>

          {/* 3-Segment Progress Bar */}
          <div className="h-[20px] w-full rounded-full bg-[#F1F5F9] flex overflow-hidden p-[2px] mt-2.5">
            {/* Segment 1: Dense Blue Vertical Lines (75%) */}
            <div 
              className="h-full rounded-l-full bg-[#3B82F6]" 
              style={{
                width: '68%',
                backgroundImage: 'repeating-linear-gradient(90deg, #FFFFFF, #FFFFFF 1.5px, transparent 1.5px, transparent 3.5px)'
              }}
            />
            {/* Segment 2: Diagonal Crosshatch (25%) */}
            <div 
              className="h-full bg-[#60A5FA]" 
              style={{
                width: '24%',
                backgroundImage: 'repeating-linear-gradient(45deg, #FFFFFF, #FFFFFF 1.5px, transparent 1.5px, transparent 5px)'
              }}
            />
            {/* Segment 3: Light Muted Gray (10%) */}
            <div className="h-full bg-[#E2E8F0] rounded-r-full" style={{ width: '8%' }} />
          </div>
        </div>
      </div>

      {/* ========================================================
          COLUMN 3: CONVERSION RATE + ENDED TASK (2 x 120px + 16px gap = 256px)
          ======================================================== */}
      <div className="flex flex-col justify-between w-[290px] h-[256px] flex-shrink-0">
        
        {/* Conversion Rate Card (120px) */}
        <div className="bg-white rounded-[24px] p-5 shadow-[0_12px_32px_-4px_rgba(70,100,60,0.08),0_4px_12px_rgba(0,0,0,0.02)] flex flex-col justify-between h-[120px]">
          <div className="flex items-center justify-between">
            <span className="text-[14px] font-semibold text-[#0F172A]">Conversion Rate</span>
            <button className="w-8 h-8 rounded-full bg-[#F8FAFC] flex items-center justify-center text-[#475569] hover:bg-slate-100 transition-colors">
              <ArrowUpRight className="w-4 h-4"/>
            </button>
          </div>
          <div className="text-[28px] font-bold text-[#0F172A] leading-none">75%</div>
          
          {/* 32 Vertical Ticks */}
          <div className="flex items-center gap-[2px] mt-1">
            {Array.from({ length: 32 }).map((_, i) => (
              <span
                key={i}
                className="w-[3px] h-[14px] rounded-[1.5px]"
                style={{ backgroundColor: i < 24 ? '#2563EB' : '#E2E8F0' }}
              />
            ))}
          </div>
        </div>

        {/* Ended Task Card (120px) */}
        <div className="bg-white rounded-[24px] p-5 shadow-[0_12px_32px_-4px_rgba(70,100,60,0.08),0_4px_12px_rgba(0,0,0,0.02)] flex items-center justify-between h-[120px]">
          <div>
            <span className="text-[14px] font-semibold text-[#0F172A]">Ended Task</span>
            <div className="text-[28px] font-bold text-[#0F172A] leading-none mt-2">80</div>
          </div>

          {/* Dot Matrix: 4 Rows x 12 Cols */}
          <div className="grid grid-cols-12 gap-[3px] self-center">
            {Array.from({ length: 48 }).map((_, i) => {
              const row = Math.floor(i / 12);
              const col = i % 12;
              // Ascending diagonal blue progress dots
              const isBlue =
                (row === 3 && (col === 4 || col === 5)) ||
                (row === 2 && (col === 6 || col === 7)) ||
                (row === 1 && (col === 8 || col === 9 || col === 10)) ||
                (row === 0 && (col === 9 || col === 10 || col === 11));
              return (
                <span
                  key={i}
                  className={`rounded-full transition-all ${
                    isBlue
                      ? 'w-[6px] h-[6px] bg-[#2563EB]'
                      : 'w-[4px] h-[4px] bg-[#E2E8F0] m-[1px]'
                  }`}
                />
              );
            })}
          </div>
        </div>

      </div>

    </div>
  );
};
