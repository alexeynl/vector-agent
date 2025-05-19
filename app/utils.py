import subprocess
import tempfile
import os

vector_bin_path = "/opt/vector/bin/vector"
gitsync_bin_path = "/opt/git-sync/bin/git-sync"
config_branch = "test-branch"
repo = "https://github.com/alexeynl/vector-configs.git"
root_vrl_path_env_name = "VECTOR_CONFIG_PATH"
env_files = ["/etc/vector/.env"]

def vector_validate_config_branch(repo, branch):
    envs = load_envs(env_files)
    print(envs)
    with tempfile.TemporaryDirectory() as tmpdirname:
        gitsync_root =  os.path.join(tmpdirname, "root")
        gitsync_link = os.path.join(tmpdirname, "configs")
        #envs = envs | {root_vrl_path_env_name: gitsync_link}
        print(envs)
        sync_result = sync_branch(repo, branch, gitsync_root, gitsync_link)
        result = {}
        status = "ok"
        if sync_result["status"] == "fail":
            status = "fail"
            result["reason"] = sync_result["reason"]
        else:
            p = subprocess.run([vector_bin_path, "validate", "-C", gitsync_link], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=envs)
            if p.returncode != 0:
                status = "fail"
                result["reason"] = "Incorrect config"
            result["output"] = p.stdout
        result["status"] = status
        return result

def vector_validate_configs(paths):
    p = subprocess.run([vector_bin_path, "validate"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if p.returncode == 0:
        print(p.stdout)
    print(p.returncode)

def sync_branch(repo, branch, gitsync_root_path, git_sync_link_path):
    #subprocess.run([gitsync_bin_path, "--repo", repo, "--ref", branch, "--root", gitsync_root_path, "--link", git_sync_link_path, "--one-time"])
    
    p = subprocess.run([gitsync_bin_path, "--repo", repo, "--ref", branch, "--root", gitsync_root_path, "--link", git_sync_link_path, "--one-time"],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        print ('new_dict',new_dict, result)
    return result

print(vector_validate_config_branch(repo, "test-branch"))