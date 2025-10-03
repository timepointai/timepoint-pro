#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# --- Configuration ---
PROJECT_DIR="claude-sandbox"
IMAGE_NAME="claude-code-dev"
COLIMA_CPU=4
# FIX: Colima expects the memory flag to be a number (GiB), not a string with 'G' suffix.
COLIMA_MEMORY="6" 

echo "=========================================================="
echo " Starting Claude Code Sandbox Setup (Colima/Docker/Node)"
echo " Project Directory: $PROJECT_DIR"
echo " Docker Image: $IMAGE_NAME"
# Note: Updated output to reflect the corrected memory value for Colima
echo " VM Specs: ${COLIMA_CPU} CPU, ${COLIMA_MEMORY} GiB RAM"
echo "=========================================================="

# 1. Check for Homebrew (The macOS package manager)
if ! command -v brew &> /dev/null
then
    echo "🚨 Homebrew not found!"
    echo "Please install Homebrew first: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi
echo "✅ Homebrew found."

# 2. Install Docker CLI and Colima
echo "⚙️ Installing docker and colima via Homebrew..."
# Using 'brew install' will automatically handle upgrades if they are outdated.
# The logs show that docker was upgraded from 20.10.21 to 28.5.0, which is fine.
brew install docker colima

# 3. Start Colima (Docker Desktop alternative)
echo "🚀 Starting Colima with specified resources..."
# Note: --memory now uses the corrected variable COLIMA_MEMORY="6"
colima start --cpu "$COLIMA_CPU" --memory "$COLIMA_MEMORY" --disk 100 --runtime docker

# Check if Docker is running and configured correctly
if docker info &> /dev/null
then
    echo "✅ Colima and Docker daemon running successfully."
else
    echo "❌ Failed to connect to Docker daemon. Please check Colima status."
    echo "Run 'colima status' for details."
    exit 1
fi

# 4. Create the Project Directory and Dev Files
echo "📁 Creating project directory: $PROJECT_DIR"
# The -p flag ensures that if the directory exists, it does not throw an error.
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# Create the Dockerfile
echo "🏗️ Writing Dockerfile..."
cat << EOF > Dockerfile
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
EOF

# Create the run.sh script
echo "▶️ Writing run.sh execution script..."
cat << EOF > run.sh
#!/bin/bash
# Starts the Docker container, mounts the current directory to /code inside the container,
# and executes the 'claude' command.

# Ensure the container runs interactively (-it), deletes itself on exit (--rm),
# and mounts the local code directory.
docker run \\
  --name claude-sandbox \\
  -it \\
  --rm \\
  -v "$(pwd):/code" \\
  $IMAGE_NAME "\$@"
EOF

chmod +x run.sh

# 5. Build the Docker Image
echo "🛠️ Building Docker image: $IMAGE_NAME..."
docker build -t "$IMAGE_NAME" .

echo "=========================================================="
echo "             🎉 Setup Complete! 🎉"
echo "=========================================================="
echo "Next Steps:"
echo "1. Navigate to the project directory:"
echo "   cd $PROJECT_DIR"
echo "2. Run the Claude Code Sandbox:"
echo "   ./run.sh"
echo ""
echo "This command will launch the container and drop you directly into the 'claude' CLI."
echo "Your current local directory is mounted to /code inside the container."
echo "You may need to provide your Anthropic API Key the first time you run 'claude'."

cd ..
