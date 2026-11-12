"""Verify required HTTP behavior and restart persistence on a disposable database.
Run from the API root after migrations and seed, with DATABASE_URL set explicitly.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import httpx
from sqlalchemy import text
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db import engine

if engine.url.database not in {'lab7_verify_20261105', 'lab7_verify_20261112'}:
    raise SystemExit('HTTP verification requires the dedicated disposable database')

base = 'http://127.0.0.1:8017'

def start(log):
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8017'],
        stdout=log, stderr=log,
    )
    try:
        for _ in range(600):
            if process.poll() is not None:
                raise RuntimeError('Verification server exited before becoming ready')
            try:
                response = httpx.get(base + '/', timeout=1)
                if response.status_code == 200:
                    return process
            except httpx.ConnectError:
                pass
            time.sleep(0.1)
        raise RuntimeError('Verification server did not become ready')
    except BaseException:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.seek(0)
        print(log.read(), flush=True)
        raise

def stop(process):
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)

with tempfile.TemporaryFile(mode='w+') as log:
    process = start(log)
    original = None
    try:
        subprocess.run([sys.executable, 'try_errors.py'],
                       env={**os.environ, 'API_URL': base}, check=True)
        with httpx.Client(base_url=base) as client:
            stats = client.get('/stats/courses').json()
            assert {row['courseId']: row['enrolled'] for row in stats} == {
                'ai-integration': 3, 'modern-frontend': 2, 'backend-fastapi': 1,
                'api-design': 0, 'databases-postgresql': 0, 'web-security': 0,
            }
            original = client.get('/courses/api-design').json()['likes']
            response = client.post('/courses/api-design/like')
            assert response.status_code == 200
            assert response.json()['likes'] == original + 1
        stop(process)
        process = start(log)
        assert httpx.get(base + '/courses/api-design').json()['likes'] == original + 1
        print('Statistics including zero enrollments: PASS', flush=True)
        print('Like persists after stopping and restarting API: PASS', flush=True)
    finally:
        stop(process)
        if original is not None:
            with engine.begin() as connection:
                connection.execute(text('UPDATE courses SET likes=:likes WHERE id=:id'),
                                   {'likes': original, 'id': 'api-design'})
        engine.dispose()
print('HTTP CRITERIA PASSED; original like counter restored', flush=True)
