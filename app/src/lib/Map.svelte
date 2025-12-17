// src/lib/MapViewer.svelte
<script lang="ts">
  import Map from "ol/Map.js";
  import OSM from "ol/source/OSM.js";
  import TileLayer from "ol/layer/Tile.js";
  import View from "ol/View.js";
  import VectorLayer from "ol/layer/Vector.js";
  import VectorSource from "ol/source/Vector.js";
  import GeoJSON from "ol/format/GeoJSON.js";
  import { Style, Fill, Stroke, Text } from "ol/style.js";
  import { fromLonLat } from "ol/proj.js";
  import { onMount, onDestroy } from "svelte";
  
  export let sessionId: string | null;
  export let mapType: 'raw' | 'ref';
  export let keyCol: string;
  export let geojson: any;
  export let bounds: number[]; // [minX, minY, maxX, maxY]
  export let onSelect: (plotId: string) => void;
  export let selected: string | null = null;
  
  let mapContainer: HTMLDivElement;
  let map: Map;
  let vectorLayer: VectorLayer<VectorSource>;
  let vectorSource: VectorSource;
  
  onMount(() => {
    // Calculate center from bounds
    const centerLon = (bounds[0] + bounds[2]) / 2;
    const centerLat = (bounds[1] + bounds[3]) / 2;
    const center = fromLonLat([centerLon, centerLat]);
    
    // Create vector source from GeoJSON
    vectorSource = new VectorSource({
      features: new GeoJSON().readFeatures(geojson, {
        featureProjection: 'EPSG:3857'
      })
    });
    
    // Style function
    const styleFunction = (feature: { get: (arg0: string) => any; }, resolution: any) => {
      const plotId = feature.get(keyCol);
      const isSelected = plotId === selected;
      const color = mapType === 'raw' ? '#ef4444' : '#22c55e';
      const selectedColor = '#f59e0b';
      
      return new Style({
        stroke: new Stroke({
          color: isSelected ? selectedColor : color,
          width: isSelected ? 4 : 2
        }),
        fill: new Fill({
          color: isSelected 
            ? 'rgba(245, 158, 11, 0.3)' 
            : mapType === 'raw' 
              ? 'rgba(239, 68, 68, 0.2)' 
              : 'rgba(34, 197, 94, 0.2)'
        }),
        text: new Text({
          text: String(plotId),
          font: '11px sans-serif',
          fill: new Fill({
            color: mapType === 'raw' ? '#dc2626' : '#16a34a'
          }),
          stroke: new Stroke({
            color: '#ffffff',
            width: 3
          }),
          offsetY: 0
        })
      });
    };
    
    // Create vector layer
    vectorLayer = new VectorLayer({
      source: vectorSource,
      style: styleFunction
    });
    
    // Initialize map
    map = new Map({
      target: mapContainer,
      layers: [
        new TileLayer(),
        vectorLayer
      ],
      view: new View({
        center: center,
        zoom: 16,
      }),
    });
    
    // Fit to bounds
    const extent = vectorSource.getExtent();
    map.getView().fit(extent, {
      
      maxZoom: 18
    });
    
    // Click handler
    map.on('click', (evt) => {
      map.forEachFeatureAtPixel(evt.pixel, (feature) => {
        const plotId = feature.get(keyCol);
        if (plotId) {
          onSelect(String(plotId));
        }
        return true;
      });
    });
    
    // Pointer cursor on hover
    map.on('pointermove', (evt) => {
      const hit = map.forEachFeatureAtPixel(evt.pixel, () => true);
      map.getTargetElement().style.cursor = hit ? 'pointer' : '';
    });
  });
  
  onDestroy(() => {
    if (map) {
      map.setTarget(undefined);
    }
  });
  
  // Update style when selected changes
  $: if (vectorLayer && selected !== undefined) {
    vectorLayer.changed();
  }
</script>

<div bind:this={mapContainer} class="w-full h-96 rounded-lg"></div>

<style>
  div {
    position: relative;
  }
  
  :global(.ol-viewport) {
    border-radius: 0.5rem;
  }
</style>