// SPDX-License-Identifier: MIT
/**
 * SEGEL Official Design System Tokens
 * Derived strictly from the TypeGPU/WebGPU anisotropic lit rays shader:
 * - 60% Dominant: TNI AD Military Sage Green & Crisp Military Canvas
 * - 30% Secondary: Tactical Warm Sand & Bronze Gold
 * - 10% Accent: Tactical Field Green, Luminous Mint Glow & Triadic Iridescent Lavender
 */

export const SEGEL_PALETTE = {
  // ── 1. 60% Dominant Foundation (TNI AD Sage & Military Canvas) ──
  canvas: {
    bg: '#F2F7F0',          // vec3f(0.948, 0.970, 0.942) - Clean military white-sage
    surface: '#FFFFFF',     // Pure white card elevation
    elevated: 'rgba(255, 255, 255, 0.85)', // Frosted glass navigation & floating pods
    border: 'rgba(122, 158, 107, 0.22)',   // Soft sage boundary
    shadow: '0 12px 32px -4px rgba(60, 90, 55, 0.08), 0 4px 12px rgba(0, 0, 0, 0.02)',
  },
  sage: {
    soft: '#B8D2AD',        // vec3f(0.720, 0.825, 0.680) - TNI AD Sage Green
    deep: '#7A9E6B',        // vec3f(0.480, 0.620, 0.420) - Tactical Midtone Sage
    tactical: '#3B7A32',    // Saturated Field Green for primary emphasis
    darkForest: '#24531E',  // Deep tactical green for pressed/active states
  },
  typography: {
    primary: '#0F172A',     // High contrast dark tactical slate
    secondary: '#334155',   // Subheaders & key labels
    muted: '#64748B',       // Descriptive captions & inactive legends
    subtle: '#52664D',      // Sage-tinted muted text
  },

  // ── 2. 30% Secondary System (Tactical Warm Sand & Bronze Gold) ──
  sand: {
    gold: '#D1BD99',        // vec3f(0.820, 0.740, 0.600) - Warm Sand / Bronze
    amber: '#C7B08A',       // Warm amber sheen on folds & tracks
    bronze: '#8C734B',      // Darker bronze for secondary badges & icons
    subtle: '#F7F4EC',      // Soft champagne pill backgrounds
    border: '#E8DFD0',      // Warm panel separator
  },

  // ── 3. 10% Accent System (Luminous Mint Flare & Triadic Lavender) ──
  accent: {
    mintGlow: '#EBFCF2',    // vec3f(0.920, 0.990, 0.950) - Luminous Mint Glow
    mintActive: '#10B981',  // Saturated emerald mint
    lavender: '#D9CFED',    // vec3f(0.850, 0.810, 0.930) - Triadic Iridescent Accent
    violetFlare: '#8B5CF6', // High-intensity triadic specular peak
    violetDeep: '#7C3AED',  // Active violet highlight
  },

  // ── 4. Semantic Status Colors (Preserved for Usability & Conventions) ──
  semantic: {
    success: '#15803D',
    successBg: '#EBFCF2',
    successBorder: '#B8D2AD',
    warning: '#B45309',
    warningBg: '#FEF3C7',
    warningBorder: '#D1BD99',
    error: '#B91C1C',
    errorBg: '#FEF2F2',
    errorBorder: '#FECACA',
    info: '#3B7A32',
    infoBg: '#F2F7F0',
    infoBorder: '#B8D2AD',
  },
} as const;

export type SegelPalette = typeof SEGEL_PALETTE;
