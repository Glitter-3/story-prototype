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
          <!-- 统一的照片展示区：Stage3，4 时拆分为原图 + AI 增强图 -->
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

          <!-- Stage3/4 专用：原图 + AI增强图 -->
          <div v-else-if="currentStage === 3 || currentStage === 4" class="split-container">
            <div class="split-title">🎞️ 原照片集</div>

            <!-- 上半部：原图 -->
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

            <!-- 下半部：AI 增强图 -->
            <div class="bottom-panel">
              <div class="split-title">🪄 AI 增强照片</div>
              <div class="photo-grid ai-photo-grid">
                <div class="photo-slot" v-for="(ap, idx) in aiPhotos" :key="'ai-'+idx">
                  <div class="photo-placeholder ai-placeholder" @click="onClickAiSlot(idx)">
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

          <!-- Stage5 专用：原图 + AI增强视频（只保留一个相框） -->
          <div v-else-if="currentStage === 5" class="split-container">
            <div class="split-title">🎞️ 原照片集</div>

            <!-- 上半部：原图 -->
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

            <!-- 下半部：AI 增强视频 -->
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
          
        <!-- ✅ 改为可编辑div，同时能显示蓝色旧内容 -->
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

      <!-- 右侧AI助手 -->
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
            已迭代 {{ iterationCount }} 轮
          </span>
          <span class="progress-text" v-if="currentStage === 2">
            {{ answeredCount }}/{{ questions.length }} 问题已回答
          </span>

        </div>

        <!-- Stage3 专用：显示 Qwen 整合结果（只读） -->
        <div v-if="currentStage === 3" class="assistant-integration-result" style="margin:10px 0; padding:10px; border-radius:6px; border:1px dashed #d0d7de; background:#fafafa;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <strong>🧾 AI 整合结果（仅供参考）</strong>
            <div style="font-size:12px; color:#666;">
              <span v-if="integrating">整合中...</span>
            </div>
          </div>

          <div v-if="assistantIntegratedText" style="white-space:pre-wrap; max-height:220px; overflow:auto; color:#222; line-height:1.6;">
            {{ assistantIntegratedText }}
          </div>
          <div v-else style="color:#888; font-size:13px;">
            （尚无整合结果，点击下方「整合文本」或在 Stage 2 回答问题后再试）
          </div>
        </div>

        <!-- Stage 4 专用：AI 建议输入区 -->
        <div v-if="currentStage === 4" class="ai-modify-section" style="margin:10px 0; text-align:center;">
          <label style="display:block; font-weight:600; margin-bottom:12px; text-align:center;">
            你对当前AI修改的照片有什么建议？
          </label>
          <textarea
            v-model="aiSuggestion"
            rows="24" 
            placeholder="请输入你的建议，例如：色调更暖、人物锐化、保留背景细节等..."
            style="width:100%; box-sizing:border-box; padding:8px; border-radius:6px; border:1px solid #ddd; font-size:14px;"
          ></textarea>
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

        <!-- Stage 4 专用按钮，两个上下排列 -->
        <div v-if="currentStage === 4" style="display:flex; flex-direction:column; gap:8px; margin-top:10px;">
          <button class="control-btn primary" @click="continueModification">继续修改</button>
        </div>

        <!-- Stage 2 的开始提问按钮 -->
        <button 
          v-if="currentStage === 2" 
          class="control-btn primary"
          @click="fetchQuestions">
          开始提问
        </button>

        <!-- Stage3：整合文本（把 Stage2 的问答 + Stage2 的口述合并成连贯叙述，输出到 Stage3 编辑器） -->
        <button 
          v-if="currentStage === 3" 
          class="control-btn primary"
          :disabled="integrating"
          @click="integrateText">
          {{ integrating ? '整合中...' : '整合文本' }}
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
      maxIterations: 8,       // 最大迭代轮数
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
    }
  },
  computed: {
    progressPercentage() {
      if (this.currentStage === 4) {
        return (this.iterationCount / this.maxIterations) * 100
      }
      return (this.answeredCount / this.questions.length) * 100
    },
    answeredCount() {
      return this.questions.filter(q => q.answered).length
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

      // 判断元素是否为蓝色历史段（兼容 style 或 computed）
      const isBlueNode = (n) => {
        if (!n) return false;
        const inline = (n.style && n.style.color) ? n.style.color.toLowerCase() : '';
        if (inline && inline.includes('#007bff')) return true;
        try {
          const comp = window.getComputedStyle(n).color;
          if (comp === 'rgb(0, 123, 255)') return true;
        } catch (err) {}
        return false;
      };

      // 如果光标在蓝色段内，拆分蓝色并插入黑色占位
      if (isBlueNode(anchorEl)) {
        this.splitBlueSpanAtRange(anchorEl, range);
        // splitBlueSpanAtRange 会把光标放到黑色占位里
      }

      // 保存当前 HTML（蓝色段已被正确拆分或保持不动）
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
          // 生成一个蓝色 span（历史） + 紧随一个黑色空 span（用于后续输入）
          const blue = `<span style="color:#007BFF;">${this.escapeHtml(prevText)}</span>`;
          const black = `<span style="color:#000000;">\u200B</span>`;
          this.userNarratives[stage] = blue + black;
        } else {
          this.userNarratives[stage] = '';
        }
      }

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
    // 新增：把蓝色 span 在光标处拆成 左蓝 + 黑色插入位 + 右蓝
    splitBlueSpanAtRange(blueSpan, range) {
      // blueSpan 必须包含文本（如果包含复杂子节点这里做一个简单文本抽取处理）
      const tmp = document.createElement('div');
      tmp.appendChild(blueSpan.cloneNode(true));
      const fullText = tmp.textContent || '';

      // 通过一个 Range 计算从 blueSpan 开始到光标处的文本长度
      const preRange = document.createRange();
      preRange.setStart(blueSpan, 0);
      try {
        preRange.setEnd(range.startContainer, range.startOffset);
      } catch (err) {
        // 若 setEnd 失败（极少情况），退回到以文本长度分割
        preRange.selectNodeContents(blueSpan);
        preRange.setEnd(blueSpan, 0);
      }
      const leftText = preRange.toString();
      const rightText = fullText.slice(leftText.length);

      const parent = blueSpan.parentNode;

      // 创建新的左蓝 span（若 leftText 为空则不插入）
      if (leftText) {
        const leftSpan = document.createElement('span');
        leftSpan.style.color = '#007BFF';
        leftSpan.textContent = leftText;
        parent.insertBefore(leftSpan, blueSpan);
      }

      // 创建黑色插入位（带一个零宽字符，便于放置光标）
      const blackSpan = document.createElement('span');
      blackSpan.style.color = '#000000';
      blackSpan.innerHTML = '\u200B'; // zero-width space
      parent.insertBefore(blackSpan, blueSpan);

      // 创建新的右蓝 span（若 rightText 为空则不插入）
      if (rightText) {
        const rightSpan = document.createElement('span');
        rightSpan.style.color = '#007BFF';
        rightSpan.textContent = rightText;
        parent.insertBefore(rightSpan, blueSpan);
      }

      // 移除原来的 blueSpan（已被拆分）
      parent.removeChild(blueSpan);

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
    // 判断节点是否为我们定义的“蓝色历史段”
    isBlueNode(node) {
      if (!node) return false;
      if (node.nodeType !== 1) return false; // 不是元素
      // 优先检查内联 style，再兼容 computed style rgb
      const inline = (node.style && node.style.color) ? node.style.color.toLowerCase() : '';
      if (inline && inline.includes('#007bff')) return true;
      try {
        const comp = window.getComputedStyle(node).color;
        if (comp === 'rgb(0, 123, 255)') return true;
      } catch (err) {}
      return false;
    },

    // 处理删除键（Backspace / Delete），保证蓝色段可以被整段删除或在蓝字间插入的黑字可删
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
        // 则尝试删除前一个 sibling，如果前一个是蓝色 span，就删除它（整段删除）
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
            if (prev && this.isBlueNode(prev)) {
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

        // 情况 B：如果光标直接位于蓝色 span 内（比如用户把光标点在蓝字中），
        // 我们允许在蓝字内部删除字符（默认行为）——无需阻止
        // 但若想要在蓝字内部输入把插入部分变黑，已有 onEditableInput 会拆分
        return; // 让默认行为继续
      }

      // ---------- Delete 键 逻辑 ----------
      if (e.key === 'Delete') {
        // 情况：若光标在黑色 span 末尾并且下一个 sibling 是蓝色 span -> 删除那个蓝色段
        // 判定是否在元素末尾
        const isAtEnd = (() => {
          if (range.startContainer.nodeType === 3) {
            return range.startOffset === range.startContainer.textContent.length;
          }
          return range.startOffset === anchorEl.childNodes.length;
        })();

        if (isAtEnd) {
          const next = anchorEl.nextSibling;
          if (next && this.isBlueNode(next)) {
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

    continueModification() {
      if (this.iterationCount < this.maxIterations) {
        this.iterationCount += 1;
      }
      console.log(`当前迭代轮数：${ this.iterationCount}`);
      this.aiSuggestion = ''
      
      // 如果你希望每次迭代同时做一些 AI 修改逻辑，也可以在这里调用：
      // this.applyAiModification()
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

          const pair = this.sentencePairs[idx];

          let targetAiIndex = -1;
          if (pair && pair.photo) {
            if (idx < this.photos.length) {
              targetAiIndex = idx;
            } else {
              const photoSlot = this.photos.findIndex(p => p.url === pair.photo);
              if (photoSlot !== -1) targetAiIndex = photoSlot;
            }
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
    showTextInput(index) {
      this.questions[index].showInput = true
    },
    skipQuestion(index) {
      this.questions[index].answered = true
      if (index < this.questions.length - 1) this.currentQuestionIndex = index + 1
    },
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
}

.control-btn:hover {
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