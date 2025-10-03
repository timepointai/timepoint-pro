# Use a Node.js image as the base, as claude code is an npm package
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /code

# Install the official Anthropic Claude Code CLI globally
# The 'claude' executable will be available in the container's PATH
RUN npm install -g @anthropic-ai/claude-code

# Set a non-root user for security (optional but recommended)
RUN adduser -D appuser
USER appuser

# Set the entrypoint to the claude CLI
ENTRYPOINT ["claude"]

# When the user runs the container, they will be dropped into the claude tool.
# This ensures that any changes made within the container are immediately visible 
# to the 'claude' agent, and that 'claude' can interact with the mounted volume.
