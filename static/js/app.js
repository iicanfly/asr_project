let isRecording = false;
        let audioContext = null;
        let processor = null;
        let mediaStream = null;
        let socket = null;
        let transcriptData = [];
        let startTime = 0;
        let timerInterval = null;

let audioChunks = [];
        let isBackendOnline = false;
        let cacheSaveTimer = null;
        const storageWarningState = {
            transcript: false,
            audio: false,
            history: false
        };

        const CACHE_KEY = 'voice_system_transcript_cache';
        const AUDIO_CACHE_KEY = 'voice_system_audio_blob';
        const CACHE_SAVE_DEBOUNCE_MS = 1500;

let messageIdCounter = 0;
        let seenResultIds = new Set();

        let currentDocType = 'meeting';

        const DOC_HISTORY_KEY = 'voice_system_doc_history';
        let docHistory = [];
        let currentDocument = null;

        function initSocketIO() {
            socket = io({
                transports: ['websocket', 'polling'],
                reconnection: true,
                reconnectionAttempts: Infinity,
                reconnectionDelay: 1000,
                reconnectionDelayMax: 5000
            });

            socket.on('connect', () => {
                console.log('Socket.IO 已连接, sid:', socket.id);
                isBackendOnline = true;
                updateConnectionStatus(true);
            });

            socket.on('disconnect', (reason) => {
                console.log('Socket.IO 断开连接:', reason);
                isBackendOnline = false;
                updateConnectionStatus(false);
            });

            socket.on('asr_result', (data) => {
                handleASRResult(data);
            });

            socket.on('asr_error', (data) => {
                console.error('ASR 错误:', data.message);
            });

            socket.on('connect_error', (error) => {
                console.error('Socket.IO 连接错误:', error);
                isBackendOnline = false;
                updateConnectionStatus(false);
            });
        }

        function updateConnectionStatus(online) {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.textContent = online ? '✅ 已连接' : '❌ 未连接';
                statusEl.style.color = online ? '#2ecc71' : '#e74c3c';
            }
            const badge = document.getElementById('ws-status');
            if (badge) {
                badge.textContent = online ? '🟢 已连接' : '🔴 未连接';
                badge.className = 'status-badge ' + (online ? 'status-online' : 'status-error');
            }
        }

        function shouldBufferAudioLocally() {
            return !isBackendOnline || !(socket && socket.connected);
        }

        function cacheOfflineAudioChunk(inputData) {
            if (!shouldBufferAudioLocally()) return;
            audioChunks.push(new Float32Array(inputData));
        }

        function formatBytes(bytes) {
            if (!bytes || bytes <= 0) return '0 KB';
            if (bytes < 1024 * 1024) {
                return `${(bytes / 1024).toFixed(1)} KB`;
            }
            return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
        }

        function showStorageWarning(kind, message) {
            if (!storageWarningState[kind]) {
                storageWarningState[kind] = true;
                console.warn(message);
            }

            const infoEl = document.getElementById('cache-info');
            if (infoEl) {
                infoEl.title = message;
                infoEl.dataset.warning = 'true';
                infoEl.style.color = '#e67e22';
            }
        }

        function clearStorageWarning(kind) {
            storageWarningState[kind] = false;
            if (Object.values(storageWarningState).some(Boolean)) return;

            const infoEl = document.getElementById('cache-info');
            if (infoEl) {
                infoEl.title = '';
                delete infoEl.dataset.warning;
                infoEl.style.color = '';
            }
        }

        function safeSetLocalStorage(key, value, { warningKind, warningMessage } = {}) {
            try {
                localStorage.setItem(key, value);
                if (warningKind) {
                    clearStorageWarning(warningKind);
                }
                return true;
            } catch (error) {
                console.error(`localStorage 写入失败: ${key}`, error);
                if (warningKind && warningMessage) {
                    showStorageWarning(warningKind, warningMessage);
                }
                return false;
            }
        }

        function safeRemoveLocalStorage(key) {
            try {
                localStorage.removeItem(key);
            } catch (error) {
                console.error(`localStorage 删除失败: ${key}`, error);
            }
        }

        window.onload = async () => {
            initSocketIO();
            initConfigPage();
            checkBackendStatus();
            updateCacheInfo();
            checkPendingAudio();
            loadDocHistory();

            setInterval(checkBackendStatus, 5000);
        };

        window.addEventListener('beforeunload', () => {
            saveCache({ immediate: true });
        });

        // --- 侧边栏切换 ---
        function switchTab(tabId) {
            // 更新菜单项状态
            document.querySelectorAll('.menu-item').forEach(item => {
                item.classList.remove('active');
            });
            event.currentTarget.classList.add('active');

            // 如果正在录音，切换 Tab 前提示用户
            if (isRecording && tabId !== 'realtime') {
                const continueRecording = confirm('正在录音中，切换页面后录音将继续进行。是否继续？');
                if (!continueRecording) {
                    return; // 取消切换
                }
            }

            // 更新面板显示
            document.querySelectorAll('.main-content').forEach(panel => {
                panel.style.display = 'none';
            });
            document.getElementById(`tab-${tabId}`).style.display = 'flex';

            // 如果切换到实时转写标签，恢复会话状态（不清空）
            if (tabId === 'realtime') {
                // 检查是否有未恢复的会话
                showSessionRestoreHint();
            }

            // 如果切换到历史记录标签，刷新历史列表
            if (tabId === 'history') {
                renderDocHistory();
            }
        }

        // 显示会话恢复提示
        function showSessionRestoreHint() {
            // 如果有转写内容或正在录音，显示提示
            if (transcriptData.length > 0 || isRecording) {
                // 可以在页面顶部显示一个可关闭的提示条
                // 这里简单处理：如果有内容就保持，不做额外提示
                console.log('会话已恢复，转写条数:', transcriptData.length);
            }
        }

        function checkBackendStatus() {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.innerHTML = '<span style="color: #666;">检测中...</span>';
            }
            if (socket && socket.connected) {
                isBackendOnline = true;
                const badge = document.getElementById('backend-status');
                const health = document.getElementById('system-health');
                if (badge) {
                    badge.innerText = '后端：在线';
                    badge.className = 'status-badge status-online';
                }
                if (health) health.innerText = '运行正常';
                if (statusEl) statusEl.innerHTML = '<span style="color: #2ecc71;">✅ 已连接</span>';
            } else {
                isBackendOnline = false;
                const badge = document.getElementById('backend-status');
                if (badge) {
                    badge.innerText = '后端：离线';
                    badge.className = 'status-badge status-error';
                }
                const health = document.getElementById('system-health');
                if (health) health.innerText = '连接异常';
                if (statusEl) statusEl.innerHTML = '<span style="color: #e74c3c;">❌ 未连接</span>';
            }
        }

        function initConfigPage() {
            fetch('/api/v1/debug/status')
                .then(res => res.json())
                .then(data => {
                    document.getElementById('config-asr-url').value = data.asr_model || '';
                    document.getElementById('config-llm-url').value = data.llm_model || '';
                    document.getElementById('config-mode').value = data.mode || '';
                })
                .catch(() => {});
        }

        // --- 录音逻辑 ---

        async function toggleRecording() {
            if (!isRecording) {
                await startRecording();
            } else {
                stopRecording();
            }
        }

        async function startRecording() {
            try {
                audioChunks = [];

                if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                    console.log('navigator.mediaDevices:', navigator.mediaDevices);
                    console.log('navigator.mediaDevices.getUserMedia:', navigator.mediaDevices?.getUserMedia);
                    alert("当前环境不支持 getUserMedia。请确保在 HTTPS 或 localhost 环境下运行。\n\n解决方案：\n1. 在服务器电脑上用 localhost 访问\n2. 配置 HTTPS 证书\n3. 使用 ngrok 等工具创建安全隧道");
                    return;
                }

                console.log("正在请求麦克风权限...");
                mediaStream = await navigator.mediaDevices.getUserMedia({
                    audio: {
                        channelCount: 1,
                        sampleRate: 16000,
                        echoCancellation: true,
                        noiseSuppression: true
                    }
                });
                console.log("麦克风权限获取成功", mediaStream);

                if (!isBackendOnline) {
                    console.warn("后端离线，录音将仅进行本地缓存");
                    document.getElementById('asr-status').innerText = '本地缓存模式';
                    document.getElementById('asr-status').classList.add('status-error');
                }

                await setupAudioProcessing();

                isRecording = true;
                document.getElementById('record-text').innerText = '停止录音';
                document.getElementById('record-btn').classList.replace('btn-danger', 'btn-primary');
                document.getElementById('record-icon').innerHTML = '<span class="recording-pulse"></span>';

                startTimer();

            } catch (err) {
                console.error("无法开启麦克风:", err);
                let errorMsg = "无法访问麦克风。\n\n";
                if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                    errorMsg += "原因：权限被拒绝。\n\n解决方法：\n请在浏览器中允许麦克风权限";
                } else if (err.name === 'NotFoundError') {
                    errorMsg += "原因：未检测到麦克风设备。";
                } else {
                    errorMsg += "错误信息：" + err.message;
                }
                alert(errorMsg);
            }
        }

        async function setupAudioProcessing() {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
            const source = audioContext.createMediaStreamSource(mediaStream);

            try {
                await audioContext.audioWorklet.addModule('/static/js/audio-processor.js');
                processor = new AudioWorkletNode(audioContext, 'audio-processor');

                processor.port.onmessage = (e) => {
                    if (!isRecording) return;

                    const inputData = e.data;

                    cacheOfflineAudioChunk(inputData);

                    if (socket && socket.connected) {
                        const pcmData = convertFloat32To16BitPCM(inputData);
                        socket.emit('audio_stream', pcmData);
                    }

                    updateVisualizer(inputData);
                };

                source.connect(processor);
            } catch (err) {
                console.warn('AudioWorklet 不可用，回退到 ScriptProcessorNode:', err);
                processor = audioContext.createScriptProcessor(512, 1, 1);

                processor.onaudioprocess = (e) => {
                    if (!isRecording) return;

                    const inputData = e.inputBuffer.getChannelData(0);

                    cacheOfflineAudioChunk(inputData);

                    if (socket && socket.connected) {
                        const pcmData = convertFloat32To16BitPCM(inputData);
                        socket.emit('audio_stream', pcmData);
                    }

                    updateVisualizer(inputData);
                };

                source.connect(processor);
                processor.connect(audioContext.destination);
            }
        }

        function emitStopRecording() {
            if (socket && socket.connected) {
                socket.emit('stop_recording', {
                    reason: 'manual_stop',
                    client_time: new Date().toISOString()
                });
            }
        }

function stopRecording() {
            isRecording = false;
            emitStopRecording();
            
            if (mediaStream) mediaStream.getTracks().forEach(t => t.stop());
            if (processor) processor.disconnect();
            if (audioContext) audioContext.close();

            saveAudioToLocal();
            saveCache({ immediate: true });

            document.getElementById('record-text').innerText = '继续录音';
            document.getElementById('record-btn').classList.replace('btn-primary', 'btn-danger');
            document.getElementById('record-icon').innerText = '⏺️';
            document.getElementById('asr-status').innerText = 'ASR：就绪';
            document.getElementById('asr-status').className = 'status-badge';
            
            stopTimer();
            
            if (transcriptData.length > 0 || audioChunks.length > 0) {
                const btn = document.getElementById('minutes-btn');
                btn.style.display = 'flex';
                btn.disabled = false;
                btn.innerText = '📝 生成文档';
            }
        }

        // --- 补偿机制核心逻辑 ---
        const COMP_PROCESSED_KEY = 'voice_system_comp_processed';

        function saveAudioToLocal() {
            if (audioChunks.length === 0) return;
            
            const flatBuffer = flattenArray(audioChunks);
            const pcmBuffer = convertFloat32To16BitPCM(flatBuffer);
            const blob = new Blob([pcmBuffer], { type: 'audio/wav' });
            
            const reader = new FileReader();
            reader.onload = function() {
                const audioSaved = safeSetLocalStorage(AUDIO_CACHE_KEY, reader.result, {
                    warningKind: 'audio',
                    warningMessage: '离线补偿音频缓存写入失败，可能是浏览器本地存储空间不足。'
                });

                if (audioSaved) {
                    safeSetLocalStorage(COMP_PROCESSED_KEY, 'false');
                    console.log("音频已存入本地缓存");
                }

                audioChunks = [];
                updateCacheInfo();
            };
            reader.readAsDataURL(blob);
        }

        function checkPendingAudio() {
            const pending = localStorage.getItem(AUDIO_CACHE_KEY);
            const processed = localStorage.getItem(COMP_PROCESSED_KEY);
            
            if (pending && processed === 'false' && isBackendOnline) {
                // 如果当前没有任何转写内容，才提示补偿，避免干扰正常录音流程
                if (transcriptData.length === 0) {
                    showUploadPrompt();
                }
            }
        }

        function showUploadPrompt() {
            if (confirm("检测到有上次录音未完整上传（或后端曾离线），是否立即上传补偿并识别？")) {
                uploadCachedAudio();
            } else {
                // 用户拒绝后，标记为已处理，避免反复弹出
                safeSetLocalStorage(COMP_PROCESSED_KEY, 'true');
                updateCacheInfo();
            }
        }

        async function uploadCachedAudio() {
            const dataUrl = localStorage.getItem(AUDIO_CACHE_KEY);
            if (!dataUrl) return;

            const blob = dataURLtoBlob(dataUrl);
            const formData = new FormData();
            formData.append('file', blob, `rec_recovery_${Date.now()}.wav`);

            try {
                const res = await fetch('/api/v1/audio/upload', {
                    method: 'POST',
                    body: formData
                });
                
                if (res.ok) {
                    const result = await res.json();
                    safeSetLocalStorage(COMP_PROCESSED_KEY, 'true'); // 标记为已补偿
                    // 暂时保留原始音频，直到用户手动清空或新录音覆盖
                    updateCacheInfo();
                    
                    // 将补偿转写结果展示出来
                    const transcriptText = result.transcript && result.transcript.trim() ? result.transcript : "[未识别到话语]";
                    
                    handleASRResult({
                        speaker_id: "离线补偿",
                        text: transcriptText,
                        is_final: true
                    });
                    
                    alert("音频补偿识别成功！结果已加入列表。");
                    
                    if (transcriptData.length > 0) {
                        document.getElementById('minutes-btn').style.display = 'flex';
                    }
                }
            } catch (e) {
                console.error("补偿上传失败:", e);
                alert("补偿上传失败，请稍后重试。");
            }
        }

        function flattenArray(chunks) {
            const length = chunks.reduce((acc, curr) => acc + curr.length, 0);
            const result = new Float32Array(length);
            let offset = 0;
            for (const chunk of chunks) {
                result.set(chunk, offset);
                offset += chunk.length;
            }
            return result;
        }

        function dataURLtoBlob(dataurl) {
            var arr = dataurl.split(','), mime = arr[0].match(/:(.*?);/)[1],
                bstr = atob(arr[1]), n = bstr.length, u8arr = new Uint8Array(n);
            while(n--){
                u8arr[n] = bstr.charCodeAt(n);
            }
            return new Blob([u8arr], {type:mime});
        }

        // --- 数据处理 ---
        let lastSpeaker = null;
        let lastMessageTime = 0;

function buildTranscriptEntry(data, messageId, text, timeStr) {
            return {
                id: messageId,
                speaker: data.speaker_id,
                content: text,
                time: timeStr,
                serverResultId: data.result_id || null,
                segmentId: data.segment_id || null,
                resultType: data.result_type || (data.is_final ? 'final' : 'partial')
            };
        }

function rememberResultId(resultId) {
            if (!resultId) return;
            seenResultIds.add(resultId);
        }

        function rememberMessageId(messageId) {
            const numericId = Number(messageId);
            if (!Number.isFinite(numericId) || numericId <= 0) return;
            messageIdCounter = Math.max(messageIdCounter, numericId);
        }

        function rebuildSeenResultIds() {
            seenResultIds = new Set();
            transcriptData.forEach(item => {
                if (item.serverResultId) {
                    seenResultIds.add(item.serverResultId);
                }
            });
        }

        function hasSeenResultId(resultId) {
            return Boolean(resultId) && seenResultIds.has(resultId);
        }

        function shouldInsertTranscriptSpace(previousText, nextText) {
            const prev = (previousText || '').trim();
            const next = (nextText || '').trim();
            if (!prev || !next) return false;

            const prevChar = prev.slice(-1);
            const nextChar = next.charAt(0);
            const asciiWord = /[A-Za-z0-9]/;
            return asciiWord.test(prevChar) && asciiWord.test(nextChar);
        }

        function mergeTranscriptText(previousText, nextText) {
            const prev = (previousText || '').trim();
            const next = (nextText || '').trim();
            if (!prev) return next;
            if (!next) return prev;
            return shouldInsertTranscriptSpace(prev, next) ? `${prev} ${next}` : `${prev}${next}`;
        }

        function updateMessageUI(messageId, text, time) {
            const messageDiv = document.querySelector(`div[data-message-id="${messageId}"]`);
            if (!messageDiv) return false;

            const contentDiv = messageDiv.querySelector('.message-content');
            const timeTag = messageDiv.querySelector('.time-tag');

            if (contentDiv) contentDiv.innerText = text;
            if (timeTag) timeTag.innerText = time;
            return true;
        }

        function replaceTranscriptEntry(data, text, timeStr) {
            if (!data.replace_target_id) return false;

            const target = transcriptData.find(item => item.serverResultId === data.replace_target_id);
            if (!target) return false;

            target.content = text;
            target.time = timeStr;
            target.serverResultId = data.result_id || target.serverResultId;
            target.segmentId = data.segment_id || target.segmentId;
            target.resultType = data.result_type || target.resultType;
            rememberResultId(data.result_id);

            updateMessageUI(target.id, text, timeStr);
            saveCache();
            document.getElementById('clear-btn').style.display = 'block';
            return true;
        }

function handleASRResult(data) {
            // 实时更新转写列表
            const list = document.getElementById('transcript-list');
            if (list.querySelector('.empty-state')) list.innerHTML = '';

            if (hasSeenResultId(data.result_id)) {
                console.log('跳过重复 result_id:', data.result_id);
                return;
            }

            // 如果识别结果为空，显示"未识别到话语"
            const text = data.text && data.text.trim() ? data.text : "[未识别到话语]";
            const now = Date.now();
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            if (replaceTranscriptEntry(data, text, timeStr)) {
                lastSpeaker = data.speaker_id;
                lastMessageTime = now;
                return;
            }

            const lastEntry = transcriptData.length > 0 ? transcriptData[transcriptData.length - 1] : null;
            const sameSegmentContinuation = Boolean(
                lastEntry &&
                data.segment_id &&
                lastEntry.segmentId &&
                data.segment_id === lastEntry.segmentId
            );
            const serverDrivenSegmentBoundary = Boolean(
                lastEntry &&
                data.segment_id &&
                lastEntry.segmentId &&
                data.segment_id !== lastEntry.segmentId
            );

            // 智能分段逻辑：
            // 1. 如果后端显式给出了相同 segment_id，则强制继续合并到同一个段落
            // 2. 如果后端显式切换了新的 segment_id，则强制新建段落
            // 3. 其它情况沿用原有“同说话人 + 10 秒内”规则
            const shouldMerge = sameSegmentContinuation || (
                !serverDrivenSegmentBoundary &&
                lastSpeaker === data.speaker_id &&
                (now - lastMessageTime < 10000)
            );

            if (shouldMerge && transcriptData.length > 0) {
                const mergedText = mergeTranscriptText(lastEntry.content, text);
                addMessageUI(data.speaker_id, text, timeStr, true, lastEntry.id);
                lastEntry.content = mergedText;
                lastEntry.time = timeStr;
                lastEntry.serverResultId = data.result_id || lastEntry.serverResultId;
                lastEntry.segmentId = data.segment_id || lastEntry.segmentId;
                lastEntry.resultType = data.result_type || lastEntry.resultType;
                rememberResultId(data.result_id);
            } else {
                // 生成唯一消息 ID
                const messageId = ++messageIdCounter;

                addMessageUI(data.speaker_id, text, timeStr, false, messageId);
                transcriptData.push(buildTranscriptEntry(data, messageId, text, timeStr));
                rememberResultId(data.result_id);
            }

            lastSpeaker = data.speaker_id;
            lastMessageTime = now;
            saveCache();

            // 显示清空按钮
            document.getElementById('clear-btn').style.display = 'block';
        }

function addMessageUI(speaker, text, time, merge = false, messageId = null) {
            const list = document.getElementById('transcript-list');
            const isSpeaker2 = speaker.includes('Speaker_2') || speaker.includes('2');

            if (merge && list.lastElementChild && list.lastElementChild.classList.contains('message')) {
                // 合并到最后一个消息气泡
                const lastMsg = list.lastElementChild;
                const contentDiv = lastMsg.querySelector('.message-content');
                contentDiv.innerText = mergeTranscriptText(contentDiv.innerText, text);
                const timeTag = lastMsg.querySelector('.time-tag');
                if (timeTag) timeTag.innerText = time;
            } else {
                // 新建消息气泡
                const div = document.createElement('div');
                div.className = `message ${isSpeaker2 ? 'speaker-2' : 'speaker-1'}`;
                const resolvedMessageId = messageId || ++messageIdCounter;
                rememberMessageId(resolvedMessageId);
                div.dataset.messageId = resolvedMessageId;

                div.innerHTML = `
                    <div class="message-actions">
                        <button class="message-action-btn" onclick="editMessage(${div.dataset.messageId})" title="编辑">✏️</button>
                        <button class="message-action-btn" onclick="deleteMessage(${div.dataset.messageId})" title="删除">🗑️</button>
                    </div>
                    <span class="speaker-tag">${speaker}</span>
                    <div class="message-content">${text}</div>
                    <span class="time-tag">${time}</span>
                `;
                list.appendChild(div);
            }
            list.scrollTop = list.scrollHeight;
        }

        // --- 辅助工具 ---

        function convertFloat32To16BitPCM(input) {
            const output = new Int16Array(input.length);
            for (let i = 0; i < input.length; i++) {
                const s = Math.max(-1, Math.min(1, input[i]));
                output[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
            }
            return output.buffer;
        }

        function updateVisualizer(data) {
            const bars = document.querySelectorAll('.v-bar');
            const step = Math.floor(data.length / bars.length);
            for (let i = 0; i < bars.length; i++) {
                let sum = 0;
                for (let j = 0; j < step; j++) {
                    sum += Math.abs(data[i * step + j]);
                }
                const height = Math.min(40, (sum / step) * 200 + 4);
                bars[i].style.height = `${height}px`;
            }
        }

        // --- 计时器 ---
        function startTimer() {
            startTime = Date.now();
            const el = document.getElementById('record-timer');
            el.style.display = 'block';
            timerInterval = setInterval(() => {
                const diff = Date.now() - startTime;
                const h = Math.floor(diff / 3600000).toString().padStart(2, '0');
                const m = Math.floor((diff % 3600000) / 60000).toString().padStart(2, '0');
                const s = Math.floor((diff % 60000) / 1000).toString().padStart(2, '0');
                el.innerText = `${h}:${m}:${s}`;
            }, 1000);
        }

        function stopTimer() {
            clearInterval(timerInterval);
        }

        // --- 文件上传处理 ---
        async function handleFileUpload(event) {
            const files = event.target.files;
            if (!files || files.length === 0) return;

            const progressContainer = document.getElementById('upload-progress-container');
            const progressBar = document.getElementById('progress-bar');
            const uploadInput = event.target;
            
            // 重置"生成文档"按钮状态，防止卡在"正在思考"
            const minutesBtn = document.getElementById('minutes-btn');
            minutesBtn.disabled = false;
            minutesBtn.innerText = '📝 生成文档';
            
            progressContainer.style.display = 'block';

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                progressBar.style.width = `${(i / files.length) * 100}%`;
                
                const formData = new FormData();
                formData.append('file', file);

                try {
                    console.log(`正在上传并识别文件 (${i + 1}/${files.length}):`, file.name);
                    
                    const response = await fetch('/api/v1/audio/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    if (!response.ok) throw new Error(`文件 ${file.name} 上传识别失败`);
                    
                    const result = await response.json();
                    
                    // 将识别结果加入转写列表
                    if (result.transcript && result.transcript.trim()) {
                        handleASRResult({
                            speaker_id: `文件_${file.name.slice(0, 5)}`,
                            text: result.transcript,
                            is_final: true
                        });
                    } else {
                        handleASRResult({
                            speaker_id: `文件_${file.name.slice(0, 5)}`,
                            text: "[未识别到话语]",
                            is_final: true
                        });
                    }
                    minutesBtn.style.display = 'flex';

                } catch (err) {
                    console.error("文件处理失败:", err);
                    alert(`文件 ${file.name} 处理失败: ` + err.message);
                }
            }

            progressBar.style.width = '100%';
            setTimeout(() => {
                progressContainer.style.display = 'none';
                uploadInput.value = ''; // 允许重复上传
            }, 500);
        }

        // --- 手动输入文本 ---
        function handleInputKeypress(event) {
            // 回车键提交
            if (event.key === 'Enter') {
                submitManualInput();
            }
        }

        function submitManualInput() {
            const input = document.getElementById('manual-input');
            const text = input.value.trim();

            if (!text) {
                alert('请输入内容');
                return;
            }

            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            // 添加到转写列表
            handleASRResult({
                speaker_id: "手动输入",
                text: text,
                is_final: true
            });

            // 清空输入框
            input.value = '';

            // 显示生成文档按钮
            const btn = document.getElementById('minutes-btn');
            btn.style.display = 'flex';
            btn.disabled = false;
            btn.innerText = '📝 生成文档';

            console.log(`手动输入已添加: ${text}`);
        }

        // --- 大输入框模态框功能 ---
        function openInputModal() {
            // 将当前小输入框的内容同步到大输入框
            const smallInput = document.getElementById('manual-input');
            const modalInput = document.getElementById('modal-input-text');
            modalInput.value = smallInput.value;

            // 显示模态框
            document.getElementById('input-modal-overlay').classList.add('show');

            // 聚焦到输入框
            setTimeout(() => {
                modalInput.focus();
            }, 100);
        }

        function closeInputModal() {
            document.getElementById('input-modal-overlay').classList.remove('show');
        }

        function submitModalInput() {
            const modalInput = document.getElementById('modal-input-text');
            const text = modalInput.value.trim();

            if (!text) {
                alert('请输入内容');
                return;
            }

            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

            // 添加到转写列表
            handleASRResult({
                speaker_id: "手动输入",
                text: text,
                is_final: true
            });

            // 清空两个输入框
            modalInput.value = '';
            document.getElementById('manual-input').value = '';

            // 关闭模态框
            closeInputModal();

            // 显示生成文档按钮
            const btn = document.getElementById('minutes-btn');
            btn.style.display = 'flex';
            btn.disabled = false;
            btn.innerText = '📝 生成文档';

            console.log(`手动输入已添加: ${text}`);
        }

        // 点击模态框外部关闭
        document.addEventListener('DOMContentLoaded', function() {
            const overlay = document.getElementById('input-modal-overlay');
            if (overlay) {
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) {
                        closeInputModal();
                    }
                });
            }
        });

        // --- 消息编辑功能 ---
        function editMessage(messageId) {
            const messageDiv = document.querySelector(`div[data-message-id="${messageId}"]`);
            if (!messageDiv) return;

            // 添加编辑状态类，增加宽度
            messageDiv.classList.add('editing');

            const contentDiv = messageDiv.querySelector('.message-content');
            const currentText = contentDiv.innerText.trim();

            // 将内容替换为编辑框
            contentDiv.innerHTML = `
                <textarea class="message-edit-input" id="edit-input-${messageId}">${currentText}</textarea>
                <div class="message-edit-actions">
                    <button class="btn" style="padding: 4px 10px; font-size: 0.8rem;" onclick="cancelEdit(${messageId}, '${currentText.replace(/'/g, "\\'")}')">取消</button>
                    <button class="btn btn-primary" style="padding: 4px 10px; font-size: 0.8rem;" onclick="saveEdit(${messageId})">保存</button>
                </div>
            `;

            // 聚焦到输入框
            const textarea = document.getElementById(`edit-input-${messageId}`);
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);

            // 禁用编辑按钮
            const editBtn = messageDiv.querySelector('.message-action-btn:first-child');
            editBtn.disabled = true;
            editBtn.style.opacity = '0.5';
        }

        function cancelEdit(messageId, originalText) {
            const messageDiv = document.querySelector(`div[data-message-id="${messageId}"]`);
            if (!messageDiv) return;

            const contentDiv = messageDiv.querySelector('.message-content');
            contentDiv.innerHTML = originalText;

            // 移除编辑状态类
            messageDiv.classList.remove('editing');

            // 启用编辑按钮
            const editBtn = messageDiv.querySelector('.message-action-btn:first-child');
            editBtn.disabled = false;
            editBtn.style.opacity = '1';
        }

        function saveEdit(messageId) {
            const textarea = document.getElementById(`edit-input-${messageId}`);
            if (!textarea) return;

            const newText = textarea.value.trim();
            if (!newText) {
                alert('内容不能为空');
                return;
            }

            // 更新 UI
            const messageDiv = document.querySelector(`div[data-message-id="${messageId}"]`);
            if (!messageDiv) return;

            const contentDiv = messageDiv.querySelector('.message-content');
            contentDiv.innerHTML = newText;

            // 移除编辑状态类
            messageDiv.classList.remove('editing');

            // 更新数据
            const messageData = transcriptData.find(m => m.id === messageId);
            if (messageData) {
                messageData.content = newText;
                saveCache();
            }

            // 启用编辑按钮
            const editBtn = messageDiv.querySelector('.message-action-btn:first-child');
            editBtn.disabled = false;
            editBtn.style.opacity = '1';

            console.log(`消息 ${messageId} 已更新: ${newText}`);
        }

        function deleteMessage(messageId) {
            if (!confirm('确定要删除这条消息吗？')) return;

            // 从 DOM 中删除
            const messageDiv = document.querySelector(`div[data-message-id="${messageId}"]`);
            if (messageDiv) {
                messageDiv.remove();
            }

            // 从数据中删除
            const index = transcriptData.findIndex(m => m.id === messageId);
            if (index !== -1) {
                transcriptData.splice(index, 1);
                rebuildSeenResultIds();
                saveCache();
            }

            // 如果没有消息了，隐藏生成文档按钮和清空按钮
            if (transcriptData.length === 0) {
                document.getElementById('minutes-btn').style.display = 'none';
                document.getElementById('clear-btn').style.display = 'none';
                const list = document.getElementById('transcript-list');
                if (list.children.length === 0) {
                    list.innerHTML = '<div class="empty-state">等待音频输入... 请点击下方"开始录音"或"上传音频"</div>';
                }
            }

            console.log(`消息 ${messageId} 已删除`);
        }

        // --- 文档类型选择 ---
        function showDocumentTypeDialog() {
            const modal = document.getElementById('doc-type-modal');
            modal.style.display = 'flex';
        }

        function closeDocumentTypeDialog() {
            const modal = document.getElementById('doc-type-modal');
            modal.style.display = 'none';
        }

        async function generateDocument(docType) {
            closeDocumentTypeDialog();

            // 保存当前文档类型
            currentDocType = docType;

            const btn = document.getElementById('minutes-btn');
            const content = document.getElementById('minutes-content');

            // 文档类型映射
            const docTypeNames = {
                'meeting': '会议纪要',
                'report': '出差报告',
                'publicity': '宣传报道'
            };

            const docTypeName = docTypeNames[docType];

            btn.disabled = true;
            btn.innerText = '正在生成...';
            content.innerHTML = `<div class="empty-state">AI 正在生成${docTypeName}，请稍候...</div>`;

            // 立即更新右侧面板标题
            const panelTitle = document.getElementById('minutes-panel-title');
            if (panelTitle) {
                panelTitle.innerText = `${docTypeName} (LLM)`;
            }

            try {
                const response = await fetch('/api/v1/llm/summarize', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        transcript: transcriptData,
                        doc_type: docType
                    })
                });

                const data = await response.json();

                // 保存当前文档信息
                currentDocument = {
                    id: Date.now(),
                    title: data.doc_title || docTypeName,
                    content: data.summary_text,
                    docType: docType,
                    docTypeName: docTypeName,
                    createdTime: data.created_time || new Date().toLocaleString(),
                    transcript: [...transcriptData]
                };

                // 保存到历史记录
                saveDocToHistory(currentDocument);

                // 在右侧面板显示文档
                content.innerHTML = `
                    <div style="background: #fdfdfe; padding: 15px; border-radius: 6px; border: 1px solid #eee;">
                        <h4 style="margin-top:0; color: var(--accent-color);">${currentDocument.title}</h4>
                        <div style="white-space: pre-wrap; line-height: 1.6; font-size: 0.95rem;">${data.summary_text}</div>
                    </div>
                `;

                document.getElementById('minutes-actions').style.display = 'flex';
                btn.style.display = 'none';

            } catch (e) {
                content.innerHTML = '<div class="status-error" style="padding:10px; border-radius:4px;">生成失败，请确认后端 API 是否可用。</div>';
                btn.disabled = false;
                btn.innerText = '📝 生成文档';
            }
        }

        // --- 历史记录管理 ---
        function loadDocHistory() {
            const saved = localStorage.getItem(DOC_HISTORY_KEY);
            if (saved) {
                try {
                    docHistory = JSON.parse(saved);
                } catch (e) {
                    console.error('加载历史记录失败:', e);
                    docHistory = [];
                    safeRemoveLocalStorage(DOC_HISTORY_KEY);
                    showStorageWarning('history', '历史文档缓存读取失败，已自动忽略损坏缓存。');
                }
            }
        }

        function saveDocToHistory(doc) {
            // 添加到历史记录开头
            docHistory.unshift(doc);

            // 限制历史记录数量（最多保存 50 条）
            if (docHistory.length > 50) {
                docHistory = docHistory.slice(0, 50);
            }

            // 保存到 localStorage
            safeSetLocalStorage(DOC_HISTORY_KEY, JSON.stringify(docHistory), {
                warningKind: 'history',
                warningMessage: '历史文档缓存写入失败，可能是浏览器本地存储空间不足。'
            });
        }

        function renderDocHistory() {
            const listContainer = document.getElementById('history-list');

            if (!docHistory || docHistory.length === 0) {
                listContainer.innerHTML = '<div class="empty-state">暂无历史文档</div>';
                // 隐藏清空按钮
                document.getElementById('clear-history-btn').style.display = 'none';
                return;
            }

            // 显示清空按钮
            document.getElementById('clear-history-btn').style.display = 'block';

            listContainer.innerHTML = '<ul class="history-list-ul">' +
                docHistory.map(doc => `
                    <li class="history-item">
                        <div class="history-item-content" onclick="openHistoryDoc(${doc.id})">
                            <div class="history-item-title">${doc.title}</div>
                            <div class="history-item-meta">
                                <span>📅 ${doc.createdTime}</span>
                                <span>👤 系统用户</span>
                                <span>📄 ${doc.docTypeName}</span>
                            </div>
                        </div>
                        <button class="history-delete-btn" onclick="deleteHistoryDoc(${doc.id}, event)" title="删除">🗑️</button>
                    </li>
                `).join('') +
                '</ul>';
        }

        function openHistoryDoc(docId) {
            const doc = docHistory.find(d => d.id === docId);
            if (!doc) return;

            // 保存当前查看的历史文档，用于预览和下载
            currentDocument = doc;
            currentDocType = doc.docType;

            // 填充抽屉内容
            const metaDiv = document.getElementById('drawer-doc-meta');
            metaDiv.innerHTML = `
                <div class="doc-meta-item">
                    <span class="doc-meta-label">文档类型：</span>
                    <span>${doc.docTypeName}</span>
                </div>
                <div class="doc-meta-item">
                    <span class="doc-meta-label">创建时间：</span>
                    <span>${doc.createdTime}</span>
                </div>
                <div class="doc-meta-item">
                    <span class="doc-meta-label">转写条数：</span>
                    <span>${doc.transcript ? doc.transcript.length : 0} 条</span>
                </div>
            `;

            const bodyDiv = document.getElementById('drawer-doc-body');
            bodyDiv.innerHTML = `
                <h4>${doc.title}</h4>
                <div class="doc-body-content">${doc.content}</div>
            `;

            // 填充转写记录
            const transcriptDiv = document.getElementById('drawer-transcript-list');
            if (doc.transcript && doc.transcript.length > 0) {
                transcriptDiv.innerHTML = doc.transcript.map(item => `
                    <div class="drawer-transcript-item">
                        <div>
                            <span class="drawer-transcript-speaker">${item.speaker}</span>
                            <span class="drawer-transcript-time">${item.time || ''}</span>
                        </div>
                        <div class="drawer-transcript-content">${item.content}</div>
                    </div>
                `).join('');
            } else {
                transcriptDiv.innerHTML = '<p style="color: #999; text-align: center;">无转写记录</p>';
            }

            // 显示抽屉
            document.getElementById('history-drawer-overlay').style.display = 'block';
            const drawer = document.getElementById('history-drawer');
            drawer.style.display = 'flex';
            setTimeout(() => drawer.classList.add('open'), 10);
        }

        function closeHistoryDrawer() {
            const drawer = document.getElementById('history-drawer');
            drawer.classList.remove('open');
            setTimeout(() => {
                drawer.style.display = 'none';
                document.getElementById('history-drawer-overlay').style.display = 'none';
            }, 300);
        }

        // 删除历史文档
        function deleteHistoryDoc(docId, event) {
            // 阻止事件冒泡，防止触发打开文档
            if (event) {
                event.stopPropagation();
            }

            if (!confirm('确定要删除这条历史记录吗？')) {
                return;
            }

            // 从历史记录中删除
            const index = docHistory.findIndex(d => d.id === docId);
            if (index !== -1) {
                docHistory.splice(index, 1);

                // 保存到 localStorage
                safeSetLocalStorage(DOC_HISTORY_KEY, JSON.stringify(docHistory), {
                    warningKind: 'history',
                    warningMessage: '历史文档缓存写入失败，可能是浏览器本地存储空间不足。'
                });

                // 重新渲染列表
                renderDocHistory();

                console.log(`历史文档 ${docId} 已删除`);
            }
        }

        // 清空所有历史记录
        function clearAllHistory() {
            if (!docHistory || docHistory.length === 0) {
                alert('当前没有历史记录');
                return;
            }

            const count = docHistory.length;
            if (!confirm(`确定要清空所有历史记录吗？\n\n共有 ${count} 条记录将被删除，此操作无法撤销。`)) {
                return;
            }

            // 清空历史记录
            docHistory = [];

            // 清空 localStorage
            safeRemoveLocalStorage(DOC_HISTORY_KEY);

            // 重新渲染列表
            renderDocHistory();

            alert('✅ 已清空所有历史记录');
        }

        // 预览历史文档
        function previewHistoryDoc() {
            if (!currentDocument) return;
            // 使用当前历史文档的内容调用预览功能
            const modal = document.getElementById('preview-modal');
            const previewDoc = document.getElementById('preview-document');

            const docTypeNames = {
                'meeting': '会议纪要与转写记录',
                'report': '出差报告',
                'publicity': '宣传报道'
            };
            const docTypeName = docTypeNames[currentDocument.docType] || '文档';

            let wordContent = `<h1>${currentDocument.title}</h1>`;
            wordContent += '<h2>一、文档内容</h2>';

            // 去除 Markdown 格式标记
            let content = removeMarkdownFormatting(currentDocument.content);
            const paragraphs = content.split('\n');
            paragraphs.forEach(para => {
                if (para.trim()) {
                    if (para.match(/^[一二三四五六七八九十、[【]/) || (para.includes('：') && para.length < 30)) {
                        wordContent += `<h3>${para}</h3>`;
                    } else {
                        wordContent += `<p>${para}</p>`;
                    }
                }
            });

            wordContent += '<div class="transcript-section">';
            wordContent += '<h2>二、详细转写记录</h2>';

            if (currentDocument.transcript) {
                currentDocument.transcript.forEach(item => {
                    wordContent += `
                        <div class="transcript-item">
                            <div>
                                <span class="transcript-speaker">${item.speaker}</span>
                                <span class="transcript-time">${item.time || ''}</span>
                            </div>
                            <div class="transcript-content">${item.content}</div>
                        </div>
                    `;
                });
            }

            wordContent += '</div>';

            previewDoc.innerHTML = wordContent;
            modal.style.display = 'flex';
        }

        // 下载历史文档
        async function downloadHistoryDoc() {
            if (!currentDocument) return;

            try {
                const response = await fetch('/api/v1/export/word', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        summary: currentDocument.content,
                        transcript: currentDocument.transcript || [],
                        doc_type: currentDocument.docType
                    })
                });

                const data = await response.json();
                if (data.download_url) {
                    const link = document.createElement('a');
                    link.href = data.download_url;
                    link.download = '';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            } catch (e) {
                alert("导出失败，请检查后端服务");
            }
        }

        // --- 下载和复制功能 ---
        async function downloadMinutes() {
            const content = document.getElementById('minutes-content').innerText;
            if (!content || content.includes('待转写') || content.includes('请稍候')) {
                alert("请先生成文档");
                return;
            }

            try {
                const response = await fetch('/api/v1/export/word', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        summary: content,
                        transcript: transcriptData,
                        doc_type: currentDocType
                    })
                });

                const data = await response.json();
                if (data.download_url) {
                    const link = document.createElement('a');
                    link.href = data.download_url;
                    link.download = '';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            } catch (e) {
                alert("导出失败，请检查后端服务");
            }
        }

        function copyMinutes() {
            const text = document.getElementById('minutes-content').innerText;
            if (!text || text.includes('待转写') || text.includes('请稍候')) {
                alert("没有可复制的内容");
                return;
            }
            navigator.clipboard.writeText(text).then(() => alert("已复制到剪贴板"));
        }

        // --- 去除 Markdown 格式标记 ---
        function removeMarkdownFormatting(text) {
            if (!text) return text;

            // 去除加粗标记 **text** 或 __text__
            text = text.replace(/\*\*(.*?)\*\*/g, '$1');
            text = text.replace(/__(.*?)__/g, '$1');

            // 去除斜体标记 *text* 或 _text_ (避免误匹配加粗后的结果)
            text = text.replace(/(?<!\*)\*(?!\*)(.*?)\*(?!\*)/g, '$1');
            text = text.replace(/(?<!_)_(?!_)(.*?)_(?!_)/g, '$1');

            // 去除删除线标记 ~~text~~
            text = text.replace(/~~(.*?)~~/g, '$1');

            // 去除行内代码标记 `text`
            text = text.replace(/`(.*?)`/g, '$1');

            // 去除链接标记 [text](url)
            text = text.replace(/\[(.*?)\]\(.*?\)/g, '$1');

            // 去除图片标记 ![alt](url)
            text = text.replace(/!\[(.*?)\]\(.*?\)/g, '$1');

            return text;
        }

        // --- 文档预览功能 ---
        function previewDocument() {
            const content = document.getElementById('minutes-content').innerText;
            if (!content || content.includes('待转写') || content.includes('请稍候')) {
                alert("请先生成文档");
                return;
            }

            const modal = document.getElementById('preview-modal');
            const previewDoc = document.getElementById('preview-document');

            // 获取文档类型名称
            const docTypeNames = {
                'meeting': '会议纪要与转写记录',
                'report': '出差报告',
                'publicity': '宣传报道'
            };
            const docTypeName = docTypeNames[currentDocType] || '文档';

            // 生成 Word 风格的预览内容
            let wordContent = '';

            // 添加主标题
            if (currentDocument && currentDocument.title) {
                wordContent += `<h1>${currentDocument.title}</h1>`;
            } else {
                wordContent += `<h1>${docTypeName}</h1>`;
            }

            // 添加文档内容部分
            wordContent += '<h2>一、文档内容</h2>';

            // 获取纯文本内容并去除 Markdown 格式标记
            const summaryElement = document.getElementById('minutes-content');
            let summaryText = summaryElement.innerText;
            summaryText = removeMarkdownFormatting(summaryText);

            // 将内容按段落分割并格式化
            const paragraphs = summaryText.split('\n');
            paragraphs.forEach(para => {
                if (para.trim()) {
                    // 检查是否是标题行（如：会议主题：、核心议题：等）
                    if (para.match(/^[一二三四五六七八九十、[【]/) || para.includes('：') && para.length < 30) {
                        wordContent += `<h3>${para}</h3>`;
                    } else {
                        wordContent += `<p>${para}</p>`;
                    }
                }
            });

            // 添加转写记录部分
            wordContent += '<div class="transcript-section">';
            wordContent += '<h2>二、详细转写记录</h2>';

            transcriptData.forEach(item => {
                wordContent += `
                    <div class="transcript-item">
                        <div>
                            <span class="transcript-speaker">${item.speaker}</span>
                            <span class="transcript-time">${item.time || ''}</span>
                        </div>
                        <div class="transcript-content">${item.content}</div>
                    </div>
                `;
            });

            wordContent += '</div>';

            previewDoc.innerHTML = wordContent;
            modal.style.display = 'flex';
        }

        function closePreviewModal() {
            document.getElementById('preview-modal').style.display = 'none';
        }

        // --- 反馈优化功能 ---
        function toggleFeedbackPanel() {
            const content = document.getElementById('feedback-content');
            const toggleBtn = document.getElementById('feedback-toggle-btn');

            if (content.style.display === 'none') {
                content.style.display = 'block';
                toggleBtn.innerText = '收起';
            } else {
                content.style.display = 'none';
                toggleBtn.innerText = '展开';
            }
        }

        // 监听单选按钮变化，显示/隐藏自定义输入框
        document.addEventListener('DOMContentLoaded', function() {
            const radioButtons = document.querySelectorAll('input[name="feedback-preset"]');
            const customInput = document.getElementById('feedback-custom-input');

            radioButtons.forEach(radio => {
                radio.addEventListener('change', function() {
                    if (this.value === 'custom') {
                        customInput.style.display = 'block';
                        customInput.focus();
                    } else {
                        customInput.style.display = 'none';
                    }
                });
            });
        });

        async function regenerateDocument() {
            // 获取选中的反馈选项
            const selectedPreset = document.querySelector('input[name="feedback-preset"]:checked');
            if (!selectedPreset) {
                alert('请选择优化选项或输入自定义要求');
                return;
            }

            const presetValue = selectedPreset.value;
            let feedbackPrompt = '';

            // 预设选项对应的提示词
            const presetPrompts = {
                'formal': '请使用更正式、更专业的商务语言风格重写文档，用词要准确、严谨，避免口语化表达。',
                'detailed': '请对文档内容进行详细展开，补充必要的背景说明、数据支撑和分析，使内容更加丰满。',
                'concise': '请精简文档内容，提炼核心要点，去除冗余表述，使文档更加简洁明了。'
            };

            if (presetValue === 'custom') {
                const customInput = document.getElementById('feedback-custom-input').value.trim();
                if (!customInput) {
                    alert('请输入您的具体要求');
                    return;
                }
                feedbackPrompt = customInput;
            } else {
                feedbackPrompt = presetPrompts[presetValue];
            }

            // 显示加载状态
            const previewDoc = document.getElementById('preview-document');
            const originalContent = previewDoc.innerHTML;
            previewDoc.innerHTML = '<div style="text-align: center; padding: 50px; color: #666;"><div style="font-size: 24px; margin-bottom: 10px;">🔄</div>正在重新生成，请稍候...</div>';

            // 禁用按钮防止重复提交
            const regenerateBtn = document.querySelector('.feedback-actions .btn-primary');
            const originalBtnText = regenerateBtn.innerHTML;
            regenerateBtn.disabled = true;
            regenerateBtn.innerHTML = '生成中...';

            try {
                const response = await fetch('/api/v1/llm/regenerate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        transcript: transcriptData,
                        doc_type: currentDocType,
                        feedback: feedbackPrompt
                    })
                });

                const data = await response.json();

                // 更新当前文档内容
                if (currentDocument) {
                    currentDocument.content = data.summary_text;
                    currentDocument.title = data.doc_title;
                }

                // 更新预览内容
                const docTypeNames = {
                    'meeting': '会议纪要与转写记录',
                    'report': '出差报告',
                    'publicity': '宣传报道'
                };
                const docTypeName = docTypeNames[currentDocType] || '文档';

                let wordContent = `<h1>${data.doc_title}</h1>`;
                wordContent += '<h2>一、文档内容</h2>';

                // 去除 Markdown 格式标记
                let content = removeMarkdownFormatting(data.summary_text);
                const paragraphs = content.split('\n');

                paragraphs.forEach(para => {
                    if (para.trim()) {
                        if (para.match(/^[一二三四五六七八九十、[【]/) || (para.includes('：') && para.length < 30)) {
                            wordContent += `<h3>${para}</h3>`;
                        } else {
                            wordContent += `<p>${para}</p>`;
                        }
                    }
                });

                wordContent += '<div class="transcript-section">';
                wordContent += '<h2>二、详细转写记录</h2>';

                transcriptData.forEach(item => {
                    wordContent += `
                        <div class="transcript-item">
                            <div>
                                <span class="transcript-speaker">${item.speaker}</span>
                                <span class="transcript-time">${item.time || ''}</span>
                            </div>
                            <div class="transcript-content">${item.content}</div>
                        </div>
                    `;
                });

                wordContent += '</div>';

                previewDoc.innerHTML = wordContent;

                // 更新右侧面板内容
                document.getElementById('minutes-content').innerHTML = `
                    <div style="background: #fdfdfe; padding: 15px; border-radius: 6px; border: 1px solid #eee;">
                        <h4 style="margin-top:0; color: var(--accent-color);">${data.doc_title}</h4>
                        <div style="white-space: pre-wrap; line-height: 1.6; font-size: 0.95rem;">${data.summary_text}</div>
                    </div>
                `;

                // 收起反馈面板
                toggleFeedbackPanel();

                alert('✅ 文档已重新生成！');

            } catch (e) {
                console.error('重新生成失败:', e);
                previewDoc.innerHTML = originalContent;
                alert('生成失败，请检查后端服务是否正常运行。');
            } finally {
                regenerateBtn.disabled = false;
                regenerateBtn.innerHTML = originalBtnText;
            }
        }

        // --- 缓存与持久化 ---
function persistCacheNow() {
            safeSetLocalStorage(CACHE_KEY, JSON.stringify(transcriptData), {
                warningKind: 'transcript',
                warningMessage: '转写缓存写入失败，可能是浏览器本地存储空间不足；页面刷新后最近结果可能无法恢复。'
            });
            updateCacheInfo();
        }

        function saveCache(options = {}) {
            const { immediate = false } = options;

            if (immediate) {
                if (cacheSaveTimer) {
                    clearTimeout(cacheSaveTimer);
                    cacheSaveTimer = null;
                }
                persistCacheNow();
                return;
            }

            if (cacheSaveTimer) return;

            cacheSaveTimer = setTimeout(() => {
                cacheSaveTimer = null;
                persistCacheNow();
            }, CACHE_SAVE_DEBOUNCE_MS);
        }

        function loadCache() {
            const cached = localStorage.getItem(CACHE_KEY);
            if (cached) {
                try {
                    const data = JSON.parse(cached);
                    if (data.length > 0) {
                        const list = document.getElementById('transcript-list');
                        list.innerHTML = '';
                        transcriptData = [];
                        lastSpeaker = null;
                        lastMessageTime = 0;
                        
                        data.forEach(d => {
                            const timeStr = d.time || new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
                            // 如果缓存的数据有 ID，使用它；否则生成新的
                            const msgId = d.id || ++messageIdCounter;
                            rememberMessageId(msgId);
                            d.id = msgId; // 确保数据有 ID

                            addMessageUI(d.speaker, d.content, timeStr, false, msgId);

                            transcriptData.push(d);
                            lastSpeaker = d.speaker;
                        });
                        rebuildSeenResultIds();
                        document.getElementById('minutes-btn').style.display = 'flex';
                    }
                } catch (error) {
                    console.error('转写缓存解析失败，已忽略损坏缓存', error);
                    safeRemoveLocalStorage(CACHE_KEY);
                    showStorageWarning('transcript', '转写缓存读取失败，已自动忽略损坏缓存。');
                }
            }
        }

        function clearTranscript() {
            const itemCount = transcriptData.length;
            const message = itemCount > 0
                ? `确定要开始新会话吗？\n\n当前会话有 ${itemCount} 条转写记录，清空后将无法恢复。`
                : "确定要开始新会话吗？";

            if (confirm(message)) {
                transcriptData = [];
                lastSpeaker = null;
                lastMessageTime = 0;
                seenResultIds = new Set();
                safeRemoveLocalStorage(CACHE_KEY);
                safeRemoveLocalStorage(AUDIO_CACHE_KEY);
                safeRemoveLocalStorage(COMP_PROCESSED_KEY);
                document.getElementById('transcript-list').innerHTML = '<div class="empty-state">等待音频输入... 请点击下方"开始录音"或"上传音频"</div>';
                document.getElementById('minutes-btn').style.display = 'none';
                document.getElementById('clear-btn').style.display = 'none';
                document.getElementById('minutes-content').innerHTML = '<div class="empty-state">待转写完成后点击生成</div>';
                document.getElementById('minutes-actions').style.display = 'none';
                document.getElementById('minutes-panel-title').innerText = 'AI 文档生成';
                updateCacheInfo();
            }
        }

        function updateCacheInfo() {
            const transcriptBytes = new Blob([JSON.stringify(transcriptData)]).size;
            const pendingAudio = localStorage.getItem(AUDIO_CACHE_KEY) || '';
            const pendingAudioBytes = pendingAudio ? new Blob([pendingAudio]).size : 0;
            const infoEl = document.getElementById('cache-info');
            if (!infoEl) return;

            const warningSuffix = Object.values(storageWarningState).some(Boolean) ? ' · 缓存受限' : '';
            infoEl.innerText = `文本 ${formatBytes(transcriptBytes)} / 音频 ${formatBytes(pendingAudioBytes)}${warningSuffix}`;
        }
