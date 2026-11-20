"""Shared settings. All paths are relative to the project folder, so the
project runs the same way on any computer it is copied to."""
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

N_USERS = 5

# Attempts per session for the account owner typing their own password.
OWN_TARGETS = {1: 30, 2: 10}

# Attempts per session for typing OTHER people's passwords ("someone who knows
# the password"). Keyed by the distance between users in the list, so every
# person types 5 others' attempts per session and every password receives
# 5 attempts by others per session:
#   next user: 2, the one after: 1, then 1, then 1.
OTHERS_PLAN = {1: 2, 2: 1, 3: 1, 4: 1}
SESSIONS = (1, 2)

# Sanity limits for one password attempt.
MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 64
MAX_DWELL_MS = 2000
MAX_ATTEMPT_MS = 30000

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

        self.users_file = self.data_dir / "users.json"
        self.raw_file = self.data_dir / "raw_keystrokes.csv"
        self.features_dir = self.data_dir / "features"
        self.login_log_file = self.data_dir / "login_log.csv"
        self.thresholds_file = self.models_dir / "thresholds.json"
        self.cv_metrics_file = self.reports_dir / "cv_metrics.json"
        self.test_metrics_file = self.reports_dir / "test_metrics.json"

    def model_file(self, model_name, user_id):
        return self.models_dir / f"{model_name}_{user_id}.joblib"

    def features_file(self, user_id):
        return self.features_dir / f"{user_id}.csv"

    def ensure_dirs(self):
        for d in (self.data_dir, self.models_dir, self.figures_dir, self.features_dir):
            d.mkdir(parents=True, exist_ok=True)


def add_workspace_argument(parser):
    parser.add_argument("--workspace", default=None,
                        help='use a separate workspace folder, e.g. "sim" for simulated data')
