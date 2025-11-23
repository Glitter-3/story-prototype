<template>
  <div class="photo-story-container">
    <header class="app-header">
      <div class="header-left">
        <div class="logo">
          <span class="logo-icon">📸</span>
          <span class="logo-text">Photo Story AI</span>
        </div>
      </div>

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
      </div>
      <div v-if="currentStage === 5" style="text-align: center; margin-top: 2px;">
        <button 
          class="control-btn primary"
          @click="saveExperimentLog"
          style="padding: 6px 8px; font-size: 12px; background: #ffffff; color: #666666;">
          保存日志
        </button>
      </div>
    </header>

    <div class="main-content">
      <section class="content-area" ref="contentArea">
        <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
          <div class="panel-header">
            <h2>📷 照片面板</h2>
            <div class="panel-controls">
              <input 
                type="file" 
                ref="fileInput"
                multiple
                accept="image/*"
                @change="handleFileChange"
                style="display: none;"
              />
              <button button v-if="currentStage === 1" class="control-btn" @click="addPhoto">➕ 添加照片</button>
              <button button v-if="currentStage === 1" class="control-btn" @click="confirmUpload">确认上传图片</button>

            </div>
          </div>
          <div v-if="currentStage !== 3 && currentStage !== 4 && currentStage !== 5" class="photo-grid">
            <div class="photo-slot" v-for="(photo, index) in photos" :key="index">
              <div class="photo-placeholder" @click="triggerFileInput(index)" v-if="currentStage === 1">
                <template v-if="photo.url">
                  <img :src="photo.url" class="photo-preview" alt="预览图片" />
                </template>
                <template v-else>
                  <span class="photo-number">{{ index + 1 }}</span>
                  <span class="add-icon">+</span>
                </template>
              </div>

              <div class="photo-placeholder" v-else>
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

          <div v-else-if="currentStage === 3 || currentStage === 4" class="split-container">
            <div class="split-title">🎞️ 原照片集</div>

            <div class="top-panel">
              <div class="photo-grid">
                <div class="photo-slot" v-for="(photo, index) in photos" :key="'orig-'+index">
                  <div class="photo-placeholder">
                    <template v-if="photo.url">
                      <img :src="photo.url" class="photo-preview" alt="原始图片" />
                    </template>
                    <template v-else>
                      <span class="photo-number">{{ index + 1 }}</span>
                      <span class="add-icon">+</span>
                    </template>
                  </div>
                </div>
              </div>
            </div>

            <div class="bottom-panel">
              <div class="split-title">🪄 AI 增强照片</div>
              <div class="photo-grid ai-photo-grid">
                <div class="photo-slot-ai" v-for="(ap, idx) in aiPhotos" :key="'ai-'+idx">
                  <div class="photo-placeholder ai-placeholder" 
                       @click="onClickAiSlot(idx)"
                       @mouseover="onPhotoHover(idx)"
                       @mouseleave="onPhotoLeave">
                    <span class="ai-photo-label">{{ getLetterIndex(idx) }}</span>
                    <span v-if="ap.iterationLabel" class="ai-photo-iter-label">{{ ap.iterationLabel }}</span>
                    <template v-if="ap.url">
                      <img :src="ap.url" class="photo-preview" alt="AI增强图片" />
                    </template>
                    <template v-else>
                      <span class="photo-number">{{ idx + 1 }}</span>
                      <span class="add-icon">+</span>
                    </template>
                  </div>
                  <button 
                    v-if="currentStage === 4" 
                    class="edit-photo-btn" 
                    @click="openSuggestionModal(idx)"
                    :disabled="iterationStopped"> ✏️ 建议
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-else-if="currentStage === 5" class="split-container">
            <div class="split-title">🎞️ 原照片集</div>

            <div class="top-panel">
              <div class="photo-grid">
                <div class="photo-slot" v-for="(photo, index) in photos" :key="'orig-'+index">
                  <div class="photo-placeholder">
                    <template v-if="photo.url">
                      <img :src="photo.url" class="photo-preview" alt="原始图片" />
                    </template>
                    <template v-else>
                      <span class="photo-number">{{ index + 1 }}</span>
                      <span class="add-icon">+</span>
                    </template>
                  </div>
                </div>
              </div>
            </div>

            <div class="bottom-panel">
              <div v-if="currentStage === 5" style="text-align: center; margin-bottom: 10px;">
                <button 
                  class="control-btn primary" 
                  @click="generateAiVideo"
                  :disabled="isGeneratingVideo">
                  {{ isGeneratingVideo ? '生成中…' : '🎬 生成最终视频' }}
                </button>
                <span v-if="videoGenerationError" style="color: red; font-size: 12px; margin-left: 8px;">
                  {{ videoGenerationError }}
                </span>
              </div>              
              <div class="split-title">🎬 AI 增强视频</div>
              <div class="video-slot">
                <video 
                  v-if="aiVideo.url" 
                  :src="aiVideo.url" 
                  controls 
                  style="width:100%; border-radius:6px; border:1px solid #ccc;">
                </video>
                <div v-else class="video-placeholder" 
                    style="display:flex; justify-content:center; align-items:center; height:100px; border:1px dashed #ccc; border-radius:6px; color:#666;">
                  <span>AI 视频占位</span>
                </div>

              </div>
            </div>
          </div>

        </div>

        <div 
          class="resize-handle" 
          @mousedown="startResize"
          :class="{ 'resizing': isResizing }">
       <div class= "handle-line"></div>
        </div>

        <div class="narrative-section" :style="{ flex: 1 }">
          <div class="panel-header">
            <h3>📝 用户口述</h3>
            <div class="panel-controls">
              <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
              <button class="control-btn" @click="reselectText">🔄 重新口述</button>

              <button v-if="currentStage === 3" class="control-btn" @click="generateImages">图像补全</button>
              </div>
          </div>
          
        <div
            ref="editableNarrative"
            class="narrative-input"
            contenteditable="true"
            @input="onEditableInput"
            @keydown="onEditableKeydown"
            :placeholder="'请在此输入您对这阶段照片的描述、回忆或故事……'"
            style="white-space: pre-wrap; overflow-y: auto; min-height: 160px; border: 1px solid #ccc; padding: 10px; border-radius: 6px; color: black;"
          ></div>

        </div>
      </section>

      <aside class="ai-assistant" v-if="currentStage !== 1 && currentStage !== 5">
        <div class="assistant-header">
          <h3>🤖 AI创作助手</h3>
          <span class="status-indicator">● 在线</span>
        </div>

        <div class="progress-section" v-if="currentStage === 2 || currentStage === 4">
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
          </div>
          <span class="progress-text" v-if="currentStage === 4">
             已迭代 {{ iterationCount - 1 }} 轮
          </span>
          <span class="progress-text" v-if="currentStage === 2">
            {{ answeredCount }}/{{ questions.length }} 问题已回答
          </span>

        </div>

        <div 
          v-if="currentStage === 3 || currentStage === 4" 
          class="assistant-integration-result" 
          :style="{ 'max-height': aiResultHeight + 'px', 'height': aiResultHeight + 'px' }"
          style="margin:10px 0; padding:10px; border-radius:6px; border:1px dashed #d0d7de; background:#fafafa; position: relative; overflow: hidden; display: flex; flex-direction: column;"
        >
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; flex-shrink: 0;">
            <strong>🧾 my photo story</strong>
            <div style="display:flex; gap:8px; align-items:center;">
              <template v-if="currentStage === 3 || currentStage === 4">
                <button
                  v-if="!assistantEditMode && (assistantIntegratedText || assistantUpdatedText)"
                  class="control-btn"
                  @click="startEditAssistantText"
                  style="padding:4px 8px; font-size:12px;"
                >修改</button>

                <span v-if="assistantEditMode" style="display:flex; gap:6px;">
                  <button class="control-btn primary" @click="confirmAssistantEdit" :disabled="isUpdatingText" style="padding: 4px 4px; font-size: 14px;">
                    确认
                  </button>
                  <button class="control-btn primary" @click="cancelAssistantEdit" :disabled="isUpdatingText" style="padding: 4px 4px; font-size: 14px;">
                    取消
                  </button>
                </span>

                <span v-if="assistantEditedByUser" style="font-size:12px; color:#667eea; margin-left:6px;">已编辑</span>
              </template>
            </div>
            <button 
              v-if="currentStage === 4"
              class="control-btn"
              @click="generateNewImagesFromNarrative"
              :disabled="iterationStopped || !assistantUpdatedText" title="根据新的叙事文本（紫色部分）生成新图片"
              style="padding: 4px 8px; font-size: 12px;">
              新一轮图像更新
            </button>
            <div v-else style="font-size:12px; color:#666;">
              <span v-if="integrating">整合中...</span>
              <span v-if="isUpdatingText">文本更新中...</span>
            </div>
          </div>
          
          <div 
            v-if="!assistantEditMode && (assistantIntegratedText || assistantUpdatedText)" 
            v-html="highlightedStoryText"
            style="white-space:pre-wrap; overflow:auto; color:#222; line-height:1.6; flex: 1; min-height: 0;"
          >
            </div>

          <div 
            v-else-if="assistantEditMode" 
            style="flex: 1; display: flex; flex-direction: column; min-height: 0;"
          >
            <textarea
              v-model="assistantEditBuffer"
              rows="6"
              style="
                flex: 1; 
                font-size: 14px; 
                padding: 10px; 
                border: 1px solid #ccc; 
                border-radius: 4px; 
                resize: vertical;
                min-height: 0;
              "
              placeholder="请在此编辑整合后的照片故事……"
            ></textarea>
          </div>

          <div 
            v-else 
            style="color:#888; font-size:13px; flex: 1; display: flex; align-items: center;"
          >
            尚无整合结果，点击下方「整合文本」或回答问题后再试
          </div>
          
          <div 
            class="resize-handle-ai" 
            @mousedown="startResizeAiResult"
            :class="{ 'resizing': isResizingAiResult }">
            <div class= "handle-line"></div>
          </div>
        </div>

        <div v-if="currentStage === 4" class="ai-modify-section" style="margin:10px 0; text-align:center; padding: 0 20px;"> 
          <button 
            class="control-btn" 
            @click="fetchStage4Questions" 
            :disabled="isFetchingS4Questions || iterationStopped" style="width: 100%; margin-bottom: 10px;"
          >
            {{ isFetchingS4Questions ? '获取中...' : '获取新一轮提问' }} </button>
        </div>


        <div class="questions-container" v-if="currentStage === 2">
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
              <button class="action-btn text-btn" @click="showTextInput(index, 'questions')">📝 文字输入</button>             
              <button class="action-btn skip-btn" @click="skipQuestion(index, 'questions')">⏭️ 跳过</button>
            </div>
            
            <div v-if="question.showInput && !question.answered" class="text-input-area">
              <textarea
                v-model="question.answer"
                placeholder="请输入您的回答..."
                rows="3"></textarea>
              <button class="submit-btn" @click="submitAnswer(index, 'questions')">确认</button>
            </div>
            
            <div v-if="question.answered && question.answer" class="answer-display">
              <p>{{ question.answer }}</p>
            </div>

            
          </div>
        </div>
        
        <div class="questions-container" v-if="currentStage === 4 && stage4Questions.length > 0" style="padding-top: 0;">
          <div 
            v-for="(question, index) in stage4Questions" 
            :key="'s4-'+index"
            class="question-card"
            :class="{ active: currentQuestionIndex === index, answered: question.answered }">
            
            <div class="question-header">
              <span class="question-number">{{ index + 1 }}</span>
              <span v-if="question.answered" class="answered-badge">✓</span>
            </div>
            
            <p class="question-text">{{ question.text }}</p>
            
            <div v-if="currentQuestionIndex === index && !question.answered" class="answer-actions">
              <button class="action-btn text-btn" @click="showTextInput(index, 'stage4Questions')">📝 文字输入</button>             
              <button class="action-btn skip-btn" @click="skipQuestion(index, 'stage4Questions')">⏭️ 跳过</button>
            </div>
            
            <div v-if="question.showInput && !question.answered" class="text-input-area">
              <textarea
                v-model="question.answer"
                placeholder="请输入您的回答..."
                rows="3"></textarea>
              <button class="submit-btn" @click="submitAnswer(index, 'stage4Questions')">确认</button>
            </div>
            
            <div v-if="question.answered && question.answer" class="answer-display">
              <p>{{ question.answer }}</p>
            </div>
          </div>
        </div>


        <div v-if="currentStage === 4" style="display:flex; flex-direction:column; gap:8px; margin: 0 20px 20px 20px;">
          <button 
            class="control-btn" 
            @click="stopIteration" 
            style="margin: 0; background: #f5f5f5; width: 100%;" 
            :disabled="iterationStopped"> 已满意，终止迭代
          </button>
        </div>

        <button 
          v-if="currentStage === 2" 
          class="control-btn primary"
          @click="fetchQuestions">
          开始提问
        </button>

        <button 
          v-if="currentStage === 3 || (currentStage === 4 && stage4Questions.length > 0 && answeredCount > 0)" class="control-btn primary"
          :disabled="integrating || isUpdatingText || iterationStopped" @click="currentStage === 3 ? integrateText() : updateText()">
          {{ integrating ? '整合中...' : (isUpdatingText ? '更新中...' : (currentStage === 3 ? '整合文本' : '整合文本')) }}
        </button>
        
    <div v-if="showSuggestionModal" class="suggestion-modal-backdrop">
      <div class="suggestion-modal">
        <h3>对照片 {{ getLetterIndex(suggestionForPhotoIndex) }} 的建议</h3>
        <textarea
          v-model="currentSuggestionText"
          rows="5"
          placeholder="请输入你对这张照片的具体建议，例如：色调更暖、人物锐化..."
        ></textarea>
        <div class="modal-actions">
          <button class="control-btn" @click="showSuggestionModal = false">取消</button>
          <button class="control-btn primary" @click="submitIndividualPhotoUpdate" :disabled="!currentSuggestionText.trim() || isUpdatingPhoto">
            {{ isUpdatingPhoto ? '更新中...' : '立即更新' }}
          </button>
        </div>
      </div>
    </div>

      </aside>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
import { toRaw } from 'vue'

export default {
  name: 'PhotoStoryAI',
  data() {
    return {
      // === 实验日志字段 ===
      userId: null,
      sessionId: null,
      startTime: null,
      stageTimestamps: {
        1: null, 2: null, 3: null, 4: null, 5: null
      },
      stage2QA: [],
      stage4QA: [],
      originalPhotosBase64: [],
      aiPhotosHistory: [],
      stage4Iterations: [],
      stage4Modifications: [],
      userAgent: navigator.userAgent,
      screenResolution: `${screen.width}x${screen.height}`,

      // === 原有状态 ===
      currentStage: 1,
      photoPanelHeight: 360,
      isResizing: false,
      aiVideo: { url: '' },
      iterationCount: 1,
      // maxIterations: 3, // ✅ [修改 B.1] 移除
      startY: 0,
      startHeight: 0,
      highlightedTexts: [],
      aiSuggestion: '',
      modificationInProgress: false,
      selectedText: '',
      integrating: false,
      assistantIntegratedText: '',
      photos: [],
      aiPhotos: [],
      allPhotos: [],
      uploadTargetIndex: null,
      userNarratives: { 1: '', 2: '', 3: '', 4: '', 5: '' },
      currentQuestionIndex: 0,
      questions: [],
      sentencePairs: [],
      stage4Questions: [],
      assistantUpdatedText: '',
      isFetchingS4Questions: false,
      isUpdatingText: false,
      aiResultHeight: 220,
      isResizingAiResult: false,
      startY_ai: 0,
      startHeight_ai: 0,
      iterationStopped: false,
      showSuggestionModal: false,
      suggestionForPhotoIndex: null,
      currentSuggestionText: '',
      isUpdatingPhoto: false,
      // 视频生成状态
      isGeneratingVideo: false,
      videoGenerationError: null,
      // stage 3&4 整合文本用户修改功能
      assistantEditMode: false,        // 是否处于编辑模式（显示 textarea）
      assistantEditBuffer: '',        // 编辑缓冲文本（textarea 的 v-model）
      assistantEditedByUser: false,   // 标记用户是否已手动编辑过 AI 文本
      stage3Modifications: [],        // 记录 Stage3 的每次用户修改（timestamp, before, after）
      
      highlightedSentence: null, // ✅ [修改 C.2] 新增高亮状态
    }
  },
  computed: {
    // ✅ [修改 C.5] 新增 computed 属性用于高亮
    highlightedStoryText() {
      // Get base texts and escape them for security before v-html
      let text = this.escapeHtml(this.assistantIntegratedText || '');
      const updatedText = this.escapeHtml(this.assistantUpdatedText || '');
      
      // Apply highlight if a sentence is hovered
      if (this.highlightedSentence) {
        const sentence = this.escapeHtml(this.highlightedSentence);
        // Must escape the sentence for the regex to handle special chars
        const regex = new RegExp(this.escapeRegExp(sentence), 'g'); // 'g' for all occurrences
        // Use inline style for simplicity, avoiding scoped CSS issues with v-html
        text = text.replace(regex, `<span style="background-color: #fff8c4; border-radius: 3px; padding: 1px 0;">${sentence}</span>`);
      }
      
      // Append the (already styled) updated text
      if (updatedText) {
        // Re-add the purple color span for the updated part
        text += ` <span style="color:#667eea; margin-top: 5px; display: inline-block;">${updatedText}</span>`;
      }
      
      return text;
    },
    progressPercentage() {
      if (this.currentStage === 4) {
        // ✅ [修改 B.1] 移除 maxIterations 依赖, 变成只增不减的进度
        return 0; // Or some other logic if needed, maybe hide it?
        // return ((this.iterationCount - 1) / this.maxIterations) * 100 
      }
      if (this.currentStage === 2 && this.questions.length > 0) {
        return (this.answeredCount / this.questions.length) * 100
      }
      return 0
    },
    answeredCount() {
      const list = this.currentStage === 2 ? this.questions : this.stage4Questions;
      if (!list) return 0;
      return list.filter(q => q.answered).length
    }
  },
  mounted() {
    const uuid = () => ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
      (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
    this.sessionId = uuid();
    this.startTime = new Date().toISOString();
    this.userId = localStorage.getItem('userId') || uuid();
    localStorage.setItem('userId', this.userId);
    console.log(`[Log] Session started: ${this.sessionId}`);
  },
  methods: {
    // ✅ [修改 C.5] 新增正则转义辅助函数
    escapeRegExp(string) {
      // $& means the whole matched string
      return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); 
    },
    // ✅ [修改 C.3] 新增悬停处理方法
    onPhotoHover(idx) {
      if (this.aiPhotos[idx] && this.aiPhotos[idx].sentence) {
        this.highlightedSentence = this.aiPhotos[idx].sentence;
      }
    },
    onPhotoLeave() {
      this.highlightedSentence = null;
    },
    onEditableInput(e) {
      const el = this.$refs.editableNarrative;
      if (!el) return;
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) {
        this.userNarratives[this.currentStage] = el.innerHTML;
        return;
      }
      const range = sel.getRangeAt(0);
      if (!range.collapsed) {
        range.deleteContents();
        sel.removeAllRanges();
        sel.addRange(range);
      }
      let node = range.startContainer;
      const anchorEl = node.nodeType === 3 ? node.parentElement : node;

      const isHistoryNode = (n) => {
        if (!n) return false;
        const inline = (n.style && n.style.color) ? n.style.color.toLowerCase() : '';
        if (inline && inline.includes('#7c83b9')) return true;
        try {
          const comp = window.getComputedStyle(n).color;
          if (comp === 'rgb(124, 131, 185)') return true;
        } catch (err) {}
        return false;
      };

      if (isHistoryNode(anchorEl)) {
        this.splitHistorySpanAtRange(anchorEl, range);
      }

      this.userNarratives[this.currentStage] = el.innerHTML;
    },
    switchStage(stage) {
      if (!this.stageTimestamps[stage]) {
        this.stageTimestamps[stage] = new Date().toISOString();
      }
      this.currentStage = stage;

      if (stage > 1 && !this.userNarratives[stage]) {
        const prevHtml = this.userNarratives[stage - 1] || '';
        const tmp = document.createElement('div');
        tmp.innerHTML = prevHtml;
        const prevText = tmp.textContent || tmp.innerText || '';
        if (prevText) {
          const purple = `<span style="color:#7c83b9;">${this.escapeHtml(prevText)}</span>`;
          const black = `<span style="color:#000000;">\u200B</span>`;
          this.userNarratives[stage] = purple + black;
        } else {
          this.userNarratives[stage] = '';
        }
      }

      if (stage === 4) {
        this.stage4Questions = [];
        this.assistantUpdatedText = '';
        this.aiSuggestion = '';
        this.iterationCount = 1;
        this.currentQuestionIndex = 0;
        this.iterationStopped = false;
      }
      if (stage === 2) {
        this.currentQuestionIndex = 0;
      }
      if (stage === 3) {
        this.assistantUpdatedText = '';
      }

      this.$nextTick(() => {
        const editor = this.$refs.editableNarrative;
        if (!editor) return;
        editor.innerHTML = this.userNarratives[stage] || '';

        let blackSpan = null;
        const spans = Array.from(editor.querySelectorAll('span'));
        for (const s of spans.reverse()) {
          const col = (s.style && s.style.color) ? s.style.color.toLowerCase() : window.getComputedStyle(s).color;
          if (col && (col.includes('#000000') || col.includes('rgb(0, 0, 0)') || col.includes('0, 0, 0'))) {
            blackSpan = s;
            break;
          }
        }
        if (!blackSpan) {
          const s = document.createElement('span');
          s.style.color = '#000000';
          s.innerHTML = '\u200B';
          editor.appendChild(s);
          blackSpan = s;
        }
        this.placeCaretInElement(blackSpan);
      });

      console.log(`已切换到 Stage ${stage}`);
      this.$nextTick(() => {
        this.userNarratives[stage] = this.$refs.editableNarrative?.innerHTML || '';
      });
    },
    splitHistorySpanAtRange(purpleSpan, range) {
      const tmp = document.createElement('div');
      tmp.appendChild(purpleSpan.cloneNode(true));
      const fullText = tmp.textContent || '';

      const preRange = document.createRange();
      preRange.setStart(purpleSpan, 0);
      try {
        preRange.setEnd(range.startContainer, range.startOffset);
      } catch (err) {
        preRange.selectNodeContents(purpleSpan);
        preRange.setEnd(purpleSpan, 0);
      }
      const leftText = preRange.toString();
      const rightText = fullText.slice(leftText.length);
      const parent = purpleSpan.parentNode;

      if (leftText) {
        const leftSpan = document.createElement('span');
        leftSpan.style.color = '#7c83b9';
        leftSpan.textContent = leftText;
        parent.insertBefore(leftSpan, purpleSpan);
      }

      const blackSpan = document.createElement('span');
      blackSpan.style.color = '#000000';
      blackSpan.innerHTML = '\u200B';
      parent.insertBefore(blackSpan, purpleSpan);

      if (rightText) {
        const rightSpan = document.createElement('span');
        rightSpan.style.color = '#7c83b9';
        rightSpan.textContent = rightText;
        parent.insertBefore(rightSpan, purpleSpan);
      }

      parent.removeChild(purpleSpan);
      this.placeCaretInElement(blackSpan);
    },
    placeCaretInElement(el) {
      if (!el) return;
      el.focus && el.focus();
      const range = document.createRange();
      range.selectNodeContents(el);
      range.collapse(false);
      const sel = window.getSelection();
      sel.removeAllRanges();
      sel.addRange(range);
    },
    escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },
    isHistoryNode(node) {
      if (!node) return false;
      if (node.nodeType !== 1) return false;
      const inline = (node.style && node.style.color) ? node.style.color.toLowerCase() : '';
      if (inline && inline.includes('#7c83b9')) return true;
      try {
        const comp = window.getComputedStyle(node).color;
        if (comp === 'rgb(124, 131, 185)') return true;
      } catch (err) {}
      return false;
    },
    onEditableKeydown(e) {
      const editor = this.$refs.editableNarrative;
      if (!editor) return;
      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);

      if (!range.collapsed) {
        setTimeout(() => {
          this.userNarratives[this.currentStage] = editor.innerHTML;
        }, 0);
        return;
      }

      const getAnchorElement = (r) => {
        let n = r.startContainer;
        return (n.nodeType === 3 ? n.parentElement : n);
      };
      const anchorEl = getAnchorElement(range);

      if (e.key === 'Backspace') {
        const isAtStart = (() => {
          if (range.startContainer.nodeType === 3) {
            return range.startOffset === 0;
          }
          return range.startOffset === 0;
        })();
        if (isAtStart) {
          const prev = anchorEl.previousSibling;
          if (prev && this.isHistoryNode(prev)) {
            e.preventDefault();
            prev.parentNode.removeChild(prev);
            this.$nextTick(() => {
              this.placeCaretInElement(anchorEl);
              this.userNarratives[this.currentStage] = editor.innerHTML;
            });
            return;
          }
        }
        return;
      }

      if (e.key === 'Delete') {
        const isAtEnd = (() => {
          if (range.startContainer.nodeType === 3) {
            return range.startOffset === range.startContainer.textContent.length;
          }
          return range.startOffset === anchorEl.childNodes.length;
        })();
        if (isAtEnd) {
          const next = anchorEl.nextSibling;
          if (next && this.isHistoryNode(next)) {
            e.preventDefault();
            next.parentNode.removeChild(next);
            this.$nextTick(() => {
              this.placeCaretInElement(anchorEl);
              this.userNarratives[this.currentStage] = editor.innerHTML;
            });
            return;
          }
        }
        return;
      }
    },
    async fetchQuestions() {
      console.log('开始获取问题...')
      if (this.currentStage === 2) {
        try {
          const base64Photos = await Promise.all(
            this.photos.map(photo => this.convertToBase64(photo.file))
          );
          const response = await axios.post('http://127.0.0.1:5000/generate-questions', {
            photos: base64Photos,
            narratives: this.userNarratives[1],
          });
          this.questions = response.data.questions || [];
          this.currentQuestionIndex = 0;

          this.stage2QA = this.questions.map((q, idx) => ({
            stage: 2,
            index: idx,
            question: q.text,
            fetchedTime: new Date().toISOString()
          }));
        } catch (error) {
          console.error("Error fetching questions:", error);
        }
      }
    },
    convertToBase64(file) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = (error) => reject(error);
        reader.readAsDataURL(file);
      });
    },
    async urlToBase64(url) {
      if (!url) return null;
      try {
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Failed to fetch URL: ${url} (Status: ${response.status})`);
        }
        const blob = await response.blob();
        return new Promise((resolve, reject) => {
          const reader = new FileReader();
          reader.onloadend = () => resolve(reader.result);
          reader.onerror = (err) => {
            console.error("FileReader error:", err);
            reject(err);
          };
          reader.readAsDataURL(blob);
        });
      } catch (error) {
        console.error("Error converting URL to Base64:", url, error);
        return null;
      }
    },
    startResize(e) {
      this.isResizing = true;
      this.startY = e.clientY;
      this.startHeight = this.photoPanelHeight;
      document.addEventListener('mousemove', this.doResize);
      document.addEventListener('mouseup', this.stopResize);
    },
    addPhoto() {
      this.$refs.fileInput.click();
      console.log('已添加一个新的照片面板');
    },
    triggerFileInput(index) {
      this.uploadTargetIndex = index;
      this.$refs.fileInput.click();
    },
    confirmUpload() {
      if (this.photos.every(photo => !photo.file)) {
        alert("请先选择图片！");
        return;
      }
      console.log("准备上传的图片：", this.photos.map(p => p.name));
    },
    async uploadPhoto(file) {
      const formData = new FormData();
      formData.append('photo', file);

      try {
        const resp = await axios.post('http://127.0.0.1:5000/upload-photo', formData);
        if (resp.data.success && resp.data.url) {
          return resp.data.url; // e.g. "/static/uploads/abc123.jpg"
        } else {
          throw new Error(resp.data.message || 'Upload failed');
        }
      } catch (err) {
        console.error('Photo upload failed:', err);
        alert('图片上传失败，请重试');
        return null;
      }
    },
    async handleFileChange(event) {
      const files = Array.from(event.target.files);
      if (!files.length) return;
      const file = files[0];

      // ✅ 先上传，获取持久化 URL
      const uploadedUrl = await this.uploadPhoto(file);
      if (!uploadedUrl) return;

      const newPhoto = {
        file, // 仍保留 file（供 base64 生成用）
        url: uploadedUrl, // ← 关键！不再是 blob:
        name: file.name,
      };

      if (this.uploadTargetIndex !== null) {
        this.$set(this.photos, this.uploadTargetIndex, newPhoto);
        this.uploadTargetIndex = null;
      } else {
        this.photos.push(newPhoto);
      }

      console.log('已上传图片：', file.name, '→', uploadedUrl);
      event.target.value = '';
    },
    doResize(e) {
      if (!this.isResizing) return;
      const diff = e.clientY - this.startY;
      const newHeight = Math.min(Math.max(200, this.startHeight + diff), 500);
      this.photoPanelHeight = newHeight;
    },
    stopResize() {
      this.isResizing = false;
      document.removeEventListener('mousemove', this.doResize);
      document.removeEventListener('mouseup', this.stopResize);
    },
    handleTextSelection() {
      const selection = window.getSelection();
      if (selection.toString()) {
        this.selectedText = selection.toString();
      }
    },
    toggleHighlight(index) {
      const idx = this.highlightedTexts.indexOf(index);
      if (idx > -1) this.highlightedTexts.splice(idx, 1);
      else this.highlightedTexts.push(index);
    },
    calculateMemoryMetrics() {
      const stage = this.currentStage;
      const content = this.userNarratives[stage];
      console.log(`Stage ${stage} 的口述内容已保存：`, content);
      alert(`第 ${stage} 阶段的口述内容已保存`);
    },
    async integrateText() {
      if (this.currentStage !== 3) {
        alert("整合文本仅在 Stage 3 可用");
        return;
      }
      const narrative = this.userNarratives[2] || '';
      const qa_pairs = (this.questions || [])
        .filter(q => q.answered && q.answer && q.answer.trim())
        .map(q => ({ question: q.text, answer: q.answer.trim() }));
      if (!narrative && qa_pairs.length === 0) {
        alert("没有可供整合的口述或问答，请先在 Stage2 完成口述与回答。");
        return;
      }

      console.log("准备发往 /integrate-text 的 payload:", { narrative, qa_pairs });

      try {
        this.integrating = true;
        this.assistantIntegratedText = '';
        this.assistantUpdatedText = '';
        const resp = await axios.post('http://127.0.0.1:5000/integrate-text', {
          narrative,
          qa_pairs,
          options: { output_format: 'text' }
        }, { timeout: 120000 });

        if (resp.data && resp.data.integrated_text) {
          this.assistantIntegratedText = String(resp.data.integrated_text).trim();
          this.$message?.success?.("整合完成，已在 AI 面板显示（只读）");
        } else {
          console.error("integrate-text 返回结构异常：", resp.data);
          alert("整合失败，请查看后端日志");
        }
      } catch (err) {
        console.error("整合文本错误：", err);
        alert("整合文本时出错，请查看控制台或后端日志");
      } finally {
        this.integrating = false;
      }
    },
    // async generateImages() {
    //   if (this.currentStage !== 3) {
    //     alert("图像补全功能仅在 Stage 3 可用");
    //     return;
    //   }
    //   console.log('开始获取文生图prompt...');
    //   const narrative = this.assistantIntegratedText;
    //   if (!narrative) {
    //     alert("AI 整合结果为空，请先点击 [整合文本]");
    //     return;
    //   }
    //   try {
    //     // 1️⃣ 上传原始照片转 base64
    //     const base64Photos = await Promise.all(
    //       this.photos.map(photo => this.convertToBase64(photo.file))
    //     );
    //     // 2️⃣ 获取 Qwen 生成的 sentence_pairs
    //     const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
    //       photos: base64Photos,
    //       narrative: narrative,
    //     });
    //     this.sentencePairs = response.data.sentence_pairs || [];
    //     console.log('图文配对结果：', toRaw(this.sentencePairs));
    //     this.sentencePairs.sort((a, b) => a.index - b.index);
    //     alert("Qwen已完成分句与prompt生成");

    //     // 3️⃣ 过滤出需要生成的 prompt
    //     const toGenerate = this.sentencePairs.filter(p => p.prompt);
    //     if (!toGenerate.length) {
    //       alert("没有需要生成的 prompt，操作结束");
    //       return;
    //     }

    //     this.aiPhotos = [];
    //     this.allPhotos = []; // ✅ 清空，重新填充

    //     // 4️⃣ 构建 payload：取前4张原图作参考（可灵要求 2~4 张）
    //     const payloadToSend = toGenerate.map(item => ({
    //       ...item,
    //       photo: base64Photos.slice(0, 4)
    //     }));

    //     console.log(`[Stage 3] 准备发送 ${payloadToSend.length} 个生成任务...`);
    //     const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
    //       sentence_pairs: payloadToSend
    //     }, { timeout: 600000 });

    //     if (!(genResp.data && genResp.data.results)) {
    //       console.error("generate-images 返回异常：", genResp.data);
    //       alert("生成图片时出错，请查看控制台");
    //       return;
    //     }
    //     const results = genResp.data.results;
    //     console.log("生成图片结果：", results);
    //     const BACKEND_BASE = "http://127.0.0.1:5000";

    //     // ✅【关键】5️⃣ 用 for...of + await 替代 forEach —— 支持串行下载
    //     const aiMap = {};
    //     for (const res of results) {
    //       const idx = res.index;
    //       const urls = res.generated_urls || [];
    //       if (!urls.length) continue; // 跳过失败项

    //       let firstUrl = urls[0];

    //       let finalUrl = firstUrl;
    //       // 如果是可灵返回的完整 URL（如 http://127.0.0.1:5000/static/generated/xxx.jpg），直接用
    //       if (firstUrl.includes('/static/')) {
    //         finalUrl = firstUrl;
    //       } else if (firstUrl.startsWith('/')) {
    //         finalUrl = BACKEND_BASE + firstUrl;
    //       } else if (!firstUrl.startsWith('http')) {
    //         finalUrl = BACKEND_BASE + '/static/generated/' + firstUrl;
    //       } else if (!firstUrl.startsWith("data:")) {
    //         firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
    //       }
    //       // data: URL 忽略（kling 不应返回）

    //       const pair = this.sentencePairs.find(p => p.index === idx);
    //       const aiObj = {
    //         file: null,
    //         url: firstUrl,
    //         name: `ai_generated_${Date.now()}_${idx}.jpg`,
    //         prompt: res.prompt || pair?.prompt || null,
    //         origin_pair_index: idx,
    //         sentence: pair?.sentence || null,
    //         iterationLabel: `S3_Init`
    //       };
    //       this.aiPhotos.push(aiObj);
    //       aiMap[idx] = aiObj;
    //     }

    //     // 6️⃣ ✅ 构建 allPhotos（严格按叙事顺序）
    //     this.allPhotos = [];
    //     this.sentencePairs.forEach(pair => {
    //       const aiPhoto = aiMap[pair.index];

    //       if (aiPhoto) {
    //         this.allPhotos.push({
    //           type: 'ai',
    //           sourceIndex: pair.index,
    //           url: aiPhoto.url,
    //           prompt: aiPhoto.prompt,
    //           sentence: pair.sentence
    //         });
    //       } else {
    //         // fallback：找原图
    //         let fallbackUrl = null;
    //         if (pair.origin_pair_index !== undefined && this.photos[pair.origin_pair_index]) {
    //           fallbackUrl = this.photos[pair.origin_pair_index].url;
    //         } else if (this.photos.length > 0) {
    //           fallbackUrl = this.photos[0].url;
    //         }

    //         if (fallbackUrl) {
    //           this.allPhotos.push({
    //             type: 'original',
    //             sourceIndex: pair.index,
    //             url: fallbackUrl,
    //             sentence: pair.sentence
    //           });
    //         }
    //       }
    //     });

    //     // 7️⃣ 记录历史
    //     this.aiPhotosHistory.push({
    //       timestamp: new Date().toISOString(),
    //       type: 'batch',
    //       iterationLabel: `S3_Init`,
    //       count: results.length,
    //       pairs: results.map(r => ({
    //         index: r.index,
    //         prompt: r.prompt,
    //         urls: r.generated_urls
    //       }))
    //     });

    //     alert("图像生成并更新完毕，已显示在 AI 增强照片区");
    //   } catch (error) {
    //     console.error("Error generating prompts or images:", error);
    //     alert("生成图像时出错，请查看控制台");
    //   }
    // },
    async generateImages() {
      if (this.currentStage !== 3) {
        alert("图像补全功能仅在 Stage 3 可用");
        return;
      }
      console.log('开始获取文生图prompt...');
      const narrative = this.assistantIntegratedText;
      if (!narrative) {
        alert("AI 整合结果为空，请先点击 [整合文本]");
        return;
      }

      try {
        // 1️⃣ 上传原始照片转 base64
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );

        // 2️⃣ 获取 Qwen 生成的 sentence_pairs
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative,
        });
        this.sentencePairs = response.data.sentence_pairs || [];
        console.log('图文配对结果：', toRaw(this.sentencePairs));
        this.sentencePairs.sort((a, b) => a.index - b.index);
        alert("Qwen已完成分句与prompt生成");

        // 3️⃣ 过滤出需要生成的 prompt
        const toGenerate = this.sentencePairs.filter(p => p.prompt);
        if (!toGenerate.length) {
          alert("没有需要生成的 prompt，操作结束");
          return;
        }

        this.aiPhotos = [];
        this.allPhotos = [];

        // 4️⃣ 构建 payload：取前4张原图作参考（可灵要求 2~4 张）
        const payloadToSend = toGenerate.map(item => ({
          ...item,
          photo: base64Photos.slice(0, 4)
        }));

        console.log(`[Stage 3] 准备发送 ${payloadToSend.length} 个生成任务...`);
        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: payloadToSend
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results)) {
          console.error("generate-images 返回异常：", genResp.data);
          alert("生成图片时出错，请查看控制台");
          return;
        }

        const results = genResp.data.results;
        console.log("生成图片结果：", results);
        const BACKEND_BASE = "http://127.0.0.1:5000";

        // ✅【核心】5️⃣ 构建 aiMap，确保 url 是可持久访问的本地路径
        const aiMap = {};
        for (const res of results) {
          const idx = res.index;
          const urls = res.generated_urls || [];
          if (!urls.length) continue; // 跳过失败项

          let firstUrl = urls[0];

          // ✅【关键修复】统一规范化 URL：确保它指向 /static/generated/ 下的本地资源
          let finalUrl = '';
          if (firstUrl.includes('/static/')) {
            // 已是本地路径（绝对或相对），补全为完整 URL
            if (firstUrl.startsWith('/')) {
              finalUrl = BACKEND_BASE + firstUrl;
            } else if (firstUrl.startsWith('http')) {
              finalUrl = firstUrl; // 已完整，如 http://127.0.0.1:5000/static/...
            } else {
              // 纯路径如 "xxx.jpg" —— 不存在，但兜底处理
              finalUrl = BACKEND_BASE + '/static/generated/' + firstUrl;
            }
          } else if (firstUrl.startsWith('/')) {
            finalUrl = BACKEND_BASE + firstUrl;
          } else if (firstUrl.startsWith('http')) {
            // ⚠️ 可能是可灵外链（如 oss.kling.ai/xxx.jpg）
            // ❗ 但 /generate-images 已调用 download_to_generated，不应出现外部 URL
            // 若出现，说明后端未保存成功 → 前端无法访问，应 fallback 或报错
            console.warn('⚠️ 检测到外部 URL（非 /static/），可能无法访问：', firstUrl);
            // 这里可选：跳过 / 显示警告 / 交由后端统一处理（推荐）
            // 我们选择：仍用它，但标记风险（真实项目应要求后端保证返回本地路径）
            finalUrl = firstUrl;
          } else if (!firstUrl.startsWith('data:')) {
            // 假设是文件名
            finalUrl = BACKEND_BASE + '/static/generated/' + firstUrl;
          } else {
            console.warn('⚠️ 忽略 data URL（不应出现）：', firstUrl);
            continue;
          }

          const pair = this.sentencePairs.find(p => p.index === idx);
          const aiObj = {
            file: null,
            url: finalUrl, // ✅ 用 finalUrl，不是 firstUrl！
            name: `ai_generated_${Date.now()}_${idx}.jpg`,
            prompt: res.prompt || pair?.prompt || null,
            origin_pair_index: idx,
            sentence: pair?.sentence || null,
            iterationLabel: `S3_Init`
          };
          this.aiPhotos.push(aiObj);
          aiMap[idx] = aiObj;
        }

        // 6️⃣ 构建 allPhotos（严格按 sentencePairs 顺序）
        this.allPhotos = [];
        for (const pair of this.sentencePairs) {
          const aiPhoto = aiMap[pair.index];
          if (aiPhoto) {
            this.allPhotos.push({
              type: 'ai',
              sourceIndex: pair.index,
              url: aiPhoto.url,
              prompt: aiPhoto.prompt,
              sentence: pair.sentence
            });
          } else {
            // fallback：找原图
            let fallbackUrl = null;
            if (pair.origin_pair_index !== undefined && this.photos[pair.origin_pair_index]) {
              fallbackUrl = this.photos[pair.origin_pair_index].url;
              // 确保原图 URL 也是完整路径（上传时已返回 /static/uploads/...）
              if (fallbackUrl && fallbackUrl.startsWith('/')) {
                fallbackUrl = BACKEND_BASE + fallbackUrl;
              }
            } else if (this.photos.length > 0) {
              fallbackUrl = this.photos[0].url;
              if (fallbackUrl && fallbackUrl.startsWith('/')) {
                fallbackUrl = BACKEND_BASE + fallbackUrl;
              }
            }
            if (fallbackUrl) {
              this.allPhotos.push({
                type: 'original',
                sourceIndex: pair.index,
                url: fallbackUrl,
                sentence: pair.sentence
              });
            }
          }
        }

        // 7️⃣ 记录历史
        this.aiPhotosHistory.push({
          timestamp: new Date().toISOString(),
          type: 'batch',
          iterationLabel: `S3_Init`,
          count: results.length,
          pairs: results.map(r => ({
            index: r.index,
            prompt: r.prompt,
            urls: r.generated_urls
          }))
        });

        alert("图像生成并更新完毕，已显示在 AI 增强照片区");
      } catch (error) {
        console.error("Error generating prompts or images:", error);
        alert("生成图像时出错，请查看控制台");
      }
    },
    reselectText() {
      this.highlightedTexts = [];
      this.userNarratives[this.currentStage] = '';
      console.log('已清空用户口述内容');
    },
    showTextInput(index, questionListKey) {
      const questions = this[questionListKey];
      if (questions && questions[index]) {
        questions[index].showInput = true;
      }
    },
    skipQuestion(index, questionListKey) {
      const questions = this[questionListKey];
      if (!questions || !questions[index]) return;
      questions[index].answered = true;

      const nextIndex = questions.findIndex((q, i) => i > index && !q.answered);
      if (nextIndex !== -1) {
        this.currentQuestionIndex = nextIndex;
      } else {
        this.currentQuestionIndex = index;
      }

      // ✅ 补 now + 记录
      const now = new Date().toISOString();
      const record = {
        stage: this.currentStage,
        index,
        question: questions[index].text,
        action: 'skipped',
        skipTime: now
      };
      if (this.currentStage === 2) this.stage2QA.push(record);
      else if (this.currentStage === 4) this.stage4QA.push(record);
    },
    submitAnswer(index, questionListKey) {
      const questions = this[questionListKey];
      if (!questions || !questions[index]) return;
      const question = questions[index];
      if (!question.answer?.trim()) return;

      // ✅ 补 now
      const now = new Date().toISOString();

      question.answered = true;
      question.answer = question.answer.trim();
      question.showInput = false;

      // ✅ 记录 QA
      const record = {
        stage: this.currentStage,
        index,
        question: question.text,
        answer: question.answer,
        answerTime: now
      };

      if (this.currentStage === 2) {
        const existing = this.stage2QA.find(r => r.index === index);
        if (existing) {
          existing.answer = question.answer;
          existing.answerTime = now;
        } else {
          this.stage2QA.push(record);
        }
      } else if (this.currentStage === 4) {
        const existing = this.stage4QA.find(r => r.index === index);
        if (existing) {
          existing.answer = question.answer;
          existing.answerTime = now;
        } else {
          this.stage4QA.push(record);
        }
      }

      const nextIndex = questions.findIndex((q, i) => i > index && !q.answered);
      this.currentQuestionIndex = nextIndex !== -1 ? nextIndex : index;
    },
    // 进入编辑模式
    startEditAssistantText() {
      // 编辑内容 = 当前整合文本 + 更新文本（拼接，保留用户 Stage4 修改）
      const currentText = (this.assistantIntegratedText + '\n' + (this.assistantUpdatedText || '')).trim();
      this._assistantBeforeEdit = this.assistantIntegratedText; // 备份原值
      this.assistantEditBuffer = currentText;
      this.assistantEditMode = true;
      this.$nextTick(() => {
        // 自动聚焦（可选）
        const textarea = this.$el.querySelector('textarea');
        if (textarea) textarea.focus();
      });
    },

    // 取消编辑，恢复原样
    cancelAssistantEdit() {
      this.assistantEditMode = false;
      this.assistantEditBuffer = '';
      delete this._assistantBeforeEdit;
    },

    // ✅ 核心：确认编辑 → 更新 assistantIntegratedText，并清空更新缓冲
    confirmAssistantEdit() {
      if (!this.assistantEditBuffer.trim()) {
        alert('内容不能为空');
        return;
      }
      // 将编辑后文本 → 覆盖原整合文本
      const beforeText = this._assistantBeforeEdit || " "; 
      this.assistantIntegratedText = this.assistantEditBuffer.trim();
      // 清空 "更新文本"（因为已合并进主文本）
      this.assistantUpdatedText = '';
      // 退出编辑模式
      this.assistantEditMode = false;
      this.assistantEditBuffer = '';
      // 标记用户主动编辑过（可用于日志/提示）
      this.assistantEditedByUser = true;

      // ✅【关键】记录用户修改（用于实验日志）
      this.stage3Modifications.push({
        timestamp: new Date().toISOString(),
        before: beforeText, // 注意：此时 before 是旧的，应提前备份
        after: this.assistantEditBuffer.trim()
      });

      this.$message?.success?.('整合文本已更新');
    },
    async fetchStage4Questions() {
      console.log('开始获取 Stage 4 问题...');
      if (this.currentStage !== 4) return;

      this.isFetchingS4Questions = true;
      this.stage4Questions = [];
      try {
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        const aiPhotoBase64s = await Promise.all(
          this.aiPhotos.map(p => this.urlToBase64(p.url))
        );
        const aiPhotoURLs = aiPhotoBase64s.filter(Boolean);

        if (aiPhotoURLs.length === 0) {
          alert("没有可供提问的 AI 图像，或无法读取 AI 图像 (CORS/Network error)");
          this.isFetchingS4Questions = false;
          return;
        }

        const response = await axios.post('http://127.0.0.1:5000/generate-stage4-questions', {
          original_photos: base64Photos,
          ai_photos_urls: aiPhotoURLs,
        });

        this.stage4Questions = response.data.questions || [];
        this.currentQuestionIndex = 0;

        this.stage4QA = this.stage4Questions.map((q, idx) => ({
          stage: 4,
          index: idx,
          question: q.text,
          fetchedTime: new Date().toISOString()
        }));
      } catch (error) {
        console.error("Error fetching stage 4 questions:", error);
        alert("获取 Stage 4 问题失败，请查看控制台");
      } finally {
        this.isFetchingS4Questions = false;
      }
    },
    async updateText() {
      if (this.currentStage !== 4) return;
      const qa_pairs = (this.stage4Questions || [])
        .filter(q => q.answered && q.answer && q.answer.trim())
        .map(q => ({ question: q.text, answer: q.answer.trim() }));
      if (qa_pairs.length === 0) {
        alert("没有可供更新的回答，请先回答 Stage 4 的引导问题。");
        return;
      }

      console.log("准备发往 /update-text 的 payload:", {
        current_narrative: this.assistantIntegratedText,
        new_qa_pairs: qa_pairs
      });

      try {
        this.isUpdatingText = true;
        this.assistantUpdatedText = '';
        const resp = await axios.post('http://127.0.0.1:5000/update-text', {
          current_narrative: this.assistantIntegratedText,
          new_qa_pairs: qa_pairs
        }, { timeout: 120000 });

        if (resp.data && resp.data.updated_text) {
          this.assistantUpdatedText = String(resp.data.updated_text).trim();
          this.$message?.success?.("文本更新完成，已在 AI 面板显示（紫色）");
        } else {
          console.error("update-text 返回结构异常：", resp.data);
          alert("文本更新失败，请查看后端日志");
        }
      } catch (err) {
        console.error("更新文本错误：", err);
        alert("更新文本时出错，请查看控制台或后端日志");
      } finally {
        this.isUpdatingText = false;
      }
    },

    // ==========================================================
    // === ❗️【已修复】HERE IS THE FIX ❗️ ===
    // ==========================================================
    async generateNewImagesFromNarrative() {
      console.log('S4: 开始根据更新后的叙事文本生成新图片...');
      const narrative = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim();

      if (!narrative || !this.assistantUpdatedText) {
        alert("AI 叙事没有更新，请先回答问题并[整合文本]");
        return;
      }

      try {
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative,
        });

        let newSentencePairs = response.data.sentence_pairs || [];
        
        // ✅ [ Bug 修复点 ]
        // 过滤出所有带 prompt 的新句子
        const toGenerateWithPrompts = newSentencePairs.filter(p => p.prompt);

        if (toGenerateWithPrompts.length > 0) {
          console.log(`[Stage 4 Fix] 找到了 ${toGenerateWithPrompts.length} 个新 prompt，附加参考图后发送...`);

          // ✅ [修改]
          // 将原始照片(base64Photos)数组附加到 *每一个* // 需要生成的 item 的 'photo' 字段上，以供后端参考
          const payloadToSend = toGenerateWithPrompts.map(item => ({
              ...item,
              photo: base64Photos // 关键：添加原始照片
          }));
          
          const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
            sentence_pairs: payloadToSend // ✅ 发送修正后的 payload
          }, { timeout: 600000 });

          if (!(genResp.data && genResp.data.results)) {
            console.error("S4 generate-images 返回异常：", genResp.data);
            alert("S4 生成图片时出错，请查看控制台");
            return;
          }

          const results = genResp.data.results;
          const BACKEND_BASE = "http://127.0.0.1:5000";

          const beforeNarrative = this.assistantIntegratedText;
          const beforePhotos = [...this.aiPhotos.map(p => ({ url: p.url, prompt: p.prompt }))];

          results.forEach(res => {
            const idx = res.index; 
            
            // 从完整的 newSentencePairs 列表中查找
            const pairFromAll = newSentencePairs.find(p => p.index === idx);

            const urls = res.generated_urls || [];
            if (!urls.length) {
                console.warn(`[Stage 4] Index ${idx} (Prompt: ${pairFromAll?.prompt}) 未能生成 URL。`);
                return; // 跳过生成失败的
            }
            let firstUrl = urls[0];
            if (firstUrl.startsWith("/")) {
              firstUrl = BACKEND_BASE + firstUrl;
            } else if (!firstUrl.startsWith("http://") && !firstUrl.startsWith("https://")) {
              firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
            }

            const aiObj = {
              file: null,
              url: firstUrl,
              name: `ai_generated_s4_${Date.now()}_${idx}.jpg`,
              prompt: res.prompt || pairFromAll?.prompt || null,
              iterationLabel: `Iter ${this.iterationCount}`,
              sentence: pairFromAll?.sentence || null 
            };

            this.aiPhotos.push(aiObj); // ✅ 直接 push 新图片

            // Sync to allPhotos
            this.allPhotos.push({
              type: 'ai',
              sourceIndex: idx,
              url: aiObj.url,
              prompt: aiObj.prompt,
              sentence: aiObj.sentence,
              iterationLabel: aiObj.iterationLabel
            });

            // ✅ 单图生成记录
            this.aiPhotosHistory.push({
              timestamp: new Date().toISOString(),
              type: 'iteration',
              iterationLabel: `Iter ${this.iterationCount}`,
              index: idx,
              prompt: aiObj.prompt,
              url: aiObj.url
            });
          });

          // 迭代收尾
          this.assistantIntegratedText = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim();
          this.iterationCount += 1;
          this.assistantUpdatedText = '';
          this.aiSuggestion = '';
          this.stage4Questions = [];
          this.currentQuestionIndex = 0;

          const afterNarrative = this.assistantIntegratedText;
          const afterPhotos = [...this.aiPhotos.map(p => ({ url: p.url, prompt: p.prompt }))];

          // ✅ 记录迭代事件
          this.stage4Iterations.push({
            iterNum: this.iterationCount - 1,
            time: new Date().toISOString(),
            trigger: 'auto',
            narrativeBefore: beforeNarrative,
            narrativeAfter: afterNarrative,
            photosBefore: beforePhotos,
            photosAfter: afterPhotos,
            newPrompts: payloadToSend.map(p => p.prompt), // ✅ [修复]
            generatedCount: results.length
          });

        } else {
           console.log("[Stage 4 Fix] /generate-prompts 未返回任何带 prompt 的新句子，跳过生成。");
           // 如果没有新图生成，也要合并文本
           this.assistantIntegratedText = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim();
           this.iterationCount += 1; // 仍然消耗一次迭代
           this.assistantUpdatedText = '';
           this.aiSuggestion = '';
           this.stage4Questions = [];
           this.currentQuestionIndex = 0;
        }
      } catch (error) {
        console.error("Error in generateNewImagesFromNarrative:", error);
        alert("S4: 根据叙事更新图像时出错，请查看控制台");
      }
    },
    async submitIndividualPhotoUpdate() {
      const index = this.suggestionForPhotoIndex;
      const suggestion = this.currentSuggestionText.trim();
      if (index === null || !suggestion) return;

      const photo = this.aiPhotos[index];
      if (!photo || !photo.prompt) {
        alert("未找到原始 Prompt，无法更新。");
        return;
      }

      console.log(`S4: 开始根据建议 "${suggestion}" 修改照片 ${index}...`);
      this.isUpdatingPhoto = true;

      try {
        // ✅ 【关键修复】准备参考图片 base64 字符串数组（带 data:image/... 前缀）
        const base64Photos = await Promise.all(
          this.photos.slice(0, 4).map(p => this.convertToBase64(p.file))
        );

        // ✅ 合成新 prompt（原 prompt + 用户建议）
        const newPrompt = `${photo.prompt}, ${suggestion}`;

        // ✅ 构造 sentence_pairs：photo 字段必须是 string[]（base64 data URLs）
        const manual_sentence_pairs = [{
          index: 0,
          prompt: newPrompt,
          photo: base64Photos, // ✅ 直接传字符串数组，后端能正确解析
        }];

        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: manual_sentence_pairs
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results && genResp.data.results.length > 0)) {
          console.error("S4 submitIndividualPhotoUpdate 返回异常：", genResp.data);
          alert("根据建议更新图片时出错，请查看控制台");
          return;
        }

        const result = genResp.data.results[0];
        const urls = result.generated_urls || [];
        if (!urls.length) {
          alert("AI 未能生成图片，请重试");
          return;
        }

        // ✅ 更新 UI
        let firstUrl = urls[0];
        const BACKEND_BASE = "http://127.0.0.1:5000";
        if (firstUrl.startsWith("/")) {
          firstUrl = BACKEND_BASE + firstUrl;
        } else if (!firstUrl.startsWith("http://") && !firstUrl.startsWith("https://")) {
          firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
        }

        const updatedAiObj = {
          ...this.aiPhotos[index],
          url: firstUrl,
          prompt: newPrompt,
          name: `ai_modified_${Date.now()}_${index}.jpg`,
          iterationLabel: `Manual_${this.iterationCount}`
          // sentence 保持不变
        };

        this.aiPhotos[index] = updatedAiObj;

        // 同步更新 allPhotos
        const targetInAll = this.allPhotos.find(p => p.type === 'ai' && p.url === photo.url);
        if (targetInAll) {
          targetInAll.url = updatedAiObj.url;
          targetInAll.prompt = updatedAiObj.prompt;
          targetInAll.iterationLabel = updatedAiObj.iterationLabel;
        }

        // ✅ 记录修改
        this.stage4Modifications.push({
          time: new Date().toISOString(),
          photoIndex: index,
          photoLabel: this.getLetterIndex(index),
          oldUrl: photo.url,
          newUrl: updatedAiObj.url,
          suggestion: suggestion,
          oldPrompt: photo.prompt,
          newPrompt: newPrompt
        });

        this.aiPhotosHistory.push({
          timestamp: new Date().toISOString(),
          type: 'manual',
          photoIndex: index,
          oldUrl: photo.url,
          newUrl: updatedAiObj.url,
          suggestion: suggestion,
          prompt: newPrompt
        });

        alert(`照片 ${this.getLetterIndex(index)} 更新完毕！`);
      } catch (error) {
        console.error("Error in submitIndividualPhotoUpdate:", error);
        alert("S4: 根据建议更新图像时出错，请查看控制台");
      } finally {
        this.isUpdatingPhoto = false;
        this.showSuggestionModal = false;
      }
    },
    openSuggestionModal(index) {
      this.suggestionForPhotoIndex = index;
      this.currentSuggestionText = '';
      this.showSuggestionModal = true;
    },
    startResizeAiResult(e) {
      this.isResizingAiResult = true;
      this.startY_ai = e.clientY;
      this.startHeight_ai = this.aiResultHeight;
      document.addEventListener('mousemove', this.doResizeAiResult);
      document.addEventListener('mouseup', this.stopResizeAiResult);
    },
    doResizeAiResult(e) {
      if (!this.isResizingAiResult) return;
      const diff = e.clientY - this.startY_ai;
      const newHeight = Math.min(Math.max(100, this.startHeight_ai + diff), 400);
      this.aiResultHeight = newHeight;
    },
    stopResizeAiResult() {
      this.isResizingAiResult = false;
      document.removeEventListener('mousemove', this.doResizeAiResult);
      document.removeEventListener('mouseup', this.stopResizeAiResult);
    },
    stopIteration() {
      this.iterationStopped = true;
      console.log("用户终止迭代");
    },
    getLetterIndex(idx) {
      return String.fromCharCode(97 + idx);
    },
    async generateAiVideo() {
      if (this.isGeneratingVideo) return;
      this.isGeneratingVideo = true;
      this.videoGenerationError = null;

      let pollInterval = null;

      try {
        console.log('🎬 [Stage5] 开始生成即梦视频（AABBCCDD → AA, AB, BB, BC, CC, CD, DD）...');

        // ————— Step 1~4：构造 jimengPhotos & jimengPrompts（和原来一样）—————
        const basePhotos = this.allPhotos
          .map(p => p.url)
          .filter(url => url && typeof url === 'string');

        if (basePhotos.length === 0) {
          console.warn('[Stage5] allPhotos 为空，退回到 photos+aiPhotos 逻辑');
          for (let i = 0; i < this.photos.length; i++) {
            const origUrl = this.photos[i]?.url;
            if (!origUrl) continue;
            basePhotos.push(origUrl);
            const aiGroup = this.aiPhotos.filter(ai => ai.origin_pair_index === i);
            if (aiGroup.length > 0) {
              const latest = aiGroup.reduce((a, b) => {
                const numA = this._parseIterNum(a?.iterationLabel || '');
                const numB = this._parseIterNum(b?.iterationLabel || '');
                return numA > numB ? a : b;
              });
              if (latest?.url) basePhotos.push(latest.url);
            }
          }
        }

        if (basePhotos.length === 0) {
          throw new Error('无有效照片序列（allPhotos 与 fallback 均为空）');
        }

        const K = basePhotos.length;
        const jimengPhotos = [];
        for (let i = 0; i < K; i++) {
          jimengPhotos.push(basePhotos[i], basePhotos[i]);
          if (i < K - 1) {
            jimengPhotos.push(basePhotos[i], basePhotos[i + 1]);
          }
        }

        const fullStory = (this.assistantUpdatedText || this.assistantIntegratedText || '').trim();
        const sentences = fullStory
          .split(/[。！？；\n]/)
          .map(s => s.trim())
          .filter(s => s.length > 3);

        const alignedSentences = [];
        for (let i = 0; i < K; i++) {
          alignedSentences.push(
            i < sentences.length ? sentences[i] :
            sentences.length > 0 ? sentences[i % sentences.length] :
            `画面 ${i + 1}`
          );
        }

        const jimengPromises = [];
        for (let i = 0; i < jimengPhotos.length / 2; i++) {
          const idx1 = i * 2, idx2 = idx1 + 1;
          const url1 = jimengPhotos[idx1], url2 = jimengPhotos[idx2];

          let promptType = 'transition', sent1 = '', sent2 = '', sentPrev = '', sentNext = '';

          if (url1 === url2) {
            promptType = 'static';
            const piIndex = basePhotos.indexOf(url1);
            if (piIndex >= 0) {
              sent1 = alignedSentences[piIndex] || '';
              sentPrev = piIndex > 0 ? alignedSentences[piIndex - 1] || '' : '';
              sentNext = piIndex + 1 < alignedSentences.length ? alignedSentences[piIndex + 1] || '' : '';
            }
          } else {
            promptType = 'transition';
            const idxA = basePhotos.indexOf(url1), idxB = basePhotos.indexOf(url2);
            sent1 = idxA >= 0 ? alignedSentences[idxA] || '' : '';
            sent2 = idxB >= 0 ? alignedSentences[idxB] || '' : '';
            sentPrev = idxA > 0 ? alignedSentences[idxA - 1] || '' : '';
            sentNext = idxB + 1 < alignedSentences.length ? alignedSentences[idxB + 1] || '' : '';
          }

          jimengPromises.push(
            axios.post('http://127.0.0.1:5000/refine-prompt', {
              type: promptType,
              sentence: sent1,
              next_sentence: sent2,
              prev_sentence: sentPrev,
              post_sentence: sentNext
            }, { timeout: 8000 })
            .then(res => (res.data.prompt || '').trim() || 
                  (promptType === 'static' ? '人物静止，微表情变化，镜头轻微推进' : '平滑过渡'))
            .catch(err => {
              console.warn(`[Prompt ${i}] fallback`, err.message);
              return promptType === 'static' ? '静帧画面' : '自然过渡';
            })
          );
        }

        const jimengPrompts = await Promise.all(jimengPromises);
        console.log(`[Stage5] 生成 prompts（${jimengPrompts.length} 个）:`, jimengPrompts);

        // ————— Step 5: 提交任务（不再 await，改为轮询）—————
        const submitResp = await axios.post('http://127.0.0.1:5000/generate-video', {
          photos: jimengPhotos,
          prompts: jimengPrompts
        }, {
          timeout: 30000 // 提交本身不应太久
        });

        if (!submitResp.data.task_id) {
          throw new Error('后端未返回 task_id');
        }

        const taskId = submitResp.data.task_id;
        console.log(`✅ 视频任务已提交，task_id = ${taskId}`);

        // ————— Step 6: 轮询直到完成 —————
        return new Promise((resolve, reject) => {
          const MAX_POLL = 720; // 最多轮询 12 分钟（每秒 1 次）
          let pollCount = 0;

          const poll = async () => {
            try {
              pollCount++;
              const statusResp = await axios.get(`http://127.0.0.1:5000/video-status/${taskId}`, {
                timeout: 10000
              });

              const { status, videoUrl, error, elapsed } = statusResp.data;

              if (status === 'success') {
                // ✅ 成功
                clearInterval(pollInterval);
                this.aiVideo.url = videoUrl;
                this.$message?.success?.("🎬 视频生成成功！情感故事已呈现");
                resolve();
              } else if (status === 'failed') {
                // ❌ 失败
                clearInterval(pollInterval);
                const msg = error || '生成失败';
                this.videoGenerationError = msg;
                this.$message?.error?.(`视频生成失败：${msg}`);
                reject(new Error(msg));
              } else if (pollCount >= MAX_POLL) {
                // ⏳ 超时
                clearInterval(pollInterval);
                const msg = `生成超时（>12 分钟，已运行 ${Math.floor(elapsed || 0)} 秒）`;
                this.videoGenerationError = msg;
                this.$message?.error?.(msg);
                reject(new Error(msg));
              } else {
                // 🔄 继续轮询
                console.log(`[Task ${taskId.slice(0,6)}] 等待中... ${status} (第 ${pollCount}s)`);
              }
            } catch (err) {
              console.error(`轮询 /video-status/${taskId} 出错:`, err);
              // 可选：遇到网络错误不终止，继续轮询（更健壮）
              // 也可 clearInterval + reject
            }
          };

          pollInterval = setInterval(poll, 1000);
          poll(); // 立即首次查询
        });

      } catch (err) {
        console.error("[Video Gen Submit Error]", err);
        this.videoGenerationError = err.message || "提交失败";
        this.$message?.error?.("视频任务提交失败，请查看控制台");
        throw err; // 让 finally 能统一处理
      } finally {
        // ✅ 确保清理定时器
        if (pollInterval) clearInterval(pollInterval);
        this.isGeneratingVideo = false;
      }
    }
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
  cursor: pointer; /* ✅ [新增] */
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

/* ✅ [新增] :disabled 样式 */
.control-btn:disabled {
  background: #f0f0f0;
  color: #aaa;
  cursor: not-allowed;
  border-color: #e0e0e0;
}


.control-btn.primary {
  background: linear-gradient(135deg, #c3c9e8, #d4c5e0);
  color: white;
  border: none;
}

.control-btn.primary:hover {
  opacity: 0.9;
}

/* ✅ [新增] :disabled 样式 */
.control-btn.primary:disabled {
  background: #dcdcdc;
  opacity: 0.7;
}

/* 照片面板 - 紧凑设计 */
.photo-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  flex-shrink: 0;
  /* ✅ [修改] 支持内部滚动 */
  display: flex; 
  flex-direction: column;
  overflow: hidden;
}

/* ✅ [新增] Stage 3/4 专用 */
.split-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow-y: auto; /* 允许容器滚动 */
  min-height: 0;
}
.split-title {
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
  margin-top: 5px; 
}
.top-panel, .bottom-panel {
  margin-bottom: 10px;
}
.bottom-panel {
   border-top: 1px solid #eee;
   padding-top: 10px;
}
.ai-photo-grid .photo-placeholder {
  border-color: #c3c9e8;
}

.photo-grid {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-bottom: 12px;
  flex-wrap: wrap; /* ✅ [新增] 允许换行 */
}

.photo-slot {
  width: 120px;
  height: 120px;
  position: relative;
  flex-shrink: 0; /* ✅ [新增] 防止缩放 */
}

/* ✅ [新增] AI 照片槽位 */
.photo-slot-ai {
  width: 120px;
  display: flex;
  flex-direction: column;
  gap: 4px; /* 按钮和图片的间距 */
  align-items: center;
}
.edit-photo-btn {
  width: 100%;
  padding: 4px;
  font-size: 12px;
  background: #f0f2f5;
  border: 1px solid #ddd;
  border-radius: 4px;
  cursor: pointer;
}
.edit-photo-btn:hover {
  background: #e8ebf7;
}
.edit-photo-btn:disabled {
  background: #f9f9f9;
  color: #ccc;
  cursor: not-allowed;
}


.photo-placeholder {
  width: 100%;
  height: 120px; /* ✅ [修改] 固定高度 */
  background: #f5f6f7;
  border: 2px dashed #d0d0d0;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s;
  position: relative; /* ✅ [新增] 为编号定位 */
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
  flex-shrink: 0; /* ✅ [新增] */
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
  border: 1px solid #f0f0f0; /* ✅ [新增] */
}

.question-card.active {
  background: white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border-color: #c3c9e8; /* ✅ [新增] */
  box-shadow: 0 2px 8px rgba(195, 201, 232, 0.4); /* ✅ [新增] */
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
  flex-shrink: 0; /* ✅ [新增] */
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
  flex-wrap: wrap; /* ✅ [新增] */
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

/* ✅ [修改] 增加 hover */
.submit-btn:hover {
  opacity: 0.9;
}

.answer-display {
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  margin-top: 8px;
  border: 1px solid #e8e8e8; /* ✅ [新增] */
}

.answer-display p {
  font-size: 13px;
  color: #666;
  white-space: pre-wrap; /* ✅ [新增] */
  word-break: break-word; /* ✅ [新增] */
}

.control-btn.primary {
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
  width: calc(100% - 40px); /* ✅ [新增] */
}

/* ✅ [修改] 修正 hover 效果 */
.control-btn.primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(195, 201, 232, 0.4);
  opacity: 1; 
}

/* ✅ [新增] 修正 disabled hover 效果 */
.control-btn.primary:disabled:hover {
  transform: none;
  box-shadow: none;
  opacity: 0.7;
}


.narrative-input {
  width: 100%;
  height: 100%; /* ✅ [修改] 占满 */
  flex: 1; /* ✅ [新增] */
  border: none;
  outline: none;
  resize: none;
  font-size: 15px;
  line-height: 1.8;
  color: #444;
  background: #fafbfc;
  font-family: inherit;
  padding: 16px; /* ✅ [修改] 统一 padding */
  border-radius: 6px;
  overflow-y: auto; /* ✅ [新增] */
}

.narrative-input::placeholder {
  color: #aaa;
  font-style: italic;
}

/* ✅ [新增] 修复 contenteditable 焦点样式 */
.narrative-input:focus {
  outline: 2px solid #c3c9e8;
  box-shadow: 0 0 5px rgba(195, 201, 232, 0.5);
}

/* --- ✅ [新增] Req 1 拖拽条样式 --- */
.resize-handle-ai {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 12px;
  cursor: ns-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent; /* 拖拽区域 */
  z-index: 10;
}
.resize-handle-ai:hover .handle-line,
.resize-handle-ai.resizing .handle-line {
  background: #9ca3db;
}

/* --- ✅ [新增] Req 4 编号样式 --- */
.ai-photo-label {
  position: absolute;
  top: 4px;
  left: 4px;
  background: rgba(0, 0, 0, 0.5);
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  z-index: 2;
}

/* --- ✅ [新增] Req 2 迭代标签样式 --- */
.ai-photo-iter-label {
  position: absolute;
  top: 4px;
  right: 4px;
  background: rgba(124, 131, 185, 0.8); /* 紫色 */
  color: white;
  border-radius: 4px;
  padding: 2px 4px;
  font-size: 10px;
  font-weight: bold;
  z-index: 2;
}


/* --- ✅ [新增] Req 1 模态框样式 --- */
.suggestion-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.suggestion-modal {
  background: white;
  padding: 24px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  width: 400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.suggestion-modal h3 {
  margin: 0;
}
.suggestion-modal textarea {
  width: 100%;
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>