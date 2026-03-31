import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ログディレクトリ・ファイル設定
root_dir = Path(__file__).resolve().parent.parent  # attendance/ をルートに
log_dir = root_dir / "logs"
log_file = log_dir / "log.log"
log_dir.mkdir(parents=True, exist_ok=True)

# ローテーション付きファイルハンドラー
rotating_handler = RotatingFileHandler(
    log_file, maxBytes=32 * 1024, backupCount=3, encoding="utf-8"
)

# ログ基本設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[rotating_handler, logging.StreamHandler()],
)

logger = logging.getLogger("main")
