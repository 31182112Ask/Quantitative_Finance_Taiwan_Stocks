import { useEffect, useRef } from 'react';
import {
  CandlestickSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type IPriceLine,
  type SeriesMarker,
  type UTCTimestamp,
} from 'lightweight-charts';
import type { MarketSnapshot } from '../types';

interface MarketChartProps {
  snapshot: MarketSnapshot;
}

export function MarketChart({ snapshot }: MarketChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const snapshotRef = useRef(snapshot);
  snapshotRef.current = snapshot;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: container.clientHeight,
      layout: {
        background: { type: ColorType.Solid, color: '#0b0e11' },
        textColor: '#a7b0bf',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: '#171b22' },
        horzLines: { color: '#171b22' },
      },
      crosshair: {
        vertLine: { color: '#758696', labelBackgroundColor: '#2a2e39' },
        horzLine: { color: '#758696', labelBackgroundColor: '#2a2e39' },
      },
      rightPriceScale: { borderColor: '#252a34' },
      timeScale: {
        borderColor: '#252a34',
        timeVisible: true,
        secondsVisible: true,
        rightOffset: 8,
      },
      localization: { locale: 'zh-TW' },
    });

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      priceFormat: { type: 'price', precision: 2, minMove: 0.05 },
    });
    const vwap = chart.addSeries(LineSeries, {
      color: '#f2c94c',
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true,
      title: 'VWAP',
    });
    const volume = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
      lastValueVisible: false,
      priceLineVisible: false,
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });

    const markerApi = createSeriesMarkers(candles, []);
    let priceLines: IPriceLine[] = [];

    const render = (data: MarketSnapshot) => {
      candles.setData(
        data.bars.map((bar) => ({
          time: bar.time as UTCTimestamp,
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
        })),
      );
      vwap.setData(
        data.bars.map((bar) => ({ time: bar.time as UTCTimestamp, value: bar.vwap })),
      );
      volume.setData(
        data.bars.map((bar) => ({
          time: bar.time as UTCTimestamp,
          value: bar.volume,
          color: bar.close >= bar.open ? '#1c6f68aa' : '#8f3434aa',
        })),
      );

      const markers: SeriesMarker<UTCTimestamp>[] = data.signals.map((signal) => ({
        time: signal.time as UTCTimestamp,
        position: signal.action === 'BUY' ? 'belowBar' : 'aboveBar',
        color: signal.action === 'BUY' ? '#26a69a' : '#ef5350',
        shape: signal.action === 'BUY' ? 'arrowUp' : 'arrowDown',
        text: signal.text,
      }));
      markerApi.setMarkers(markers);

      priceLines.forEach((line) => candles.removePriceLine(line));
      priceLines = [];
      const decision = data.decision;
      if (decision?.entry != null) {
        priceLines.push(
          candles.createPriceLine({
            price: decision.entry,
            color: '#4c8bf5',
            lineWidth: 1,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: 'ENTRY',
          }),
        );
      }
      if (decision?.stop != null) {
        priceLines.push(
          candles.createPriceLine({
            price: decision.stop,
            color: '#ef5350',
            lineWidth: 1,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: 'STOP',
          }),
        );
      }
      if (decision?.take_profit != null) {
        priceLines.push(
          candles.createPriceLine({
            price: decision.take_profit,
            color: '#26a69a',
            lineWidth: 1,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: 'TP',
          }),
        );
      }
    };

    render(snapshotRef.current);
    chart.timeScale().fitContent();

    const observer = new ResizeObserver(([entry]) => {
      chart.applyOptions({
        width: Math.floor(entry.contentRect.width),
        height: Math.floor(entry.contentRect.height),
      });
    });
    observer.observe(container);

    const interval = window.setInterval(() => render(snapshotRef.current), 100);
    return () => {
      window.clearInterval(interval);
      observer.disconnect();
      chart.remove();
    };
  }, []);

  return <div ref={containerRef} className="chart-canvas" />;
}
