#!/usr/bin/env python3
# picosnitch
# Copyright (C) 2020 Eric Lesiuta

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# https://github.com/elesiuta/picosnitch

import collections
import difflib
import ipaddress
import json
import hashlib
import multiprocessing
import os
import pickle
import queue
import shlex
import signal
import socket
import struct
import sys
import time
import typing

try:
    from bcc import BPF
    import filelock
    import plyer
    import psutil
    import vt
except Exception as e:
    print(type(e).__name__ + str(e.args))
    print("Make sure dependency is installed, or environment is preserved if running with sudo")


def read() -> dict:
    """read snitch from correct location (even if sudo is used without preserve-env), or init a new one if not found"""
    template = {
        "Config": {"Only log connections": True, "Remote address unlog": ["firefox"], "VT API key": "", "VT file upload": False, "VT last request": 0, "VT limit request": 15},
        "Errors": [],
        "Latest Entries": [],
        "Names": {},
        "Processes": {},
        "Remote Addresses": {}
    }
    if sys.platform.startswith("linux") and os.getuid() == 0 and os.getenv("SUDO_USER") is not None:
        home_dir = os.path.join("/home", os.getenv("SUDO_USER"))
    else:
        home_dir = os.path.expanduser("~")
    file_path = os.path.join(home_dir, ".config", "picosnitch", "snitch.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8", errors="surrogateescape") as json_file:
            data = json.load(json_file)
        assert all(key in data and type(data[key]) == type(template[key]) for key in template), "Invalid snitch.json"
        assert all(key in data["Config"] for key in template["Config"]), "Invalid config"
        return data
    template["Template"] = True
    return template


def write(snitch: dict) -> None:
    """write snitch to correct location (root privileges should be dropped first)"""
    file_path = os.path.join(os.path.expanduser("~"), ".config", "picosnitch", "snitch.json")
    if not os.path.isdir(os.path.dirname(file_path)):
        os.makedirs(os.path.dirname(file_path))
    try:
        with open(file_path, "w", encoding="utf-8", errors="surrogateescape") as json_file:
            json.dump(snitch, json_file, indent=2, separators=(',', ': '), sort_keys=True, ensure_ascii=False)
    except Exception:
        toast("picosnitch write error", file=sys.stderr)


def drop_root_privileges() -> None:
    """drop root privileges on linux"""
    if sys.platform.startswith("linux") and os.getuid() == 0:
        os.setgid(int(os.getenv("SUDO_GID")))
        os.setuid(int(os.getenv("SUDO_UID")))


def terminate(snitch: dict, p_snitch: multiprocessing.Process, q_term: multiprocessing.Queue):
    """write snitch one last time, then terminate picosnitch and subprocesses if running"""
    write(snitch)
    q_term.put("TERMINATE")
    p_snitch.join(5)
    p_snitch.close()
    sys.exit(0)


def toast(msg: str, file=sys.stdout) -> None:
    """create a system tray notification, tries printing as a last resort, requires -E if running with sudo"""
    try:
        plyer.notification.notify(title="picosnitch", message=msg, app_name="picosnitch")
    except Exception:
        print("picosnitch (toast failed): " + msg, file=file)


def reverse_dns_lookup(ip: str) -> str:
    """do a reverse dns lookup, return original ip if fails"""
    try:
        return socket.getnameinfo((ip, 0), 0)[0]
    except Exception:
        return ip


def reverse_domain_name(dns: str) -> str:
    """reverse domain name, don't reverse if ip"""
    try:
        _ = ipaddress.ip_address(dns)
        return dns
    except ValueError:
        return ".".join(reversed(dns.split(".")))


def get_common_pattern(a: str, l: list, cutoff: float) -> None:
    """if there is a close match to a in l, replace it with a common pattern, otherwise append a to l"""
    b = difflib.get_close_matches(a, l, n=1, cutoff=cutoff)
    if b:
        common_pattern = ""
        for match in difflib.SequenceMatcher(None, a.lower(), b[0].lower(), False).get_matching_blocks():
            common_pattern += "*" * (match.a - len(common_pattern))
            common_pattern += a[match.a:match.a+match.size]
        l[l.index(b[0])] = common_pattern
        while l.count(common_pattern) > 1:
            l.remove(common_pattern)
    else:
        l.append(a)


def get_sha256(exe: str) -> str:
    """get sha256 of process executable"""
    try:
        with open(exe, "rb") as f:
            sha256 = hashlib.sha256(f.read())
        return sha256.hexdigest()
    except Exception:
        return "0000000000000000000000000000000000000000000000000000000000000000"


def get_vt_results(sha256: str, proc: dict, config: dict) -> str:
    """get virustotal results of process executable and toast negative results"""
    if config["VT API key"]:
        client = vt.Client(config["VT API key"])
        time.sleep(max(0, config["VT last request"] + config["VT limit request"] - time.time()))
        config["VT last request"] = time.time()
        try:
            analysis = client.get_object("/files/" + sha256)
        except Exception:
            if config["VT file upload"]:
                toast("Uploading " + proc["name"] + " for analysis")
                with open(proc["exe"], "rb") as f:
                    analysis = client.scan_file(f, wait_for_completion=True)
            else:
                return "File not analyzed (analysis not found)"
        if analysis.last_analysis_stats["malicious"] != 0 or analysis.last_analysis_stats["suspicious"] != 0:
            toast("Suspicious results for " + proc["name"])
        return str(analysis.last_analysis_stats)
    return "File not analyzed (no api key)"


def initial_poll(snitch: dict, known_pids: dict) -> None:
    """poll initial processes and connections using psutil, then runs update_snitch_*"""
    ctime = time.ctime()
    current_processes = {}
    for proc in psutil.process_iter(attrs=["name", "exe", "cmdline", "pid"], ad_value=""):
        if os.path.isfile(proc.info["exe"]):
            current_processes[proc.info["exe"]] = proc.info
            known_pids["pid"] = proc.info
    proc = {"name": "", "exe": "", "cmdline": "", "pid": ""}
    current_connections = set(psutil.net_connections(kind="all"))
    for conn in current_connections:
        try:
            if conn.pid is not None and conn.raddr and not ipaddress.ip_address(conn.raddr.ip).is_private:
                proc = psutil.Process(conn.pid).as_dict(attrs=["name", "exe", "cmdline", "pid"], ad_value="")
                conn_dict = {"ip": conn.raddr.ip, "port": conn.raddr.port}
                sha256 = get_sha256(proc["exe"])
                _ = current_processes.pop(proc["exe"], 0)
                update_snitch(snitch, proc, conn_dict, sha256, ctime)
        except Exception as e:
            # too late to grab process info (most likely) or some other error
            error = "Init " + type(e).__name__ + str(e.args) + str(conn)
            if conn.pid == proc["pid"]:
                error += str(proc)
            else:
                error += "{process no longer exists}"
            snitch["Errors"].append(ctime + " " + error)
    if not snitch["Config"]["Only log connections"]:
        conn = {"ip": "", "port": 0}
        for proc in current_processes.values():
            try:
                sha256 = get_sha256(proc["exe"])
                update_snitch(snitch, proc, conn, sha256, ctime)
            except Exception as e:
                error = "Init " + type(e).__name__ + str(e.args) + str(proc)
                snitch["Errors"].append(ctime + " " + error)


def process_queue(snitch: dict, known_pids: dict, missed_conns: list, new_processes: list) -> list:
    """process list of new processes and call update_snitch"""
    ctime = time.ctime()
    pending_list = []
    pending_conns = []
    for proc in new_processes:
        if proc["type"] == "exec":
            proc["exe"] = shlex.split(proc["cmdline"])[0]
            if proc["exe"] == "exec":
                proc["exe"] = shlex.split(proc["cmdline"])[1]
            known_pids[proc["pid"]] = proc
            if not snitch["Config"]["Only log connections"]:
                pending_list.append(proc)
        elif proc["type"] == "conn":
            if proc["pid"] in known_pids:
                proc["name"] = known_pids[proc["pid"]]["name"]
                proc["exe"] = known_pids[proc["pid"]]["exe"]
                proc["cmdline"] = known_pids[proc["pid"]]["cmdline"]
                pending_list.append(proc)
            else:
                proc_psutil = psutil.Process(proc["pid"]).as_dict(attrs=["name", "exe", "cmdline", "pid"], ad_value="")
                if proc_psutil["exe"]:
                    known_pids[proc_psutil["pid"]] = proc_psutil
                pending_conns.append(proc)
    for proc in missed_conns:
        if proc["pid"] in known_pids:
            proc["name"] = known_pids[proc["pid"]]["name"]
            proc["exe"] = known_pids[proc["pid"]]["exe"]
            proc["cmdline"] = known_pids[proc["pid"]]["cmdline"]
            pending_list.append(proc)
        else:
            snitch["Errors"].append(ctime + " no known process for conn: " + str(proc))
    for proc in pending_list:
        try:
            if proc["type"] == "conn":
                conn = {"ip": proc["ip"], "port": proc["port"]}
            else:
                conn = {"ip": "", "port": 0}
            sha256 = get_sha256(proc["exe"])
            update_snitch(snitch, proc, conn, sha256, ctime)
        except Exception as e:
            error = type(e).__name__ + str(e.args) + str(proc)
            snitch["Errors"].append(ctime + " " + error)
            toast("Processsnitch error: " + error, file=sys.stderr)
    return pending_conns


def update_snitch(snitch: dict, proc: dict, conn: dict, sha256: str, ctime: str) -> None:
    """update the snitch with data from queues and create a notification if new entry"""
    # Get DNS reverse name and reverse the name for sorting
    reversed_dns = reverse_domain_name(reverse_dns_lookup(conn["ip"]))
    # Update Latest Entries
    if proc["exe"] not in snitch["Processes"] or proc["name"] not in snitch["Names"]:
        snitch["Latest Entries"].append(ctime + " " + proc["name"] + " - " + proc["exe"])
    # Update Names
    if proc["name"] in snitch["Names"]:
        if proc["exe"] not in snitch["Names"][proc["name"]]:
            snitch["Names"][proc["name"]].append(proc["exe"])
            toast("New executable detected for " + proc["name"] + ": " + proc["exe"])
    elif conn["ip"] or conn["port"]:
        snitch["Names"][proc["name"]] = [proc["exe"]]
        toast("First network connection detected for " + proc["name"])
    # Update Processes
    if proc["exe"] not in snitch["Processes"]:
        snitch["Processes"][proc["exe"]] = {
            "name": proc["name"],
            "cmdlines": [str(proc["cmdline"])],
            "first seen": ctime,
            "last seen": ctime,
            "days seen": 1,
            "ports": [conn["port"]],
            "remote addresses": [],
            "results": {sha256: get_vt_results(sha256, proc, snitch["Config"])}
        }
        if conn["port"] not in snitch["Config"]["Remote address unlog"] and proc["name"] not in snitch["Config"]["Remote address unlog"]:
            snitch["Processes"][proc["exe"]]["remote addresses"].append(reversed_dns)
    else:
        entry = snitch["Processes"][proc["exe"]]
        if proc["name"] not in entry["name"]:
            entry["name"] += " alternative=" + proc["name"]
        if str(proc["cmdline"]) not in entry["cmdlines"]:
            get_common_pattern(str(proc["cmdline"]), entry["cmdlines"], 0.8)
            entry["cmdlines"].sort()
        if conn["port"] not in entry["ports"]:
            entry["ports"].append(conn["port"])
            entry["ports"].sort()
        if reversed_dns not in entry["remote addresses"]:
            if conn["port"] not in snitch["Config"]["Remote address unlog"] and proc["name"] not in snitch["Config"]["Remote address unlog"]:
                entry["remote addresses"].append(reversed_dns)
        if sha256 not in entry["results"]:
            entry["results"][sha256] = get_vt_results(sha256, proc, snitch["Config"])
        if ctime.split()[:3] != entry["last seen"].split()[:3]:
            entry["days seen"] += 1
        entry["last seen"] = ctime
    # Update Remote Addresses
    if reversed_dns in snitch["Remote Addresses"]:
        if proc["exe"] not in snitch["Remote Addresses"][reversed_dns]:
            snitch["Remote Addresses"][reversed_dns].insert(1, proc["exe"])
            if "No processes found during polling" in snitch["Remote Addresses"][reversed_dns]:
                snitch["Remote Addresses"][reversed_dns].remove("No processes found during polling")
    else:
        if conn["port"] not in snitch["Config"]["Remote address unlog"] and proc["name"] not in snitch["Config"]["Remote address unlog"]:
            snitch["Remote Addresses"][reversed_dns] = ["First connection: " + ctime, proc["exe"]]


def loop(vt_api_key: str = ""):
    """main loop"""
    # acquire lock (since the prior one would be released by starting the daemon)
    lock = filelock.FileLock(os.path.join(os.path.expanduser("~"), ".picosnitch_lock"), timeout=1)
    lock.acquire()
    # read config and set VT API key if entered
    snitch = read()
    _ = snitch.pop("Template", 0)
    if vt_api_key:
        snitch["Config"]["VT API key"] = vt_api_key
    # init bpf program
    p_snitch_mon, q_snitch, q_error, q_term = init_snitch_subprocess(snitch["Config"])
    drop_root_privileges()
    # set signal handlers
    signal.signal(signal.SIGTERM, lambda *args: terminate(snitch, p_snitch_mon, q_term))
    signal.signal(signal.SIGINT, lambda *args: terminate(snitch, p_snitch_mon, q_term))
    # snitch init checks
    if p_snitch_mon is None:
        snitch["Errors"].append(time.ctime() + " Snitch subprocess init failed, __name__ != __main__, try: python -m picosnitch")
        toast("Snitch subprocess init failed, try: python -m picosnitch", file=sys.stderr)
        sys.exit(1)
    # init variables for loop
    known_pids = {}
    missed_conns = []
    sizeof_snitch = sys.getsizeof(pickle.dumps(snitch))
    last_write = 0
    # get initial running processes and connections
    initial_poll(snitch, known_pids)
    while True:
        # check for subprocess errors
        while not q_error.empty():
            error = q_error.get()
            snitch["Errors"].append(time.ctime() + " " + error)
            toast(error, file=sys.stderr)
        # log snitch death, exit picosnitch
        if not p_snitch_mon.is_alive():
            snitch["Errors"].append(time.ctime() + " snitch subprocess stopped")
            toast("snitch subprocess stopped, exiting picosnitch", file=sys.stderr)
            terminate(snitch, p_snitch_mon, q_term)
        # list of new processes and connections since last poll
        new_processes = []
        if q_snitch.empty():
            time.sleep(5)
        while not q_snitch.empty():
            new_processes.append(pickle.loads(q_snitch.get()))
        missed_conns = process_queue(snitch, known_pids, missed_conns, new_processes)
        # write snitch
        if time.time() - last_write > 30:
            new_size = sys.getsizeof(pickle.dumps(snitch))
            if new_size != sizeof_snitch or time.time() - last_write > 600:
                sizeof_snitch = new_size
                last_write = time.time()
                write(snitch)


def init_snitch_subprocess(config: dict) -> typing.Tuple[multiprocessing.Process, multiprocessing.Queue, multiprocessing.Queue, multiprocessing.Queue]:
    """init snitch subprocess and monitor with root (before dropping root privileges)"""
    def snitch_linux(config, q_snitch, q_error, q_term_monitor):
        """runs a bpf program to monitor the system for new processes and connections and puts them in the queue"""
        if os.getuid() == 0:
            b = BPF(text=bpf_text)
            execve_fnname = b.get_syscall_fnname("execve")
            b.attach_kprobe(event=execve_fnname, fn_name="syscall__execve")
            b.attach_kretprobe(event=execve_fnname, fn_name="do_ret_sys_execve")
            b.attach_kprobe(event="security_socket_connect", fn_name="security_socket_connect_entry")
            argv = collections.defaultdict(list)
            def queue_exec_event(cpu, data, size):
                event = b["exec_events"].event(data)
                if event.type == 0:  # EVENT_ARG
                    argv[event.pid].append(event.argv)
                elif event.type == 1:  # EVENT_RET
                    argv_text = b' '.join(argv[event.pid]).replace(b'\n', b'\\n')
                    q_snitch.put(pickle.dumps({"type": "exec", "pid": event.pid, "name": event.comm.decode(), "cmdline": argv_text.decode()}))
                    try:
                        del(argv[event.pid])
                    except Exception:
                        pass
            def queue_ipv4_event(cpu, data, size):
                event = b["ipv4_events"].event(data)
                q_snitch.put(pickle.dumps({"type": "conn", "pid": event.pid, "port": event.dport, "ip": socket.inet_ntop(socket.AF_INET, struct.pack("I", event.daddr))}))
            def queue_ipv6_event(cpu, data, size):
                event = b["ipv6_events"].event(data)
                q_snitch.put(pickle.dumps({"type": "conn", "pid": event.pid, "port": event.dport, "ip": socket.inet_ntop(socket.AF_INET6, event.daddr)}))
            def queue_other_event(cpu, data, size):
                event = b["other_socket_events"].event(data)
                q_snitch.put(pickle.dumps({"type": "conn", "pid": event.pid, "port": 0, "ip": ""}))
            b["exec_events"].open_perf_buffer(queue_exec_event)
            b["ipv4_events"].open_perf_buffer(queue_ipv4_event)
            b["ipv6_events"].open_perf_buffer(queue_ipv6_event)
            b["other_socket_events"].open_perf_buffer(queue_other_event)
            while True:
                try:
                    b.perf_buffer_poll()
                except Exception as e:
                    error = "BPF " + type(e).__name__ + str(e.args)
                    q_error.put(error)
                try:
                    if q_term_monitor.get(block=False):
                        return 0
                except queue.Empty:
                    if not multiprocessing.parent_process().is_alive():
                        return 0
        else:
            q_error.put("Snitch subprocess permission error, requires root")
        return 1

    def snitch_monitor(config, q_snitch, q_error, q_term):
        """monitor the snitch subprocess and parent process, has same privileges as subprocess for clean termination at the command or death of the parent"""
        signal.signal(signal.SIGINT, lambda *args: None)
        if sys.platform.startswith("linux"):
            p_snitch_func = snitch_linux
        # elif sys.platform.startswith("win"):
        #     process_monitor = snitch_windows
        else:
            q_error.put("Did not detect a supported operating system")
            return 1
        q_term_monitor = multiprocessing.Queue()
        terminate_subprocess = lambda p_snitch_sub: q_term_monitor.put("TERMINATE") or p_snitch_sub.join(3) or (p_snitch_sub.is_alive() and p_snitch_sub.kill()) or p_snitch_sub.close()
        p_snitch_sub = multiprocessing.Process(name="processsnitch", target=p_snitch_func, args=(config, q_snitch, q_error, q_term_monitor), daemon=True)
        p_snitch_sub.start()
        time_last_start = time.time()
        while True:
            if p_snitch_sub.is_alive():
                if psutil.Process(p_snitch_sub.pid).memory_info().vms > 512000000:
                    q_error.put("Snitch subprocess memory usage exceeded 512 MB, restarting snitch")
                    terminate_subprocess(p_snitch_sub)
                    p_snitch_sub = multiprocessing.Process(name="processsnitch", target=p_snitch_func, args=(config, q_snitch, q_error, q_term_monitor), daemon=True)
                    p_snitch_sub.start()
                    time_last_start = time.time()
            elif time.time() - time_last_start > 300:
                q_error.put("Snitch subprocess died, restarting snitch")
                p_snitch_sub = multiprocessing.Process(name="processsnitch", target=p_snitch_func, args=(config, q_snitch, q_error, q_term_monitor), daemon=True)
                p_snitch_sub.start()
                time_last_start = time.time()
            try:
                if q_term.get(block=True, timeout=10):
                    break
            except queue.Empty:
                if not multiprocessing.parent_process().is_alive() or not p_snitch_sub.is_alive():
                    break
        terminate_subprocess(p_snitch_sub)
        return 0

    if __name__ == "__main__":
        q_snitch, q_error, q_term = multiprocessing.Queue(), multiprocessing.Queue(), multiprocessing.Queue()
        p_snitch_mon = multiprocessing.Process(name="processsnitchmonitor", target=snitch_monitor, args=(config, q_snitch, q_error, q_term))
        p_snitch_mon.start()
        return p_snitch_mon, q_snitch, q_error, q_term
    return None, None, None, None


def main():
    """startup picosnitch as a daemon on posix systems, regular process otherwise, and ensure only one instance is running"""
    lock = filelock.FileLock(os.path.join(os.path.expanduser("~"), ".picosnitch_lock"), timeout=1)
    try:
        lock.acquire()
        lock.release()
    except filelock.Timeout:
        print("Error: another instance of this application is currently running", file=sys.stderr)
        sys.exit(1)
    try:
        tmp_snitch = read()
        if not tmp_snitch["Config"]["VT API key"] and "Template" in tmp_snitch:
            tmp_snitch["Config"]["VT API key"] = input("Enter your VirusTotal API key (optional)\n>>> ")
    except Exception as e:
        print(type(e).__name__ + str(e.args))
        sys.exit(1)
    if sys.prefix != sys.base_prefix:
            print("Warning: picosnitch is running in a virtual environment, notifications may not function", file=sys.stderr)
    if os.name == "posix":
        if os.path.expanduser("~") == "/root":
            print("Warning: picosnitch was run as root without preserving environment", file=sys.stderr)
        import daemon
        with daemon.DaemonContext():
            loop(tmp_snitch["Config"]["VT API key"])
    else:
        # not really supported right now (waiting to see what happens with https://github.com/microsoft/ebpf-for-windows)
        loop(tmp_snitch["Config"]["VT API key"])


bpf_text = """
// This BPF program was adapted from the following sources, both licensed under the Apache License, Version 2.0
// https://github.com/iovisor/bcc/blob/023154c7708087ddf6c2031cef5d25c2445b70c4/tools/execsnoop.py
// https://github.com/p-/socket-connect-bpf/blob/7f386e368759e53868a078570254348e73e73e22/securitySocketConnectSrc.bpf
// Copyright 2016 Netflix, Inc.
// Copyright 2019 Peter Stöckli

// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <uapi/linux/ptrace.h>
#include <linux/socket.h>
#include <linux/sched.h>
#include <linux/fs.h>
#include <linux/in.h>
#include <linux/in6.h>
#include <linux/ip.h>

#define ARGSIZE  128

enum event_type {
    EVENT_ARG,
    EVENT_RET,
};

struct data_t {
    u32 pid;  // PID as in the userspace term (i.e. task->tgid in kernel)
    u32 ppid; // Parent PID as in the userspace term (i.e task->real_parent->tgid in kernel)
    u32 uid;
    char comm[TASK_COMM_LEN];
    enum event_type type;
    char argv[ARGSIZE];
    int retval;
};
BPF_PERF_OUTPUT(exec_events);

struct ipv4_event_t {
    u64 ts_us;
    u32 pid;
    u32 uid;
    u32 af;
    char task[TASK_COMM_LEN];
    u32 daddr;
    u16 dport;
} __attribute__((packed));
BPF_PERF_OUTPUT(ipv4_events);

struct ipv6_event_t {
    u64 ts_us;
    u32 pid;
    u32 uid;
    u32 af;
    char task[TASK_COMM_LEN];
    unsigned __int128 daddr;
    u16 dport;
} __attribute__((packed));
BPF_PERF_OUTPUT(ipv6_events);

struct other_socket_event_t {
    u64 ts_us;
    u32 pid;
    u32 uid;
    u32 af;
    char task[TASK_COMM_LEN];
} __attribute__((packed));
BPF_PERF_OUTPUT(other_socket_events);

static int __submit_arg(struct pt_regs *ctx, void *ptr, struct data_t *data)
{
    bpf_probe_read_user(data->argv, sizeof(data->argv), ptr);
    exec_events.perf_submit(ctx, data, sizeof(struct data_t));
    return 1;
}

static int submit_arg(struct pt_regs *ctx, void *ptr, struct data_t *data)
{
    const char *argp = NULL;
    bpf_probe_read_user(&argp, sizeof(argp), ptr);
    if (argp) {
        return __submit_arg(ctx, (void *)(argp), data);
    }
    return 0;
}

int syscall__execve(struct pt_regs *ctx,
    const char __user *filename,
    const char __user *const __user *__argv,
    const char __user *const __user *__envp)
{

    u32 uid = bpf_get_current_uid_gid() & 0xffffffff;

    // create data here and pass to submit_arg to save stack space (#555)
    struct data_t data = {};
    struct task_struct *task;

    data.pid = bpf_get_current_pid_tgid() >> 32;

    task = (struct task_struct *)bpf_get_current_task();
    // Some kernels, like Ubuntu 4.13.0-generic, return 0
    // as the real_parent->tgid.
    // We use the get_ppid function as a fallback in those cases. (#1883)
    data.ppid = task->real_parent->tgid;

    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    data.type = EVENT_ARG;

    __submit_arg(ctx, (void *)filename, &data);

    // skip first arg, as we submitted filename
    #pragma unroll
    for (int i = 1; i < 20; i++) {
        if (submit_arg(ctx, (void *)&__argv[i], &data) == 0)
             goto out;
    }

    // handle truncated argument list
    char ellipsis[] = "...";
    __submit_arg(ctx, (void *)ellipsis, &data);
out:
    return 0;
}

int do_ret_sys_execve(struct pt_regs *ctx)
{
    struct data_t data = {};
    struct task_struct *task;

    u32 uid = bpf_get_current_uid_gid() & 0xffffffff;

    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.uid = uid;

    task = (struct task_struct *)bpf_get_current_task();
    // Some kernels, like Ubuntu 4.13.0-generic, return 0
    // as the real_parent->tgid.
    // We use the get_ppid function as a fallback in those cases. (#1883)
    data.ppid = task->real_parent->tgid;

    bpf_get_current_comm(&data.comm, sizeof(data.comm));
    data.type = EVENT_RET;
    data.retval = PT_REGS_RC(ctx);
    exec_events.perf_submit(ctx, &data, sizeof(data));

    return 0;
}

int security_socket_connect_entry(struct pt_regs *ctx, struct socket *sock, struct sockaddr *address, int addrlen)
{
    int ret = PT_REGS_RC(ctx);

    u64 pid_tgid = bpf_get_current_pid_tgid();
    u32 pid = pid_tgid >> 32;

    u32 uid = bpf_get_current_uid_gid();

    struct sock *skp = sock->sk;

    // The AF options are listed in https://github.com/torvalds/linux/blob/master/include/linux/socket.h

    u32 address_family = address->sa_family;
    if (address_family == AF_INET) {
        struct ipv4_event_t data4 = {.pid = pid, .uid = uid, .af = address_family};
        data4.ts_us = bpf_ktime_get_ns() / 1000;

        struct sockaddr_in *daddr = (struct sockaddr_in *)address;

        bpf_probe_read(&data4.daddr, sizeof(data4.daddr), &daddr->sin_addr.s_addr);

        u16 dport = 0;
        bpf_probe_read(&dport, sizeof(dport), &daddr->sin_port);
        data4.dport = ntohs(dport);

        bpf_get_current_comm(&data4.task, sizeof(data4.task));

        if (data4.dport != 0) {
            ipv4_events.perf_submit(ctx, &data4, sizeof(data4));
        }
    }
    else if (address_family == AF_INET6) {
        struct ipv6_event_t data6 = {.pid = pid, .uid = uid, .af = address_family};
        data6.ts_us = bpf_ktime_get_ns() / 1000;

        struct sockaddr_in6 *daddr6 = (struct sockaddr_in6 *)address;

        bpf_probe_read(&data6.daddr, sizeof(data6.daddr), &daddr6->sin6_addr.in6_u.u6_addr32);

        u16 dport6 = 0;
        bpf_probe_read(&dport6, sizeof(dport6), &daddr6->sin6_port);
        data6.dport = ntohs(dport6);

        bpf_get_current_comm(&data6.task, sizeof(data6.task));

        if (data6.dport != 0) {
            ipv6_events.perf_submit(ctx, &data6, sizeof(data6));
        }
    }
    else if (address_family != AF_UNIX && address_family != AF_UNSPEC) { // other sockets, except UNIX and UNSPEC sockets
        struct other_socket_event_t socket_event = {.pid = pid, .uid = uid, .af = address_family};
        socket_event.ts_us = bpf_ktime_get_ns() / 1000;
        bpf_get_current_comm(&socket_event.task, sizeof(socket_event.task));
        other_socket_events.perf_submit(ctx, &socket_event, sizeof(socket_event));
    }

    return 0;
}
"""

if __name__ == "__main__":
    sys.exit(main())
