import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Clusters from '@/views/Clusters.vue'
import ClusterDetail from '@/views/ClusterDetail.vue'
import ClusterPosts from '@/views/ClusterPosts.vue'
import PlatformDetail from '@/views/PlatformDetail.vue'
import NarrativeBank from '@/views/NarrativeBank.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard
    },
    {
      path: '/clusters',
      name: 'clusters',
      component: Clusters
    },
    {
      path: '/narratives',
      name: 'narratives',
      component: NarrativeBank
    },
    {
      path: '/clusters/:name',
      name: 'cluster-detail',
      component: ClusterDetail,
      props: true
    },
    {
      path: '/clusters/:name/posts',
      name: 'cluster-posts',
      component: ClusterPosts,
      props: true
    },
    {
      path: '/platform/:platform/:type',
      name: 'platform-detail',
      component: PlatformDetail,
      props: true
    },
  ]
})

export default router