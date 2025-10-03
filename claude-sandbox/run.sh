#!/bin/bash
# Starts the Docker container, mounts the current directory to /code inside the container,
# and executes the 'claude' command.

# Ensure the container runs interactively (-it), deletes itself on exit (--rm),
# and mounts the local code directory.
docker run \
  --name claude-sandbox \
  -it \
  --rm \
  -v "/Users/seanmcdonald/Documents/GitHub/timepoint-daedalus/claude-sandbox:/code" \
  claude-code-dev "$@"
