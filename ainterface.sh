SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
exec python $SCRIPT_DIR/main.py "$@"
