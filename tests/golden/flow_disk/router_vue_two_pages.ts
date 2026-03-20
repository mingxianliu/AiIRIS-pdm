import { type RouteRecordRaw } from 'vue-router';

export const flowRoutes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('./login/Component.vue') },
  { path: '/register', component: () => import('./register/Component.vue') },
];

export const flowRouteMeta: Array<{ path: string; name: string }> = [
  { path: '/login', name: "Login" },
  { path: '/register', name: "Register" },
];
