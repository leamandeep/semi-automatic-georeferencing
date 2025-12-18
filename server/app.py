from pathlib import Path
import sys
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Tuple, Optional
import geopandas as gpd
import numpy as np
import tempfile
import zipfile
import os
import json
import shutil
from shapely.geometry import Point, Polygon, MultiPolygon, LineString, MultiLineString
from io import BytesIO
from loguru import logger
import fiona
app = FastAPI(title="Georeferencing API")

logger.remove()


logger.add(
    sys.stdout,
    level="DEBUG",
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
    backtrace=True,
    diagnose=True,
    enqueue=True,
)



# Enable CORS for Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Store session data (in production, use Redis or database)
sessions = {}

# ======================================================================
# MODELS
# ======================================================================

class UploadResponse(BaseModel):
    session_id: str
    columns: List[str]
    feature_count: int
    bounds: List[float]
    geojson: dict

class PairRequest(BaseModel):
    session_id: str
    raw_id: str
    ref_id: str


class FeatureInfo(BaseModel):
    properties: dict
    geometry: dict

# ======================================================================
# HELPER FUNCTIONS
# ======================================================================

def load_shapefile_from_zip(zip_file_bytes: bytes, filename: str) -> gpd.GeoDataFrame:
    """Load shapefile from uploaded ZIP bytes"""
    tmp = tempfile.mkdtemp()
    zpath = os.path.join(tmp, filename)
    
    with open(zpath, "wb") as f:
        f.write(zip_file_bytes)
    
    with zipfile.ZipFile(zpath, "r") as z:
        z.extractall(tmp)
    
    shp_files = [os.path.join(tmp, f) for f in os.listdir(tmp) if f.endswith(".shp")]
    
    if not shp_files:
        raise HTTPException(status_code=400, detail=f"No .shp file found in {filename}")
    
    gdf = gpd.read_file(shp_files[0], engine="fiona")
    return gdf

def safe_centroid(g):
    """Safely compute centroid of geometry"""
    try:
        c = g.centroid
        return float(c.x), float(c.y)
    except Exception:
        return None


class TransformRequest(BaseModel):
    session_id: str
    pairs: List[Tuple[Tuple[float, float], Tuple[float, float]]]  # [(raw_point, ref_point), ...]


def compute_similarity_transform(src, dst):
    """Compute similarity transformation (scale, rotation, translation)"""
    src = np.asarray(src).reshape(-1, 2)
    dst = np.asarray(dst).reshape(-1, 2)
    
    src_mean = src.mean(axis=0)
    dst_mean = dst.mean(axis=0)
    
    src_c = src - src_mean
    dst_c = dst - dst_mean
    
    M = src_c.T @ dst_c
    U, _, Vt = np.linalg.svd(M)
    R = Vt.T @ U.T
    
    if np.linalg.det(R) < 0:
        Vt[-1] *= -1
        R = Vt.T @ U.T
    
    A = src_c @ R.T
    scale = np.sum(dst_c * A) / np.sum(src_c * src_c)
    
    t = dst_mean - scale * (R @ src_mean)
    return scale, R, t


def transform_point(x, y, model):
    """Transform a single point"""
    scale, R, t = model["scale"], model["R"], model["t"]
    p = np.array([x, y])
    P = scale * (R @ p) + t
    return float(P[0]), float(P[1])


def transform_geom(g, model):
    """Transform geometry using similarity transform"""
    if g.geom_type == "Point":
        return Point(*transform_point(g.x, g.y, model))
    
    if g.geom_type == "Polygon":
        exterior = [transform_point(x, y, model) for x, y in g.exterior.coords]
        holes = [[transform_point(x, y, model) for x, y in ring.coords] for ring in g.interiors]
        return Polygon(exterior, holes)
    
    if g.geom_type == "MultiPolygon":
        return MultiPolygon([transform_geom(poly, model) for poly in g.geoms])
    
    if g.geom_type == "LineString":
        return LineString([transform_point(x, y, model) for x, y in g.coords])
    
    if g.geom_type == "MultiLineString":
        return MultiLineString([transform_geom(ls, model) for ls in g.geoms])
    
    return g


def gdf_to_geojson(gdf: gpd.GeoDataFrame, key_col: str) -> dict:
    """Convert GeoDataFrame to GeoJSON with plot_id"""
    gdf_copy = gdf.copy()
    gdf_copy['plot_id'] = gdf_copy[key_col].astype(str)
    return json.loads(gdf_copy.to_json())

# ======================================================================
# ENDPOINTS
# ======================================================================

@app.post("/upload/raw", response_model=UploadResponse)
async def upload_raw(file: UploadFile = File(...)):
    """Upload RAW shapefile ZIP"""

    logger.info("Starting RAW shapefile upload for file: {}", file.filename)
    try:
        
        content = await file.read()
        logger.debug("File content read successfully. Size: {} bytes", len(content))

        # Load GeoDataFrame
        gdf = load_shapefile_from_zip(content, file.filename)
        logger.info("Shapefile loaded successfully. Feature count: {}", len(gdf))
        # Store in session (generate unique ID)
        import uuid
        session_id = str(uuid.uuid4())
        logger.debug("Generated session ID: {}", session_id)
        # Force CRS for display
        gdf_display = gdf.copy()
        gdf_display = gdf_display.set_crs(3857, allow_override=True)
        logger.debug("CRS set to EPSG:3857 for display version.")

        sessions[session_id] = {
            "raw": gdf,
            "raw_display": gdf_display
        }
        logger.info("GeoDataFrames stored in session: {}", session_id)
        
        bounds = gdf_display.total_bounds.tolist()
        logger.success(
            "Upload complete for session {}. Features: {}, Bounds: {}",
            session_id,
            len(gdf),
            bounds
        )
        return UploadResponse(
            session_id=session_id,
            columns=gdf.columns.tolist(),
            feature_count=len(gdf),
            bounds=bounds,
            geojson=gdf_to_geojson(gdf_display, gdf.columns[0])
        )
    except Exception as e:
        logger.exception("An error occurred during RAW shapefile upload for file {}: {}", file.filename, e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload/ref", response_model=UploadResponse)
async def upload_ref(session_id: str, file: UploadFile = File(...)):
    """Upload REF shapefile ZIP"""
    try:
        if session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        content = await file.read()
        gdf = load_shapefile_from_zip(content, file.filename)
        
        sessions[session_id]["ref"] = gdf
        
        bounds = gdf.total_bounds.tolist()
        
        return UploadResponse(
            session_id=session_id,
            columns=gdf.columns.tolist(),
            feature_count=len(gdf),
            bounds=bounds,
            geojson=gdf_to_geojson(gdf, gdf.columns[0])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/geojson/raw/{session_id}")
async def get_raw_geojson(session_id: str, key_col: str):
    """Get RAW GeoJSON for map display"""
    if session_id not in sessions or "raw_display" not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="Session or data not found")
    
    gdf = sessions[session_id]["raw_display"]
    print(gdf.columns)
    return gdf_to_geojson(gdf, key_col)

@app.get("/geojson/ref/{session_id}")
async def get_ref_geojson(session_id: str, key_col: str):
    """Get REF GeoJSON for map display"""
    if session_id not in sessions or "ref" not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="Session or data not found")
    
    gdf = sessions[session_id]["ref"]
    return gdf_to_geojson(gdf, key_col)

@app.get("/feature/raw/{session_id}")
async def get_raw_feature(session_id: str, key_col: str, feature_id: str):
    """Get specific RAW feature by ID"""

    print(key_col)
    if session_id not in sessions or "raw" not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="Session or data not found")
    
    gdf = sessions[session_id]["raw"]
    print(gdf.columns)

    feature = gdf[gdf[key_col] == feature_id]
    
    if len(feature) == 0:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return {
        "properties": feature.iloc[0].to_dict(),
        "geometry": json.loads(gpd.GeoSeries([feature.iloc[0].geometry]).to_json())
    }

@app.get("/feature/ref/{session_id}")
async def get_ref_feature(session_id: str, key_col: str, feature_id: str):
    """Get specific REF feature by ID"""
    if session_id not in sessions or "ref" not in sessions[session_id]:
        raise HTTPException(status_code=404, detail="Session or data not found")
    
    gdf = sessions[session_id]["ref"]
    feature = gdf[gdf[key_col] == feature_id]
    
    if len(feature) == 0:
        raise HTTPException(status_code=404, detail="Feature not found")
    
    return {
        "properties": feature.iloc[0].to_dict(),
        "geometry": json.loads(gpd.GeoSeries([feature.iloc[0].geometry]).to_json())
    }



@app.post("/transform")
async def apply_transformation(request: TransformRequest):
    """Apply similarity transformation and return georeferenced shapefile"""
    try:
        if request.session_id not in sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if len(request.pairs) < 3:
            raise HTTPException(status_code=400, detail="At least 3 control point pairs required")
        
        raw = sessions[request.session_id]["raw"]
        
        print(request.pairs)
        # Extract points directly from the pairs
        raw_pts = np.array([pair[0] for pair in request.pairs])  # [(x, y), ...]
        ref_pts = np.array([pair[1] for pair in request.pairs])  # [(lon, lat), ...]
        
        # Compute transformation
        scale, R, t = compute_similarity_transform(raw_pts, ref_pts)
        model = {"scale": scale, "R": R, "t": t}
        
        # Transform all geometries in the raw dataset
        raw_trans = raw.copy()
        raw_trans["geometry"] = raw.geometry.apply(lambda g: transform_geom(g, model))
        raw_trans = raw_trans.set_crs(4326)
        
        # Create ZIP file with all shapefile components
        outdir = tempfile.mkdtemp()
        shp_path = os.path.join(outdir, "georef_final.shp")
        raw_trans.to_file(shp_path)
        
        # Create ZIP
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in os.listdir(outdir):
                file_path = os.path.join(outdir, file)
                zipf.write(file_path, arcname=file)
        
        # Cleanup
        shutil.rmtree(outdir)
        
        zip_buffer.seek(0)
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=georef_final.zip"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/session/{session_id}/info")
async def get_session_info(session_id: str):
    """Get session information"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    return {
        "has_raw": "raw" in session,
        "has_ref": "ref" in session,
        "raw_count": len(session["raw"]) if "raw" in session else 0,
        "ref_count": len(session["ref"]) if "ref" in session else 0
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete session data"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted"}
    raise HTTPException(status_code=404, detail="Session not found")
