"""
Patient Intake Page
Handles patient registration and symptom collection
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date
import os
from pathlib import Path
import json
import time

from core.ai_models.medical_nlp import MedicalEntityRecognizer
from utils.session_manager import get_session_state, update_session_state

def calculate_age(born):
    """Calculate age from birthdate"""
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def show_patient_intake():
    """Display the patient intake page"""
    
    st.header("📋 Smart Patient Intake Portal")
    
    # Initialize session state for patient data if not exists
    if 'patient_data' not in st.session_state:
        st.session_state.patient_data = {}
    
    # Tabs for different sections of intake
    tab1, tab2, tab3 = st.tabs(["Patient Registration", "Symptom Collection", "Document Upload"])
    
    # Tab 1: Patient Registration
    with tab1:
        st.subheader("Patient Registration")
        
        # Create a form for patient registration
        with st.form("patient_registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Basic Demographics
                st.markdown("### Basic Demographics")
                
                # Auto-generate MRN if not already set
                if "mrn" not in st.session_state.patient_data:
                    import random
                    mrn = f"MRN{random.randint(100000, 999999)}"
                else:
                    mrn = st.session_state.patient_data.get("mrn", "")
                
                mrn_input = st.text_input("Medical Record Number", value=mrn, disabled=True)
                
                name = st.text_input("Full Name", value=st.session_state.patient_data.get("name", ""))
                preferred_name = st.text_input("Preferred Name (Optional)", value=st.session_state.patient_data.get("preferred_name", ""))
                
                dob = st.date_input("Date of Birth", 
                                   value=datetime.strptime(st.session_state.patient_data.get("dob", "1980-01-01"), "%Y-%m-%d").date() 
                                   if "dob" in st.session_state.patient_data else date(1980, 1, 1))
                
                # Calculate and display age
                age = calculate_age(dob)
                st.info(f"Age: {age} years")
                
                gender = st.selectbox("Gender", 
                                     options=["Male", "Female", "Non-binary", "Prefer not to say"],
                                     index=["Male", "Female", "Non-binary", "Prefer not to say"].index(st.session_state.patient_data.get("gender", "Male")))
            
            with col2:
                # Contact Information
                st.markdown("### Contact Information")
                
                phone = st.text_input("Phone Number", value=st.session_state.patient_data.get("phone", ""))
                sms_consent = st.checkbox("Consent to SMS notifications", value=st.session_state.patient_data.get("sms_consent", False))
                
                email = st.text_input("Email Address", value=st.session_state.patient_data.get("email", ""))
                portal_access = st.checkbox("Set up patient portal access", value=st.session_state.patient_data.get("portal_access", False))
                
                st.markdown("### Emergency Contact")
                emergency_name = st.text_input("Emergency Contact Name", value=st.session_state.patient_data.get("emergency_name", ""))
                emergency_phone = st.text_input("Emergency Contact Phone", value=st.session_state.patient_data.get("emergency_phone", ""))
            
            # Visit Information
            st.markdown("### Visit Information")
            col1, col2 = st.columns(2)
            
            with col1:
                visit_type = st.selectbox("Visit Type", 
                                         options=["New Patient", "Follow-up", "Urgent Care", "Routine"],
                                         index=["New Patient", "Follow-up", "Urgent Care", "Routine"].index(st.session_state.patient_data.get("visit_type", "New Patient")))
                
                referring_physician = st.text_input("Referring Physician (if any)", value=st.session_state.patient_data.get("referring_physician", ""))
            
            with col2:
                insurance_provider = st.text_input("Insurance Provider", value=st.session_state.patient_data.get("insurance_provider", ""))
                insurance_id = st.text_input("Insurance ID", value=st.session_state.patient_data.get("insurance_id", ""))
                
                # Mock insurance verification
                if insurance_provider and insurance_id:
                    st.success("✅ Insurance verified")
            
            submit_button = st.form_submit_button("Save Patient Information")
            
            if submit_button:
                # Save patient data to session state
                st.session_state.patient_data.update({
                    "mrn": mrn_input,
                    "name": name,
                    "preferred_name": preferred_name,
                    "dob": dob.strftime("%Y-%m-%d"),
                    "age": age,
                    "gender": gender,
                    "phone": phone,
                    "sms_consent": sms_consent,
                    "email": email,
                    "portal_access": portal_access,
                    "emergency_name": emergency_name,
                    "emergency_phone": emergency_phone,
                    "visit_type": visit_type,
                    "referring_physician": referring_physician,
                    "insurance_provider": insurance_provider,
                    "insurance_id": insurance_id
                })
                
                st.success("Patient information saved successfully!")
                st.balloons()
                
                # Automatically switch to next tab
                time.sleep(1)
                st.experimental_rerun()
    
    # Tab 2: Symptom Collection
    with tab2:
        st.subheader("Multi-Modal Symptom Collection")
        
        # Check if patient info is completed
        if not st.session_state.patient_data.get("name"):
            st.warning("Please complete patient registration first.")
            return
        
        # Display patient info summary
        with st.expander("Patient Information", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Name:** {st.session_state.patient_data.get('name')}")
                st.write(f"**MRN:** {st.session_state.patient_data.get('mrn')}")
                st.write(f"**Age:** {st.session_state.patient_data.get('age')}")
                st.write(f"**Gender:** {st.session_state.patient_data.get('gender')}")
            with col2:
                st.write(f"**Visit Type:** {st.session_state.patient_data.get('visit_type')}")
                st.write(f"**Insurance:** {st.session_state.patient_data.get('insurance_provider')}")
        
        # Symptom collection methods
        method_tab1, method_tab2, method_tab3 = st.tabs(["Text Input", "Audio Recording", "Image Upload"])
        
        # Text Input Method
        with method_tab1:
            st.markdown("### Text Symptom Input")
            
            # Chief complaint
            chief_complaint = st.text_area("What brings you in today?", 
                                         value=st.session_state.patient_data.get("chief_complaint", ""),
                                         height=100,
                                         placeholder="Describe your main symptoms or concerns...")
            
            # When did it start
            col1, col2 = st.columns(2)
            with col1:
                symptom_onset = st.text_input("When did this start?", 
                                            value=st.session_state.patient_data.get("symptom_onset", ""),
                                            placeholder="e.g., 3 days ago, last week")
            
            # Severity rating
            with col2:
                severity = st.slider("Rate your discomfort (1-10)", 
                                   min_value=1, max_value=10, 
                                   value=int(st.session_state.patient_data.get("severity", 5)))
            
            # Symptom quality
            symptom_quality = st.text_area("Describe the sensation", 
                                         value=st.session_state.patient_data.get("symptom_quality", ""),
                                         height=100,
                                         placeholder="e.g., sharp pain, dull ache, burning sensation")
            
            # Process text input with NLP
            if chief_complaint:
                with st.spinner("Analyzing symptoms..."):
                    # Initialize medical entity recognizer
                    nlp = MedicalEntityRecognizer()
                    
                    # Combine all text inputs for analysis
                    combined_text = f"{chief_complaint} {symptom_onset} {symptom_quality}"
                    
                    # Extract medical entities
                    entities = nlp.extract_entities(combined_text)
                    
                    # Save to session state
                    st.session_state.patient_data.update({
                        "chief_complaint": chief_complaint,
                        "symptom_onset": symptom_onset,
                        "severity": severity,
                        "symptom_quality": symptom_quality,
                        "extracted_entities": entities
                    })
                    
                    # Display extracted entities
                    with st.expander("AI Analysis Results", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.markdown("#### Detected Symptoms")
                            if entities["symptoms"]:
                                for symptom in entities["symptoms"]:
                                    st.markdown(f"- {symptom.title()}")
                            else:
                                st.write("No specific symptoms detected")
                        
                        with col2:
                            st.markdown("#### Anatomical Sites")
                            if entities["anatomical_sites"]:
                                for site in entities["anatomical_sites"]:
                                    st.markdown(f"- {site.title()}")
                            else:
                                st.write("No anatomical sites detected")
                        
                        # Show temporal information
                        if entities["temporal_expressions"]:
                            st.markdown("#### Temporal Information")
                            for temporal in entities["temporal_expressions"]:
                                st.markdown(f"- {temporal}")
        
        # Audio Recording Method
        with method_tab2:
            st.markdown("### Audio Symptom Recording")
            st.info("This feature would allow patients to record audio descriptions of their symptoms.")
            
            # Placeholder for audio recording component
            # In a real implementation, we would use streamlit-webrtc or audio-recorder-streamlit
            st.write("Audio recording component would be implemented here.")
            
            # Mock audio controls
            col1, col2, col3 = st.columns(3)
            with col1:
                st.button("Start Recording", key="start_audio")
            with col2:
                st.button("Stop Recording", key="stop_audio")
            with col3:
                st.button("Play Recording", key="play_audio")
            
            st.markdown("#### Transcription Preview")
            st.text_area("Transcribed Text", value="I've been experiencing a headache for the past 3 days, mainly on the right side of my head. It gets worse when I bend over.", height=100, disabled=True)
        
        # Image Upload Method
        with method_tab3:
            st.markdown("### Medical Image Upload")
            st.info("Upload images related to your symptoms (e.g., skin conditions, wounds, etc.)")
            
            uploaded_file = st.file_uploader("Choose an image file", type=["jpg", "jpeg", "png"])
            
            if uploaded_file is not None:
                # Display the uploaded image
                st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
                
                # Mock AI analysis
                with st.spinner("Analyzing image..."):
                    time.sleep(2)  # Simulate processing time
                    
                    st.success("Image analysis complete!")
                    
                    # Mock analysis results
                    st.markdown("#### Image Analysis Results")
                    st.markdown("- **Type:** Skin lesion")
                    st.markdown("- **Characteristics:** Round, well-circumscribed, 1.2cm diameter")
                    st.markdown("- **Color:** Reddish-brown")
                    st.markdown("- **Recommendation:** Clinical evaluation recommended")
        
        # Review of Systems
        st.markdown("### Review of Systems")
        st.info("Please check any symptoms you are currently experiencing")
        
        # Create columns for symptom categories
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### General")
            fever = st.checkbox("Fever", value=st.session_state.patient_data.get("ros_fever", False), key="ros_fever")
            chills = st.checkbox("Chills", value=st.session_state.patient_data.get("ros_chills", False), key="ros_chills")
            fatigue = st.checkbox("Fatigue", value=st.session_state.patient_data.get("ros_fatigue", False), key="ros_fatigue")
            weight_loss = st.checkbox("Weight Loss", value=st.session_state.patient_data.get("ros_weight_loss", False), key="ros_weight_loss")
            
            st.markdown("#### Respiratory")
            cough = st.checkbox("Cough", value=st.session_state.patient_data.get("ros_cough", False), key="ros_cough")
            shortness_breath = st.checkbox("Shortness of Breath", value=st.session_state.patient_data.get("ros_shortness_breath", False), key="ros_shortness_breath")
            wheezing = st.checkbox("Wheezing", value=st.session_state.patient_data.get("ros_wheezing", False), key="ros_wheezing")
        
        with col2:
            st.markdown("#### Cardiovascular")
            chest_pain = st.checkbox("Chest Pain", value=st.session_state.patient_data.get("ros_chest_pain", False), key="ros_chest_pain")
            palpitations = st.checkbox("Palpitations", value=st.session_state.patient_data.get("ros_palpitations", False), key="ros_palpitations")
            edema = st.checkbox("Swelling in Legs", value=st.session_state.patient_data.get("ros_edema", False), key="ros_edema")
            
            st.markdown("#### Gastrointestinal")
            nausea = st.checkbox("Nausea", value=st.session_state.patient_data.get("ros_nausea", False), key="ros_nausea")
            vomiting = st.checkbox("Vomiting", value=st.session_state.patient_data.get("ros_vomiting", False), key="ros_vomiting")
            diarrhea = st.checkbox("Diarrhea", value=st.session_state.patient_data.get("ros_diarrhea", False), key="ros_diarrhea")
            constipation = st.checkbox("Constipation", value=st.session_state.patient_data.get("ros_constipation", False), key="ros_constipation")
        
        with col3:
            st.markdown("#### Neurological")
            headache = st.checkbox("Headache", value=st.session_state.patient_data.get("ros_headache", False), key="ros_headache")
            dizziness = st.checkbox("Dizziness", value=st.session_state.patient_data.get("ros_dizziness", False), key="ros_dizziness")
            numbness = st.checkbox("Numbness/Tingling", value=st.session_state.patient_data.get("ros_numbness", False), key="ros_numbness")
            
            st.markdown("#### Psychiatric")
            anxiety = st.checkbox("Anxiety", value=st.session_state.patient_data.get("ros_anxiety", False), key="ros_anxiety")
            depression = st.checkbox("Depression", value=st.session_state.patient_data.get("ros_depression", False), key="ros_depression")
            sleep_problems = st.checkbox("Sleep Problems", value=st.session_state.patient_data.get("ros_sleep_problems", False), key="ros_sleep_problems")
        
        # Risk Assessment
        st.markdown("### Risk Assessment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### COVID-19 Screening")
            covid_exposure = st.checkbox("Recent COVID-19 exposure", value=st.session_state.patient_data.get("covid_exposure", False))
            covid_symptoms = st.checkbox("COVID-19 symptoms in past 14 days", value=st.session_state.patient_data.get("covid_symptoms", False))
            covid_positive = st.checkbox("Positive COVID-19 test in past 14 days", value=st.session_state.patient_data.get("covid_positive", False))
        
        with col2:
            st.markdown("#### Travel History")
            travel_history = st.selectbox("Recent travel in last 30 days?", 
                                        options=["None", "Domestic", "International"],
                                        index=["None", "Domestic", "International"].index(st.session_state.patient_data.get("travel_history", "None")))
            
            if travel_history != "None":
                travel_location = st.text_input("Travel location", value=st.session_state.patient_data.get("travel_location", ""))
        
        # Allergies
        st.markdown("### Allergies")
        allergies = st.text_area("List any allergies (medications, food, environmental)", 
                               value=st.session_state.patient_data.get("allergies", ""),
                               height=100,
                               placeholder="e.g., Penicillin, peanuts, latex")
        
        # Save all symptom data
        if st.button("Save Symptom Information", key="save_symptoms"):
            # Update session state with review of systems data
            ros_data = {
                "ros_fever": fever,
                "ros_chills": chills,
                "ros_fatigue": fatigue,
                "ros_weight_loss": weight_loss,
                "ros_cough": cough,
                "ros_shortness_breath": shortness_breath,
                "ros_wheezing": wheezing,
                "ros_chest_pain": chest_pain,
                "ros_palpitations": palpitations,
                "ros_edema": edema,
                "ros_nausea": nausea,
                "ros_vomiting": vomiting,
                "ros_diarrhea": diarrhea,
                "ros_constipation": constipation,
                "ros_headache": headache,
                "ros_dizziness": dizziness,
                "ros_numbness": numbness,
                "ros_anxiety": anxiety,
                "ros_depression": depression,
                "ros_sleep_problems": sleep_problems
            }
            
            # Update risk assessment data
            risk_data = {
                "covid_exposure": covid_exposure,
                "covid_symptoms": covid_symptoms,
                "covid_positive": covid_positive,
                "travel_history": travel_history,
                "allergies": allergies
            }
            
            if travel_history != "None":
                risk_data["travel_location"] = travel_location
            
            # Update session state
            st.session_state.patient_data.update(ros_data)
            st.session_state.patient_data.update(risk_data)
            
            st.success("Symptom information saved successfully!")
            
            # Automatically switch to next tab
            time.sleep(1)
            st.experimental_rerun()
    
    # Tab 3: Document Upload
    with tab3:
        st.subheader("Pre-Visit Document Upload")
        
        # Check if patient info is completed
        if not st.session_state.patient_data.get("name"):
            st.warning("Please complete patient registration first.")
            return
        
        st.info("Upload any relevant medical documents for your visit")
        
        # Document type selection
        doc_type = st.selectbox("Document Type", 
                              options=["Lab Results", "Imaging", "Previous Records", "Insurance Card", "Other"],
                              index=0)
        
        # File uploader
        uploaded_file = st.file_uploader(f"Upload {doc_type}", type=["pdf", "jpg", "jpeg", "png", "dcm"])
        
        if uploaded_file is not None:
            # Display file information
            file_details = {
                "Filename": uploaded_file.name,
                "File size": f"{uploaded_file.size / 1024:.2f} KB",
                "File type": uploaded_file.type
            }
            
            st.json(file_details)
            
            # Process based on document type
            if doc_type == "Lab Results":
                st.success("Lab results uploaded successfully!")
                
                # Mock document processing
                with st.spinner("Processing lab results..."):
                    time.sleep(2)  # Simulate processing time
                    
                    # Mock extracted data
                    st.markdown("#### Extracted Lab Values")
                    
                    lab_data = pd.DataFrame({
                        "Test": ["Hemoglobin A1c", "Glucose", "Total Cholesterol", "LDL", "HDL"],
                        "Value": ["5.7", "102", "185", "110", "45"],
                        "Unit": ["%", "mg/dL", "mg/dL", "mg/dL", "mg/dL"],
                        "Reference": ["4.0-5.6", "70-99", "<200", "<100", ">40"],
                        "Flag": ["H", "H", "", "H", ""]
                    })
                    
                    st.dataframe(lab_data)
                    
                    # Save to session state
                    if "documents" not in st.session_state.patient_data:
                        st.session_state.patient_data["documents"] = []
                    
                    st.session_state.patient_data["documents"].append({
                        "type": doc_type,
                        "filename": uploaded_file.name,
                        "extracted_data": lab_data.to_dict(),
                        "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
            
            elif doc_type == "Imaging":
                st.success("Imaging uploaded successfully!")
                
                # Display image if it's an image file
                if uploaded_file.type.startswith("image"):
                    st.image(uploaded_file, caption="Uploaded Image", use_column_width=True)
                else:
                    st.info("DICOM viewer would be implemented here for medical imaging files")
                
                # Save to session state
                if "documents" not in st.session_state.patient_data:
                    st.session_state.patient_data["documents"] = []
                
                st.session_state.patient_data["documents"].append({
                    "type": doc_type,
                    "filename": uploaded_file.name,
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
            
            else:
                st.success(f"{doc_type} uploaded successfully!")
                
                # Save to session state
                if "documents" not in st.session_state.patient_data:
                    st.session_state.patient_data["documents"] = []
                
                st.session_state.patient_data["documents"].append({
                    "type": doc_type,
                    "filename": uploaded_file.name,
                    "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Display uploaded documents
        if "documents" in st.session_state.patient_data and st.session_state.patient_data["documents"]:
            st.markdown("### Uploaded Documents")
            
            for i, doc in enumerate(st.session_state.patient_data["documents"]):
                with st.expander(f"{doc['type']}: {doc['filename']}"):
                    st.write(f"**Upload Time:** {doc['upload_time']}")
                    
                    if "extracted_data" in doc:
                        st.write("**Extracted Data Available**")
        
        # Continue to next stage
        if st.button("Complete Pre-Visit Information", key="complete_intake"):
            # Check if minimum required information is provided
            if not st.session_state.patient_data.get("chief_complaint"):
                st.error("Please provide at least a chief complaint before continuing.")
            else:
                st.success("Pre-visit information completed successfully!")
                st.balloons()
                
                # Move to next stage
                st.session_state.current_stage = 2
                st.experimental_rerun()
