SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
# If `python3.12` exists
if command -v python3.12 &> /dev/null; then
    exec python3.12 $SCRIPT_DIR/main.py "$@"
fi
exec python3 $SCRIPT_DIR/main.py "$@"
