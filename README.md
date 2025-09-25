# MedAssist AI Pro - Simple Demo

A simplified version of the MedAssist AI Pro clinical workflow demonstration app built with Streamlit.

## Demo Video

Watch our demonstration video to see Medical AI Idea in action (this is generated with Veo and Google Video 😉 ):

https://github.com/user-attachments/assets/South_African_EHR Idea_ A Unified_Healthcare_Platform.mp4

*Note: This video showcases the unified healthcare platform concept and MedAssist AI Pro's clinical workflow capabilities.*

## Quick Start

### Using uv (if you have uv installed)
```bash
uv sync 

# Run the app after installing
uv run streamlit run simple_app.py
```

## What's Included

This simple version includes:

1. **Patient Intake Portal** - Basic patient registration and symptom collection
2. **AI Pre-Screening** - Simple symptom analysis and risk assessment
3. **Consultation Interface** - Mock clinical consultation with AI suggestions
4. **Final Report** - Clinical report generation
5. **Visit Completion** - Summary and next steps

## Features

- ✅ Patient registration
- ✅ Symptom collection with basic AI analysis
- ✅ Review of systems checklist
- ✅ Risk assessment and recommendations
- ✅ Clinical workflow progression
- ✅ Responsive medical-themed UI

## Key Differences from Full Version

The simple version removes complex dependencies like:
- Google Generative AI
- Advanced NLP models
- Audio recording capabilities
- Image processing
- Document parsing
- FHIR integration

Instead, it uses basic pattern matching for symptom detection and provides a working demonstration of the clinical workflow.

## Usage

1. Start the app with `streamlit run simple_app.py`
2. Navigate through the 5-stage clinical workflow:
   - Patient Intake
   - Pre-Screening
   - Consultation
   - Final Report
   - Submission
3. Fill in patient information and symptoms
4. See AI analysis and recommendations
5. Complete the clinical workflow

## Technical Details

- **Framework**: Streamlit
- **Dependencies**: streamlit, pandas
- **AI Analysis**: Basic pattern matching for symptom detection
- **Data Storage**: Session state (in-memory)
- **UI**: Medical-themed responsive design
