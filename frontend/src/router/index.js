import { createRouter, createWebHistory } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import Dashboard from '@/views/Dashboard.vue'
import Clusters from '@/views/Clusters.vue'
import ClusterDetail from '@/views/ClusterDetail.vue'
import ClusterPosts from '@/views/ClusterPosts.vue'
import PlatformDetail from '@/views/PlatformDetail.vue'
import NarrativeBank from '@/views/NarrativeBank.vue'
import PublishHub from '@/views/PublishHub.vue'
import DraftsQueue from '@/views/DraftsQueue.vue'
import SocialAccountsPage from '@/views/SocialAccountsPage.vue'
import TemplatesPage from '@/views/TemplatesPage.vue'
import AutomationPage from '@/views/AutomationPage.vue'
import ExternalNewsPage from '@/views/ExternalNewsPage.vue'
import ScraperPage from '@/views/ScraperPage.vue'
import PostCreatorPage from '@/views/PostCreatorPage.vue'
import CalendarPage from '@/views/CalendarPage.vue'
import PostsPage from '@/views/PostsPage.vue'
import AnalyticsPage from '@/views/AnalyticsPage.vue'
import ResearchPage from '@/views/ResearchPage.vue'
import SearchPage from '@/views/SearchPage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        { path: '', name: 'dashboard', component: Dashboard },
        { path: 'clusters', name: 'clusters', component: Clusters },
        { path: 'narratives', name: 'narratives', component: NarrativeBank },
        { path: 'publish', name: 'publish', component: PublishHub },
        { path: 'drafts', name: 'drafts', component: DraftsQueue },
        { path: 'social-accounts', name: 'social-accounts', component: SocialAccountsPage },
        { path: 'templates', name: 'templates', component: TemplatesPage },
        { path: 'automation', name: 'automation', component: AutomationPage },
        { path: 'external-news', name: 'external-news', component: ExternalNewsPage },
        { path: 'scraper', name: 'scraper', component: ScraperPage },
        { path: 'post-creator', name: 'post-creator', component: PostCreatorPage },
        { path: 'calendar', name: 'calendar', component: CalendarPage },
        { path: 'posts', name: 'posts', component: PostsPage },
        { path: 'analytics', name: 'analytics', component: AnalyticsPage },
        { path: 'research', name: 'research', component: ResearchPage },
        { path: 'search', name: 'search', component: SearchPage },
        { path: 'clusters/:name', name: 'cluster-detail', component: ClusterDetail, props: true },
        { path: 'clusters/:name/posts', name: 'cluster-posts', component: ClusterPosts, props: true },
        { path: 'platform/:platform/:type', name: 'platform-detail', component: PlatformDetail, props: true },
      ]
    }
  ]
})

export default router