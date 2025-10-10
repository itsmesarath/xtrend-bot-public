import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const TradingChart = ({ symbol, data, volumeProfile, currentPrice }) => {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candleSeriesRef = useRef();
  const volumeSeriesRef = useRef();
  const priceLineRefs = useRef([]);
  const [timeframe, setTimeframe] = useState('1m');
  const [isFullscreen, setIsFullscreen] = useState(false);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Create chart with v4 API - TradingView style
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: isFullscreen ? window.innerHeight * 0.8 : 500,
      layout: {
        backgroundColor: '#0f172a',
        textColor: '#94a3b8',
        fontSize: 12,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      },
      grid: {
        vertLines: { 
          color: '#1e293b',
          style: 1,
        },
        horzLines: { 
          color: '#1e293b',
          style: 1,
        },
      },
      crosshair: {
        mode: 1,
        vertLine: {
          color: '#64748b',
          width: 1,
          style: 2,
          labelBackgroundColor: '#334155',
        },
        horzLine: {
          color: '#64748b',
          width: 1,
          style: 2,
          labelBackgroundColor: '#334155',
        },
      },
      rightPriceScale: {
        borderColor: '#334155',
        scaleMargins: {
          top: 0.1,
          bottom: 0.2,
        },
      },
      timeScale: {
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 12,
        barSpacing: 6,
        minBarSpacing: 3,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
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

    // Add volume series - v4 API in separate pane
    const volumeSeries = chart.addHistogramSeries({
      color: '#334155',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
      scaleMargins: {
        top: 0.7,  // Volume takes bottom 30% of chart
        bottom: 0,
      },
    });

    volumeSeriesRef.current = volumeSeries;
    
    // Create separate price scale for volume
    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.7,
        bottom: 0,
      },
    });

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
      if (chartRef.current) {
        try {
          chartRef.current.remove();
          chartRef.current = null;
        } catch (e) {
          // Chart already disposed
        }
      }
    };
  }, [timeframe, isFullscreen]);

  // Update candle data with better handling
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !data || data.length === 0) return;

    try {
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
        color: candle.close >= candle.open ? '#10b98150' : '#ef444450',  // Semi-transparent
      }));

      candleSeriesRef.current.setData(candleData);
      volumeSeriesRef.current.setData(volumeData);
      
      // Auto-fit content
      if (chartRef.current) {
        chartRef.current.timeScale().fitContent();
      }
    } catch (error) {
      console.error('Error updating chart data:', error);
    }
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
      {/* Chart Controls - TradingView Style */}
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        {/* Symbol Badge */}
        <Badge className="bg-slate-800/90 backdrop-blur-sm border-slate-700 text-white px-3 py-1.5 text-sm font-semibold">
          {symbol}
        </Badge>
        
        {/* Timeframe Selector */}
        <div className="flex items-center gap-1 bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg p-1">
          {['1m', '5m', '15m', '1h'].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 text-xs rounded transition-all ${
                timeframe === tf
                  ? 'bg-cyan-500 text-white font-semibold'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
              data-testid={`timeframe-${tf}`}
            >
              {tf}
            </button>
          ))}
        </div>

        {/* Price Info */}
        {data && data.length > 0 && (
          <div className="bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg px-3 py-1.5 text-xs">
            <span className="text-slate-400">Price: </span>
            <span className="text-white font-semibold">${data[data.length - 1]?.close?.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Chart Container */}
      <div ref={chartContainerRef} className="rounded-lg overflow-hidden border border-slate-700" style={{ height: isFullscreen ? '80vh' : '600px' }} />
      
      {/* Legend - Bottom Left */}
      <div className="absolute bottom-4 left-4 bg-slate-800/80 backdrop-blur-sm p-3 rounded-lg border border-slate-700 text-xs space-y-1.5">
        <div className="font-semibold text-cyan-400 mb-2 text-sm">Volume Profile Levels</div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-cyan-500"></div>
          <span className="text-slate-300">POC</span>
          {volumeProfile?.poc && (
            <span className="text-slate-400 ml-1">${volumeProfile.poc.toFixed(2)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-slate-500 border-t border-dashed"></div>
          <span className="text-slate-300">VAH</span>
          {volumeProfile?.vah && (
            <span className="text-slate-400 ml-1">${volumeProfile.vah.toFixed(2)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-slate-500 border-t border-dashed"></div>
          <span className="text-slate-300">VAL</span>
          {volumeProfile?.val && (
            <span className="text-slate-400 ml-1">${volumeProfile.val.toFixed(2)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 bg-orange-500 border-t border-dashed"></div>
          <span className="text-slate-300">LVN</span>
          <span className="text-slate-400 ml-1">Low Volume</span>
        </div>
      </div>

      {/* Chart Info - Top Right */}
      {data && data.length > 0 && (
        <div className="absolute top-3 right-3 z-10 bg-slate-800/90 backdrop-blur-sm border border-slate-700 rounded-lg p-3 text-xs space-y-1">
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">O</span>
            <span className="text-white font-mono">${data[data.length - 1]?.open?.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">H</span>
            <span className="text-emerald-400 font-mono">${data[data.length - 1]?.high?.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">L</span>
            <span className="text-red-400 font-mono">${data[data.length - 1]?.low?.toFixed(2)}</span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">C</span>
            <span className={`font-mono font-semibold ${
              data[data.length - 1]?.close >= data[data.length - 1]?.open ? 'text-emerald-400' : 'text-red-400'
            }`}>
              ${data[data.length - 1]?.close?.toFixed(2)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default TradingChart;
