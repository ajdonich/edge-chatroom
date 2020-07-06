#!/bin/bash

# The _pb2.py files also get generated automatically from Dockerfile
# in the repo root, with for eg: docker build -t chatroom-service .
cd .. && protoc --python_out=. `ls proto/*.proto`
