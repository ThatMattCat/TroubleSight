#!/usr/bin/env python3
"""
Application Manager - Runs multiple python apps simultaneously
Cross-platform compatible(hopefully, Windows untested)
"""

import subprocess
import threading
import signal
import sys
import time
import os
import platform
from pathlib import Path
from typing import List, Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(levelname)s %(asctime)s: %(message)s',
    datefmt='%H:%M:%S'
)

class ApplicationManager:
    """Manages multiple Python applications with virtual environment support"""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.shutdown_event = threading.Event()
        self.logger = logging.getLogger('AppManager')
        self.is_windows = platform.system() == 'Windows'
        self.python_cmd = 'python' if self.is_windows else 'python3'
        self.venv_activate = self._get_venv_activate_cmd()
    
    def _get_venv_activate_cmd(self) -> str:
        """Get the correct virtual environment activation command for the platform"""
        venv_path = Path('venv')
        
        if self.is_windows:
            activate_script = venv_path / 'Scripts' / 'activate.bat'
            if activate_script.exists():
                return f'"{activate_script}" && '
            python_exe = venv_path / 'Scripts' / 'python.exe'
            if python_exe.exists():
                self.python_cmd = str(python_exe)
                return ''
        else:
            activate_script = venv_path / 'bin' / 'activate'
            if activate_script.exists():
                return f'. "{activate_script}" && '
            python_exe = venv_path / 'bin' / 'python'
            if python_exe.exists():
                self.python_cmd = str(python_exe)
                return ''
        
        self.logger.warning("Virtual environment not found, using system Python")
        return ''
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info("\nShutting down applications...")
        self.shutdown_event.set()
        self.terminate_all_processes()
        sys.exit(0)
    
    def terminate_all_processes(self):
        """Terminate all running processes"""
        for process in self.processes:
            if process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning(f"Force killing process {process.pid}")
                    process.kill()
                except Exception as e:
                    self.logger.error(f"Error terminating process: {e}")
    
    def run_application(self, name: str, working_dir: str, command: List[str]):
        """
        Run a Python application in a subprocess
        """

        logger = logging.getLogger(name) 
        self.logger.info(f"Starting {name}...")
        if self.venv_activate:
            if self.is_windows:
                cmd = f'{self.venv_activate}cd /d "{working_dir}" && {" ".join(command)}'
                shell = True
                executable = None
            else:
                cmd = f'{self.venv_activate}cd "{working_dir}" && {" ".join(command)}'
                shell = True
                executable = '/bin/bash'
        else:
            cmd = command
            shell = False
            executable = None
        
        try:
            proc_env = os.environ.copy()

            startup_info = None
            if self.is_windows and not shell:
                # Prevent console window on Windows
                startup_info = subprocess.STARTUPINFO()
                startup_info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                cmd,
                shell=shell,
                executable=executable,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                cwd=working_dir if not shell else None,
                startupinfo=startup_info,
                env=os.environ.copy()
            )
            
            self.processes.append(process)
            def read_output(pipe, prefix):
                try:
                    for line in iter(pipe.readline, ''):
                        if line and not self.shutdown_event.is_set():
                            print(f"{line.strip()}", flush=True)
                except Exception as e:
                    if not self.shutdown_event.is_set():
                        logger.error(f"Error reading output: {e}")
            
            stdout_thread = threading.Thread(
                target=read_output, 
                args=(process.stdout, 'STDOUT'),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_output, 
                args=(process.stderr, 'STDERR'),
                daemon=True
            )
            
            stdout_thread.start()
            stderr_thread.start()
            
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0 and not self.shutdown_event.is_set():
                logger.error(f"Process exited with code {process.returncode}")
        
        except Exception as e:
            logger.error(f"Failed to start: {e}")
    
    def run(self):
        """Main execution method"""
        signal.signal(signal.SIGINT, self.signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.logger.info("Starting Application Manager...")
        self.logger.info("Press Ctrl+C to stop all applications\n")
        applications = [
            {
                'name': 'Streamlit',
                'working_dir': './json2ui',
                'command': ['streamlit', 'run', 'J2UI.py']
            }#,
            # {
            #     'name': 'Other App',
            #     'working_dir': './other-app',
            #     'command': [self.python_cmd, 'main.py']
            # }
        ]
        threads = []
        for i, app in enumerate(applications):
            if not Path(app['working_dir']).exists():
                self.logger.error(f"Working directory '{app['working_dir']}' not found for {app['name']}")
                continue
            
            thread = threading.Thread(
                target=self.run_application,
                args=(app['name'], app['working_dir'], app['command']),
                daemon=True
            )
            threads.append(thread)
            thread.start()
            if i < len(applications) - 1:
                time.sleep(2)
        try:
            for thread in threads:
                thread.join()
        except KeyboardInterrupt:
            self.signal_handler(None, None)


def main():
    """Entry point"""
    manager = ApplicationManager()
    manager.run()


if __name__ == "__main__":
    main()
