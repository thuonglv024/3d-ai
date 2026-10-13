"use client";

import React, { useState, useMemo } from "react";
import {
  type ChartTimelinePoint,
  getSourceLabel,
  getModeLabel,
  formatScanDateTime,
  formatScanTime,
  formatScanDate,
} from "../../lib/userScansApi";
import { Info, Calendar, ExternalLink, Activity, Layers, X, Sparkles } from "lucide-react";
import Link from "next/link";

export type MetricKey = "chest_cm" | "waist_cm" | "hip_cm" | "shoulder_width_cm";

interface MetricConfig {
  key: MetricKey;
  label: string;
  color: string;
  fillColor: string;
  symbol: "circle" | "square" | "diamond" | "triangle";
  symbolChar: string;
}

export const METRIC_CONFIGS: Record<MetricKey, MetricConfig> = {
  chest_cm: {
    key: "chest_cm",
    label: "Vòng ngực",
    color: "#9E6D38", // Amber Gold, 5.2:1 contrast
    fillColor: "#F7F1E3",
    symbol: "circle",
    symbolChar: "●",
  },
  waist_cm: {
    key: "waist_cm",
    label: "Vòng eo",
    color: "#8F4A14", // Terracotta Brown, 6.1:1 contrast
    fillColor: "#FCEFE7",
    symbol: "square",
    symbolChar: "■",
  },
  hip_cm: {
    key: "hip_cm",
    label: "Vòng mông",
    color: "#1A5B80", // Slate Navy, 5.8:1 contrast
    fillColor: "#EBF3F8",
    symbol: "diamond",
    symbolChar: "◆",
  },
  shoulder_width_cm: {
    key: "shoulder_width_cm",
    label: "Rộng vai",
    color: "#196347", // Deep Emerald, 5.4:1 contrast
    fillColor: "#E9F5EF",
    symbol: "triangle",
    symbolChar: "▲",
  },
};

interface BodyChartProps {
  timeline: ChartTimelinePoint[];
  range: "30d" | "90d" | "all";
  onRangeChange: (range: "30d" | "90d" | "all") => void;
  onSelectScan?: (scanId: string) => void;
  disclaimer?: string;
}

interface TooltipInfo {
  x: number;
  y: number;
  scanId: string;
  capturedAt: string;
  captureMode: string;
  metricKey: MetricKey;
  metricLabel: string;
  valueCm: number;
  source: string;
  color: string;
}

export default function BodyChart({
  timeline,
  range,
  onRangeChange,
  onSelectScan,
  disclaimer = "Số đo là ước lượng. Tư thế, trang phục và điều kiện chụp có thể ảnh hưởng đến kết quả.",
}: BodyChartProps) {
  const [selectedMetrics, setSelectedMetrics] = useState<Record<MetricKey, boolean>>({
    chest_cm: true,
    waist_cm: true,
    hip_cm: true,
    shoulder_width_cm: true,
  });

  const [activeTooltip, setActiveTooltip] = useState<TooltipInfo | null>(null);
  const [showDataTable, setShowDataTable] = useState(false);

  const toggleMetric = (key: MetricKey) => {
    setSelectedMetrics((prev) => {
      const activeCount = Object.values(prev).filter(Boolean).length;
      if (prev[key] && activeCount <= 1) return prev; // Keep at least one active
      return { ...prev, [key]: !prev[key] };
    });
  };

  // Chronologically sorted points
  const sortedPoints = useMemo(() => {
    return [...timeline].sort((a, b) => new Date(a.captured_at).getTime() - new Date(b.captured_at).getTime());
  }, [timeline]);

  // Dimensions for SVG
  const width = 840;
  const height = 340;
  const padding = { top: 30, right: 30, bottom: 50, left: 55 };
  const chartInnerWidth = width - padding.left - padding.right;
  const chartInnerHeight = height - padding.top - padding.bottom;

  // Calculate Y min and max across all active and valid metrics
  const { minY, maxY, hasValidData } = useMemo(() => {
    let min = Infinity;
    let max = -Infinity;
    let count = 0;

    sortedPoints.forEach((p) => {
      (Object.keys(selectedMetrics) as MetricKey[]).forEach((mk) => {
        if (!selectedMetrics[mk]) return;
        const m = p.metrics?.[mk];
        if (m && m.valid_for_tracking && m.value !== null && !isNaN(m.value) && m.value > 0) {
          if (m.value < min) min = m.value;
          if (m.value > max) max = m.value;
          count++;
        }
      });
    });

    if (count === 0 || min === Infinity) {
      return { minY: 50, maxY: 120, hasValidData: false };
    }

    // Add 5cm padding around min and max
    const paddedMin = Math.max(30, Math.floor((min - 4) / 5) * 5);
    const paddedMax = Math.ceil((max + 4) / 5) * 5;
    return {
      minY: paddedMin,
      maxY: Math.max(paddedMin + 15, paddedMax),
      hasValidData: true,
    };
  }, [sortedPoints, selectedMetrics]);

  // Linear time-based X coordinate computation
  // x = padding.left + ((t - firstTime) / (lastTime - firstTime)) * chartInnerWidth
  // If span <= 0 or single point: centered at padding.left + chartInnerWidth / 2.
  const { xCoords, firstTime, lastTime, timeSpan } = useMemo(() => {
    const n = sortedPoints.length;
    if (n === 0) {
      return { xCoords: [], firstTime: 0, lastTime: 0, timeSpan: 0 };
    }
    const timestamps = sortedPoints.map((p) => new Date(p.captured_at).getTime());
    const minT = Math.min(...timestamps);
    const maxT = Math.max(...timestamps);
    const span = maxT - minT;

    if (span <= 0 || n === 1) {
      const mid = padding.left + chartInnerWidth / 2;
      return {
        xCoords: sortedPoints.map(() => mid),
        firstTime: minT,
        lastTime: maxT,
        timeSpan: 0,
      };
    }

    const coords = timestamps.map((t) => {
      const ratio = (t - minT) / span;
      return padding.left + ratio * chartInnerWidth;
    });

    return {
      xCoords: coords,
      firstTime: minT,
      lastTime: maxT,
      timeSpan: span,
    };
  }, [sortedPoints, chartInnerWidth, padding.left]);

  // Detect clusters: multiple scans with distance < 16px along the true linear X axis
  interface ScanCluster {
    id: string;
    centerX: number;
    scans: { point: ChartTimelinePoint; index: number; x: number }[];
  }

  const clusters = useMemo(() => {
    const result: ScanCluster[] = [];
    if (sortedPoints.length < 2) return result;

    let currentGroup: { point: ChartTimelinePoint; index: number; x: number }[] = [
      { point: sortedPoints[0], index: 0, x: xCoords[0] },
    ];

    for (let i = 1; i < sortedPoints.length; i++) {
      const prevX = currentGroup[currentGroup.length - 1].x;
      const currX = xCoords[i];

      // Points within 16px of each other belong to the same cluster
      if (currX - prevX < 16) {
        currentGroup.push({ point: sortedPoints[i], index: i, x: currX });
      } else {
        if (currentGroup.length > 1) {
          const avgX =
            currentGroup.reduce((sum, item) => sum + item.x, 0) / currentGroup.length;
          result.push({
            id: `cluster-${currentGroup[0].point.scan_id}`,
            centerX: avgX,
            scans: [...currentGroup],
          });
        }
        currentGroup = [{ point: sortedPoints[i], index: i, x: currX }];
      }
    }

    if (currentGroup.length > 1) {
      const avgX =
        currentGroup.reduce((sum, item) => sum + item.x, 0) / currentGroup.length;
      result.push({
        id: `cluster-${currentGroup[0].point.scan_id}`,
        centerX: avgX,
        scans: [...currentGroup],
      });
    }

    return result;
  }, [sortedPoints, xCoords]);

  // Quick lookup to see if a scan belongs to a cluster
  const clusterByScanId = useMemo(() => {
    const map = new Map<string, ScanCluster>();
    clusters.forEach((c) => {
      c.scans.forEach((s) => map.set(s.point.scan_id, c));
    });
    return map;
  }, [clusters]);

  const [activeCluster, setActiveCluster] = useState<ScanCluster | null>(null);

  const getYCoord = (val: number) => {
    if (maxY === minY) return padding.top + chartInnerHeight / 2;
    const ratio = (val - minY) / (maxY - minY);
    return padding.top + chartInnerHeight - ratio * chartInnerHeight;
  };

  // Y-axis ticks (4 to 6 ticks)
  const yTicks = useMemo(() => {
    const step = (maxY - minY) <= 20 ? 5 : 10;
    const ticks: number[] = [];
    for (let v = minY; v <= maxY; v += step) {
      ticks.push(v);
    }
    return ticks;
  }, [minY, maxY]);

  // Construct broken line paths for each metric
  // Strict honesty: If a point is null, NaN, <= 0, or template_model (e.g. mông ở chế độ upper_body),
  // we break the line segment cleanly. NEVER draw to 0, NEVER connect across unmeasured gaps.
  const metricPaths = useMemo(() => {
    const results: Record<
      MetricKey,
      {
        segments: { d: string; points: { x: number; y: number; p: ChartTimelinePoint; val: number; src: string }[] }[];
        allValidPoints: { x: number; y: number; p: ChartTimelinePoint; val: number; src: string }[];
      }
    > = {
      chest_cm: { segments: [], allValidPoints: [] },
      waist_cm: { segments: [], allValidPoints: [] },
      hip_cm: { segments: [], allValidPoints: [] },
      shoulder_width_cm: { segments: [], allValidPoints: [] },
    };

    (Object.keys(selectedMetrics) as MetricKey[]).forEach((mk) => {
      if (!selectedMetrics[mk]) return;

      const segments: { d: string; points: { x: number; y: number; p: ChartTimelinePoint; val: number; src: string }[] }[] = [];
      const allValid: { x: number; y: number; p: ChartTimelinePoint; val: number; src: string }[] = [];
      let currentSegment: { x: number; y: number; p: ChartTimelinePoint; val: number; src: string }[] = [];

      sortedPoints.forEach((p, idx) => {
        const m = p.metrics?.[mk];
        const isValid =
          m &&
          m.valid_for_tracking === true &&
          m.source !== "template_model" &&
          m.value !== null &&
          !isNaN(m.value) &&
          m.value > 0;

        if (isValid) {
          const pt = {
            x: xCoords[idx],
            y: getYCoord(m.value!),
            p,
            val: m.value!,
            src: m.source,
          };
          currentSegment.push(pt);
          allValid.push(pt);
        } else {
          // Break in data (null, invalid, or template_model)
          if (currentSegment.length > 0) {
            const d = currentSegment.reduce(
              (acc, pt, i) => (i === 0 ? `M ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}` : `${acc} L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`),
              ""
            );
            segments.push({ d, points: [...currentSegment] });
            currentSegment = [];
          }
        }
      });

      if (currentSegment.length > 0) {
        const d = currentSegment.reduce(
          (acc, pt, i) => (i === 0 ? `M ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}` : `${acc} L ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`),
          ""
        );
        segments.push({ d, points: [...currentSegment] });
      }

      results[mk] = { segments, allValidPoints: allValid };
    });

    return results;
  }, [sortedPoints, selectedMetrics, xCoords, minY, maxY]);

  // Render symbol shape in SVG for accessibility
  const renderSymbol = (
    symbol: "circle" | "square" | "diamond" | "triangle",
    x: number,
    y: number,
    color: string,
    size = 7
  ) => {
    switch (symbol) {
      case "circle":
        return <circle cx={x} cy={y} r={size - 1} fill="#FFFFFF" stroke={color} strokeWidth={2.5} />;
      case "square":
        return (
          <rect
            x={x - size + 1.5}
            y={y - size + 1.5}
            width={(size - 1.5) * 2}
            height={(size - 1.5) * 2}
            fill="#FFFFFF"
            stroke={color}
            strokeWidth={2.5}
          />
        );
      case "diamond":
        return (
          <polygon
            points={`${x},${y - size} ${x + size},${y} ${x},${y + size} ${x - size},${y}`}
            fill="#FFFFFF"
            stroke={color}
            strokeWidth={2.5}
          />
        );
      case "triangle":
        return (
          <polygon
            points={`${x},${y - size} ${x + size * 0.9},${y + size * 0.8} ${x - size * 0.9},${y + size * 0.8}`}
            fill="#FFFFFF"
            stroke={color}
            strokeWidth={2.5}
          />
        );
    }
  };

  return (
    <div className="body-chart-card">
      {/* Chart Header: Controls & Period Filter */}
      <div className="chart-header">
        <div className="chart-title-area">
          <div className="chart-title-badge">
            <Activity size={16} strokeWidth={2.5} />
            <span>Biểu đồ số đo theo thời gian</span>
          </div>
          <p className="chart-subtitle">
            Theo dõi xu hướng biến thiên số đo cơ thể thực tế qua các phiên scan hợp lệ.
          </p>
        </div>

        {/* Range Selector */}
        <div className="chart-range-group" role="group" aria-label="Khoảng thời gian lọc">
          {(["30d", "90d", "all"] as const).map((r) => (
            <button
              key={r}
              type="button"
              className={`range-pill ${range === r ? "is-active" : ""}`}
              onClick={() => onRangeChange(r)}
            >
              {r === "30d" ? "30 ngày" : r === "90d" ? "90 ngày" : "Toàn bộ"}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Filter Toggles (Accessible with distinct icons and colors) */}
      <div className="chart-metric-toggles" role="group" aria-label="Chọn số đo hiển thị">
        {(Object.keys(METRIC_CONFIGS) as MetricKey[]).map((mk) => {
          const cfg = METRIC_CONFIGS[mk];
          const isSelected = selectedMetrics[mk];
          return (
            <button
              key={mk}
              type="button"
              className={`metric-toggle-btn ${isSelected ? "is-active" : "is-inactive"}`}
              style={{
                borderColor: isSelected ? cfg.color : "var(--border)",
                backgroundColor: isSelected ? cfg.fillColor : "var(--surface-card)",
                color: isSelected ? cfg.color : "var(--text-muted)",
              }}
              onClick={() => toggleMetric(mk)}
              aria-pressed={isSelected}
            >
              <span className="metric-symbol-icon" aria-hidden="true" style={{ color: cfg.color }}>
                {cfg.symbolChar}
              </span>
              <span className="metric-name">{cfg.label}</span>
            </button>
          );
        })}
      </div>

      {/* SVG Canvas Area */}
      <div className="chart-canvas-wrapper" onMouseLeave={() => setActiveTooltip(null)}>
        {sortedPoints.length === 0 ? (
          <div className="chart-empty-state">
            <Calendar size={36} className="empty-icon" />
            <p className="empty-title">Không có dữ liệu trong khoảng thời gian này</p>
            <p className="empty-hint">Hãy chọn bộ lọc &quot;Toàn bộ&quot; hoặc thực hiện lần quét mới.</p>
          </div>
        ) : (
          <div className="svg-container">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="body-chart-svg"
              preserveAspectRatio="xMidYMid meet"
              role="img"
              aria-label="Biểu đồ số đo cơ thể theo thời gian"
            >
              <defs>
                {/* Horizontal grid lines */}
                <pattern id="grid-pattern" width="10" height="10" patternUnits="userSpaceOnUse">
                  <path d="M 10 0 L 0 0 0 10" fill="none" stroke="#EFE9DB" strokeWidth="0.5" />
                </pattern>
              </defs>

              {/* Background Chart Area */}
              <rect
                x={padding.left}
                y={padding.top}
                width={chartInnerWidth}
                height={chartInnerHeight}
                fill="#FCFAF7"
                rx={10}
              />

              {/* Y Grid Lines & Tick Labels */}
              {yTicks.map((tick) => {
                const y = getYCoord(tick);
                return (
                  <g key={`ytick-${tick}`}>
                    <line
                      x1={padding.left}
                      y1={y}
                      x2={padding.left + chartInnerWidth}
                      y2={y}
                      stroke="#E5DEC9"
                      strokeDasharray="3 3"
                      strokeWidth={1}
                    />
                    <text
                      x={padding.left - 10}
                      y={y + 4}
                      textAnchor="end"
                      fontSize="11"
                      fill="#8C8479"
                      fontFamily="Be Vietnam Pro, sans-serif"
                    >
                      {tick} cm
                    </text>
                  </g>
                );
              })}

              {/* X Axis Timestamps & Vertical Grid Lines (Non-overlapping) */}
              {xCoords.map((x, idx) => {
                const p = sortedPoints[idx];
                return (
                  <line
                    key={`x-grid-${p.scan_id}-${idx}`}
                    x1={x}
                    y1={padding.top}
                    x2={x}
                    y2={padding.top + chartInnerHeight}
                    stroke="#F0ECE1"
                    strokeWidth={1}
                  />
                );
              })}

              {/* Render spaced X-Axis Text Labels */}
              {(() => {
                if (sortedPoints.length === 0) return null;
                if (sortedPoints.length === 1 || timeSpan <= 0) {
                  const p = sortedPoints[0];
                  const midX = padding.left + chartInnerWidth / 2;
                  return (
                    <g key="x-axis-single">
                      <text
                        x={midX}
                        y={padding.top + chartInnerHeight + 18}
                        textAnchor="middle"
                        fontSize="11"
                        fontWeight={600}
                        fill="#26211A"
                        fontFamily="Be Vietnam Pro, sans-serif"
                      >
                        {formatScanDate(p.captured_at)}
                      </text>
                      <text
                        x={midX}
                        y={padding.top + chartInnerHeight + 32}
                        textAnchor="middle"
                        fontSize="10"
                        fill="#8C8479"
                        fontFamily="Be Vietnam Pro, sans-serif"
                      >
                        {formatScanTime(p.captured_at)}
                      </text>
                    </g>
                  );
                }

                // Filter labels so adjacent labels maintain at least 55px spacing
                const labelsToRender: { x: number; p: ChartTimelinePoint }[] = [];
                let lastRenderedX = -Infinity;

                sortedPoints.forEach((p, idx) => {
                  const x = xCoords[idx];
                  const isFirst = idx === 0;
                  const isLast = idx === sortedPoints.length - 1;

                  if (isFirst || x - lastRenderedX >= 55 || isLast) {
                    if (isLast && x - lastRenderedX < 45 && labelsToRender.length > 1) {
                      labelsToRender.pop();
                    }
                    labelsToRender.push({ x, p });
                    lastRenderedX = x;
                  }
                });

                return labelsToRender.map(({ x, p }, lIdx) => (
                  <g key={`x-label-${p.scan_id}-${lIdx}`}>
                    <text
                      x={x}
                      y={padding.top + chartInnerHeight + 18}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight={600}
                      fill="#26211A"
                      fontFamily="Be Vietnam Pro, sans-serif"
                    >
                      {formatScanDate(p.captured_at)}
                    </text>
                    <text
                      x={x}
                      y={padding.top + chartInnerHeight + 32}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#8C8479"
                      fontFamily="Be Vietnam Pro, sans-serif"
                    >
                      {formatScanTime(p.captured_at)}
                    </text>
                  </g>
                ));
              })()}

              {/* Single scan point or zero-span notice */}
              {sortedPoints.length === 1 && (
                <text
                  x={width / 2}
                  y={padding.top + 20}
                  textAnchor="middle"
                  fontSize="12"
                  fill="#5C564D"
                  fontFamily="Be Vietnam Pro, sans-serif"
                >
                  (1 lần scan duy nhất — Điểm số đo hiện tại, chưa có đường xu hướng lịch sử)
                </text>
              )}
              {sortedPoints.length > 1 && timeSpan <= 0 && (
                <text
                  x={width / 2}
                  y={padding.top + 20}
                  textAnchor="middle"
                  fontSize="12"
                  fill="#5C564D"
                  fontFamily="Be Vietnam Pro, sans-serif"
                >
                  (Các lần scan được chụp cùng thời điểm — Hiển thị điểm số đo độc lập)
                </text>
              )}

              {/* Metric Line Paths (True Linear Time, broken on missing / template data) */}
              {(Object.keys(METRIC_CONFIGS) as MetricKey[]).map((mk) => {
                if (!selectedMetrics[mk]) return null;
                const { segments } = metricPaths[mk];
                const cfg = METRIC_CONFIGS[mk];

                return segments.map((seg, segIdx) => (
                  <path
                    key={`line-${mk}-${segIdx}`}
                    d={seg.d}
                    fill="none"
                    stroke={cfg.color}
                    strokeWidth={2.6}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                ));
              })}

              {/* Cluster Badges: For scans close together (< 16px distance) */}
              {clusters.map((cluster) => {
                const isSelected = activeCluster?.id === cluster.id;
                const badgeY = padding.top + 14;

                return (
                  <g
                    key={`cluster-badge-${cluster.id}`}
                    className="chart-cluster-badge-group"
                    style={{ cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      setActiveCluster((prev) => (prev?.id === cluster.id ? null : cluster));
                      setActiveTooltip(null);
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`Cụm ${cluster.scans.length} lần scan chụp gần nhau`}
                  >
                    {/* Vertical dashed guideline through cluster center */}
                    <line
                      x1={cluster.centerX}
                      y1={padding.top}
                      x2={cluster.centerX}
                      y2={padding.top + chartInnerHeight}
                      stroke="#C6A15B"
                      strokeWidth={1.2}
                      strokeDasharray="3 3"
                      opacity={0.7}
                    />

                    {/* Badge Pill Background */}
                    <rect
                      x={cluster.centerX - 24}
                      y={badgeY - 10}
                      width={48}
                      height={20}
                      rx={10}
                      fill={isSelected ? "#C6A15B" : "#FAF5EB"}
                      stroke="#C6A15B"
                      strokeWidth={1.4}
                    />

                    {/* Overlapping double circle icon */}
                    <circle
                      cx={cluster.centerX - 13}
                      cy={badgeY}
                      r={3.5}
                      fill={isSelected ? "#FFFFFF" : "#C6A15B"}
                      opacity={0.8}
                    />
                    <circle
                      cx={cluster.centerX - 9}
                      cy={badgeY}
                      r={3.5}
                      fill={isSelected ? "#FFFFFF" : "#8F4A14"}
                      stroke={isSelected ? "#C6A15B" : "#FAF5EB"}
                      strokeWidth={1}
                    />

                    {/* Scan count text */}
                    <text
                      x={cluster.centerX + 5}
                      y={badgeY + 3.5}
                      textAnchor="middle"
                      fontSize="10"
                      fontWeight="700"
                      fill={isSelected ? "#FFFFFF" : "#4A3B2C"}
                      fontFamily="Be Vietnam Pro, sans-serif"
                    >
                      {cluster.scans.length}
                    </text>
                  </g>
                );
              })}

              {/* Data Points Interactive Circles / Symbols */}
              {(Object.keys(METRIC_CONFIGS) as MetricKey[]).map((mk) => {
                if (!selectedMetrics[mk]) return null;
                const { allValidPoints } = metricPaths[mk];
                const cfg = METRIC_CONFIGS[mk];

                return allValidPoints.map((pt, ptIdx) => {
                  const isHovered =
                    activeTooltip?.scanId === pt.p.scan_id && activeTooltip?.metricKey === mk;
                  const cluster = clusterByScanId.get(pt.p.scan_id);

                  return (
                    <g
                      key={`pt-${mk}-${pt.p.scan_id}-${ptIdx}`}
                      className="chart-interactive-point"
                      style={{ cursor: "pointer" }}
                      tabIndex={0}
                      role="button"
                      aria-label={`${cfg.label}: ${pt.val} cm ngày ${formatScanDateTime(pt.p.captured_at)}${
                        cluster ? ` (thuộc cụm ${cluster.scans.length} lần scan)` : ""
                      }`}
                      onMouseEnter={() => {
                        if (cluster) {
                          // If in a cluster, activate cluster view for clarity
                          setActiveCluster(cluster);
                        }
                        setActiveTooltip({
                          x: pt.x,
                          y: pt.y,
                          scanId: pt.p.scan_id,
                          capturedAt: pt.p.captured_at,
                          captureMode: pt.p.capture_mode,
                          metricKey: mk,
                          metricLabel: cfg.label,
                          valueCm: pt.val,
                          source: pt.src,
                          color: cfg.color,
                        });
                      }}
                      onClick={() => {
                        if (cluster) {
                          setActiveCluster(cluster);
                        } else if (onSelectScan) {
                          onSelectScan(pt.p.scan_id);
                        }
                      }}
                    >
                      {/* Generous invisible touch target */}
                      <circle cx={pt.x} cy={pt.y} r={16} fill="transparent" />

                      {/* Visual symbol icon */}
                      {renderSymbol(cfg.symbol, pt.x, pt.y, cfg.color, isHovered ? 9 : 7)}
                    </g>
                  );
                });
              })}
            </svg>

            {/* Cluster Selection Popover: Appears when clicking/hovering a cluster marker or cluster point */}
            {activeCluster && (
              <div
                className="chart-cluster-popover"
                style={{
                  left: `${Math.min(80, Math.max(20, (activeCluster.centerX / width) * 100))}%`,
                  top: `${Math.max(6, (padding.top / height) * 100)}%`,
                }}
              >
                <div className="cluster-popover-header">
                  <div className="cluster-header-title">
                    <Layers size={14} className="cluster-icon" />
                    <strong>Cụm {activeCluster.scans.length} lần scan chụp gần nhau</strong>
                  </div>
                  <button
                    type="button"
                    className="cluster-close-btn"
                    onClick={() => setActiveCluster(null)}
                    aria-label="Đóng bảng chọn lần scan"
                  >
                    <X size={14} />
                  </button>
                </div>

                <p className="cluster-popover-note">
                  Các lần scan dưới đây diễn ra sát thời gian (&lt; 16px trên đồ thị). Chọn lần scan cụ thể để xem số đo:
                </p>

                <div className="cluster-scans-list">
                  {activeCluster.scans.map(({ point: p }) => (
                    <div key={`cluster-item-${p.scan_id}`} className="cluster-scan-item">
                      <div className="cluster-item-meta">
                        <span className="cluster-item-time">{formatScanTime(p.captured_at)}</span>
                        <span className="cluster-item-date">{formatScanDate(p.captured_at)}</span>
                        <span className="cluster-item-mode">{getModeLabel(p.capture_mode)}</span>
                      </div>

                      <div className="cluster-item-measurements">
                        {p.metrics?.chest_cm?.value && (
                          <span className="meas-chip">
                            Ngực: <strong>{p.metrics.chest_cm.value} cm</strong>
                          </span>
                        )}
                        {p.metrics?.waist_cm?.value && (
                          <span className="meas-chip">
                            Eo: <strong>{p.metrics.waist_cm.value} cm</strong>
                          </span>
                        )}
                        {p.metrics?.hip_cm?.value && p.metrics.hip_cm.valid_for_tracking && (
                          <span className="meas-chip">
                            Mông: <strong>{p.metrics.hip_cm.value} cm</strong>
                          </span>
                        )}
                        {p.metrics?.shoulder_width_cm?.value && (
                          <span className="meas-chip">
                            Vai: <strong>{p.metrics.shoulder_width_cm.value} cm</strong>
                          </span>
                        )}
                      </div>

                      <div className="cluster-item-action">
                        {onSelectScan ? (
                          <button
                            type="button"
                            className="cluster-scan-select-btn"
                            onClick={() => {
                              setActiveCluster(null);
                              onSelectScan(p.scan_id);
                            }}
                          >
                            Xem chi tiết <ExternalLink size={11} />
                          </button>
                        ) : (
                          <Link
                            href={`/account/body-profile/scans/${p.scan_id}`}
                            className="cluster-scan-select-btn"
                            onClick={() => setActiveCluster(null)}
                          >
                            Xem chi tiết <ExternalLink size={11} />
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Interactive Tooltip Card Floating on Chart (Single Point) */}
            {activeTooltip && !activeCluster && (
              <div
                className="chart-floating-tooltip"
                style={{
                  left: `${(activeTooltip.x / width) * 100}%`,
                  top: `${Math.max(10, (activeTooltip.y / height) * 100 - 15)}%`,
                }}
              >
                <div className="tooltip-header">
                  <span className="tooltip-time">{formatScanDateTime(activeTooltip.capturedAt)}</span>
                  <span className="tooltip-mode-badge">{getModeLabel(activeTooltip.captureMode)}</span>
                </div>
                <div className="tooltip-body">
                  <span className="tooltip-metric" style={{ color: activeTooltip.color }}>
                    {activeTooltip.metricLabel}:
                  </span>
                  <span className="tooltip-value">{activeTooltip.valueCm} cm</span>
                </div>
                <div className="tooltip-source">
                  <span>Nguồn: </span>
                  <strong>{getSourceLabel(activeTooltip.source)}</strong>
                </div>
                {onSelectScan && (
                  <button
                    type="button"
                    className="tooltip-action-btn"
                    onClick={() => onSelectScan(activeTooltip.scanId)}
                  >
                    Xem chi tiết lần scan <ExternalLink size={12} />
                  </button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Mandatory Disclaimer Note */}
      <div className="chart-disclaimer-bar">
        <Info size={16} className="disclaimer-icon" />
        <span className="disclaimer-text">{disclaimer}</span>
      </div>

      {/* Accessible Data Table Toggle */}
      <div className="chart-table-toggle-row">
        <button
          type="button"
          className="table-toggle-btn"
          onClick={() => setShowDataTable((prev) => !prev)}
          aria-expanded={showDataTable}
        >
          {showDataTable ? "Ẩn bảng dữ liệu số đo ▲" : "Xem bảng số đo chi tiết bên dưới ▼"}
        </button>
      </div>

      {/* Accessible Equivalent Data Table */}
      {showDataTable && (
        <div className="chart-data-table-container">
          <table className="chart-data-table">
            <caption className="sr-only">Bảng chi tiết số đo các lần scan theo thời gian</caption>
            <thead>
              <tr>
                <th scope="col">Ngày & Giờ</th>
                <th scope="col">Chế độ</th>
                <th scope="col">Ngực (cm)</th>
                <th scope="col">Eo (cm)</th>
                <th scope="col">Mông (cm)</th>
                <th scope="col">Rộng vai (cm)</th>
                <th scope="col">Hành động</th>
              </tr>
            </thead>
            <tbody>
              {sortedPoints.map((p) => {
                const chest = p.metrics?.chest_cm;
                const waist = p.metrics?.waist_cm;
                const hip = p.metrics?.hip_cm;
                const shoulder = p.metrics?.shoulder_width_cm;

                return (
                  <tr key={`tbl-row-${p.scan_id}`}>
                    <td className="cell-datetime">{formatScanDateTime(p.captured_at)}</td>
                    <td>
                      <span className="mode-pill">{getModeLabel(p.capture_mode)}</span>
                    </td>
                    <td>
                      {chest && chest.valid_for_tracking && chest.value !== null ? (
                        <span>
                          <strong>{chest.value}</strong>{" "}
                          <small className="src-hint">({getSourceLabel(chest.source)})</small>
                        </span>
                      ) : (
                        <span className="text-muted">--</span>
                      )}
                    </td>
                    <td>
                      {waist && waist.valid_for_tracking && waist.value !== null ? (
                        <span>
                          <strong>{waist.value}</strong>{" "}
                          <small className="src-hint">({getSourceLabel(waist.source)})</small>
                        </span>
                      ) : (
                        <span className="text-muted">--</span>
                      )}
                    </td>
                    <td>
                      {hip && hip.valid_for_tracking && hip.value !== null ? (
                        <span>
                          <strong>{hip.value}</strong>{" "}
                          <small className="src-hint">({getSourceLabel(hip.source)})</small>
                        </span>
                      ) : (
                        <span className="text-muted" title={hip?.source === "template_model" ? "Theo mẫu 3D — không dùng theo dõi" : "Chưa đo"}>
                          {hip?.source === "template_model" ? "Mẫu 3D" : "--"}
                        </span>
                      )}
                    </td>
                    <td>
                      {shoulder && shoulder.valid_for_tracking && shoulder.value !== null ? (
                        <span>
                          <strong>{shoulder.value}</strong>{" "}
                          <small className="src-hint">({getSourceLabel(shoulder.source)})</small>
                        </span>
                      ) : (
                        <span className="text-muted">--</span>
                      )}
                    </td>
                    <td>
                      <Link
                        href={`/account/body-profile/scans/${p.scan_id}`}
                        className="tbl-action-link"
                      >
                        Chi tiết <ExternalLink size={12} />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
