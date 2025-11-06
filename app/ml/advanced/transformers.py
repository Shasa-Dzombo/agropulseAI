"""
Transformer-based Agricultural AI Models

Advanced NLP and computer vision using Transformer architectures.

Features:
- BERT for agricultural text understanding
- GPT for report generation
- Vision Transformers (ViT) for image analysis
- Multi-modal transformers
- Fine-tuning on agricultural data
- Question answering systems
- Document understanding
- Sentiment analysis
"""

import logging
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import json

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import Dataset, DataLoader
    from transformers import (
        BertTokenizer, BertModel, BertForSequenceClassification,
        GPT2Tokenizer, GPT2LMHeadModel,
        ViTImageProcessor, ViTForImageClassification,
        AutoTokenizer, AutoModel, AutoModelForQuestionAnswering,
        Trainer, TrainingArguments
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    logging.warning("Transformers library not available")


logger = logging.getLogger(__name__)


@dataclass
class TextPrediction:
    """Text prediction result"""
    text: str
    label: str
    confidence: float
    embeddings: Optional[np.ndarray] = None
    attention_weights: Optional[np.ndarray] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class GeneratedText:
    """Generated text result"""
    prompt: str
    generated_text: str
    tokens_generated: int
    generation_time: float
    perplexity: float
    metadata: Dict = field(default_factory=dict)


class AgriculturalBERT:
    """
    BERT model fine-tuned for agricultural text understanding
    
    Applications:
    - Crop disease diagnosis from descriptions
    - Pest identification from reports
    - Weather impact analysis
    - Market sentiment analysis
    - Q&A for farmers
    """
    
    def __init__(
        self,
        model_name: str = 'bert-base-uncased',
        num_labels: int = 10,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        """
        Initialize Agricultural BERT
        
        Args:
            model_name: Pre-trained BERT model name
            num_labels: Number of classification labels
            device: Device to run on
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        self.device = device
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(
            model_name,
            num_labels=num_labels
        ).to(device)
        
        # Agricultural vocabulary extensions
        self.agricultural_terms = [
            'nitrogen', 'phosphorus', 'potassium', 'fertilizer',
            'irrigation', 'drought', 'harvest', 'planting',
            'pesticide', 'herbicide', 'fungicide', 'insecticide',
            'aphid', 'caterpillar', 'blight', 'rust', 'mildew',
            'organic', 'conventional', 'sustainable', 'precision'
        ]
        
        # Add agricultural terms to tokenizer
        self.tokenizer.add_tokens(self.agricultural_terms)
        self.model.resize_token_embeddings(len(self.tokenizer))
        
        logger.info(f"AgriculturalBERT initialized on {device}")
    
    def encode_text(
        self,
        text: str,
        max_length: int = 512
    ) -> Dict[str, torch.Tensor]:
        """
        Encode text to BERT input format
        
        Args:
            text: Input text
            max_length: Maximum sequence length
            
        Returns:
            Dictionary with input_ids, attention_mask, token_type_ids
        """
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {k: v.to(self.device) for k, v in encoding.items()}
    
    def classify_text(
        self,
        text: str,
        labels: List[str]
    ) -> TextPrediction:
        """
        Classify agricultural text
        
        Args:
            text: Input text
            labels: List of possible labels
            
        Returns:
            Text prediction
        """
        # Encode text
        inputs = self.encode_text(text)
        
        # Run inference
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predictions = torch.softmax(logits, dim=-1)
        
        # Get top prediction
        confidence, predicted_idx = torch.max(predictions, dim=-1)
        predicted_label = labels[predicted_idx.item()]
        
        return TextPrediction(
            text=text,
            label=predicted_label,
            confidence=confidence.item(),
            metadata={'all_probabilities': predictions[0].cpu().numpy().tolist()}
        )
    
    def get_embeddings(self, text: str) -> np.ndarray:
        """Get BERT embeddings for text"""
        inputs = self.encode_text(text)
        
        self.model.eval()
        with torch.no_grad():
            outputs = self.model.bert(**inputs)
            # Use [CLS] token embedding
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()
        
        return embeddings[0]
    
    def fine_tune(
        self,
        train_texts: List[str],
        train_labels: List[int],
        val_texts: Optional[List[str]] = None,
        val_labels: Optional[List[int]] = None,
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5,
        output_dir: str = './agricultural_bert'
    ):
        """
        Fine-tune BERT on agricultural data
        
        Args:
            train_texts: Training texts
            train_labels: Training labels
            val_texts: Validation texts
            val_labels: Validation labels
            epochs: Number of epochs
            batch_size: Batch size
            learning_rate: Learning rate
            output_dir: Output directory
        """
        # Create dataset
        class AgriDataset(Dataset):
            def __init__(self, texts, labels, tokenizer, max_length=512):
                self.texts = texts
                self.labels = labels
                self.tokenizer = tokenizer
                self.max_length = max_length
            
            def __len__(self):
                return len(self.texts)
            
            def __getitem__(self, idx):
                encoding = self.tokenizer(
                    self.texts[idx],
                    add_special_tokens=True,
                    max_length=self.max_length,
                    padding='max_length',
                    truncation=True,
                    return_tensors='pt'
                )
                
                return {
                    'input_ids': encoding['input_ids'].flatten(),
                    'attention_mask': encoding['attention_mask'].flatten(),
                    'labels': torch.tensor(self.labels[idx], dtype=torch.long)
                }
        
        train_dataset = AgriDataset(train_texts, train_labels, self.tokenizer)
        
        eval_dataset = None
        if val_texts and val_labels:
            eval_dataset = AgriDataset(val_texts, val_labels, self.tokenizer)
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            warmup_steps=500,
            weight_decay=0.01,
            logging_dir=f'{output_dir}/logs',
            logging_steps=100,
            evaluation_strategy="epoch" if eval_dataset else "no",
            save_strategy="epoch",
            load_best_model_at_end=True if eval_dataset else False,
        )
        
        # Trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset
        )
        
        # Train
        logger.info(f"Starting fine-tuning for {epochs} epochs...")
        trainer.train()
        
        # Save model
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        logger.info(f"Fine-tuning completed. Model saved to {output_dir}")


class AgriculturalGPT:
    """
    GPT model for agricultural text generation
    
    Applications:
    - Crop care recommendations
    - Pest management guides
    - Market reports
    - Weather advisories
    - Farming tips
    """
    
    def __init__(
        self,
        model_name: str = 'gpt2',
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        """
        Initialize Agricultural GPT
        
        Args:
            model_name: Pre-trained GPT model name
            device: Device to run on
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        self.device = device
        self.tokenizer = GPT2Tokenizer.from_pretrained(model_name)
        self.model = GPT2LMHeadModel.from_pretrained(model_name).to(device)
        
        # Set pad token
        self.tokenizer.pad_token = self.tokenizer.eos_token
        
        logger.info(f"AgriculturalGPT initialized on {device}")
    
    def generate_text(
        self,
        prompt: str,
        max_length: int = 200,
        temperature: float = 0.7,
        top_k: int = 50,
        top_p: float = 0.95,
        num_return_sequences: int = 1
    ) -> GeneratedText:
        """
        Generate agricultural text
        
        Args:
            prompt: Input prompt
            max_length: Maximum generation length
            temperature: Sampling temperature
            top_k: Top-k sampling
            top_p: Top-p (nucleus) sampling
            num_return_sequences: Number of sequences to generate
            
        Returns:
            Generated text
        """
        import time
        
        # Encode prompt
        inputs = self.tokenizer.encode(prompt, return_tensors='pt').to(self.device)
        
        # Generate
        self.model.eval()
        start_time = time.time()
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                max_length=max_length,
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                num_return_sequences=num_return_sequences,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        generation_time = time.time() - start_time
        
        # Decode generated text
        generated_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Remove prompt from generated text
        generated_text = generated_text[len(prompt):].strip()
        
        # Calculate perplexity (simplified)
        perplexity = 0.0  # Would need proper calculation
        
        return GeneratedText(
            prompt=prompt,
            generated_text=generated_text,
            tokens_generated=len(outputs[0]) - len(inputs[0]),
            generation_time=generation_time,
            perplexity=perplexity
        )
    
    def generate_recommendation(
        self,
        crop: str,
        issue: str,
        context: Optional[str] = None
    ) -> str:
        """
        Generate crop care recommendation
        
        Args:
            crop: Crop name
            issue: Issue description
            context: Optional context
            
        Returns:
            Recommendation text
        """
        prompt = f"Crop: {crop}\nIssue: {issue}\n"
        if context:
            prompt += f"Context: {context}\n"
        prompt += "Recommendation: "
        
        result = self.generate_text(prompt, max_length=300)
        return result.generated_text


class VisionTransformerCropAnalysis:
    """
    Vision Transformer for crop image analysis
    
    Applications:
    - Crop health assessment
    - Growth stage detection
    - Yield estimation
    - Quality grading
    """
    
    def __init__(
        self,
        model_name: str = 'google/vit-base-patch16-224',
        num_labels: int = 10,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu'
    ):
        """
        Initialize Vision Transformer
        
        Args:
            model_name: Pre-trained ViT model name
            num_labels: Number of classification labels
            device: Device to run on
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        self.device = device
        self.processor = ViTImageProcessor.from_pretrained(model_name)
        self.model = ViTForImageClassification.from_pretrained(
            model_name,
            num_labels=num_labels,
            ignore_mismatched_sizes=True
        ).to(device)
        
        logger.info(f"VisionTransformer initialized on {device}")
    
    def classify_image(
        self,
        image: np.ndarray,
        labels: List[str]
    ) -> TextPrediction:
        """
        Classify crop image
        
        Args:
            image: Input image (numpy array)
            labels: List of possible labels
            
        Returns:
            Classification result
        """
        # Preprocess image
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # Run inference
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            predictions = torch.softmax(logits, dim=-1)
        
        # Get top prediction
        confidence, predicted_idx = torch.max(predictions, dim=-1)
        predicted_label = labels[predicted_idx.item()]
        
        # Get attention weights
        attention_weights = None
        if hasattr(outputs, 'attentions') and outputs.attentions is not None:
            # Average attention across layers and heads
            attention_weights = torch.stack(outputs.attentions).mean(dim=(0, 1))
            attention_weights = attention_weights.cpu().numpy()
        
        return TextPrediction(
            text=f"Image classification: {predicted_label}",
            label=predicted_label,
            confidence=confidence.item(),
            attention_weights=attention_weights
        )


class MultiModalAgriculturalAI:
    """
    Multi-modal AI combining text and image understanding
    
    Applications:
    - Complete farm analysis
    - Integrated diagnostics
    - Smart recommendations
    """
    
    def __init__(self):
        """Initialize multi-modal AI"""
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        self.text_model = AgriculturalBERT()
        self.vision_model = VisionTransformerCropAnalysis()
        self.language_model = AgriculturalGPT()
        
        logger.info("MultiModalAgriculturalAI initialized")
    
    def analyze_farm_situation(
        self,
        image: np.ndarray,
        description: str,
        farmer_question: str
    ) -> Dict:
        """
        Comprehensive farm situation analysis
        
        Args:
            image: Farm/crop image
            description: Text description
            farmer_question: Farmer's question
            
        Returns:
            Complete analysis with recommendations
        """
        # Visual analysis
        visual_result = self.vision_model.classify_image(
            image,
            labels=['healthy', 'diseased', 'stressed', 'mature', 'immature']
        )
        
        # Text understanding
        text_result = self.text_model.classify_text(
            description,
            labels=['disease', 'pest', 'nutrition', 'water', 'normal']
        )
        
        # Generate integrated recommendation
        context = f"Visual assessment: {visual_result.label} ({visual_result.confidence:.2f}). "
        context += f"Text analysis: {text_result.label} ({text_result.confidence:.2f}). "
        context += f"Farmer question: {farmer_question}"
        
        recommendation = self.language_model.generate_recommendation(
            crop="detected_crop",
            issue=text_result.label,
            context=context
        )
        
        return {
            'visual_analysis': {
                'assessment': visual_result.label,
                'confidence': visual_result.confidence
            },
            'text_analysis': {
                'category': text_result.label,
                'confidence': text_result.confidence
            },
            'recommendation': recommendation,
            'severity': self._calculate_severity(visual_result, text_result),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_severity(
        self,
        visual_result: TextPrediction,
        text_result: TextPrediction
    ) -> str:
        """Calculate overall severity"""
        avg_confidence = (visual_result.confidence + text_result.confidence) / 2
        
        if visual_result.label in ['diseased', 'stressed'] and avg_confidence > 0.7:
            return 'high'
        elif text_result.label in ['disease', 'pest'] and avg_confidence > 0.6:
            return 'medium'
        else:
            return 'low'


class QuestionAnsweringSystem:
    """
    Question answering for agricultural knowledge
    
    Provides answers to farmer questions from knowledge base.
    """
    
    def __init__(
        self,
        model_name: str = 'deepset/roberta-base-squad2'
    ):
        """
        Initialize QA system
        
        Args:
            model_name: Pre-trained QA model name
        """
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("Transformers library not available")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForQuestionAnswering.from_pretrained(model_name)
        
        # Agricultural knowledge base (simplified)
        self.knowledge_base = {
            'tomato': "Tomatoes require full sun, well-drained soil with pH 6.0-6.8, regular watering (1-2 inches per week), and support stakes. Common diseases include early blight, late blight, and fusarium wilt. Harvest when fruits are fully colored.",
            'corn': "Corn needs full sun, fertile soil with pH 5.8-6.8, and consistent moisture. Plant after last frost when soil is 60°F. Common pests include corn borers and armyworms. Harvest when kernels are plump and milky.",
            'wheat': "Wheat grows best in cool weather with moderate rainfall. Sow in fall for winter wheat or spring for spring wheat. Requires pH 6.0-7.0 and good drainage. Harvest when grain moisture is 13-14%."
        }
        
        logger.info("QuestionAnsweringSystem initialized")
    
    def answer_question(
        self,
        question: str,
        crop: Optional[str] = None
    ) -> Tuple[str, float]:
        """
        Answer farmer question
        
        Args:
            question: Question text
            crop: Optional crop context
            
        Returns:
            (answer, confidence)
        """
        # Get relevant context
        if crop and crop.lower() in self.knowledge_base:
            context = self.knowledge_base[crop.lower()]
        else:
            # Use all knowledge
            context = " ".join(self.knowledge_base.values())
        
        # Encode question and context
        inputs = self.tokenizer(
            question,
            context,
            add_special_tokens=True,
            return_tensors="pt"
        )
        
        # Get answer
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(**inputs)
            answer_start = torch.argmax(outputs.start_logits)
            answer_end = torch.argmax(outputs.end_logits) + 1
            
            # Calculate confidence
            start_confidence = torch.softmax(outputs.start_logits, dim=-1)[0, answer_start]
            end_confidence = torch.softmax(outputs.end_logits, dim=-1)[0, answer_end-1]
            confidence = (start_confidence * end_confidence).item()
        
        # Decode answer
        answer = self.tokenizer.decode(
            inputs['input_ids'][0][answer_start:answer_end],
            skip_special_tokens=True
        )
        
        return answer, confidence
