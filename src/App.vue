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
                <div class="photo-slot" v-for="(ap, idx) in aiPhotos" :key="'ai-'+idx">
                  <div class="photo-placeholder ai-placeholder" @click="onClickAiSlot(idx)">
                    <span class="ai-photo-label">{{ getLetterIndex(idx) }}</span>
                    <template v-if="ap.url">
                      <img :src="ap.url" class="photo-preview" alt="AI增强图片" />
                    </template>
                    <template v-else>
                      <span class="photo-number">{{ idx + 1 }}</span>
                      <span class="add-icon">+</span>
                    </template>
                  </div>
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
              <button v-if="currentStage === 4" class="control-btn" @click="updateImagesWithSuggestion" :disabled="iterationStopped || iterationCount > maxIterations">初次图像更新</button>
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
            <div style="font-size:12px; color:#666;">
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

        <div v-if="currentStage === 4" class="ai-modify-section" style="margin:10px 0; text-align:center; padding: 0 20px;"> <label style="display:block; font-weight:600; margin-bottom:12px; text-align:left;"> 对AI增强照片的建议
          </label>
          <textarea
            v-model="aiSuggestion"
            rows="4" :placeholder="'例如：照片a色调暖一些；照片b人物锐化...'" style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; border:1px solid #ddd; font-size:14px; margin-bottom: 10px;" :disabled="iterationStopped || iterationCount > maxIterations"
          ></textarea>
          
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
            class="control-btn primary" 
            @click="continueModification"
            :disabled="iterationStopped || iterationCount > maxIterations"
            style="margin: 0; width: 100%;" >
            {{ (iterationCount > maxIterations) ? '已达最大迭代' : '新一轮图像更新' }} </button>
            
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
          v-if="currentStage === 3 || (currentStage === 4 && stage4Questions.length > 0)" class="control-btn primary"
          :disabled="integrating || isUpdatingText || iterationStopped || iterationCount > maxIterations"
          @click="currentStage === 3 ? integrateText() : updateText()">
          {{ integrating ? '整合中...' : (isUpdatingText ? '更新中...' : (currentStage === 3 ? '整合文本' : '文本更新')) }}
        </button>


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
      currentStage: 1, // ✅ 默认Stage 1
      photoPanelHeight: 360,
      isResizing: false,
      aiVideo: { url: '' },  // Stage5 AI 增强视频
      iterationCount: 1,      // Stage 4 迭代次数，初始为1
      maxIterations: 3,       // ✅ 最大迭代轮数 (改为 3)
      startY: 0,
      startHeight: 0,
      highlightedTexts: [],
      aiSuggestion: '',               // Stage4 输入框绑定内容
      modificationInProgress: false,  // 是否处于 AI 修改中（可用于按钮状态）
      selectedText: '',
      integrating: false, // 整合文本状态
      assistantIntegratedText: '', // AI助手整合后的文本,只读
      photos: [], 
      aiPhotos: [], 
      allPhotos: [],
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
      sentencePairs: [], // [{sentence, photo, prompt}]
      
      // --- ✅ [新增] Stage 4 状态 ---
      stage4Questions: [], // Stage 4 的引导问题
      assistantUpdatedText: '', // Stage 4 AI 返回的紫色更新文本
      isFetchingS4Questions: false, // Stage 4 获取问题 loading
      isUpdatingText: false, // Stage 4 更新文本 loading
      
      // --- ✅ [新增] Req 1 拖拽 ---
      aiResultHeight: 220, // 默认高度
      isResizingAiResult: false,
      startY_ai: 0,
      startHeight_ai: 0,
      
      // --- ✅ [新增] Req 2 迭代 ---
      iterationStopped: false,
    }
  },
  computed: {
    progressPercentage() {
      if (this.currentStage === 4) {
        // ✅ [修改] 迭代从 1 开始
        return ((this.iterationCount - 1) / this.maxIterations) * 100
      }
      // ✅ [修改] 增加分母检查
      if (this.currentStage === 2 && this.questions.length > 0) {
        return (this.answeredCount / this.questions.length) * 100
      }
      return 0
    },
    answeredCount() {
      // ✅ [修改] 区分 Stage 2 和 4
      const list = this.currentStage === 2 ? this.questions : this.stage4Questions;
      if (!list) return 0;
      return list.filter(q => q.answered).length
    }
  },

  methods: {
// 替换：onEditableInput
    onEditableInput(e) {
      const el = this.$refs.editableNarrative;
      if (!el) return;

      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) {
        this.userNarratives[this.currentStage] = el.innerHTML;
        return;
      }
      const range = sel.getRangeAt(0);

      // 如果选区有内容，先删除选区（用户选中蓝字并直接输入的场景）
      if (!range.collapsed) {
        range.deleteContents();
        // 更新 selection/range
        sel.removeAllRanges();
        sel.addRange(range);
      }

      // 获取光标所在的元素（如果是文本节点则取父元素）
      let node = range.startContainer;
      const anchorEl = node.nodeType === 3 ? node.parentElement : node;

      // ✅ [修改] 调用 isHistoryNode
      // 判断元素是否为紫色历史段（兼容 style 或 computed）
      const isHistoryNode = (n) => {
        if (!n) return false;
        const inline = (n.style && n.style.color) ? n.style.color.toLowerCase() : '';
         // ✅ [修改] 颜色
        if (inline && inline.includes('#7c83b9')) return true;
        try {
          const comp = window.getComputedStyle(n).color;
           // ✅ [修改] 颜色 rgb(124, 131, 185)
          if (comp === 'rgb(124, 131, 185)') return true;
        } catch (err) {}
        return false;
      };

      // ✅ [修改] 调用 isHistoryNode
      // 如果光标在紫色段内，拆分紫色并插入黑色占位
      if (isHistoryNode(anchorEl)) {
        this.splitHistorySpanAtRange(anchorEl, range); // ✅ [修改] 调用 splitHistorySpanAtRange
        // splitHistorySpanAtRange 会把光标放到黑色占位里
      }

      // 保存当前 HTML（紫色段已被正确拆分或保持不动）
      this.userNarratives[this.currentStage] = el.innerHTML;
    },

    switchStage(stage) {
      this.currentStage = stage;

      // 仅在第一次进入该 stage 且该 stage 目前为空时，带入上一阶段文本（以纯文本方式取前一阶段内容，避免重复包 span）
      if (stage > 1 && !this.userNarratives[stage]) {
        const prevHtml = this.userNarratives[stage - 1] || '';
        const tmp = document.createElement('div');
        tmp.innerHTML = prevHtml;
        const prevText = tmp.textContent || tmp.innerText || '';

        if (prevText) {
          // ✅ [修改] 颜色
          // 生成一个紫色 span（历史） + 紧随一个黑色空 span（用于后续输入）
          const purple = `<span style="color:#7c83b9;">${this.escapeHtml(prevText)}</span>`;
          const black = `<span style="color:#000000;">\u200B</span>`;
          this.userNarratives[stage] = purple + black;
        } else {
          this.userNarratives[stage] = '';
        }
      }

      // --- ✅ [新增] Stage 状态重置 ---
      if (stage === 4) {
        this.stage4Questions = [];
        this.assistantUpdatedText = '';
        this.aiSuggestion = '';
        this.iterationCount = 1; // 每次进入 Stage 4 都重置迭代计数
        this.currentQuestionIndex = 0;
        this.iterationStopped = false; // ✅ [新增] 重置终止状态
      }
      if (stage === 2) {
        this.currentQuestionIndex = 0;
        // this.questions = []; // 可选：是否每次都清空
      }
      if (stage === 3) {
         this.assistantUpdatedText = ''; // 从4切回3时，清除紫字
      }
      // --- END ---

      // 更新编辑区 DOM，并把光标放在黑色 span（如果存在）
      this.$nextTick(() => {
        const editor = this.$refs.editableNarrative;
        if (!editor) return;
        editor.innerHTML = this.userNarratives[stage] || '';

        // 确保末尾存在黑色 span，若没有创建一个
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
          // append a black span with zwsp
          const s = document.createElement('span');
          s.style.color = '#000000';
          s.innerHTML = '\u200B';
          editor.appendChild(s);
          blackSpan = s;
        }

        // 将光标放入黑色 span（末尾），便于输入并保证新输入为黑色
        this.placeCaretInElement(blackSpan);
      });

      console.log(`已切换到 Stage ${stage}`);
    },
    // ✅ [修改] 重命名
    // 新增：把紫色 span 在光标处拆成 左紫 + 黑色插入位 + 右紫
    splitHistorySpanAtRange(purpleSpan, range) {
      // purpleSpan 必须包含文本（如果包含复杂子节点这里做一个简单文本抽取处理）
      const tmp = document.createElement('div');
      tmp.appendChild(purpleSpan.cloneNode(true));
      const fullText = tmp.textContent || '';

      // 通过一个 Range 计算从 purpleSpan 开始到光标处的文本长度
      const preRange = document.createRange();
      preRange.setStart(purpleSpan, 0);
      try {
        preRange.setEnd(range.startContainer, range.startOffset);
      } catch (err) {
        // 若 setEnd 失败（极少情况），退回到以文本长度分割
        preRange.selectNodeContents(purpleSpan);
        preRange.setEnd(purpleSpan, 0);
      }
      const leftText = preRange.toString();
      const rightText = fullText.slice(leftText.length);

      const parent = purpleSpan.parentNode;

      // 创建新的左紫 span（若 leftText 为空则不插入）
      if (leftText) {
        const leftSpan = document.createElement('span');
        leftSpan.style.color = '#7c83b9'; // ✅ [修改] 颜色
        leftSpan.textContent = leftText;
        parent.insertBefore(leftSpan, purpleSpan);
      }

      // 创建黑色插入位（带一个零宽字符，便于放置光标）
      const blackSpan = document.createElement('span');
      blackSpan.style.color = '#000000';
      blackSpan.innerHTML = '\u200B'; // zero-width space
      parent.insertBefore(blackSpan, purpleSpan);

      // 创建新的右紫 span（若 rightText 为空则不插入）
      if (rightText) {
        const rightSpan = document.createElement('span');
        rightSpan.style.color = '#7c83b9'; // ✅ [修改] 颜色
        rightSpan.textContent = rightText;
        parent.insertBefore(rightSpan, purpleSpan);
      }

      // 移除原来的 purpleSpan（已被拆分）
      parent.removeChild(purpleSpan);

      // 把光标放到 blackSpan 内
      this.placeCaretInElement(blackSpan);
    },


    // 把光标放到元素内部（元素末端）
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

    // 简单转义 HTML（用于把纯文本包进 span）
    escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    },
    // ✅ [修改] 重命名
    // 判断节点是否为我们定义的“紫色历史段”
    isHistoryNode(node) {
      if (!node) return false;
      if (node.nodeType !== 1) return false; // 不是元素
      // 优先检查内联 style，再兼容 computed style rgb
      const inline = (node.style && node.style.color) ? node.style.color.toLowerCase() : '';
      if (inline && inline.includes('#7c83b9')) return true; // ✅ [修改] 颜色
      try {
        const comp = window.getComputedStyle(node).color;
        if (comp === 'rgb(124, 131, 185)') return true; // ✅ [修改] 颜色
      } catch (err) {}
      return false;
    },

    // 处理删除键（Backspace / Delete），保证紫色段可以被整段删除或在紫字间插入的黑字可删
    onEditableKeydown(e) {
      const editor = this.$refs.editableNarrative;
      if (!editor) return;

      const sel = window.getSelection();
      if (!sel || sel.rangeCount === 0) return;
      const range = sel.getRangeAt(0);

      // 如果存在选区（用户选中了一段），让默认行为生效，之后延迟更新保存内容
      if (!range.collapsed) {
        // 保存在下一tick（删除/替换后 DOM 已变）
        setTimeout(() => {
          this.userNarratives[this.currentStage] = editor.innerHTML;
        }, 0);
        return;
      }

      // helper：找到当前光标所在的元素（若在文本节点则返回父元素）
      const getAnchorElement = (r) => {
        let n = r.startContainer;
        return (n.nodeType === 3 ? n.parentElement : n);
      };

      const anchorEl = getAnchorElement(range);

      // ---------- Backspace 逻辑 ----------
      if (e.key === 'Backspace') {
        // 情况 A：如果光标在一个黑色 span（插入位）并且光标位于其开始位置，
        // 则尝试删除前一个 sibling，如果前一个是紫色 span，就删除它（整段删除）
        if (anchorEl && anchorEl.nodeType === 1) {
          // 如果是文本节点父元素且 offset===0（光标在开头）
          const isAtStart = (() => {
            // 若 startContainer 是文本节点，检查 startOffset
            if (range.startContainer.nodeType === 3) {
              return range.startOffset === 0;
            }
            // 否则使用 startOffset 与 childNodes 长度比较
            return range.startOffset === 0;
          })();

          if (isAtStart) {
            const prev = anchorEl.previousSibling;
            if (prev && this.isHistoryNode(prev)) { // ✅ [修改] 调用 isHistoryNode
              e.preventDefault();
              prev.parentNode.removeChild(prev);
              // 更新 model 并把光标放到当前 anchorEl 开头
              this.$nextTick(() => {
                this.placeCaretInElement(anchorEl);
                this.userNarratives[this.currentStage] = editor.innerHTML;
              });
              return;
            }
          }
        }

        // 情况 B：如果光标直接位于紫色 span 内（比如用户把光标点在紫字中），
        // 我们允许在紫字内部删除字符（默认行为）——无需阻止
        // 但若想要在紫字内部输入把插入部分变黑，已有 onEditableInput 会拆分
        return; // 让默认行为继续
      }

      // ---------- Delete 键 逻辑 ----------
      if (e.key === 'Delete') {
        // 情况：若光标在黑色 span 末尾并且下一个 sibling 是紫色 span -> 删除那个紫色段
        // 判定是否在元素末尾
        const isAtEnd = (() => {
          if (range.startContainer.nodeType === 3) {
            return range.startOffset === range.startContainer.textContent.length;
          }
          return range.startOffset === anchorEl.childNodes.length;
        })();

        if (isAtEnd) {
          const next = anchorEl.nextSibling;
          if (next && this.isHistoryNode(next)) { // ✅ [修改] 调用 isHistoryNode
            e.preventDefault();
            next.parentNode.removeChild(next);
            this.$nextTick(() => {
              this.placeCaretInElement(anchorEl);
              this.userNarratives[this.currentStage] = editor.innerHTML;
            });
            return;
          }
        }

        // 否则允许默认 Delete 行为（删除字符）
        return;
      }

      // 其余按键正常处理（例如字符输入会触发 input 事件，在 onEditableInput 处理拆分/插入）
    },

    // ✅ [修改] S4 迭代逻辑
    async continueModification() {
      if (this.iterationCount >= this.maxIterations) { // ✅ [修改] 检查
        alert("已达到最大迭代次数！");
        this.iterationStopped = true; // 自动终止
        return;
      }
        
      // 1. ✅ [修改] 根据“更新后”的叙事文本，生成“新一轮”的 AI 图像
      console.log("continueModification: 正在根据更新后的文本生成新版图片...");
      await this.generateImagesFromUpdatedNarrative(); // 等待图片生成完毕
      
      // 2. 增加迭代次数
      this.iterationCount += 1;
      
      // 3. 将上一轮的“紫色更新” (UpdatedText) 合并到“黑色基础” (IntegratedText)
      this.assistantIntegratedText = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim();

      // 4. 清空上一轮的 Stage 4 状态，准备新一轮
      this.assistantUpdatedText = '';
      this.aiSuggestion = '';
      this.stage4Questions = [];
      this.currentQuestionIndex = 0;

      console.log(`开始第 ${ this.iterationCount} 轮迭代`);

      if (this.iterationCount > this.maxIterations) {
        console.log("已完成最后一轮迭代，自动终止。");
        this.iterationStopped = true;
      }
    },


    // 获取问题
    async fetchQuestions() {
      console.log('开始获取问题...')
      if (this.currentStage === 2) {    
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
          this.currentQuestionIndex = 0; // ✅ 重置索引
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
        reader.readAsDataURL(file); // 直接读取为 Base64
      });
    },
    
    // --- ✅ [新增] 修复 BUG 所需的帮助函数 ---
    // 将 URL (http://localhost... 或 blob:...) 转换为 Base64 data URL
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
        return null; // Handle error gracefully
      }
    },
    // --- 结束 [新增] ---

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
      console.log(`Stage ${stage} 的口述内容已保存：`, content)

      this.$message?.success?.(`第 ${stage} 阶段的口述内容已保存`) 
      // 或者用 alert:
      alert(`第 ${stage} 阶段的口述内容已保存`)
    },
    async integrateText() {
      if (this.currentStage !== 3) {
        alert("整合文本仅在 Stage 3 可用");
        return;
      }

      // 使用 Stage2 的口述和 Stage2 的已回答问答对作为输入
      const narrative = this.userNarratives[2] || '';
      const qa_pairs = (this.questions || [])
        .filter(q => q.answered && q.answer && q.answer.trim())
        .map(q => ({ question: q.text, answer: q.answer.trim() }));

      if (!narrative && qa_pairs.length === 0) {
        alert("没有可供整合的口述或问答，请先在 Stage2 完成口述与回答。");
        return;
      }
 
      // Debug 日志，便于后端看到我们真正发了什么
      console.log("准备发往 /integrate-text 的 payload:", { narrative, qa_pairs });

      try {
        this.integrating = true;
        this.assistantIntegratedText = ''; // 清空旧结果
        this.assistantUpdatedText = '';  // ✅ 确保紫字也被清空

        const resp = await axios.post('http://127.0.0.1:5000/integrate-text', {
          narrative,
          qa_pairs,
          options: { output_format: 'text' }
        }, { timeout: 120000 });

        if (resp.data && resp.data.integrated_text) {
          // **关键**：只把结果写进 assistantIntegratedText，不修改 userNarratives[3]
          this.assistantIntegratedText = String(resp.data.integrated_text).trim();
          // 给用户提示
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
      const narrative = this.assistantIntegratedText; // 获取 AI 整合之后的叙述性文本
      
      if (!narrative) { // ✅ 增加检查
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

        // 按照 index 排序
        this.sentencePairs.sort((a, b) => a.index - b.index);

        alert("Qwen已完成分句与prompt生成");

        const toGenerate = this.sentencePairs.map((p, i) => ({ ...p, __index: i }))
                                        .filter(p => p.prompt);

        if (!toGenerate.length) {
          alert("没有需要生成的 prompt，操作结束");
          return;
        }

        // ✅ 清空旧的 AI 照片
        this.aiPhotos = []; 
        this.allPhotos = [];

        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: this.sentencePairs
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results)) {
          console.error("generate-images 返回异常：", genResp.data);
          alert("生成图片时出错，请查看控制台");
          return;
        }

        const results = genResp.data.results;
        console.log("生成图片结果：", results);

        const BACKEND_BASE = "http://127.0.0.1:5000";

        if (!Array.isArray(this.aiPhotos)) this.aiPhotos = [];

        const setAiPhoto = (index, obj) => {
          if (typeof this.$set === 'function') {
            this.$set(this.aiPhotos, index, obj);
          } else {
            this.aiPhotos[index] = obj;
            this.aiPhotos = this.aiPhotos.slice();
          }
        };

        // 1. 将原始照片与 AI 生成的照片配对
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

          const pair = this.sentencePairs.find(p => p.index === idx); // ✅ [修改] 查找正确的 pair

          let targetAiIndex = -1;
          if (pair && pair.photo) {
            // (原始逻辑)
            // if (idx < this.photos.length) { 
            //   targetAiIndex = idx;
            // } else {
            //   const photoSlot = this.photos.findIndex(p => p.url === pair.photo);
            //   if (photoSlot !== -1) targetAiIndex = photoSlot;
            // }
            
            // ✅ [修改] 查找原始照片在 photos 数组中的索引
            const photoSlot = this.photos.findIndex(p => p.url === pair.photo || (p.file && pair.photo.includes("data:"))); // 修正
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

          // 2. 将生成的图片插入到 allPhotos 中
          const aiObj = {
            file: null,
            url: firstUrl,
            name: `ai_generated_${Date.now()}_${targetAiIndex}.jpg`,
            prompt: res.prompt || pair?.prompt || null,
            origin_pair_index: idx
          };

          // 插入到 allPhotos
          this.allPhotos.push({
            ...this.photos[targetAiIndex] || {}, // 可能是原始照片
            aiGenerated: aiObj,
            index: idx
          });

          // 更新 aiPhotos
          setAiPhoto(targetAiIndex, aiObj);
        });

        alert("图像生成并更新完毕，已显示在 AI 增强照片区");
      } catch (error) {
        console.error("Error generating prompts or images:", error);
        alert("生成图像时出错，请查看控制台");
      }
    },
    reselectText() {
      this.highlightedTexts = []
      this.userNarratives[this.currentStage] = ''
      console.log('已清空用户口述内容')
    },
    // ✅ [修改] 重构 showTextInput 以接收 key
    showTextInput(index, questionListKey) {
      // questionListKey 是 'questions' (S2) 或 'stage4Questions' (S4)
      const questions = this[questionListKey];
      if (questions && questions[index]) {
        questions[index].showInput = true;
      }
    },
    // ✅ [修改] 重构 skipQuestion 以接收 key
    skipQuestion(index, questionListKey) {
      const questions = this[questionListKey];
      if (!questions || !questions[index]) return;

      questions[index].answered = true;
      
      // 寻找下一个未回答问题
      const nextIndex = questions.findIndex((q, i) => i > index && !q.answered);
      if (nextIndex !== -1) {
        this.currentQuestionIndex = nextIndex;
      } else {
        // 如果后面没有了，就留在原地
        this.currentQuestionIndex = index;
      }
    },
    // 处理用户回答问题
    // ✅ [修改] 重构 submitAnswer 以接收 key
    submitAnswer(index, questionListKey) {
      const questions = this[questionListKey];
      if (!questions || !questions[index]) return;
      
      const question = questions[index];
      if (!question.answer.trim()) return; // 如果答案为空不提交

      question.answered = true;
      question.answer = question.answer.trim();
      question.showInput = false; // 关闭当前输入框

      // 自动切换到下一个未回答的问题
      // for (let i = index + 1; i < this.questions.length; i++) {
      //   if (!this.questions[i].answered) {
      //     this.currentQuestionIndex = i;
      //     return;
      //   }
      // }
      const nextIndex = questions.findIndex((q, i) => i > index && !q.answered);
      if (nextIndex !== -1) {
        this.currentQuestionIndex = nextIndex;
      } else {
         // 如果所有问题都已回答，则保持最后一个
        this.currentQuestionIndex = index;
      }
    },

    // --- ✅ (新增) Stage 4 方法 ---
    
    // ✅ (修改) 获取 Stage 4 问题 (根据新逻辑修改)
    async fetchStage4Questions() {
      console.log('开始获取 Stage 4 问题...')
      if (this.currentStage !== 4) return;

      this.isFetchingS4Questions = true;
      this.stage4Questions = []; // 清空旧问题
      try {
        // 1. Convert original photos (File objects) to base64
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        
        // 2. ✅ [FIX] Convert AI photos (localhost URLs) to base64
        const aiPhotoBase64s = await Promise.all(
          this.aiPhotos.map(p => this.urlToBase64(p.url))
        );
        
        const aiPhotoURLs = aiPhotoBase64s.filter(Boolean); // Filter out any nulls from failed conversions

        if (aiPhotoURLs.length === 0) {
            alert("没有可供提问的 AI 图像，或无法读取 AI 图像 (CORS/Network error)");
            this.isFetchingS4Questions = false;
            return;
        }

        const response = await axios.post('http://127.0.0.1:5000/generate-stage4-questions', {
          original_photos: base64Photos,
          ai_photos_urls: aiPhotoURLs, // ✅ Now sending base64 data URLs
          // ✅ [Note] The server.py route already expects 'suggestion' to be missing
        });

        this.stage4Questions = response.data.questions || [];
        this.currentQuestionIndex = 0; // 重置问题索引
      } catch (error) {
        console.error("Error fetching stage 4 questions:", error);
        alert("获取 Stage 4 问题失败，请查看控制台");
      } finally {
        this.isFetchingS4Questions = false;
      }
    },

    // ✅ (新增 Stage 4) 更新文本
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
        current_narrative: this.assistantIntegratedText, // 发送黑字基础
        new_qa_pairs: qa_pairs 
      });

      try {
        this.isUpdatingText = true;
        this.assistantUpdatedText = ''; // 清空旧的紫字

        const resp = await axios.post('http://127.0.0.1:5000/update-text', {
          current_narrative: this.assistantIntegratedText,
          new_qa_pairs: qa_pairs
        }, { timeout: 120000 });

        if (resp.data && resp.data.updated_text) {
          // 只把*新*结果写进 assistantUpdatedText (紫色文本)
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
    
    // ✅ (新增 Stage 4) 图像更新 (根据 S3 逻辑，用于 continueModification)
    async generateImagesFromUpdatedNarrative() {
      console.log('S4: 开始根据更新后的叙事文本生成新图片...');
      
      // ✅ 关键：Stage 4 使用合并后的完整叙事
      const narrative = (this.assistantIntegratedText + '\n' + this.assistantUpdatedText).trim(); 
      
      if (!narrative) {
        alert("AI 叙事为空，无法生成新图片");
        return;
      }
      
      // (其余逻辑与 generateImages 基本相同)
      try {
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative, // 使用合并后的 narrative
        });

        this.sentencePairs = response.data.sentence_pairs || [];
        console.log('S4 图文配对结果：', toRaw(this.sentencePairs));

        this.sentencePairs.sort((a, b) => a.index - b.index);
        // alert("S4: Qwen已完成分句与prompt生成"); // 暂时注释掉 alert

        const toGenerate = this.sentencePairs.map((p, i) => ({ ...p, __index: i }))
                                        .filter(p => p.prompt);
        if (!toGenerate.length) {
          console.log("S4: 没有需要生成的 new prompt，跳过");
          return;
        }

        // ✅ 关键: 清空旧的 AI 照片，准备接收新一轮
        this.aiPhotos = []; 
        this.allPhotos = [];

        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: this.sentencePairs
        }, { timeout: 600000 });

        if (!(genResp.data && genResp.data.results)) {
          console.error("S4 generate-images 返回异常：", genResp.data);
          alert("S4 生成图片时出错，请查看控制台");
          return;
        }

        const results = genResp.data.results;
        console.log("S4 生成图片结果：", results);

        const BACKEND_BASE = "http://127.0.0.1:5000";
        if (!Array.isArray(this.aiPhotos)) this.aiPhotos = [];

        const setAiPhoto = (index, obj) => {
          if (typeof this.$set === 'function') {
            this.$set(this.aiPhotos, index, obj);
          } else {
            this.aiPhotos[index] = obj;
            this.aiPhotos = this.aiPhotos.slice();
          }
        };

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
          const pair = this.sentencePairs.find(p => p.index === idx); // ✅ [修改] 查找正确的 pair
          
          let targetAiIndex = -1;
          if (pair && pair.photo) {
            const photoSlot = this.photos.findIndex(p => p.url === pair.photo || (p.file && pair.photo.includes("data:"))); // 修正
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
            file: null, url: firstUrl,
            name: `ai_generated_s4_${Date.now()}_${targetAiIndex}.jpg`,
            prompt: res.prompt || pair?.prompt || null, // ✅ 保存 prompt
            origin_pair_index: idx
          };
          this.allPhotos.push({
            ...this.photos[targetAiIndex] || {},
            aiGenerated: aiObj, index: idx
          });
          setAiPhoto(targetAiIndex, aiObj);
        });

        console.log("S4: 图像更新完毕");
        // alert("S4: 图像更新完毕");
      } catch (error) {
        console.error("Error in generateImagesFromUpdatedNarrative:", error);
        alert("S4: 根据叙事更新图像时出错，请查看控制台");
      }
    },

    // ✅ (新增 Stage 4) 图像更新 (根据用户建议)
    async updateImagesWithSuggestion() {
      if (this.currentStage !== 4) return;
      
      const suggestion = this.aiSuggestion.trim();
      if (!suggestion) {
        alert("请输入您对图像的修改建议");
        return;
      }
      
      if (this.aiPhotos.length === 0) {
        alert("当前没有 AI 图像可供修改");
        return;
      }
      
      console.log(`S4: 开始根据建议 "${suggestion}" 修改 ${this.aiPhotos.length} 张图片...`);
      
      // 1. 手动构建 sentence_pairs
      const manual_sentence_pairs = this.aiPhotos.map((photo, index) => {
        const original_prompt = photo.prompt || "a photo"; // 降级处理
        return {
          index: index, // 使用 aiPhotos 的索引
          prompt: `${original_prompt}, ${suggestion}`, // 附加建议
          photo: null // 我们是生成新图，不是图生图
        }
      }).filter(p => p.prompt); // 确保有 prompt
      
      if (manual_sentence_pairs.length === 0) {
        alert("没有找到可供修改的原始 Prompt");
        return;
      }
      
      console.log("S4: 手动生成的 new_prompts:", manual_sentence_pairs);

      // 2. 调用 /generate-images
      try {
        const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
          sentence_pairs: manual_sentence_pairs
        }, { timeout: 600000 });
        
        if (!(genResp.data && genResp.data.results)) {
          console.error("S4 updateImagesWithSuggestion 返回异常：", genResp.data);
          alert("根据建议更新图片时出错，请查看控制台");
          return;
        }

        const results = genResp.data.results;
        console.log("S4 根据建议生成的图片结果：", results);

        const BACKEND_BASE = "http://127.0.0.1:5000";

        const setAiPhoto = (index, obj) => {
          if (typeof this.$set === 'function') {
            this.$set(this.aiPhotos, index, obj);
          } else {
            this.aiPhotos[index] = obj;
            this.aiPhotos = this.aiPhotos.slice();
          }
        };

        // 3. 原地替换 aiPhotos
        results.forEach(res => {
          const idx = res.index; // 这里的 index 对应我们 aiPhotos 的索引
          if (idx >= 0 && idx < this.aiPhotos.length) {
            const urls = res.generated_urls || [];
            if (!urls.length) return; // 跳过生成失败的

            let firstUrl = urls[0];
            if (firstUrl.startsWith("/")) {
              firstUrl = BACKEND_BASE + firstUrl;
            } else if (!firstUrl.startsWith("http://") && !firstUrl.startsWith("https://")) {
              firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
            }
            
            // 更新 aiPhotos 数组中*对应索引*的对象
            const updatedAiObj = {
              ...this.aiPhotos[idx], // 保留旧信息
              url: firstUrl, // 更新 URL
              prompt: res.prompt, // 更新为修改后的 Prompt
              name: `ai_modified_${Date.now()}_${idx}.jpg`,
            };
            
            setAiPhoto(idx, updatedAiObj);
          }
        });

        alert("根据您的建议，图像更新完毕！");
        
      } catch (error) {
         console.error("Error in updateImagesWithSuggestion:", error);
         alert("S4: 根据建议更新图像时出错，请查看控制台");
      }
    },
    
    // --- ✅ [新增] Req 1 拖拽方法 ---
    startResizeAiResult(e) {
      this.isResizingAiResult = true
      this.startY_ai = e.clientY
      this.startHeight_ai = this.aiResultHeight
      document.addEventListener('mousemove', this.doResizeAiResult)
      document.addEventListener('mouseup', this.stopResizeAiResult)
    },
    doResizeAiResult(e) {
      if (!this.isResizingAiResult) return
      const diff = e.clientY - this.startY_ai
      const newHeight = Math.min(Math.max(100, this.startHeight_ai + diff), 400) // 100px min, 400px max
      this.aiResultHeight = newHeight
    },
    stopResizeAiResult() {
      this.isResizingAiResult = false
      document.removeEventListener('mousemove', this.doResizeAiResult)
      document.removeEventListener('mouseup', this.stopResizeAiResult)
    },
    
    // --- ✅ [新增] Req 2 终止迭代 ---
    stopIteration() {
      this.iterationStopped = true;
      console.log("用户终止迭代");
    },
    
    // --- ✅ [新增] Req 4 编号 ---
    getLetterIndex(idx) {
      return String.fromCharCode(97 + idx); // 97 = 'a'
    }
    // --- END Stage 4 ---
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
</style>