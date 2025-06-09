from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum
import tempfile
import os
from pathlib import Path
import logging

from utils.pdf_processor import process_blood_report, ProcessingError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class TestStatus(str, Enum):
    NORMAL = "normal"
    HIGH = "high"
    LOW = "low"

class Severity(str, Enum):
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"

class BloodTest(BaseModel):
    testName: str = Field(..., description="Name of the blood test")
    value: float = Field(..., description="Test result value")
    unit: str = Field(..., description="Unit of measurement")

    model_config = {
        "json_schema_extra": {
            "example": {
                "testName": "Hemoglobin",
                "value": 14.5,
                "unit": "g/dL"
            }
        }
    }

class BloodTestResult(BaseModel):
    testName: str
    value: float
    unit: str
    normalRange: str
    status: TestStatus
    severity: Optional[Severity] = None
    suggestion: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "testName": "Hemoglobin",
                "value": 14.5,
                "unit": "g/dL",
                "normalRange": "13.5-17.5",
                "status": "normal",
                "severity": None,
                "suggestion": None
            }
        }
    }

class BloodTestResponse(BaseModel):
    tests: List[BloodTestResult]
    summary: Dict[str, int]
    interpretation: str
    recommendations: List[str]

    model_config = {
        "json_schema_extra": {
            "example": {
                "tests": [{
                    "testName": "Hemoglobin",
                    "value": 14.5,
                    "unit": "g/dL",
                    "normalRange": "13.5-17.5",
                    "status": "normal",
                    "severity": None,
                    "suggestion": None
                }],
                "summary": {
                    "normalCount": 1,
                    "abnormalCount": 0,
                    "criticalCount": 0
                },
                "interpretation": "All blood test results are within normal ranges.",
                "recommendations": ["Continue regular health maintenance and scheduled check-ups."]
            }
        }
    }

class ProcessingMetadata(BaseModel):
    success: bool
    pdf_type: str
    extraction_method: str = ""
    test_count: int = 0
    error_type: str = ""
    error_details: Dict[str, Any] = {}

class AnalysisResponse(BaseModel):
    success: bool
    results: List[BloodTestResult] = []
    metadata: ProcessingMetadata
    message: str = ""

# Reference ranges and units for common blood tests
REFERENCE_RANGES = {
    "hemoglobin": {
        "unit": "g/dL",
        "ranges": {
            "male": {"min": 13.5, "max": 17.5},
            "female": {"min": 12.0, "max": 15.5}
        },
        "severity_thresholds": {
            "high": {"mild": 18, "moderate": 20},
            "low": {"mild": 11, "moderate": 9}
        }
    },
    "wbc": {
        "unit": "×10³/μL",
        "ranges": {"min": 4.0, "max": 11.0},
        "severity_thresholds": {
            "high": {"mild": 12, "moderate": 15},
            "low": {"mild": 3.5, "moderate": 2.5}
        }
    },
    "platelets": {
        "unit": "×10³/μL",
        "ranges": {"min": 150, "max": 450},
        "severity_thresholds": {
            "high": {"mild": 500, "moderate": 700},
            "low": {"mild": 100, "moderate": 50}
        }
    },
    "glucose_fasting": {
        "unit": "mg/dL",
        "ranges": {"min": 70, "max": 100},
        "severity_thresholds": {
            "high": {"mild": 120, "moderate": 160},
            "low": {"mild": 60, "moderate": 50}
        }
    },
    "cholesterol_total": {
        "unit": "mg/dL",
        "ranges": {"min": 0, "max": 200},
        "severity_thresholds": {
            "high": {"mild": 240, "moderate": 300},
            "low": None
        }
    },
    "rbc": {
        "unit": "M/µL",
        "ranges": {"min": 4.5, "max": 5.9},
        "severity_thresholds": {
            "high": {"mild": 6.1, "moderate": 6.5},
            "low": {"mild": 4.0, "moderate": 3.5}
        }
    },
    "hematocrit": {
        "unit": "%",
        "ranges": {
            "male": {"min": 41, "max": 50},
            "female": {"min": 36, "max": 44}
        },
        "severity_thresholds": {
            "high": {"mild": 52, "moderate": 55},
            "low": {"mild": 34, "moderate": 30}
        }
    },
    "mcv": {
        "unit": "fL",
        "ranges": {"min": 80, "max": 96},
        "severity_thresholds": {
            "high": {"mild": 98, "moderate": 102},
            "low": {"mild": 78, "moderate": 75}
        }
    },
    "mch": {
        "unit": "pg",
        "ranges": {"min": 27.5, "max": 33.2},
        "severity_thresholds": {
            "high": {"mild": 34, "moderate": 36},
            "low": {"mild": 26, "moderate": 24}
        }
    },
    "mchc": {
        "unit": "g/dL",
        "ranges": {"min": 33.4, "max": 35.5},
        "severity_thresholds": {
            "high": {"mild": 36, "moderate": 37},
            "low": {"mild": 32, "moderate": 31}
        }
    }
}

def normalize_test_name(test_name: str) -> str:
    """Convert test name to standardized key."""
    test_name = test_name.lower().replace(" ", "_")
    test_name = test_name.replace("(", "").replace(")", "")
    return test_name

def get_test_status(value: float, ranges: Dict[str, float]) -> tuple[TestStatus, Optional[Severity]]:
    """Determine test status and severity."""
    if value < ranges["min"]:
        status = TestStatus.LOW
    elif value > ranges["max"]:
        status = TestStatus.HIGH
    else:
        return TestStatus.NORMAL, None

    # Check severity thresholds if available
    severity = None
    if "severity_thresholds" in ranges:
        thresholds = ranges["severity_thresholds"][status]
        if thresholds:
            if status == TestStatus.HIGH:
                if value >= thresholds.get("moderate", float("inf")):
                    severity = Severity.MODERATE
                elif value >= thresholds.get("mild", float("inf")):
                    severity = Severity.MILD
            else:  # LOW
                if value <= thresholds.get("moderate", float("-inf")):
                    severity = Severity.MODERATE
                elif value <= thresholds.get("mild", float("-inf")):
                    severity = Severity.MILD

    return status, severity

def get_suggestion(test_name: str, status: TestStatus, severity: Optional[Severity]) -> Optional[str]:
    """Generate suggestions based on test results."""
    suggestions = {
        "hemoglobin": {
            "high": "Elevated hemoglobin may indicate polycythemia. Consider further evaluation.",
            "low": "Low hemoglobin may indicate anemia. Consider iron supplementation and dietary changes."
        },
        "wbc": {
            "high": "Elevated WBC count may indicate infection or inflammation. Monitor closely.",
            "low": "Low WBC count may indicate reduced immune function. Monitor for infections."
        },
        "platelets": {
            "high": "Elevated platelet count may indicate thrombocytosis. Monitor for clotting risks.",
            "low": "Low platelet count may increase bleeding risk. Monitor for bruising or bleeding."
        },
        "glucose_fasting": {
            "high": "Elevated fasting glucose may indicate pre-diabetes or diabetes. Consider dietary changes.",
            "low": "Low blood sugar may cause fatigue and dizziness. Consider regular meal timing."
        },
        "cholesterol_total": {
            "high": "Elevated cholesterol increases cardiovascular risk. Consider dietary modifications and exercise.",
            "low": None
        },
        "rbc": {
            "high": "Elevated RBC count may indicate polycythemia. Further evaluation recommended.",
            "low": "Low RBC count may indicate anemia. Consider iron status evaluation."
        },
        "hematocrit": {
            "high": "Elevated hematocrit may indicate dehydration or polycythemia.",
            "low": "Low hematocrit may indicate anemia or overhydration."
        },
        "mcv": {
            "high": "High MCV may indicate macrocytic anemia. Check B12 and folate levels.",
            "low": "Low MCV may indicate microcytic anemia. Check iron status."
        },
        "mch": {
            "high": "High MCH may indicate macrocytic anemia.",
            "low": "Low MCH may indicate iron deficiency."
        },
        "mchc": {
            "high": "High MCHC may indicate hereditary spherocytosis.",
            "low": "Low MCHC may indicate iron deficiency anemia."
        }
    }
    
    if test_name in suggestions and status != TestStatus.NORMAL:
        base_suggestion = suggestions[test_name][status.lower()]
        if severity == Severity.MODERATE:
            return f"{base_suggestion} Consultation recommended."
        return base_suggestion
    return None

def analyze_blood_tests(tests: List[BloodTest]) -> BloodTestResponse:
    """Analyze blood test results and provide interpretations."""
    analyzed_tests = []
    abnormal_tests = []
    critical_tests = []

    for test in tests:
        normalized_name = normalize_test_name(test.testName)
        
        if normalized_name not in REFERENCE_RANGES:
            continue

        reference = REFERENCE_RANGES[normalized_name]
        
        # Verify unit matches
        if test.unit != reference["unit"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid unit for {test.testName}. Expected {reference['unit']}"
            )

        # Get ranges (handle gender-specific ranges)
        ranges = reference["ranges"]
        if isinstance(ranges, dict) and "male" in ranges:
            # For demo, use male ranges. In production, add gender to request
            ranges = ranges["male"]

        # Analyze test result
        status, severity = get_test_status(test.value, ranges)
        
        # Generate suggestion if needed
        suggestion = get_suggestion(normalized_name, status, severity) if status != TestStatus.NORMAL else None

        # Format normal range string
        normal_range = f"{ranges['min']}-{ranges['max']}"

        result = BloodTestResult(
            testName=test.testName,
            value=test.value,
            unit=test.unit,
            normalRange=normal_range,
            status=status,
            severity=severity,
            suggestion=suggestion
        )
        
        analyzed_tests.append(result)
        
        if status != TestStatus.NORMAL:
            abnormal_tests.append(result)
            if severity == Severity.MODERATE:
                critical_tests.append(result)

    # Generate summary
    summary = {
        "normalCount": len(analyzed_tests) - len(abnormal_tests),
        "abnormalCount": len(abnormal_tests),
        "criticalCount": len(critical_tests)
    }

    # Generate interpretation
    interpretation = generate_interpretation(abnormal_tests, critical_tests)
    
    # Generate recommendations
    recommendations = generate_recommendations(abnormal_tests, critical_tests)

    return BloodTestResponse(
        tests=analyzed_tests,
        summary=summary,
        interpretation=interpretation,
        recommendations=recommendations
    )

def generate_interpretation(abnormal_tests: List[BloodTestResult], critical_tests: List[BloodTestResult]) -> str:
    """Generate a clinical interpretation of the results."""
    if not abnormal_tests:
        return "All blood test results are within normal ranges."

    critical_count = len(critical_tests)
    abnormal_count = len(abnormal_tests)

    interpretation = []
    
    if critical_count > 0:
        interpretation.append(f"Found {critical_count} test{'s' if critical_count > 1 else ''} requiring immediate attention.")
    
    # Add specific details for abnormal tests
    for test in abnormal_tests:
        status_text = "elevated" if test.status == TestStatus.HIGH else "low"
        interpretation.append(f"{test.testName} is {status_text} ({test.value} {test.unit}).")

    return " ".join(interpretation)

def generate_recommendations(abnormal_tests: List[BloodTestResult], critical_tests: List[BloodTestResult]) -> List[str]:
    """Generate recommendations based on test results."""
    recommendations = set()

    if not abnormal_tests:
        return ["Continue regular health maintenance and scheduled check-ups."]

    # Add general recommendations based on abnormal results
    if critical_tests:
        recommendations.add("Schedule a follow-up appointment with your healthcare provider to discuss critical results.")

    # Add test-specific recommendations
    for test in abnormal_tests:
        if test.suggestion:
            recommendations.add(test.suggestion.split(". ")[0] + ".")

    # Add general health recommendations
    recommendations.add("Maintain a balanced diet and regular exercise routine.")
    if len(abnormal_tests) > 0:
        recommendations.add("Consider scheduling a follow-up test to monitor changes.")

    return list(recommendations)

def extract_medical_entities_from_blood_tests(tests: List[BloodTestResult]) -> List[Dict[str, Any]]:
    """Extract comprehensive medical entities from blood test results."""
    entities = []
    
    # Define entity categories and their patterns
    test_categories = {
        "BLOOD_COUNT": {
            "tests": ["hemoglobin", "hematocrit", "rbc", "wbc", "platelets", "mcv", "mch", "mchc"],
            "description": "Complete Blood Count"
        },
        "METABOLIC": {
            "tests": ["glucose", "cholesterol", "triglycerides", "hdl", "ldl", "alt", "ast", "albumin"],
            "description": "Metabolic Panel"
        },
        "ELECTROLYTES": {
            "tests": ["sodium", "potassium", "chloride", "bicarbonate", "calcium", "magnesium", "phosphate"],
            "description": "Electrolyte Panel"
        },
        "KIDNEY": {
            "tests": ["creatinine", "bun", "egfr", "uric_acid"],
            "description": "Kidney Function"
        },
        "LIVER": {
            "tests": ["alt", "ast", "alp", "ggt", "bilirubin", "protein"],
            "description": "Liver Function"
        }
    }
    
    # Track which categories have abnormal results
    abnormal_categories = set()
    
    # Process each test result
    for test in tests:
        test_name = test.testName.lower()
        
        # Add the test itself as a medical entity
        entities.append({
            "text": test.testName,
            "type": "LAB_TEST",
            "confidence": 1.0,
            "value": f"{test.value} {test.unit}",
            "status": test.status,
            "normalRange": test.normalRange
        })
        
        # If test is abnormal, add it as a condition entity
        if test.status != TestStatus.NORMAL:
            condition_text = f"{test.status.capitalize()} {test.testName}"
            entities.append({
                "text": condition_text,
                "type": "CONDITION",
                "confidence": 1.0,
                "details": f"{test.value} {test.unit} (Normal: {test.normalRange})"
            })
            
            # Add severity if present
            if test.severity:
                entities.append({
                    "text": f"{test.severity.capitalize()} {condition_text}",
                    "type": "SEVERITY",
                    "confidence": 1.0,
                    "details": test.suggestion if test.suggestion else ""
                })
        
        # Check which category this test belongs to
        for category, info in test_categories.items():
            if any(test_pattern in test_name for test_pattern in info["tests"]):
                if test.status != TestStatus.NORMAL:
                    abnormal_categories.add(category)
                break
    
    # Add category-level entities for abnormal categories
    for category in abnormal_categories:
        entities.append({
            "text": test_categories[category]["description"],
            "type": "TEST_PANEL",
            "confidence": 1.0,
            "details": f"Abnormalities detected in {test_categories[category]['description']}"
        })
    
    # Add clinical interpretations based on patterns
    clinical_patterns = {
        "ANEMIA": {
            "conditions": [
                lambda t: any(test.testName.lower() == "hemoglobin" and test.status == TestStatus.LOW for test in tests),
                lambda t: any(test.testName.lower() == "hematocrit" and test.status == TestStatus.LOW for test in tests)
            ],
            "text": "Possible Anemia"
        },
        "INFECTION": {
            "conditions": [
                lambda t: any(test.testName.lower() == "wbc" and test.status == TestStatus.HIGH for test in tests)
            ],
            "text": "Possible Infection/Inflammation"
        },
        "DIABETES_RISK": {
            "conditions": [
                lambda t: any(test.testName.lower() == "glucose_fasting" and test.status == TestStatus.HIGH for test in tests)
            ],
            "text": "Elevated Diabetes Risk"
        },
        "BLEEDING_RISK": {
            "conditions": [
                lambda t: any(test.testName.lower() == "platelets" and test.status == TestStatus.LOW for test in tests)
            ],
            "text": "Increased Bleeding Risk"
        }
    }
    
    # Check for clinical patterns
    for pattern_name, pattern_info in clinical_patterns.items():
        if all(condition(tests) for condition in pattern_info["conditions"]):
            entities.append({
                "text": pattern_info["text"],
                "type": "CLINICAL_INTERPRETATION",
                "confidence": 0.9,
                "details": f"Based on abnormal test results"
            })
    
    return entities

@router.post("/upload-blood-report")
async def upload_blood_report(file: UploadFile):
    """
    Upload and analyze a blood test report PDF.
    Returns structured blood test results with analysis.
    
    Raises:
        400: If file is not a PDF
        422: If no valid blood test results could be extracted
        500: For other processing errors
    """
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    tmp_path = None
    try:
        # Create a temporary file to store the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
            logger.info(f"Processing blood report PDF: {file.filename}")

            # Process the PDF and extract test results
            test_results, metadata = process_blood_report(tmp_path)
            
            if not test_results:
                logger.warning(f"No test results extracted from {file.filename}")
                raise HTTPException(
                    status_code=422,
                    detail={
                        "message": "Could not extract any valid blood test results from the PDF",
                        "metadata": metadata
                    }
                )
            
            logger.info(f"Successfully extracted {len(test_results)} test results using {metadata['extraction_method']}")
            
            # Analyze the test results
            analysis = analyze_blood_tests([BloodTest(**test) for test in test_results])
            
            # Extract medical entities
            medical_entities = extract_medical_entities_from_blood_tests(analysis.tests)
            
            # Format response to match medical document analysis
            abnormal_tests = [test for test in analysis.tests if test.status != "normal"]
            critical_tests = [test for test in abnormal_tests if test.severity == "severe"]
            
            # Generate diagnosis from abnormal tests
            diagnosis = []
            if abnormal_tests:
                diagnosis.append("Blood test abnormalities detected:")
                for test in abnormal_tests:
                    diagnosis.append(f"{test.testName} is {test.status} ({test.value} {test.unit})")
            
            # Generate treatments from recommendations
            treatments = []
            if analysis.recommendations:
                treatments.extend(analysis.recommendations)
            
            # Generate medical history from interpretation
            history = []
            if analysis.interpretation:
                history.append(analysis.interpretation)
            
            return {
                "success": True,
                "primary_diagnosis": diagnosis[0] if diagnosis else "All blood test results are normal",
                "prescribed_medication": treatments,
                "followup_instructions": history[0] if history else "",
                "medical_entities": medical_entities,
                "icd_codes": [],  # TODO: Add ICD code mapping for blood test abnormalities
                "blood_data": {
                    "tests": analysis.tests,
                    "summary": analysis.summary,
                    "interpretation": analysis.interpretation,
                    "recommendations": analysis.recommendations
                }
            }
            
    except ProcessingError as pe:
        logger.error(f"Processing error for {file.filename}: {pe.message}")
        raise HTTPException(
            status_code=422,
            detail={
                "message": pe.message,
                "error_type": pe.error_type,
                "details": pe.details
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error processing {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing blood report: {str(e)}"
        )
    finally:
        # Clean up the temporary file
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {tmp_path}: {str(e)}") 