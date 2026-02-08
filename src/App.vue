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
        
        <!-- Stage 1: 照片上传和分组 -->
        <div v-if="currentStage === 1" class="stage1-layout">
          <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
            <div class="panel-header">
              <h2>📷 照片面板</h2>
              <!-- 在照片面板的panel-controls中添加角色识别按钮 -->
              <div class="panel-controls">
                <input 
                  type="file" 
                  ref="fileInput"
                  multiple
                  accept="image/*"
                  @change="handleFileChange"
                  style="display: none;"
                />
                <button class="control-btn" @click="addPhoto">➕ 添加照片</button>
                <button class="control-btn" @click="confirmUpload">确认上传图片</button>

                <!-- 新增角色识别按钮 -->
                <button 
                  class="control-btn" 
                  @click="identifyCharacters" 
                  :disabled="photos.length === 0 || isAnalyzingCharacters"
                  style="background: #f0f2f8; border-color: #7c83b9; color: #7c83b9;"
                >
                  {{ isAnalyzingCharacters ? '正在识别...' : '👤角色识别' }}
                </button>

                <button class="control-btn" @click="groupPhotosByTime" :disabled="photos.length === 0 || groupingInProgress">
                  {{ groupingInProgress ? '分组中…' : '照片分组' }}
                </button>
              </div>
            </div>
            
            <!-- 照片网格 -->
            <div class="photo-grid">
              <div class="photo-slot" v-for="(photo, index) in photos" :key="index">
                <div class="photo-placeholder" 
                    draggable="true" 
                    @dragstart="onPhotoDragStart($event, index)"  
                    @click="triggerFileInput(index)">
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

            <!-- 分组结果展示 -->
            <div v-if="showGroups" class="group-section">
              <h3 style="margin: 16px 0; font-size:15px; color:#333;">🕒 照片分组结果</h3>
              <div v-for="(group, gIdx) in photoGroups" :key="gIdx">
                <div class="group-block" @dragover="onGroupDragOver" @drop="onGroupDrop($event, gIdx)">
                  <div
                    class="group-title"
                    :style="{ cursor: 'pointer' }"
                    @click="editGroupName(gIdx)"
                    title="点击修改标题"
                  >
                    {{ group.name }}
                  </div>

                  <div class="photo-grid">
                    <div class="photo-slot" v-for="idx in group.photo_indices" :key="idx">
                      <div class="photo-placeholder" draggable="true" @dragstart="onPhotoDragStart($event, idx)">
                        <img v-if="photos[idx]?.url" :src="photos[idx].url" class="photo-preview" />
                        <span v-else class="photo-number">{{ idx + 1 }}</span>
                      </div>
                    </div>
                  </div>
                  <button class="control-btn" @click="addNewGroupAfter(gIdx)"> ➕ 在此分组后新建</button>
                  <button class="control-btn danger" @click="deleteGroup(gIdx)">  🗑 删除分组</button>
                </div>
              </div>
            </div>
          </div>

          <div class="resize-handle" @mousedown="startResize" :class="{ 'resizing': isResizing }">
            <div class="handle-line"></div>
          </div>

          <div class="narrative-section" :style="{ flex: 1 }">
            <div class="panel-header">
              <h3>📝 用户口述</h3>
              <div class="panel-controls">
                <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
                <button class="control-btn" @click="reselectText">🔄 重新口述</button>
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
        </div>

        <!-- Stage 2: 记忆总结和问答 -->
        <div v-if="currentStage === 2" class="stage2-layout">
          <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
            <div class="panel-header">
              <h2>📷 照片面板</h2>
            </div>
            
            <!-- 分组结果展示 -->
            <div class="group-section">
              <h3 style="margin: 16px 0; font-size:15px; color:#333;">🕒 照片分组结果</h3>
              <div v-for="(group, gIdx) in photoGroups" :key="gIdx">
                <div class="group-block">
                  <div class="group-title">
                    {{ group.name }}
                  </div>

                  <!-- 五维记忆总结 -->
                  <div
                    v-if="groupSummaries[gIdx]"
                    class="group-summary"
                  >
                    <div class="summary-header">
                      <strong>🧠 记忆总结</strong>
                      <div class="summary-actions">
                        <button
                          v-if="!groupSummaries[gIdx].isEditing"
                          class="control-btn"
                          @click="startEditGroupSummary(gIdx)"
                        >
                          修改
                        </button>
                        <template v-else>
                          <div class="inter-edit-actions">
                            <button @click="confirmEditGroupSummary(gIdx)"> 确认 </button>
                            <button @click="cancelEditGroupSummary(gIdx)"> 取消 </button>
                          </div>
                        </template>
                      </div>
                    </div>
                    <div v-if="!groupSummaries[gIdx].isEditing">
                      <div class="summary-item"><strong> 人物：</strong>{{ groupSummaries[gIdx].data.who || '—' }}</div>
                      <div class="summary-item"><strong> 时间：</strong>{{ groupSummaries[gIdx].data.when || '—' }}</div>
                      <div class="summary-item"><strong> 地点：</strong>{{ groupSummaries[gIdx].data.where || '—' }}</div>
                      <div class="summary-item"><strong> 事件：</strong>{{ groupSummaries[gIdx].data.what || '—' }}</div>
                      <div class="summary-item"><strong> 情感：</strong>{{ groupSummaries[gIdx].data.emotion || '—' }}</div>
                    </div>
                
                    <div v-else class="summary-edit">
                      <div class="summary-edit-item">
                        <label>👤 人物</label>
                        <input v-model="groupSummaries[gIdx].editBuffer.who" />
                      </div>
                      <div class="summary-edit-item">
                        <label>⏰ 时间</label>
                        <input v-model="groupSummaries[gIdx].editBuffer.when" />
                      </div>
                      <div class="summary-edit-item">
                        <label>📍 地点</label>
                        <input v-model="groupSummaries[gIdx].editBuffer.where" />
                      </div>
                      <div class="summary-edit-item">
                        <label>📖 事件</label>
                        <textarea v-model="groupSummaries[gIdx].editBuffer.what" rows="2" />
                      </div>
                      <div class="summary-edit-item">
                        <label>💗 情感</label>
                        <input v-model="groupSummaries[gIdx].editBuffer.emotion" />
                      </div>
                    </div>
                  </div>

                  <div class="photo-grid">
                    <div class="photo-slot" v-for="idx in group.photo_indices" :key="idx">
                      <div class="photo-placeholder">
                        <img v-if="photos[idx]?.url" :src="photos[idx].url" class="photo-preview" />
                        <span v-else class="photo-number">{{ idx + 1 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 组间过渡 -->
                <div
                  v-if="interGroupSummaries[`${gIdx}-${gIdx + 1}`]"
                  class="inter-group-block"
                >
                  <div class="inter-header">
                    <strong>⏳ 阶段过渡</strong>
                    <div class="summary-actions">
                      <button
                        v-if="!interGroupSummaries[`${gIdx}-${gIdx + 1}`].isEditing"
                        class="control-btn"
                        @click="startEditInterGroupSummary(gIdx, gIdx + 1)"
                      >
                        修改
                      </button>
                      <template v-else>
                        <div class="inter-edit-actions">  
                          <button @click="confirmEditInterGroupSummary(gIdx, gIdx + 1)"> 确认 </button>
                          <button @click="cancelEditInterGroupSummary(gIdx, gIdx + 1)"> 取消 </button>
                        </div>
                      </template>
                    </div>
                  </div>

                  <div
                    v-if="!interGroupSummaries[`${gIdx}-${gIdx + 1}`].isEditing"
                    class="inter-summary-text"
                  >
                    {{ interGroupSummaries[`${gIdx}-${gIdx + 1}`].data.text || '—' }}
                  </div>

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

          <div class="narrative-section" :style="{ flex: 1 }">
            <div class="panel-header">
              <h3>📝 用户口述</h3>
              <div class="panel-controls">
                <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
                <button class="control-btn" @click="reselectText">🔄 重新口述</button>
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
        </div>

        <!-- Stage 3: AI图像生成 -->
        <div v-if="currentStage === 3" class="stage3-layout">
          <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
            <div class="split-container">
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
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="resize-handle" @mousedown="startResize" :class="{ 'resizing': isResizing }">
            <div class="handle-line"></div>
          </div>

          <div class="narrative-section" :style="{ flex: 1 }">
            <div class="panel-header">
              <h3>📝 用户口述</h3>
              <div class="panel-controls">
                <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
                <button class="control-btn" @click="reselectText">🔄 重新口述</button>
                <button class="control-btn" @click="generateImages">图像补全</button>
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
        </div>

        <!-- Stage 4: 迭代优化 -->
        <div v-if="currentStage === 4" class="stage4-layout">
          <div class="photo-panel" :style="{ height: photoPanelHeight + 'px' }">
            <div class="split-container">
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
          </div>

          <div class="resize-handle" @mousedown="startResize" :class="{ 'resizing': isResizing }">
            <div class="handle-line"></div>
          </div>

          <div class="narrative-section" :style="{ flex: 1 }">
            <div class="panel-header">
              <h3>📝 用户口述</h3>
              <div class="panel-controls">
                <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
                <button class="control-btn" @click="reselectText">🔄 重新口述</button>
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
        </div>

        <!-- Stage 5: 视频生成 -->
        <div v-if="currentStage === 5" class="stage5-layout">
          <!-- 照片和视频区域 -->
          <div class="stage5-content-section" :style="{ height: stage5PhotoHeight + 'px' }">
            <!-- 原照片集区域 -->
            <div class="stage5-section original-photos-section">
              <div class="section-title">🎞️ 原照片集</div>
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
            

            <!-- 在Stage5布局中找到视频播放器部分，修改为： -->
            <div class="stage5-section video-section">
              <div class="section-title">🎬🎬 AI 增强视频</div>
              <div class="video-controls">
                <button class="control-btn primary" @click="generateAiVideo" :disabled="isGeneratingVideo">
                  {{ isGeneratingVideo ? '视频生成中…' : '生成最终视频' }}
                </button>
                <span v-if="isGeneratingVideo" style="margin-left: 10px; color: #666; font-size: 12px;">
                </span>
                <span v-if="videoGenerationError" class="error-message">
                  {{ videoGenerationError }}
                </span>
              </div>
              
              <!-- 修改这里：添加居中容器 -->
              <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin-top: 20px;">
                <div class="video-slot" style="display: flex; justify-content: center; align-items: center;">
                  <video 
                    v-if="aiVideo.url" 
                    :src="aiVideo.url" 
                    controls 
                    class="video-player"
                    style="max-width: 100%; max-height: 300px; width: auto; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"
                  >
                  </video>
                  <div v-else class="video-placeholder" style="width: 100%; height: 200px; display: flex; align-items: center; justify-content: center; background: #f5f5f5; border-radius: 8px;">
                    <span style="color: #999;">视频生成后将显示在这里</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Stage5的resize-handle，用于调整照片面板和用户口述的高度 -->
          <div 
            class="resize-handle" 
            @mousedown="startResizeStage5"
            :class="{ 'resizing': isResizingStage5 }">
            <div class="handle-line"></div>
          </div>

          <!-- Stage5的用户口述部分 -->
            <div class="narrative-section" :style="{ 
            flex: 1, 
            backgroundColor: '#ffffff', // 添加白色背景确保不透明
            position: 'relative',
            zIndex: 10 // 确保在其他内容之上
          }">
            <div class="panel-header">
              <h3>📝 用户口述</h3>
              <div class="panel-controls">
                <button class="control-btn" @click="calculateMemoryMetrics">保存文本</button>
                <button class="control-btn" @click="reselectText">🔄 重新口述</button>
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
        </div>
      </section>



      <!-- AI助手侧边栏 -->
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
            <div class="handle-line"></div>
          </div>
        </div>

        <div v-if="currentStage === 4" class="ai-modify-section" style="margin:10px 0; text-align:center; padding: 0 20px;"> 
          <button 
            class="control-btn" 
            @click="fetchStage4Questions" 
            :disabled="isFetchingS4Questions || iterationStopped" style="width: 100%; margin-bottom: 10px;"
          >
            {{ isFetchingS4Questions ? '获取中...' : '获取新一轮提问' }}
          </button>
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
          v-if="currentStage === 3 || (currentStage === 4 && stage4Questions.length > 0 && answeredCount > 0)" 
          class="control-btn primary"
          :disabled="integrating || isUpdatingText || iterationStopped" 
          @click="currentStage === 3 ? integrateText() : updateText()">
          {{ integrating ? '整合中...' : (isUpdatingText ? '更新中...' : (currentStage === 3 ? '整合文本' : '整合文本')) }}
        </button>
      </aside>
      
      <!-- 在照片面板代码后面添加角色面板 -->
      <aside class="character-sidebar" :class="{ collapsed: isCharacterPanelCollapsed }" style="width: 300px; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06); display: flex; flex-direction: column; flex-shrink: 0;">
        <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
          <h3 style="font-size: 16px; color: #333;">👥角色面板</h3>
          <button class="control-btn" @click="isCharacterPanelCollapsed = !isCharacterPanelCollapsed">
            {{ isCharacterPanelCollapsed ? '展开' : '收起' }}
          </button>
        </div>
        
        <div v-show="!isCharacterPanelCollapsed" class="character-content" style="flex: 1; overflow-y: auto;">
          <!-- 修改角色列表项，添加头像显示 -->
          <div class="character-list">
            <div 
              v-for="char in characters" 
              :key="char.id" 
              @click="selectedCharacterId = char.id"
              style="display: flex; align-items: center; gap: 12px; padding: 10px; border: 1px solid #eee; border-radius: 8px; margin-bottom: 10px; cursor: pointer;"
              :style="selectedCharacterId === char.id ? 'border-color: #7c83b9; background: #f0f2f8;' : ''"
            >
              <!-- 修复1：将 activeCharacter.avatar 改为 char.avatar（循环项是char不是activeCharacter） -->
              <!-- 修复2：添加 img 的 error 事件，加载失败时显示占位符 -->
              <div v-if="char.avatar" class="character-avatar-large" style="width: 120px; height: 160px; border-radius: 12px; overflow: hidden; margin: 0 auto; border: 3px solid #7c83b9;">
                <img 
                  :src="char.avatar" 
                  style="width: 100%; height: 100%; object-fit: cover;" 
                  alt="角色头像"
                  @error="() => { char.avatar = '' }"  
                />
              </div>
              <div v-else class="character-avatar-large-placeholder" style="width: 120px; height: 160px; border-radius: 12px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; margin: 0 auto; border: 3px solid #7c83b9;">
                <span style="font-size: 24px;">👤</span>
              </div>
              
              <div style="flex: 1; min-width: 0;">
                <strong style="font-size: 14px; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                  {{ char.name || '未命名' }}
                </strong>
                
                <span 
                  v-if="shouldShowTag(char)"
                  style="font-size: 11px; background: #e8ebf7; color: #7c83b9; padding: 2px 8px; border-radius: 10px; margin-top: 4px; display: inline-block;"
                >
                  {{ char.relationType === '其他' ? char.customRelation : char.relationType }}
                </span>
              </div>
              <span v-if="char.isMain" style="font-size: 16px;">⭐</span>
            </div>
          </div>

          <div v-if="activeCharacter" style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #eee;">
            
            <!-- 添加角色头像显示 -->
            <div style="text-align: center; margin-bottom: 15px;">
              <div v-if="activeCharacter.avatar" class="character-avatar-large" style="width: 80px; height: 80px; border-radius: 50%; overflow: hidden; margin: 0 auto;">
                <img :src="activeCharacter.avatar" style="width: 100%; height: 100%; object-fit: cover;" alt="角色大头像" />
              </div>
              <div v-else class="character-avatar-large-placeholder" style="width: 80px; height: 80px; border-radius: 50%; background: #f0f0f0; display: flex; align-items: center; justify-content: center; margin: 0 auto;">
                <span style="font-size: 24px;">👤</span>
              </div>
            </div>
            
            <div style="margin-bottom: 12px;">
              <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">人物</label>
              <input v-model="activeCharacter.name" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" />
            </div>

            <div style="margin-bottom: 12px;">
              <label style="font-size: 12px; color: #666; display: block; margin-bottom: 4px;">与主角关系</label>
              <select v-model="activeCharacter.relationType" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 8px;">
                <option value="" disabled>-- 请选择关系 --</option>
                <option value="自己">自己</option>
                <option value="家人">家人</option>
                <option value="朋友">朋友</option>
                <option value="同事">同事</option>
                <option value="其他">其他...</option>
              </select>
              
              <input 
                v-if="activeCharacter.relationType === '其他'" 
                v-model="activeCharacter.customRelation" 
                placeholder="请填写具体关系" 
                style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px;" 
              />
            </div>

            <label style="font-size: 13px; display: flex; align-items: center; gap: 8px; cursor: pointer; color: #333;">
              <input type="checkbox" v-model="activeCharacter.isMain" /> 设定为故事主角
            </label>
          </div>
        </div>
      </aside>
    </div>


    
    <!-- 裁剪模态框 -->
    <div v-show="showCropperModal" class="cropper-modal-backdrop">
      <div class="cropper-modal">
        <div class="cropper-header">
          <h3>🖼️ 选择人物主体</h3>
          <button class="close-btn" @click="closeCropper">×</button>
        </div>
        
        <div class="cropper-content">
          <img 
            ref="cropperImage" 
            :src="selectedPhotoForCropping" 
            alt="待裁剪图片" 
            @load="onCropperImageLoad"
            @error="onCropperImageError"
          />
        </div>
        
        <div class="cropper-actions">
          <button class="control-btn" @click="closeCropper">取消</button>
          <button class="control-btn primary" @click="confirmCrop">确认裁剪</button>
        </div>
      </div>
    </div>

    <!-- 建议模态框 -->
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

    <!-- Prompt确认模态框 -->
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
      

      // === 新增角色相关数据 ===
      characters: [], // 角色列表
      selectedCharacterId: null, // 当前选中的角色ID
      isCharacterPanelCollapsed: false, // 角色面板是否折叠
      isAnalyzingCharacters: false, // 是否正在识别人物

      // === 原有状态 ===
      currentStage: 1,
      pendingSentencePairs: [], // 暂存待用户确认的 pairs
      pendingBase64Photos: [], // 暂存原始图片 base64，供生图使用
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
      groupSummaries: {},
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
      photoGroups: [], // 保存分组结果 [{ name: '...', photoIndices: [...] }]
      showGroups: false,  
      groupingInProgress: false,
      // 视频生成状态
      isGeneratingVideo: false,
      videoGenerationError: null,
      // stage 3&4 整合文本用户修改功能
      assistantEditMode: false,        // 是否处于编辑模式（显示 textarea）
      assistantEditBuffer: '',        // 编辑缓冲文本（textarea 的 v-model）
      assistantEditedByUser: false,   // 标记用户是否已手动编辑过 AI 文本
      stage3Modifications: [],        // 记录 Stage3 的每次用户修改（timestamp, before, after）
      
      highlightedSentence: null, // ✅ [修改 C.2] 新增高亮状态

      // 新增Stage5专用高度状态
      stage5PhotoHeight: 300,
      isResizingStage5: false,
      startYStage5: 0,
      startHeightStage5: 0,
      showPromptModal: false,

      
    }
  },
  computed: {

    activeCharacter() {
      return this.characters.find(c => c.id === this.selectedCharacterId);
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
        * 1️⃣ 组内（groupSummaries）初始化
        * =============================== */
        if (!this.groupSummaries || typeof this.groupSummaries !== 'object') {
          this.groupSummaries = {};
        }

        this.photoGroups.forEach((g, gIdx) => {
          if (!this.groupSummaries[gIdx]) {
            this.groupSummaries[gIdx] = {
              data: {
                who: "",
                when: "",
                where: "",
                what: "",
                emotion: ""
              },
              editBuffer: {
                who: "",
                when: "",
                where: "",
                what: "",
                emotion: ""
              },
              isEditing: false,
              lastUpdatedBy: 'init'
            };
          }
        });

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
          this.photoGroups = resp.data.groups;
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
        photo_indices: []
      });
    },
    deleteGroup(groupIndex) {
      const groups = this.photoGroups;

      if (groups.length === 1) {
        alert("至少需要保留一个分组");
        return;
      }

      const deletedGroup = groups[groupIndex];

      const targetIndex = groupIndex > 0
        ? groupIndex - 1
        : groupIndex + 1;

      const targetGroup = groups[targetIndex];

      // 合并照片
      targetGroup.photo_indices = [
        ...targetGroup.photo_indices,
        ...deletedGroup.photo_indices
      ];

      // 排序（可选）
      targetGroup.photo_indices.sort((a, b) => a - b);

      // 删除分组
      groups.splice(groupIndex, 1);
    },
    editGroupName(index) {
      const oldName = this.photoGroups[index].name;
      const newName = prompt('修改分组名称：', oldName);
      if (newName === null || newName.trim() === '') return;
      this.photoGroups[index].name = newName.trim()
    },
    onPhotoDragStart(event, photoIndex) {
      event.dataTransfer.setData('text/plain', String(photoIndex));
      event.dataTransfer.effectAllowed = 'move';
    },
    onGroupDrop(event, targetGroupIndex) {
      event.preventDefault();
      const photoIndexStr = event.dataTransfer.getData('text/plain');
      const photoIndex = parseInt(photoIndexStr, 10);
      if (isNaN(photoIndex)) return;

      const targetGroup = this.photoGroups[targetGroupIndex];

      // 如果已在该组，不重复添加
      if (targetGroup.photo_indices.includes(photoIndex)) return;

      // 从原分组移除（如果存在）
      for (const group of this.photoGroups) {
        const i = group.photo_indices.indexOf(photoIndex);
        if (i !== -1) {
          group.photo_indices.splice(i, 1);
          break;
        }
      }

      // 添加到目标分组
      targetGroup.photo_indices.push(photoIndex);
    },
    onGroupDragOver(event) {
      event.preventDefault(); // 必须！否则 drop 不会触发
      event.dataTransfer.dropEffect = 'move';
    },

    async fetchQuestions() {
      if (this.currentStage !== 2) return;
      if (this.photoGroups.length === 0) {
        console.error('photoGroups is empty, abort fetchQuestions');
        return;
      }
      try {
        const groupsPayload = await Promise.all(
          this.photoGroups.map(async (group, groupIdx) => {
            const groupPhotos = await Promise.all(
              group.photo_indices.map(idx =>
                this.convertToBase64(this.photos[idx].file)
              )
            );

            return {
              group_id: groupIdx,
              name: group.name,
              photo_indices: group.photo_indices,
              photos: groupPhotos
            };
          })
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
      if (question.type === "intra") {
        await this.updateIntraGroupSummary(question)
      } else if (question.type === "inter") {
        await this.updateInterGroupSummary(question)
      }
    },
    async updateIntraGroupSummary(question) {
      const groupId = question.group_id
      if (!this.photoGroups[groupId]) return

      const answeredQs = this.getAnsweredIntraQuestionsByGroup(groupId)
      if (answeredQs.length === 0) return

      // 用户正在编辑 or 已人工修改，跳过自动更新
      const existing = this.groupSummaries[groupId]
      if (existing?.isEditing || existing?.lastUpdatedBy === 'user') {
        console.log(`⛔ Skip auto-summary for group ${groupId}, user-edited`)
        return
      }

      const payload = {
        group_id: groupId,
        group_title: this.photoGroups[groupId].name,
        qa_pairs: answeredQs.map(q => ({
          question: q.text,
          answer: q.answer
        }))
      }

      const res = await axios.post(
        "http://127.0.0.1:5000/summarize-group-memory",
        payload
      )
      
      this.groupSummaries[groupId] = {
        data: res.data.summary,
        isEditing: false,
        editBuffer: null,
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
    startEditGroupSummary(groupId) {
      const summary = this.groupSummaries[groupId]
      if (!summary || !summary.data) return

      summary.editBuffer = JSON.parse(JSON.stringify(summary.data))
      summary.isEditing = true
    },

    confirmEditGroupSummary(groupId) {
      const summary = this.groupSummaries[groupId]
      summary.data = JSON.parse(JSON.stringify(summary.editBuffer))
      summary.editBuffer = null
      summary.isEditing = false
      summary.lastUpdatedBy = "user"
    },

    cancelEditGroupSummary(groupId) {
      const summary = this.groupSummaries[groupId]
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

    shouldShowTag(char) {
      // 1. 如果没选关系，不显示
      if (!char.relationType) return false;
      // 2. 如果选了"其他"，但还没填具体内容，不显示
      if (char.relationType === '其他' && !char.customRelation) return false;
      // 3. 其他情况（选了自己、家人等）正常显示
      return true;
    },

    // 角色识别方法
    async identifyCharacters() {
      if (this.photos.length === 0) {
        alert("请先添加并确认上传图片！");
        return;
      }
      
      this.isAnalyzingCharacters = true;
      
      try {
        // 使用 confirmUpload 相同的逻辑
        const photoInfos = await Promise.all(
          this.photos.map(async (p, index) => {
            if (!p.file) {
              console.error(`图片 ${index} 没有文件对象`);
              return null;
            }
            
            const base64 = await this.convertToBase64(p.file);
            return {
              url: p.url,
              index: index,
              base64: base64
            };
          })
        );
        
        const validPhotoInfos = photoInfos.filter(info => info !== null);
        
        if (validPhotoInfos.length === 0) {
          alert("没有有效的图片可以处理");
          return;
        }
        
        const resp = await axios.post('http://127.0.0.1:5000/analyze-characters', {
          photos: validPhotoInfos
        });
        
        if (resp.data.characters) {
          this.characters = resp.data.characters.map(char => ({
            ...char,
            relationType: char.relationType || "",
            customRelation: char.customRelation || "",
            photoIndex: char.photoIndex || 0,
            photoUrl: char.photoUrl || this.photos[char.photoIndex || 0]?.url || "",
            aiPhotoUrls: char.aiPhotoUrls || []
          }));
          
          if (this.characters.length > 0) {
            this.selectedCharacterId = this.characters[0].id;
          }
          alert(`识别完成！共发现 ${this.characters.length} 处人物面部。`);
        } else {
          alert("未能识别到清晰的人物面部。");
        }
      } catch (err) {
        console.error("角色分析失败:", err);
        alert("识别服务连接失败，请检查后端运行状态。");
      } finally {
        this.isAnalyzingCharacters = false;
      }
    },

  async confirmUpload() {
    // 1. 检查是否有图片
    if (this.photos.length === 0) {
      alert("请先添加图片！");
      return;
    }
    
    console.log("正在启动 AI 人物识别与聚类...");
    
    try {
      // 2. 使用 Promise.all 并行处理所有图片的 base64 转换
      const photoInfos = await Promise.all(
        this.photos.map(async (p, index) => {
          // 确保文件存在
          if (!p.file) {
            console.error(`图片 ${index} 没有文件对象`);
            return null;
          }
          
          const base64 = await this.convertToBase64(p.file);
          return {
            url: p.url,
            index: index,
            base64: base64
          };
        })
      );
      
      // 过滤掉无效的图片
      const validPhotoInfos = photoInfos.filter(info => info !== null);
      
      if (validPhotoInfos.length === 0) {
        alert("没有有效的图片可以处理");
        return;
      }
      
      console.log(`准备发送 ${validPhotoInfos.length} 张图片进行人脸识别`);
      
      // 3. 调用后端 analyze-characters 接口
      const resp = await axios.post('http://127.0.0.1:5000/analyze-characters', {
        photos: validPhotoInfos
      });
      
      // 4. 将识别结果注入角色面板
      if (resp.data.characters) {
        this.characters = resp.data.characters.map(char => ({
          ...char,
          relationType: char.relationType || "",
          customRelation: char.customRelation || "",
          photoIndex: char.photoIndex || 0,
          photoUrl: char.photoUrl || this.photos[char.photoIndex || 0]?.url || "",
          aiPhotoUrls: char.aiPhotoUrls || []
        }));
        
        if (this.characters.length > 0) {
          this.selectedCharacterId = this.characters[0].id;
        }
        alert(`人物识别完成！共发现 ${this.characters.length} 个角色。`);
      } else {
        alert("未能识别到清晰的人物面部。");
      }
    } catch (err) {
      console.error("角色分析请求失败:", err);
      alert("人物识别服务异常，请检查后端 Python 终端报错信息。");
    }
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
      const newHeight = this.startHeight + diff;
      // 移除最小200px和最大500px的限制，只保留非负检查
      if (newHeight < 0) {
        this.photoPanelHeight = 0;
      } else {
        this.photoPanelHeight = newHeight;
      }
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
          ...item,
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
        if (question.type === "intra" && question.group_id !== null) {
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
    getAnsweredIntraQuestionsByGroup(groupId) {
      return this.questions.filter(q =>
        q.type === "intra" &&
        q.group_id === groupId &&
        q.answered &&
        q.answer.trim() !== ""
      )
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
        // ========== 新增：AI照片与角色绑定 ==========
        this.aiPhotos.forEach((aiPhoto, aiIndex) => {
          // 根据AI照片的原始索引，找到对应的角色
          const relatedChar = this.characters.find(char => char.photoIndex === aiPhoto.origin_pair_index);
          if (relatedChar) {
            // 避免重复添加
            if (!relatedChar.aiPhotoUrls.includes(aiPhoto.url)) {
              relatedChar.aiPhotoUrls.push(aiPhoto.url);
            }
            // 可选：给AI照片标记所属角色ID
            aiPhoto.characterId = relatedChar.id;
          }
        });
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

  startResizeStage5(e) {
    this.isResizingStage5 = true;
    this.startYStage5 = e.clientY;
    this.startHeightStage5 = this.stage5PhotoHeight;
    document.addEventListener('mousemove', this.doResizeStage5);
    document.addEventListener('mouseup', this.stopResizeStage5);
  },
  
  doResizeStage5(e) {
    if (!this.isResizingStage5) return;
    const diff = e.clientY - this.startYStage5;
    const newHeight = Math.max(100, this.startHeightStage5 + diff); // 最小高度100px
    this.stage5PhotoHeight = newHeight;
  },
  
  stopResizeStage5() {
    this.isResizingStage5 = false;
    document.removeEventListener('mousemove', this.doResizeStage5);
    document.removeEventListener('mouseup', this.stopResizeStage5);
  },

  async generateAiVideo() {
  if (this.isGeneratingVideo) return;
  this.isGeneratingVideo = true;
  this.videoGenerationError = null;

  let pollInterval = null;

  try {
    console.log('🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬🎬 [Stage5] 开始生成即梦视频（使用角色面板主角脸部）...');

    // ✅ 直接使用原始照片或AI照片
    let photosToUse = [];
    let subjectPhotosToUse = []; // 存储角色面板中的主角脸部照片
    
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

    // ✅ 新功能：为每张照片查找对应的主角脸部照片
    photosToUse.forEach((photo, index) => {
      // 获取照片的索引
      const photoIndex = photo.sourceIndex !== undefined ? photo.sourceIndex : index;
      
      // 在角色面板中查找该照片对应的主角（isMain为true的角色）
      const mainCharacter = this.characters.find(char => 
        char.photoIndex === photoIndex && char.isMain
      );
      
      if (mainCharacter && mainCharacter.avatar) {
        subjectPhotosToUse.push(mainCharacter.avatar);
        console.log(`✅ 照片 ${index} 找到对应主角脸部`);
      } else {
        // 如果没有找到主角脸部照片，使用原始照片作为占位
        subjectPhotosToUse.push(photo.url);
        console.log(`⚠️ 照片 ${index} 未找到主角脸部，使用原图`);
      }
    });

    const allPhotosUrls = photosToUse.map(p => p.url).filter(url => url && typeof url === 'string');
    const allSentences = photosToUse.map(p => p.sentence || '');
    const allSourceIndexes = photosToUse.map(p => p.sourceIndex || 0);

    console.log(`[Stage5] 使用 ${allPhotosUrls.length} 张图片生成视频`);
    console.log(`[Stage5] 使用 ${subjectPhotosToUse.length} 张主角脸部照片`);

    // ✅ 处理单张图片的情况 - 重复使用同一张图片
    let processedPhotosUrls = [...allPhotosUrls];
    let processedSourceIndexes = [...allSourceIndexes];
    let processedSentences = [...allSentences];
    let processedSubjectPhotos = [...subjectPhotosToUse];
    
    if (allPhotosUrls.length === 1) {
        console.log('⚠️ 只有一张图片，将重复使用以创建视频效果');
        processedPhotosUrls.push(allPhotosUrls[0]);
        processedSourceIndexes.push(allSourceIndexes[0]);
        processedSentences.push(allSentences[0] + '（重复）');
        processedSubjectPhotos.push(subjectPhotosToUse[0]);
    }

    console.log(`[Stage5] 处理后的图片序列:`, processedPhotosUrls.map((url, i) => 
      `图${i+1}`).join(' -> '));

    // ✅ 构建视频序列：包括静态视频和过渡视频
    const videoSequences = [];
    
    for (let i = 0; i < processedPhotosUrls.length; i++) {
        // 1. 生成静态视频（AA, BB, CC...）
        const staticSequence = {
            type: 'static',
            index: i * 2,
            photo1: processedPhotosUrls[i],
            photo2: processedPhotosUrls[i],
            subject1: processedSubjectPhotos[i], // 使用主角脸部照片
            subject2: processedSubjectPhotos[i],
            sourceIndex: processedSourceIndexes[i],
            sentence: processedSentences[i] || `图片 ${i + 1}`,
            description: `静态视频 - ${processedSentences[i]}`
        };
        videoSequences.push(staticSequence);
        
        // 2. 生成过渡视频（AB, BC...），除了最后一张照片
        if (i < processedPhotosUrls.length - 1) {
            const transitionSequence = {
                type: 'transition',
                index: i * 2 + 1,
                photo1: processedPhotosUrls[i],
                photo2: processedPhotosUrls[i + 1],
                subject1: processedSubjectPhotos[i], // 使用第一张的主角脸部
                subject2: processedSubjectPhotos[i + 1], // 使用第二张的主角脸部
                sourceIndex1: processedSourceIndexes[i],
                sourceIndex2: processedSourceIndexes[i + 1],
                sentence1: processedSentences[i] || `图片 ${i + 1}`,
                sentence2: processedSentences[i + 1] || `图片 ${i + 2}`,
                description: `过渡视频 - 从"${processedSentences[i]}"到"${processedSentences[i + 1]}"`
            };
            videoSequences.push(transitionSequence);
        }
    }

    console.log(`[Stage5] 生成 ${videoSequences.length} 个视频序列`);

    // 为每个视频序列动态生成专用prompt
    const jimengPromises = videoSequences.map(async (sequence, seqIndex) => {
        try {
            let promptType = sequence.type;
            let photoPair = [];
            let sentence = '';
            let nextSentence = '';
            let subjectPair = [];

            if (promptType === 'static') {
                photoPair = [sequence.photo1, sequence.photo1];
                subjectPair = [sequence.subject1, sequence.subject1];
                sentence = sequence.sentence;
                nextSentence = sequence.sentence;
            } else {
                photoPair = [sequence.photo1, sequence.photo2];
                subjectPair = [sequence.subject1, sequence.subject2];
                sentence = sequence.sentence1;
                nextSentence = sequence.sentence2;
            }

            const response = await axios.post('http://127.0.0.1:5000/refine-prompt', {
                type: promptType,
                photo_pair: photoPair,
                subject_pair: subjectPair, // 传入主角脸部照片
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
        if (result.type === 'static') {
            flatPhotos.push(result.photos[0], result.photos[0]);
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

    // 立即显示一个临时视频占位符（如果有的话）
    this.aiVideo.url = ''; // 清空之前的视频

    // 🔥🔥🔥【核心修复】添加40秒等待期
    console.log('⏳ 等待40秒后开始检测视频生成状态...');
    this.$message?.info?.('视频任务已提交，等待40秒后开始检测生成状态...');
    
    // 延迟40秒后再开始检测
    setTimeout(() => {
        this.startVideoPolling(taskId, allPhotosUrls, videoSequences);
    }, 40000); // 40秒等待

  } catch (err) {
    console.error("[Video Gen Submit Error]", err);
    this.videoGenerationError = err.message || "提交失败";
    this.isGeneratingVideo = false;
    this.$message?.error?.(`视频任务提交失败: ${err.message}`);
  }
},

// 🔥🔥🔥【新增】独立的视频轮询方法
// 替换 startVideoPolling 方法
startVideoPolling(taskId, allPhotosUrls, videoSequences) {
  console.log('🔍🔍 开始检测视频文件状态...');
  this.$message?.info?.('开始检测视频生成进度...');

  const MAX_POLL = 1800; // 30分钟（1800秒）
  let pollCount = 0;
  
  // 🔥🔥🔥【核心修复】新增基准时间点状态记录
  let baselineFileSize = 0;     // 第40秒的文件大小
  let baselineModified = 0;      // 第40秒的修改时间
  let baselineRecorded = false;  // 是否已记录基准状态
  
  // 🔥🔥🔥【核心修复】新增40秒后检测标志
  let checkAfter40s = false;     // 是否开始40秒后检测
  let fileChanged = false;       // 文件是否发生了变化

  const pollInterval = setInterval(async () => {
    try {
      pollCount++;
      
      // 检查视频文件状态
      const statusResp = await axios.get(`http://127.0.0.1:5000/video-file-status`, {
        timeout: 10000,
        params: {
          taskId: taskId,
          timestamp: Date.now() // 避免缓存
        }
      });

      const { fileExists, fileSize, lastModified: currentModified, videoUrl, isCompleted, error } = statusResp.data;

      console.log(`[视频检测] 轮询第${pollCount}次 - 文件存在: ${fileExists}, 大小: ${fileSize}字节, 修改时间: ${currentModified}`);

      if (error) {
        clearInterval(pollInterval);
        this.videoGenerationError = error;
        this.isGeneratingVideo = false;
        this.$message?.error?.(`视频生成错误：${error}`);
        return;
      }

      // 🔥🔥🔥【核心修复】第40秒记录基准状态
      if (pollCount === 1) { // 第40秒（因为等待40秒后才开始轮询，所以第一次轮询就是第40秒）
        baselineFileSize = fileSize || 0;
        baselineModified = currentModified || 0;
        baselineRecorded = true;
        console.log(`📊📊 第40秒基准状态记录 - 大小: ${baselineFileSize}, 修改时间: ${baselineModified}`);
        this.$message?.info?.('已记录第40秒视频文件状态，开始检测40秒后的变化...');
        
        // 如果文件不存在或大小为0，设置默认基准
        if (!fileExists || fileSize === 0) {
          console.log('⚠️⚠️ 第40秒文件不存在或为空，等待文件生成...');
        }
      }

      // 🔥🔥🔥【核心修复】第80秒进行对比检测（第8次轮询，因为40秒后每5秒一次，8 * 5=40秒）
      if (pollCount === 8 && baselineRecorded) {
        checkAfter40s = true;
        
        const currentFileSize = fileSize || 0;
        const currentModifiedTime = currentModified || 0;
        
        console.log(`📊📊 第80秒状态 - 大小: ${currentFileSize}, 修改时间: ${currentModifiedTime}`);
        console.log(`📊📊 40秒前后对比 - 大小变化: ${currentFileSize - baselineFileSize}, 修改时间是否相同: ${currentModifiedTime === baselineModified}`);
        
        // 🔥🔥🔥【核心逻辑】检测40秒后是否有变化 - 只有变化才算完成
        if (currentFileSize !== baselineFileSize || currentModifiedTime !== baselineModified) {
          // 文件发生了变化，认为视频生成完成
          fileChanged = true;
          console.log('✅✅✅ 检测到文件在40秒内发生变化，视频生成完成！');
          
          clearInterval(pollInterval);
          const finalVideoUrl = videoUrl + '?t=' + Date.now();
          this.aiVideo.url = finalVideoUrl;
          this.isGeneratingVideo = false;
          
          this.$message?.success?.("🎬 视频生成成功！（检测到40秒内文件变化）");
          
          // 记录到实验日志
          this.stage5VideoResult = {
            generatedTime: new Date().toISOString(),
            videoUrl: finalVideoUrl,
            fileSize: currentFileSize,
            lastModified: currentModifiedTime,
            baseline40s: {
              size: baselineFileSize,
              modified: baselineModified
            },
            after40s: {
              size: currentFileSize,
              modified: currentModifiedTime,
              changed: true
            },
            changeDetected: true,
            sizeChange: currentFileSize - baselineFileSize,
            timeChange: currentModifiedTime !== baselineModified,
            detectionMethod: '40s_change_detected',
            totalWaitTime: 40 + (pollCount * 5) // 40秒等待 + 轮询时间
          };
          
          return;
        } else {
          // 40秒内文件没有变化，继续监控
          console.log('⏳⏳ 40秒内文件无变化，继续监控...');
          this.$message?.info?.('40秒内未检测到文件变化，继续监控文件状态...');
        }
      }

      // 🔥🔥🔥【核心修复】第80秒后继续监控，直到检测到变化
      if (checkAfter40s && !fileChanged) {
        const currentFileSize = fileSize || 0;
        const currentModifiedTime = currentModified || 0;
        
        // 检查是否发生变化
        if (currentFileSize !== baselineFileSize || currentModifiedTime !== baselineModified) {
          // 文件发生了变化，认为视频生成完成
          fileChanged = true;
          console.log(`✅✅✅ 第${pollCount * 5}秒检测到文件变化，视频生成完成！`);
          
          clearInterval(pollInterval);
          const finalVideoUrl = videoUrl + '?t=' + Date.now();
          this.aiVideo.url = finalVideoUrl;
          this.isGeneratingVideo = false;
          
          this.$message?.success?.(`🎬 视频生成成功！（第${pollCount * 5}秒检测到变化）`);
          
          this.stage5VideoResult = {
            generatedTime: new Date().toISOString(),
            videoUrl: finalVideoUrl,
            fileSize: currentFileSize,
            lastModified: currentModifiedTime,
            baseline40s: {
              size: baselineFileSize,
              modified: baselineModified
            },
            after40s: {
              size: currentFileSize,
              modified: currentModifiedTime,
              changed: true
            },
            changeDetected: true,
            sizeChange: currentFileSize - baselineFileSize,
            timeChange: currentModifiedTime !== baselineModified,
            detectionMethod: `change_detected_at_${pollCount * 5}s`,
            totalWaitTime: 40 + (pollCount * 5)
          };
          
          return;
        } else {
          // 文件尚未变化，继续监控
          if (pollCount % 5 === 0) { // 每25秒提示一次
            console.log(`⏳⏳ 第${pollCount * 5}秒，文件尚未发生变化，继续监控...`);
            this.$message?.info?.(`已监控${pollCount * 5}秒，文件尚未完成生成，继续等待...`);
          }
        }
      }

      // 超时处理
      if (pollCount >= MAX_POLL) {
        clearInterval(pollInterval);
        const msg = `检测超时（${MAX_POLL * 5}秒），未检测到文件变化`;
        this.videoGenerationError = msg;
        this.isGeneratingVideo = false;
        this.$message?.error?.(msg);
        
        // 记录超时状态
        this.stage5VideoResult = {
          generatedTime: new Date().toISOString(),
          videoUrl: videoUrl || '',
          fileSize: fileSize || 0,
          lastModified: currentModified || 0,
          baseline40s: {
            size: baselineFileSize,
            modified: baselineModified
          },
          after40s: {
            size: fileSize || 0,
            modified: currentModified || 0,
            changed: false
          },
          changeDetected: false,
          timeout: true,
          detectionMethod: 'timeout_no_change',
          totalWaitTime: MAX_POLL * 5
        };
        
        console.error(msg);
      }
      
      // 进度提示
      if (pollCount === 1) {
        this.$message?.info?.('开始检测，已等待40秒，开始记录基准状态...');
      } else if (pollCount === 8) {
        this.$message?.info?.('已检测40秒，正在分析文件变化...');
      } else if (pollCount % 10 === 0 && !checkAfter40s) {
        this.$message?.info?.(`持续检测中，已进行 ${pollCount} 次检测（${pollCount * 5}秒）...`);
      }
      
    } catch (err) {
      console.error(`轮询视频文件状态出错:`, err);
      
      // 网络错误不立即失败，继续重试
      if (pollCount % 5 === 0) {
        this.$message?.warning?.(`网络检测错误，继续重试... (第${pollCount}次)`);
      }
      
      if (pollCount >= MAX_POLL) {
        clearInterval(pollInterval);
        const msg = `轮询超时（${MAX_POLL}次）`;
        this.videoGenerationError = msg;
        this.isGeneratingVideo = false;
        this.$message?.error?.(msg);
        console.error(msg);
      }
    }
  }, 5000); // 每5秒轮询一次
}
  }
}
</script>

<style scoped>
@import './style.css';
</style>