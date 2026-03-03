"""
Configuration dataclasses for the simulation monitor.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class DisplayMode(Enum):
    """Display mode for monitor output"""

    RAW = "raw"  # Show only raw subprocess output
    LLM = "llm"  # Show only LLM summaries
    BOTH = "both"  # Show both raw and LLM summaries


class OutputFormat(Enum):
    """Output format for monitor"""

    CONSOLE = "console"  # Human-readable console output
    JSON = "json"  # JSON format
    MARKDOWN = "markdown"  # Markdown format


@dataclass
class MonitorConfig:
    """Configuration for the simulation monitor"""

    # Command to monitor
    command: list[str]

    # Display settings
    display_mode: DisplayMode = DisplayMode.BOTH
    output_format: OutputFormat = OutputFormat.CONSOLE

    # LLM settings
    llm_model: str = "meta-llama/llama-3.1-8b-instruct:free"
    max_input_tokens: int = 4000
    max_output_tokens: int = 150
    update_interval: int = 300  # seconds (5 minutes)

    # Prompt configuration
    system_prompt_file: Path | None = None

    # Database inspection
    enable_db_inspection: bool = True
    metadata_db_path: Path = field(default_factory=lambda: Path("metadata/runs.db"))
    datasets_dir: Path = field(default_factory=lambda: Path("datasets"))

    # API keys
    openrouter_api_key: str | None = None

    # Auto-confirmation
    auto_confirm: bool = False

    # Interactive chat
    enable_chat: bool = False

    def __post_init__(self):
        """Validate and normalize configuration"""
        if self.system_prompt_file is None:
            self.system_prompt_file = Path(__file__).parent / "prompts" / "system_prompt.txt"

        # Ensure paths are Path objects
        if isinstance(self.system_prompt_file, str):
            self.system_prompt_file = Path(self.system_prompt_file)
        if isinstance(self.metadata_db_path, str):
            self.metadata_db_path = Path(self.metadata_db_path)
        if isinstance(self.datasets_dir, str):
            self.datasets_dir = Path(self.datasets_dir)


@dataclass
class MonitorState:
    """Current state of the monitor"""

    # Template tracking
    current_template: str | None = None
    current_run_id: str | None = None
    templates_completed: int = 0
    templates_total: int | None = None

    # Cost tracking
    total_cost_usd: float = 0.0
    llm_api_cost_usd: float = 0.0

    # Performance tracking
    start_time: float | None = None
    last_update_time: float | None = None

    # Accumulated logs since last LLM update
    log_buffer: list[str] = field(default_factory=list)

    # Status
    is_running: bool = False
    error_message: str | None = None
