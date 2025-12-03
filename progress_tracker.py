"""
Progress Tracker with Colorful Console Output

Provides thread-safe progress tracking with visual feedback using colorama.
Designed for run_all_mechanism_tests.py and related simulation workflows.
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque

try:
    from colorama import Fore, Back, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    # Fallback: empty strings if colorama not available
    class FallbackColors:
        def __getattr__(self, name):
            return ""
    Fore = FallbackColors()
    Back = FallbackColors()
    Style = FallbackColors()


@dataclass
class PhaseInfo:
    """Information about a simulation phase."""
    name: str
    total_steps: int
    completed_steps: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class JobProgress:
    """Track progress of a single job/template."""
    name: str
    total_phases: int = 0
    completed_phases: int = 0
    current_phase: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    status: str = "pending"  # pending, running, success, failed
    error: Optional[str] = None


class ProgressTracker:
    """
    Thread-safe progress tracker with colorful console output.

    Usage:
        tracker = ProgressTracker(total_jobs=10)
        tracker.start_job("template_name")
        tracker.update_phase("narrative_generation", current=3, total=5)
        tracker.complete_job("template_name", success=True)
        tracker.print_status()
    """

    def __init__(self, total_jobs: int, show_eta: bool = True, update_interval: float = 30.0):
        """
        Initialize the progress tracker.

        Args:
            total_jobs: Total number of jobs/templates to run
            show_eta: Whether to calculate and show ETA
            update_interval: Minimum seconds between automatic status prints
        """
        self.total_jobs = total_jobs
        self.show_eta = show_eta
        self.update_interval = update_interval

        # Thread-safe state
        self._lock = threading.Lock()
        self._jobs: Dict[str, JobProgress] = {}
        self._completed_jobs: List[str] = []
        self._failed_jobs: List[str] = []
        self._current_job: Optional[str] = None

        # Timing for ETA
        self._start_time = time.time()
        self._job_durations: deque = deque(maxlen=10)  # Rolling average of last 10 jobs
        self._last_print_time = 0.0

        # Counters
        self._total_cost = 0.0
        self._total_tokens = 0

    def start_job(self, name: str, total_phases: int = 0):
        """Mark a job as started."""
        with self._lock:
            self._jobs[name] = JobProgress(
                name=name,
                total_phases=total_phases,
                start_time=time.time(),
                status="running"
            )
            self._current_job = name

    def update_phase(self, phase_name: str, current: int = 0, total: int = 0, job_name: Optional[str] = None):
        """Update the current phase progress."""
        with self._lock:
            job = job_name or self._current_job
            if job and job in self._jobs:
                self._jobs[job].current_phase = phase_name
                if total > 0:
                    self._jobs[job].total_phases = max(self._jobs[job].total_phases, total)
                if current > 0:
                    self._jobs[job].completed_phases = current

    def complete_job(self, name: str, success: bool = True, error: Optional[str] = None,
                     cost: float = 0.0, tokens: int = 0):
        """Mark a job as completed."""
        with self._lock:
            if name in self._jobs:
                job = self._jobs[name]
                job.end_time = time.time()
                job.status = "success" if success else "failed"
                job.error = error

                # Track duration for ETA
                if job.start_time:
                    duration = job.end_time - job.start_time
                    self._job_durations.append(duration)

                if success:
                    self._completed_jobs.append(name)
                else:
                    self._failed_jobs.append(name)

                self._total_cost += cost
                self._total_tokens += tokens

                if self._current_job == name:
                    self._current_job = None

    def add_cost(self, cost: float, tokens: int = 0):
        """Add to the running cost total."""
        with self._lock:
            self._total_cost += cost
            self._total_tokens += tokens

    def get_progress(self) -> Dict[str, Any]:
        """Get current progress state."""
        with self._lock:
            completed = len(self._completed_jobs)
            failed = len(self._failed_jobs)
            total = self.total_jobs

            # Calculate ETA
            eta_seconds = None
            if self.show_eta and self._job_durations and completed > 0:
                avg_duration = sum(self._job_durations) / len(self._job_durations)
                remaining = total - completed - failed
                eta_seconds = avg_duration * remaining

            return {
                "completed": completed,
                "failed": failed,
                "total": total,
                "percent": (completed + failed) / total * 100 if total > 0 else 0,
                "current_job": self._current_job,
                "eta_seconds": eta_seconds,
                "elapsed_seconds": time.time() - self._start_time,
                "total_cost": self._total_cost,
                "total_tokens": self._total_tokens,
            }

    def format_duration(self, seconds: float) -> str:
        """Format seconds as human-readable duration."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = seconds / 60
            return f"{mins:.1f}m"
        else:
            hours = seconds / 3600
            mins = (seconds % 3600) / 60
            return f"{hours:.0f}h {mins:.0f}m"

    def get_progress_bar(self, percent: float, width: int = 30) -> str:
        """Generate a colorful progress bar."""
        filled = int(width * percent / 100)
        empty = width - filled

        # Color based on progress
        if percent < 25:
            bar_color = Fore.RED
        elif percent < 50:
            bar_color = Fore.YELLOW
        elif percent < 75:
            bar_color = Fore.CYAN
        else:
            bar_color = Fore.GREEN

        bar = bar_color + "█" * filled + Style.DIM + "░" * empty + Style.RESET_ALL
        return f"[{bar}]"

    def format_status_line(self) -> str:
        """Format a single-line status update."""
        progress = self.get_progress()

        completed = progress["completed"]
        failed = progress["failed"]
        total = progress["total"]
        percent = progress["percent"]

        # Build the status line
        parts = []

        # Progress bar
        bar = self.get_progress_bar(percent, width=20)
        parts.append(bar)

        # Percentage with color
        if percent < 50:
            pct_color = Fore.YELLOW
        elif percent < 100:
            pct_color = Fore.CYAN
        else:
            pct_color = Fore.GREEN
        parts.append(f"{pct_color}{percent:5.1f}%{Style.RESET_ALL}")

        # Counts
        count_str = f"{Fore.GREEN}{completed}{Style.RESET_ALL}"
        if failed > 0:
            count_str += f"/{Fore.RED}{failed}{Style.RESET_ALL}"
        count_str += f"/{total}"
        parts.append(count_str)

        # Current job (truncated)
        if progress["current_job"]:
            job_name = progress["current_job"]
            if len(job_name) > 25:
                job_name = job_name[:22] + "..."
            parts.append(f"{Fore.BLUE}{job_name}{Style.RESET_ALL}")

        # ETA
        if progress["eta_seconds"] is not None:
            eta = self.format_duration(progress["eta_seconds"])
            parts.append(f"ETA: {Fore.MAGENTA}{eta}{Style.RESET_ALL}")

        # Cost
        if progress["total_cost"] > 0:
            parts.append(f"${progress['total_cost']:.2f}")

        return " | ".join(parts)

    def print_status(self, force: bool = False):
        """Print a status update if enough time has passed."""
        current_time = time.time()

        with self._lock:
            if not force and (current_time - self._last_print_time) < self.update_interval:
                return
            self._last_print_time = current_time

        status = self.format_status_line()
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n{Fore.WHITE}{Style.DIM}[{timestamp}]{Style.RESET_ALL} {status}")

    def print_header(self, title: str = "TIMEPOINT SIMULATION RUNNER"):
        """Print a colorful header."""
        width = 70
        print()
        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}{title.center(width-4)}{Style.RESET_ALL} {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{Style.DIM}Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Jobs: {self.total_jobs}{Style.RESET_ALL}")
        print()

    def print_summary(self):
        """Print a colorful summary at the end."""
        progress = self.get_progress()

        completed = progress["completed"]
        failed = progress["failed"]
        total = progress["total"]
        elapsed = progress["elapsed_seconds"]

        width = 70
        print()
        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}║{Style.RESET_ALL} {Fore.WHITE}{Style.BRIGHT}{'SIMULATION COMPLETE'.center(width-4)}{Style.RESET_ALL} {Fore.CYAN}║{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")

        # Success rate
        success_rate = (completed / total * 100) if total > 0 else 0
        if success_rate >= 90:
            rate_color = Fore.GREEN
        elif success_rate >= 70:
            rate_color = Fore.YELLOW
        else:
            rate_color = Fore.RED

        print(f"  {Fore.GREEN}✓ Completed:{Style.RESET_ALL} {completed}/{total}")
        if failed > 0:
            print(f"  {Fore.RED}✗ Failed:{Style.RESET_ALL}    {failed}/{total}")
        print(f"  {rate_color}Success Rate:{Style.RESET_ALL} {success_rate:.1f}%")
        print(f"  {Fore.WHITE}Duration:{Style.RESET_ALL}     {self.format_duration(elapsed)}")

        if progress["total_cost"] > 0:
            print(f"  {Fore.YELLOW}Total Cost:{Style.RESET_ALL}   ${progress['total_cost']:.2f}")

        if self._failed_jobs:
            print(f"\n  {Fore.RED}Failed Jobs:{Style.RESET_ALL}")
            for job in self._failed_jobs[:5]:  # Show first 5
                print(f"    - {job}")
            if len(self._failed_jobs) > 5:
                print(f"    ... and {len(self._failed_jobs) - 5} more")

        print(f"{Fore.CYAN}{'═' * width}{Style.RESET_ALL}")
        print()


class PhaseTracker:
    """
    Tracks progress within a single simulation run (phases/steps).

    Usage:
        phase = PhaseTracker("portal_timepoint_unicorn", total_steps=10)
        phase.start_phase("backward_exploration")
        phase.update(current=3, message="Processing year 2028")
        phase.complete_phase()
    """

    def __init__(self, job_name: str, total_steps: int = 0):
        self.job_name = job_name
        self.total_steps = total_steps
        self.current_step = 0
        self.current_phase = None
        self.phase_start_time = None

    def start_phase(self, phase_name: str, total_steps: int = 0):
        """Start a new phase."""
        self.current_phase = phase_name
        self.phase_start_time = time.time()
        if total_steps > 0:
            self.total_steps = total_steps
        self.current_step = 0

        phase_display = phase_name.replace("_", " ").title()
        print(f"  {Fore.BLUE}▶{Style.RESET_ALL} {phase_display}", end="")
        if total_steps > 0:
            print(f" {Style.DIM}(0/{total_steps}){Style.RESET_ALL}")
        else:
            print()

    def update(self, current: int = 0, total: int = 0, message: str = ""):
        """Update step progress within current phase."""
        if current > 0:
            self.current_step = current
        else:
            self.current_step += 1

        if total > 0:
            self.total_steps = total

        if self.total_steps > 0:
            percent = (self.current_step / self.total_steps) * 100
            bar = self._mini_bar(percent)
            step_info = f"{self.current_step}/{self.total_steps}"
        else:
            bar = ""
            step_info = str(self.current_step)

        if message:
            print(f"    {Style.DIM}{bar} {step_info}{Style.RESET_ALL} {message}")

    def _mini_bar(self, percent: float, width: int = 10) -> str:
        """Generate a small progress bar."""
        filled = int(width * percent / 100)
        empty = width - filled
        return f"[{'▓' * filled}{'░' * empty}]"

    def complete_phase(self, success: bool = True):
        """Complete the current phase."""
        if self.phase_start_time:
            duration = time.time() - self.phase_start_time
            duration_str = f"{duration:.1f}s"
        else:
            duration_str = ""

        if success:
            status = f"{Fore.GREEN}✓{Style.RESET_ALL}"
        else:
            status = f"{Fore.RED}✗{Style.RESET_ALL}"

        phase_display = self.current_phase.replace("_", " ").title() if self.current_phase else "Phase"
        print(f"  {status} {phase_display} complete {Style.DIM}({duration_str}){Style.RESET_ALL}")

        self.current_phase = None
        self.phase_start_time = None


# Convenience functions for quick status updates
def print_step_progress(step: int, total: int, message: str = "", color: str = "cyan"):
    """Print a quick step progress update."""
    colors = {
        "red": Fore.RED,
        "green": Fore.GREEN,
        "yellow": Fore.YELLOW,
        "blue": Fore.BLUE,
        "magenta": Fore.MAGENTA,
        "cyan": Fore.CYAN,
        "white": Fore.WHITE,
    }
    c = colors.get(color, Fore.CYAN)

    percent = (step / total * 100) if total > 0 else 0
    bar_width = 15
    filled = int(bar_width * percent / 100)
    empty = bar_width - filled
    bar = f"[{'█' * filled}{'░' * empty}]"

    if message:
        print(f"  {c}{bar} {step}/{total}{Style.RESET_ALL} {message}")
    else:
        print(f"  {c}{bar} {step}/{total}{Style.RESET_ALL}")


def print_success(message: str):
    """Print a success message."""
    print(f"  {Fore.GREEN}✓{Style.RESET_ALL} {message}")


def print_error(message: str):
    """Print an error message."""
    print(f"  {Fore.RED}✗{Style.RESET_ALL} {message}")


def print_warning(message: str):
    """Print a warning message."""
    print(f"  {Fore.YELLOW}⚠{Style.RESET_ALL} {message}")


def print_info(message: str):
    """Print an info message."""
    print(f"  {Fore.BLUE}ℹ{Style.RESET_ALL} {message}")
