<template>
  <aside class="left-panel">
    <!-- 章节列表 -->
    <div class="section chapters-section">
      <h3 class="section-title">📖 故事章节</h3>
      <div class="chapters-list">
        <div 
          v-for="chapter in chapters" 
          :key="chapter.id"
          class="chapter-item"
          :class="{ active: chapter.active }"
        >
          <span class="chapter-icon">{{ chapter.active ? '📝' : '📄' }}</span>
          <span class="chapter-title">{{ chapter.title }}</span>
        </div>
      </div>
    </div>
    
    <!-- 角色面板 -->
    <div class="section characters-section">
      <h3 class="section-title">👥 故事角色</h3>
      <div class="characters-grid">
        <div v-for="character in characters" :key="character.id" class="character-card">
          <div class="character-avatar">{{ character.avatar }}</div>
          <div class="character-info">
            <div class="character-name">{{ character.name }}</div>
            <div class="character-age">{{ character.age }}</div>
            <div class="character-desc">{{ character.description }}</div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 故事设置 -->
    <div class="section settings-section">
      <h3 class="section-title">⚙️ 故事设置</h3>
      <div class="settings-list">
        <div class="setting-item">
          <label>背景音乐</label>
          <select class="setting-select">
            <option>温馨回忆</option>
            <option>童年时光</option>
            <option>夏日微风</option>
          </select>
        </div>
        <div class="setting-item">
          <label>叙述语音</label>
          <select class="setting-select">
            <option>温柔女声</option>
            <option>磁性男声</option>
            <option>童声旁白</option>
          </select>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  chapters: {
    type: Array,
    default: () => []
  },
  characters: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.left-panel {
  width: 280px;
  background: #f9fafb;
  border-right: 1px solid #e5e5e7;
  overflow-y: auto;
  padding: 20px;
}

.section {
  margin-bottom: 28px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.chapters-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chapter-item {
  padding: 10px 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #4b5563;
}

.chapter-item:hover {
  border-color: #667eea;
  background: #f3f4ff;
}

.chapter-item.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
}

.chapter-icon {
  font-size: 16px;
}

.characters-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.character-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.character-avatar {
  font-size: 32px;
  width: 48px;
  height: 48px;
  background: #f3f4f6;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.character-info {
  flex: 1;
}

.character-name {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
}

.character-age {
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.character-desc {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
}

.settings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.setting-item label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
}

.setting-select {
  padding: 8px 12px;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}

.setting-select:focus {
  outline: none;
  border-color: #667eea;
}
</style>