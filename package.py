name = "scoopz"
version = "2020.11.26.0"
requires = ["python-3", "rez-2.7+"]

# Each version of Scoop of heavily coupled with whatever its
# repository of available packages look like at the time. It
# is an informal relationship, enforced by Scoop's automatic
# update mechanism.
_buckets = {
    "main": (
        "https://github.com/ScoopInstaller/Main/archive/"
        "75e9929147b11d37f20ac80e5a346bdb83003ff9.zip"
    ),
    "versions": (
        "https://github.com/ScoopInstaller/Versions/archive/"
        "1611dcdc9cc864a3a966858542eeaf7b9d554158.zip"
    )
}

build_command = "python {root}/install.py %s" % version
build_command += " --overwrite"
build_command += " --bucket %s" % _buckets["main"]
build_command += " --bucket %s" % _buckets["versions"]

variants = [['platform-windows', 'arch-AMD64']]


def commands():
    global env
    global alias

    env.PATH.prepend("{root}/home/apps/scoop/current/bin")  # Expose scoop.ps1
    env.PYTHONPATH.prepend("{root}/python")

    alias("install", "python -u -m scoopz")

    env.SCOOP = "{root}/home"
    env.SCOOP_HOME = "{root}/home"
