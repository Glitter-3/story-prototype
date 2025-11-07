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
                  <div class="photo-placeholder ai-placeholder" @click="onClickAiSlot(idx)">
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
                    :disabled="iterationStopped || iterationCount > maxIterations">
                    ✏️ 建议
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
              <button class="control-btn" @click="calculateMemoryMetrics">计算记忆指标</button>
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
             已迭代 {{ iterationCount }} / {{ maxIterations }} 轮
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
            <button 
              v-if="currentStage === 4"
              class="control-btn"
              @click="generateNewImagesFromNarrative"
              :disabled="iterationStopped || iterationCount > maxIterations || !assistantUpdatedText"
              title="根据新的叙事文本（紫色部分）生成新图片"
              style="padding: 4px 8px; font-size: 12px;">
              新一轮图像更新
            </button>
            <div v-else style="font-size:12px; color:#666;">
              <span v-if="integrating">整合中...</span>
              <span v-if="isUpdatingText">文本更新中...</span>
            </div>
          </div>
          
          <div v-if="assistantIntegratedText || assistantUpdatedText" style="white-space:pre-wrap; overflow:auto; color:#222; line-height:1.6; flex: 1;">
            <span>{{ assistantIntegratedText }}</span>
            <span v-if="assistantUpdatedText" style="color:#667eea; margin-top: 5px; display: inline-block;">
              {{ assistantUpdatedText }}
            </span>
          </div>
          <div v-else style="color:#888; font-size:13px;">
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
            :disabled="isFetchingS4Questions || iterationStopped || iterationCount > maxIterations"
            style="width: 100%; margin-bottom: 10px;"
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
            style="margin: 0; background: #f5f5f5; width: 100%;" :disabled="iterationStopped || iterationCount > maxIterations"
            >
            已满意，终止迭代
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
          :disabled="integrating || isUpdatingText || iterationStopped || iterationCount > maxIterations"
          @click="currentStage === 3 ? integrateText() : updateText()">
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
      maxIterations: 3,
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
    }
  },
  computed: {
    progressPercentage() {
      if (this.currentStage === 4) {
        return ((this.iterationCount - 1) / this.maxIterations) * 100
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
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative,
        });

        this.sentencePairs = response.data.sentence_pairs || [];
        console.log('图文配对结果：', toRaw(this.sentencePairs));
        this.sentencePairs.sort((a, b) => a.index - b.index);

        alert("Qwen已完成分句与prompt生成");

        const toGenerate = this.sentencePairs.filter(p => p.prompt);
        if (!toGenerate.length) {
          alert("没有需要生成的 prompt，操作结束");
          return;
        }

        this.aiPhotos = [];
        this.allPhotos = [];

        const sentencePairsWithPhotos = this.sentencePairs.map((sentence, index) => ({
          ...sentence,
          photo: base64Photos || null
        }));

        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: sentencePairsWithPhotos,
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results)) {
          console.error("generate-images 返回异常：", genResp.data);
          alert("生成图片时出错，请查看控制台");
          return;
        }

        const results = genResp.data.results;
        console.log("生成图片结果：", results);

        const BACKEND_BASE = "http://127.0.0.1:5000";

        results.forEach(res => {
          const idx = res.index;
          const urls = res.generated_urls || [];
          if (!urls.length) return;
          let firstUrl = urls[0];
          if (firstUrl.startsWith("/")) {
            firstUrl = BACKEND_BASE + firstUrl;
          } else if (!firstUrl.startsWith("http://") && !firstUrl.startsWith("https://")) {
            firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
          }

          const pair = this.sentencePairs.find(p => p.index === idx);
          let targetAiIndex = -1;
          if (pair && pair.photo) {
            const photoSlot = this.photos.findIndex(p => p.url === pair.photo || (p.file && pair.photo.includes("data:")));
            if (photoSlot !== -1) targetAiIndex = photoSlot;
          }

          if (targetAiIndex === -1) {
            const emptyIndex = this.aiPhotos.findIndex(a => !a.url);
            if (emptyIndex !== -1) targetAiIndex = emptyIndex;
          }
          if (targetAiIndex === -1) {
            targetAiIndex = this.aiPhotos.length;
            this.aiPhotos.push({});
          }

          const aiObj = {
            file: null,
            url: firstUrl,
            name: `ai_generated_${Date.now()}_${targetAiIndex}.jpg`,
            prompt: res.prompt || pair?.prompt || null,
            origin_pair_index: idx
          };

          this.allPhotos.push({
            ...this.photos[targetAiIndex] || {},
            aiGenerated: aiObj,
            index: idx
          });

          if (typeof this.$set === 'function') {
            this.$set(this.aiPhotos, targetAiIndex, aiObj);
          } else {
            this.aiPhotos[targetAiIndex] = aiObj;
            this.aiPhotos = this.aiPhotos.slice();
          }
        });

        // ✅ 记录批量生成
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
    async generateNewImagesFromNarrative() {
      if (this.iterationCount > this.maxIterations) {
        alert("已达到最大迭代次数！");
        this.iterationStopped = true;
        return;
      }

      console.log('S4: 开始根据更新后的叙事文本生成新图片...');
      const narrative = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim(); // ✅ 修正为 '\n'

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
        const toGenerate = newSentencePairs.filter(p => p.prompt);
        const limitedToGenerate = toGenerate.slice(0, 2);

        if (limitedToGenerate.length > 0) {
          const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
            sentence_pairs: limitedToGenerate
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
            const originalPair = limitedToGenerate[idx];
            const urls = res.generated_urls || [];
            if (!urls.length) return;
            let firstUrl = urls[0];
            if (firstUrl.startsWith("/")) {
              firstUrl = BACKEND_BASE + firstUrl;
            } else if (!firstUrl.startsWith("http://") && !firstUrl.startsWith("https://")) {
              firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
            }

            const aiObj = {
              file: null,
              url: firstUrl,
              name: `ai_generated_s4_${Date.now()}.jpg`,
              prompt: res.prompt || originalPair?.prompt || null,
              iterationLabel: `Iter ${this.iterationCount}`
            };

            this.aiPhotos.push(aiObj);

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
          this.assistantIntegratedText = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim(); // ✅ 修正为 '\n'
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
            newPrompts: limitedToGenerate.map(p => p.prompt),
            generatedCount: results.length
          });

          if (this.iterationCount > this.maxIterations) {
            this.iterationStopped = true;
          }
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

      console.log(`S4: 开始根据建议 "${suggestion}" 修改照片 ${index} (a.k.a. ${this.getLetterIndex(index)})...`);
      this.isUpdatingPhoto = true;

      const manual_sentence_pairs = [{
        index: 0,
        prompt: `${photo.prompt}, ${suggestion}`,
        photo: null
      }];

      try {
        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: manual_sentence_pairs
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results && genResp.data.results.length > 0)) {
          console.error("S4 submitIndividualPhotoUpdate 返回异常：", genResp.data);
          alert("根据建议更新图片时出错，请查看控制台");
          this.isUpdatingPhoto = false;
          return;
        }

        const result = genResp.data.results[0];
        const urls = result.generated_urls || [];
        if (!urls.length) {
          alert("AI 未能生成图片，请重试");
          this.isUpdatingPhoto = false;
          return;
        }

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
          prompt: result.prompt,
          name: `ai_modified_${Date.now()}_${index}.jpg`,
        };

        this.$set(this.aiPhotos, index, updatedAiObj);

        // ✅ 记录修改
        this.stage4Modifications.push({
          time: new Date().toISOString(),
          photoIndex: index,
          photoLabel: this.getLetterIndex(index),
          oldUrl: photo.url,
          newUrl: updatedAiObj.url,
          suggestion: suggestion,
          oldPrompt: photo.prompt,
          newPrompt: updatedAiObj.prompt
        });

        // ✅ 记录生成
        this.aiPhotosHistory.push({
          timestamp: new Date().toISOString(),
          type: 'manual',
          photoIndex: index,
          oldUrl: photo.url,
          newUrl: updatedAiObj.url,
          suggestion: suggestion,
          prompt: updatedAiObj.prompt
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
    async saveExperimentLog() {
      try {
        const logData = {
          userId: this.userId,
          sessionId: this.sessionId,
          startTime: this.startTime,
          endTime: new Date().toISOString(),
          userAgent: this.userAgent,
          screenResolution: this.screenResolution,
          stageTimestamps: { ...this.stageTimestamps },
          narratives: { ...this.userNarratives },
          stage2QA: [...this.stage2QA],
          stage4QA: [...this.stage4QA],
          stage4Iterations: [...this.stage4Iterations],
          stage4Modifications: [...this.stage4Modifications],
          aiPhotosHistory: [...this.aiPhotosHistory],
          originalPhotoUrls: this.photos.map(p => p.url).filter(Boolean),
          aiPhotoUrls: this.aiPhotos.map(p => p.url).filter(Boolean),
          aiPhotoMeta: this.aiPhotos.map(p => ({
            url: p.url,
            prompt: p.prompt,
            iterationLabel: p.iterationLabel
          }))
        };

        const resp = await axios.post('http://127.0.0.1:5000/save-experiment-log', {
          log: logData
        });

        if (resp.data.success) {
          alert(`✅ 实验日志已保存！\nSession ID: ${this.sessionId}`);
        } else {
          throw new Error(resp.data.message || '后端保存失败');
        }
      } catch (err) {
        console.error('[Log Save Error]', err);
        alert('❌ 实验日志保存失败，请重试\n' + (err.message || 'Unknown error'));
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