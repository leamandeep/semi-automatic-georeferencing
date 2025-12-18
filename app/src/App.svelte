<script lang="ts">
  import { onMount } from "svelte";
  import { api } from "./utils/api";
  import Map from "./lib/Map.svelte";

  let rawFile = null;
  let refFile = null;
  /**
   * @type {string | null}
   */
  let sessionId = null;

  /**
   * @type {{ columns: string | any[]; feature_count: any; geojson: any; bounds: any;  } | null}
   */
  let rawData = null;
  /**
   * 
   * @type {{ columns: string | any[]; feature_count: any; geojson: any; bounds: any; } | null}
   */
  let refData = null;

  let rawKeyCol = "";
  let refKeyCol = "";

  /**
   * @type {null}
   */
  let selectedRaw = null;
  /**
   * @type {null}
   */
  let selectedRef = null;

  let loading = false;
  /**
   * @type {string | null}
   */
  let error = null;
  let step = 1; // 1: upload, 2: select columns, 3: select pairs, 4: transform

  type ControlPair = {
    id: number;
    color: string;
    raw: [number, number];
    ref: [number, number];
  };

  let pairs: Array<ControlPair> = [];
  let pendingRaw: [number, number] | null = null;
  let pendingRef: [number, number] | null = null;

  /**
   * @param {{ target: { files: any[]; }; }} event
   */
  async function handleRawUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    rawFile = file;
    loading = true;
    error = null;

    try {
      const result = await api.uploadRaw(file);
      sessionId = result.session_id;
      rawData = result;

      console.log(result);

      if (rawData.columns.length > 0) {
        console.log(rawData?.columns);
        rawKeyCol = rawData.columns[0];
      }

      if (refData) {
        step = 2;
      }
    } catch (err) {
      error = `RAW Upload Error: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  /**
   * @param {{ target: { files: any[]; }; }} event
   */
  async function handleRefUpload(event) {
    const file = event.target.files[0];
    if (!file || !sessionId) return;

    refFile = file;
    loading = true;
    error = null;

    try {
      const result = await api.uploadRef(sessionId, file);
      refData = result;

      if (refData.columns.length > 0) {
        refKeyCol = refData.columns[0];
      }

      if (rawData) {
        step = 2;
      }
    } catch (err) {
      error = `REF Upload Error: ${err.message}`;
    } finally {
      loading = false;
    }
  }

  function proceedToMapping() {
    if (!rawKeyCol || !refKeyCol) {
      error = "Please select key columns for both RAW and REF";
      return;
    }
    step = 3;
  }

  /**
   * @param {any} plotId
   */
  function handleRawSelect(plotId) {
    selectedRaw = plotId;

    checkAndAddPair();
  }

  /**
   * @param {any} plotId
   */
  function handleRefSelect(plotId) {
    selectedRef = plotId;
    checkAndAddPair();
  }

  function checkAndAddPair() {
    if (selectedRaw && selectedRef) {
      // Check if pair already exists
      const exists = pairs?.some(
        (p) => p[0] === selectedRaw && p[1] === selectedRef,
      );

      console.log(pairs);
      if (!exists) {
        // @ts-ignore
        pairs = [...pairs, [selectedRaw, selectedRef]];
      }
      selectedRaw = null;
      selectedRef = null;
    }
  }

  /**
   * @param {number} index
   */
  function removePair(index) {
    pairs = pairs?.filter((_, i) => i !== index);
  }


  type Palette = string;
let paletteIndex = 0;

function nextColor(
  paletteCount = 12,
  colorsPerPalette = 5,
): string {
  const hueStep = 360 / paletteCount;
  const lightnessRange = [35, 50, 65, 75, 85];
  const saturation = 70;

  const palette = paletteIndex % paletteCount;
  const color = Math.floor(paletteIndex / paletteCount);

  const hue = Math.round(palette * hueStep);
  const lightness =
    lightnessRange[color % lightnessRange.length];

  paletteIndex++;

  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}




  function tryCreatePair() {
    if (!pendingRaw || !pendingRef) return;

    const exists = pairs.some(
      (p) =>
        p.raw[0] === pendingRaw[0] &&
        p.raw[1] === pendingRaw[1] &&
        p.ref[0] === pendingRef[0] &&
        p.ref[1] === pendingRef[1],
    );

    if (!exists) {
      pairs = [
        ...pairs,
        {
          id: pairs.length,
          color: nextColor(),
          raw: pendingRaw,
          ref: pendingRef,
        },
      ];
    }

    pendingRaw = null;
    pendingRef = null;
  }

  async function applyTransformation() {
    // @ts-ignore
    if (pairs.length < 3) {
      error = "At least 3 control pairs are required";
      return;
    }

    loading = true;
    error = null;

    const cleanPairs = pairs.map((p) => [p.raw, p.ref]);

    try {
      const blob = await api.applyTransform(
        sessionId,
        rawKeyCol,
        refKeyCol,
        cleanPairs,
      );

      // Download the file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "georef_final.zip";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      error = `Transform Error: ${err?.message}`;
    } finally {
      loading = false;
    }
  }

  function reset() {
    rawFile = null;
    refFile = null;
    sessionId = null;
    rawData = null;
    refData = null;
    rawKeyCol = "";
    refKeyCol = "";
    selectedRaw = null;
    selectedRef = null;
    pairs = [];
    step = 1;
    error = null;
  }
</script>

<main class="flex flex-col items-center gap-5 my-10 px-4">
  <h1 class="text-2xl font-bold">
    🌐 Semi-Automatic Georeferencing (RAW + REF)
  </h1>

  {#if error}
    <div class="alert alert-error max-w-2xl">
      <span>{error}</span>
    </div>
  {/if}

  {#if loading}
    <div class="flex items-center gap-2">
      <span class="loading loading-spinner"></span>
      <span>Processing...</span>
    </div>
  {/if}

  <!-- Step 1: File Upload -->
  {#if step === 1}
    <div class="flex gap-5">
      <fieldset class="fieldset border p-4 rounded">
        <legend class="fieldset-legend font-semibold px-2"
          >Pick a Raw file</legend
        >
        <input
          type="file"
          name="raw"
          class="file-input w-full max-w-xs"
          accept=".zip"
          on:change={handleRawUpload}
          disabled={loading}
        />
        <label class="label" for="raw">
          <span class="label-text">Max size 200MB</span>
        </label>
        {#if rawData}
          <div class="text-sm text-success">
            ✓ Loaded: {rawData.feature_count} features
          </div>
        {/if}
      </fieldset>

      <fieldset class="fieldset border p-4 rounded">
        <legend class="fieldset-legend font-semibold px-2"
          >Pick a Ref file</legend
        >
        <input
          type="file"
          name="ref"
          class="file-input w-full max-w-xs"
          accept=".zip"
          on:change={handleRefUpload}
          disabled={loading || !sessionId}
        />
        <label class="label" for="ref">
          <span class="label-text">Max size 200MB</span>
        </label>
        {#if refData}
          <div class="text-sm text-success">
            ✓ Loaded: {refData.feature_count} features
          </div>
        {/if}
      </fieldset>
    </div>
  {/if}

  <!-- Step 2: Select Key Columns -->
  {#if step === 2}
    <div class="card bg-base-200 shadow-xl max-w-2xl w-full">
      <div class="card-body">
        <h2 class="card-title">Select Key Columns</h2>

        <div class="form-control">
          <label class="label" for="raw">
            <span class="label-text">RAW Plot Number Column</span>
          </label>

        
          <select class="select select-bordered" bind:value={rawKeyCol}>
            {#each rawData?.columns as col}
              <option value={col}>{col}</option>
            {/each}
          </select>
        </div>

        <div class="form-control">
          <label class="label" for="ref">
            <span class="label-text">REF Plot Number Column</span>
          </label>
      
          <select class="select select-bordered" bind:value={refKeyCol}>
            {#each refData?.columns as col}
              <option value={col}>{col}</option>
            {/each}
          </select>
        </div>

        <div class="card-actions justify-end mt-4">
          <button class="btn btn-primary" on:click={proceedToMapping}>
            Next: Select Pairs →
          </button>
        </div>
      </div>
    </div>
  {/if}

  <!-- Step 3: Select Control Pairs -->
  {#if step === 3}
    <div class="w-full max-w-7xl">
      <h2 class="text-xl font-semibold mb-4">
        Step 1: Select Matching Plot Numbers
      </h2>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card bg-base-200 shadow-xl">
          <div class="card-body">
            <h3 class="card-title text-red-600">🟥 RAW Map</h3>
            <Map
              {sessionId}
              mapType="raw"
              keyCol={rawKeyCol}
              geojson={rawData?.geojson}
              bounds={rawData?.bounds}
              {pairs}
              onSelect={(coords) => {
                pendingRaw = coords;
                tryCreatePair();
              }}
              selectedPoint={selectedRaw}
            />
          </div>
        </div>

        <div class="card bg-base-200 shadow-xl">
          <div class="card-body">
            <h3 class="card-title text-green-600">🟩 REF Map</h3>
            <Map
              {sessionId}
              mapType="ref"
              keyCol={refKeyCol}
              geojson={refData?.geojson}
              bounds={refData?.bounds}
              {pairs}
              selectedPoint={selectedRef}
              onSelect={(coords) => {
                pendingRef = coords;
                tryCreatePair();
              }}
            />
          </div>
        </div>
      </div>

      <div class="card bg-base-200 shadow-xl mt-4">
        <div class="card-body">
          <h3 class="card-title">Control Pairs ({pairs.length})</h3>

          {#if pairs.length > 0}
            <div class="overflow-x-auto">
              <table class="table table-zebra">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>color</th>
                    <th>RAW</th>
                    <th>REF</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {#each pairs as pair, i}
                    <tr>
                      <td>{i + 1}</td>
                      <td
                        ><svg
                          height="32"
                          width="32"
                          viewBox="0 0 24 24"
                          xmlns="http://www.w3.org/2000/svg"
                        >
                          <circle
                            r="8"
                            cx="12"
                            cy="12"
                            fill={pair["color"]}
                            stroke="white"
                            stroke-width="2"
                          />
                        </svg></td
                      >
                      <td>{"(" +pair["raw"][0] +","+ pair["raw"][1] +")"}</td>
                      <td>{"(" +pair["ref"][0] +","+ pair["ref"][1] +")"}</td>
                      <td>
                        <!-- <button class="btn btn-xs btn-info"> zoom </button> -->
                        <button
                          class="btn btn-xs btn-error"
                          on:click={() => removePair(i)}
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {:else}
            <p class="text-sm opacity-70">
              Click on matching plots in both maps to add control pairs. At
              least 3 pairs required.
            </p>
          {/if}

          <div class="card-actions justify-end mt-4">
            <button class="btn" on:click={reset}>Reset</button>
            <button
              class="btn btn-primary"
              disabled={pairs.length < 3 || loading}
              on:click={applyTransformation}
            >
              🚀 Apply Georeferencing
            </button>
          </div>
        </div>
      </div>
    </div>
  {/if}

  <!-- Step 4: Success -->
  {#if step === 4}
    <div class="card bg-success text-success-content shadow-xl max-w-2xl">
      <div class="card-body items-center text-center">
        <h2 class="card-title">✅ Georeferencing Complete!</h2>
        <p>Your georeferenced shapefile has been downloaded.</p>
        <div class="card-actions justify-center mt-4">
          <button class="btn btn-primary" on:click={reset}>
            Start New Session
          </button>
        </div>
      </div>
    </div>
  {/if}
</main>
