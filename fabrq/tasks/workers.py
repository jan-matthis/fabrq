import os
from pathlib import Path

from fabric import task as task_fabric
from invoke import run as run_invoke
from invoke import task as task_invoke

try:
    REDIS_HOST = os.environ["REDIS_HOST"]
except:
    print("Environment variables should contain REDIS_HOST")
try:
    REDIS_PORT = os.environ["REDIS_PORT"]
except:
    print("Environment variables should contain REDIS_PORT")
try:
    REDIS_PASSWORD = os.environ["REDIS_PASSWORD"]
except:
    print("Environment variables should contain REDIS_PASSWORD")
try:
    REDIS_DB = os.environ["REDIS_DB"]
except:
    print("Environment variables should contain REDIS_DB")
try:
    REDIS_URL = os.environ["REDIS_URL"]
except:
    print("Environment variables should contain REDIS_URL")


@task_fabric
def start(c, 
    queue=None,
    conda_env=None,
    num_workers=None,
    burst=False,
    tmux=True,
    ):
    assert queue is not None, "Specify queue"
    assert conda_env is not None, "Specify conda env"
    assert num_workers is not None, "Specify number of workers"

    source_bashrc = f"source ~/.bashrc"
    set_env_vars = "export MKL_NUM_THREADS=1; export NUMEXPR_NUM_THREADS=1; export OMP_NUM_THREADS=1"
    activate_venv = f"conda activate {conda_env}"

    if tmux:
        # Create session if it does not exist
        session_name = "rq_workers"
        c.run(f"tmux has-session -t {session_name} || tmux new-session -d -s {session_name}")

    for n in range(1, int(num_workers) + 1):
        worker_name = f"rq_worker_{n}_`hostname`_`whoami`_`date +%s`"
        start_rq_worker = f"rq worker {queue} --url {REDIS_URL} --name {worker_name}"
        if burst:
            start_rq_worker += " --burst"

        if tmux:
            t = f"{session_name}:{n}"
            c.run(f"tmux new-window -d -k -t {t} -n rq{n}")
            c.run(f"tmux send-keys -t {t} 'bash -l' C-m")
            c.run(f"tmux send-keys -t {t} '{source_bashrc}' C-m")
            c.run(f"tmux send-keys -t {t} '{set_env_vars}' C-m")
            c.run(f"tmux send-keys -t {t} '{activate_venv}' C-m")
            c.run(f"tmux send-keys -t {t} '{start_rq_worker}' C-m")
        else:
            screen_cmd = f"screen -S {worker_name} -d -m bash -l -c"
            cmd = f"{screen_cmd} '{source_bashrc}; {set_env_vars}; {activate_venv}; {start_rq_worker}'"
            c.run(cmd)


@task_fabric
def stop(c):
    """Run `pkill rq_worker` (local/remote)
    """
    c.run("pkill -f rq_worker_*")
