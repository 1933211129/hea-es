import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import NewTask from '../views/NewTask.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/new-task',
    name: 'NewTask',
    component: NewTask
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router

