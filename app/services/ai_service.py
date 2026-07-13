import boto3
import io
from PIL import Image
from typing import List, Dict, Optional
import json
from app.config import settings
import time


class AWSAIService:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        self.sagemaker_runtime = boto3.client(
            'sagemaker-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        self.bedrock_runtime = boto3.client(
            'bedrock-runtime',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
    
    async def upload_to_s3(self, file_content: bytes, file_name: str, folder: str = "diagnoses") -> str:
        """
        Upload image to S3 and return URL
        """
        try:
            key = f"{folder}/{file_name}"
            self.s3_client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
                Body=file_content,
                ContentType='image/jpeg'
            )

            url = f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            return url
        except Exception as e:
            print(f"Error uploading to S3: {e}")
            raise
    
    async def diagnose_crop_disease(
        self,
        image_urls: List[str],
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Perform crop disease diagnosis using AWS SageMaker endpoint
        """
        start_time = time.time()
        
        try:
            # Prepare input for SageMaker
            payload = {
                "image_urls": image_urls,
                "metadata": metadata or {}
            }
            
            # Call SageMaker endpoint
            response = self.sagemaker_runtime.invoke_endpoint(
                EndpointName=settings.AWS_SAGEMAKER_ENDPOINT,
                ContentType='application/json',
                Body=json.dumps(payload)
            )
            
            result = json.loads(response['Body'].read().decode())
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "primary_diagnosis": result.get("diagnosis"),
                "confidence_score": result.get("confidence", 0.0),
                "category": result.get("category"),
                "alternative_diagnoses": result.get("alternatives", []),
                "affected_area_percentage": result.get("affected_area", 0.0),
                "severity_level": result.get("severity", "unknown"),
                "treatment_recommendations": result.get("treatments", []),
                "preventive_measures": result.get("prevention", []),
                "processing_time_seconds": processing_time,
                "ai_model_version": result.get("model_version", "1.0")
            }
        
        except Exception as e:
            print(f"Error in crop diagnosis: {e}")
            return {
                "success": False,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
    
    async def generate_treatment_recommendations(
        self,
        diagnosis: str,
        crop_type: str,
        severity: str
    ) -> Dict:
        """
        Use AWS Bedrock (Claude) to generate detailed treatment recommendations
        """
        try:
            prompt = f"""
            You are an expert agronomist. A farmer has the following crop issue:
            
            Crop: {crop_type}
            Diagnosis: {diagnosis}
            Severity: {severity}
            
            Please provide:
            1. Immediate treatment steps
            2. Recommended products (pesticides, fungicides, or fertilizers)
            3. Application methods and dosage
            4. Preventive measures for future
            5. Expected recovery timeline
            6. Estimated cost in Kenyan Shillings
            
            Format the response as JSON.
            """
            
            body = json.dumps({
                "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                "max_tokens_to_sample": 1000,
                "temperature": 0.5,
                "top_p": 0.9,
            })
            
            response = self.bedrock_runtime.invoke_model(
                modelId=settings.AWS_BEDROCK_MODEL_ID,
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            recommendations = response_body.get('completion', '')
            
            # Parse the JSON response
            try:
                parsed_recommendations = json.loads(recommendations)
            except:
                parsed_recommendations = {"raw_text": recommendations}
            
            return {
                "success": True,
                "recommendations": parsed_recommendations
            }
        
        except Exception as e:
            print(f"Error generating recommendations: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class AzureAIService:
    def __init__(self):
        self.subscription_key = settings.AZURE_SUBSCRIPTION_KEY
        self.endpoint = settings.AZURE_ENDPOINT
    
    async def analyze_crop_image(self, image_url: str) -> Dict:
        """
        Analyze crop image using Azure Computer Vision
        """
        import httpx
        
        url = f"{self.endpoint}/vision/v3.2/analyze"
        
        headers = {
            'Ocp-Apim-Subscription-Key': self.subscription_key,
            'Content-Type': 'application/json'
        }
        
        params = {
            'visualFeatures': 'Objects,Tags,Description,Color',
            'details': 'Landmarks'
        }
        
        body = {"url": image_url}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    params=params,
                    json=body,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            print(f"Error analyzing image with Azure: {e}")
            return {"error": str(e)}


# Singleton instances
aws_ai_service = AWSAIService()
azure_ai_service = AzureAIService()
