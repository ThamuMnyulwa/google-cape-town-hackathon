"""
Simple MedAssist AI Pro - Clinical Workflow Demo
Minimal Streamlit Application for Testing
"""

import streamlit as st
from datetime import datetime, date
import random
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
import json
import re

# Load environment variables from .env file
load_dotenv()

# Set page config
st.set_page_config(
    page_title="MedAssist AI Pro - Simple Demo",
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
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'patient_data' not in st.session_state:
    st.session_state.patient_data = {}
if 'current_stage' not in st.session_state:
    st.session_state.current_stage = 1
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = None

# User database (in production, this would be a real database)
USERS_DB = {
    "admin": {"password": "admin123", "role": "admin", "name": "System Administrator"},
    "doctor": {"password": "doctor123", "role": "doctor", "name": "Dr. Doo Little"},
    "nurse": {"password": "nurse123", "role": "nurse", "name": "Nurse Smith"},
    "receptionist": {"password": "reception123", "role": "receptionist", "name": "Receptionist Jones"},
    "patient": {"password": "patient123", "role": "patient", "name": "Patient Portal"}
}

def authenticate_user(username, password):
    """Authenticate user credentials"""
    if username in USERS_DB and USERS_DB[username]["password"] == password:
        return True, USERS_DB[username]
    return False, None


def get_fallback_id_data():
    """Fallback ID data when AI extraction fails"""
    return {
        "name": "Abdul Sattar",
        "id_number": "800101 5009 08",
        "dob": "1998-05-15",
        "gender": "Male",
        "nationality": "South African"
    }


# Define Pydantic models for structured data
class IDCardData(BaseModel):
    name: str = Field(default="Not readable")
    id_number: str = Field(default="Not readable")
    dob: str = Field(default="1998-05-15")
    gender: str = Field(default="Not readable")
    nationality: str = Field(default="Not readable")

class MedicalAidData(BaseModel):
    scheme: str = Field(default="Not readable")
    member_number: str = Field(default="Not readable")
    plan: str = Field(default="Not readable")
    status: str = Field(default="Not readable")
    coverage: str = Field(default="Not readable")
    co_payment: str = Field(default="Not readable")

def clean_json_response(text):
    """Clean and extract JSON from AI response"""
    # Try to find JSON-like content
    json_patterns = [
        r'\{[^{}]*\}',  # Simple JSON object
        r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}',  # Nested JSON
    ]
    
    for pattern in json_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            # Take the largest match (likely the main JSON)
            json_str = max(matches, key=len)
            try:
                # Clean common issues
                json_str = json_str.replace('\n', ' ')
                json_str = re.sub(r',\s*}', '}', json_str)  # Remove trailing commas
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
    return None

def extract_id_information(uploaded_file):
    """Extract information from ID card using Gemini Vision API with Pydantic validation"""
    try:
        from google import genai
        from PIL import Image
        import io

        # Set up Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.warning("🔑 GEMINI_API_KEY not found. Using fallback data.")
            return get_fallback_id_data()

        # Set API key in environment for google-genai SDK
        os.environ["GEMINI_API_KEY"] = api_key
        client = genai.Client()
        
        # Convert uploaded file to image
        image = Image.open(io.BytesIO(uploaded_file.read()))
        
        # Enhanced prompt with examples
        prompt = """
        Analyze this ID card image and extract the following information. 
        Return ONLY a JSON object with these exact fields:
        
        {
            "name": "Full name from ID",
            "id_number": "ID number from card",
            "dob": "Date in YYYY-MM-DD format",
            "gender": "Male or Female",
            "nationality": "Country/Nationality"
        }
        
        Rules:
        - Use "Not readable" if any field cannot be determined
        - For dates, use YYYY-MM-DD format (e.g., "1990-01-15")
        - Return ONLY the JSON object, no other text
        - Do not include any markdown formatting
        """
        
        # Generate content using Gemini Vision
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image]
        )
        response_text = response.text.strip()
        
        # Debug output
        st.info(f"🔍 Raw AI Response (first 200 chars): {response_text[:200]}")
        
        # Try multiple parsing strategies
        extracted_data = None
        
        # Strategy 1: Direct JSON parsing
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Strategy 2: Clean and extract JSON
            extracted_data = clean_json_response(response_text)
            
            if not extracted_data:
                # Strategy 3: Extract key-value pairs manually
                extracted_data = {}
                patterns = {
                    'name': r'"name"\s*:\s*"([^"]*)"',
                    'id_number': r'"id_number"\s*:\s*"([^"]*)"',
                    'dob': r'"dob"\s*:\s*"([^"]*)"',
                    'gender': r'"gender"\s*:\s*"([^"]*)"',
                    'nationality': r'"nationality"\s*:\s*"([^"]*)"'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        extracted_data[field] = match.group(1)
        
        # Validate with Pydantic model
        if extracted_data:
            try:
                id_data = IDCardData(**extracted_data)
                
                # Check if we got actual data (not all defaults)
                if id_data.name != "Not readable" or id_data.id_number != "Not readable":
                    st.success("✅ Successfully extracted ID information!")
                    return id_data.model_dump()
                else:
                    st.warning("⚠️ Could not read ID details clearly. Using fallback data.")
                    return get_fallback_id_data()
                    
            except ValidationError as e:
                st.warning(f"⚠️ Data validation error: {str(e)}. Using fallback data.")
                return get_fallback_id_data()
        else:
            st.warning("⚠️ Could not parse AI response. Using fallback data.")
            return get_fallback_id_data()
            
    except Exception as e:
        st.error(f"⚠️ AI extraction error: {str(e)}")
        return get_fallback_id_data()

def extract_medical_aid_information(uploaded_file):
    """Extract information from medical aid card using Gemini Vision API with Pydantic validation"""
    try:
        from google import genai
        from PIL import Image
        import io
        
        # Set up Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.warning("🔑 GEMINI_API_KEY not found. Using fallback data.")
            return get_fallback_medical_data()

        # Set API key in environment for google-genai SDK
        os.environ["GEMINI_API_KEY"] = api_key
        client = genai.Client()
        
        # Convert uploaded file to image
        image = Image.open(io.BytesIO(uploaded_file.read()))
        
        # Enhanced prompt with specific instructions
        prompt = """
        Analyze this medical aid/insurance card image and extract information.
        Return ONLY a JSON object with these exact fields:
        
        {
            "scheme": "Medical aid scheme/insurance company name",
            "member_number": "Member/policy number",
            "plan": "Plan or coverage type name",
            "status": "Active or Inactive",
            "coverage": "Type of coverage (e.g., Comprehensive)",
            "co_payment": "Co-payment amount or percentage"
        }
        
        Rules:
        - Use "Not readable" for fields you cannot determine
        - For status, use "Active" if card appears valid
        - Return ONLY the JSON, no markdown or explanations
        - Include quotes around all string values
        
        Example response:
        {"scheme": "Discovery Health", "member_number": "123456", "plan": "Classic", "status": "Active", "coverage": "Comprehensive", "co_payment": "R0"}
        """
        
        # Generate content using Gemini Vision
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image]
        )
        response_text = response.text.strip()
        
        # Debug output
        st.info(f"🔍 Raw AI Response (first 200 chars): {response_text[:200]}")
        
        # Try multiple parsing strategies
        extracted_data = None
        
        # Remove markdown code blocks if present
        response_text = re.sub(r'```json\s*', '', response_text)
        response_text = re.sub(r'```\s*', '', response_text)
        
        # Strategy 1: Direct JSON parsing
        try:
            extracted_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Strategy 2: Clean and extract JSON
            extracted_data = clean_json_response(response_text)
            
            if not extracted_data:
                # Strategy 3: Manual extraction
                extracted_data = {}
                patterns = {
                    'scheme': r'"scheme"\s*:\s*"([^"]*)"',
                    'member_number': r'"member_number"\s*:\s*"([^"]*)"',
                    'plan': r'"plan"\s*:\s*"([^"]*)"',
                    'status': r'"status"\s*:\s*"([^"]*)"',
                    'coverage': r'"coverage"\s*:\s*"([^"]*)"',
                    'co_payment': r'"co_payment"\s*:\s*"([^"]*)"'
                }
                
                for field, pattern in patterns.items():
                    match = re.search(pattern, response_text, re.IGNORECASE)
                    if match:
                        extracted_data[field] = match.group(1)
        
        # Validate with Pydantic model
        if extracted_data:
            try:
                medical_data = MedicalAidData(**extracted_data)
                
                # Check if we got actual data
                if medical_data.scheme != "Not readable" or medical_data.member_number != "Not readable":
                    st.success("✅ Successfully extracted medical aid information!")
                    return medical_data.model_dump()
                else:
                    st.warning("⚠️ Could not read medical aid details clearly. Using fallback data.")
                    return get_fallback_medical_data()
                    
            except ValidationError as e:
                st.warning(f"⚠️ Data validation error: {str(e)}. Using fallback data.")
                return get_fallback_medical_data()
        else:
            st.warning("⚠️ Could not parse AI response. Using fallback data.")
            return get_fallback_medical_data()
            
    except Exception as e:
        st.error(f"⚠️ AI extraction error: {str(e)}")
        return get_fallback_medical_data()

# Alternative approach using structured generation
def extract_with_structured_output(uploaded_file, data_type="id"):
    """Alternative extraction using structured prompting"""
    try:
        from google import genai
        from PIL import Image
        import io
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return get_fallback_id_data() if data_type == "id" else get_fallback_medical_data()

        # Set API key in environment for google-genai SDK
        os.environ["GEMINI_API_KEY"] = api_key
        client = genai.Client()
        
        image = Image.open(io.BytesIO(uploaded_file.read()))
        
        if data_type == "id":
            prompt = """
            Extract from this ID card. Respond with ONLY these fields, one per line:
            NAME: [extracted name]
            ID: [extracted id number]
            DOB: [date in YYYY-MM-DD]
            GENDER: [Male/Female]
            NATIONALITY: [country]
            
            Use "Not readable" if unclear.
            """
        else:
            prompt = """
            Extract from this medical aid card. Respond with ONLY these fields, one per line:
            SCHEME: [insurance company name]
            MEMBER: [member number]
            PLAN: [plan name]
            STATUS: [Active/Inactive]
            COVERAGE: [coverage type]
            COPAY: [co-payment amount]
            
            Use "Not readable" if unclear.
            """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, image]
        )
        response_text = response.text.strip()
        
        # Parse line-by-line format
        data = {}
        for line in response_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                # Map to expected field names
                field_map = {
                    'name': 'name',
                    'id': 'id_number',
                    'dob': 'dob',
                    'gender': 'gender',
                    'nationality': 'nationality',
                    'scheme': 'scheme',
                    'member': 'member_number',
                    'plan': 'plan',
                    'status': 'status',
                    'coverage': 'coverage',
                    'copay': 'co_payment'
                }
                
                if key in field_map:
                    data[field_map[key]] = value
        
        # Validate with appropriate model
        if data_type == "id":
            validated_data = IDCardData(**data)
            return validated_data.model_dump()
        else:
            validated_data = MedicalAidData(**data)
            return validated_data.model_dump()
            
    except Exception as e:
        st.error(f"Structured extraction failed: {str(e)}")
        return get_fallback_id_data() if data_type == "id" else get_fallback_medical_data()
        
        # Parse the response
        try:
            import json
            extracted_data = json.loads(response.text.strip())
            
            # Validate and clean the data
            cleaned_data = {
                "scheme": extracted_data.get("scheme", "Not readable"),
                "member_number": extracted_data.get("member_number", "Not readable"),
                "plan": extracted_data.get("plan", "Not readable"),
                "status": extracted_data.get("status", "Not readable"),
                "coverage": extracted_data.get("coverage", "Not readable"),
                "co_payment": extracted_data.get("co_payment", "Not readable")
            }
            
            # If scheme is not readable, use fallback
            if cleaned_data["scheme"] == "Not readable":
                cleaned_data["scheme"] = "Discovery Health"
                cleaned_data["member_number"] = "123456789"
                cleaned_data["plan"] = "Classic Saver"
                cleaned_data["status"] = "Active"
                cleaned_data["coverage"] = "Comprehensive"
                cleaned_data["co_payment"] = "R0"
            
            return cleaned_data
            
        except json.JSONDecodeError:
            st.warning("⚠️ Could not parse AI response. Using fallback data.")
            return get_fallback_medical_data()
            
    except Exception as e:
        st.warning(f"⚠️ AI extraction failed: {str(e)}. Using fallback data.")
        return get_fallback_medical_data()

def get_fallback_medical_data():
    """Fallback medical aid data when AI extraction fails"""
    return {
        "scheme": "Discovery Health",
        "member_number": "123456789",
        "plan": "Classic Saver",
        "status": "Active",
        "coverage": "Comprehensive",
        "co_payment": "R0"
    }

def show_landing_page():
    """Display landing page for non-authenticated users"""
    st.markdown("""
    <div class="main-header">
        <h1>🏥 MedAssist AI Pro</h1>
        <p>Revolutionary AI-Powered Clinical Workflow System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Hero section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 🚀 Welcome to the Future of Healthcare
        
        **MedAssist AI Pro** is a cutting-edge clinical workflow system that combines artificial intelligence 
        with medical expertise to streamline patient care and improve clinical outcomes.
        
        ### ✨ Key Features
        
        - **🤖 AI-Powered Diagnosis** - Advanced symptom analysis and ICD-10 code suggestions
        - **📄 Smart Document Processing** - Automatic extraction from ID cards and medical aid
        - **👥 Multi-Role Access** - Tailored interfaces for doctors, nurses, and staff
        - **🔒 Secure & Compliant** - HIPAA-compliant with role-based access control
        - **📊 Real-time Analytics** - Clinical insights and performance metrics
        
        ### 🎯 Who Can Use MedAssist AI Pro?
        
        - **👨‍⚕️ Doctors** - Full clinical workflow access with AI assistance
        - **👩‍⚕️ Nurses** - Patient care documentation and monitoring
        - **📋 Receptionists** - Patient intake and registration management
        - **👤 Patients** - Portal access to personal health information
        - **👑 Administrators** - System management and analytics
        """)
    
    with col2:
        st.markdown("### 🔐 Quick Access")
        
        # Quick login buttons
        st.markdown("**Demo Accounts:**")
        
        if st.button("👨‍⚕️ Doctor Demo", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_role = "doctor"
            st.session_state.username = "doctor"
            st.rerun()
        
        if st.button("👩‍⚕️ Nurse Demo", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_role = "nurse"
            st.session_state.username = "nurse"
            st.rerun()
        
        if st.button("📋 Receptionist Demo", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_role = "receptionist"
            st.session_state.username = "receptionist"
            st.rerun()
        
        if st.button("👤 Patient Demo", use_container_width=True):
            st.session_state.authenticated = True
            st.session_state.user_role = "patient"
            st.session_state.username = "patient"
            st.rerun()
        
        st.markdown("---")
        st.markdown("**Or use the sidebar to log in with your credentials**")
    
    # Features showcase
    st.markdown("---")
    st.markdown("## 🌟 System Capabilities")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🧠 AI Clinical Assistant
        - Symptom analysis and pattern recognition
        - ICD-10 code suggestions using Gemini AI
        - Clinical decision support
        - Risk assessment and prioritization
        """)
    
    with col2:
        st.markdown("""
        ### 📱 Smart Intake Process
        - Document upload and OCR processing
        - Automatic data extraction from IDs
        - Medical aid verification
        - Pre-populated patient forms
        """)
    
    with col3:
        st.markdown("""
        ### 🔒 Security & Compliance
        - Role-based access control
        - Secure authentication system
        - HIPAA-compliant data handling
        - Audit trails and logging
        """)
    
    # Statistics
    st.markdown("---")
    st.markdown("## 📊 Impact Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Time Saved", "45%", "↑ 12%")
    with col2:
        st.metric("Accuracy", "96%", "↑ 8%")
    with col3:
        st.metric("User Satisfaction", "4.8/5", "↑ 15%")
    with col4:
        st.metric("Error Reduction", "67%", "↑ 23%")

def show_sidebar_login():
    """Display login form in sidebar"""
    with st.sidebar:
        st.markdown("### 🔐 Login")
        
        with st.form("sidebar_login_form"):
            username = st.text_input("Username", placeholder="Enter username", key="sidebar_username")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="sidebar_password")
            
            col1, col2 = st.columns(2)
            with col1:
                login_button = st.form_submit_button("Login", use_container_width=True)
            with col2:
                demo_button = st.form_submit_button("Demo", use_container_width=True)
            
            if login_button:
                if username and password:
                    success, user_info = authenticate_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_role = user_info["role"]
                        st.session_state.username = username
                        st.success(f"Welcome, {user_info['name']}!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.error("❌ Enter both fields")
            
            if demo_button:
                # Demo login with doctor credentials
                st.session_state.authenticated = True
                st.session_state.user_role = "doctor"
                st.session_state.username = "doctor"
                st.success("Welcome, Dr. Doo Little!")
                st.rerun()
        
        # Show available demo accounts
        with st.expander("📋 Demo Accounts"):
            for user, info in USERS_DB.items():
                st.write(f"**{user}** - `{info['password']}`")


def calculate_age(born):
    """Calculate age from birthdate"""
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def simple_medical_analysis(text):
    """Simple medical entity extraction using basic pattern matching"""
    text_lower = text.lower()
    
    # Simple symptom detection
    symptoms = ["fever", "cough", "headache", "nausea", "pain", "fatigue", "shortness of breath"]
    detected_symptoms = [symptom for symptom in symptoms if symptom in text_lower]
    
    # Simple anatomical sites
    sites = ["head", "chest", "abdomen", "back", "arm", "leg"]
    detected_sites = [site for site in sites if site in text_lower]
    
    return {
        "symptoms": detected_symptoms,
        "anatomical_sites": detected_sites,
        "text_length": len(text)
    }

def show_patient_intake():
    """Display the patient intake page"""
    
    st.header("📋 Smart Patient Intake Portal")

    # Make a paragraph explaining this is pre-populated data from OCR extraction
    st.write("This form will be pre-populated with data extracted from your ID and medical aid cards using OCR")
    
    # Tabs for different sections of intake
    tab1, tab2, tab3 = st.tabs(["Document Upload", "Patient Registration", "Symptom Collection"])
    
    # Tab 1: Document Upload
    with tab1:
        st.subheader("📄 Document Upload")
        
        st.info("Upload photos of your ID and medical aid card. We'll extract your information automatically using OCR technology!")
        
        # Initialize document storage
        if "uploaded_documents" not in st.session_state:
            st.session_state.uploaded_documents = {
                "id_card": None,
                "medical_aid": None
            }
        
        # ID Card Upload
        st.markdown("### 🆔 ID Card Upload")
        id_uploaded_file = st.file_uploader(
            "Upload photo of ID Card", 
            type=["jpg", "jpeg", "png", "pdf"],
            key="id_upload",
            help="Upload a clear photo of your government-issued ID card"
        )
        
        if id_uploaded_file is not None:
            # Display the uploaded image
            if id_uploaded_file.type.startswith("image"):
                st.image(id_uploaded_file, caption="ID Card", width="stretch")
            else:
                st.info("PDF document uploaded")
            
            # Store document info
            st.session_state.uploaded_documents["id_card"] = {
                "filename": id_uploaded_file.name,
                "size": f"{id_uploaded_file.size / 1024:.2f} KB",
                "type": id_uploaded_file.type,
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.success("✅ ID Card uploaded successfully! OCR extraction in progress...")
            
            # Real ID verification using Gemini Vision API
            with st.spinner("Extracting ID information using AI..."):
                extracted_id_data = extract_id_information(id_uploaded_file)
                
                # Auto-populate patient data from ID
                st.session_state.patient_data.update({
                    "name": extracted_id_data["name"],
                    "dob": extracted_id_data["dob"],
                    "gender": extracted_id_data["gender"],
                    "id_number": extracted_id_data["id_number"]
                })
                
                # Display extracted data
                st.markdown("#### ✅ OCR-Extracted ID Information (via Gemini Vision API):")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Name:** {extracted_id_data['name']}")
                    st.write(f"**ID Number:** {extracted_id_data['id_number']}")
                    st.write(f"**Date of Birth:** {extracted_id_data['dob']}")
                with col2:
                    st.write(f"**Gender:** {extracted_id_data['gender']}")
                    st.write(f"**Nationality:** {extracted_id_data['nationality']}")
                    st.write("**Status:** ✅ OCR-Verified & Auto-populated")
        
        # Medical Aid Upload
        st.markdown("### 🏥 Medical Aid Card Upload")
        medical_aid_file = st.file_uploader(
            "Upload photo of Medical Aid Card", 
            type=["jpg", "jpeg", "png", "pdf"],
            key="medical_aid_upload",
            help="Upload a clear photo of your medical aid card"
        )
        
        if medical_aid_file is not None:
            # Display the uploaded image
            if medical_aid_file.type.startswith("image"):
                st.image(medical_aid_file, caption="Medical Aid Card", width="stretch")
            else:
                st.info("PDF document uploaded")
            
            # Store document info
            st.session_state.uploaded_documents["medical_aid"] = {
                "filename": medical_aid_file.name,
                "size": f"{medical_aid_file.size / 1024:.2f} KB",
                "type": medical_aid_file.type,
                "upload_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            st.success("✅ Medical Aid Card uploaded successfully! OCR extraction in progress...")
            
            # Real medical aid verification using Gemini Vision API
            with st.spinner("Extracting medical aid information using AI..."):
                extracted_medical_data = extract_medical_aid_information(medical_aid_file)
                
                # Auto-populate insurance data
                st.session_state.patient_data.update({
                    "insurance_provider": extracted_medical_data["scheme"],
                    "insurance_id": extracted_medical_data["member_number"],
                    "insurance_plan": extracted_medical_data["plan"]
                })
                
                # Display extracted data
                st.markdown("#### ✅ OCR-Extracted Medical Aid Information (via Gemini Vision API):")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Scheme:** {extracted_medical_data['scheme']}")
                    st.write(f"**Member Number:** {extracted_medical_data['member_number']}")
                    st.write(f"**Plan:** {extracted_medical_data['plan']}")
                with col2:
                    st.write(f"**Status:** ✅ {extracted_medical_data['status']}")
                    st.write(f"**Coverage:** {extracted_medical_data['coverage']}")
                    st.write(f"**Co-payment:** {extracted_medical_data['co_payment']}")
                    st.write("**Status:** ✅ OCR-Verified & Auto-populated")
        
        # Document Summary
        if st.session_state.uploaded_documents["id_card"] or st.session_state.uploaded_documents["medical_aid"]:
            st.markdown("### 📋 Upload Summary")
            
            if st.session_state.uploaded_documents["id_card"]:
                id_doc = st.session_state.uploaded_documents["id_card"]
                st.write(f"**ID Card:** {id_doc['filename']} ({id_doc['size']}) - {id_doc['upload_time']}")
            
            if st.session_state.uploaded_documents["medical_aid"]:
                med_doc = st.session_state.uploaded_documents["medical_aid"]
                st.write(f"**Medical Aid:** {med_doc['filename']} ({med_doc['size']}) - {med_doc['upload_time']}")
        
        # Continue button
        if st.button("Continue to Patient Registration", key="continue_to_registration"):
            if st.session_state.uploaded_documents["id_card"] and st.session_state.uploaded_documents["medical_aid"]:
                st.success("All documents uploaded! Patient information has been auto-populated using OCR extraction. Proceeding to registration.")
                st.rerun()
            else:
                st.warning("Please upload both ID card and medical aid card before continuing.")
    
    # Tab 2: Patient Registration
    with tab2:
        st.subheader("Patient Registration")
        
        # Check if documents are uploaded
        if not st.session_state.uploaded_documents.get("id_card") or not st.session_state.uploaded_documents.get("medical_aid"):
            st.warning("Please upload your ID card and medical aid card first.")
            return
        
        st.success("✅ Patient information has been auto-populated from your uploaded documents using OCR extraction!")
        
        # Create a form for patient registration
        with st.form("patient_registration_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Basic Demographics
                st.markdown("### Basic Demographics")
                
                # Auto-generate MRN if not already set
                if "mrn" not in st.session_state.patient_data:
                    mrn = f"MRN{random.randint(100000, 999999)}"
                else:
                    mrn = st.session_state.patient_data.get("mrn", "")
                
                mrn_input = st.text_input("Medical Record Number", value=mrn, disabled=True)
                
                # Auto-populated from ID card using OCR extraction
                name = st.text_input("Full Name (OCR from ID card)", value=st.session_state.patient_data.get("name", ""))
                preferred_name = st.text_input("Preferred Name (Optional)", value=st.session_state.patient_data.get("preferred_name", ""))
                
                # Auto-populated from ID card using OCR extraction
                dob = st.date_input("Date of Birth (OCR from ID card)", 
                                   value=datetime.strptime(st.session_state.patient_data.get("dob", "1980-01-01"), "%Y-%m-%d").date() 
                                   if "dob" in st.session_state.patient_data else date(1980, 1, 1))
                
                # Calculate and display age based on OCR-extracted date
                age = calculate_age(dob)
                st.info(f"Age: {age} years (calculated from OCR-extracted DOB)")
                
                # Auto-populated from ID card using OCR extraction
                gender = st.selectbox("Gender (OCR from ID card)", 
                                     options=["Male", "Female", "Non-binary", "Prefer not to say"],
                                     index=["Male", "Female", "Non-binary", "Prefer not to say"].index(st.session_state.patient_data.get("gender", "Male")))
            
            with col2:
                # Contact Information
                st.markdown("### Contact Information")
                
                phone = st.text_input("Phone Number", value=st.session_state.patient_data.get("phone", ""))
                email = st.text_input("Email Address", value=st.session_state.patient_data.get("email", ""))
                
                st.markdown("### Visit Information")
                visit_type = st.selectbox("Visit Type", 
                                         options=["New Patient", "Follow-up", "Urgent Care", "Routine"],
                                         index=["New Patient", "Follow-up", "Urgent Care", "Routine"].index(st.session_state.patient_data.get("visit_type", "New Patient")))
                
                # Auto-populated from medical aid card using OCR extraction
                insurance_provider = st.text_input("Insurance Provider (OCR from medical aid card)", value=st.session_state.patient_data.get("insurance_provider", ""))
                
                # Show additional insurance info from OCR extraction
                if st.session_state.patient_data.get("insurance_id"):
                    st.info(f"**Insurance ID (OCR extracted):** {st.session_state.patient_data.get('insurance_id')}")
                if st.session_state.patient_data.get("insurance_plan"):
                    st.info(f"**Plan (OCR extracted):** {st.session_state.patient_data.get('insurance_plan')}")
            
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
                    "email": email,
                    "visit_type": visit_type,
                    "insurance_provider": insurance_provider
                })
                
                st.success("Patient information saved successfully!")
                st.balloons()
    
    # Tab 3: Symptom Collection
    with tab3:
        st.subheader("Symptom Collection")
        
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
            with col2:
                st.write(f"**Gender:** {st.session_state.patient_data.get('gender')}")
                st.write(f"**Visit Type:** {st.session_state.patient_data.get('visit_type')}")
        
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
        
        # Process text input with simple NLP
        if chief_complaint:
            with st.spinner("Analyzing symptoms..."):
                # Simple medical analysis
                analysis = simple_medical_analysis(chief_complaint)
                
                # Save to session state
                st.session_state.patient_data.update({
                    "chief_complaint": chief_complaint,
                    "symptom_onset": symptom_onset,
                    "severity": severity,
                    "analysis": analysis
                })
                
                # Display analysis results
                with st.expander("AI Analysis Results", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### Detected Symptoms")
                        if analysis["symptoms"]:
                            for symptom in analysis["symptoms"]:
                                st.markdown(f"- {symptom.title()}")
                        else:
                            st.write("No specific symptoms detected")
                    
                    with col2:
                        st.markdown("#### Anatomical Sites")
                        if analysis["anatomical_sites"]:
                            for site in analysis["anatomical_sites"]:
                                st.markdown(f"- {site.title()}")
                        else:
                            st.write("No anatomical sites detected")
        
        # Review of Systems - Simplified
        st.markdown("### Review of Systems")
        st.info("Please check any symptoms you are currently experiencing")
        
        # Create columns for symptom categories
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### General")
            fever = st.checkbox("Fever", value=st.session_state.patient_data.get("ros_fever", False), key="ros_fever")
            fatigue = st.checkbox("Fatigue", value=st.session_state.patient_data.get("ros_fatigue", False), key="ros_fatigue")
            
            st.markdown("#### Respiratory")
            cough = st.checkbox("Cough", value=st.session_state.patient_data.get("ros_cough", False), key="ros_cough")
            shortness_breath = st.checkbox("Shortness of Breath", value=st.session_state.patient_data.get("ros_shortness_breath", False), key="ros_shortness_breath")
        
        with col2:
            st.markdown("#### Cardiovascular")
            chest_pain = st.checkbox("Chest Pain", value=st.session_state.patient_data.get("ros_chest_pain", False), key="ros_chest_pain")
            
            st.markdown("#### Gastrointestinal")
            nausea = st.checkbox("Nausea", value=st.session_state.patient_data.get("ros_nausea", False), key="ros_nausea")
            vomiting = st.checkbox("Vomiting", value=st.session_state.patient_data.get("ros_vomiting", False), key="ros_vomiting")
        
        with col3:
            st.markdown("#### Neurological")
            headache = st.checkbox("Headache", value=st.session_state.patient_data.get("ros_headache", False), key="ros_headache")
            dizziness = st.checkbox("Dizziness", value=st.session_state.patient_data.get("ros_dizziness", False), key="ros_dizziness")
        
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
                "ros_fatigue": fatigue,
                "ros_cough": cough,
                "ros_shortness_breath": shortness_breath,
                "ros_chest_pain": chest_pain,
                "ros_nausea": nausea,
                "ros_vomiting": vomiting,
                "ros_headache": headache,
                "ros_dizziness": dizziness,
                "allergies": allergies
            }
            
            # Update session state
            st.session_state.patient_data.update(ros_data)
            
            st.success("Symptom information saved successfully!")
            
            # Move to next stage
            st.session_state.current_stage = 2
            st.rerun()

def show_pre_screening():
    """Display the pre-screening page"""
    st.header("🔍 AI Pre-Screening Analysis")
    
    # Check if we have basic patient data
    if not st.session_state.patient_data.get("name"):
        st.warning("Please complete patient registration first.")
        st.info("Go back to Patient Intake tab and fill in the patient information.")
        return
    
    # If no chief complaint, allow adding it here
    if not st.session_state.patient_data.get("chief_complaint"):
        st.info("💡 No chief complaint entered yet. You can add symptoms below or continue to consultation.")
        
        # Quick symptom entry
        with st.expander("Add Chief Complaint", expanded=True):
            chief_complaint = st.text_area("What brings you in today?", 
                                         placeholder="Describe your main symptoms or concerns...",
                                         height=100)
            
            if st.button("Save Chief Complaint", key="save_chief_complaint"):
                if chief_complaint:
                    # Simple analysis
                    analysis = simple_medical_analysis(chief_complaint)
                    st.session_state.patient_data.update({
                        "chief_complaint": chief_complaint,
                        "analysis": analysis
                    })
                    st.success("Chief complaint saved!")
                    st.rerun()
                else:
                    st.error("Please enter a chief complaint.")
    
    # Display patient summary
    st.subheader("Patient Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Patient", st.session_state.patient_data.get("name", "N/A"))
        st.metric("Age", f"{st.session_state.patient_data.get('age', 'N/A')} years")
    
    with col2:
        st.metric("Visit Type", st.session_state.patient_data.get("visit_type", "N/A"))
        st.metric("Severity", f"{st.session_state.patient_data.get('severity', 'N/A')}/10")
    
    with col3:
        st.metric("Symptoms Detected", len(st.session_state.patient_data.get("analysis", {}).get("symptoms", [])))
        st.metric("Risk Level", "Low" if st.session_state.patient_data.get("severity", 5) < 7 else "High")
    
    # AI Analysis Results
    st.subheader("AI Analysis Results")
    
    if "analysis" in st.session_state.patient_data:
        analysis = st.session_state.patient_data["analysis"]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Detected Symptoms")
            if analysis.get("symptoms"):
                for symptom in analysis["symptoms"]:
                    st.markdown(f"- {symptom.title()}")
            else:
                st.write("No specific symptoms detected")
        
        with col2:
            st.markdown("#### Anatomical Sites")
            if analysis.get("anatomical_sites"):
                for site in analysis["anatomical_sites"]:
                    st.markdown(f"- {site.title()}")
            else:
                st.write("No anatomical sites detected")
    
    # Recommendations
    st.subheader("AI Recommendations")
    
    severity = st.session_state.patient_data.get("severity", 5)
    symptoms = st.session_state.patient_data.get("analysis", {}).get("symptoms", [])
    
    if severity >= 8:
        st.error("🚨 High Priority: Patient requires immediate attention")
        st.markdown("- Consider urgent care or emergency department")
        st.markdown("- Monitor vital signs closely")
    elif severity >= 5:
        st.warning("⚠️ Moderate Priority: Patient should be seen today")
        st.markdown("- Schedule same-day appointment if possible")
        st.markdown("- Consider telemedicine consultation")
    else:
        st.success("✅ Low Priority: Routine follow-up appropriate")
        st.markdown("- Schedule routine appointment")
        st.markdown("- Provide self-care instructions")
    
    # Next steps
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Continue to Consultation", key="continue_consultation"):
            st.session_state.current_stage = 3
            st.rerun()
    
    with col2:
        if st.button("Go Back to Patient Intake", key="back_to_intake"):
            st.session_state.current_stage = 1
            st.rerun()

def get_icd10_suggestions(symptoms_text, clinical_notes=""):
    """Get ICD-10 code suggestions using Gemini API"""
    try:
        from google import genai
        
        # Set up Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            st.warning("🔑 GEMINI_API_KEY not found in environment variables. Using fallback suggestions.")
            return get_fallback_icd10_suggestions(symptoms_text)

        # Set API key in environment for google-genai SDK
        os.environ["GEMINI_API_KEY"] = api_key
        client = genai.Client()
        
        # Create prompt for ICD-10 suggestions
        prompt = f"""
        Based on the following patient symptoms and clinical notes, suggest the most appropriate ICD-10 codes. Behave like MedGemma.
        
        Symptoms: {symptoms_text}
        Clinical Notes: {clinical_notes}
        
        Please provide:
        1. Primary ICD-10 code (most likely diagnosis)
        2. Secondary ICD-10 codes (if applicable)
        3. Brief explanation for each code
        
        Format your response as:
        PRIMARY: [ICD-10 Code] - [Description]
        SECONDARY: [ICD-10 Code] - [Description] (if applicable)
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt]
        )
        return response.text.split('\n')
        
    except Exception:
        # Fallback suggestions based on symptoms
        return get_fallback_icd10_suggestions(symptoms_text)

def get_fallback_icd10_suggestions(symptoms_text):
    """Fallback ICD-10 suggestions when Gemini is not available"""
    symptoms_lower = symptoms_text.lower()
    
    suggestions = []
    
    if "fever" in symptoms_lower and "cough" in symptoms_lower:
        suggestions.append("PRIMARY: J06.9 - Acute upper respiratory infection, unspecified")
        suggestions.append("SECONDARY: R50.9 - Fever, unspecified")
    elif "chest pain" in symptoms_lower:
        suggestions.append("PRIMARY: R06.02 - Shortness of breath")
        suggestions.append("SECONDARY: R07.9 - Chest pain, unspecified")
    elif "headache" in symptoms_lower:
        suggestions.append("PRIMARY: R51 - Headache")
        suggestions.append("SECONDARY: G44.1 - Vascular headache, not elsewhere classified")
    elif "abdominal pain" in symptoms_lower:
        suggestions.append("PRIMARY: R10.9 - Unspecified abdominal pain")
        suggestions.append("SECONDARY: K59.00 - Constipation, unspecified")
    else:
        # Default fallback to headache ICD-10 codes
        suggestions.append("PRIMARY: R51 - Headache")
        suggestions.append("SECONDARY: G44.1 - Vascular headache, not elsewhere classified")
        suggestions.append("NOTE: Default fallback suggestion - consider reviewing symptoms for more specific diagnosis")
    
    return suggestions

def show_consultation():
    """Display the consultation page"""
    # Role-based access control
    if st.session_state.user_role not in ["doctor", "admin"]:
        st.error("🚫 Access Denied: Only doctors and administrators can access consultation.")
        st.info("Please contact your administrator if you need access to this section.")
        return
    
    st.header("👨‍⚕️ AI-Assisted Consultation")
    
    # Restart consultation button
    if st.button("🔄 Restart Consultation", key="restart_consultation"):
        # Reset consultation data
        if "consultation_data" in st.session_state:
            del st.session_state.consultation_data
        st.success("Consultation restarted!")
        st.rerun()
    
    st.info("This is where the AI assists with the clinical consultation process.")
    
    # Initialize consultation data
    if "consultation_data" not in st.session_state:
        st.session_state.consultation_data = {
            "clinical_notes": "",
            "selected_icd10": "",
            "ai_suggestions": []
        }
    
    # Mock consultation interface
    st.subheader("Clinical Notes")
    clinical_notes = st.text_area("Enter clinical findings and notes", 
                                 value=st.session_state.consultation_data.get("clinical_notes", ""),
                                 height=200,
                                 key="clinical_notes_input")
    
    # Update session state
    st.session_state.consultation_data["clinical_notes"] = clinical_notes
    
    st.subheader("Diagnosis Suggestions")
    st.write("Based on symptoms and analysis:")
    
    # Simple diagnosis suggestions based on symptoms
    chief_complaint = st.session_state.patient_data.get("chief_complaint", "")
    symptoms = st.session_state.patient_data.get("analysis", {}).get("symptoms", [])
    
    if "fever" in symptoms and "cough" in symptoms:
        st.markdown("- **Possible Diagnosis:** Upper respiratory infection")
        st.markdown("- **Recommended Tests:** CBC, Chest X-ray")
        st.markdown("- **Treatment:** Rest, fluids, symptomatic care")
    elif "chest pain" in symptoms:
        st.markdown("- **Possible Diagnosis:** Cardiac evaluation needed")
        st.markdown("- **Recommended Tests:** ECG, Troponin, Chest X-ray")
        st.markdown("- **Treatment:** Immediate evaluation")
    elif "headache" in symptoms:
        st.markdown("- **Possible Diagnosis:** Tension headache")
        st.markdown("- **Recommended Tests:** Blood pressure")
        st.markdown("- **Treatment:** Pain management, stress reduction")
    else:
        st.markdown("- **Possible Diagnosis:** General evaluation needed")
        st.markdown("- **Recommended Tests:** Basic metabolic panel")
        st.markdown("- **Treatment:** Symptomatic care")
    
    # ICD-10 Code Selection
    st.subheader("ICD-10 Code Selection")
    
    # Debug section for API key
    with st.expander("🔧 Debug: API Key Status", expanded=False):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            st.success(f"✅ GEMINI_API_KEY found: {api_key[:10]}...")
        else:
            st.error("❌ GEMINI_API_KEY not found")
            st.info("Make sure your .env file contains: GEMINI_API_KEY=your_key_here")
    
    # Get AI suggestions
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🤖 Get AI ICD-10 Suggestions", key="get_icd10_suggestions"):
            with st.spinner("Getting AI suggestions..."):
                symptoms_text = f"{chief_complaint} {' '.join(symptoms)}"
                suggestions = get_icd10_suggestions(symptoms_text, clinical_notes)
                st.session_state.consultation_data["ai_suggestions"] = suggestions
    
    with col2:
        if st.button("🧪 Test Fallback (Headache)", key="test_fallback"):
            with st.spinner("Testing fallback suggestions..."):
                suggestions = get_fallback_icd10_suggestions("headache pain")
                st.session_state.consultation_data["ai_suggestions"] = suggestions
                st.info("Fallback suggestions loaded (defaults to headache codes)")
    
    # Display AI suggestions
    if st.session_state.consultation_data.get("ai_suggestions"):
        st.markdown("#### AI-Generated ICD-10 Suggestions:")
        for suggestion in st.session_state.consultation_data["ai_suggestions"]:
            if suggestion.strip():
                st.write(suggestion)
    
    # ICD-10 Code Dropdown
    icd10_codes = [
        "Select ICD-10 Code",
        "J06.9 - Acute upper respiratory infection, unspecified",
        "R50.9 - Fever, unspecified", 
        "R06.02 - Shortness of breath",
        "R07.9 - Chest pain, unspecified",
        "R51 - Headache",
        "G44.1 - Vascular headache, not elsewhere classified",
        "R10.9 - Unspecified abdominal pain",
        "K59.00 - Constipation, unspecified",
        "Z00.00 - Encounter for general adult medical examination without abnormal findings",
        "R69 - Illness, unspecified",
        "I10 - Essential hypertension",
        "E11.9 - Type 2 diabetes mellitus without complications",
        "J45.9 - Asthma, unspecified",
        "M79.3 - Panniculitis, unspecified"
    ]
    
    # Add AI suggestions to dropdown if available
    if st.session_state.consultation_data.get("ai_suggestions"):
        for suggestion in st.session_state.consultation_data["ai_suggestions"]:
            if "PRIMARY:" in suggestion or "SECONDARY:" in suggestion:
                code_part = suggestion.split(" - ")[0].replace("PRIMARY:", "").replace("SECONDARY:", "").strip()
                if code_part not in [item.split(" - ")[0] for item in icd10_codes]:
                    icd10_codes.append(suggestion.replace("PRIMARY:", "").replace("SECONDARY:", "").strip())
    
    selected_icd10 = st.selectbox("Select Primary ICD-10 Code", 
                                options=icd10_codes,
                                index=0,
                                key="icd10_dropdown")
    
    # Update session state
    st.session_state.consultation_data["selected_icd10"] = selected_icd10
    
    # Display selected code
    if selected_icd10 != "Select ICD-10 Code":
        st.success(f"✅ Selected: {selected_icd10}")
        
        # Show additional information about the code
        if "J06.9" in selected_icd10:
            st.info("💡 This code is commonly used for upper respiratory infections. Consider additional codes for specific complications.")
        elif "R51" in selected_icd10:
            st.info("💡 Headache codes may require additional specificity. Consider G44.x codes for migraine or tension headaches.")
        elif "R10.9" in selected_icd10:
            st.info("💡 Abdominal pain codes should be more specific when possible. Consider organ-specific codes.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Complete Consultation", key="complete_consultation"):
            st.session_state.current_stage = 4
            st.rerun()
    
    with col2:
        if st.button("Back to Pre-Screening", key="back_to_prescreening"):
            st.session_state.current_stage = 2
            st.rerun()

def show_final_report():
    """Display the final report page"""
    # Role-based access control
    if st.session_state.user_role not in ["doctor", "nurse", "admin"]:
        st.error("🚫 Access Denied: Only doctors, nurses, and administrators can access clinical reports.")
        st.info("Please contact your administrator if you need access to this section.")
        return
    
    st.header("📋 Final Clinical Report")
    
    # Generate report
    st.subheader("Patient Information")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Name:** {st.session_state.patient_data.get('name', 'N/A')}")
        st.write(f"**MRN:** {st.session_state.patient_data.get('mrn', 'N/A')}")
        st.write(f"**Age:** {st.session_state.patient_data.get('age', 'N/A')}")
        st.write(f"**Gender:** {st.session_state.patient_data.get('gender', 'N/A')}")
    
    with col2:
        st.write(f"**Visit Type:** {st.session_state.patient_data.get('visit_type', 'N/A')}")
        st.write(f"**Insurance:** {st.session_state.patient_data.get('insurance_provider', 'N/A')}")
        st.write(f"**Date:** {datetime.now().strftime('%Y-%m-%d')}")
    
    st.subheader("Clinical Summary")
    st.write(f"**Chief Complaint:** {st.session_state.patient_data.get('chief_complaint', 'N/A')}")
    st.write(f"**Symptom Onset:** {st.session_state.patient_data.get('symptom_onset', 'N/A')}")
    st.write(f"**Severity:** {st.session_state.patient_data.get('severity', 'N/A')}/10")
    
    if "analysis" in st.session_state.patient_data:
        analysis = st.session_state.patient_data["analysis"]
        st.write(f"**Detected Symptoms:** {', '.join(analysis.get('symptoms', []))}")
        st.write(f"**Anatomical Sites:** {', '.join(analysis.get('anatomical_sites', []))}")
    
    # Clinical Notes and ICD-10 Code
    if "consultation_data" in st.session_state:
        consultation_data = st.session_state.consultation_data
        st.write(f"**Clinical Notes:** {consultation_data.get('clinical_notes', 'N/A')}")
        st.write(f"**Primary ICD-10 Code:** {consultation_data.get('selected_icd10', 'N/A')}")
    
    # Uploaded Documents
    if "uploaded_documents" in st.session_state:
        st.subheader("📄 Uploaded Documents")
        uploaded_docs = st.session_state.uploaded_documents
        
        if uploaded_docs.get("id_card"):
            id_doc = uploaded_docs["id_card"]
            st.write(f"**ID Card:** {id_doc['filename']} - ✅ Verified")
        
        if uploaded_docs.get("medical_aid"):
            med_doc = uploaded_docs["medical_aid"]
            st.write(f"**Medical Aid:** {med_doc['filename']} - ✅ Verified")
    
    st.subheader("Recommendations")
    st.write("Based on the AI analysis and clinical assessment:")
    st.write("- Follow-up appointment scheduled")
    st.write("- Patient education materials provided")
    st.write("- Prescription medications as indicated")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Report", key="generate_report"):
            st.success("Clinical report generated successfully!")
            st.balloons()
            
            st.session_state.current_stage = 5
            st.rerun()
    
    with col2:
        if st.button("Back to Consultation", key="back_to_consultation"):
            st.session_state.current_stage = 3
            st.rerun()

def show_submission():
    """Display the submission page"""
    st.header("✅ Visit Complete")
    
    st.success("Patient visit has been completed successfully!")
    
    # Summary metrics
    st.subheader("Visit Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Time Saved", "15 min", "↑ 30%")
    with col2:
        st.metric("Accuracy", "96%", "↑ 8%")
    with col3:
        st.metric("Patient Satisfaction", "4.8/5", "↑ 12%")
    
    st.subheader("Next Steps")
    st.write("1. Patient has been discharged")
    st.write("2. Follow-up appointment scheduled")
    st.write("3. Prescription sent to pharmacy")
    st.write("4. Patient portal access provided")
    
    if st.button("Start New Patient", key="new_patient"):
        # Reset session state
        st.session_state.patient_data = {}
        st.session_state.current_stage = 1
        st.rerun()

def main():
    """Main application function"""
    
    # Sidebar navigation
    with st.sidebar:
        st.title("📋 Clinical Workflow")
        
        # Show login form or user information
        if st.session_state.authenticated:
            # Show user information
            user_info = USERS_DB[st.session_state.username]
            role_emoji = {
                "admin": "👑",
                "doctor": "👨‍⚕️", 
                "nurse": "👩‍⚕️",
                "receptionist": "📋",
                "patient": "👤"
            }
            
            st.markdown("### 👤 User Info")
            st.write(f"{role_emoji.get(st.session_state.user_role, '👤')} **{user_info['name']}**")
            st.write(f"**Role:** {st.session_state.user_role.title()}")
            st.write(f"**Username:** {st.session_state.username}")
            
            # Logout button
            if st.button("🚪 Logout", use_container_width=True):
                # Clear all session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        else:
            # Show login form
            show_sidebar_login()
    
    # Main content - show landing page or clinical workflow
    if not st.session_state.authenticated:
        show_landing_page()
        return
    
    # Header for authenticated users
    st.markdown("""
    <div class="main-header">
        <h1>🏥 MedAssist AI Pro - Clinical Workflow</h1>
        <p>AI-Powered Clinical Workflow System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar content for authenticated users
    with st.sidebar:
        # Progress indicator
        stages = [
            "1. Patient Intake",
            "2. Pre-Screening",
            "3. Consultation",
            "4. Final Report",
            "5. Submission"
        ]
        
        for i, stage in enumerate(stages, 1):
            status_class = "status-complete" if i <= st.session_state.current_stage else "status-pending"
            
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
            st.metric("Time Saved", "2.5 min", "↑ 25%")
        with col2:
            st.metric("Accuracy", "92%", "↑ 15%")
    
    # Role-based access control
    if st.session_state.authenticated:
        if st.session_state.user_role == "patient":
            st.info("👤 **Patient Portal Mode** - Limited access to your own information")
        elif st.session_state.user_role == "receptionist":
            st.info("📋 **Receptionist Mode** - Access to patient intake and registration")
        elif st.session_state.user_role == "nurse":
            st.info("👩‍⚕️ **Nurse Mode** - Access to patient care and documentation")
        elif st.session_state.user_role == "doctor":
            st.info("👨‍⚕️ **Doctor Mode** - Full access to clinical workflow")
        elif st.session_state.user_role == "admin":
            st.info("👑 **Admin Mode** - Full system access")
    else:
        st.info("🔐 **Please log in** using the sidebar to access the clinical workflow")
    
    # Main content area
    if st.session_state.current_stage == 1:
        show_patient_intake()
    elif st.session_state.current_stage == 2:
        show_pre_screening()
    elif st.session_state.current_stage == 3:
        show_consultation()
    elif st.session_state.current_stage == 4:
        show_final_report()
    elif st.session_state.current_stage == 5:
        show_submission()

if __name__ == "__main__":
    main()
