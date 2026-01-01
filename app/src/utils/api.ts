
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

export const api = {
  async uploadRaw(file: string | Blob) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload/raw`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  async uploadRef(sessionId: any, file: string | Blob) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload/ref?session_id=${sessionId}`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
  },

  async getRawGeoJSON(sessionId: any, keyCol: any) {
    const response = await fetch(`${API_BASE_URL}/geojson/raw/${sessionId}?key_col=${keyCol}`);
    if (!response.ok) throw new Error('Failed to fetch RAW GeoJSON');
    return response.json();
  },

  async getRefGeoJSON(sessionId: any, keyCol: any) {
    const response = await fetch(`${API_BASE_URL}/geojson/ref/${sessionId}?key_col=${keyCol}`);
    if (!response.ok) throw new Error('Failed to fetch REF GeoJSON');
    return response.json();
  },

  async getRawFeature(sessionId: any, keyCol: any, featureId: any) {
    const response = await fetch(
      `${API_BASE_URL}/feature/raw/${sessionId}?key_col=${keyCol}&feature_id=${featureId}`
    );
    if (!response.ok) throw new Error('Failed to fetch RAW feature');
    return response.json();
  },

  async getRefFeature(sessionId: any, keyCol: any, featureId: any) {
    const response = await fetch(
      `${API_BASE_URL}/feature/ref/${sessionId}?key_col=${keyCol}&feature_id=${featureId}`
    );
    if (!response.ok) throw new Error('Failed to fetch REF feature');
    return response.json();
  },

  async applyTransform(sessionId: any, rawKey: any, refKey: any, pairs: any) {
    const response = await fetch(`${API_BASE_URL}/transform`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        raw_key: rawKey,
        ref_key: refKey,
        pairs: pairs,
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Transform failed');
    }

    // FIX: Return the WHOLE response so we can read headers in the component
    return response; 
},

  async getSessionInfo(sessionId: any) {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}/info`);
    if (!response.ok) throw new Error('Failed to fetch session info');
    return response.json();
  },

  async deleteSession(sessionId: any) {
    const response = await fetch(`${API_BASE_URL}/session/${sessionId}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete session');
    return response.json();
  }
};