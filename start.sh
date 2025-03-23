#!/bin/bash
uvicorn main:app --host 0.0.0.0 --port $PORT
gunicorn main:app -c gunicorn_config.py 