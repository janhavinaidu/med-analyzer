# utils/icd_extractor.py
import json
import re
from typing import List, Dict, Set, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ICDExtractor:
    def __init__(self, icd_codes_path: str = "data/icd10_codes.json"):
        """Initialize the ICD extractor with the codes database"""
        self.icd_codes_path = icd_codes_path
        self.icd_codes = self._load_icd_codes()
        self.condition_mappings = self._get_enhanced_condition_mappings()
        
    def _load_icd_codes(self) -> List[Dict]:
        """Load ICD-10 codes from JSON file"""
        try:
            # Try multiple possible paths
            possible_paths = [
                Path(self.icd_codes_path),
                Path(__file__).parent.parent / "data" / "icd10_codes.json",
                Path("data/icd10_codes.json"),
                Path("./data/icd10_codes.json")
            ]
            
            for path in possible_paths:
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        codes = json.load(f)
                        logger.info(f"Loaded {len(codes)} ICD codes from {path}")
                        return codes
            
            logger.error(f"Could not find ICD codes file at any of these paths: {possible_paths}")
            return []
            
        except Exception as e:
            logger.error(f"Error loading ICD codes: {str(e)}")
            return []

    def _get_enhanced_condition_mappings(self) -> Dict[str, str]:
        """Enhanced condition mappings with medical variations"""
        return {
            # Diabetes related
            "type 2 diabetes": "E11.9",
            "diabetes type 2": "E11.9",
            "type 2 diabetes mellitus": "E11.9",
            "t2dm": "E11.9",
            "adult onset diabetes": "E11.9",
            "type ii diabetes": "E11.9",
            "diabetes mellitus type 2": "E11.9",
            "non-insulin dependent diabetes": "E11.9",
            "niddm": "E11.9",
            
            # Type 1 Diabetes
            "type 1 diabetes": "E10.9",
            "diabetes type 1": "E10.9",
            "t1dm": "E10.9",
            "juvenile diabetes": "E10.9",
            "insulin dependent diabetes": "E10.9",
            "iddm": "E10.9",
            
            # Hypertension related
            "hypertension": "I10",
            "high blood pressure": "I10",
            "elevated blood pressure": "I10",
            "htn": "I10",
            "essential hypertension": "I10",
            "primary hypertension": "I10",
            "systolic hypertension": "I10",
            "diastolic hypertension": "I10",
            
            # Heart conditions
            "heart failure": "I50.9",
            "chf": "I50.9",
            "congestive heart failure": "I50.9",
            "cardiac failure": "I50.9",
            "left heart failure": "I50.1",
            "right heart failure": "I50.9",
            "coronary artery disease": "I25.9",
            "cad": "I25.9",
            "myocardial infarction": "I21.9",
            "heart attack": "I21.9",
            "mi": "I21.9",
            "angina": "I20.9",
            "chest pain": "R06.00",
            
            # Respiratory conditions
            "asthma": "J45.909",
            "chronic asthma": "J45.909",
            "bronchial asthma": "J45.909",
            "allergic asthma": "J45.909",
            "copd": "J44.9",
            "chronic obstructive pulmonary disease": "J44.9",
            "emphysema": "J43.9",
            "chronic bronchitis": "J42",
            "pneumonia": "J18.9",
            "bronchitis": "J40",
            "shortness of breath": "R06.00",
            "dyspnea": "R06.00",
            
            # Mental health
            "depression": "F32.9",
            "major depression": "F32.9",
            "depressive disorder": "F32.9",
            "mdd": "F32.9",
            "clinical depression": "F32.9",
            "anxiety": "F41.9",
            "anxiety disorder": "F41.9",
            "gad": "F41.1",
            "generalized anxiety disorder": "F41.1",
            "panic disorder": "F41.0",
            "panic attacks": "F41.0",
            "bipolar disorder": "F31.9",
            "bipolar": "F31.9",
            "ptsd": "F43.10",
            "post traumatic stress disorder": "F43.10",
            
            # Pain conditions
            "chronic pain": "G89.4",
            "chronic pain syndrome": "G89.4",
            "low back pain": "M54.5",
            "lumbago": "M54.5",
            "back pain": "M54.5",
            "neck pain": "M54.2",
            "headache": "R51",
            "migraine": "G43.909",
            "chronic migraine": "G43.909",
            "fibromyalgia": "M79.3",
            "arthritis": "M19.90",
            "osteoarthritis": "M19.90",
            "oa": "M19.90",
            "rheumatoid arthritis": "M06.9",
            "ra": "M06.9",
            
            # Metabolic conditions
            "obesity": "E66.9",
            "overweight": "E66.3",
            "hyperlipidemia": "E78.5",
            "high cholesterol": "E78.00",
            "hypercholesterolemia": "E78.00",
            "hld": "E78.5",
            "dyslipidemia": "E78.5",
            "metabolic syndrome": "E88.81",
            
            # Sleep disorders
            "sleep apnea": "G47.30",
            "obstructive sleep apnea": "G47.33",
            "osa": "G47.33",
            "insomnia": "G47.00",
            "sleep disorder": "G47.9",
            
            # Gastrointestinal
            "gerd": "K21.9",
            "acid reflux": "K21.9",
            "gastroesophageal reflux": "K21.9",
            "heartburn": "K21.9",
            "peptic ulcer": "K27.9",
            "gastritis": "K29.70",
            "ibs": "K58.9",
            "irritable bowel syndrome": "K58.9",
            "constipation": "K59.00",
            "diarrhea": "K59.1",
            "nausea": "R11.10",
            "vomiting": "R11.10",
            
            # Endocrine
            "hypothyroidism": "E03.9",
            "hyperthyroidism": "E05.90",
            "thyroid disorder": "E07.9",
            "adrenal insufficiency": "E27.40",
            
            # Kidney/Urinary
            "chronic kidney disease": "N18.9",
            "ckd": "N18.9",
            "kidney failure": "N19",
            "uti": "N39.0",
            "urinary tract infection": "N39.0",
            "kidney stones": "N20.0",
            "hematuria": "R31.9",
            "proteinuria": "R80.9",
            
            # Infectious diseases
            "covid": "U07.1",
            "covid-19": "U07.1",
            "coronavirus": "U07.1",
            "flu": "J11.1",
            "influenza": "J11.1",
            "pneumonia": "J18.9",
            "bronchitis": "J40",
            "sinusitis": "J32.9",
            "pharyngitis": "J02.9",
            "sore throat": "J02.9",
            
            # Skin conditions
            "eczema": "L30.9",
            "dermatitis": "L30.9",
            "psoriasis": "L40.9",
            "acne": "L70.9",
            "rash": "R21",
            
            # Neurological
            "seizure": "G40.909",
            "epilepsy": "G40.909",
            "stroke": "I63.9",
            "tia": "G93.1",
            "transient ischemic attack": "G93.1",
            "dementia": "F03.90",
            "alzheimer": "G30.9",
            "parkinson": "G20",
            "multiple sclerosis": "G35",
            "ms": "G35",
            
            # Eye conditions
            "glaucoma": "H40.9",
            "cataract": "H25.9",
            "macular degeneration": "H35.30",
            "diabetic retinopathy": "E11.319",
            
            # Cancer (general)
            "cancer": "C80.1",
            "malignancy": "C80.1",
            "tumor": "D49.9",
            "breast cancer": "C50.919",
            "lung cancer": "C78.00",
            "prostate cancer": "C61",
            "colon cancer": "C18.9",
        }

    def preprocess_text(self, text: str) -> str:
        """Enhanced text preprocessing for better medical term matching"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Replace common medical abbreviations
        abbreviations = {
            r'\bdm\b': 'diabetes mellitus',
            r'\bhtn\b': 'hypertension',
            r'\bcad\b': 'coronary artery disease',
            r'\bchf\b': 'congestive heart failure',
            r'\bcopd\b': 'chronic obstructive pulmonary disease',
            r'\bgerd\b': 'gastroesophageal reflux disease',
            r'\bra\b': 'rheumatoid arthritis',
            r'\bosa\b': 'obstructive sleep apnea',
            r'\bafib\b': 'atrial fibrillation',
            r'\bhld\b': 'hyperlipidemia',
            r'\bckd\b': 'chronic kidney disease',
            r'\bgad\b': 'generalized anxiety disorder',
            r'\bmdd\b': 'major depressive disorder',
            r'\bt2dm\b': 'type 2 diabetes mellitus',
            r'\bt1dm\b': 'type 1 diabetes mellitus',
            r'\bmi\b': 'myocardial infarction',
            r'\buti\b': 'urinary tract infection',
            r'\bibs\b': 'irritable bowel syndrome',
            r'\bms\b': 'multiple sclerosis',
            r'\btia\b': 'transient ischemic attack',
        }
        
        for abbr, full in abbreviations.items():
            text = re.sub(abbr, full, text)
        
        return text

    def extract_medical_conditions(self, text: str) -> Set[str]:
        """Extract potential medical conditions from text using various patterns"""
        conditions = set()
        processed_text = self.preprocess_text(text)
        
        # Pattern 1: Direct condition mentions
        for condition in self.condition_mappings.keys():
            if condition in processed_text:
                conditions.add(condition)
        
        # Pattern 2: Diagnosis patterns
        diagnosis_patterns = [
            r'diagnosed with ([^.,;:\n]+)',
            r'diagnosis of ([^.,;:\n]+)',
            r'has ([^.,;:\n]+)',
            r'suffers from ([^.,;:\n]+)',
            r'history of ([^.,;:\n]+)',
            r'presents with ([^.,;:\n]+)',
            r'complains of ([^.,;:\n]+)',
            r'treated for ([^.,;:\n]+)',
            r'managing ([^.,;:\n]+)',
            r'patient has ([^.,;:\n]+)',
            r'condition: ([^.,;:\n]+)',
            r'primary diagnosis: ([^.,;:\n]+)',
            r'secondary diagnosis: ([^.,;:\n]+)',
        ]
        
        for pattern in diagnosis_patterns:
            matches = re.finditer(pattern, processed_text, re.IGNORECASE)
            for match in matches:
                condition_text = match.group(1).strip().lower()
                # Check if extracted condition matches any known condition
                for known_condition in self.condition_mappings.keys():
                    if known_condition in condition_text or condition_text in known_condition:
                        conditions.add(known_condition)
        
        return conditions

    def identify_icd_codes_from_text(self, text: str) -> List[Dict[str, str]]:
        """
        Main function to identify ICD codes from medical text
        """
        if not text or not text.strip():
            return []
        
        # Extract conditions from text
        found_conditions = self.extract_medical_conditions(text)
        
        # Map conditions to ICD codes
        found_codes = set()
        for condition in found_conditions:
            if condition in self.condition_mappings:
                found_codes.add(self.condition_mappings[condition])
        
        # Convert to result format with descriptions
        result = []
        for code in found_codes:
            # Find the description from our ICD codes database
            description = self._get_code_description(code)
            if description:
                result.append({
                    "code": code,
                    "description": description,
                    "confidence": 0.8  # Base confidence for direct matches
                })
        
        # Sort by ICD code for consistent output
        return sorted(result, key=lambda x: x["code"])

    def _get_code_description(self, code: str) -> Optional[str]:
        """Get description for an ICD code"""
        for icd_entry in self.icd_codes:
            if icd_entry.get("code") == code:
                return icd_entry.get("description", "")
        return None

    def search_codes_by_description(self, query: str, limit: int = 10) -> List[Dict]:
        """Search ICD codes by description or code"""
        query = query.lower()
        matches = []
        
        for code_entry in self.icd_codes:
            code = code_entry.get("code", "").lower()
            description = code_entry.get("description", "").lower()
            
            if query in code or query in description:
                matches.append(code_entry)
        
        return matches[:limit]

# Singleton instance for use across the application
icd_extractor = ICDExtractor()