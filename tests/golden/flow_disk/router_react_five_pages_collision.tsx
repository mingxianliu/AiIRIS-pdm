import React from 'react';

export const flowRoutes: Array<{ path: string; lazy: React.LazyExoticComponent<React.ComponentType<any>> }> = [
  { path: '/dashboard', lazy: React.lazy(() => import('./dashboard/Component')) },
  { path: '/dashboard-2', lazy: React.lazy(() => import('./dashboard-2/Component')) },
  { path: '/dashboard-3', lazy: React.lazy(() => import('./dashboard-3/Component')) },
  { path: '/dashboard-4', lazy: React.lazy(() => import('./dashboard-4/Component')) },
  { path: '/settings', lazy: React.lazy(() => import('./settings/Component')) },
];

export const flowRouteMeta: Array<{ path: string; name: string }> = [
  { path: '/dashboard', name: "Dashboard" },
  { path: '/dashboard-2', name: "Dashboard" },
  { path: '/dashboard-3', name: "Dashboard" },
  { path: '/dashboard-4', name: "Dashboard" },
  { path: '/settings', name: "Settings" },
];
