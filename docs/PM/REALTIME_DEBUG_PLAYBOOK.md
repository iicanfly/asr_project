# REALTIME_DEBUG_PLAYBOOK

## 目的

- 记录本项目在“实时转写”调试过程中已经验证有效的排查方法。
- 避免后续再次靠感觉乱猜，把问题越改越乱。
- 作为 Codex 的长期记忆文档：以后只要继续做实时转写相关开发，默认应先回看这份手册。

---

## 核心教训

### 1. 先抓证据，不要先猜

实时转写出现“慢、碎、没回写、假分段、颜色不对、静音不收尾”时，**不要先靠体感判断是 API 慢还是代码慢**。

默认排查顺序：

1. 看前端现象
2. 看后端日志
3. 看实时 trace
4. 再判断问题在：
   - 前端展示
   - 后端状态机
   - ASR 上传门控
   - ASR API 耗时
   - 回写替换逻辑

---

## 默认调试入口

### 1. 状态接口

先确认当前运行的是不是最新代码：

```bash
https://127.0.0.1:6543/api/v1/debug/status
```

重点看：

- `git_head`
- `app_js_version`
- `mode`
- `asr_model`
- `realtime_trace_count`

用途：

- 防止“代码改了，但服务没重启”
- 防止“前端 JS 改了，但浏览器还没刷新到新版本”

---

### 2. 实时 trace 接口

实时转写问题，默认优先抓：

```bash
https://127.0.0.1:6543/api/v1/debug/realtime_trace
```

重点看每条事件的：

- `ts`
- `segment_id`
- `result_type`
- `processing_reason`
- `replace_target_id`
- `result_id`

用途：

- 判断有没有真的触发 `partial / medium / high`
- 判断“没回写”到底是后端没发，还是前端没替换
- 判断“分段了”到底是后端真开新段，还是前端把同一段拆开了

---

## 前后端问题的默认分界方法

### 1. 判断“后端真分段”还是“前端假分段”

如果前端出现两条 `Speaker_1`，不要直接认定是后端分段。

先查 trace：

- 如果多条消息的 `segment_id` 一直相同：
  - 说明**后端没有真分段**
  - 问题大概率在前端替换 / 合并逻辑

- 如果 `segment_id` 真的变化了：
  - 才说明是后端新开段

这条教训已经实战验证过：

- 曾出现“没有点击停止录音却出现第二条 Speaker_1”
- 最终确认不是后端分段，而是前端在 partial 未命中 `replace_target_id` 时，没有按 `segment_id` 回退替换

---

### 2. 判断“API 慢”还是“本地逻辑慢”

如果用户感觉：

- 说完话后很久才出结果
- 停止说话后很久才黑化

不要先归咎于 ASR API。

默认先排查：

1. 静音门控是否还在持续收到 PCM
2. idle timeout 的计时基准是否正确
3. 是否被 30 秒窗口回写误当成“10 秒静音收尾”
4. 后端是否一直没有真正进入最终回写条件

已经验证过的关键教训：

- **静音超时不能基于 `last_audio_time`**
- 因为用户不说话时，前端仍可能持续上传静音 PCM
- 这会不断刷新“最后收到音频时间”
- 正确做法应基于：
  - `last_speech_time`
  - 即“最后一次真实有声活动时间”

---

## 时延问题的默认拆解方法

当用户说“很慢”时，默认把时延拆成以下层次，不要把所有慢都混成一个问题：

1. 前端采集与送包延迟
2. 后端缓冲等待与 chunk 判定延迟
3. 上传门控 / 静音门控延迟
4. ASR API 请求耗时
5. 回写触发条件延迟
6. 前端替换渲染延迟

默认原则：

- 没抓到分层证据前，不要随便改阈值
- 先确认“慢”究竟发生在哪一层

如果下一轮仍然觉得慢，应优先补更精确的耗时日志：

- 收到音频时间
- 触发 chunk 时间
- 发起 ASR 时间
- ASR 返回时间
- 发出 socket 消息时间
- 前端收到消息时间

---

## 回写问题的默认排查顺序

如果用户反馈“从来没看到回写触发”，默认按下面顺序查：

1. trace 中有没有 `medium_rewrite` / `high_rewrite`
2. 如果有：
   - 问题偏前端展示 / 替换
3. 如果没有：
   - 问题偏后端阈值 / 计时 / 状态累计

还要重点看：

- `processing_reason`
- `replace_target_id`
- `segment_id`

因为：

- 有可能后端已经发了 rewrite，但前端没替换成功
- 也可能前端确实替换了，但颜色层没更新对

---

## 颜色与文本层级问题的默认排查顺序

如果用户反馈：

- 前面已经回写好的内容又变回橙色
- 黑色部分被重新刷色
- 蓝色 / 橙色尾巴一直不收口

默认先检查：

1. 后端 payload 是否已正确拆成：
   - `stable_text`
   - `medium_text`
   - `partial_text`
2. 前端是否按三层分别渲染
3. 新 partial 到来时，是否错误把整段重新整体染色

默认原则：

- 前端不能只按整段 `text` 染色
- 必须按三层文本分别着色

---

## 真实录音样本的使用规则

### 1. 优先使用真实 `temp_audio` 录音回放

如果问题是：

- 静音过滤
- 弱语音门控
- 说完后不出字
- 长时间录音后不输出

优先用真实录音样本，而不是只靠手工口述描述。

默认样本位置：

- `temp_audio/`

用途：

- 回放真实用户刚才那一轮的录音
- 对照原文看：
  - 漏字
  - 分段
  - 语气词
  - 回写
  - 静音收尾

---

### 2. 必须把“用户原文”和“转写结果”并排对照

不能只看“有没有输出”，还要看：

- 是否漏掉后半段
- 是否出现无意义语气词
- 是否回写后反而更差
- 是否把同一段话拆碎

这条对实时转写特别重要。

---

## 前端测试的默认规则

### 1. 浏览器问题先确认是不是旧 JS

每次改完前端后，默认做：

1. 重启服务
2. 刷新网页
3. 检查 `/api/v1/debug/status` 里的 `app_js_version`

避免出现：

- 代码已经改了
- 但浏览器还是旧版本 JS

---

### 2. 重启服务由 Codex 负责

这是已经明确的协作约定：

- kill / restart 由 Codex 做
- 用户只负责刷新网页和口测反馈

所以每次前后端联调后，默认动作应是：

1. 本地 commit（如果形成有效阶段）
2. 重启服务
3. 让用户刷新网页
4. 再开始口测

---

## 内网安全检查规则

只要这轮修改碰到实时转写主链路，发布前默认检查：

1. `USE_INTRANET=True` 时
2. `config.ASR_MODE` 是否仍为内网预期
3. 是否仍走内网独立调用路径
4. 是否没有误启用外网 simplified realtime pipeline

默认可用的快速检查方式：

- 用 `USE_INTRANET=True` 启动一次 import 级验证
- 打印：
  - `config.USE_INTRANET`
  - `config.ASR_MODE`
  - `main.ENABLE_SIMPLIFIED_REALTIME_PIPELINE`
  - `main.DECIDE_REALTIME_CHUNK.__name__`

目的：

- 防止外网调试时写顺手，把内网默认链路改乱

---

## Git 与调试节奏教训

### 1. 不要在一条坏路径上连续瞎改

如果用户已经明确反馈“你改乱了”，默认动作不是继续堆 patch，而是：

1. 先停下来
2. 总结当前实现逻辑
3. 写说明文档 / 重构方案 / 实施清单
4. 再按简化方案重走

这比继续在混乱状态上叠补丁更稳。

---

### 2. 每个清晰阶段都要有本地提交

尤其是调实时转写这种容易越改越乱的链路时，默认要做到：

- 每完成一个阶段，就有一次本地 commit
- 保证随时可回滚

---

## 与中文文档相关的额外教训

- 不要通过 PowerShell 直接写中文文档
- 优先用 `apply_patch`
- 改完中文文档后默认执行：

```bash
python tools/check_doc_corruption.py
```

---

## 以后默认执行的调试流程

以后只要继续做实时转写相关任务，默认按这套流程：

1. 先确认当前服务 / JS 版本
2. 先抓 trace，不先猜
3. 先区分前端问题还是后端问题
4. 先区分计时问题还是 API 问题
5. 尽量基于真实录音样本回放验证
6. 修改后更新相关 PM 文档
7. 做本地 commit
8. 由 Codex 重启服务
9. 让用户刷新网页继续测

---

## 标准调试清单

下面这份清单用于后续“实时转写专项联调”时直接照着执行。

### A. 开始调试前

- [ ] 先确认当前任务是否属于实时转写问题
- [ ] 先回看：
  - `AGENTS.md`
  - `docs/PM/CODEX_PLAYBOOK.md`
  - `docs/PM/SESSION_SUMMARY.md`
  - `docs/PM/REALTIME_DEBUG_PLAYBOOK.md`
- [ ] 先确认当前代码是否已经本地 commit，保证后续可回滚
- [ ] 先确认服务是否需要由 Codex 重启，而不是让用户自己处理

### B. 改代码前

- [ ] 先看 `/api/v1/debug/status`
- [ ] 先看 `/api/v1/debug/realtime_trace`
- [ ] 先判断问题更像：
  - [ ] 前端展示问题
  - [ ] 后端状态机问题
  - [ ] 门控 / 静音检测问题
  - [ ] ASR API 耗时问题
  - [ ] 回写替换问题
- [ ] 如果用户已经提供真实录音，优先基于 `temp_audio/` 样本排查

### C. 改代码后

- [ ] 跑最小自动化检查
- [ ] 如果改了中文文档，跑 `python tools/check_doc_corruption.py`
- [ ] 更新受影响的 PM 文档
- [ ] 做本地 commit
- [ ] 由 Codex 重启服务
- [ ] 让用户刷新网页后继续口测

### D. 用户口测时重点观察

- [ ] 有没有假分段
- [ ] partial / medium / high 是否都触发
- [ ] 静音 10 秒后是否自动高级回写
- [ ] 黑化后继续说话，前面黑色是否保持不变
- [ ] 语气词是否明显减少
- [ ] 长时间录音后是否出现越来越慢 / 不输出

---

## 常用命令速查表

以下命令是后续调试实时转写时最常用的一组，默认优先复用，不要每次临时拼。

### 1. 查看当前服务状态

```powershell
python -c "import urllib.request, ssl; ctx=ssl._create_unverified_context(); print(urllib.request.urlopen('https://127.0.0.1:6543/api/v1/debug/status', context=ctx, timeout=10).read().decode('utf-8'))"
```

用途：

- 确认 `git_head`
- 确认 `app_js_version`
- 确认当前是不是正确模式

---

### 2. 查看实时 trace

```powershell
python -c "import urllib.request, ssl, json; ctx=ssl._create_unverified_context(); data=json.loads(urllib.request.urlopen('https://127.0.0.1:6543/api/v1/debug/realtime_trace', context=ctx, timeout=10).read().decode('utf-8')); print(data['count']); [print(e['ts'], e.get('segment_id'), e.get('result_type'), e.get('processing_reason')) for e in data['events'][-20:]]"
```

用途：

- 看最近 20 条实时事件
- 快速判断有没有触发 partial / medium / high

---

### 3. 查看服务日志尾部

```powershell
Get-Content -Path C:\Users\16010\Desktop\asr_developing_project\asr_project\temp_audio\server_stdout.log -Tail 200
```

用途：

- 看后端日志
- 看是否有异常、门控、回写触发记录

---

### 4. 重启本地服务

```powershell
$listener = Get-NetTCPConnection -LocalPort 6543 -State Listen -ErrorAction SilentlyContinue
if ($listener) { Stop-Process -Id $listener.OwningProcess -Force; Start-Sleep -Seconds 2 }
$pythonExe = 'C:\Users\16010\.conda\envs\asr\python.exe'
$workdir = 'C:\Users\16010\Desktop\asr_developing_project\asr_project'
$stdoutLog = Join-Path $workdir 'temp_audio\server_stdout.log'
$stderrLog = Join-Path $workdir 'temp_audio\server_stderr.log'
if (Test-Path $stdoutLog) { Remove-Item -LiteralPath $stdoutLog -Force }
if (Test-Path $stderrLog) { Remove-Item -LiteralPath $stderrLog -Force }
Start-Process -FilePath $pythonExe -ArgumentList 'main.py' -WorkingDirectory $workdir -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -WindowStyle Hidden | Out-Null
Start-Sleep -Seconds 5
python -c "import urllib.request, ssl; ctx=ssl._create_unverified_context(); print(urllib.request.urlopen('https://127.0.0.1:6543/api/v1/debug/status', context=ctx, timeout=10).read().decode('utf-8'))"
```

用途：

- kill 老进程
- 启动新服务
- 启动后立即验证状态

---

### 5. 内网链路快速核查

```powershell
@'
import os, subprocess
base = r'C:\Users\16010\Desktop\asr_developing_project\asr_project'
env = os.environ.copy()
env['USE_INTRANET'] = 'True'
code = "import config; import main; print('USE_INTRANET=', config.USE_INTRANET); print('ASR_MODE=', config.ASR_MODE); print('SIMPLIFIED=', main.ENABLE_SIMPLIFIED_REALTIME_PIPELINE); print('DECIDER=', main.DECIDE_REALTIME_CHUNK.__name__)"
result = subprocess.run([r'C:\Users\16010\.conda\envs\asr\python.exe', '-c', code], cwd=base, env=env, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
print('returncode=', result.returncode)
'@ | python -
```

用途：

- 发布前确认内网逻辑没被改乱

---

### 6. 最小自动化回归

```powershell
conda run --no-capture-output -n asr python -m py_compile C:\Users\16010\Desktop\asr_developing_project\asr_project\main.py
conda run --no-capture-output -n asr python -m unittest C:\Users\16010\Desktop\asr_developing_project\asr_project\tests\test_asr_service.py C:\Users\16010\Desktop\asr_developing_project\asr_project\tests\test_realtime_tiered_rewrite.py
node --check C:\Users\16010\Desktop\asr_developing_project\asr_project\static\js\app.js
```

用途：

- 快速验证主链路没语法错误
- 快速验证实时转写关键测试没回归

---

### 7. 中文文档自检

```powershell
conda run --no-capture-output -n asr python tools/check_doc_corruption.py
```

用途：

- 只要改了中文文档，默认执行

---

## 常见症状 -> 默认优先怀疑点

### 1. 用户说“没有点击停止录音却出现第二条 Speaker_1”

默认优先怀疑：

1. 前端假分段
2. `replace_target_id` 没命中
3. `segment_id` 回退替换逻辑没做好

不是先怀疑后端真分段。

### 2. 用户说“说完后很久才黑化”

默认优先怀疑：

1. 静音超时计时基准错误
2. 静音 PCM 持续刷新了计时器
3. 实际走的是 30 秒窗口高级回写，而不是 10 秒 idle 收尾

不是先怀疑 API 慢。

### 3. 用户说“前面已经回写好的内容又变橙了”

默认优先怀疑：

1. 前端按整段统一染色
2. 没按 `stable_text / medium_text / partial_text` 三层渲染

### 4. 用户说“没输出 / 输出越来越慢”

默认优先怀疑：

1. chunk 门控太严
2. 后端缓冲迟迟没到触发条件
3. 长录音状态累计逻辑有问题
4. 真实有声活动没有被正确识别

---

## 以后继续补充的方向

这份手册后续还可以继续沉淀：

- 常见日志样例与判读
- 典型 trace 模式对照
- 真实音频样本索引
- 延迟统计日志模板
- 前端颜色层 QA 截图案例

只要后续某一轮调试方法被验证“复用价值高”，默认继续补到这份手册里。
