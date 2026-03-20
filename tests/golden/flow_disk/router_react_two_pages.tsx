import React from 'react';

export const flowRoutes: Array<{ path: string; lazy: React.LazyExoticComponent<React.ComponentType<any>> }> = [
  { path: '/login', lazy: React.lazy(() => import('./login/Component')) },
  { path: '/register', lazy: React.lazy(() => import('./register/Component')) },
];

export const flowRouteMeta: Array<{ path: string; name: string }> = [
  { path: '/login', name: "Login" },
  { path: '/register', name: "Register" },
];
