#!/bin/bash

hypercorn --workers 1 --bind 0.0.0.0:11434 api:app