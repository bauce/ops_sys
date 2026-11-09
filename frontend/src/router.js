import { createRouter, createWebHistory } from 'vue-router'
import { ensureAuth } from './store'

const routes = [
  { path: '/', component: () => import('./views/Home.vue') },
  { path: '/r/:qr', component: () => import('./views/Report.vue') },
  { path: '/mine', component: () => import('./views/Mine.vue') },
  { path: '/query', redirect: '/mine' },
  { path: '/login', component: () => import('./views/Login.vue') },
  { path: '/board', component: () => import('./views/Board.vue'), meta: { requiresStaff: true } },
  {
    path: '/admin',
    component: () => import('./views/StaffLayout.vue'),
    meta: { requiresStaff: true },
    children: [
      { path: '', component: () => import('./views/Dashboard.vue') },
      { path: 'tickets', component: () => import('./views/Tickets.vue') },
      { path: 'materials', component: () => import('./views/Materials.vue') },
      { path: 'assets', component: () => import('./views/Assets.vue') },
      { path: 'rooms', component: () => import('./views/Rooms.vue') },
      { path: 'reports', component: () => import('./views/Reports.vue') },
      { path: 'duty', component: () => import('./views/Duty.vue') },
      { path: 'settings', component: () => import('./views/Settings.vue') },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach(async (to) => {
  if (to.meta.requiresStaff || to.path.startsWith('/admin')) {
    const staff = await ensureAuth()
    if (!staff) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }
  return true
})

export default router
