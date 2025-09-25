"""
MedAssist AI Pro - Clinical Workflow Demo
Main Streamlit Application Entry Point
"""

import streamlit as st
import os
from pathlib import Path

# Set page config
st.set_page_config(
    page_title="MedAssist AI Pro",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for medical theme
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .clinical-card {
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-complete { background-color: #28a745; }
    .status-pending { background-color: #ffc107; }
    .status-error { background-color: #dc3545; }
    
    .metric-card {
        background: white;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}
if 'current_stage' not in st.session_state:
    st.session_state.current_stage = 1
if 'clinical_data' not in st.session_state:
    st.session_state.clinical_data = {}

def main():
    """Main application function"""
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏥 MedAssist AI Pro - Clinical Workflow Demo</h1>
        <p>AI-Powered EHR System Inspired by Google's MedGemma Approach</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📋 Clinical Workflow")
        
        # Progress indicator
        stages = [
            "1. Patient Intake",
            "2. Pre-Screening",
            "3. Consultation",
            "4. Final Report",
            "5. Submission"
        ]
        
        for i, stage in enumerate(stages, 1):
            status_class = "status-complete" if i < st.session_state.current_stage else "status-pending"
            if i == st.session_state.current_stage:
                status_class = "status-complete"
            
            st.markdown(f"""
            <div class="clinical-card">
                <span class="status-indicator {status_class}"></span>
                <strong>{stage}</strong>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Quick metrics
        st.subheader("📊 Session Metrics")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Time Saved today", "3.2 min", "↑ 45%")
        with col2:
            st.metric("Accuracy today", "94.2%", "↑ 12%")
    
    # Main content area
    if st.session_state.current_stage == 1:
        from pages.patient_intake import show_patient_intake
        show_patient_intake()
    elif st.session_state.current_stage == 2:
        from pages.pre_screening import show_pre_screening
        show_pre_screening()
    elif st.session_state.current_stage == 3:
        from pages.consultation import show_consultation
        show_consultation()
    elif st.session_state.current_stage == 4:
        from pages.final_report import show_final_report
        show_final_report()
    elif st.session_state.current_stage == 5:
        from pages.submission import show_submission
        show_submission()

if __name__ == "__main__":
    main()
