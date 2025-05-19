import subprocess
import tempfile
import os
import yaml


default_vector_bin_path = "/usr/bin/vector"
default_gitsync_bin_path = "/usr/bin/git-sync"

vector_bin_path = "/opt/vector/bin/vector"
gitsync_bin_path = "/opt/git-sync/bin/git-sync"

config_branch = "test-branch"
config_subdirs = ["test"]
repo = "https://github.com/alexeynl/vector-configs.git"
root_vrl_path_env_name = "VECTOR_CONFIG_PATH"
env_files = ["/etc/vector/.env"]
ssh_key_path = ""
ssh_known_hosts_path = ""

class VectorAgent:
    def __init__(self, config_path):
        self._config_path = config_path
        self._vector_bin_path = default_vector_bin_path
        self._gitsync_bin_path = default_gitsync_bin_path
        self._load_config(config_path)
        # todo: add attribute validation
        if not hasattr(self, "_config_subdirs"):
            self._config_subdirs = []
        
    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            try:
                self._vector_bin_path = data["vector"]["bin_path"]
            except KeyError:
                pass

            try:
                self._gitsync_bin_path = data["git-sync"]["bin_path"]
            except KeyError:
                pass
            
            try:
                self._repo_url = data["vector-agent"]["repo"]["url"]
            except KeyError:
                pass

            try:
                self._ssh_key_path = data["vector-agent"]["repo"]["ssh_key_path"]
            except KeyError:
                pass

            try:
                self._ssh_known_hosts_path = data["vector-agent"]["repo"]["ssh_known_hosts_path"]
            except KeyError:
                pass

            try:
                self._env_files = data["vector-agent"]["env_files"]
            except KeyError:
                pass

            try:
                self._root_vrl_path_env_name = data["vector-agent"]["root_vrl_path_env_name"]
            except KeyError:
                pass

            try:
                self._config_subdirs = data["vector-agent"]["config_subdirs"]
            except KeyError:
                pass

    def validate_config_branch(self, branch: str):
        envs = load_envs(self._env_files)
        with tempfile.TemporaryDirectory() as tmpdirname:
            gitsync_root = os.path.join(tmpdirname, "root")
            gitsync_link = os.path.join(tmpdirname, "configs")
            envs = envs | {self._root_vrl_path_env_name: gitsync_link}
            sync_result = self._sync_branch(self._repo_url, branch, gitsync_root, gitsync_link)
            result = {}
            status = "ok"
            if sync_result["status"] == "fail":
                status = "fail"
                result["reason"] = sync_result["reason"]
            else:
                if len(self._config_subdirs) == 0:
                    cmd = [vector_bin_path, "validate", "-C", gitsync_link]
                else:
                    config_dirs_str = ",".join([os.path.join(gitsync_link, subdir) for subdir in config_subdirs])
                    cmd = [vector_bin_path, "validate", "-C", config_dirs_str]
                print("Validation command: {}".format(" ".join(cmd)))
                p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=envs)
                if p.returncode != 0:
                    status = "fail"
                    result["reason"] = "Incorrect config"
                result["output"] = p.stdout
            result["status"] = status
            return result

    def _sync_branch(self, repo_url: str, branch: str, gitsync_root_path: str, git_sync_link_path: str):
        cmd = [gitsync_bin_path, "--repo", repo_url, "--ref", branch, "--root", gitsync_root_path, "--link", git_sync_link_path, "--one-time"]
        print("Sync command: {}".format(" ".join(cmd)))
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = {}
        result_status = "ok"
        if p.returncode != 0:
            result_status = "fail"
            if "fatal: couldn't find remote ref" in p.stderr.decode("utf8"):
                result["reason"] = "branch not found"
        result["status"] = result_status
        return result

def get_envvars(env_file='.env', set_environ=True, ignore_not_found_error=False, exclude_override=()):
    """
    Set env vars from a file
    :param env_file:
    :param set_environ:
    :param ignore_not_found_error: ignore not found error
    :param exclude_override: if parameter found in this list, don't overwrite environment
    :return: list of tuples, env vars
    """
    env_vars = []
    try:

        with open(env_file) as f:
            for line in f:
                line = line.replace('\n', '')

                if not line or line.startswith('#'):
                    continue

                # Remove leading `export `
                if line.lower().startswith('export '):
                    key, value = line.replace('export ', '', 1).strip().split('=', 1)
                else:
                    try:
                        key, value = line.strip().split('=', 1)
                    except ValueError:
                        logging.error(f"envar_utils.get_envvars error parsing line: '{line}'")
                        raise

                if set_environ and key not in exclude_override:
                    os.environ[key] = value

                if key in exclude_override:
                    env_vars.append({'name': key, 'value': os.getenv(key)})
                else:
                    env_vars.append({'name': key, 'value': value})
    except FileNotFoundError:
        if not ignore_not_found_error:
            raise

    return env_vars

def load_envs(files):
    result = {}
    for file in files:
        env_list = get_envvars(file, set_environ=False, ignore_not_found_error=True) 
        new_dict = {item['name']:item['value'] for item in env_list}
        result = result | new_dict
    return result

x = VectorAgent("/mnt/d/dev/github/vector-agent/app/config.yaml")
print(x.validate_config_branch("test-branch"))