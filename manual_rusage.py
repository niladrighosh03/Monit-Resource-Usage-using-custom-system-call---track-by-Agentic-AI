import os
import sys

def get_children_recursive(pid):
    """
    Manually scans /proc to find all descendants of the given PID.
    This is the "slow" part that your syscall avoids.
    """
    children = []
    try:
        # Iterate over all directories in /proc
        for p in os.listdir('/proc'):
            if not p.isdigit(): 
                continue
            
            child_pid = int(p)
            try:
                # Read the stat file to find the PPID (Parent PID)
                with open(f"/proc/{child_pid}/stat", 'r') as f:
                    # The status file format: pid (comm) state ppid ...
                    # We split after the last ')' to handle spaces in process names
                    content = f.read()
                    r_par_index = content.rfind(')')
                    stats = content[r_par_index + 2:].split()
                    
                    # Field 1 in the split list is ppid (originally field 3)
                    ppid = int(stats[1])
                    
                    if ppid == pid:
                        children.append(child_pid)
                        # Recursively find this child's children
                        children.extend(get_children_recursive(child_pid))
            except (IOError, FileNotFoundError):
                # Process might die while we scan
                continue
    except Exception:
        pass
    
    return children

def get_manual_usage(root_pid):
    # 1. Get the list of all PIDs in the tree
    pids = [root_pid] + get_children_recursive(root_pid)
    
    print(f"Scanning /proc for PIDs: {pids}")

    total_utime = 0
    total_stime = 0
    max_rss_kb = 0
    total_minflt = 0
    total_majflt = 0
    
    clk_tck = os.sysconf('SC_CLK_TCK')

    for pid in pids:
        try:
            # 2. Parse /proc/[pid]/stat for CPU & Faults
            with open(f"/proc/{pid}/stat", 'r') as f:
                content = f.read()
                r_par = content.rfind(')')
                stats = content[r_par + 2:].split()
                
                # Mapping /proc/pid/stat fields (0-indexed after ')' split):
                # 7: minflt, 8: cminflt, 9: majflt, 10: cmajflt
                # 11: utime, 12: stime, 13: cutime, 14: cstime
                
                min_flt = int(stats[7])
                cmin_flt = int(stats[8])
                maj_flt = int(stats[9])
                cmaj_flt = int(stats[10])
                
                utime = int(stats[11])
                stime = int(stats[12])
                cutime = int(stats[13])
                cstime = int(stats[14])

                # Accumulate current process + its waited-for children
                total_minflt += (min_flt + cmin_flt)
                total_majflt += (maj_flt + cmaj_flt)
                total_utime += (utime + cutime)
                total_stime += (stime + cstime)

            # 3. Parse /proc/[pid]/status for Max Memory (High Water Mark)
            with open(f"/proc/{pid}/status", 'r') as f:
                for line in f:
                    if line.startswith("VmHWM:"):
                        # Format: VmHWM:    1234 kB
                        kb = int(line.split()[1])
                        # Logic from your kernel code: 
                        # total->ru_maxrss = max(total->ru_maxrss, add->ru_maxrss);
                        if kb > max_rss_kb:
                            max_rss_kb = kb
                        break
                        
        except (IOError, FileNotFoundError):
            # Handle race condition where process dies during read
            continue

    return {
        "utime_sec": total_utime / clk_tck,
        "stime_sec": total_stime / clk_tck,
        "maxrss_kb": max_rss_kb,
        "minflt": total_minflt,
        "majflt": total_majflt
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: sudo python3 {sys.argv[0]} <PID>")
        sys.exit(1)

    target_pid = int(sys.argv[1])

    try:
        results = get_manual_usage(target_pid)
        
        print("\n=== Manual Calculation Results ===")
        print(f"PID Tree Root: {target_pid}")
        print(f"User CPU Time:   {results['utime_sec']:.6f} s")
        print(f"Sys CPU Time:    {results['stime_sec']:.6f} s")
        print(f"Max RSS:         {results['maxrss_kb']} kB")
        print(f"Minor Faults:    {results['minflt']}")
        print(f"Major Faults:    {results['majflt']}")
        print("==================================")
        
    except Exception as e:
        print(f"Error: {e}")