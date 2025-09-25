"""
Comprehensive Synthetic Data Generator for South African Hospital ERP System
=========================================================================

This script generates realistic synthetic data for a South African hospital ERP system,
combining the best features from both existing scripts and adding BigQuery integration.

Features:
- Comprehensive healthcare data warehouse structure
- South African context (provinces, districts, healthcare system)
- ERP-specific tables (financial, suppliers, procurement)
- BigQuery integration for direct data upload
- Configurable data volumes and date ranges
- Realistic business logic and relationships

Usage:
    python generate_data.py --help
    python generate_data.py --facilities 50 --patients 10000 --output bigquery
"""

import argparse
import datetime
import hashlib
import os
import random
import string
from typing import Tuple, Optional

import numpy as np
import pandas as pd
from faker import Faker

# BigQuery imports (will be added to dependencies)
try:
    from google.cloud import bigquery
    from google.oauth2 import service_account
    BIGQUERY_AVAILABLE = True
except ImportError:
    BIGQUERY_AVAILABLE = False
    print("Warning: BigQuery dependencies not available. Install with: pip install google-cloud-bigquery")

# PostgreSQL imports
try:
    import psycopg2
    from sqlalchemy import create_engine
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    print("Warning: PostgreSQL dependencies not available. Install with: pip install psycopg2-binary sqlalchemy")

# Initialize Faker
fake = Faker('en_US')  # Using US locale as SA locale not available
np.random.seed(42)
random.seed(42)

# Configuration constants
PROVINCES = [
    'Western Cape', 'Eastern Cape', 'KwaZulu-Natal', 'Gauteng', 'Limpopo',
    'Mpumalanga', 'Free State', 'Northern Cape', 'North West'
]

FACILITY_LEVELS = ['clinic', 'CHC', 'district_hospital', 'regional_hospital', 'tertiary_hospital']

# South African provinces with realistic geographic bounds
PROVINCES_BOUNDS = {
    "Western Cape": (-34.83, -30.67, 18.0, 26.0),
    "Eastern Cape": (-34.1, -29.0, 22.6, 30.0),
    "Northern Cape": (-32.0, -20.0, 16.0, 24.0),
    "KwaZulu-Natal": (-29.5, -27.0, 29.0, 32.8),
    "Gauteng": (-26.7, -25.3, 27.0, 29.4),
    "Mpumalanga": (-26.5, -23.5, 28.0, 31.7),
    "Limpopo": (-25.5, -22.1, 24.7, 31.5),
    "Free State": (-30.7, -26.0, 24.7, 29.3),
    "North West": (-27.5, -24.6, 24.5, 28.0),
}

# Comprehensive drug list for South African healthcare
DRUG_DATABASE = [
    ("Paracetamol", "N02BE01", "500 mg", "tablet", 20, False, True, 15.50),
    ("Amoxicillin", "J01CA04", "250 mg", "capsule", 20, False, True, 45.20),
    ("Ibuprofen", "M01AE01", "400 mg", "tablet", 20, False, True, 25.80),
    ("Insulin Glargine", "A10AB01", "100 IU/mL", "vial", 1, True, True, 285.90),
    ("Metformin", "A10BA02", "500 mg", "tablet", 30, False, True, 18.75),
    ("Atenolol", "C07AB03", "50 mg", "tablet", 30, False, True, 22.40),
    ("Salbutamol", "R03AC02", "100 mcg", "inhaler", 1, False, True, 89.50),
    ("Fluconazole", "J02AC01", "150 mg", "tablet", 1, False, True, 35.60),
    ("Simvastatin", "C10AA01", "20 mg", "tablet", 30, False, True, 28.90),
    ("Furosemide", "C03CA01", "40 mg", "tablet", 28, False, True, 12.30),
    ("Prednisone", "H02AB07", "10 mg", "tablet", 30, False, True, 19.80),
    ("Omeprazole", "A02BC01", "20 mg", "capsule", 28, False, True, 32.40),
    ("Rifampicin", "J04AB02", "300 mg", "capsule", 30, False, True, 45.70),
    ("Ethambutol", "J04AK02", "400 mg", "tablet", 28, False, True, 38.20),
    ("Pyrazinamide", "J04AK01", "500 mg", "tablet", 28, False, True, 42.10),
    ("Isoniazid", "J04AC01", "300 mg", "tablet", 28, False, True, 15.90),
    ("Ceftriaxone", "J01DD04", "1 g", "vial", 1, False, True, 125.80),
    ("Azithromycin", "J01FA10", "500 mg", "tablet", 3, False, True, 55.40),
    ("Aspirin", "B01AC06", "81 mg", "tablet", 30, False, True, 8.90),
    ("Enalapril", "C09AA02", "10 mg", "tablet", 28, False, True, 24.60),
    ("Losartan", "C09CA01", "50 mg", "tablet", 30, False, True, 35.20),
    ("Diclofenac", "M01AB05", "50 mg", "tablet", 30, False, True, 18.40),
    ("Ciprofloxacin", "J01MA02", "500 mg", "tablet", 10, False, True, 42.80),
    ("Doxycycline", "J01AA02", "100 mg", "capsule", 14, False, True, 28.50),
    ("Levothyroxine", "H03AA01", "100 mcg", "tablet", 30, False, True, 22.70),
    ("Haloperidol", "N05AD01", "5 mg", "tablet", 30, False, True, 38.90),
    ("Fluoxetine", "N06AB03", "20 mg", "capsule", 30, False, True, 45.60),
    ("Carbamazepine", "N03AF01", "200 mg", "tablet", 30, False, True, 52.30),
    ("Valproate", "N03AG01", "500 mg", "tablet", 30, False, True, 48.70),
    ("ARV Combination", "J05AR06", "Various", "tablet", 30, False, True, 0.00),  # Free in SA
    ("TB Treatment Pack", "J04AK99", "Various", "pack", 30, False, True, 0.00),  # Free in SA
]

# ICD-10 codes common in South African healthcare with GEMA classifications
ICD10_DATABASE = [
    ("J06.9", "Acute upper respiratory infection", "RESP", "Respiratory", "Acute"),
    ("I10", "Essential hypertension", "CARD", "Cardiovascular", "Chronic"),
    ("E11.9", "Type 2 diabetes mellitus", "ENDO", "Endocrine", "Chronic"),
    ("J45.9", "Asthma", "RESP", "Respiratory", "Chronic"),
    ("K21.0", "Gastroesophageal reflux disease", "GAST", "Gastrointestinal", "Chronic"),
    ("M79.3", "Panniculitis", "MUSC", "Musculoskeletal", "Acute"),
    ("R50.9", "Fever, unspecified", "SYMP", "Symptom", "Acute"),
    ("A09", "Diarrhea and gastroenteritis", "GAST", "Gastrointestinal", "Acute"),
    ("L02.9", "Cutaneous abscess", "DERM", "Dermatology", "Acute"),
    ("N39.0", "Urinary tract infection", "UROL", "Urology", "Acute"),
    ("B20", "HIV disease", "INFEC", "Infectious Disease", "Chronic"),
    ("A15.0", "Pulmonary tuberculosis", "INFEC", "Infectious Disease", "Chronic"),
    ("O80", "Normal delivery", "OBGY", "Obstetrics/Gynecology", "Acute"),
    ("Z23", "Encounter for immunization", "PREV", "Preventive", "Acute"),
    ("T78.4", "Allergy, unspecified", "IMMUN", "Immunology", "Acute"),
    ("F32.9", "Depressive episode", "PSYCH", "Psychiatry", "Chronic"),
    ("G43.9", "Migraine", "NEURO", "Neurology", "Chronic"),
    ("M54.5", "Low back pain", "MUSC", "Musculoskeletal", "Chronic"),
    ("E78.5", "Hyperlipidemia", "ENDO", "Endocrine", "Chronic"),
    ("R05", "Cough", "RESP", "Respiratory", "Acute"),
    ("J20.9", "Acute bronchitis", "RESP", "Respiratory", "Acute"),
    ("K21.9", "Gastroesophageal reflux disease", "GAST", "Gastrointestinal", "Chronic"),
    ("B34.9", "Viral infection", "INFEC", "Infectious Disease", "Acute"),
    ("M54.5", "Low back pain", "MUSC", "Musculoskeletal", "Chronic"),
]

# GEMA classification categories
GEMA_CATEGORIES = {
    "RESP": "Respiratory",
    "CARD": "Cardiovascular", 
    "ENDO": "Endocrine",
    "GAST": "Gastrointestinal",
    "MUSC": "Musculoskeletal",
    "SYMP": "Symptom",
    "DERM": "Dermatology",
    "UROL": "Urology",
    "INFEC": "Infectious Disease",
    "OBGY": "Obstetrics/Gynecology",
    "PREV": "Preventive",
    "IMMUN": "Immunology",
    "PSYCH": "Psychiatry",
    "NEURO": "Neurology"
}

# Supplier information for South African pharmaceutical companies
SUPPLIERS = [
    ("Aspen Pharmacare", "South Africa", "Private", "Large"),
    ("Adcock Ingram", "South Africa", "Private", "Large"),
    ("Sandoz", "International", "Private", "Large"),
    ("Pfizer", "International", "Private", "Large"),
    ("Novartis", "International", "Private", "Large"),
    ("GSK", "International", "Private", "Large"),
    ("Sanofi", "International", "Private", "Large"),
    ("Roche", "International", "Private", "Large"),
    ("Merck", "International", "Private", "Large"),
    ("Johnson & Johnson", "International", "Private", "Large"),
    ("Government Medical Supply", "South Africa", "Public", "Large"),
    ("Medicines Control Council", "South Africa", "Public", "Medium"),
    ("Local Distributor A", "South Africa", "Private", "Small"),
    ("Local Distributor B", "South Africa", "Private", "Small"),
    ("Regional Supplier", "South Africa", "Private", "Medium"),
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive synthetic healthcare ERP data for South Africa",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--facilities", type=int, default=25, help="Number of facilities to generate")
    parser.add_argument("--patients", type=int, default=5000, help="Number of unique patients")
    parser.add_argument("--drugs", type=int, default=30, help="Number of drugs in formulary")
    parser.add_argument("--start_date", type=str, default=None, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end_date", type=str, default=None, help="End date (YYYY-MM-DD)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", choices=["csv", "bigquery", "postgres"], default="csv", help="Output format")
    parser.add_argument("--output_dir", type=str, default="./data", help="Output directory for CSV")
    parser.add_argument("--project_id", type=str, default=None, help="BigQuery project ID")
    parser.add_argument("--dataset_id", type=str, default="healthcare_erp", help="BigQuery dataset ID")
    parser.add_argument("--credentials", type=str, default=None, help="Path to BigQuery credentials JSON")
    parser.add_argument("--postgres_url", type=str, default=None, help="PostgreSQL connection URL")
    return parser.parse_args()


def set_seed(seed: int) -> None:
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)


def random_coord(bbox: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Generate random coordinates within a bounding box."""
    lat = random.uniform(bbox[0], bbox[1])
    lon = random.uniform(bbox[2], bbox[3])
    return round(lat, 6), round(lon, 6)


def generate_facilities(n: int) -> pd.DataFrame:
    """Generate healthcare facilities across South Africa with realistic distribution."""
    facilities = []
    
    # Realistic facility distribution by province (based on population and healthcare needs)
    province_facility_counts = {
        'Gauteng': int(n * 0.35),      # Most populous - most facilities
        'Western Cape': int(n * 0.25),  # Second most populous
        'KwaZulu-Natal': int(n * 0.15), # Third most populous
        'Eastern Cape': int(n * 0.08),
        'Limpopo': int(n * 0.06),
        'Mpumalanga': int(n * 0.05),
        'Free State': int(n * 0.03),
        'North West': int(n * 0.02),
        'Northern Cape': int(n * 0.01)  # Least populous - fewest facilities
    }
    
    # Ensure we have at least 1 facility per province
    for province in province_facility_counts:
        if province_facility_counts[province] == 0:
            province_facility_counts[province] = 1
    
    # Adjust total to match n
    total_allocated = sum(province_facility_counts.values())
    if total_allocated != n:
        # Adjust Gauteng and Western Cape to make up the difference
        diff = n - total_allocated
        province_facility_counts['Gauteng'] += diff // 2
        province_facility_counts['Western Cape'] += diff - (diff // 2)
    
    facility_id_counter = 1
    
    for province, count in province_facility_counts.items():
        for _ in range(count):
            lat, lon = random_coord(PROVINCES_BOUNDS[province])
            level = random.choice(FACILITY_LEVELS)
            
            # Generate realistic facility names
            if level == 'clinic':
                name = f"{fake.city()} Community Clinic"
            elif level == 'CHC':
                name = f"{fake.city()} Community Health Centre"
            elif level == 'district_hospital':
                name = f"{fake.city()} District Hospital"
            elif level == 'regional_hospital':
                name = f"{fake.city()} Regional Hospital"
            else:
                name = f"{fake.city()} Tertiary Hospital"
            
            # Generate opening date (most facilities opened in last 30 years)
            opened_date = fake.date_between(start_date='-30y', end_date='-1y')
            
            facility = {
                'facility_id': f'FAC{facility_id_counter:04d}',
                'facility_name': name,
                'province': province,
                'district': f'{fake.city()} District',
                'latitude': lat,
                'longitude': lon,
                'level': level,
                'is_active': True,
                'opened_date': opened_date,
                'closed_date': None,
                'bed_capacity': random.randint(10, 500) if level in ['district_hospital', 'regional_hospital', 'tertiary_hospital'] else None,
                'staff_count': random.randint(5, 200),
                'load_ts': pd.Timestamp.utcnow()
            }
            facilities.append(facility)
            facility_id_counter += 1
    
    return pd.DataFrame(facilities)


def generate_patients(n: int) -> pd.DataFrame:
    """Generate pseudonymized patient records with realistic SA province distribution."""
    patients = []
    
    # Realistic South African province population distribution
    province_weights = {
        'Gauteng': 0.35,      # Most populous province
        'Western Cape': 0.25,  # Second most populous
        'KwaZulu-Natal': 0.15, # Third most populous
        'Eastern Cape': 0.08,
        'Limpopo': 0.06,
        'Mpumalanga': 0.05,
        'Free State': 0.03,
        'North West': 0.02,
        'Northern Cape': 0.01  # Least populous
    }
    
    # Create weighted province list
    weighted_provinces = []
    for province, weight in province_weights.items():
        weighted_provinces.extend([province] * int(weight * 100))
    
    for i in range(1, n + 1):
        # Create pseudonymized patient ID
        patient_id = hashlib.md5(f'patient_{i}'.encode()).hexdigest()[:12].upper()
        
        birth_year = random.randint(1940, 2010)
        sex = random.choice(['M', 'F', 'Other', 'Unknown'])
        home_province = random.choice(weighted_provinces)
        
        # 30% enrolled in chronic disease management
        chronic_enrolled = random.random() < 0.3
        enrollment_date = None
        if chronic_enrolled:
            enrollment_date = fake.date_between(start_date='-5y', end_date='today')
        
        patient = {
            'patient_id': patient_id,
            'birth_year': birth_year,
            'sex': sex,
            'home_province': home_province,
            'chronic_program_enrolled': chronic_enrolled,
            'enrollment_date': enrollment_date,
            'medical_aid': random.choice(['None', 'Discovery', 'Bonitas', 'Medihelp', 'Momentum', 'Other']),
            'load_ts': pd.Timestamp.utcnow()
        }
        patients.append(patient)
    
    return pd.DataFrame(patients)


def generate_drugs(n: int) -> pd.DataFrame:
    """Generate drug formulary."""
    drugs = []
    
    for i in range(min(n, len(DRUG_DATABASE))):
        if i < len(DRUG_DATABASE):
            name, atc, strength, form, pack_size, cold_chain, essential, unit_cost = DRUG_DATABASE[i]
        else:
            # Generate additional synthetic drugs
            name = f"Generic Drug {i}"
            atc = "Z99" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=3))
            strength = f"{random.choice([50, 100, 200, 500])} mg"
            form = random.choice(["tablet", "capsule", "syrup", "vial"])
            pack_size = random.choice([10, 14, 20, 28, 30, 100])
            cold_chain = False
            essential = random.random() < 0.7
            unit_cost = round(random.uniform(10.0, 200.0), 2)
        
        drug = {
            'drug_id': f'DRUG{i+1:04d}',
            'atc_code': atc,
            'generic_name': name,
            'strength': strength,
            'form': form,
            'pack_size': pack_size,
            'cold_chain_required': cold_chain,
            'is_essential_list': essential,
            'unit_cost_zar': unit_cost,
            'supplier_id': f'SUP{random.randint(1, len(SUPPLIERS)):03d}',
            'load_ts': pd.Timestamp.utcnow()
        }
        drugs.append(drug)
    
    return pd.DataFrame(drugs)


def generate_suppliers() -> pd.DataFrame:
    """Generate supplier information."""
    suppliers = []
    
    for i, (name, country, type_, size) in enumerate(SUPPLIERS, 1):
        supplier = {
            'supplier_id': f'SUP{i:03d}',
            'supplier_name': name,
            'country': country,
            'supplier_type': type_,
            'size_category': size,
            'contact_email': f'contact@{name.lower().replace(" ", "")}.com',
            'contact_phone': fake.phone_number(),
            'is_active': True,
            'load_ts': pd.Timestamp.utcnow()
        }
        suppliers.append(supplier)
    
    return pd.DataFrame(suppliers)


def generate_calendar(start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Generate calendar dimension with South African context."""
    dates = pd.date_range(start_date, end_date, freq="D")
    records = []
    
    # South African public holidays
    public_holidays = {
        (1, 1),    # New Year's Day
        (3, 21),   # Human Rights Day
        (4, 27),   # Freedom Day
        (5, 1),    # Workers' Day
        (6, 16),   # Youth Day
        (8, 9),    # National Women's Day
        (9, 24),   # Heritage Day
        (12, 16),  # Day of Reconciliation
        (12, 25),  # Christmas
        (12, 26),  # Day of Goodwill
    }
    
    for dt in dates:
        dow = dt.isoweekday()  # Monday=1
        week = dt.isocalendar().week
        month = dt.month
        quarter = (month - 1) // 3 + 1
        year = dt.year
        is_weekend = dow >= 6
        is_public_holiday = (dt.month, dt.day) in public_holidays
        
        # Payday logic (15th and month-end)
        is_payday = dt.day == 15 or dt == dt + pd.offsets.MonthEnd(0)
        
        # School terms (4 terms per year)
        school_term = (month - 1) // 3 + 1
        
        # South African seasons
        if month in [12, 1, 2]:
            season = "Summer"
        elif month in [3, 4, 5]:
            season = "Autumn"
        elif month in [6, 7, 8]:
            season = "Winter"
        else:
            season = "Spring"
        
        record = {
            'dt': dt.date(),
            'dow': dow,
            'week': week,
            'month': month,
            'quarter': quarter,
            'year': year,
            'is_weekend': is_weekend,
            'is_public_holiday': is_public_holiday,
            'is_payday': is_payday,
            'school_term': school_term,
            'season': season,
        }
        records.append(record)
    
    return pd.DataFrame(records)


def random_time_on_day(date: datetime.date, start_hour: int = 7, end_hour: int = 17) -> datetime.datetime:
    """Generate random time within business hours."""
    hour = random.randint(start_hour, end_hour - 1)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime.datetime.combine(date, datetime.time(hour, minute, second))


def generate_visits(facilities_df: pd.DataFrame, patients_df: pd.DataFrame, 
                   calendar_df: pd.DataFrame, visits_per_facility_range: Tuple[int, int] = (200, 600)) -> pd.DataFrame:
    """Generate patient visits with diagnosis information."""
    visit_records = []
    patient_ids = patients_df["patient_id"].tolist()
    facility_ids = facilities_df["facility_id"].tolist()
    visit_id_counter = 1
    
    # Create province-based visit distribution (more realistic for SA)
    province_weights = {
        'Gauteng': 0.35,      # Most populous province
        'Western Cape': 0.25,  # Second most populous
        'KwaZulu-Natal': 0.15, # Third most populous
        'Eastern Cape': 0.08,
        'Limpopo': 0.06,
        'Mpumalanga': 0.05,
        'Free State': 0.03,
        'North West': 0.02,
        'Northern Cape': 0.01  # Least populous
    }
    
    for fac_id in facility_ids:
        # Get facility province
        facility_province = facilities_df[facilities_df['facility_id'] == fac_id]['province'].iloc[0]
        
        # Adjust visit count based on province population
        base_visits = random.randint(*visits_per_facility_range)
        province_multiplier = province_weights.get(facility_province, 0.05)
        
        # Scale visits based on province weight
        num_visits = int(base_visits * (1 + province_multiplier * 2))
        
        for _ in range(num_visits):
            visit_id = f'VISIT{visit_id_counter:07d}'
            visit_id_counter += 1
            patient_id = random.choice(patient_ids)
            
            # Random date from calendar
            date_row = calendar_df.sample(1).iloc[0]
            date = date_row["dt"]
            
            # 20% walk-ins, 80% scheduled
            if random.random() < 0.2:
                scheduled_time = None
                arrival_time = random_time_on_day(date)
                arrival_delay = None
            else:
                scheduled_time = random_time_on_day(date)
                delay_minutes = int(np.clip(np.random.normal(loc=5, scale=15), -30, 120))
                arrival_time = scheduled_time + datetime.timedelta(minutes=delay_minutes)
                arrival_delay = delay_minutes
            
            # Ensure arrival stays on same day
            if arrival_time.date() != date:
                arrival_time = datetime.datetime.combine(date, datetime.time(23, 50, 0))
                if scheduled_time:
                    arrival_delay = int((arrival_time - scheduled_time).total_seconds() / 60)
            
            # Triage level (skewed towards moderate urgency)
            triage_level = random.choices([1, 2, 3, 4, 5], weights=[5, 10, 40, 30, 15])[0]
            
            # Visit timing
            visit_start = arrival_time + datetime.timedelta(minutes=max(0, int(np.random.normal(15, 10))))
            visit_duration = max(5, int(np.random.exponential(scale=20)))
            visit_end = visit_start + datetime.timedelta(minutes=visit_duration)
            
            visit_type = random.choice(["acute", "chronic", "follow-up", "emergency", "routine"])
            
            # Generate primary diagnosis for this visit
            primary_diagnosis = random.choice(ICD10_DATABASE)
            primary_icd10_code = primary_diagnosis[0]
            primary_icd10_description = primary_diagnosis[1]
            primary_gema_code = primary_diagnosis[2]
            primary_gema_category = primary_diagnosis[3]
            primary_condition_type = primary_diagnosis[4]
            
            # Generate MedGemini AI ICD-10 classification
            # Simulate AI model that might classify ICD-10 codes differently from medical providers
            primary_medgemini_icd10_code = primary_icd10_code
            primary_medgemini_icd10_description = primary_icd10_description
            
            # 20% chance that MedGemini disagrees with medical provider's ICD-10 classification
            if random.random() < 0.20:
                # Generate alternative ICD-10 code from the database
                alternative_diagnoses = [diag for diag in ICD10_DATABASE if diag[0] != primary_icd10_code]
                alternative_diagnosis = random.choice(alternative_diagnoses)
                primary_medgemini_icd10_code = alternative_diagnosis[0]
                primary_medgemini_icd10_description = alternative_diagnosis[1]
            
            # Calculate classification confidence/accuracy percentage
            if primary_medgemini_icd10_code == primary_icd10_code:
                classification_accuracy = random.uniform(88, 100)  # High accuracy when they agree
            else:
                classification_accuracy = random.uniform(65, 88)   # Lower accuracy when they disagree
            
            # Generate secondary diagnosis (optional - 30% chance)
            secondary_icd10_code = None
            secondary_icd10_description = None
            secondary_gema_code = None
            secondary_gema_category = None
            secondary_condition_type = None
            secondary_medgemini_icd10_code = None
            secondary_medgemini_icd10_description = None
            secondary_classification_accuracy = None
            
            if random.random() < 0.3:
                secondary_diagnosis = random.choice(ICD10_DATABASE)
                secondary_icd10_code = secondary_diagnosis[0]
                secondary_icd10_description = secondary_diagnosis[1]
                secondary_gema_code = secondary_diagnosis[2]
                secondary_gema_category = secondary_diagnosis[3]
                secondary_condition_type = secondary_diagnosis[4]
                
                # Generate MedGemini AI ICD-10 classification for secondary diagnosis
                secondary_medgemini_icd10_code = secondary_icd10_code
                secondary_medgemini_icd10_description = secondary_icd10_description
                
                # 20% chance that MedGemini disagrees with medical provider for secondary diagnosis
                if random.random() < 0.20:
                    alternative_diagnoses = [diag for diag in ICD10_DATABASE if diag[0] != secondary_icd10_code]
                    alternative_diagnosis = random.choice(alternative_diagnoses)
                    secondary_medgemini_icd10_code = alternative_diagnosis[0]
                    secondary_medgemini_icd10_description = alternative_diagnosis[1]
                
                # Calculate secondary classification accuracy
                if secondary_medgemini_icd10_code == secondary_icd10_code:
                    secondary_classification_accuracy = random.uniform(88, 100)
                else:
                    secondary_classification_accuracy = random.uniform(65, 88)
            
            record = {
                "visit_id": visit_id,
                "patient_id": patient_id,
                "facility_id": fac_id,
                "scheduled_time": scheduled_time,
                "arrival_time": arrival_time,
                "arrival_delay_minutes": arrival_delay,
                "triage_level": triage_level,
                "visit_start_time": visit_start,
                "visit_end_time": visit_end,
                "visit_duration_minutes": int((visit_end - visit_start).total_seconds() / 60),
                "visit_type": visit_type,
                # Primary diagnosis fields
                "primary_icd10_code": primary_icd10_code,
                "primary_icd10_description": primary_icd10_description,
                "primary_gema_code": primary_gema_code,
                "primary_gema_category": primary_gema_category,
                "primary_condition_type": primary_condition_type,
                "primary_medgemini_icd10_code": primary_medgemini_icd10_code,
                "primary_medgemini_icd10_description": primary_medgemini_icd10_description,
                "primary_classification_accuracy": round(classification_accuracy, 1),
                "primary_provider_medgemini_match": primary_medgemini_icd10_code == primary_icd10_code,
                # Secondary diagnosis fields
                "secondary_icd10_code": secondary_icd10_code,
                "secondary_icd10_description": secondary_icd10_description,
                "secondary_gema_code": secondary_gema_code,
                "secondary_gema_category": secondary_gema_category,
                "secondary_condition_type": secondary_condition_type,
                "secondary_medgemini_icd10_code": secondary_medgemini_icd10_code,
                "secondary_medgemini_icd10_description": secondary_medgemini_icd10_description,
                "secondary_classification_accuracy": round(secondary_classification_accuracy, 1) if secondary_classification_accuracy else None,
                "secondary_provider_medgemini_match": secondary_medgemini_icd10_code == secondary_icd10_code if secondary_medgemini_icd10_code else None,
                "created_at": pd.Timestamp.utcnow(),
                "partition_dt": date,
            }
            visit_records.append(record)
    
    return pd.DataFrame(visit_records)


def generate_diagnoses(visits_df: pd.DataFrame) -> pd.DataFrame:
    """Generate diagnosis records."""
    diag_records = []
    
    for _, row in visits_df.iterrows():
        num_codes = random.randint(1, 3)
        codes = random.sample(ICD10_DATABASE, num_codes)
        
        for idx, (code, description, gema_code, gema_category, condition_type) in enumerate(codes, start=1):
            diag_records.append({
                "visit_id": row["visit_id"],
                "icd10_code": code,
                "icd10_description": description,
                "gema_code": gema_code,
                "gema_category": gema_category,
                "condition_type": condition_type,
                "is_primary": idx == 1,
                "diagnosis_seq": idx,
                "created_at": row["arrival_time"],
            })
    
    return pd.DataFrame(diag_records)


def generate_med_orders(visits_df: pd.DataFrame, drugs_df: pd.DataFrame) -> pd.DataFrame:
    """Generate medication orders based on diagnoses."""
    orders = []
    drug_ids = drugs_df["drug_id"].tolist()
    order_counter = 1
    
    # Create a mapping of common drug-diagnosis relationships
    diagnosis_drug_mapping = {
        'I10': ['DRUG0001', 'DRUG0005', 'DRUG0006'],  # Hypertension -> Enalapril, Atenolol, Losartan
        'E11.9': ['DRUG0004', 'DRUG0005'],  # Diabetes -> Insulin, Metformin
        'J45.9': ['DRUG0007'],  # Asthma -> Salbutamol
        'J06.9': ['DRUG0001', 'DRUG0002'],  # Upper respiratory -> Paracetamol, Amoxicillin
        'A09': ['DRUG0001'],  # Gastroenteritis -> Paracetamol
        'N39.0': ['DRUG0002'],  # UTI -> Amoxicillin
        'B20': ['DRUG0029'],  # HIV -> ARV Combination
        'A15.0': ['DRUG0013', 'DRUG0014', 'DRUG0015', 'DRUG0016'],  # TB -> TB drugs
        'M54.5': ['DRUG0001', 'DRUG0003'],  # Back pain -> Paracetamol, Ibuprofen
        'F32.9': ['DRUG0027'],  # Depression -> Fluoxetine
        'G43.9': ['DRUG0001'],  # Migraine -> Paracetamol
        'K21.0': ['DRUG0012'],  # GERD -> Omeprazole
        'R50.9': ['DRUG0001'],  # Fever -> Paracetamol
        'L02.9': ['DRUG0002'],  # Abscess -> Amoxicillin
        'O80': ['DRUG0001'],  # Normal delivery -> Paracetamol
        'Z23': ['DRUG0001'],  # Immunization -> Paracetamol
        'T78.4': ['DRUG0001'],  # Allergy -> Paracetamol
        'E78.5': ['DRUG0009'],  # Hyperlipidemia -> Simvastatin
        'R05': ['DRUG0001'],  # Cough -> Paracetamol
        'J20.9': ['DRUG0001', 'DRUG0002'],  # Bronchitis -> Paracetamol, Amoxicillin
        'K21.9': ['DRUG0012'],  # GERD -> Omeprazole
        'B34.9': ['DRUG0001'],  # Viral infection -> Paracetamol
    }
    
    for _, row in visits_df.iterrows():
        # Determine medication probability based on diagnosis
        primary_diagnosis = row["primary_icd10_code"]
        
        # Some diagnoses are more likely to require medication
        if primary_diagnosis in ['I10', 'E11.9', 'J45.9', 'B20', 'A15.0', 'F32.9']:
            med_probability = 0.8  # High probability for chronic conditions
        elif primary_diagnosis in ['J06.9', 'A09', 'N39.0', 'J20.9']:
            med_probability = 0.7  # Medium-high for infections
        else:
            med_probability = 0.4  # Lower probability for other conditions
        
        if random.random() < med_probability:
            # Determine number of medications based on diagnosis complexity
            if primary_diagnosis in ['B20', 'A15.0']:  # HIV, TB - multiple drugs
                num_orders = random.randint(2, 4)
            elif primary_diagnosis in ['I10', 'E11.9']:  # Chronic conditions - 1-2 drugs
                num_orders = random.randint(1, 2)
            else:
                num_orders = random.randint(1, 2)
            
            for _ in range(num_orders):
                order_id = f'ORD{order_counter:08d}'
                order_counter += 1
                
                # Choose drug based on diagnosis if mapping exists, otherwise random
                if primary_diagnosis in diagnosis_drug_mapping:
                    drug_id = random.choice(diagnosis_drug_mapping[primary_diagnosis])
                else:
                    drug_id = random.choice(drug_ids)
                
                # Adjust quantities based on diagnosis type
                if primary_diagnosis in ['B20', 'A15.0']:  # Long-term treatments
                    quantity_units = random.choice([30, 60, 90])
                    days_supply = random.choice([28, 30, 60, 90])
                    repeats = random.randint(2, 6)
                elif primary_diagnosis in ['I10', 'E11.9']:  # Chronic conditions
                    quantity_units = random.choice([28, 30, 60])
                    days_supply = random.choice([28, 30, 60])
                    repeats = random.randint(1, 3)
                else:  # Acute conditions
                    quantity_units = random.choice([10, 20, 30])
                    days_supply = random.choice([7, 14, 28])
                    repeats = random.randint(0, 1)
                
                # Order time within visit
                start_time = row["visit_start_time"]
                end_time = row["visit_end_time"]
                if start_time >= end_time:
                    order_time = start_time
                else:
                    delta_seconds = int((end_time - start_time).total_seconds())
                    order_time = start_time + datetime.timedelta(seconds=random.randint(0, delta_seconds))
                
                chronic_flag = row["visit_type"] == "chronic"
                
                orders.append({
                    "order_id": order_id,
                    "visit_id": row["visit_id"],
                    "patient_id": row["patient_id"],
                    "facility_id": row["facility_id"],
                    "drug_id": drug_id,
                    "quantity_units": quantity_units,
                    "days_supply": days_supply,
                    "repeats": repeats,
                    "order_time": order_time,
                    "chronic_refill_flag": chronic_flag,
                    "created_at": pd.Timestamp.utcnow(),
                    "partition_dt": order_time.date(),
                })
    
    return pd.DataFrame(orders)


def generate_dispense(orders_df: pd.DataFrame) -> pd.DataFrame:
    """Generate dispensing records."""
    dispenses = []
    dispense_counter = 1
    stock_sources = ['pharmacy', 'main_store', 'cabinet', 'CCMDD', 'ward_stock']
    
    for _, row in orders_df.iterrows():
        # 85% of orders are dispensed
        if random.random() < 0.85:
            dispense_id = f'DISP{dispense_counter:08d}'
            dispense_counter += 1
            
            # Sometimes partial dispensing
            qty_dispensed = int(row["quantity_units"] * random.uniform(0.8, 1.0))
            
            # Dispense time after order
            order_time = row["order_time"]
            dispense_time = order_time + datetime.timedelta(minutes=int(np.random.exponential(scale=30)))
            
            dispenses.append({
                "dispense_id": dispense_id,
                "order_id": row["order_id"],
                "patient_id": row["patient_id"],
                "facility_id": row["facility_id"],
                "drug_id": row["drug_id"],
                "quantity_units": qty_dispensed,
                "dispense_time": dispense_time,
                "stock_source": random.choice(stock_sources),
                "created_at": pd.Timestamp.utcnow(),
                "partition_dt": dispense_time.date(),
            })
    
    return pd.DataFrame(dispenses)


def generate_inventory_daily(facilities_df: pd.DataFrame, drugs_df: pd.DataFrame, 
                           start_date: datetime.date, end_date: datetime.date, 
                           dispense_df: pd.DataFrame) -> pd.DataFrame:
    """Generate daily inventory snapshots."""
    facility_ids = facilities_df["facility_id"].tolist()
    drug_ids = drugs_df["drug_id"].tolist()
    date_range = pd.date_range(start_date, end_date, freq="D")
    inventory_records = []
    
    # Precompute daily dispensed units
    if dispense_df.empty:
        dispensed_map = {}
    else:
        dispense_df_copy = dispense_df.copy()
        dispense_df_copy["dt"] = dispense_df_copy["dispense_time"].dt.date
        dispensed_map = dispense_df_copy.groupby(["facility_id", "drug_id", "dt"])["quantity_units"].sum().to_dict()
    
    # Initial opening stocks
    opening_stock = {
        (f, d): random.randint(500, 2000) for f in facility_ids for d in drug_ids
    }
    
    for dt in date_range:
        for f in facility_ids:
            for d in drug_ids:
                open_qty = opening_stock[(f, d)]
                
                # Simulate daily movements
                receipts = np.random.poisson(lam=5)
                issues = np.random.poisson(lam=3)
                adjustments = int(np.random.normal(0, 2))
                dispensed = dispensed_map.get((f, d, dt.date()), 0)
                
                closing = open_qty + receipts - issues - dispensed + adjustments
                closing = max(0, closing)
                
                stockout_flag = closing == 0
                avg_daily_use = max(1, dispensed)
                days_of_cover = closing / avg_daily_use
                
                on_order = random.randint(0, 500) if closing < 200 else 0
                backorder = random.randint(0, 200) if stockout_flag else 0
                
                inventory_records.append({
                    "facility_id": f,
                    "drug_id": d,
                    "dt": dt.date(),
                    "opening_stock_units": open_qty,
                    "receipts_units": receipts,
                    "issues_units": issues,
                    "dispensed_units": dispensed,
                    "adjustments_units": adjustments,
                    "closing_stock_units": closing,
                    "stockout_flag": stockout_flag,
                    "days_of_cover": round(days_of_cover, 2),
                    "on_order_units": on_order,
                    "backorder_units": backorder,
                    "created_at": pd.Timestamp.utcnow(),
                })
                
                # Update for next day
                opening_stock[(f, d)] = closing
    
    return pd.DataFrame(inventory_records)


def generate_financial_transactions(facilities_df: pd.DataFrame, drugs_df: pd.DataFrame, 
                                  start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Generate financial transactions for ERP system."""
    transactions = []
    transaction_counter = 1
    
    facility_ids = facilities_df["facility_id"].tolist()
    drug_ids = drugs_df["drug_id"].tolist()
    date_range = pd.date_range(start_date, end_date, freq="D")
    
    transaction_types = ['purchase', 'sale', 'adjustment', 'transfer', 'return']
    
    for dt in date_range:
        # Generate 5-20 transactions per day
        num_transactions = random.randint(5, 20)
        
        for _ in range(num_transactions):
            transaction_id = f'TXN{transaction_counter:08d}'
            transaction_counter += 1
            
            facility_id = random.choice(facility_ids)
            drug_id = random.choice(drug_ids)
            transaction_type = random.choice(transaction_types)
            
            # Get drug cost
            drug_info = drugs_df[drugs_df['drug_id'] == drug_id].iloc[0]
            unit_cost = drug_info['unit_cost_zar']
            
            quantity = random.randint(1, 100)
            total_amount = quantity * unit_cost
            
            # Add some variation for different transaction types
            if transaction_type == 'sale':
                total_amount *= random.uniform(1.1, 1.3)  # Markup
            elif transaction_type == 'return':
                total_amount *= -1  # Negative for returns
            
            transactions.append({
                'transaction_id': transaction_id,
                'facility_id': facility_id,
                'drug_id': drug_id,
                'transaction_type': transaction_type,
                'quantity': quantity,
                'unit_cost_zar': unit_cost,
                'total_amount_zar': round(total_amount, 2),
                'transaction_date': dt.date(),
                'created_at': pd.Timestamp.utcnow(),
                'partition_dt': dt.date(),
            })
    
    return pd.DataFrame(transactions)


def generate_procurement_orders(suppliers_df: pd.DataFrame, drugs_df: pd.DataFrame, 
                               start_date: datetime.date, end_date: datetime.date) -> pd.DataFrame:
    """Generate procurement orders."""
    orders = []
    order_counter = 1
    
    supplier_ids = suppliers_df["supplier_id"].tolist()
    drug_ids = drugs_df["drug_id"].tolist()
    date_range = pd.date_range(start_date, end_date, freq="D")
    
    for dt in date_range:
        # Generate 1-5 procurement orders per day
        num_orders = random.randint(1, 5)
        
        for _ in range(num_orders):
            order_id = f'PROC{order_counter:08d}'
            order_counter += 1
            
            supplier_id = random.choice(supplier_ids)
            drug_id = random.choice(drug_ids)
            
            # Get drug cost
            drug_info = drugs_df[drugs_df['drug_id'] == drug_id].iloc[0]
            unit_cost = drug_info['unit_cost_zar']
            
            quantity = random.randint(100, 1000)
            total_amount = quantity * unit_cost
            
            # Order status progression
            status = random.choice(['pending', 'approved', 'ordered', 'shipped', 'delivered', 'cancelled'])
            
            orders.append({
                'procurement_order_id': order_id,
                'supplier_id': supplier_id,
                'drug_id': drug_id,
                'quantity': quantity,
                'unit_cost_zar': unit_cost,
                'total_amount_zar': round(total_amount, 2),
                'order_date': dt.date(),
                'status': status,
                'created_at': pd.Timestamp.utcnow(),
                'partition_dt': dt.date(),
            })
    
    return pd.DataFrame(orders)


def write_to_csv(df: pd.DataFrame, filename: str, output_dir: str) -> None:
    """Write DataFrame to CSV file."""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    df.to_csv(path, index=False)
    print(f"Wrote {len(df):,} rows to {path}")


def write_to_bigquery(df: pd.DataFrame, table_name: str, project_id: str, 
                     dataset_id: str, credentials_path: Optional[str] = None) -> None:
    """Write DataFrame to BigQuery table."""
    if not BIGQUERY_AVAILABLE:
        raise ImportError("BigQuery dependencies not available. Install with: pip install google-cloud-bigquery")
    
    # Initialize BigQuery client
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(credentials=credentials, project=project_id)
    else:
        client = bigquery.Client(project=project_id)
    
    # Create dataset if it doesn't exist
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"  # You can change this to your preferred location
        client.create_dataset(dataset)
        print(f"Created dataset {dataset_id}")
    
    # Write data to table
    table_id = f"{project_id}.{dataset_id}.{table_name}"
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",  # Overwrite existing data
        create_disposition="CREATE_IF_NEEDED"
    )
    
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Wait for job to complete
    
    print(f"Wrote {len(df):,} rows to BigQuery table {table_id}")


def write_to_postgres(df: pd.DataFrame, table_name: str, postgres_url: str) -> None:
    """Write DataFrame to PostgreSQL table."""
    if not POSTGRES_AVAILABLE:
        raise ImportError("PostgreSQL dependencies not available. Install with: pip install psycopg2-binary sqlalchemy")
    
    try:
        # Create SQLAlchemy engine
        engine = create_engine(postgres_url)
        
        # Write data to PostgreSQL table
        df.to_sql(
            table_name, 
            engine, 
            if_exists='replace',  # Replace existing data
            index=False,
            method='multi',  # Use multi-row insert for better performance
            chunksize=1000  # Process in chunks for large datasets
        )
        
        print(f"Wrote {len(df):,} rows to PostgreSQL table {table_name}")
        
    except Exception as e:
        print(f"Error writing to PostgreSQL: {e}")
        raise


def main() -> None:
    """Main function to generate all data."""
    args = parse_args()
    set_seed(args.seed)
    
    # Determine date range
    today = datetime.date.today()
    if args.end_date:
        end_date = datetime.datetime.strptime(args.end_date, "%Y-%m-%d").date()
    else:
        end_date = today
    
    if args.start_date:
        start_date = datetime.datetime.strptime(args.start_date, "%Y-%m-%d").date()
    else:
        start_date = end_date - datetime.timedelta(days=365)
    
    print(f"Generating data from {start_date} to {end_date}")
    print(f"Facilities: {args.facilities}, Patients: {args.patients}, Drugs: {args.drugs}")
    
    # Generate dimension tables
    print("\nGenerating dimension tables...")
    facilities_df = generate_facilities(args.facilities)
    patients_df = generate_patients(args.patients)
    drugs_df = generate_drugs(args.drugs)
    suppliers_df = generate_suppliers()
    calendar_df = generate_calendar(start_date, end_date)
    
    # Generate fact tables
    print("Generating fact tables...")
    visits_df = generate_visits(facilities_df, patients_df, calendar_df)
    diagnosis_df = generate_diagnoses(visits_df)
    orders_df = generate_med_orders(visits_df, drugs_df)
    dispense_df = generate_dispense(orders_df)
    inventory_df = generate_inventory_daily(facilities_df, drugs_df, start_date, end_date, dispense_df)
    
    # Generate ERP-specific tables
    print("Generating ERP tables...")
    financial_df = generate_financial_transactions(facilities_df, drugs_df, start_date, end_date)
    procurement_df = generate_procurement_orders(suppliers_df, drugs_df, start_date, end_date)
    
    # Output data
    if args.output == "csv":
        print(f"\nWriting data to CSV files in {args.output_dir}...")
        write_to_csv(facilities_df, "dim_facility.csv", args.output_dir)
        write_to_csv(patients_df, "dim_patient_pseudo.csv", args.output_dir)
        write_to_csv(drugs_df, "dim_drug.csv", args.output_dir)
        write_to_csv(suppliers_df, "dim_supplier.csv", args.output_dir)
        write_to_csv(calendar_df, "dim_calendar.csv", args.output_dir)
        write_to_csv(visits_df, "fact_visit.csv", args.output_dir)
        write_to_csv(diagnosis_df, "fact_diagnosis.csv", args.output_dir)
        write_to_csv(orders_df, "fact_med_order.csv", args.output_dir)
        write_to_csv(dispense_df, "fact_dispense.csv", args.output_dir)
        write_to_csv(inventory_df, "fact_inventory_daily.csv", args.output_dir)
        write_to_csv(financial_df, "fact_financial_transaction.csv", args.output_dir)
        write_to_csv(procurement_df, "fact_procurement_order.csv", args.output_dir)
        
    elif args.output == "bigquery":
        if not args.project_id:
            raise ValueError("--project_id is required for BigQuery output")
        
        print(f"\nWriting data to BigQuery project {args.project_id}, dataset {args.dataset_id}...")
        write_to_bigquery(facilities_df, "dim_facility", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(patients_df, "dim_patient_pseudo", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(drugs_df, "dim_drug", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(suppliers_df, "dim_supplier", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(calendar_df, "dim_calendar", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(visits_df, "fact_visit", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(diagnosis_df, "fact_diagnosis", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(orders_df, "fact_med_order", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(dispense_df, "fact_dispense", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(inventory_df, "fact_inventory_daily", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(financial_df, "fact_financial_transaction", args.project_id, args.dataset_id, args.credentials)
        write_to_bigquery(procurement_df, "fact_procurement_order", args.project_id, args.dataset_id, args.credentials)
        
    elif args.output == "postgres":
        if not args.postgres_url:
            raise ValueError("--postgres_url is required for PostgreSQL output")
        
        print(f"\nWriting data to PostgreSQL database...")
        write_to_postgres(facilities_df, "dim_facility", args.postgres_url)
        write_to_postgres(patients_df, "dim_patient_pseudo", args.postgres_url)
        write_to_postgres(drugs_df, "dim_drug", args.postgres_url)
        write_to_postgres(suppliers_df, "dim_supplier", args.postgres_url)
        write_to_postgres(calendar_df, "dim_calendar", args.postgres_url)
        write_to_postgres(visits_df, "fact_visit", args.postgres_url)
        write_to_postgres(diagnosis_df, "fact_diagnosis", args.postgres_url)
        write_to_postgres(orders_df, "fact_med_order", args.postgres_url)
        write_to_postgres(dispense_df, "fact_dispense", args.postgres_url)
        write_to_postgres(inventory_df, "fact_inventory_daily", args.postgres_url)
        write_to_postgres(financial_df, "fact_financial_transaction", args.postgres_url)
        write_to_postgres(procurement_df, "fact_procurement_order", args.postgres_url)
    
    # Print summary
    print("\n=== Data Generation Complete ===")
    print(f"Facilities: {len(facilities_df)}")
    print(f"Patients: {len(patients_df)}")
    print(f"Drugs: {len(drugs_df)}")
    print(f"Suppliers: {len(suppliers_df)}")
    print(f"Calendar days: {len(calendar_df)}")
    print(f"Visits: {len(visits_df)}")
    print(f"Diagnoses: {len(diagnosis_df)}")
    print(f"Medication orders: {len(orders_df)}")
    print(f"Dispenses: {len(dispense_df)}")
    print(f"Inventory records: {len(inventory_df)}")
    print(f"Financial transactions: {len(financial_df)}")
    print(f"Procurement orders: {len(procurement_df)}")
    
    # Create data dictionary
    data_dict = """
    SOUTH AFRICAN HOSPITAL ERP DATA DICTIONARY
    =========================================
    
    Dimension Tables:
    - dim_facility.csv: Healthcare facilities across South African provinces
    - dim_patient_pseudo.csv: Pseudonymized patient records with medical aid info
    - dim_drug.csv: Comprehensive drug formulary with costs and suppliers
    - dim_supplier.csv: Pharmaceutical suppliers (local and international)
    - dim_calendar.csv: Date dimension with SA holidays and seasons
    
    Fact Tables:
    - fact_visit.csv: Patient visits/encounters with timing details
    - fact_diagnosis.csv: ICD-10 diagnoses per visit
    - fact_med_order.csv: Medication prescriptions with quantities
    - fact_dispense.csv: Medication dispensing events
    - fact_inventory_daily.csv: Daily inventory snapshots per facility/drug
    - fact_financial_transaction.csv: Financial transactions for ERP
    - fact_procurement_order.csv: Procurement orders to suppliers
    
    Key Features:
    - South African healthcare context (provinces, districts, public holidays)
    - Realistic drug costs in ZAR
    - Comprehensive ERP functionality
    - Proper data relationships and business logic
    - Support for both CSV and BigQuery output
    """
    
    if args.output == "csv":
        with open(os.path.join(args.output_dir, 'README.md'), 'w') as f:
            f.write(data_dict)
        print(f"\nData dictionary saved to {args.output_dir}/README.md")


if __name__ == "__main__":
    main()
