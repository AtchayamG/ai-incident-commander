import { defineConfig, devices } from '@playwright/test';
import path from 'path';
import fs from 'fs';

// Ensure output directory exists before running tests
const outputDir = path.resolve(__dirname, 'output', 'playwright');
if (!fs.existsSync(outputDir)) {
  fs.mkdirSync(outputDir, { recursive: true });
}

const tempDbPath = path.join(outputDir, `temp_e2e_${process.pid}_${Date.now()}.db`);
// Convert to a clean SQLite URL format with forward slashes
const sqliteDbUrl = `sqlite:///${tempDbPath.replace(/\\/g, '/')}`;

const isWin = process.platform === 'win32';
const pythonPath = isWin ? '.venv\\Scripts\\python' : '.venv/bin/python';

export default defineConfig({
  testDir: './e2e',
  timeout: 60 * 1000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'output/playwright/report', open: 'never' }],
    ['list']
  ],
  outputDir: 'output/playwright/results',
  use: {
    baseURL: 'http://localhost:3001',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: `${pythonPath} -m uvicorn app.main:app --port 8001`,
      cwd: path.resolve(__dirname, '../../services/api'),
      port: 8001,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        DEMO_MODE: 'true',
        DEMO_ADMIN_KEY: 'demo-admin-key',
        API_PORT: '8001',
        DATABASE_URL: sqliteDbUrl,
        CORS_ORIGINS: 'http://localhost:3001',
      },
    },
    {
      command: 'pnpm exec next dev -p 3001',
      cwd: path.resolve(__dirname),
      port: 3001,
      reuseExistingServer: false,
      stdout: 'pipe',
      stderr: 'pipe',
      env: {
        PORT: '3001',
        NEXT_PUBLIC_API_URL: 'http://localhost:8001',
      },
    },
  ],
});
