import subprocess
import shutil
import tempfile
import os
import yaml
import re
import time
import sys
import logging
import platform

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)
logger.setLevel("DEBUG")

# defaults
default_vector_bin_path =  "/usr/bin/vector"
default_vector_systemd_unit = "vector.service"
default_vector_log_path = "/var/log/messages"
default_vector_embedded_config_dirs = []
default_gitsync_bin_path = "/usr/bin/git-sync"
default_synced_config_dir =     "01-synced"
default_hold_config_dir =       "02-hold"
default_valid_config_dir =      "03-valid"
default_active_config_dir =     "04-active"
default_vector_reload_timeout = 60*2 #2 minutes
default_vector_configs_workdir = "/opt/vector-agent/vector-confdir"
default_apply_rules_config_name = "apply-rules.yaml"

class VectorAgent:
    def __init__(self, config_path):

        # init values
        self._config_path = config_path
        self._status = "inactive"
        self._vector_configs_workdir = default_vector_configs_workdir
        self._vector_bin_path = default_vector_bin_path
        self._vector_systemd_unit = default_vector_systemd_unit
        self._vector_log_path = default_vector_log_path
        self._vector_embedded_config_dirs = default_vector_embedded_config_dirs
        self._gitsync_bin_path = default_gitsync_bin_path
        self._vector_reload_timeout = default_vector_reload_timeout
        self._apply_rules_config_name = default_apply_rules_config_name
        self._vector_config_root_dir = None
        self._vector_config_subdir_patterns = None
        self._vector_service_status = None
        self._synced_git_branch = ""
        self._active_git_branch = ""
        self._synced_config_hash = ""
        self._active_config_hash = ""
        self._apply_status = ""
        self._gitsync_env_files = []
        self._repo_use_gitsync_settings = False

        # load values from Agent config
        self._load_config(config_path)

        self._synced_config_path = os.path.join(self._vector_configs_workdir, default_synced_config_dir)
        self._hold_config_path = os.path.join(self._vector_configs_workdir, default_hold_config_dir)
        self._valid_config_path = os.path.join(self._vector_configs_workdir, default_valid_config_dir)
        self._active_config_path = os.path.join(self._vector_configs_workdir, default_active_config_dir)
        self._apply_rules_config_path = os.path.join(self._synced_config_path, self._apply_rules_config_name)

        # load value from git-sync env file
        if self._repo_use_gitsync_settings:
            if self._gitsync_env_files and len(self._gitsync_env_files) > 0:
                logger.debug("Loading repo setting from git sync env")
                self._load_repo_gitsync_settings(self._gitsync_env_files)
            else:
                logger.error("Could not load repo setting. gitsync env file paths has not been set")

        # todo: add all attributes validation
        if not hasattr(self, "_config_subdirs"):
            self._config_subdirs = []
        if not os.path.isfile(self._output_env_file):
            # try to create env file
            open(self._output_env_file, 'a').close()

        logger.debug("Inited Vector Agent with the following values:")
        logger.debug("_vector_configs_workdir = {}".format(self._vector_configs_workdir))
        logger.debug("_vector_embedded_confi_dirs = {}".format(self._vector_embedded_config_dirs))
        logger.debug("_synced_config_path = {}".format(self._synced_config_path))
        logger.debug("_hold_config_path = {}".format(self._hold_config_path))
        logger.debug("_valid_config_path = {}".format(self._valid_config_path))
        logger.debug("_active_config_path = {}".format(self._active_config_path))
        logger.debug("_vector_bin_path = {}".format(self._vector_bin_path))
        logger.debug("_gitsync_bin_path = {}".format(self._gitsync_bin_path))
        logger.debug("_vector_reload_timeout = {}".format(self._vector_reload_timeout))
        logger.debug("_vector_log_path = {}".format(self._vector_bin_path))
        logger.debug("_apply_rules_config_name = {}".format(self._apply_rules_config_name))
        logger.debug("_apply_rules_config_path = {}".format(self._apply_rules_config_path))
        logger.debug("_vector_config_root_dir = {}".format(self._vector_config_root_dir))
        logger.debug("_vector_config_subdir_patterns = {}".format(self._vector_config_subdir_patterns))
        logger.debug("_vector_service_status = {}".format(self._vector_service_status))
        logger.debug("_input_env_files = {}".format(self._input_env_files))
        logger.debug("_synced_git_branch = {}".format(self._synced_git_branch))
        logger.debug("_active_git_branch = {}".format(self._active_git_branch))
        logger.debug("_synced_config_hash = {}".format(self._synced_config_hash))
        logger.debug("_active_config_hash = {}".format(self._active_config_hash))
        logger.debug("_apply_status = {}".format(self._apply_status))
        logger.debug("_output_env_file = {}".format(self._output_env_file))
        logger.debug("_gitsync_env_files = {}".format(self._gitsync_env_files))
        logger.debug("_repo_use_gitsync_settings = {}".format(self._repo_use_gitsync_settings))
        logger.debug("_ssh_key_path = {}".format(self._ssh_key_path))
        logger.debug("_ssh_known_hosts_path = {}".format(self._ssh_known_hosts_path))
        logger.debug("_repo_url = {}".format(self._repo_url))
        
    def _load_config(self, config_path: str):
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
            try:
                self._vector_bin_path = data["vector"]["bin_path"]
            except KeyError:
                pass

            try:
                self._vector_systemd_unit = data["vector"]["systemd_unit"]
            except KeyError:
                pass

            try:
                self._vector_log_path = data["vector"]["log_path"]
            except KeyError:
                pass

            try:
                self._vector_embedded_config_dirs = data["vector"]["embedded_config_dirs"]
            except KeyError:
                pass

            try:
                self._gitsync_bin_path = data["git-sync"]["bin_path"]
            except KeyError:
                pass

            try:
                self._gitsync_env_files = data["git-sync"]["env_files"]
            except KeyError:
                pass

            try:
                self._vector_configs_workdir = data["vector-agent"]["configs_workdir"]
            except KeyError:
                pass

            try:
                self._repo_use_gitsync_settings = data["vector-agent"]["repo"]["use_gitsync_settings"]
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
                self._input_env_files = data["vector-agent"]["env_files"]["input"]
            except KeyError:
                pass

            try:
                self._output_env_file = data["vector-agent"]["env_files"]["output"]
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

    def _load_repo_gitsync_settings(self, env_paths: list):
        vars_dict = {}
        for env_path in env_paths:
            with open(env_path, 'r') as fh:
                vars_dict = vars_dict | dict(
                    tuple(line.replace('\n', '').split('='))
                    for line in fh.readlines() if not line.startswith('#')
                )
        self._ssh_key_path = vars_dict["GITSYNC_SSH_KEY_FILE"]
        self._ssh_known_hosts_path = vars_dict["GITSYNC_SSH_KNOWN_HOSTS_FILE"]
        self._repo_url = vars_dict["GITSYNC_REPO"]

    def validate_config_branch(self, branch: str):
        with tempfile.TemporaryDirectory() as tmpdirname:
            gitsync_root = os.path.join(tmpdirname, "root")
            gitsync_link = os.path.join(tmpdirname, "configs")
            logger.debug("Starting to sync config from branch {} to directory {}".format(branch, gitsync_link))
            sync_result = self._sync_branch(self._repo_url, branch, gitsync_root, gitsync_link)
            logger.debug("Sync status: ".format(sync_result["status"]))
            result = {}
            if sync_result["status"] == "fail":
                result["status"] = "fail"
                result["reason"] = sync_result["reason"]
            else:
                result = self.validate_config(gitsync_link)
            return result

    def _sync_branch(self, repo_url: str, branch: str, gitsync_root_path: str, git_sync_link_path: str):
        cmd = [self._gitsync_bin_path, "--repo", repo_url, "--ref", branch, "--root", gitsync_root_path, "--link", git_sync_link_path, "--one-time"]
        if "@git" in repo_url or repo_url.startswith("ssh://"):
            logger.debug("SSH protocol used for repo")
            cmd.extend(["--ssh-key-file", self._ssh_key_path, "--ssh-known-hosts-file", self._ssh_known_hosts_path])
        else:
            logger.debug("No SSH protocol used for repo")
        logger.debug("Sync command: {}".format(" ".join(cmd)))
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result = {}
        result_status = "ok"
        if p.returncode != 0:
            logger.error("Repo one time sync ends with error. stderr:{}".format(p.stderr.decode("utf8")))
            result_status = "fail"
            if "fatal: couldn't find remote ref" in p.stderr.decode("utf8"):
                result["reason"] = "branch not found"
        result["status"] = result_status
        return result
    
    def _extract_config_specs(self, apply_rules_config_path: str, hostname: str):
        logger.debug("Config specs extraction from rule file {} for host {}".format(apply_rules_config_path, hostname))
        config_specs = {}
        with open(apply_rules_config_path, 'r') as f:
            data = yaml.safe_load(f)
            rules = data["rules"]
            host_config_specs = None
            for rule_name, rule in rules.items():
                for host_pattern in rule["host_patterns"]:
                    if re.match(host_pattern, hostname):
                        logger.debug("Matched rule {} found for host {}".format(rule_name, hostname))
                        host_config_specs = {}
                        try:
                            root_dir = rule["root_dir"]
                        except KeyError:
                            root_dir = "."
                        try:
                            dir_patterns = rule["includes"]
                            subdir_patterns_list = []
                            for dir_pattern in dir_patterns:
                                subdir_patterns_list.append(dir_pattern)
                        except KeyError:
                            subdir_patterns_list = []
                        host_config_specs["root_dir"] = root_dir
                        host_config_specs["subdir_patterns"] = subdir_patterns_list
        return host_config_specs
    
    def _apply_config_specs(self, apply_rules_config_path: str, hostname: str, config_path: str):
        config_specs = self._extract_config_specs(apply_rules_config_path, hostname)
        logger.debug("Extracted config specs: {}".format(config_specs))
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        if config_specs == None:
            logger.info("No config specs found for current host")
            logger.debug("Change Vector status to stop_pending")
            self._vector_service_status = "stop_pending"
            logger.debug("Remove previous specs from Agent config")
            data["vector-agent"].pop("config_root_dir", None)
            data["vector-agent"].pop("config_subdir_patterns", None)
            self._vector_config_root_dir = None
            self._vector_config_subdir_patterns = None
        else:
            logger.debug("Add new specs {} to Agent config".format(config_specs))
            data["vector-agent"]["config_root_dir"] = config_specs["root_dir"]
            data["vector-agent"]["config_subdir_patterns"] = config_specs["subdir_patterns"]
            self._vector_config_root_dir = config_specs["root_dir"]
            self._vector_config_subdir_patterns = config_specs["subdir_patterns"]
            if len(self._vector_embedded_config_dirs) > 0:
                config_env_var = "VECTOR_CONFIG_DIR=" + ",".join(self._vector_embedded_config_dirs)
            else:
                config_env_var = "VECTOR_CONFIG_DIR="
            if len(self._vector_config_subdir_patterns) > 0:
                config_env_var = config_env_var + "," + ",".join([os.path.join(self._active_config_path, subdir_pattern) for subdir_pattern in self._vector_config_subdir_patterns])
            else:
                config_env_var = config_env_var + "," + os.path.join(self._active_config_path, "**")
            logger.debug("Saving env variable {} to env file: {}".format(config_env_var, self._output_env_file))
            with open(self._output_env_file, "r") as f:
                env_data = f.readlines()
            found = False
            for i, line in enumerate(env_data):
                if line.startswith("VECTOR_CONFIG_DIR"):
                    logger.debug("Found line {} start with VECTOR_CONFIG_DIR".format(line))
                    env_data[i] = config_env_var + "\n"
                    logger.debug("Line replaced with value {}".format(config_env_var))
                    found = True
                    break
            if not found:
                logger.debug("Not found line started with VECTOR_CONFIG_DIR, append new line: {}".format(config_env_var))
                if not env_data[-1].endswith("\n"):
                    logger.debug("Last line of env file {} not ends with new line, adding new line".format(self._output_env_file))
                    env_data[-1] = env_data[-1] + "\n"
                env_data.append(config_env_var + "\n")
            logger.debug("Write content {} to file {}".format(env_data, self._output_env_file))
            with open(self._output_env_file, "w") as f:
                f.writelines(env_data)
            if set(self._config_subdirs) == set(config_specs):
                if self._vector_service_status == "running":
                    self._vector_service_status = "restart_pending"
            
        logger.debug("Write content of new Agent config: {}".format(data))
        with open(config_path, 'w') as f:
            yaml.dump(data, f)

    def _get_host_name(self):
        hostname = platform.node()
        logger.debug("Host name is:{}".format(hostname))
        return hostname

    def apply_config_specs(self):
        self._apply_config_specs(self._apply_rules_config_path, self._get_host_name(), self._config_path)

    def _refresh_vector_service_status(self):
        p = subprocess.run(["systemctl", "is-active", "--quiet", self._vector_systemd_unit])
        if p.returncode == 0:
            if self._vector_service_status != "restart_pending" and self._vector_service_status != "stop_pending":
                self._vector_service_status = "running"
        else:
            self._vector_service_status = "stopped"

    def validate_config(self, config_path: str):
        result = {}
        status = "ok"
        envs = load_envs(self._input_env_files)
        envs = envs | os.environ
        envs = envs | {self._root_vrl_path_env_name: config_path}
        if len(self._vector_config_subdir_patterns) == 0:
            cmd = [self._vector_bin_path, "validate", "-C", os.path.join(config_path, "**")]
        else:
            config_dirs_str = ",".join([os.path.join(config_path, subdir) for subdir in self._vector_config_subdir_patterns])
            cmd = [self._vector_bin_path, "validate", "-C", config_dirs_str]
        logger.info("Running validation command: {}".format(" ".join(cmd)))
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=envs)
        for line in p.stdout.splitlines():
            logger.info("vector stdout: {}".format(line.decode(encoding="utf8")))
        for line in p.stderr.splitlines():
            logger.error("vector stderr: {}".format(line.decode(encoding="utf8")))
        if p.returncode != 0:
            status = "fail"
            result["reason"] = "Incorrect config"
            result["output"] = p.stdout
        result["status"] = status
        return result

    def apply_config(self, config_path: str):
        pass

    def _get_synced_branch(self):
        branch = "master"
        logger.debug("Searching for GITSYNC_REF in {}".format(self._gitsync_env_files))
        for path in self._gitsync_env_files:
            with open(path, "r") as f:
                data = f.readlines()
                for line in data:
                    if line.startswith("GITSYNC_REF"):
                        parts = line.split("=")
                        if len(parts) > 1:
                            branch = parts[1].rstrip()
        return branch
    
    def _get_synced_hash(self):
        return os.path.basename(os.path.realpath(self._synced_config_path))

    def apply_synced_config(self):
        logger.info("Starting to apply synced config")
        target_hash = self._get_synced_hash()
        self._synced_config_hash = target_hash
        target_branch = self._get_synced_branch()
        self._synced_git_branch = target_branch
        logger.info("Target branch: {}, target hash: {}".format(target_branch, target_hash))
        logger.debug("Active branch: {}, active hash: {}".format(self._active_git_branch, self._active_config_hash))
        if target_hash == self._active_config_hash:
            logger.info("Target hash is the same as active. No action needed.")
            return 0

        logger.debug("Executing apply_config_specs()")
        self.apply_config_specs()
        logger.debug("Vector config root dir and vector config subdir patterns applied".format(self._vector_config_root_dir, self._vector_config_subdir_patterns))
        if self._vector_config_root_dir == None and self._vector_config_subdir_patterns == None:
            logger.info("No specs found for current host")
            if self._vector_service_status != "stopped":
                logger.info("Stopping vector")
                p = subprocess.run(["systemctl", "stop", "--quiet", self._vector_systemd_unit])
                if p.returncode == 0:
                    logger.info("Vector successfully stopped")
                else:
                    logger.info("Could not stop Vector service")
        else:
            self._apply_status = "in_progress"
            logger.info("Synced config path: {}".format(self._synced_config_path))
            config_root_dir = self._vector_config_root_dir
            logger.info("Make a copy of config (snapshot), snapshot name is synced config hash {}".format(target_hash))
            # /opt/vector-agent/vector-confdir/290348a80a8f8d0074bu233
            hold_snapshot_path = os.path.join(self._hold_config_path, target_hash)
            shutil.copytree(self._synced_config_path, hold_snapshot_path)
            snapshot_current_path = hold_snapshot_path
            config_to_validate_path = snapshot_current_path
            if config_root_dir:
                # # /opt/vector-agent/vector-confdir/290348a80a8f8d0074bu233/collector-01
                config_to_validate_path = os.path.join(snapshot_current_path, config_root_dir)
            self._apply_status = "validation"
            validation_result = self.validate_config(config_to_validate_path)
            if validation_result["status"] == "ok":
                logger.info("Config validation success")
                valid_snapshot_path = os.path.join(self._valid_config_path, target_hash)
                logger.debug("Moving validated snapshot to validated dir: {}".format(valid_snapshot_path))
                shutil.move(snapshot_current_path, valid_snapshot_path)
                snapshot_current_path = valid_snapshot_path
                logger.debug("Snapshot current path:".format(snapshot_current_path))
                logger.info("Checking if vector service is running")
                self._refresh_vector_service_status()
                logger.debug("Vector status is: {}".format(self._vector_service_status))
                self._apply_status = "applying"
                if self._vector_service_status == "running":
                    logger.info("Vector service is running, trying to apply config")
                    logger.info("Make a backup of current active config")
                    current_active_config_path = os.path.realpath(self._active_config_path)
                    #current_active_config_backup_path = current_active_config_path + "_" + "backup"
                    #logger.debug("Copy files from {} to {}".format(current_active_config_path, current_active_config_backup_path))
                    #shutil.copytree(current_active_config_path, current_active_config_backup_path)
                    # replace symlink
                    tmp_symlink = self._active_config_path + target_hash
                    os.symlink(snapshot_current_path, tmp_symlink, target_is_directory=False)
                    os.rename(tmp_symlink, self._active_config_path)
                    # remove original current active config, keep only backup

                    logger.debug("Wait for \"Vector has reloaded\" in Vector log")
                    timeout = time.time() + self._vector_reload_timeout
                    vector_reload_success = False
                    logger.info("Reload Vector service to trigger config reloading")
                    p = subprocess.run(["systemctl", "reload", "--quiet", self._vector_systemd_unit])
                    with open(self._vector_log_path, "r") as f:
                        lines = follow(f, self._vector_reload_timeout)
                        while (line := next(lines, None)) is not None:
                            #logger.debug("Time: {}".format(time.time()))
                            if "Vector has reloaded" in line:
                                vector_reload_success = True
                                break
                    if vector_reload_success:
                        logger.info("Successed to apply new config to running Vector")
                        #logger.debug("Remove backup of old config {}".format(current_active_config_backup_path))
                        logger.debug("Remove old config {}".format(current_active_config_path))
                        shutil.rmtree(current_active_config_path)
                        self._active_git_branch = target_branch
                        self._active_config_hash = target_hash
                        self._apply_status = "successed"
                        logger.info("Finished to apply synced config")
                        return 0
                    else:
                        logger.error("Failed to apply new config to running Vector")
                        logger.info("Restoring current active config")
                        #os.rename(current_active_config_path + "_" + "backup", current_active_config_path)
                        # revert back symlink to current active config
                        tmp_symlink = self._active_config_path + "_" + self._active_config_hash
                        os.symlink(current_active_config_path, tmp_symlink, target_is_directory=False)
                        os.rename(tmp_symlink, self._active_config_path)
                        logger.debug("Removing snapshot dir")
                        shutil.rmtree(snapshot_current_path)
                        logger.info("Finished to apply synced config")
                        self._apply_status = "failed"
                        return 1
                else:
                    logger.info("Make validated snapshot as active")
                    if self._vector_config_root_dir == ".":
                        symlink_source_path = snapshot_current_path
                    else:
                        symlink_source_path = os.path.join(snapshot_current_path, self._vector_config_root_dir)
                    logger.debug("Creating symlink from {} to {}".format(symlink_source_path, self._active_config_path))
                    os.symlink(symlink_source_path, self._active_config_path, target_is_directory=False)
                    logger.info("Trying to start Vector service")
                    p = subprocess.run(["systemctl", "start", "--quiet", self._vector_systemd_unit])
                    if p.returncode == 0:
                        logger.info("Vector successfully started")
                        self._active_git_branch = target_branch
                        self._active_config_hash = target_hash
                        self._apply_status = "successed"
                        logger.info("Finished to apply synced config")
                        return 0
                    else:
                        logger.error("Vector failed to start")
                        self._apply_status = "failed"
                        logger.info("Finished to apply synced config")
                        return 1
            else:
                logger.info("Config validation failed")
                logger.info("vector validate output: {}".format(validation_result["output"]))
                logger.debug("Removing snapshor from dir: {}".format(snapshot_current_path))
                shutil.rmtree(snapshot_current_path)
                self._apply_status = "failed"
                logger.info("Finished to apply synced config")
                return 1

    def get_status(self):
        result = {}
        result["synced_git_branch"] = self._synced_git_branch
        result["active_git_branch"] = self._active_git_branch
        result["synced_hash"] = self._synced_config_hash
        result["active_hash"] = self._active_config_hash
        result["apply_status"] = self._apply_status
        status_messages = []

        vector_running_latest_config = False
        if self._active_config_hash == self._synced_config_hash:
            vector_running_latest_config = True
        else:
            status_messages.append("Vector not running latest config")

        vector_service_running = False
        if get_systemd_service_status(self._vector_systemd_unit) == "running":
            vector_service_running = True
        else:
            status_messages.append("Vector systemd service is not running")
        
        if not vector_running_latest_config or not vector_service_running:
            status = "fail"
        else:
            status = "ok"
            status_messages = ["Everything OK"]
        
        result["status"] = status
        result["message"] = "|".join(status_messages)

        return result

def get_systemd_service_status(unit: str):
        cmd = ["systemctl", "is-active", "--quiet", unit]
        logging.debug("Running command to check systemd service {} status: {}".format(unit, " ".join(cmd)))
        p = subprocess.run(["systemctl", "is-active", "--quiet", unit])
        if p.returncode == 0:
            result = "running"
        else:
            result = "stopped"
        logging.debug("Systemd service {} status is {}".format(unit, result))
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

def follow(thefile, timeout_sec):
    stop_time = time.time() + timeout_sec
    thefile.seek(0,2) # Go to the end of the file
    while time.time() < stop_time:
        line = thefile.readline()
        if not line:
            time.sleep(0.1) # Sleep briefly
            continue
        yield line

#x = VectorAgent("/mnt/d/dev/github/vector-agent/app/config.yaml")
#x.apply_synced_config()
