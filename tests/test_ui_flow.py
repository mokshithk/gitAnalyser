import os
import time
import socket
import subprocess
import pytest
from playwright.sync_api import sync_playwright

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

def wait_for_port(port: int, timeout: int = 15) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False

@pytest.fixture(scope="module")
def running_servers():
    """Starts backend (uvicorn) and frontend (vite preview) with robust port health checking."""
    env = os.environ.copy()
    env["PYTHONPATH"] = "D:\\gitAnalyserProject"

    # Start FastAPI
    backend_proc = subprocess.Popen(
        [
            "D:\\gitAnalyserProject\\.venv\\Scripts\\python.exe",
            "-m", "uvicorn",
            "backend.main:app",
            "--host", "127.0.0.1",
            "--port", str(BACKEND_PORT)
        ],
        env=env,
    )

    # Start Vite Preview (serving built frontend)
    frontend_proc = subprocess.Popen(
        f"npm.cmd run preview -- --host 127.0.0.1 --port {FRONTEND_PORT}",
        cwd="D:\\gitAnalyserProject\\frontend",
        env=env,
        shell=True,
    )

    backend_ok = wait_for_port(BACKEND_PORT, timeout=15)
    frontend_ok = wait_for_port(FRONTEND_PORT, timeout=15)

    if not backend_ok or not frontend_ok:
        backend_proc.kill()
        frontend_proc.kill()
        raise RuntimeError(f"Servers failed to bind: backend={backend_ok}, frontend={frontend_ok}")

    yield f"http://127.0.0.1:{FRONTEND_PORT}"

    # Terminate cleanly
    try:
        subprocess.run(f"taskkill /F /T /PID {frontend_proc.pid}", shell=True, capture_output=True)
        subprocess.run(f"taskkill /F /T /PID {backend_proc.pid}", shell=True, capture_output=True)
    except Exception:
        pass

def test_full_ui_flow(running_servers):
    frontend_url = running_servers

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # 1. Navigate to frontend
        page.goto(frontend_url)
        page.wait_for_load_state("networkidle")

        # 2. Switch to Register mode
        toggle_btn = page.get_by_text("Don't have an account? Register here")
        if toggle_btn.is_visible():
            toggle_btn.click()

        # 3. Fill in registration form
        import uuid
        rand_email = f"e2e_{uuid.uuid4().hex[:6]}@student.edu"
        page.fill("input[type='email']", rand_email)
        page.fill("input[type='password']", "SecurePassword123!")
        page.click("button:has-text('Register Account')")

        # 4. Assert arrival at Dashboard
        page.wait_for_selector("text=Analysis Dashboard", timeout=8000)
        assert page.is_visible("text=Analysis Dashboard")
        assert page.is_visible(f"text={rand_email}")

        # 5. Navigate to New Analysis Page
        page.click("button:has-text('+ Start New Analysis')")
        page.wait_for_selector("text=Submit Repository for Triage Analysis", timeout=5000)
        assert page.is_visible("text=Submit Repository for Triage Analysis")

        # 6. Fill in Git URL
        page.fill("input[placeholder='https://github.com/username/project.git']", "https://github.com/mokshithk/gitAnalyser.git")
        page.click("button:has-text('Analyze Git Repository')")

        # 7. Assert arrival at Analysis Detail page
        page.wait_for_selector("text=Mandatory Human Review Disclaimer", timeout=10000)
        assert page.is_visible("text=Mandatory Human Review Disclaimer")
        assert page.is_visible("text=System Limitations & Boundary Conditions")

        browser.close()
