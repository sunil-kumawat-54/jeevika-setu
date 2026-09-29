'use client';

import { useEffect } from 'react';

/** Registers the service worker. Failure is non-fatal — the app still works. */
export default function RegisterSW() {
  useEffect(() => {
    if (typeof navigator === 'undefined' || !('serviceWorker' in navigator)) return;
    const register = () => {
      navigator.serviceWorker.register('/sw.js').catch(() => {
        /* offline caching is an enhancement, never a requirement */
      });
      // iOS Safari evicts script-writable storage after 7 days without
      // interaction unless the PWA is installed (research.md §9.5).
      navigator.storage?.persist?.().catch(() => {});
    };
    if (document.readyState === 'complete') register();
    else window.addEventListener('load', register);
    return () => window.removeEventListener('load', register);
  }, []);
  return null;
}
