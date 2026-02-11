<script lang="ts">
  import { onMount } from "svelte";
  import Map from "ol/Map";
  import View from "ol/View";
  import TileLayer from "ol/layer/Tile";
  import VectorLayer from "ol/layer/Vector";
  import VectorSource from "ol/source/Vector";
  import { fromLonLat, toLonLat } from "ol/proj";
  import GeoJSON from "ol/format/GeoJSON";
  import { Style, Stroke, Fill, Circle as CircleStyle, Text } from "ol/style";
  import Feature from "ol/Feature";
  import Point from "ol/geom/Point";
  import Draw from "ol/interaction/Draw";
  import Snap from "ol/interaction/Snap";

  interface Props {
    sessionId: string | null;
    mapType: "raw" | "ref";
    keyCol: string;
    geojson: any;
    bounds: number[];
    onSelect: (coords: [number, number]) => void;
    selectedPoint?: [number, number] | null; // Optional prop with default
    pairs: Array<ControlPair>; // Optional prop with default
  }

  // Destructure props with default values
  let {
    sessionId,
    mapType,
    keyCol,
    geojson,
    bounds,
    onSelect,
    selectedPoint = null,
    pairs = $bindable([]),
  }: Props = $props();
  type ControlPair = {
    id: number;
    color: string;
    raw: [number, number];
    ref: [number, number];
  };

  let mapContainer: HTMLDivElement;
  let map: Map;
  let vectorLayer: VectorLayer<VectorSource>;
  let vectorSource: VectorSource;
  let pointsLayer: VectorLayer<VectorSource>;
  let pointsSource: VectorSource;

  console.log(geojson)

  onMount(() => {
    // Calculate center from bounds
    const centerLon = (bounds[0] + bounds[2]) / 2;
    const centerLat = (bounds[1] + bounds[3]) / 2;
    const center = fromLonLat([centerLon, centerLat]);

    // Create vector source from GeoJSON (base layer with plots)

    if ("crs" in geojson) {
      delete geojson.crs;
      console.log("CRS removed");
     
    }

     vectorSource = new VectorSource({
        features: new GeoJSON().readFeatures(geojson, {
          featureProjection: "EPSG:3857",
        }),
      });

    // Style for base geometries
    const baseStyleFunction = (
      feature: { get: (arg0: string) => any },
      resolution: any,
    ) => {
      const color = mapType === "raw" ? "#ef4444" : "#22c55e";
      const plotId = feature.get(keyCol);
      // return new Style({
      //   stroke: new Stroke({
      //     color: color,
      //     width: 2,
      //   }),
      //   fill: new Fill({
      //     color:
      //       mapType === "raw"
      //         ? "rgba(239, 68, 68, 0.2)"
      //         : "rgba(34, 197, 94, 0.2)",
      //   }),

      // });

      return new Style({
        stroke: new Stroke({
          color: color,
          width: 2,
        }),
        fill: new Fill({
          color:
            mapType === "raw"
              ? "rgba(239, 68, 68, 0.2)"
              : "rgba(34, 197, 94, 0.2)",
        }),
        text: new Text({
          text: plotId.toString(), // Ensure plotId is converted to string
          font: "bold 12px Calibri,sans-serif", // Added font for better rendering
          fill: new Fill({
            color: mapType === "raw" ? "#dc2626" : "#16a34a",
          }),
          stroke: new Stroke({
            color: "#ffffff",
            width: 3,
          }),
          offsetY: 0,
        }),
      });
    };

    // Create vector layer for base geometries
    vectorLayer = new VectorLayer({
      source: vectorSource,
      style: baseStyleFunction,
    });

    const snap = new Snap({
      source: vectorSource,
      edge: true,
      vertex: true,
      pixelTolerance: 20,
    });

    // Create layer for user-selected points
    pointsSource = new VectorSource();
    pointsLayer = new VectorLayer({
      source: pointsSource,
      style: (feature) => {
        const color = feature.get("color") || "#f59e0b";

        return new Style({
          image: new CircleStyle({
            radius: 8,
            fill: new Fill({ color }),
            stroke: new Stroke({ color: "#fff", width: 3 }),
          }),
        });
      },
      zIndex: 10,
    });

    // Initialize map
    map = new Map({
      target: mapContainer,
      layers: [new TileLayer(), vectorLayer, pointsLayer],
      view: new View({
        center: center,
        zoom: 15,
      }),
    });

    // Fit to bounds
    const extent = vectorSource.getExtent();
    map.getView().fit(extent, {
      padding: [50, 50, 50, 50],
      maxZoom: 18,
    });

    //  map.addInteraction(snap);
    // // Click handler - add point marker
    // map.on("click", (evt) => {
    //   const coordinate = evt.coordinate;

    //   // Get coordinates based on map type
    //   let coords: [number, number];
    //   if (mapType === "ref") {
    //     // For reference map, convert to lon/lat
    //     const lonLat = toLonLat(coordinate);
    //     coords = [lonLat[0], lonLat[1]];
    //   } else {
    //     // For raw map, use pixel/map coordinates directly
    //     coords = [coordinate[0], coordinate[1]];
    //   }

    //   // Add new point marker
    //   const pointFeature = new Feature({
    //     geometry: new Point(coordinate),
    //   });
    //   pointsSource.addFeature(pointFeature);

    //   // Notify parent component
    //   onSelect(coords);
    // });

    // // Pointer cursor
    // map.on("pointermove", (evt) => {
    //   map.getTargetElement().style.cursor = "crosshair";
    // });

    // 🟢 DRAW interaction (REPLACES click handler)
    const drawPoint = new Draw({
      source: pointsSource,
      type: "Point",
    });
    map.addInteraction(drawPoint);

    // // 🧲 SNAP interaction (THIS IS THE KEY)
    // const snap = new Snap({
    //   source: vectorSource, // snap to plot vertices
    //   pixelTolerance: 10,
    // });
    map.addInteraction(snap);

    // Capture snapped coordinate
    drawPoint.on("drawend", (event) => {
      const geometry = event.feature.getGeometry() as Point;
      const coordinate = geometry.getCoordinates();

      let coords: [number, number];
      if (mapType === "ref") {
        const lonLat = toLonLat(coordinate);
        coords = [lonLat[0], lonLat[1]];
      } else {
        coords = [coordinate[0], coordinate[1]];
      }

      onSelect(coords);
    });

    // Cursor
    map.on("pointermove", () => {
      map.getTargetElement().style.cursor = "crosshair";
    });

    return () => {
      map.setTarget(undefined);
    };
  });

  const cleanPairs = $derived(
    pairs.map((p) => {
      const rawPoint = mapType === "raw" ? p.raw : p.ref;

      // CRITICAL: If this is the REF map, we must convert Lon/Lat to Map Pixels (EPSG:3857)
      const projectedPoint =
        mapType === "ref" && rawPoint ? fromLonLat(rawPoint) : rawPoint;

      return { color: p.color, point: projectedPoint };
    }),
  );

  // Add Persistent Pairs

  $effect(() => {
    // Only run if map and source are ready
    if (!pointsSource) return;

    pointsSource.clear();

    cleanPairs.forEach(({ color, point }) => {
      if (!point) return;
      const feature = new Feature({ geometry: new Point(point) });
      feature.set("color", color);
      pointsSource.addFeature(feature);
    });

    // Add Active Selected Point
    // if (selectedPoint) {
    //   const coord =
    //     mapType === "ref"
    //       ? fromLonLat([selectedPoint[0], selectedPoint[1]])
    //       : [selectedPoint[0], selectedPoint[1]];

    //   const feature = new Feature({ geometry: new Point(coord) });
    //   // Optional: specific color for the "currently clicking" point
    //   pointsSource.addFeature(feature);
    // }
  });
</script>

<div bind:this={mapContainer} class="w-full h-96"></div>

<style>
  :global(.ol-viewport) {
    cursor: crosshair !important;
  }
</style>
