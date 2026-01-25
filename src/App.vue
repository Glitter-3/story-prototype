<template>
  <div class="photo-story-container" :class="`stage-${currentStage}`">
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
        <div v-if="currentStage !== 2" class="photo-panel" :class="{ collapsed: isPhotoPanelCollapsed }">
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
              <button v-if="currentStage === 1" class="control-btn" @click="groupPhotosByTime" :disabled="photos.length === 0 || groupingInProgress">
                {{ groupingInProgress ? '分组中…' : '照片分组' }}
              </button>
              <button
                class="control-btn"
                @click="isPhotoPanelCollapsed = !isPhotoPanelCollapsed"
              >
                {{ isPhotoPanelCollapsed ? '展开' : '收起' }}
              </button>

            </div>
          </div>
          <div  class="photo-panel-content"  v-show="!isPhotoPanelCollapsed">
            <div v-if="currentStage !== 3 && currentStage !== 4 && currentStage !== 5" class="photo-grid">
              <div class="photo-slot" v-for="(photo, index) in photos" :key="index">
                <div class="photo-placeholder" draggable="currentStage === 1" @dragstart="currentStage === 1 && onPhotoDragStart($event, idx)" @click="triggerFileInput(index)" v-if="currentStage === 1">
                  <template v-if="photo.url">
                    <img :src="photo.url" class="photo-preview" alt="预览图片" />
                  </template>
                  <template v-else>
                    <span class="photo-number">{{ index + 1 }}</span>
                    <span class="add-icon">+</span>
                  </template>
                </div>

                <div class="photo-placeholder" draggable="currentStage === 1" @dragstart="currentStage === 1 && onPhotoDragStart($event, idx)" v-else>
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

                    <div class="ai-photo-controls" style="display:flex; gap:4px; width:100%; margin-top:4px;">
                      <button 
                        class="edit-photo-btn" 
                        @click="openSuggestionModal(idx)"
                        :disabled="iterationStopped"> ✏️ 指令
                      </button>
                      <button 
                        class="edit-photo-btn" 
                        style="color: #ff4d4f; border-color: #ffccc7;"
                        @click="deleteAiPhoto(idx)"> 🗑️ 删除
                      </button>
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

        </div>
        <!-- Stage 1 / Stage 2 时间轴展示 -->
        <div v-if="showGroups" class="timeline-wrapper">

          <!-- ================= Stage 1：横向时间轴（可编辑） ================= -->
          <div v-if="currentStage === 1" class="timeline horizontal">

            <div
              v-for="(group, gIdx) in photoGroups"
              :key="gIdx"
              class="timeline-node"
            >
              <!-- 插入 group（左侧） -->
              <button
                v-if="gIdx === 0"
                class="insert-group-btn"
                @click="addNewGroupAfter(-1)"
              >＋</button>

              <!-- group 主体 -->
              <div class="group-card">
                <div
                  class="group-title editable"
                  @click="editGroupName(gIdx)"
                >
                  {{ group.name }}
                </div>

                <!-- 子分组（全部在下方） -->
                <div class="subgroup-list">
                  <div
                    v-for="(subgroup, sgIdx) in group.subgroups"
                    :key="sgIdx"
                    class="subgroup-box"
                    @dragover.prevent
                    @drop="onSubgroupDrop($event, gIdx, sgIdx)"
                  >
                    <div
                      class="subgroup-title editable"
                      @click="editSubgroupName(gIdx, sgIdx)"
                    >
                      {{ subgroup.name }}
                    </div>

                    <div class="photo-grid">
                      <div
                        class="photo-slot"
                        v-for="idx in subgroup.photo_indices"
                        :key="idx"
                      >
                        <div
                          class="photo-placeholder"
                          draggable="true"
                          @dragstart="onPhotoDragStart($event, idx)"
                        >
                          <img
                            v-if="photos[idx]?.url"
                            :src="photos[idx].url"
                            class="photo-preview"
                          />
                        </div>
                      </div>
                    </div>

                    <!-- 删除 subgroup -->
                    <button
                      v-if="group.subgroups.length >= 2"
                      class="control-btn"
                      style="padding: 4px 8px; font-size: 12px; background: #ffebee; color: #e53935; border-color: #ffcdd2;"
                      @click="deleteSubgroup(gIdx, sgIdx)"
                    >
                      删除子分组
                    </button>
                  </div>
                </div>

                <!-- group 操作 -->
                <div class="group-actions">
                  <button class="control-btn" style="padding: 4px 8px; font-size: 12px;" @click="addSubgroup(gIdx)">＋ 子分组</button>
                  <button class="control-btn" style="padding: 4px 8px; font-size: 12px; background: #ffebee; color: #e53935; border-color: #ffcdd2;" @click="deleteGroup(gIdx)">删除阶段</button>
                </div>
              </div>

              <!-- 插入 group（右侧） -->
              <button
                class="insert-group-btn"
                @click="addNewGroupAfter(gIdx)"
              >＋</button>
            </div>
          </div>

          <!-- ================= Stage 2：纵向时间轴（只读） ================= -->
          <div v-if="currentStage === 2" class="timeline vertical">

            <div
              v-for="(group, gIdx) in photoGroupsWithSummaries"
              :key="gIdx"
              class="timeline-node-vertical"
            >
              <!-- 时间节点 -->
              <div class="group-node-vertical">
                <div class="group-title">
                  {{ group.name }}
                </div>
              </div>

              <!-- 子分组 -->
              <div class="subgroup-list-vertical">
                <div
                  v-for="(subgroup, sgIdx) in group.subgroups"
                  :key="sgIdx"
                  class="subgroup-box"
                >
                  <div class="subgroup-title">
                    {{ subgroup.name }}
                  </div>
                  
                  <div class="summary-header">
                    <strong>🧠 记忆总结</strong>

                    <div class="summary-actions">
                      <button
                        v-if="!subgroupSummaries[gIdx]?.[sgIdx]?.isEditing"
                        class="control-btn"
                        @click="startEditSubgroupSummary(gIdx, sgIdx)"
                      >
                        修改
                      </button>

                      <template v-else>
                        <div class="inter-edit-actions">
                          <button @click="confirmEditSubgroupSummary(gIdx, sgIdx)"> 确认 </button>
                          <button @click="cancelEditSubgroupSummary(gIdx, sgIdx)"> 取消 </button>
                        </div>
                      </template>
                    </div>
                  </div>

                  <!-- 4W + 情感 -->
                  <div class="subgroup-summary">
                    <!-- ================= 展示态 ================= -->
                    <div
                      v-if="!subgroupSummaries[gIdx]?.[sgIdx]?.isEditing"
                    >
                      <div><strong>人物：</strong>{{ subgroupSummaries[gIdx]?.[sgIdx]?.data?.who || '—' }}</div>
                      <div><strong>时间：</strong>{{ subgroupSummaries[gIdx]?.[sgIdx]?.data?.when || '—' }}</div>
                      <div><strong>地点：</strong>{{ subgroupSummaries[gIdx]?.[sgIdx]?.data?.where || '—' }}</div>
                      <div><strong>事件：</strong>{{ subgroupSummaries[gIdx]?.[sgIdx]?.data?.what || '—' }}</div>
                      <div><strong>情感：</strong>{{ subgroupSummaries[gIdx]?.[sgIdx]?.data?.emotion || '—' }}</div>
                    </div>

                    <!-- ================= 编辑态 ================= -->
                    <div
                      v-else
                      class="summary-edit"
                    >
                      <div class="summary-edit-item">
                        <label>👤 人物</label>
                        <input v-model="subgroupSummaries[gIdx][sgIdx].editBuffer.who" />
                      </div>

                      <div class="summary-edit-item">
                        <label>⏰ 时间</label>
                        <input v-model="subgroupSummaries[gIdx][sgIdx].editBuffer.when" />
                      </div>

                      <div class="summary-edit-item">
                        <label>📍 地点</label>
                        <input v-model="subgroupSummaries[gIdx][sgIdx].editBuffer.where" />
                      </div>

                      <div class="summary-edit-item">
                        <label>📖 事件</label>
                        <textarea
                          v-model="subgroupSummaries[gIdx][sgIdx].editBuffer.what"
                          rows="2"
                        />
                      </div>

                      <div class="summary-edit-item">
                        <label>💗 情感</label>
                        <input v-model="subgroupSummaries[gIdx][sgIdx].editBuffer.emotion" />
                      </div>
                    </div>
                  </div>

                  <!-- 照片 -->
                  <div class="photo-grid">
                    <div
                      class="photo-slot"
                      v-for="idx in subgroup.photo_indices"
                      :key="idx"
                    >
                      <img
                        v-if="photos[idx]?.url"
                        :src="photos[idx].url"
                        class="photo-preview"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- 阶段过渡 -->
              <div
                v-if="interGroupSummaries[`${gIdx}-${gIdx + 1}`]"
                class="inter-group-block"
              >
                <!-- Header -->
                <div class="summary-header">
                  <strong>阶段过渡</strong>

                  <div class="summary-actions">
                    <!-- 展示态：修改 -->
                    <button
                      v-if="!interGroupSummaries[`${gIdx}-${gIdx + 1}`].isEditing"
                      class="control-btn"
                      @click="startEditInterGroupSummary(gIdx, gIdx + 1)"
                    >
                      修改
                    </button>

                    <!-- 编辑态：确认 / 取消 -->
                    <template v-else>
                      <div class="inter-edit-actions">
                        <button
                          @click="confirmEditInterGroupSummary(gIdx, gIdx + 1)"
                        >
                          确认
                        </button>
                        <button
                          @click="cancelEditInterGroupSummary(gIdx, gIdx + 1)"
                        >
                          取消
                        </button>
                      </div>
                    </template>
                  </div>
                </div>

                <!-- 📄 展示态 -->
                <div
                  v-if="!interGroupSummaries[`${gIdx}-${gIdx + 1}`].isEditing"
                  class="inter-summary-text"
                >
                  {{ interGroupSummaries[`${gIdx}-${gIdx + 1}`].data.text || '—' }}
                </div>

                <!-- ✏️ 编辑态 -->
                <div v-else>
                  <textarea
                    v-model="interGroupSummaries[`${gIdx}-${gIdx + 1}`].editBuffer.text"
                    class="inter-edit-textarea"
                  />
                </div>
              </div>

            </div>
          </div>

        </div>


        <div 
          v-if="currentStage !== 2"
          class="resize-handle" 
          @mousedown="startResize"
          :class="{ 'resizing': isResizing }">
       <div class= "handle-line"></div>
        </div>

        <div v-if="currentStage != 2" class="narrative-section" :class="{ collapsed: isNarrativeCollapsed }">
          <div class="panel-header">
            <h3>📝 用户口述</h3>
            <div class="panel-controls">
              <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
              <button class="control-btn" @click="reselectText">🔄 重新口述</button>

              <button v-if="currentStage === 3" class="control-btn" @click="generateImages">图像补全</button>
              <button
                class="control-btn"
                @click="isNarrativeCollapsed = !isNarrativeCollapsed"
              >
                {{ isNarrativeCollapsed ? '展开' : '收起' }}
              </button>
            </div>
          </div>
          <div class="narrative-content-wrapper" v-show="!isNarrativeCollapsed">  
            <div
                ref="editableNarrative"
                class="narrative-input"
                contenteditable="true"
                @input="onEditableInput"
                @keydown="onEditableKeydown"
                :placeholder="'请在此输入您对这阶段照片的描述、回忆或故事……'"
                style="white-space: pre-wrap; overflow-y: auto; min-height: 160px; border: 1px solid #ccc; padding: 10px; border-radius: 6px; color: black;"
              >
            </div>
          </div>
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

    <div v-if="showPromptModal" class="suggestion-modal-backdrop">
      <div class="suggestion-modal" style="width: 800px; max-height: 80vh; overflow-y: auto;">
        <h3>🚀 确认生成指令 (Prompts)</h3>
        <p style="font-size: 13px; color: #666; margin-bottom: 12px;">
          AI 已根据您的叙述生成了以下画面指令。请检查并修改 Prompt，或删除重复/不需要的画面，以避免图像雷同。
        </p>

        <div v-if="pendingSentencePairs.length === 0" style="text-align:center; color:#999; padding:20px;">
          没有可生成的 Prompts。
        </div>

        <div v-for="(item, idx) in pendingSentencePairs" :key="idx" class="prompt-edit-item" 
             style="display:flex; gap:12px; border:1px solid #eee; padding:10px; margin-bottom:10px; border-radius:6px; align-items:flex-start;">
          
          <div style="width: 80px; flex-shrink:0;">
             <img v-if="item.photo" :src="item.photo" style="width:100%; border-radius:4px; border:1px solid #ddd;">
             <div v-else style="width:100%; height:80px; background:#f0f0f0; display:flex; align-items:center; justify-content:center; color:#ccc; font-size:10px;">纯文生图</div>
          </div>

          <div style="flex:1;">
            <div style="font-size:12px; color:#555; margin-bottom:4px; font-weight:bold;">对应原句：</div>
            <div style="font-size:13px; color:#333; margin-bottom:8px; background:#f9f9f9; padding:6px; border-radius:4px;">
              {{ item.sentence || '(无)' }}
            </div>
            
            <div style="font-size:12px; color:#555; margin-bottom:4px; font-weight:bold;">生成 Prompt (可修改)：</div>
            <textarea v-model="item.prompt" rows="3" 
                      style="width:100%; padding:6px; font-size:13px; border:1px solid #ddd; border-radius:4px; resize:vertical;"></textarea>
          </div>

          <button class="control-btn" @click="removePromptPair(idx)" style="color:red; border-color:#ffcccc; font-size:12px;">
            🗑️ 删除
          </button>
        </div>

        <div class="modal-actions" style="border-top:1px solid #eee; padding-top:12px; margin-top:12px;">
          <button class="control-btn" @click="showPromptModal = false">取消</button>
          <button class="control-btn primary" @click="confirmGenerateImages()" :disabled="pendingSentencePairs.length === 0">
            确认并生成图片 ({{ pendingSentencePairs.length }} 张)
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
      subgroupSummaries: {},
      interGroupSummaries: {}, 
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
      photoGroups: [], // 保存分组结果
      showGroups: false,  
      groupingInProgress: false,
      isPhotoPanelCollapsed: false,
      isNarrativeCollapsed: false,
      // 视频生成状态
      isGeneratingVideo: false,
      videoGenerationError: null,
      // stage 3&4 整合文本用户修改功能
      assistantEditMode: false,        // 是否处于编辑模式（显示 textarea）
      assistantEditBuffer: '',        // 编辑缓冲文本（textarea 的 v-model）
      assistantEditedByUser: false,   // 标记用户是否已手动编辑过 AI 文本
      stage3Modifications: [],        // 记录 Stage3 的每次用户修改（timestamp, before, after）
      
      highlightedSentence: null, // ✅ [修改 C.2] 新增高亮状态
      
      // ✅ [Priority 1] Prompt 确认相关状态
      showPromptModal: false,
      pendingSentencePairs: [], // 暂存待用户确认的 pairs
      pendingBase64Photos: [], // 暂存原始图片 base64，供生图使用
    }
  },
  computed: {
    photoGroupsWithSummaries() {
      return this.photoGroups.map((group, gIdx) => ({
        ...group,
        subgroups: group.subgroups.map((subgroup, sgIdx) => ({
          ...subgroup,
          summary: this.subgroupSummaries[gIdx]?.[sgIdx]?.data || {}
        }))
      }));
    },
    interQuestionsMap() {
      const map = {};
      this.questions.forEach(q => {
        if (q.type === "inter" &&
            q.left_group_id != null &&
            q.right_group_id != null) {
          const key = `${q.left_group_id}-${q.right_group_id}`;
          if (!map[key]) map[key] = [];
          map[key].push(q);
        }
      });
      return map;
    },
    // ✅ [修改 C.5] 新增 computed 属性用于高亮
    highlightedStoryText() {
      // 1. 确定要显示的文本源
      // 如果有 assistantUpdatedText，说明刚刚完成了更新（里面包含了紫色标签），直接使用它
      // 否则使用 integratedText
      let sourceText = this.assistantUpdatedText || this.assistantIntegratedText || '';
      
      // 注意：如果是 UpdatedText，我们在 updateText 方法里已经处理过 HTML 标签了，所以这里不要再全量 escapeHtml
      // 只有当显示纯 IntegratedText 时才需要防注入 (简单起见，假设后端返回是安全的，或者只对非HTML部分处理)
      
      // 简单的处理逻辑：
      let text = sourceText; 
      if (!this.assistantUpdatedText) {
          text = this.escapeHtml(sourceText);
      }

      // 2. 处理鼠标悬停高亮 (Hover) - 仅针对非 HTML 标签部分的高亮会比较复杂
      // 为简化逻辑，如果当前处于“查看更新结果”状态（有紫色文字），暂时禁用 Hover 高亮，以免 HTML 结构冲突
      if (this.highlightedSentence && !this.assistantUpdatedText) {
        const sentence = this.escapeHtml(this.highlightedSentence);
        const regex = new RegExp(this.escapeRegExp(sentence), 'g');
        text = text.replace(regex, `<span style="background-color: #fff8c4; border-radius: 3px; padding: 1px 0;">${sentence}</span>`);
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
    // 【新增】正则转义辅助函数
    escapeRegExp(string) {
      return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); 
    },

    // 【新增】字符串相似度计算 (用于智能复用图片)
    calculateSimilarity(str1, str2) {
       if(!str1 || !str2) return 0;
       const s1 = new Set(str1.split(''));
       const s2 = new Set(str2.split(''));
       const intersection = new Set([...s1].filter(x => s2.has(x)));
       const union = new Set([...s1, ...s2]);
       return intersection.size / union.size;
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
      if (stage === 2 && this.photoGroups.length === 0) {
        alert('请先在 Stage 1 完成照片分组');
        return;
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

        /* ===============================
        * 1️⃣ 组内子分组（subgroupSummaries）初始化
        * =============================== */
        if (!this.subgroupSummaries || typeof this.subgroupSummaries !== 'object') {
          this.subgroupSummaries = {}
        }

        // 清理
        Object.keys(this.subgroupSummaries).forEach(gIdx => {
          if (!this.photoGroups[gIdx]) {
            delete this.subgroupSummaries[gIdx]
          }
        })

        this.photoGroups.forEach((group, gIdx) => {
          if (!this.subgroupSummaries[gIdx]) {
            this.subgroupSummaries[gIdx] = {}
          }

          group.subgroups.forEach((sg, sgIdx) => {
            if (!this.subgroupSummaries[gIdx][sgIdx]) {
              this.subgroupSummaries[gIdx][sgIdx] = {
                data: {
                  who: "",
                  when: group.name,   // ⭐ 默认继承 group 标题
                  where: "",
                  what: "",
                  emotion: ""
                },
                editBuffer: null,
                isEditing: false,
                lastUpdatedBy: "init"
              }
            }
          })
        })

        /* ===============================
        * 2️⃣ 组间（interGroupSummaries）初始化
        * =============================== */
        if (!this.interGroupSummaries || typeof this.interGroupSummaries !== 'object') {
          this.interGroupSummaries = {};
        }

        for (let i = 0; i < this.photoGroups.length - 1; i++) {
          const key = `${i}-${i + 1}`;
          if (!this.interGroupSummaries[key]) {
            this.interGroupSummaries[key] = {
              data: {
                text: ""
              },
              editBuffer: {
                text: ""
              },
              isEditing: false,
              lastUpdatedBy: 'init'
            };
          }
        }
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
    async groupPhotosByTime() {
      if (this.photos.length === 0) return;
      this.groupingInProgress = true;
      try {
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );
        const narrative = this.userNarratives[1] || '';
        const resp = await axios.post('http://127.0.0.1:5000/group-photos-by-time', {
          photos: base64Photos,
          narrative: narrative
        });
        if (resp.data.groups) {
          this.photoGroups = resp.data.groups.map(g => ({
            name: g.name,
            subgroups: (g.subgroups && g.subgroups.length > 0)
              ? g.subgroups.map(sg => ({
                  name: sg.name || '默认子分组',
                  photo_indices: sg.photo_indices ? [...sg.photo_indices] : []
                }))
              : [{
                  name: '默认子分组',
                  photo_indices: []
                }]
          }));
          this.showGroups = true;
        } else {
          alert('分组失败，请重试');
        }
      } catch (err) {
        console.error('分组出错:', err);
        alert('分组时发生错误，请查看控制台');
      } finally {
        this.groupingInProgress = false;
      }
    },
    addNewGroupAfter(gIdx) {
      const name = prompt('请输入新分组名称');
      if (!name) return;

      this.photoGroups.splice(gIdx + 1, 0, {
        name: name.trim(),
        subgroups: [{
          name: '默认子分组',
          photo_indices: []
        }]
      });
    },
    deleteGroup(groupIndex) {
      const groups = this.photoGroups;
      if (groups.length <= 1) {
        alert('至少需要保留一个阶段');
        return;
      }

      const deletedGroup = groups[groupIndex];
      const deletedPhotos = deletedGroup.subgroups.flatMap(sg => sg.photo_indices);

      if (deletedPhotos.length === 0) {
        // 无照片，直接删除
        groups.splice(groupIndex, 1);
        return;
      }

      let targetGroup = null;
      let targetSubgroupIndex = -1;

      if (groupIndex === 0) {
        // 删除第一个 group → 移至下一个 group 的第一个 subgroup
        targetGroup = groups[1];
        targetSubgroupIndex = 0;
      } else {
        // 删除非第一个 group → 移至上一个 group 的最后一个 subgroup
        targetGroup = groups[groupIndex - 1];
        targetSubgroupIndex = targetGroup.subgroups.length - 1;
      }

      // 将照片合并到目标 subgroup
      if (targetGroup && targetSubgroupIndex >= 0) {
        targetGroup.subgroups[targetSubgroupIndex].photo_indices.push(...deletedPhotos);
        targetGroup.subgroups[targetSubgroupIndex].photo_indices.sort((a, b) => a - b);
      }

      // 执行删除
      groups.splice(groupIndex, 1);
    },
    // 新增子分组：在指定 group 末尾添加一个空子分组
    addSubgroup(gIdx) {
      if (!this.photoGroups[gIdx]) return;
      const newSubgroup = {
        name: '默认子分组',
        photo_indices: []
      };
      this.photoGroups[gIdx].subgroups.push(newSubgroup);
    },

    // 删除子分组：将被删 subgroup 的照片移至同 group 内上一个 subgroup（若存在），否则丢弃（按需求至少保留两个）
    deleteSubgroup(gIdx, sgIdx) {
      const group = this.photoGroups[gIdx];
      if (!group || group.subgroups.length <= 1) {
        alert('每个阶段至少需要保留一个子分组');
        return;
      }

      const deletedSubgroup = group.subgroups[sgIdx];
      const photosToMove = [...deletedSubgroup.photo_indices];

      // 找上一个 subgroup（sgIdx - 1）
      const targetSgIdx = sgIdx > 0 ? sgIdx - 1 : sgIdx + 1; // 通常不会走到 else，因至少有两个
      const targetSubgroup = group.subgroups[targetSgIdx];

      if (targetSubgroup && photosToMove.length > 0) {
        targetSubgroup.photo_indices.push(...photosToMove);
        targetSubgroup.photo_indices.sort((a, b) => a - b);
      }

      // 执行删除
      group.subgroups.splice(sgIdx, 1);
    },
    editGroupName(index) {
      const oldName = this.photoGroups[index].name;
      const newName = prompt('修改分组名称：', oldName);
      if (newName === null || newName.trim() === '') return;
      this.photoGroups[index].name = newName.trim()
    },
    editSubgroupName(gIdx, sgIdx) {
      const group = this.photoGroups[gIdx];
      if (!group || !group.subgroups[sgIdx]) return;

      const oldName = group.subgroups[sgIdx].name;
      const newName = prompt('修改子分组名称：', oldName);
      
      if (newName === null || newName.trim() === '') return; // 用户取消或输入空值
      
      this.photoGroups[gIdx].subgroups[sgIdx].name = newName.trim();
    },
    onPhotoDragStart(event, photoIndex) {
      event.dataTransfer.setData('text/plain', String(photoIndex));
      event.dataTransfer.effectAllowed = 'move';
    },
    onSubgroupDrop(event, gIdx, sgIdx){
      event.preventDefault();

      const photoIndex = parseInt(
        event.dataTransfer.getData('text/plain'),
        10
      );
      if (isNaN(photoIndex)) return;

      // 1. 从所有 subgroup 中移除
      for (const group of this.photoGroups) {
        for (const sg of group.subgroups) {
          const i = sg.photo_indices.indexOf(photoIndex);
          if (i !== -1) {
            sg.photo_indices.splice(i, 1);
          }
        }
      }

      // 2. 添加到目标 subgroup
      const targetSubgroup = this.photoGroups[gIdx].subgroups[sgIdx];
      if (!targetSubgroup.photo_indices.includes(photoIndex)) {
        targetSubgroup.photo_indices.push(photoIndex);
        targetSubgroup.photo_indices.sort((a, b) => a - b);
      }
    },

    async fetchQuestions() {
      if (this.currentStage !== 2) return;
      if (this.photoGroups.length === 0) {
        console.error('photoGroups is empty, abort fetchQuestions');
        return;
      }
      try {
        const groupsPayload = await Promise.all(
          this.photoGroups.map(async (group, gIdx) => ({
            group_id: gIdx,
            name: group.name,
            subgroups: await Promise.all(
              group.subgroups.map(async (sg, sgIdx) => ({
                subgroup_id: sgIdx,
                name: sg.name,
                photo_indices: sg.photo_indices,
                photos: await Promise.all(
                  sg.photo_indices.map(idx =>
                    this.convertToBase64(this.photos[idx].file)
                  )
                )
              }))
            )
          }))
        );

        console.log("📤 Sending to backend:", {
          photoGroups: groupsPayload,
          narratives: this.userNarratives[1]
        });

        const response = await axios.post(
          'http://127.0.0.1:5000/generate-questions',
          {
            photoGroups: groupsPayload,
            narratives: this.userNarratives[1]
          }
        );

        this.questions = response.data.questions || [];
        this.currentQuestionIndex = 0;

        console.log("📥 Questions from backend:", this.questions);

      } catch (err) {
        console.error("Error fetching grouped questions:", err);
      }
    },

    async updateGroupSummary(question) {
      try{
        if (question.type === "intra") {
          await this.updateIntraSubgroupSummary(question)
        } else if (question.type === "inter") {
          await this.updateInterGroupSummary(question)
        }
      } catch (e) {
        console.error('[updateGroupSummary error]', e)
      }
    },
    async updateIntraSubgroupSummary(question) {

      const { group_id, subgroup_id } = question

      const summary = this.subgroupSummaries[group_id]?.[subgroup_id]
      if (!summary || summary.isEditing ) return

      const answeredQs = this.getAnsweredIntraQuestions(group_id, subgroup_id)
      if (!answeredQs.length) {
        console.warn('[DEBUG] No answered questions, skip summarize')
        return
      }

      const payload = {
        group_id: group_id,
        group_title: this.photoGroups[group_id].name,
        subgroup_title: this.photoGroups[group_id].subgroups[subgroup_id].name,
        qa_pairs: answeredQs.map(q => ({
          question: q.text,
          answer: q.answer
        }))
      }

      const res = await axios.post('http://127.0.0.1:5000/summarize-subgroup-memory', payload)

      const current = this.subgroupSummaries[group_id][subgroup_id];
      this.subgroupSummaries[group_id][subgroup_id] = {
        ...current,
        data:{
          ...res.data.summary,
          when: current.data.when // ⭐ 保留用户可编辑的时间
        },
        lastUpdatedBy: 'model'
      }
    },
    async updateInterGroupSummary(question) {
      const { left_group_id, right_group_id } = question
      if (left_group_id == null || right_group_id == null) return

      const key = `${left_group_id}-${right_group_id}`

      const answeredQs = this.questions.filter(q =>
        q.type === "inter" &&
        q.left_group_id === left_group_id &&
        q.right_group_id === right_group_id &&
        q.answered &&
        q.answer.trim()
      )

      if (answeredQs.length === 0) return

      const existing = this.interGroupSummaries[key]
      if (existing?.isEditing || existing?.lastUpdatedBy === 'user') return

      const payload = {
        left_group_title: this.photoGroups[left_group_id].name,
        right_group_title: this.photoGroups[right_group_id].name,
        qa_pairs: answeredQs.map(q => ({
          question: q.text,
          answer: q.answer
        }))
      }

      const res = await axios.post(
        "http://127.0.0.1:5000/summarize-inter-group",
        payload
      )

      this.interGroupSummaries[key] = {
        data: { text: res.data.text },
        isEditing: false,
        editBuffer: null,
        lastUpdatedBy: 'model'
      }

    },
    startEditSubgroupSummary(gIdx, sgIdx) {
      const summary = this.subgroupSummaries[gIdx]?.[sgIdx]
      if (!summary || !summary.data) return

      summary.editBuffer = JSON.parse(JSON.stringify(summary.data))
      summary.isEditing = true
    },
    confirmEditSubgroupSummary(gIdx, sIdx) {
      const summary = this.subgroupSummaries[gIdx]?.[sIdx]
      if (!summary || !summary.editBuffer) return

      summary.data = JSON.parse(JSON.stringify(summary.editBuffer))
      summary.editBuffer = null
      summary.isEditing = false
      summary.lastUpdatedBy = 'user'
    },
    cancelEditSubgroupSummary(gIdx, sIdx) {
      const summary = this.subgroupSummaries[gIdx]?.[sIdx]
      if (!summary) return

      summary.editBuffer = null
      summary.isEditing = false
    },

    startEditInterGroupSummary(leftId, rightId) {
      const key = `${leftId}-${rightId}`
      const summary = this.interGroupSummaries[key]
      if (!summary || !summary.data) return

      summary.editBuffer = JSON.parse(JSON.stringify(summary.data))
      summary.isEditing = true
    },

    confirmEditInterGroupSummary(leftId, rightId) {
      const key = `${leftId}-${rightId}`
      const summary = this.interGroupSummaries[key]

      summary.data = JSON.parse(JSON.stringify(summary.editBuffer))
      summary.editBuffer = null
      summary.isEditing = false
      summary.lastUpdatedBy = 'user'
    },

    cancelEditInterGroupSummary(leftId, rightId) {
      const key = `${leftId}-${rightId}`
      const summary = this.interGroupSummaries[key]

      summary.editBuffer = null
      summary.isEditing = false
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
    // async integrateText() {
    //   if (this.currentStage !== 3) {
    //     alert("整合文本仅在 Stage 3 可用");
    //     return;
    //   }
    //   const narrative = this.userNarratives[2] || '';
    //   const qa_pairs = (this.questions || [])
    //     .filter(q => q.answered && q.answer && q.answer.trim())
    //     .map(q => ({ question: q.text, answer: q.answer.trim() }));
    //   if (!narrative && qa_pairs.length === 0) {
    //     alert("没有可供整合的口述或问答，请先在 Stage2 完成口述与回答。");
    //     return;
    //   }

    //   console.log("准备发往 /integrate-text 的 payload:", { narrative, qa_pairs });

    //   try {
    //     this.integrating = true;
    //     this.assistantIntegratedText = '';
    //     this.assistantUpdatedText = '';
    //     const resp = await axios.post('http://127.0.0.1:5000/integrate-text', {
    //       narrative,
    //       qa_pairs,
    //       options: { output_format: 'text' }
    //     }, { timeout: 120000 });

    //     if (resp.data && resp.data.integrated_text) {
    //       this.assistantIntegratedText = String(resp.data.integrated_text).trim();
    //       this.$message?.success?.("整合完成，已在 AI 面板显示（只读）");
    //     } else {
    //       console.error("integrate-text 返回结构异常：", resp.data);
    //       alert("整合失败，请查看后端日志");
    //     }
    //   } catch (err) {
    //     console.error("整合文本错误：", err);
    //     alert("整合文本时出错，请查看控制台或后端日志");
    //   } finally {
    //     this.integrating = false;
    //   }
    // },
    async integrateText() {
      if (this.currentStage !== 3) {
        alert("整合文本仅在 Stage 3 可用");
        return;
      }

      // 1. 组织 Stage 2 的结构化记忆
      const group_memories = this.groupSummaries || {};
      const subgroup_memories = this.subgroupSummaries || {};
      const inter_group_memories = this.interGroupSummaries || {};

      // 2. 基本校验（替代 narrative / qa 的校验）
      const hasAnyGroup = Object.keys(subgroup_memories).length > 0;
      if (!hasAnyGroup) {
        alert("没有可供整合的阶段记忆，请先在 Stage 2 完成总结。");
        return;
      }

      const payload = {
        group_memories,
        subgroup_memories,
        inter_group_memories,
        options: { output_format: 'text' }
      };

      console.log("准备发往 /integrate-text 的 payload:", payload);

      try {
        this.integrating = true;
        this.assistantIntegratedText = '';
        this.assistantUpdatedText = '';

        const resp = await axios.post(
          'http://127.0.0.1:5000/integrate-text',
          payload,
          { timeout: 120000 }
        );

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

    // ✅ [Priority 1] 拆分 generateImages：第一步，获取 Prompts 并打开确认框
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
        this.pendingBase64Photos = base64Photos; // 暂存，供后续生图使用

        // 2️⃣ 获取 Qwen 生成的 sentence_pairs
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative,
          subgroup_summaries: this.subgroupSummaries
        });
        
        let pairs = response.data.sentence_pairs || [];
        pairs.sort((a, b) => a.index - b.index);
        
        // 过滤出需要生成的 prompt (photo == null 或 匹配分低)
        // 并在界面上显示出来，让用户确认
        this.sentencePairs = pairs; // 保存原始配对信息
        
        // 提取待生成列表 (过滤掉不需要 Prompt 的原图匹配项)
        const toGenerate = pairs.filter(p => p.prompt); 
        
        console.log("将自动生成 Prompts:", toGenerate);
        
        /* // 【原 Prompt 确认流程 - 已注释】
        this.pendingSentencePairs = pairs.filter(p => p.prompt); // 暂存待用户确认的 pairs
        console.log("等待用户确认的 Prompts:", this.pendingSentencePairs);
        this.showPromptModal = true; // 打开确认框
        */

       // 💡 【核心修改】不再自动生成，而是打开确认弹窗供用户查看/修改
      this.pendingSentencePairs = toGenerate; 
      this.showPromptModal = true;

      } catch (error) {
        console.error("Error generating prompts:", error);
        alert("生成 Prompts 时出错，请查看控制台");
      }
    },
    /*
    // ✅ [Priority 1] 用户删除不需要的 Prompt
    removePromptPair(index) {
      this.pendingSentencePairs.splice(index, 1);
    },
    */

    // ✅ [Priority 1] 第二步：用户确认后，真正调用生图
    // 💡 【核心修改】接受 toGenerate 参数，否则使用 this.pendingSentencePairs (兼容Stage4的手动更新)
    async confirmGenerateImages(passedToGenerate) { 
      /* // 【原 Prompt 确认流程 - 已注释】
      this.showPromptModal = false; // 关闭弹窗
      */
      
      const toGenerate = passedToGenerate || this.pendingSentencePairs; 
      if (!toGenerate.length) {
        alert("列表为空，未执行生成");
        return;
      }

      this.aiPhotos = [];
      this.allPhotos = [];

      try {
        // 4️⃣ 构建 payload：取前4张原图作参考
        const payloadToSend = toGenerate.map(item => ({
          index: item.index,
          sentence: item.sentence,
          prompt: item.prompt,
          group_index: item.group_index ?? null,
          subgroup_index: item.subgroup_index ?? null,
          photo: this.pendingBase64Photos.slice(0, 4)
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

        // ✅【核心】5️⃣ 构建 aiMap
        const aiMap = {};
        for (const res of results) {
          const idx = res.index;
          const urls = res.generated_urls || [];
          if (!urls.length) continue; 

          let firstUrl = urls[0];
          let finalUrl = '';
          if (firstUrl.includes('/static/')) {
            if (firstUrl.startsWith('/')) {
              finalUrl = BACKEND_BASE + firstUrl;
            } else if (firstUrl.startsWith('http')) {
              finalUrl = firstUrl;
            } else {
              finalUrl = BACKEND_BASE + '/static/generated/' + firstUrl;
            }
          } else if (firstUrl.startsWith('/')) {
            finalUrl = BACKEND_BASE + firstUrl;
          } else if (firstUrl.startsWith('http')) {
            console.warn('⚠️ 检测到外部 URL（非 /static/），可能无法访问：', firstUrl);
            finalUrl = firstUrl;
          } else if (!firstUrl.startsWith('data:')) {
            finalUrl = BACKEND_BASE + '/static/generated/' + firstUrl;
          } else {
            continue;
          }

          const pair = this.sentencePairs.find(p => p.index === idx);
          const aiObj = {
            file: null,
            url: finalUrl,
            name: `ai_generated_${Date.now()}_${idx}.jpg`,
            prompt: res.prompt || pair?.prompt || null,
            origin_pair_index: idx,
            sentence: pair?.sentence || null,
            group_index: pair?.group_index ?? null,
            subgroup_index: pair?.subgroup_index ?? null,
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
              sentence: pair.sentence,
              group_index: pair.group_index ?? null,
              subgroup_index: pair.subgroup_index ?? null
            });
          } else {
            // fallback：找原图
            let fallbackUrl = null;
            if (pair.origin_pair_index !== undefined && this.photos[pair.origin_pair_index]) {
              fallbackUrl = this.photos[pair.origin_pair_index].url;
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
                sentence: pair.sentence,
                group_index: pair.group_index ?? null,
                subgroup_index: pair.subgroup_index ?? null
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
        console.error("Error confirming images:", error);
        alert("确认生成时出错");
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
      console.log('[Submit] Answering question:', question); // 👈 看这里有没有 group_id

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
        if (question.type === "intra" && question.group_id !== null && question.subgroup_id != null) {
          this.updateGroupSummary(question);
        } else if (
          question.type === "inter" &&
          question.left_group_id != null &&
          question.right_group_id != null
        ) {
          this.updateGroupSummary(question);
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
    getAnsweredIntraQuestions(groupId, subgroupId) {
      if (!this.questions || !Array.isArray(this.questions)) {
        console.warn('[DEBUG] questions not ready');
        return [];
      }

      const result = this.questions.filter(q =>
        q.type === 'intra' &&
        q.group_id === groupId &&
        q.subgroup_id === subgroupId &&
        q.answered === true &&
        q.answer &&
        q.answer.trim().length > 0
      );

      console.log(
        '[DEBUG] answeredQs:',
        `group=${groupId}, subgroup=${subgroupId}`,
        result.map(q => ({
          text: q.text,
          answer: q.answer
        }))
      );

      return result;
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

        // ✅ [Priority 2] 传入当前完整叙事，供后端做上下文推理
        const currentNarrative = this.assistantUpdatedText || this.assistantIntegratedText;

        const response = await axios.post('http://127.0.0.1:5000/generate-stage4-questions', {
          original_photos: base64Photos,
          ai_photos_urls: aiPhotoURLs,
          narrative: currentNarrative, // ✅ 传入
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
        current_narrative: this.assistantUpdatedText || this.assistantIntegratedText,
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
    // === ❗️【核心修复】智能复用逻辑 (Smart Reuse) ❗️ ===
    // ==========================================================
    async generateNewImagesFromNarrative() {
      console.log('S4: 开始智能更新画面 (复用检测)...');
      
      // ✅ 获取最新的全量文本
      const narrative = this.assistantUpdatedText || this.assistantIntegratedText;

      if (!narrative) {
        alert("AI 叙事为空，请先整合文本");
        return;
      }

      try {
        const base64Photos = await Promise.all(
          this.photos.map(photo => this.convertToBase64(photo.file))
        );

        // 1. 获取新故事的分镜 Prompts
        const response = await axios.post('http://127.0.0.1:5000/generate-prompts', {
          photos: base64Photos,
          narrative: narrative,
        });

        const newSentencePairs = response.data.sentence_pairs || [];
        const toGenerate = [];
        const nextRoundAiPhotos = [];
        const BACKEND_BASE = "http://127.0.0.1:5000";

        // 2. 遍历新分镜，尝试复用
        console.log(`[Smart Reuse] 收到 ${newSentencePairs.length} 个新分镜，开始比对...`);

        newSentencePairs.forEach(pair => {
            // Case A: 对应原图 (无需处理，后续构建 allPhotos 会处理)
            if (!pair.prompt) return; 

            // Case B: 需要 AI 生成 -> 尝试在 aiPhotos 中找相似 Prompt
            let bestMatch = null;
            let maxScore = 0;

            for (const oldP of this.aiPhotos) {
                // 跳过无 Prompt 的图
                if (!oldP.prompt) continue;
                
                const score = this.calculateSimilarity(pair.prompt, oldP.prompt);
                if (score > maxScore) {
                    maxScore = score;
                    bestMatch = oldP;
                }
            }

            // 阈值判定: 相似度 > 0.6 视为同一场景，复用图片
            if (maxScore > 0.6 && bestMatch) {
                console.log(`♻️ 复用: 新句[${pair.index}] 与旧句[${bestMatch.origin_pair_index}] 相似度 ${maxScore.toFixed(2)}`);
                nextRoundAiPhotos.push({
                    ...bestMatch, // 继承 URL, file, name
                    index: pair.index, // 更新为新的索引
                    origin_pair_index: pair.index,
                    sentence: pair.sentence, // 更新为新的句子文本
                    prompt: pair.prompt, // 更新为新的 Prompt (以便下轮对比)
                    iterationLabel: bestMatch.iterationLabel + '(Keep)' // 标记复用
                });
            } else {
                console.log(`🆕 新增: 新句[${pair.index}] 无匹配 (MaxScore ${maxScore.toFixed(2)}), 需生成`);
                toGenerate.push(pair);
            }
        });

        // 3. 生成不可复用的新图
        if (toGenerate.length > 0) {
          console.log(`[Smart Reuse] 需新生成 ${toGenerate.length} 张图片...`);

          // 附加参考图
          const payloadToSend = toGenerate.map(item => ({
              ...item,
              photo: base64Photos 
          }));
          
          const genResp = await axios.post('http://127.0.0.1:5000/generate-images', {
            sentence_pairs: payloadToSend
          }, { timeout: 600000 });

          if (genResp.data && genResp.data.results) {
             const results = genResp.data.results;
             
             results.forEach(res => {
                const pairFromAll = toGenerate.find(p => p.index === res.index);
                const urls = res.generated_urls || [];
                if (!urls.length) return;

                let firstUrl = urls[0];
                if (firstUrl.startsWith("/")) {
                  firstUrl = BACKEND_BASE + firstUrl;
                } else if (!firstUrl.startsWith("http")) {
                  firstUrl = BACKEND_BASE + "/static/generated/" + firstUrl;
                }

                nextRoundAiPhotos.push({
                  file: null,
                  url: firstUrl,
                  name: `ai_gen_s4_${Date.now()}_${res.index}.jpg`,
                  prompt: res.prompt,
                  iterationLabel: `Iter ${this.iterationCount + 1}`,
                  sentence: pairFromAll?.sentence || null,
                  origin_pair_index: res.index
                });
             });
          }
        }

        // 4. 更新状态
        this.iterationCount += 1;
        
        // 按 index 排序，保证视觉顺序正确
        nextRoundAiPhotos.sort((a,b) => (a.origin_pair_index || 0) - (b.origin_pair_index || 0));
        
        this.aiPhotos = nextRoundAiPhotos;
        
        // 重新构建 allPhotos (用于视频生成)
        this.allPhotos = [];
        newSentencePairs.forEach(pair => {
            // 找 AI 图
            const aiP = this.aiPhotos.find(p => p.origin_pair_index === pair.index);
            if (aiP) {
                this.allPhotos.push({
                   type: 'ai',
                   sourceIndex: pair.index,
                   url: aiP.url,
                   prompt: aiP.prompt,
                   sentence: aiP.sentence
                });
            } else {
                // 找原图 Fallback
                if (this.photos[pair.index]) {
                   this.allPhotos.push({
                      type: 'original',
                      sourceIndex: pair.index,
                      url: this.photos[pair.index].url,
                      sentence: pair.sentence
                   });
                } else if (this.photos[0]) {
                   this.allPhotos.push({
                      type: 'original',
                      sourceIndex: pair.index,
                      url: this.photos[0].url,
                      sentence: pair.sentence
                   });
                }
            }
        });

        // ✅ 确认文本变更：把 Purple Text 变正文
        this.assistantIntegratedText = narrative;
        this.assistantUpdatedText = ''; 
        this.aiSuggestion = '';
        this.stage4Questions = [];
        this.currentQuestionIndex = 0;

        alert(`画面更新完成！复用了 ${nextRoundAiPhotos.length - toGenerate.length} 张，新生成 ${toGenerate.length} 张。`);

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

        // ✅ 直接使用用户在弹窗中修改后的完整指令
        const newPrompt = suggestion;

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
      this.currentSuggestionText = this.aiPhotos[index].prompt || '';
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
    deleteAiPhoto(idx) {
      // 1. 弹出确认框，防止误删
      if (confirm(`确定要删除这张 AI 生成的照片 ${this.getLetterIndex(idx)} 吗？`)) {
        
        // 获取要删除的照片对象，方便后面在 allPhotos 中比对
        const photoToDelete = this.aiPhotos[idx];

        // 2. 从 aiPhotos 数组中删除 (影响当前页面展示)
        // splice 会从索引 idx 开始删除 1 个元素
        this.aiPhotos.splice(idx, 1);

        // 3. 从 allPhotos 数组中同步删除 (影响 Stage 5 视频生成)
        // 我们过滤掉 url 相同的项，确保生成的视频序列里不再有这张图
        if (this.allPhotos && this.allPhotos.length > 0) {
          this.allPhotos = this.allPhotos.filter(p => p.url !== photoToDelete.url);
        }

        console.log(`已成功删除照片 ${this.getLetterIndex(idx)}，并同步更新了视频序列数据。`);
      }
    },


//-----------------------------Stage5---------------------------------------------

async generateAiVideo() {
    if (this.isGeneratingVideo) return;
    this.isGeneratingVideo = true;
    this.videoGenerationError = null;

    let pollInterval = null;

    try {
        console.log('🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬 [Stage5] 开始生成即梦视频（包含静态和过渡视频）...');

        // ✅ 直接使用原始照片，不管 Stage3/Stage4 是否生成 AI 图片
        let photosToUse = [];
        
        // 如果有 allPhotos（包含 AI 图片），优先使用
        if (this.allPhotos && this.allPhotos.length > 0) {
            photosToUse = this.allPhotos;
            console.log('✅ 使用 Stage3/Stage4 生成的 AI 图片');
        } 
        // 如果没有 AI 图片，直接使用原始照片
        else if (this.photos && this.photos.length > 0) {
            photosToUse = this.photos.map((photo, index) => ({
                type: 'original',
                url: photo.url,
                sentence: `原始照片 ${index + 1}`,
                sourceIndex: index
            }));
            console.log('✅ 直接使用原始照片生成视频');
        } 
        // 没有任何图片
        else {
            throw new Error('没有可用的图片素材，请先上传照片');
        }

        const allPhotosUrls = photosToUse.map(p => p.url).filter(url => url && typeof url === 'string');
        const allSentences = photosToUse.map(p => p.sentence || '');
        const allSourceIndexes = photosToUse.map(p => p.sourceIndex || 0);

        console.log(`[Stage5] 使用 ${allPhotosUrls.length} 张图片生成视频`);

        // ✅ 处理单张图片的情况 - 重复使用同一张图片
        let processedPhotosUrls = [...allPhotosUrls];
        let processedSourceIndexes = [...allSourceIndexes];
        let processedSentences = [...allSentences];
        
        if (allPhotosUrls.length === 1) {
            console.log('⚠️ 只有一张图片，将重复使用以创建视频效果');
            processedPhotosUrls.push(allPhotosUrls[0]);
            processedSourceIndexes.push(allSourceIndexes[0]);
            processedSentences.push(allSentences[0] + '（重复）');
        }

        console.log(`[Stage5] 处理后的图片序列:`, processedPhotosUrls.map((url, i) => 
          `图${i+1}`).join(' -> '));

        // ✅【核心修改】构建视频序列：包括静态视频和过渡视频
        // 格式：AA（静态）, AB（过渡）, BB（静态）, BC（过渡）, CC（静态）...
        const videoSequences = [];
        
        for (let i = 0; i < processedPhotosUrls.length; i++) {
            // 1. 生成静态视频（AA, BB, CC...）
            const staticSequence = {
                type: 'static',
                index: i * 2, // 偶数索引用于静态视频
                photo1: processedPhotosUrls[i],
                photo2: processedPhotosUrls[i], // 同一张照片
                sourceIndex: processedSourceIndexes[i],
                sentence: processedSentences[i] || `图片 ${i + 1}`,
                description: `静态视频 - ${processedSentences[i]}`
            };
            videoSequences.push(staticSequence);
            
            // 2. 生成过渡视频（AB, BC...），除了最后一张照片
            if (i < processedPhotosUrls.length - 1) {
                const transitionSequence = {
                    type: 'transition',
                    index: i * 2 + 1, // 奇数索引用于过渡视频
                    photo1: processedPhotosUrls[i],
                    photo2: processedPhotosUrls[i + 1],
                    sourceIndex1: processedSourceIndexes[i],
                    sourceIndex2: processedSourceIndexes[i + 1],
                    sentence1: processedSentences[i] || `图片 ${i + 1}`,
                    sentence2: processedSentences[i + 1] || `图片 ${i + 2}`,
                    description: `过渡视频 - 从"${processedSentences[i]}"到"${processedSentences[i + 1]}"`
                };
                videoSequences.push(transitionSequence);
            }
        }

        console.log(`[Stage5] 生成 ${videoSequences.length} 个视频序列（${videoSequences.filter(s => s.type === 'static').length}个静态 + ${videoSequences.filter(s => s.type === 'transition').length}个过渡）`);

        // 为每个视频序列动态生成专用prompt
        const jimengPromises = videoSequences.map(async (sequence, seqIndex) => {
            try {
                let promptType = sequence.type;
                let photoPair = [];
                let sentence = '';
                let nextSentence = '';

                if (promptType === 'static') {
                    // 静态视频：使用单张照片，但为了接口一致性传入两张相同的照片
                    photoPair = [sequence.photo1, sequence.photo1];
                    sentence = sequence.sentence;
                    nextSentence = sequence.sentence; // 同一描述
                } else {
                    // 过渡视频：使用两张不同的照片
                    photoPair = [sequence.photo1, sequence.photo2];
                    sentence = sequence.sentence1;
                    nextSentence = sequence.sentence2;
                }

                const response = await axios.post('http://127.0.0.1:5000/refine-prompt', {
                    type: promptType,
                    photo_pair: photoPair,
                    sentence: sentence,
                    next_sentence: nextSentence,
                });

                if (response.data && response.data.prompt) {
                    const dynamicPrompt = response.data.prompt;
                    console.log(`[Stage5] ${promptType}序列 ${seqIndex+1} 动态生成prompt: ${dynamicPrompt}`);
                    return {
                        prompt: dynamicPrompt,
                        photos: promptType === 'static' ? [sequence.photo1] : [sequence.photo1, sequence.photo2],
                        type: promptType
                    };
                } else {
                    throw new Error('未获取到有效的prompt');
                }
            } catch (error) {
                console.error(`${sequence.type}序列 ${seqIndex+1} 生成prompt失败:`, error);
                // 如果动态生成失败，使用简单的默认prompt
                let fallbackPrompt = '';
                if (sequence.type === 'static') {
                    fallbackPrompt = `展示"${sequence.sentence}"的静态画面，带有微妙的光影变化`;
                } else {
                    fallbackPrompt = `从"${sequence.sentence1}"到"${sequence.sentence2}"的平滑过渡效果`;
                }
                console.log(`[Stage5] 使用默认prompt: ${fallbackPrompt}`);
                return {
                    prompt: fallbackPrompt,
                    photos: sequence.type === 'static' ? [sequence.photo1] : [sequence.photo1, sequence.photo2],
                    type: sequence.type
                };
            }
        });

        const jimengResults = await Promise.all(jimengPromises);
        console.log(`[Stage5] 所有动态prompts生成完成`);

        // 准备提交视频生成的数据
        const flatPhotos = [];
        const flatPrompts = [];

        jimengResults.forEach((result, index) => {
            // 对于静态视频，重复使用同一张照片两次
            if (result.type === 'static') {
                flatPhotos.push(result.photos[0], result.photos[0]); // 重复一次
            } else {
                flatPhotos.push(result.photos[0], result.photos[1]);
            }
            flatPrompts.push(result.prompt);
        });

        console.log(`[Stage5] 提交 ${flatPhotos.length} 张照片和 ${flatPrompts.length} 个prompts`);

        const submitResp = await axios.post('http://127.0.0.1:5000/generate-video', {
            photos: flatPhotos, 
            prompts: flatPrompts
        }, {
            timeout: 30000
        });

        if (!submitResp.data.task_id) {
            throw new Error('后端未返回 task_id');
        }

        const taskId = submitResp.data.task_id;
        console.log(`✅ 视频任务已提交，task_id = ${taskId}`);

        // 轮询任务状态
        return new Promise((resolve, reject) => {
            const MAX_POLL = 720; // 最多轮询12分钟
            let pollCount = 0;

            const poll = async () => {
                try {
                    pollCount++;
                    const statusResp = await axios.get(`http://127.0.0.1:5000/video-status/${taskId}`, {
                        timeout: 10000
                    });

                    const { status, videoUrl, error, elapsed, progress } = statusResp.data;

                    if (status === 'success') {
                        clearInterval(pollInterval);
                        this.aiVideo.url = videoUrl;
                        this.$message?.success?.("🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬 视频生成成功！");
                        
                        // 记录到实验日志
                        this.stage5VideoResult = {
                            generatedTime: new Date().toISOString(),
                            videoUrl: videoUrl,
                            photoSource: this.allPhotos.length > 0 ? 'ai_photos' : 'original_photos',
                            photoCount: allPhotosUrls.length,
                            sequenceCount: videoSequences.length,
                            staticCount: videoSequences.filter(s => s.type === 'static').length,
                            transitionCount: videoSequences.filter(s => s.type === 'transition').length,
                            promptType: 'dynamic_with_static'
                        };
                        
                        resolve();
                    } else if (status === 'failed') {
                        clearInterval(pollInterval);
                        const msg = error || '生成失败';
                        this.videoGenerationError = msg;
                        this.$message?.error?.(`视频生成失败：${msg}`);
                        reject(new Error(msg));
                    } else if (pollCount >= MAX_POLL) {
                        clearInterval(pollInterval);
                        const msg = `生成超时（>12分钟，已运行${Math.floor(elapsed || 0)}秒）`;
                        this.videoGenerationError = msg;
                        this.$message?.error?.(msg);
                        reject(new Error(msg));
                    } else {
                        // 显示进度信息
                        if (progress) {
                            console.log(`[Task ${taskId.slice(0,6)}] 进度: ${progress} (${pollCount}s)`);
                        } else {
                            console.log(`[Task ${taskId.slice(0,6)}] 等待中... ${status} (第${pollCount}s)`);
                        }
                    }
                } catch (err) {
                    console.error(`轮询 /video-status/${taskId} 出错:`, err);
                    if (pollCount >= MAX_POLL) {
                        clearInterval(pollInterval);
                        const msg = `轮询超时（${MAX_POLL}次）`;
                        this.videoGenerationError = msg;
                        this.$message?.error?.(msg);
                        reject(new Error(msg));
                    }
                }
            };

            pollInterval = setInterval(poll, 1000);
            poll(); // 立即执行第一次查询
        });

    } catch (err) {
        console.error("[Video Gen Submit Error]", err);
        this.videoGenerationError = err.message || "提交失败";
        this.$message?.error?.(`视频任务提交失败: ${err.message}`);
        throw err;
    } finally {
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
  height: calc(100vh - 72px); /* 顶部 Stage 导航高度 */
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 24px;
  min-height: 0;
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

  display: flex;
  flex-direction: column;

  flex-shrink: 0;     /* 默认不被压缩 */
}



.photo-panel-content,
.narrative-content-wrapper {
  flex: 1;
  min-height: 0;
  overflow: auto;
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
  width: 80px; /* 可调，建议 80-100px */
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 4px;
  background: #f5f6f7;
  position: relative;
  flex-shrink: 0; /* 防止被压缩 */
}

.photo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
}

/* ✅ 优化：鼠标悬停时轻微放大 */
.photo-slot:hover .photo-preview {
  transform: scale(1.05);
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
/* .narrative-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
} */
 /* 叙事文本 */
.narrative-section {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow-y: auto; 
  /* 关键三行 */
  /* flex: 1; */
  /* min-height: 0; */
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 10; /* 确保在其他内容之上 */

  display: flex;
  flex-direction: column;
}


.narrative-content {
  flex: 1;
  min-height: 0;
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
  flex: 1; 
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
  min-height: 120px; 
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

/* 分组结果整体容器 */
.group-section {
  overflow-y: auto;      
  flex-shrink: 0;          
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  margin-top: 16px;
}

/* Stage 2：分组结果撑满左侧 */
.stage-2 .group-section {
  max-height: none;     /* ✅ 解除上限 */
  flex: 1;              /* ✅ 吃掉剩余空间 */
  flex-shrink: 1;
  overflow-y: auto;
}


/* 单个分组块 */
.group-block {
  border: 1px dashed #c3c9e8; /* 同主色调的浅紫色虚线 */
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 16px;
  background: #fafbfc; /* 浅灰蓝背景 */
}

.group-title {
  font-size: 14px;
  font-weight: 600;
  color: #7c83b9;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #f0f2f8;
  border-radius: 4px;
  display: inline-block;
}

.group-summary {
  margin-top: 10px;
  padding: 8px 10px;
  background: #fafafa;
  border-left: 3px solid #667eea;
  border-radius: 4px;
  font-size: 13px;
  color: #333;
}

.summary-item {
  margin-bottom: 4px;
  line-height: 1.4;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.summary-actions {
  display: flex;
  gap: 6px;
}

.summary-edit-item {
  display: flex;
  flex-direction: column;
  margin-bottom: 6px;
}

.summary-edit-item input,
.summary-edit-item textarea {
  font-size: 13px;
  padding: 4px 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.inter-group-block {
  margin: 12px 0 20px;
  padding: 10px 14px;
  background: #f6f7fb;
  border-left: 3px dashed #7c83b9;
  border-radius: 6px;
  font-size: 13px;
}

.inter-header {
  font-weight: 600;
  color: #5b61a6;
  margin-bottom: 6px;
}

.inter-question {
  margin-top: 6px;
}

.inter-question-text {
  color: #333;
}

.inter-question-answer {
  margin-top: 2px;
  padding-left: 8px;
  color: #666;
  font-style: italic;
}

/* 阶段过渡编辑框 */
.inter-edit-textarea {
  width: 100%;
  min-height: 80px;          /* ✅ 核心 */
  resize: vertical;         /* 允许用户拉高 */
  font-size: 13px;
  line-height: 1.6;
  padding: 8px 10px;
  border: 1px solid #c3c9e8;
  border-radius: 6px;
  background: #ffffff;
  box-sizing: border-box;
}

/* 编辑态操作区 */
.inter-edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}

/* 编辑态按钮统一尺寸 */
.inter-edit-actions button {
  min-width: 64px;
  height: 30px;
  padding: 0 12px;
  font-size: 12px;
  border-radius: 4px;

  background: #fff;
  border: 1px solid #c3c9e8;   /* ✅ 细主题色边框 */
  color: #5b61a6;

  cursor: pointer;
  transition: all 0.2s;
}

.narrative-section.collapsed,
.photo-panel.collapsed {
  flex: 0 0 auto;
  max-height: 64px;   /* 只留 header */
  padding-bottom: 0;
  overflow: hidden;
}

/* ===== Timeline Base ===== */
.timeline-wrapper {
  width: 100%;
  overflow-x: auto;
}

.timeline.horizontal {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  gap: 24px;
}

.timeline.vertical {
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: 16px;
}

/* ===== Group Node (Horizontal) ===== */
.timeline-node {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.group-card {
  background: #fff;
  border: 2px solid #ddd;
  border-radius: 8px;
  padding: 12px;
  min-width: 220px;
}


.group-title.editable {
  cursor: pointer;
}

/* ===== Subgroups ===== */
.subgroup-list,
.subgroup-list-vertical {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.subgroup-box {
  border: 2px dashed #bbb;
  border-radius: 6px;
  padding: 8px;
  background: #fafafa;
}

.subgroup-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: #746fc5; 
}

.subgroup-title.editable {
  cursor: pointer;
}


/* ===== Buttons ===== */
.insert-group-btn {
  height: 32px;
  width: 32px;
  border-radius: 50%;
  border: none;
  background: #e0e0e0;
  cursor: pointer;
}

.group-actions {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.danger-btn {
  background: #e57373;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
}

.danger-btn.small {
  font-size: 12px;
}

/* ===== Vertical Timeline ===== */
.timeline-node-vertical {
  position: relative;
  padding-left: 24px;
  border-left: 2px solid #ccc;
}

.group-node-vertical {
  margin-bottom: 12px;
}

.subgroup-summary {
  font-size: 13px;
  color: #444;
  margin-bottom: 6px;
}

/* ===== Inter Group ===== */
.inter-group-block {
  margin-top: 12px;
  padding: 8px;
  background: #f3f3f3;
  border-left: 4px solid #999;
}

</style>