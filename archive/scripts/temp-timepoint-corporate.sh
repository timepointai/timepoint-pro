#!/bin/bash
python3.10 -m monitoring.monitor_runner --mode both --enable-chat --auto-confirm --interval 300 --llm-model meta-llama/llama-3.1-70b-instruct --max-output-tokens 300 -- python3.10 run_all_mechanism_tests.py --portal-timepoint-all
