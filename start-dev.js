const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');

function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        resolve(true);
      } else {
        resolve(false);
      }
    });
    server.once('listening', () => {
      server.close();
      resolve(false);
    });
    server.listen(port, '127.0.0.1');
  });
}

function findPython() {
  const isWin = process.platform === 'win32';
  const venvPythonWin = path.join(__dirname, '.venv', 'Scripts', 'python.exe');
  const venvPythonPosix = path.join(__dirname, '.venv', 'bin', 'python');

  if (isWin && fs.existsSync(venvPythonWin)) {
    return venvPythonWin;
  }
  if (!isWin && fs.existsSync(venvPythonPosix)) {
    return venvPythonPosix;
  }
  return isWin ? 'python' : 'python3';
}

async function main() {
  console.log('\x1b[36m%s\x1b[0m', '=== Starting VendorGuard AI Development Environment ===');

  const children = [];

  const cleanup = () => {
    console.log('\n\x1b[33m%s\x1b[0m', 'Shutting down services...');
    for (const child of children) {
      if (child && !child.killed) {
        try {
          if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', child.pid, '/f', '/t'], { stdio: 'ignore' });
          } else {
            child.kill('SIGTERM');
          }
        } catch {}
      }
    }
    process.exit(0);
  };

  process.on('SIGINT', cleanup);
  process.on('SIGTERM', cleanup);

  // 1. Backend (FastAPI on Port 8000)
  const backendPortInUse = await isPortInUse(8000);
  if (backendPortInUse) {
    console.log('\x1b[32m%s\x1b[0m', '✓ Backend already running on http://127.0.0.1:8000');
  } else {
    const pythonExe = findPython();
    console.log('\x1b[34m%s\x1b[0m', `→ Launching FastAPI backend with ${pythonExe}...`);
    const backend = spawn(pythonExe, ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'], {
      cwd: __dirname,
      shell: false,
    });

    children.push(backend);

    backend.stdout.on('data', (d) => {
      process.stdout.write(`\x1b[35m[backend]\x1b[0m ${d}`);
    });
    backend.stderr.on('data', (d) => {
      process.stderr.write(`\x1b[35m[backend]\x1b[0m ${d}`);
    });
  }

  // 2. Durable Worker
  const pythonExe = findPython();
  console.log('\x1b[34m%s\x1b[0m', `→ Launching durable monitoring worker...`);
  const worker = spawn(pythonExe, ['-m', 'backend.worker'], {
    cwd: __dirname,
    shell: false,
  });
  children.push(worker);

  worker.stdout.on('data', (d) => {
    process.stdout.write(`\x1b[33m[worker]\x1b[0m ${d}`);
  });
  worker.stderr.on('data', (d) => {
    process.stderr.write(`\x1b[33m[worker]\x1b[0m ${d}`);
  });

  // 3. Frontend (Next.js on Port 3000)
  const webPortInUse = await isPortInUse(3000);
  if (webPortInUse) {
    console.log('\x1b[32m%s\x1b[0m', '✓ Next.js web application already running on http://localhost:3000');
  } else {
    console.log('\x1b[34m%s\x1b[0m', '→ Launching Next.js frontend (apps/web)...');
    const npmCmd = process.platform === 'win32' ? 'npm.cmd' : 'npm';
    const web = spawn(npmCmd, ['--prefix', 'apps/web', 'run', 'dev'], {
      cwd: __dirname,
      shell: true,
    });

    children.push(web);

    web.stdout.on('data', (d) => {
      process.stdout.write(`\x1b[36m[web]\x1b[0m ${d}`);
    });
    web.stderr.on('data', (d) => {
      process.stderr.write(`\x1b[36m[web]\x1b[0m ${d}`);
    });
  }

  console.log('\x1b[32m%s\x1b[0m', '\nVendorGuard AI is active:');
  console.log(' - Web UI:  http://localhost:3000');
  console.log(' - API Docs: http://127.0.0.1:8000/docs');
  console.log(' - API Health: http://127.0.0.1:8000/health\n');
}

main().catch(console.error);
