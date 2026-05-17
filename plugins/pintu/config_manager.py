import json
from pathlib import Path

CONFIG_PATH = Path(__file__).with_name("config.json")
DEFAULT_CONFIG = {
    "admins": ["2654278608"]
}

_config = None


def load_config():
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as file:
            config = json.load(file)
    except Exception:
        config = DEFAULT_CONFIG.copy()

    if "admins" not in config or not isinstance(config["admins"], list):
        config["admins"] = DEFAULT_CONFIG["admins"].copy()
        save_config(config)

    config["admins"] = [str(user_id) for user_id in config.get("admins", [])]
    return config


def save_config(config):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=4)


def get_config():
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_admins():
    return get_config().get("admins", [])


def is_puzzle_admin(user_id):
    return str(user_id) in [str(admin) for admin in get_admins()]


def add_admin(user_id):
    config = get_config()
    uid = str(user_id)
    if uid in config["admins"]:
        return False
    config["admins"].append(uid)
    save_config(config)
    return True


def remove_admin(user_id):
    config = get_config()
    uid = str(user_id)
    if uid not in config["admins"]:
        return False
    config["admins"].remove(uid)
    save_config(config)
    return True
