[![GitHub release](https://img.shields.io/github/v/release/elesiuta/picosnitch?color=00a0a0)](https://github.com/elesiuta/picosnitch/releases)
[![PyPI release](https://img.shields.io/pypi/v/picosnitch?color=00a0a0)](https://pypi.org/project/picosnitch)
[![AUR release](https://img.shields.io/aur/version/picosnitch?color=00a0a0)](https://aur.archlinux.org/packages/picosnitch/)
[![Copr release](https://img.shields.io/badge/dynamic/json?color=00a0a0&label=copr&query=builds.latest.source_package.version&url=https%3A%2F%2Fcopr.fedorainfracloud.org%2Fapi_3%2Fpackage%3Fownername%3Delesiuta%26projectname%3Dpicosnitch%26packagename%3Dpicosnitch%26with_latest_build%3DTrue)](https://copr.fedorainfracloud.org/coprs/elesiuta/picosnitch/)
[![OBS package build status](https://img.shields.io/obs/home:elesiuta/picosnitch/Debian_Unstable/x86_64?color=00a0a0&label=open%20build%20service)](https://build.opensuse.org/package/show/home:elesiuta/picosnitch)
[![GitHub commits since latest release](https://img.shields.io/github/commits-since/elesiuta/picosnitch/latest/master?color=00a0a0)](https://github.com/elesiuta/picosnitch/commits/master)
[![GitHub contributors](https://img.shields.io/github/contributors/elesiuta/picosnitch?color=00a0a0)](https://github.com/elesiuta/picosnitch/graphs/contributors)
[![Source size](https://img.shields.io/github/size/elesiuta/picosnitch/picosnitch.py?color=00a0a0)](https://github.com/elesiuta/picosnitch/blob/master/picosnitch.py)

![screenshot.png](https://raw.githubusercontent.com/elesiuta/picosnitch/master/docs/screenshot.png)

# [picosnitch](https://elesiuta.github.io/picosnitch/)
- 🔔 Receive notifications whenever a new program connects to the network, or when it's modified
- 📈 Monitors your bandwidth, breaking down traffic by executable, hash, parent, domain, port, or user over time
- 🛡️ Can optionally check hashes or executables using [VirusTotal](https://www.virustotal.com)
- 🚀 Executable hashes are cached based on device + inode for improved performance, and works with applications running inside containers
- 🕵️ Uses BPF [for accurate, low overhead bandwidth monitoring](https://www.gcardone.net/2020-07-31-per-process-bandwidth-monitoring-on-Linux-with-bpftrace/) and [fanotify](https://man7.org/linux/man-pages/man7/fanotify.7.html) to watch executables for modification
- 👨‍👦 Since applications can call others to send/receive data for them, the parent executable and hash is also logged for each connection
- 🧰 Pragmatic and minimalist design focussing on [accurate detection with clear error reporting when it isn't possible](#limitations)

# [installation](#installation)

### [AUR](https://aur.archlinux.org/packages/picosnitch/) for Arch and derivatives <img src="https://cdn.simpleicons.org/archlinux" width="16" height="16">
<details><summary>Details</summary>

- install `picosnitch` [manually](https://wiki.archlinux.org/title/Arch_User_Repository#Installing_and_upgrading_packages) or using your preferred [AUR helper](https://wiki.archlinux.org/title/AUR_helpers)
</details>

### [PPA](https://launchpad.net/~elesiuta/+archive/ubuntu/picosnitch) for Ubuntu and derivatives <img src="https://cdn.simpleicons.org/ubuntu" width="16" height="16">
<details><summary>Details</summary>

- `sudo add-apt-repository ppa:elesiuta/picosnitch`
- `sudo apt update`
- `sudo apt install picosnitch`
- install extra dependencies for dash using [pip](https://pip.pypa.io/) (optional): [dash](https://pypi.org/project/dash/), [pandas](https://pypi.org/project/pandas/), and [plotly](https://pypi.org/project/plotly/)
  - `sudo apt install python3-pip`
  - `pip3 install dash pandas plotly --user`
- you will likely require a newer version of [BCC](https://github.com/iovisor/bcc/blob/master/INSTALL.md#ubuntu---binary) ([unofficial PPA](https://launchpad.net/~hadret/+archive/ubuntu/bpfcc)) since the version in the [Ubuntu repos](https://repology.org/project/bcc-bpf/versions) lags behind its [supported kernel](https://github.com/iovisor/bcc/releases)
</details>

### [OBS](https://software.opensuse.org//download.html?project=home%3Aelesiuta&package=picosnitch) for Debian and derivatives <img src="https://cdn.simpleicons.org/debian" width="16" height="16">
<details><summary>Details</summary>

- visit the [OBS picosnitch page](https://software.opensuse.org//download.html?project=home%3Aelesiuta&package=picosnitch) and follow the instructions for your distribution
- install extra dependencies for dash using [pip](https://pip.pypa.io/) (optional): [dash](https://pypi.org/project/dash/), [pandas](https://pypi.org/project/pandas/), and [plotly](https://pypi.org/project/plotly/)
  - `sudo apt install python3-pip`
  - `pip3 install dash pandas plotly --user`
- if you're having issues on bullseye, you may need a newer version of [BCC](https://github.com/iovisor/bcc/blob/master/INSTALL.md#debian---binary)
</details>

### [OBS](https://software.opensuse.org//download.html?project=home%3Aelesiuta&package=picosnitch) for openSUSE Tumbleweed and derivatives <img src="https://cdn.simpleicons.org/opensuse" width="16" height="16">
<details><summary>Details</summary>

- `sudo zypper addrepo https://download.opensuse.org/repositories/home:elesiuta/openSUSE_Tumbleweed/home:elesiuta.repo`
- `sudo zypper refresh`
- `sudo zypper install picosnitch`
- install extra dependencies for dash using [pip](https://pip.pypa.io/) (optional): [dash](https://pypi.org/project/dash/), [pandas](https://pypi.org/project/pandas/), and [plotly](https://pypi.org/project/plotly/)
  - `sudo zypper install python3-pip`
  - `pip3 install dash pandas plotly --user`
</details>

### [Copr](https://copr.fedorainfracloud.org/coprs/elesiuta/picosnitch/) for Fedora, Mageia, Mandriva, and derivatives <img src="https://cdn.simpleicons.org/fedora" width="16" height="16">
<details><summary>Details</summary>

- `sudo dnf copr enable elesiuta/picosnitch`
- `sudo dnf install picosnitch`
- install extra dependencies for dash using [pip](https://pip.pypa.io/) (optional): [dash](https://pypi.org/project/dash/), [pandas](https://pypi.org/project/pandas/), and [plotly](https://pypi.org/project/plotly/)
  - `sudo dnf install python3-pip`
  - `pip3 install dash pandas plotly --user`
</details>

### [PyPI](https://pypi.org/project/picosnitch/) for any Linux distribution with Python >= 3.8 <img src="https://cdn.simpleicons.org/linux" width="16" height="16">
<details><summary>Details</summary>

- install the [BPF Compiler Collection](https://github.com/iovisor/bcc/blob/master/INSTALL.md) python package for your distribution
  - it should be called `python-bcc` or `python-bpfcc`
- install picosnitch using [pip](https://pip.pypa.io/)
  - `pip3 install "picosnitch[full]" --upgrade --user`
  - warning: installing as user makes it easier for another program to modify picosnitch; however, installing with sudo results in [xkcd.com/1987](https://xkcd.com/1987/)
- create a service file for systemd to run picosnitch (recommended)
  - `picosnitch systemd`
- optional dependencies (will install from [PyPI](https://pypi.org/) with `[full]` if not already installed)
  - for dash: [dash](https://pypi.org/project/dash/), [pandas](https://pypi.org/project/pandas/), and [plotly](https://pypi.org/project/plotly/)
  - for notifications: `dbus-python`, `python-dbus`, or `python3-dbus` (name depends on your distro and should be installed from their repo)
  - for sql server: one of [psycopg](https://pypi.org/project/psycopg/), [pymysql](https://pypi.org/project/PyMySQL/), [mariadb](https://pypi.org/project/mariadb/), or [psycopg2](https://pypi.org/project/psycopg2/) (latter two not included with `[full]`)
  - for VirusTotal: [requests](https://pypi.org/project/requests/)
</details>

### [GitHub](https://github.com/elesiuta/picosnitch) for installing from source <img src="https://cdn.simpleicons.org/python" width="16" height="16">
<details><summary>Details</summary>

- clone the repo or download `picosnitch.py` and `setup.py`
- install the [BPF Compiler Collection](https://github.com/iovisor/bcc/blob/master/INSTALL.md) python package for your distribution
  - it should be called `python-bcc` or `python-bpfcc`
- install [psutil](https://pypi.org/project/psutil/)
- install `python-setuptools`
- install picosnitch with `python setup.py install --user`
- see other options with `python setup.py [build|install] --help`
- you can also run the script `picosnitch.py` directly
</details>

# [usage](#usage)
- running picosnitch
  - enable/disable autostart on reboot with `systemctl enable|disable picosnitch`
  - start/stop/restart with `systemctl start|stop|restart picosnitch`
  - or if you don't use systemd `picosnitch start|stop|restart`
- web user interface for browsing past connections
  - start with `picosnitch dash`
  - visit [http://localhost:5100](http://localhost:5100) (you change this by setting the environment variables `HOST` and `PORT`)
- terminal user interface for browsing past connections
  - start with `picosnitch view`
  - `space/enter`: filter on entry `backspace`: remove filter `h/H`: cycle through history `t/T`: cycle time range `u/U`: cycle byte units `r`: refresh view `q`: quit
- show usage with `picosnitch help`

# [configuration](#configuration)
- config is stored in `~/.config/picosnitch/config.json`
  - restart picosnitch if it is currently running for any changes to take effect

```yaml
{
  "Bandwidth monitor": true, # Log traffic per connection since last db write
  "DB retention (days)": 90, # How many days to keep connection logs in snitch.db
  "DB sql log": true, # Write connection logs to snitch.db (SQLite)
  "DB sql server": {}, # Write connection logs to a MariaDB, MySQL, or PostgreSQL server
  "DB text log": false, # Write connection logs to conn.log
  "DB write limit (seconds)": 10, # Minimum time between writing connection logs
  # increasing it decreases disk writes by grouping connections into larger time windows
  # reducing time precision, decreasing database size, and increasing hash latency
  "Desktop notifications": true, # Try connecting to dbus to show notifications
  "Every exe (not just conns)": false, # Check every running executable with picosnitch
  # these are treated as "connections" with a port of -1
  # this feature is experimental but should work fairly well, errors should be expected as
  # picosnitch is unable to open file descriptors for some extremely short-lived processes
  # if you just want logs (no hashes) to trace process hierarchy, see execsnoop or forkstat
  "Log addresses": true, # Log remote addresses for each connection
  "Log commands": true, # Log command line args for each executable
  "Log ignore": [], # List of hashes (str), domains (str), IP subnets (str), or ports (int)
  # will omit connections that match any of these from the connection log
  # domains are in reverse domain name notation and will match all subdomains
  # the process name, executable, and hash will still be recorded in record.json
  "Perf ring buffer (pages)": 64, # Power of two number of pages for BPF program
  # only change this if it is giving you errors
  "Set RLIMIT_NOFILE": null, # Set the maximum number of open file descriptors (int)
  # it is used for caching process executables and hashes (typical system default is 1024)
  # this is good enough for most people since caching is based on executable device + inode
  # fanotify is used to detect if a cached executable is modified to trigger a hash update
  "VT API key": "", # API key for VirusTotal, leave blank to disable (str)
  "VT file upload": false, # Upload file if hash not found, only hashes are used by default
  "VT request limit (seconds)": 15 # Number of seconds between requests (free tier quota)
}
```

# [logging](#logging)
- a log of seen executables is stored in `~/.config/picosnitch/exe.log`
  - this is a history of your notifications
- a record of seen executables is stored in `~/.config/picosnitch/record.json`
  - this is used for determining whether to create a notification
  - it contains known process name(s) by executable, executable(s) by process name, and sha256 hash(es) with VirusTotal results by executable
- enable `DB sql log` (default) to write the full connection log to `~/.config/picosnitch/snitch.db`
  - this is used for `picosnitch dash`, `picosnitch view`, or something like [DB Browser](https://sqlitebrowser.org/)
  - note, connection times are based on when the group is processed, so they are accurate to within `DB write limit (seconds)` at best, and could be delayed if the previous group is slow to hash
  - notifications are handled by a separate subprocess, so they are not subject to the same delays as the connection log
- use `DB sql server` to write the full connection log to a MariaDB, MySQL, or PostgreSQL server
  - this is independent of `DB sql log` and is used for providing an [off-system copy to prevent tampering](https://en.wikipedia.org/wiki/Host-based_intrusion_detection_system#Protecting_the_HIDS) (use [GRANT](https://www.postgresql.org/docs/current/sql-grant.html) to assign privileges and see [limitations](#limitations) for other caveats)
  - to configure, add the key `client` to `DB sql server` with value `mariadb`, `psycopg`, `psycopg2`, or `pymysql`, you can also optionally set `table_name`
  - assign remaining connection parameters for [mariadb](https://mariadb-corporation.github.io/mariadb-connector-python/usage.html#connecting), [psycopg](https://www.psycopg.org/docs/module.html#psycopg2.connect), or [pymysql](https://pymysql.readthedocs.io/en/latest/modules/connections.html) to `DB sql server` as key/value pairs
- enable `DB text log` to write the full connection log to `~/.config/picosnitch/conn.log`
  - this may be useful for watching with another program
  - it contains the following fields, separated by commas (commas, newlines, and null characters are removed from values)
  - `executable,name,cmdline,sha256,time,domain,ip,port,uid,parent_exe,parent_name,parent_cmdline,parent_sha256,conns,sent,received`
- the error log is stored in `~/.config/picosnitch/error.log`
  - errors will also trigger a notification and are usually caused by far too many or extremely short-lived processes/connections, or suspending your system while a new executable is being hashed
  - while it is very unlikely for processes/connections to be missed (unless `Every exe (not just conns)` is enabled), picosnitch was designed such that it should still detect this and log an error giving you some indication of what happened
  - for most people in most cases, this should raise suspicion that a program may be misbehaving
  - a program should not be able to hide from picosnitch (either by omission or spoofing another program) without picosnitch reporting an error
  - see [limitations](#limitations) below for other sources of errors

# [limitations](#limitations)
- while picosnitch aims to be as reliable as possible, no tool is perfect and you should know the limitations when deciding whether it is useful and how to use it effectively, whether it's for your [threat model](https://opsec101.org/) or simply [measuring bandwidth](https://www.gcardone.net/2020-07-31-per-process-bandwidth-monitoring-on-Linux-with-bpftrace/#existing-tools-to-measure-bandwidth-usage-on-linux)
  - for example, picosnitch was designed to be more accurate than existing tools by hashing executables and tracking parents, but there are still ways malicious software could hide its traffic through trusted executables as described below, such as compromising shared libraries
  - for stricter security requirements you can keep an [off-system copy of your logs to protect them](https://en.wikipedia.org/wiki/Host-based_intrusion_detection_system#Protecting_the_HIDS)
    - this is not necessary for most people, and of little benefit without considering what else an adversary with these capabilities could do to your system in order to establish appropriate safeguards for your threat model, such as cross-checking with a [standalone router/firewall](https://en.wikipedia.org/wiki/List_of_router_and_firewall_distributions) to ensure all communication is accounted for, monitoring error logs, etc
- detecting open sockets, monitoring traffic, and identifying the process should be fairly reliable with BPF; however, accurately identifying the application behind it can be difficult, especially if has malicious intent
  - the process name is trivial to change, the path can be set to anything with mount namespaces, including impersonating an already existing executable (or replacing it)
  - hashing the executable helps with this; however, it is an imperfect solution since only the process executable itself is hashed and there are still ways a program can hide
    - this leaves out shared libraries (e.g. LD_PRELOAD rootkits), extensions, or scripts which could become compromised
    - if this is a concern, you may want to consider an [immutable OS](https://www.redhat.com/sysadmin/immutability-silverblue), [sandboxing](https://wiki.archlinux.org/title/Security#Sandboxing_applications) such as [flatpak](https://www.privacyguides.org/linux-desktop/sandboxing/#flatpak), or tools such as [AIDE](https://wiki.archlinux.org/title/AIDE), [fs-verity](https://www.kernel.org/doc/html/latest/filesystems/fsverity.html), [IMA/EVM](https://wiki.gentoo.org/wiki/Integrity_Measurement_Architecture), or possibly [debsums (with caveats)](https://manpages.debian.org/unstable/debsums/debsums.1.en.html)
  - if a process is too short lived, picosnitch may not be able to open a file descriptor in time in order to hash it (should be very rare)
  - the device and inode of the opened file descriptor is checked against what was reported by the BPF program to detect if the executable was replaced; however, BTRFS uses non-unique inodes, negating this protection (this is negligible and only mentioned in an attempt for thoroughness)
  - if for any reason the executable fails to hash, the traffic will still be logged with whatever information was available and you will be notified of an error
- too many processes or connections could cause the connection data to be lost if callbacks are not processed fast enough, this will be detected, logging the error and triggering a notification
- instead of playing cat and mouse by trying to cover any edge cases malware may use to hide, the focus is on accurately handling the common case, with clear and reliable error reporting for anything else
- in addition to bugs, please report any other caveats I may have missed!
