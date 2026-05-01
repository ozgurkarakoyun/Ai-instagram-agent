#!/bin/sh
python -c "
import os, subprocess, sys
port = os.environ.get('PORT', '8080')
subprocess.run(['uvicorn', 'main:app', '--host', '0.0.0.0', '--port', port])
"
