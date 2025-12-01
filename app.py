import streamlit as st
import os
import logging
import threading
import queue
import time
from main import run_ctf_solver

# Set page configuration
st.set_page_config(
    page_title="AI Web CTF Solver",
    page_icon="🚩",
    layout="wide"
)

st.title("🚩 AI Web CTF Solver")
st.markdown("""
Upload challenge files, provide a target URL, and let the AI agent attempt to solve the CTF challenge.
The agent uses a combination of web browsing, tool usage, and LLM reasoning to find the flag.
""")

# --- Sidebar ---
with st.sidebar:
    st.header("Configuration")
    st.info("The agent uses Chrome (Selenium) and Gemini Pro.")
    # You could add model selection or API key inputs here if desired

# --- Main Input Area ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Target Information")
    target_url = st.text_input("Target URL", placeholder="https://example.com/challenge")
    additional_info = st.text_area("Additional Information / Hints", 
                                  placeholder="Any extra context, hints, specific instructions, or credentials...",
                                  height=200)

with col2:
    st.subheader("Challenge Files")
    uploaded_files = st.file_uploader("Upload source code, binaries, or other assets", accept_multiple_files=True)
    if uploaded_files:
        st.success(f"{len(uploaded_files)} files selected.")

# --- Helper Functions ---
def save_uploaded_files(files):
    saved_paths = []
    if not os.path.exists("files"):
        os.makedirs("files")
    
    for uploaded_file in files:
        file_path = os.path.join("files", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        saved_paths.append(file_path)
    return saved_paths

# --- Log Handler ---
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)

# --- Execution Logic ---
if st.button("🚀 Start Solver", type="primary", use_container_width=True):
    if not target_url:
        st.error("Please provide a Target URL.")
    else:
        # 1. Save Files
        saved_file_paths = []
        if uploaded_files:
            with st.spinner("Saving uploaded files..."):
                saved_file_paths = save_uploaded_files(uploaded_files)
        
        # 2. Prepare Logging
        st.subheader("Agent Progress")
        log_container = st.empty()
        log_queue = queue.Queue()
        
        # Setup custom handler to capture logs from main.py and its modules
        # We attach to the root logger to catch everything
        queue_handler = QueueHandler(log_queue)
        queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        
        # 3. Run Solver in Background Thread
        result_queue = queue.Queue()
        
        def run_solver_thread(url, info, files, res_q):
            try:
                # This runs the synchronous solver
                result = run_ctf_solver(url=url, additional_info=info, file_list=files)
                res_q.put(("SUCCESS", result))
            except Exception as e:
                res_q.put(("ERROR", str(e)))
        
        solver_thread = threading.Thread(
            target=run_solver_thread, 
            args=(target_url, additional_info, saved_file_paths, result_queue)
        )
        solver_thread.start()
        
        # 4. Loop to update UI with logs
        all_logs = []
        start_time = time.time()
        
        while solver_thread.is_alive() or not log_queue.empty():
            # Process all available logs in queue
            while not log_queue.empty():
                try:
                    msg = log_queue.get_nowait()
                    all_logs.append(msg)
                except queue.Empty:
                    break
            
            # Update the log container (showing last 50 lines to keep it readable, or all inside a scrollable area)
            # using code block for monospaced font
            log_text = "\n".join(all_logs)
            log_container.code(log_text[-10000:], language="text") # Show last 10k chars approx
            
            # Check for result
            try:
                status, result_data = result_queue.get_nowait()
                if status == "SUCCESS":
                    st.session_state['final_result'] = result_data
                elif status == "ERROR":
                    st.session_state['solver_error'] = result_data
                break # Thread finished
            except queue.Empty:
                pass
            
            time.sleep(0.1)
            
        # Cleanup
        root_logger.removeHandler(queue_handler)
        
        # 5. Display Final Result
        st.divider()
        st.subheader("🏁 Final Result")
        
        if 'final_result' in st.session_state:
            st.success("Challenge Solved!")
            st.markdown(f"**Flag/Result:**")
            st.code(st.session_state['final_result'], language="markdown")
            # Clean up session state for next run if needed, or keep it
            del st.session_state['final_result']
            
        elif 'solver_error' in st.session_state:
            st.error("Solver encountered an error.")
            st.error(st.session_state['solver_error'])
            del st.session_state['solver_error']
        else:
            # Thread finished but no result in queue? Should be covered by queue check above
            pass
