<template>
  <div class="photo-story-container">
    <!-- 顶部导航栏 -->
    <header class="app-header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">📸</span>
          <span class="logo-text">Photo Story AI</span>
        </div>
      </div>

      <!-- ✅ 改为可点击切换 -->
      <div class="header-nav">
        <div 
          v-for="stage in 5" 
          :key="stage"
          class="nav-item"
          :class="{ active: currentStage === stage }"
          @click="switchStage(stage)"
        >
          <span class="nav-number">{{ stage }}</span>
          <span class="nav-text">Stage {{ stage }}</span>
        </div>
      </div>

      <div class="header-right">
        <button class="save-btn">💾 保存</button>
        <button class="export-btn">📤 导出</button>
      </div>
    </header>

    <!-- 以下内容保持不变 -->
    <div class="main-content">
      <!-- 中间内容区 -->
      <section class="content-area" ref="contentArea">
        <!-- 照片面板 -->
        <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
          <div class="panel-header">
            <h2>📷 照片面板</h2>
            <div class="panel-controls">
              <!-- 隐藏的文件选择框 -->
              <input 
                type="file" 
                ref="fileInput"
                multiple
                accept="image/*"
                @change="handleFileChange"
                style="display: none;"
              />
              <!-- Stage 1 显示上传照片按钮 -->
              <button button v-if="currentStage === 1" class="control-btn" @click="addPhoto">➕ 添加照片</button>
              <button button v-if="currentStage === 1" class="control-btn" @click="confirmUpload">确认上传图片</button>

            </div>
          </div>
          <!--统一的照片展示区，Stage1~5-->
          <div class="photo-grid">
            <div class="photo-slot" v-for="(photo, index) in photos" :key="index">
              <div class="photo-placeholder" @click="triggerFileInput(index)" v-if="currentStage === 1">
                <!--Stage 1 显示可添加的占位符-->
                <template v-if="photo.url">
                  <img :src="photo.url" class="photo-preview" alt="预览图片" />
                </template>
                <template v-else>
                  <span class="photo-number">{{ index + 1 }}</span>
                  <span class="add-icon">+</span>
                </template>
              </div>
              <div class="photo-placeholder" v-else>
                <!-- Stage 2~5 显示已上传的照片，不允许修改 -->
                <template v-if="photo.url">
                  <img :src="photo.url" class="photo-preview" alt="预览图片" />
                </template>
                <template v-else>
                  <span class="photo-number">{{ index + 1 }}</span>
                  <span class="add-icon">+</span>
                </template>
              </div>  
            </div>
          </div>
        </div>

        <!-- 可拖拽分隔条 -->
        <div 
          class="resize-handle" 
          @mousedown="startResize"
          :class="{ 'resizing': isResizing }">
       <div class= "handle-line"></div>
        </div>

        <!-- 叙事文本 -->
        <div class="narrative-section" :style="{ flex: 1 }">
          <div class="panel-header">
            <h3>📝 用户口述</h3>
            <div class="panel-controls">
              <!-- <button class="control-btn" @click="generateImages">图像补全</button> -->
              <button class="control-btn" @click="calculateMemoryMetrics">计算记忆指标</button>
              <button class="control-btn" @click="reselectText">🔄 重新口述</button>

              <!-- 仅 Stage 3 显示图像补全按钮 -->
              <button v-if="currentStage === 3" class="control-btn" @click="generateImages">图像补全</button>
            </div>
          </div>
          
          <!-- <div class="narrative-content" @mouseup="handleTextSelection">
            <p>
              第一阶段：高中时期 大约是在1995年，那时我刚上高一。因为座位靠得近，很自然地认识了
              <span :class="{ 'highlighted': highlightedTexts.includes(0) }" @click="toggleHighlight(0)">静静和哲哲</span>，
              我们三个成了无话不谈的好朋友。那时候的学习生活紧张又单纯，哲哲安静勤奋，经常带着我一起自习；
              静静性格细腻，有时会因为想家而落泪，我们就在课间轮流安慰她。
              <span :class="{ 'highlighted': highlightedTexts.includes(1) }" @click="toggleHighlight(1)">那张合影是班里同学带来一台新相机，在教室一角帮我们拍的</span>。
              我们有些不好意思，表情都挺僵硬。现在回头看，那是我们三个人难得停下来留下的影像。
              虽然如今大家分隔在不同城市，但还保持联系，会互相分享现在的生活近况。
            </p>
          </div> -->
          <div class="narrative-content">
            <textarea
              v-model="userNarratives[currentStage]"
              placeholder="请在此输入您对这阶段照片的描述、回忆或故事……"
              rows="8"
              class="narrative-input"
            ></textarea>
          </div>
        </div>
      </section>

      <!-- 右侧AI助手 -->
      <aside class="ai-assistant" v-if="currentStage !== 1">
        <div class="assistant-header">
          <h3>🤖 AI创作助手</h3>
          <span class="status-indicator">● 在线</span>
        </div>

        <div class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
          </div>
          <span class="progress-text">{{ answeredCount }}/{{ questions.length }} 问题已回答</span>
        </div>

        <div class="questions-container">
          <div 
            v-for="(question, index) in questions" 
            :key="index"
            class="question-card"
            :class="{ active: currentQuestionIndex === index, answered: question.answered }">
            
            <div class="question-header">
              <span class="question-number">{{ index + 1 }}</span>
              <span v-if="question.answered" class="answered-badge">✓</span>
            </div>
            
            <p class="question-text">{{ question.text }}</p>
            
            <div v-if="currentQuestionIndex === index && !question.answered" class="answer-actions">
              <button class="action-btn text-btn" @click="showTextInput(index)">📝 文字输入</button>             
              <button class="action-btn skip-btn" @click="skipQuestion(index)">⏭️ 跳过</button>
            </div>
            
            <div v-if="question.showInput && !question.answered" class="text-input-area">
              <textarea
                v-model="question.answer"
                placeholder="请输入您的回答..."
                rows="3"></textarea>
              <button class="submit-btn" @click="submitAnswer(index)">确认</button>
            </div>
            
            <div v-if="question.answered && question.answer" class="answer-display">
              <p>{{ question.answer }}</p>
            </div>
          </div>
        </div>

        <button class="update-narrative-btn">
          ✨ 更新叙事文本
        </button>
      </aside>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  name: 'PhotoStoryAI',
  data() {
    return {
      currentStage: 1, // ✅ 默认Stage 1
      photoPanelHeight: 280,
      isResizing: false,
      startY: 0,
      startHeight: 0,
      highlightedTexts: [],
      selectedText: '',
      photos: [], 
      uploadTargetIndex: null,
      userNarratives: {
        1: '',
        2: '',
        3: '',
        4: '',
        5: ''
      },
      currentQuestionIndex: 0,
      questions: [], // Qwen返回的问题
    }
  },
  computed: {
    progressPercentage() {
      return (this.answeredCount / this.questions.length) * 100
    },
    answeredCount() {
      return this.questions.filter(q => q.answered).length
    }
  },
  methods: {
    // 切换阶段
    switchStage(stage) {
      this.currentStage = stage
      console.log(`已切换到 Stage ${stage}`)
      if (stage === 2){
        this.fetchQuestions()
      }
    },
    // 获取问题
    async fetchQuestions() {
      try {
        // 把每张照片转成 base64
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );

        const response = await axios.post('http://127.0.0.1:5000/generate-questions', {
          photos: base64Photos,  // 发送 Base64 编码图片
          narratives: this.userNarratives[1],  // 获取 Stage 1 的口述文本
        });

        this.questions = response.data.questions || [];
      } catch (error) {
        console.error("Error fetching questions:", error);
      }
    },
    convertToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(file); // 直接读取为 Base64
      });
    },

    startResize(e) {
      this.isResizing = true
      this.startY = e.clientY
      this.startHeight = this.photoPanelHeight
      document.addEventListener('mousemove', this.doResize)
      document.addEventListener('mouseup', this.stopResize)
    },
    addPhoto() {
      // this.photos.push({})
      this.$refs.fileInput.click()
      console.log('已添加一个新的照片面板')
    },
    triggerFileInput(index) {
      this.uploadTargetIndex = index
      this.$refs.fileInput.click()
    },
    confirmUpload() {
      if (this.photos.every(photo => !photo.file)) {
        alert("请先选择图片！")
        return
      }
      console.log("准备上传的图片：", this.photos.map(p => p.name))
      // 未来在这里调用 Qwen API 或上传到服务器
    },
    handleFileChange(event) {
      const files = Array.from(event.target.files)
      if (!files.length) return

      const file = files[0]
      const newPhoto = {
        file,
        url: URL.createObjectURL(file),
        name: file.name,
      }

      // ✅ 如果点击的是指定槽位，则替换那一项
      if (this.uploadTargetIndex !== null) {
        this.photos[this.uploadTargetIndex] = newPhoto
        this.uploadTargetIndex = null
      } else {
        // ✅ 否则添加新照片
        this.photos.push(newPhoto)
      }

      console.log('已选择图片：', file.name)
      event.target.value = ''
    },

    doResize(e) {
      if (!this.isResizing) return
      const diff = e.clientY - this.startY
      const newHeight = Math.min(Math.max(200, this.startHeight + diff), 500)
      this.photoPanelHeight = newHeight
    },
    stopResize() {
      this.isResizing = false
      document.removeEventListener('mousemove', this.doResize)
      document.removeEventListener('mouseup', this.stopResize)
    },
    handleTextSelection() {
      const selection = window.getSelection()
      if (selection.toString()) {
        this.selectedText = selection.toString()
      }
    },
    toggleHighlight(index) {
      const idx = this.highlightedTexts.indexOf(index)
      if (idx > -1) this.highlightedTexts.splice(idx, 1)
      else this.highlightedTexts.push(index)
    },
    calculateMemoryMetrics() {
      const stage = this.currentStage
      const content = this.userNarratives[stage]

      // ✅ 将当前Stage的内容“保存”下来
      // （这里示范打印，后续你可以改为上传或进一步处理）
      console.log(`Stage ${stage} 的口述内容已保存：`, content)

      // （可选）如果希望用户看到提示
      this.$message?.success?.(`第 ${stage} 阶段的口述内容已保存`) 
      // 或者用 alert:
      alert(`第 ${stage} 阶段的口述内容已保存`)
    },
    generateImages() {
      const narrative = this.userNarratives[2]; // 获取 Stage 2 的口述文本
      // 先调用Qwen API分句，并生成文生图的prompt，再调用Kling根据prompt和原始输入图像生成新图片
      console.log('触发图片生成')
    },
    reselectText() {
      this.highlightedTexts = []
      this.userNarratives[this.currentStage] = ''
      console.log('已清空用户口述内容')
    },
    showTextInput(index) {
      this.questions[index].showInput = true
    },
    skipQuestion(index) {
      this.questions[index].answered = true
      if (index < this.questions.length - 1) this.currentQuestionIndex = index + 1
    },
    // submitAnswer(index) {
    //   if (this.questions[index].answer.trim()) {
    //     this.questions[index].answered = true
    //     this.questions[index].showInput = false
    //     if (index < this.questions.length - 1) this.currentQuestionIndex = index + 1
    //   }
    // },
    // 处理用户回答问题
    submitAnswer(index) {
      const question = this.questions[index];
      if (!question.answer.trim()) return; // 如果答案为空不提交

      question.answered = true;
      question.answer = question.answer.trim();
      question.showInput = false; // 关闭当前输入框

      // 自动切换到下一个未回答的问题
      for (let i = index + 1; i < this.questions.length; i++) {
        if (!this.questions[i].answered) {
          this.currentQuestionIndex = i;
          return;
        }
      }
      // 如果所有问题都已回答，则保持最后一个
      this.currentQuestionIndex = index;
    },
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.photo-story-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f7f8fa;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  overflow: hidden;
}

/* 顶部导航 */
.app-header {
  height: 60px;
  background: linear-gradient(135deg, #c3c9e8 0%, #d4c5e0 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 18px;
  font-weight: 600;
  color: white;
}

.logo-icon {
  font-size: 24px;
}

.header-nav {
  display: flex;
  gap: 32px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: rgba(255, 255, 255, 0.8);
  position: relative;
}

.nav-item.active {
  color: white;
}

.nav-item.active::after {
  content: '';
  position: absolute;
  bottom: -20px;
  left: 0;
  right: 0;
  height: 3px;
  background: white;
  border-radius: 2px;
}

.nav-number {
  width: 24px;
  height: 24px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.nav-item.active .nav-number {
  background: white;
  color: #9ca3db;
}

.nav-check {
  color: #4caf50;
  margin-left: 4px;
}

.header-right {
  display: flex;
  gap: 12px;
}

.save-btn, .export-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.save-btn:hover, .export-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 主内容区 */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧边栏 */
.sidebar {
  width: 240px;
  background: white;
  border-right: 1px solid #e8e8e8;
  padding: 20px;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-section h3 {
  font-size: 14px;
  color: #333;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.chapter-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.chapter-item {
  padding: 10px 12px;
  background: #f5f6f7;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #666;
}

.chapter-item.active {
  background: linear-gradient(135deg, #e8ebf7, #ede8f5);
  color: #7c83b9;
  font-weight: 500;
}

.chapter-item:hover {
  background: #efefef;
}

.chapter-icon {
  font-size: 16px;
}

.add-chapter-btn {
  width: 100%;
  padding: 10px;
  background: transparent;
  border: 2px dashed #d0d0d0;
  border-radius: 6px;
  color: #999;
  cursor: pointer;
  transition: all 0.3s;
}

.add-chapter-btn:hover {
  border-color: #9ca3db;
  color: #9ca3db;
}

/* 中间内容区 - 弹性布局 */
.content-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
}

/* 面板头部通用样式 */
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h2,
.panel-header h3 {
  font-size: 16px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.panel-controls {
  display: flex;
  gap: 8px;
}

.control-btn {
  padding: 6px 12px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  color: #666;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.control-btn:hover {
  background: #f5f5f5;
  border-color: #9ca3db;
  color: #9ca3db;
}

.control-btn.primary {
  background: linear-gradient(135deg, #c3c9e8, #d4c5e0);
  color: white;
  border: none;
}

.control-btn.primary:hover {
  opacity: 0.9;
}

/* 照片面板 - 紧凑设计 */
.photo-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
}

.photo-grid {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 12px;
}

.photo-slot {
  width: 120px;
  height: 120px;
  position: relative;
}

.photo-placeholder {
  width: 100%;
  height: 100%;
  background: #f5f6f7;
  border: 2px dashed #d0d0d0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
}

.photo-placeholder:hover {
  border-color: #9ca3db;
  background: #fafbfc;
}

.photo-number {
  font-size: 24px;
  color: #d0d0d0;
  font-weight: 600;
}

.add-icon {
  font-size: 20px;
  color: #d0d0d0;
  margin-top: 4px;
}

.photo-caption {
  text-align: center;
  color: #666;
  font-size: 13px;
}

.photo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

/* 可拖拽分隔条 */
.resize-handle {
  height: 12px;
  margin: 8px 0;
  cursor: ns-resize;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resize-handle:hover .handle-line,
.resize-handle.resizing .handle-line {
  background: #9ca3db;
}

.handle-line {
  width: 60px;
  height: 3px;
  background: #e0e0e0;
  border-radius: 2px;
  transition: background 0.2s;
}

/* 叙事文本 */
.narrative-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.narrative-content {
  flex: 1;
  line-height: 1.8;
  color: #444;
  font-size: 15px;
  padding: 16px;
  background: #fafbfc;
  border-radius: 6px;
  overflow-y: auto;
  user-select: text;
}

.narrative-content p {
  margin: 0;
}

.narrative-content span {
  cursor: pointer;
  transition: all 0.2s;
  padding: 2px 4px;
  border-radius: 3px;
}

.narrative-content span:hover {
  background: #e8ebf7;
}

.narrative-content span.highlighted {
  background: #ffe4b5;
  color: #333;
  font-weight: 500;
}

/* AI助手 */
.ai-assistant {
  width: 360px;
  background: white;
  border-left: 1px solid #e8e8e8;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  flex-shrink: 0;
}

.assistant-header {
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.assistant-header h3 {
  font-size: 16px;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-indicator {
  font-size: 12px;
  color: #4caf50;
}

.progress-section {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

.progress-bar {
  height: 6px;
  background: #f0f2f5;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #c3c9e8, #d4c5e0);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 12px;
  color: #999;
}

.questions-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.question-card {
  background: #f9fafb;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  transition: all 0.3s;
}

.question-card.active {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.question-card.answered {
  opacity: 0.7;
}

.question-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.question-number {
  width: 24px;
  height: 24px;
  background: #c3c9e8;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}

.answered-badge {
  font-size: 12px;
  color: #4caf50;
}

.question-text {
  color: #333;
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 12px;
}

.answer-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #f5f5f5;
}

.text-btn {
  border-color: #c3c9e8;
  color: #7c83b9;
}

.voice-btn {
  border-color: #d4c5e0;
  color: #9c7cb9;
}

.skip-btn {
  color: #999;
}

.text-input-area {
  margin-top: 12px;
}

.text-input-area textarea {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 13px;
  resize: vertical;
  font-family: inherit;
}

.text-input-area textarea:focus {
  outline: none;
  border-color: #c3c9e8;
}

.submit-btn {
  margin-top: 8px;
  padding: 6px 16px;
  background: #c3c9e8;
  color: white;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}

.answer-display {
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 8px;
}

.answer-display p {
  font-size: 13px;
  color: #666;
}

.update-narrative-btn {
  margin: 20px;
  padding: 12px;
  background: linear-gradient(135deg, #c3c9e8, #d4c5e0);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
}

.update-narrative-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(195, 201, 232, 0.4);
}

.narrative-input {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.8;
  color: #444;
  background: #fafbfc;
  font-family: inherit;
  padding: 8px;
  border-radius: 6px;
}

.narrative-input::placeholder {
  color: #aaa;
  font-style: italic;
}

</style>