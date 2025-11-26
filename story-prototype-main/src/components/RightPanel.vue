<template>
  <aside class="right-panel">
    <div class="chat-header">
      <div class="assistant-info">
        <span class="assistant-avatar">🤖</span>
        <div>
          <h3 class="assistant-name">AI创作助手</h3>
          <span class="assistant-status">• 在线</span>
        </div>
      </div>
      <button class="chat-settings">⚙️</button>
    </div>
    
    <div class="chat-messages">
      <div 
        v-for="message in messages" 
        :key="message.id"
        class="message"
        :class="`message-${message.type}`"
      >
        <div class="message-avatar">
          {{ message.type === 'ai' ? '🤖' : '👤' }}
        </div>
        <div class="message-content">
          <div class="message-text">{{ message.content }}</div>
          <div class="message-time">{{ getMessageTime(message.id) }}</div>
        </div>
      </div>
    </div>
    
    <div class="chat-input-area">
      <div class="quick-actions">
        <button class="quick-btn">💡 获取灵感</button>
        <button class="quick-btn">🎯 优化建议</button>
        <button class="quick-btn">❓ 使用帮助</button>
      </div>
      
      <div class="input-container">
        <input 
          type="text" 
          class="chat-input"
          placeholder="输入您的问题或需求..."
          v-model="inputText"
          @keyup.enter="handleSend"
        />
        <button class="send-btn" @click="handleSend">
          <span>发送</span>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { ref } from 'vue'

defineProps({
  messages: {
    type: Array,
    default: () => []
  }
})

const inputText = ref('')

const handleSend = () => {
  if (inputText.value.trim()) {
    console.log('发送消息:', inputText.value)
    inputText.value = ''
  }
}

const getMessageTime = (id) => {
  const times = ['刚刚', '1分钟前', '3分钟前', '5分钟前', '8分钟前', '10分钟前']
  return times[Math.min(id - 1, times.length - 1)]
}
</script>

<style scoped>
.right-panel {
  width: 360px;
  background: #fafbfc;
  border-left: 1px solid #e5e5e7;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 16px 20px;
  background: white;
  border-bottom: 1px solid #e5e5e7;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.assistant-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.assistant-avatar {
  font-size: 32px;
}

.assistant-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.assistant-status {
  font-size: 11px;
  color: #10b981;
  display: flex;
  align-items: center;
  margin-top: 2px;
}

.chat-settings {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #6b7280;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  gap: 10px;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.message-ai .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.message-content {
  flex: 1;
}

.message-text {
  background: white;
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  color: #374151;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.message-user .message-text {
  background: #667eea;
  color: white;
}

.message-time {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 4px;
  padding-left: 4px;
}

.chat-input-area {
  padding: 16px;
  background: white;
  border-top: 1px solid #e5e5e7;
}

.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.quick-btn {
  padding: 6px 10px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  font-size: 11px;
  color: #4b5563;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.quick-btn:hover {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.input-container {
  display: flex;
  gap: 8px;
}

.chat-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
  color: #1f2937;
}

.chat-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.send-btn {
  padding: 10px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.send-btn:hover {
  transform: scale(1.05);
}

.send-btn:active {
  transform: scale(0.98);
}
</style>