import sys
import ctypes
import ctypes.util
import errno
import os

# --- Part 1: Define the C structures in Python ---

class CTimeval(ctypes.Structure):
    _fields_ = [("tv_sec", ctypes.c_long),
                ("tv_usec", ctypes.c_long)]

class CRusage(ctypes.Structure):
    _fields_ = [("ru_utime", CTimeval),
                ("ru_stime", CTimeval),
                ("ru_maxrss", ctypes.c_long),
                ("ru_ixrss", ctypes.c_long),
                ("ru_idrss", ctypes.c_long),
                ("ru_isrss", ctypes.c_long),
                ("ru_minflt", ctypes.c_long),
                ("ru_majflt", ctypes.c_long),
                ("ru_nswap", ctypes.c_long),
                ("ru_inblock", ctypes.c_long),
                ("ru_oublock", ctypes.c_long),
                ("ru_msgsnd", ctypes.c_long),
                ("ru_msgrcv", ctypes.c_long),
                ("ru_nsignals", ctypes.c_long),
                ("ru_nvcsw", ctypes.c_long),
                ("ru_nivcsw", ctypes.c_long)
               ]

# --- Part 2: Load libc and find the syscall function ---

NR_GET_PROC_SUBTREE_RUSAGE = 472

libc_path = ctypes.util.find_library("c")
if not libc_path:
    print("Error: Could not find C library (libc)", file=sys.stderr)
    sys.exit(1)

# use_errno=True is what allows ctypes.get_errno() to work
libc = ctypes.CDLL(libc_path, use_errno=True)

syscall = libc.syscall
syscall.argtypes = [ctypes.c_long, ctypes.c_int, ctypes.c_int, ctypes.POINTER(CRusage)]
syscall.restype = ctypes.c_long


# --- Part 3: The main program logic ---

def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <pid>", file=sys.stderr)
        sys.exit(1)

    try:
        pid = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid PID '{sys.argv[1]}'", file=sys.stderr)
        sys.exit(1)

    print(f"Attempting to get subtree rusage for PID {pid}...")

    usage = CRusage()
    
    # We must set errno to 0 before the call
    ctypes.set_errno(0)
    
    ret = syscall(NR_GET_PROC_SUBTREE_RUSAGE, pid, 0, ctypes.byref(usage))

    if ret < 0:
        # Get the C error number using the ctypes function
        e = ctypes.get_errno()  # <-- THIS IS THE FIX
        
        # Get the error message (like perror)
        error_message = os.strerror(e)
        print(f"syscall(get_proc_subtree_rusage) failed: {error_message}", file=sys.stderr)
        sys.exit(1)

    print("Success!")
    print(f"  User CPU time:   {usage.ru_utime.tv_sec}.{usage.ru_utime.tv_usec:06d} s")
    print(f"  System CPU time: {usage.ru_stime.tv_sec}.{usage.ru_stime.tv_usec:06d} s")
    print(f"  Max RSS:         {usage.ru_maxrss} KB")
    print(f"  Minor pageflts:  {usage.ru_minflt}")
    print(f"  Major pageflts:  {usage.ru_majflt}")

if __name__ == "__main__":
    main()
