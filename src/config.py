"""Shared settings. All paths are relative to the project folder, so the
project runs the same way on any computer it is copied to."""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SENTENCE = "the quick brown fox jumps over the lazy dog"

ENROLLED_IDS = ["P01", "P02", "P03", "P04", "P05"]
IMPOSTOR_IDS = ["X01", "X02"]

# Recorded attempts needed per role and session.
# Impostors type in one session only; their attempts are used for testing only.
SESSION_TARGETS = {
    "enrolled": {1: 20, 2: 10},
    "impostor": {1: 10},
}

# Sanity limits for one attempt (milliseconds).
MAX_DWELL_MS = 2000
MAX_ATTEMPT_MS = 60000

RANDOM_SEED = 42


class Workspace:
    """Folders for one dataset.

    The default workspace is the project folder itself (data/, models/, reports/).
    A named workspace such as "sim" keeps simulated data in its own folder
    (sim/data, sim/models, sim/reports), so it can never mix with real data.
    """

    def __init__(self, name=None, root=None):
        if root is not None:
            self.root = Path(root)
        elif name:
            if not re.fullmatch(r"[a-z0-9_]+", name):
                raise ValueError("Workspace names may only use a-z, 0-9 and _")
            self.root = BASE_DIR / name
        else:
            self.root = BASE_DIR
        self.name = name or "main"
        self.data_dir = self.root / "data"
        self.models_dir = self.root / "models"
        self.reports_dir = self.root / "reports"
        self.figures_dir = self.reports_dir / "figures"

        self.raw_file = self.data_dir / "raw_keystrokes.csv"
        self.features_file = self.data_dir / "features.csv"
        self.features_b_file = self.data_dir / "features_set_b.csv"
        self.auth_log_file = self.data_dir / "auth_log.csv"
        self.thresholds_file = self.models_dir / "thresholds.json"
        self.cv_metrics_file = self.reports_dir / "cv_metrics.json"
        self.test_metrics_file = self.reports_dir / "test_metrics.json"

    def model_file(self, model_name):
        return self.models_dir / f"{model_name}.joblib"

    def ensure_dirs(self):
        for d in (self.data_dir, self.models_dir, self.figures_dir):
            d.mkdir(parents=True, exist_ok=True)


def add_workspace_argument(parser):
    parser.add_argument("--workspace", default=None,
                        help='use a separate workspace folder, e.g. "sim" for simulated data')
