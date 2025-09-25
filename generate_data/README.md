# South African Hospital ERP Data Generator

A comprehensive synthetic data generator for South African hospital ERP systems, combining healthcare operations with enterprise resource planning functionality.

## Features

### 🏥 Healthcare Data
- **Facilities**: Clinics, CHCs, district hospitals, regional hospitals across all 9 SA provinces
- **Patients**: Pseudonymized patient records with medical aid information
- **Visits**: Realistic patient encounters with timing and triage data
- **Diagnoses**: ICD-10 codes common in South African healthcare
- **Medications**: Comprehensive drug formulary with realistic costs in ZAR
- **Inventory**: Daily stock levels and movements

### 💼 ERP Functionality
- **Suppliers**: Local and international pharmaceutical suppliers
- **Procurement**: Purchase orders and supplier management
- **Financial**: Transaction tracking with proper accounting
- **Inventory Management**: Stock movements, adjustments, and forecasting data

### 🇿🇦 South African Context
- **Geographic**: Realistic coordinates within SA province boundaries
- **Cultural**: SA public holidays, school terms, seasons
- **Economic**: Drug costs in ZAR, local supplier information
- **Healthcare**: Common SA diseases, ARV/TB treatment programs

## Installation

### Prerequisites
- Python 3.11+
- pip or uv package manager

### Install Dependencies
```bash
# Using pip
pip install -r requirements.txt

# Using uv (recommended)
uv sync
```

### Required Packages
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `faker` - Realistic fake data generation
- `google-cloud-bigquery` - BigQuery integration (optional)

## Usage

### Basic CSV Generation
```bash
python generate_data.py --facilities 25 --patients 5000 --drugs 30
```

### Custom Date Range
```bash
python generate_data.py \
    --start_date 2024-01-01 \
    --end_date 2024-12-31 \
    --facilities 50 \
    --patients 10000
```

### BigQuery Integration
```bash
python generate_data.py \
    --output bigquery \
    --project_id your-gcp-project \
    --dataset_id healthcare_erp \
    --credentials path/to/credentials.json
```

### Command Line Options
```
--facilities N        Number of healthcare facilities (default: 25)
--patients N          Number of unique patients (default: 5000)
--drugs N            Number of drugs in formulary (default: 30)
--start_date DATE    Start date YYYY-MM-DD (default: 1 year ago)
--end_date DATE      End date YYYY-MM-DD (default: today)
--seed N             Random seed for reproducibility (default: 42)
--output FORMAT      Output format: csv or bigquery (default: csv)
--output_dir PATH    Output directory for CSV files (default: ./data)
--project_id ID      BigQuery project ID (required for BigQuery output)
--dataset_id ID      BigQuery dataset ID (default: healthcare_erp)
--credentials PATH   Path to BigQuery credentials JSON file
```

## Data Schema

### Dimension Tables
- **dim_facility**: Healthcare facilities with geographic and operational data
- **dim_patient_pseudo**: Pseudonymized patient records
- **dim_drug**: Drug formulary with costs and supplier information
- **dim_supplier**: Pharmaceutical suppliers (local and international)
- **dim_calendar**: Date dimension with SA holidays and seasons

### Fact Tables
- **fact_visit**: Patient visits with timing and triage information
- **fact_diagnosis**: ICD-10 diagnoses linked to visits
- **fact_med_order**: Medication prescriptions with quantities
- **fact_dispense**: Medication dispensing events
- **fact_inventory_daily**: Daily inventory snapshots per facility/drug
- **fact_financial_transaction**: Financial transactions for ERP
- **fact_procurement_order**: Procurement orders to suppliers

## Data Relationships

```
Patients → Visits → Diagnoses
         ↓
    Medication Orders → Dispenses
         ↓
    Inventory Updates

Suppliers → Procurement Orders → Financial Transactions
```

## BigQuery Setup

### 1. Create GCP Project
```bash
gcloud projects create your-project-id
gcloud config set project your-project-id
```

### 2. Enable BigQuery API
```bash
gcloud services enable bigquery.googleapis.com
```

### 3. Create Service Account
```bash
gcloud iam service-accounts create data-generator \
    --display-name="Data Generator Service Account"

gcloud projects add-iam-policy-binding your-project-id \
    --member="serviceAccount:data-generator@your-project-id.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataEditor"
```

### 4. Download Credentials
```bash
gcloud iam service-accounts keys create credentials.json \
    --iam-account=data-generator@your-project-id.iam.gserviceaccount.com
```

### 5. Generate Data to BigQuery
```bash
python generate_data.py \
    --output bigquery \
    --project_id your-project-id \
    --credentials credentials.json
```

## Example Queries

### Patient Demographics
```sql
SELECT 
    home_province,
    COUNT(*) as patient_count,
    AVG(2024 - birth_year) as avg_age
FROM `your-project.healthcare_erp.dim_patient_pseudo`
GROUP BY home_province
ORDER BY patient_count DESC;
```

### Facility Performance
```sql
SELECT 
    f.facility_name,
    f.province,
    COUNT(v.visit_id) as total_visits,
    AVG(v.visit_duration_minutes) as avg_duration
FROM `your-project.healthcare_erp.dim_facility` f
JOIN `your-project.healthcare_erp.fact_visit` v ON f.facility_id = v.facility_id
GROUP BY f.facility_name, f.province
ORDER BY total_visits DESC;
```

### Drug Usage Analysis
```sql
SELECT 
    d.generic_name,
    SUM(disp.quantity_units) as total_dispensed,
    SUM(disp.quantity_units * d.unit_cost_zar) as total_cost_zar
FROM `your-project.healthcare_erp.dim_drug` d
JOIN `your-project.healthcare_erp.fact_dispense` disp ON d.drug_id = disp.drug_id
GROUP BY d.generic_name
ORDER BY total_cost_zar DESC;
```

## Data Quality Features

### Realistic Business Logic
- Visit timing follows realistic patterns
- Medication orders linked to diagnoses
- Inventory movements reflect actual usage
- Financial transactions maintain proper accounting

### Data Consistency
- Foreign key relationships maintained
- Date ranges consistent across tables
- Patient IDs pseudonymized consistently
- Geographic coordinates within SA bounds

### South African Context
- Realistic drug costs in ZAR
- SA public holidays and seasons
- Common SA diseases and treatments
- Local supplier information

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
   ```bash
   pip install pandas numpy faker google-cloud-bigquery
   ```

2. **BigQuery Authentication**: Check credentials file path and permissions
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
   ```

3. **Memory Issues**: Reduce data volume for large datasets
   ```bash
   python generate_data.py --facilities 10 --patients 1000
   ```

4. **Date Format**: Use YYYY-MM-DD format for dates
   ```bash
   python generate_data.py --start_date 2024-01-01 --end_date 2024-12-31
   ```

## Contributing

### Adding New Data Types
1. Create generator function following existing patterns
2. Add to main() function with appropriate output handling
3. Update data dictionary in README
4. Add example queries if applicable

### Extending South African Context
1. Add new provinces/districts to PROVINCES_BOUNDS
2. Include additional SA-specific drugs in DRUG_DATABASE
3. Add more ICD-10 codes common in SA healthcare
4. Include additional suppliers in SUPPLIERS list

## License

This project is intended for educational and development purposes. The generated data is entirely synthetic and does not represent real patients or facilities.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review command-line help: `python generate_data.py --help`
3. Examine example usage: `python example_usage.py`
4. Check data quality in generated files
