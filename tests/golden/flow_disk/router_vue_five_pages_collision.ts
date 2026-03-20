import { type RouteRecordRaw } from 'vue-router';

export const flowRoutes: RouteRecordRaw[] = [
  { path: '/dashboard', component: () => import('./dashboard/Component.vue') },
  { path: '/dashboard-2', component: () => import('./dashboard-2/Component.vue') },
  { path: '/dashboard-3', component: () => import('./dashboard-3/Component.vue') },
  { path: '/dashboard-4', component: () => import('./dashboard-4/Component.vue') },
  { path: '/settings', component: () => import('./settings/Component.vue') },
];

export const flowRouteMeta: Array<{ path: string; name: string }> = [
  { path: '/dashboard', name: "Dashboard" },
  { path: '/dashboard-2', name: "Dashboard" },
  { path: '/dashboard-3', name: "Dashboard" },
  { path: '/dashboard-4', name: "Dashboard" },
  { path: '/settings', name: "Settings" },
];
