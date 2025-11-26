<template>
  <nav class="top-nav">
    <div class="nav-brand">
      <span class="brand-icon">📸</span>
      <span class="brand-name">Photo Story AI</span>
    </div>
    
    <div class="nav-stages">
      <div 
        v-for="stage in stages" 
        :key="stage.id"
        class="stage-item"
        :class="{ active: currentStage === stage.id }"
        @click="$emit('stage-change', stage.id)"
      >
        <span class="stage-number">{{ stage.id }}</span>
        <span class="stage-name">{{ stage.name }}</span>
        <span class="stage-status" v-if="stage.id < currentStage">✓</span>
      </div>
    </div>
    
    <div class="nav-actions">
      <button class="btn-save">💾 保存</button>
      <button class="btn-export">📤 导出</button>
    </div>
  </nav>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue'

defineProps({
  currentStage: {
    type: Number,
    default: 1
  }
})

defineEmits(['stage-change'])

const stages = [
  { id: 1, name: '导入与提问' },
  { id: 2, name: '图文创作' },
  { id: 3, name: '视频预览' }
]
</script>

<style scoped>
.top-nav {
  height: 60px;
  background: linear-gradient(to right, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  color: white;
  font-weight: 600;
  font-size: 18px;
}

.brand-icon {
  font-size: 24px;
}

.nav-stages {
  display: flex;
  gap: 32px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.8);
  cursor: pointer;
  padding: 8px 16px;
  border-radius: 20px;
  transition: all 0.3s ease;
  position: relative;
}

.stage-item:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.stage-item.active {
  color: white;
  background: rgba(255, 255, 255, 0.2);
  font-weight: 500;
}

.stage-number {
  width: 24px;
  height: 24px;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.stage-item.active .stage-number {
  background: white;
  color: #667eea;
}

.stage-status {
  color: #4ade80;
  font-weight: bold;
}

.nav-actions {
  display: flex;
  gap: 12px;
}

.btn-save, .btn-export {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
}

.btn-save:hover, .btn-export:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>