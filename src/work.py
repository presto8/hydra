import os
import yaml
from pathlib import PurePath
from src import utils
from src import hydra


class Work:
    def __init__(self, configdir: os.PathLike):
        self.configdir = self.resolve_configdir(configdir)
        self.status = utils.StatusKeeper(ephemeral_reasons="already-stored ignored")
        self.config = self.load_configfile()

    def resolve_configdir(self, configdir) -> PurePath:
        if configdir:
            path = configdir
        elif 'XDG_CONFIG_HOME' in os.environ:
            path = PurePath(os.environ['XDG_CONFIG_HOME'], 'hydra')
        else:
            path = PurePath(os.environ['HOME'], '.config', 'hydra')
        return os.path.abspath(path)

    def load_configfile(self) -> object:
        configfile = os.path.join(self.configdir, "hydra.yaml")
        with open(configfile) as f:
            y = yaml.safe_load(f.read())
        return y


def backup(work):
    jg = hydra.config_to_jobgroup(work.config)
    print(jg)


def doctor(work):
    print("TODO: doctor")


def init(work):
    print("TODO: init")


def info(work):
    print("TODO: info")


def status(work):
    print("TODO: status")


def verify(work):
    print("TODO: verify")
