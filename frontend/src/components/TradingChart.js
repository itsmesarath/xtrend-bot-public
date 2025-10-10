import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

const TradingChart = ({ symbol, data, volumeProfile, currentPrice }) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candleSeriesRef = useRef();
  const volumeSeriesRef = useRef();
  const priceLineRefs = useRef([]);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart with v4 API
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 450,
      layout: {
        backgroundColor: '#0f172a',
        textColor: '#94a3b8',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: '#334155',
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Add candlestick series - v4 API
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    candleSeriesRef.current = candleSeries;

    // Add volume series - v4 API
    const volumeSeries = chart.addHistogramSeries({
      color: '#334155',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: '',
      scaleMargins: {
        top: 0.8,
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chart) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chart) {
        chart.remove();
      }
    };
  }, []);

  // Update candle data
  useEffect(() => {
    if (!candleSeriesRef.current || !data || data.length === 0) return;

    const candleData = data.map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));

    const volumeData = data.map(candle => ({
      time: Math.floor(new Date(candle.timestamp).getTime() / 1000),
      value: candle.volume,
      color: candle.close >= candle.open ? '#10b981' : '#ef4444',
    }));

    candleSeriesRef.current.setData(candleData);
    volumeSeriesRef.current.setData(volumeData);
  }, [data]);

  // Draw volume profile levels
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !volumeProfile) return;

    // Remove old price lines
    priceLineRefs.current.forEach(line => {
      if (line && candleSeriesRef.current) {
        try {
          candleSeriesRef.current.removePriceLine(line);
        } catch (e) {
          // Line already removed
        }
      }
    });
    priceLineRefs.current = [];

    const series = candleSeriesRef.current;

    // Draw POC line
    if (volumeProfile.poc) {
      const pocLine = series.createPriceLine({
        price: volumeProfile.poc,
        color: '#06b6d4',
        lineWidth: 2,
        lineStyle: 0,
        axisLabelVisible: true,
        title: 'POC',
      });
      priceLineRefs.current.push(pocLine);
    }

    // Draw VAH line
    if (volumeProfile.vah) {
      const vahLine = series.createPriceLine({
        price: volumeProfile.vah,
        color: '#64748b',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'VAH',
      });
      priceLineRefs.current.push(vahLine);
    }

    // Draw VAL line
    if (volumeProfile.val) {
      const valLine = series.createPriceLine({
        price: volumeProfile.val,
        color: '#64748b',
        lineWidth: 1,
        lineStyle: 2,
        axisLabelVisible: true,
        title: 'VAL',
      });
      priceLineRefs.current.push(valLine);
    }

    // Draw LVN levels
    if (volumeProfile.levels) {
      const lvns = volumeProfile.levels.filter(l => l.is_lvn).slice(0, 3);
      lvns.forEach((lvn, idx) => {
        const lvnLine = series.createPriceLine({
          price: lvn.price,
          color: '#f97316',
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: `LVN${idx + 1}`,
        });
        priceLineRefs.current.push(lvnLine);
      });
    }

  }, [volumeProfile]);

  return (
    <div className="relative">
      <div ref={chartContainerRef} className="rounded-lg overflow-hidden border border-slate-700" />
      
      {/* Legend */}
      <div className="absolute top-4 left-4 bg-slate-800/80 backdrop-blur-sm p-3 rounded-lg border border-slate-700 text-xs space-y-1">
        <div className="font-semibold text-white mb-2">{symbol}</div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-cyan-500"></div>
          <span className="text-slate-300">POC - Point of Control</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-slate-500 border-t-2 border-dashed"></div>
          <span className="text-slate-300">VAH/VAL - Value Area</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-0.5 bg-orange-500 border-t-2 border-dashed"></div>
          <span className="text-slate-300">LVN - Low Volume Nodes</span>
        </div>
      </div>
    </div>
  );
};

export default TradingChart;
