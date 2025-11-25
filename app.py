"""
This is your main Streamlit application file, UPDATED to:
1.  Fix the "duplicate widget" glitch.
2.  Display all 5 raw stats in the dashboard, as requested.
"""

import streamlit as st
import time
import pandas as pd

# Import your compiled LangGraph app
from src.agent_graph import app 

# We still import the syscall tool directly, because the
# *Streamlit loop* (not LangGraph) will be calling it.
from src.tools import tool_call_syscall

# --- Page Configuration ---
st.set_page_config(
    page_title="Kernel-Powered Process Monitor",
    page_icon="🔬",
    layout="wide"
)

# --- Initialize Session State ---
# This is Streamlit's "memory"
if "process_list" not in st.session_state:
    st.session_state.process_list = "" # Caches the `ps -u` output
if "monitoring_pids" not in st.session_state:
    st.session_state.monitoring_pids = [] # List of PIDs to watch
if "update_interval" not in st.session_state:
    st.session_state.update_interval = 1.0
if "history" not in st.session_state:
    # Format: {pid: [list of data dicts]}
    st.session_state.history = {}
if "command_input" not in st.session_state:
    # This holds the text box value, allowing us to clear it
    st.session_state.command_input = ""


# ===================================================================
# --- CALLBACK FUNCTIONS (Unchanged) ---
# ===================================================================

def on_submit_clicked():
    """
    This function is called *before* the page reruns when
    the 'Execute' button is clicked.
    """
    user_input = st.session_state.command_input
    if not user_input:
        st.warning("Please enter a command.")
        return # Stop processing
    
    # --- Call the LangGraph "brain" to get a plan ---
    with st.spinner("Agent is thinking..."):
        final_state = app.invoke({"command": user_input})
        result_plan = final_state.get('result', {})
    # -------------------------------------------------

    plan_type = result_plan.get("type")
    
    if plan_type == "list":
        st.session_state.process_list = result_plan.get("data", "Error: No data from agent.")
    
    elif plan_type == "monitor":
        st.session_state.monitoring_pids = result_plan.get("pids", [])
        st.session_state.update_interval = result_plan.get("interval", 1.0)
        st.session_state.history = {} # Clear old history
        
        if not st.session_state.monitoring_pids:
            st.error("NLU couldn't find any PIDs in your command.")
        else:
            st.toast(f"Starting to monitor PIDs: {st.session_state.monitoring_pids}...")
    
    elif plan_type == "stop":
        st.session_state.monitoring_pids = []
        st.session_state.history = {}
        st.toast("Monitoring stopped.")
    
    elif plan_type == "error":
        st.error(result_plan.get("message", "NLU agent had an error."))
    
    else: # "unknown"
        st.error(result_plan.get("message", "I didn't understand. Try 'list processes' or 'monitor <pid>'."))
    
    # Finally, clear the text box for the next command
    st.session_state.command_input = ""

def on_stop_clicked():
    """
    This function is called *before* the page reruns when
    the 'Stop / Clear' button is clicked.
    """
    st.session_state.monitoring_pids = []
    st.session_state.history = {}
    st.session_state.process_list = ""
    st.session_state.command_input = "" # Clear text box
    st.toast("Dashboard cleared.")

# ===================================================================
# --- UI Part 1: Title ---
# ===================================================================
st.title("🔬 Kernel-Powered Process Monitor (LangGraph Edition)")
st.markdown("Use natural language to list processes and monitor multiple PIDs with a live-updating dashboard.")

# ===================================================================
# --- UI Part 2: Command Input and Process List ---
# ===================================================================
st.header("System Interaction")
col1, col2 = st.columns([1, 2]) # Make the list wider

with col1:
    st.subheader("Agent Command")
    # The form now just defines the UI elements.
    # The logic is in the callbacks.
    with st.form(key="command_form"):
        st.text_input(
            "Enter your command:", 
            placeholder="e.g., 'monitor 12345 6789 every 0.5s'",
            key="command_input" # This key links to st.session_state.command_input
        )
        
        b_col1, b_col2 = st.columns(2)
        with b_col1:
            st.form_submit_button(
                label="Execute", 
                use_container_width=True,
                on_click=on_submit_clicked 
            )
        with b_col2:
            st.form_submit_button(
                label="Stop / Clear", 
                use_container_width=True, 
                type="secondary",
                on_click=on_stop_clicked 
            )

with col2:
    st.subheader("`ps -u $USER` Output")
    st.code(st.session_state.process_list, language="bash", line_numbers=True, height=400)

# ===================================================================
# --- UI Part 3: The Auto-Update Loop (The Dashboard) ---
# ===================================================================
st.header("Live PID Dashboard")

# --- THIS IS THE FIX for the UI Glitch ---
# We create the placeholder *inside* the 'if' block.
# This ensures it's only created once per run *after*
# we know we are in monitoring mode.
if st.session_state.monitoring_pids:
    
    # Create a container that will hold all the columns
    dashboard_container = st.container()
    
    num_pids = len(st.session_state.monitoring_pids)
    cols = dashboard_container.columns(num_pids)
    
    pids_to_remove = []

    for i, pid in enumerate(st.session_state.monitoring_pids):
        
        # Streamlit (not LangGraph) calls the syscall tool directly
        usage_data = tool_call_syscall(pid)
        
        # Create a "card" for each PID
        with cols[i], st.container(border=True):
            
            if usage_data and "error" not in usage_data:
                
                # --- History Calculation (Unchanged) ---
                if pid not in st.session_state.history:
                    st.session_state.history[pid] = []
                
                history = st.session_state.history[pid]
                history.append(usage_data)
                history = history[-100:] # Limit history
                st.session_state.history[pid] = history
                
                # --- NEW: Display the 5 Raw Stats ---
                # This is your requested dashboard
                st.subheader(f"{usage_data.get('process_name', 'N/A')} (PID: {pid})")
                
                # We will show all 5 metrics directly
                m_cols = st.columns(3)
                m_cols[0].metric("User CPU (s)", f"{usage_data['user_time']:.4f}")
                m_cols[1].metric("Sys CPU (s)", f"{usage_data['sys_time']:.4f}")
                m_cols[2].metric("Max RSS (KB)", f"{usage_data['max_rss_kb']}")
                
                m_cols_2 = st.columns(2)
                m_cols_2[0].metric("Minor Faults", f"{usage_data['minor_page_faults']}")
                m_cols_2[1].metric("Major Faults", f"{usage_data['major_page_faults']}")
                
                # --- Historical Graphs (in an expander) ---
                with st.expander("Show Historical Graphs"):
                    # Create a DataFrame from this PID's history
                    df = pd.DataFrame(history)
                    
                    st.markdown("##### CPU Usage (Cumulative s)")
                    st.line_chart(df, y=['user_time', 'sys_time'], use_container_width=True)
                    
                    st.markdown("##### Max RSS (KB)")
                    st.line_chart(df, y=['max_rss_kb'], use_container_width=True, color="#FF4B4B") # Red
                    
                    st.markdown("##### Page Faults (Cumulative)")
                    st.line_chart(df, y=['minor_page_faults', 'major_page_faults'], use_container_width=True, color=["#00F", "#F00"]) # Blue/Red

            else:
                # Syscall failed (e.g., process died)
                st.error(f"PID {pid}: {usage_data.get('error', 'Unknown Error')}")
                st.info("Removing from monitor list.")
                pids_to_remove.append(pid)
    
    # --- Cleanup Loop ---
    if pids_to_remove:
        for pid in pids_to_remove:
            if pid in st.session_state.monitoring_pids:
                st.session_state.monitoring_pids.remove(pid)
            if pid in st.session_state.history:
                del st.session_state.history[pid]
        
        if not st.session_state.monitoring_pids:
            st.rerun() # Rerun to show the "stopped" message

    # If we are still monitoring, wait and rerun
    if st.session_state.monitoring_pids:
        try:
            # Set a minimum sleep time to avoid flickering
            sleep_time = max(0.1, st.session_state.update_interval)
            time.sleep(sleep_time)
            st.rerun()
        except Exception as e:
            st.error(f"Invalid update interval: {e}")
            st.session_state.monitoring_pids = []
            st.rerun()

else:
    # If not monitoring, just show a helpful message
    # This is the "else" part of the UI Glitch Fix
    with st.container():
        st.info("No PIDs are currently being monitored. Type 'list processes', then 'monitor <pid1> <pid2> ...' to begin.")