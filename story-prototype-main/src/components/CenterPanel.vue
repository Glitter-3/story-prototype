<template>
  <div class="center-panel">
    <!-- 视觉画布区 -->
    <div class="visual-canvas">
      <div class="canvas-header">
        <h3 class="canvas-title">🎨 视觉画布</h3>
        <div class="canvas-tools">
          <button class="tool-btn">➕ 添加图片</button>
          <button class="tool-btn">🎭 AI生成</button>
          <button class="tool-btn">✂️ 裁剪</button>
        </div>
      </div>
      
      <div class="images-grid">
        <div v-for="image in images" :key="image.id" class="image-card">
          <img :src="image.url" :alt="image.caption" />
          <div class="image-overlay">
            <span class="image-type">{{ image.type === 'original' ? '原始' : 'AI生成' }}</span>
          </div>
          <div class="image-caption">{{ image.caption }}</div>
        </div>
      </div>
    </div>
    
    <!-- 叙事文本编辑区 -->
    <div class="text-editor">
      <div class="editor-header">
        <h3 class="editor-title">✍️ 故事叙述</h3>
        <div class="editor-tools">
          <button class="tool-btn">🎨 AI润色</button>
          <button class="tool-btn">📝 语法检查</button>
          <button class="tool-btn">💾 保存草稿</button>
        </div>
      </div>
      
      <div class="editor-content">
        <textarea 
          v-model="localStoryContent"
          class="story-textarea"
          placeholder="在这里编写您的故事..."
        ></textarea>
        
        <div class="editor-footer">
          <span class="word-count">字数: {{ localStoryContent.length }} 字</span>
          <span class="edit-time">最后编辑: 2分钟前</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  currentStage: {
    type: Number,
    default: 2
  },
  storyContent: {
    type: String,
    default: ''
  },
  images: {
    type: Array,
    default: () => []
  }
})

const localStoryContent = ref(props.storyContent)

watch(() => props.storyContent, (newVal) => {
  localStoryContent.value = newVal
})
</script>

<style scoped>
.center-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
  overflow: hidden;
}

.visual-canvas {
  height: 45%;
  border-bottom: 1px solid #e5e5e7;
  padding: 20px;
  overflow-y: auto;
}

.canvas-header, .editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.canvas-title, .editor-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.canvas-tools, .editor-tools {
  display: flex;
  gap: 8px;
}

.tool-btn {
  padding: 6px 12px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 12px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tool-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-card {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  transition: transform 0.2s ease;
}

.image-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.image-card img {
  width: 100%;
  height: 150px;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 8px;
  right: 8px;
}

.image-type {
  background: rgba(0, 0, 0, 0.6);
  color: white;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.image-caption {
  padding: 8px 12px;
  font-size: 12px;
  color: #6b7280;
}

.text-editor {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.editor-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.story-textarea {
  flex: 1;
  width: 100%;
  padding: 16px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  resize: none;
  font-family: inherit;
  color: #1f2937;
}

.story-textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  padding: 8px 0;
  border-top: 1px solid #f3f4f6;
}

.word-count, .edit-time {
  font-size: 12px;
  color: #9ca3af;
}
</style>