# REALTIME_AUDIO_SAMPLE_MANIFEST

## 1. 目的

这份清单用于记录本地 `temp_audio/` 下可用于实时转写调参的真实录音样本，避免后续每次都重新扫目录、重新估算时长、重新回忆哪些样本可用。

## 2. 样本来源与约束

- 样本来源：网页前端点击“开始录音”后，在本地自动落盘到 `C:\Users\16010\Desktop\asr_developing_project\asr_project\temp_audio`
- 当前主要格式：`pcm`（默认按 `16kHz / mono / 16bit` 解释）
- `temp_audio/` 已被 `.gitignore` 忽略
- 原始录音样本默认不提交 Git；提交仓库的是分析工具、清单、测试代码和必要的分析结论

## 3. 当前已发现的 PCM 样本

| 文件 | 估算时长 | 备注 |
| --- | --- | --- |
| `stream_recording_20260509_194922.pcm` | 约 4.03 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260509_210233.pcm` | 约 100.16 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_050655.pcm` | 约 41.89 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_175722.pcm` | 约 50.91 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_183243.pcm` | 约 56.80 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_184803.pcm` | 约 29.18 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_185858.pcm` | 约 71.65 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_190223.pcm` | 约 49.41 秒 | 待人工归类，可直接用离线分析工具回放 |
| `stream_recording_20260510_191011.pcm` | 约 2423.36 秒 | 长时录音样本，可用于稳定性专项回归 |
| `stream_recording_20260510_195752.pcm` | 约 188.64 秒 | 中长录音样本，可用于尾静音与 stop flush 观察 |

## 4. 推荐分析命令

### 4.1 单条 PCM 录音快速分析

```powershell
python tools\analyze_realtime_audio.py --input-format pcm --pipeline simplified temp_audio\stream_recording_20260510_183243.pcm
```

### 4.2 查看关键时间线

```powershell
python tools\analyze_realtime_audio.py --input-format pcm --pipeline simplified --timeline --timeline-limit 20 temp_audio\stream_recording_20260510_183243.pcm
```

### 4.3 导出结构化 JSON 结果

```powershell
python tools\analyze_realtime_audio.py --input-format pcm --pipeline simplified --json-output temp_audio\analysis_from_pcm.json temp_audio\stream_recording_20260510_183243.pcm
```

### 4.4 批量分析多条 PCM 录音

```powershell
python tools\analyze_realtime_audio.py --input-format pcm --pipeline simplified temp_audio\stream_recording_20260510_050655.pcm temp_audio\stream_recording_20260510_175722.pcm temp_audio\stream_recording_20260510_183243.pcm
```

## 5. 当前默认观察口径

离线分析时重点观察：

- `process_count`：会被送去 ASR 的片段次数
- `drop_count`：被静音/弱语音门控丢弃的片段次数
- `speech_gate_reasons`：常规 chunk 触发时的语音门控原因
- `tail_gate_reasons`：尾静音触发路径下的门控原因
- `stop_flush_event`：停止录音后尾段是被补转写还是被丢弃
- `timeline_events`：每次 `process / drop / waiting / stop_flush` 的时间线证据

## 6. 当前结论

- 现在仓库里的离线分析工具已经可以**直接读取前端自动落盘的 PCM 真实录音**，不需要先转成 WAV
- 这些 PCM 录音可以按前端实时包粒度回放：当前离线工具默认沿用 `packet_samples=512`，等价于按约 32ms 一包重放实时录音流
- 后续静音过滤、弱语音、尾静音补刷、rewrite 时机等调参，应优先基于这批真实录音样本验证，而不是只靠合成或口头描述
