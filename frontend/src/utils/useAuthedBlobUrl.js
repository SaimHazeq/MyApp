import { useEffect, useState } from "react";
import { api } from "../services/api";

/**
 * Downloads an authenticated backend resource (e.g. /storage/{id}/video)
 * through axios (so the JWT header is attached) and exposes it as a local
 * blob: URL that a plain <video>/<img>/<track> element can use directly.
 *
 * @param {string|null} path - path relative to the API base, e.g. `/storage/${id}/video`
 */
export function useAuthedBlobUrl(path) {
  const [state, setState] = useState({ url: null, loading: Boolean(path), error: null });

  useEffect(() => {
    if (!path) {
      setState({ url: null, loading: false, error: null });
      return;
    }
    let objectUrl = null;
    let cancelled = false;

    setState({ url: null, loading: true, error: null });
    api
      .get(path, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data);
        setState({ url: objectUrl, loading: false, error: null });
      })
      .catch((error) => {
        if (!cancelled) setState({ url: null, loading: false, error });
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  return state;
}
