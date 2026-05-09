const { app, BrowserWindow } = require('electron');
const path = require('path');
const net = require('net');
const { spawn } = require('child_process');

let backendProcess = null;

function checkPortOpen(host, port, timeoutMs = 300) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    let done = false;

    const finish = (ok) => {
      if (done) return;
      done = true;
      try { socket.destroy(); } catch (_) {}
      resolve(ok);
    };

    socket.setTimeout(timeoutMs);
    socket.once('connect', () => finish(true));
    socket.once('timeout', () => finish(false));
    socket.once('error', () => finish(false));
    socket.connect(port, host);
  });
}

async function waitForPort(host, port, timeoutMs = 15000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const ok = await checkPortOpen(host, port, 300);
    if (ok) return true;
    await new Promise(r => setTimeout(r, 300));
  }
  return false;
}

function getBackendLaunchInfo() {
  const projectRoot = path.join(__dirname, '../../');

  if (app.isPackaged) {
    const exePath = path.join(process.resourcesPath, 'app.asar.unpacked', 'backend_dist', 'voice_backend.exe');
    return { command: exePath, args: [], cwd: process.resourcesPath };
  }

  return { command: 'python', args: ['main.py'], cwd: projectRoot };
}

async function ensureBackendRunning() {
  const host = '127.0.0.1';
  const port = 8000;

  const alreadyUp = await checkPortOpen(host, port, 300);
  if (alreadyUp) return;

  const { command, args, cwd } = getBackendLaunchInfo();
  backendProcess = spawn(command, args, {
    cwd,
    windowsHide: true,
    stdio: 'ignore',
    env: { ...process.env }
  });

  await waitForPort(host, port, 20000);
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, '../preload/preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false, // 允许访问麦克风
      webSecurity: false, // 允许跨域请求（开发环境）
    },
  });

  // 加载前端页面
  win.loadFile(path.join(__dirname, '../../index.html'));
}

app.whenReady().then(() => {
  ensureBackendRunning().finally(() => {
    createWindow();
  });

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    try { backendProcess.kill(); } catch (_) {}
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
