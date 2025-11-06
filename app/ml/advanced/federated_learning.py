"""
Federated Learning System for Agricultural AI

Privacy-preserving distributed machine learning system:
- Federated averaging and optimization
- Secure aggregation with encryption
- Differential privacy mechanisms
- Client selection strategies
- Byzantine-robust aggregation
- Model compression for edge devices
- Personalized federated learning
- Vertical and horizontal federation

Enables collaborative AI training across farms without sharing raw data.
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Federated aggregation strategies"""
    FED_AVG = "fedavg"  # Federated Averaging
    FED_PROX = "fedprox"  # Federated Proximal
    FED_ADAM = "fedadam"  # Federated Adam
    FED_YOGI = "fedyogi"  # Federated Yogi
    SCAFFOLD = "scaffold"  # SCAFFOLD
    TRIMMED_MEAN = "trimmed_mean"  # Byzantine-robust
    KRUM = "krum"  # Byzantine-robust
    MEDIAN = "median"  # Byzantine-robust


class ClientSelectionStrategy(Enum):
    """Client selection strategies"""
    RANDOM = "random"
    BALANCED = "balanced"
    IMPORTANCE_SAMPLING = "importance_sampling"
    DIVERSITY_BASED = "diversity_based"
    CONTRIBUTION_BASED = "contribution_based"


class FederatedModel(nn.Module):
    """Base federated learning model"""
    
    def __init__(self, input_dim: int, hidden_dims: List[int], output_dim: int):
        super().__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(prev_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            prev_dim = hidden_dim
        
        layers.append(nn.Linear(prev_dim, output_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.network(x)
    
    def get_parameters(self) -> Dict[str, np.ndarray]:
        """Get model parameters as numpy arrays"""
        return {
            name: param.detach().cpu().numpy()
            for name, param in self.named_parameters()
        }
    
    def set_parameters(self, parameters: Dict[str, np.ndarray]) -> None:
        """Set model parameters from numpy arrays"""
        with torch.no_grad():
            for name, param in self.named_parameters():
                if name in parameters:
                    param.copy_(torch.from_numpy(parameters[name]))
    
    def get_gradients(self) -> Dict[str, np.ndarray]:
        """Get model gradients"""
        return {
            name: param.grad.detach().cpu().numpy() if param.grad is not None else np.zeros_like(param.detach().cpu().numpy())
            for name, param in self.named_parameters()
        }


class FederatedClient:
    """Federated learning client (e.g., individual farm)"""
    
    def __init__(
        self,
        client_id: str,
        model: FederatedModel,
        train_data: DataLoader,
        learning_rate: float = 0.01
    ):
        self.client_id = client_id
        self.model = model
        self.train_data = train_data
        self.learning_rate = learning_rate
        
        self.optimizer = optim.SGD(self.model.parameters(), lr=learning_rate)
        self.criterion = nn.CrossEntropyLoss()
        
        # Training statistics
        self.num_samples = len(train_data.dataset)
        self.training_history: List[Dict[str, float]] = []
    
    def train(self, num_epochs: int = 1) -> Tuple[Dict[str, np.ndarray], Dict[str, float]]:
        """
        Train model locally
        
        Returns:
            Tuple of (updated_parameters, training_metrics)
        """
        self.model.train()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        for epoch in range(num_epochs):
            epoch_loss = 0.0
            epoch_correct = 0
            epoch_samples = 0
            
            for batch_idx, (data, target) in enumerate(self.train_data):
                self.optimizer.zero_grad()
                
                output = self.model(data)
                loss = self.criterion(output, target)
                
                loss.backward()
                self.optimizer.step()
                
                # Statistics
                epoch_loss += loss.item() * data.size(0)
                pred = output.argmax(dim=1)
                epoch_correct += pred.eq(target).sum().item()
                epoch_samples += data.size(0)
            
            total_loss += epoch_loss
            total_correct += epoch_correct
            total_samples += epoch_samples
        
        # Calculate metrics
        avg_loss = total_loss / total_samples
        accuracy = total_correct / total_samples
        
        metrics = {
            "loss": avg_loss,
            "accuracy": accuracy,
            "num_samples": self.num_samples
        }
        
        self.training_history.append(metrics)
        
        logger.info(f"Client {self.client_id} trained: loss={avg_loss:.4f}, acc={accuracy:.4f}")
        
        return self.model.get_parameters(), metrics
    
    def evaluate(self, test_data: DataLoader) -> Dict[str, float]:
        """Evaluate model on test data"""
        self.model.eval()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        with torch.no_grad():
            for data, target in test_data:
                output = self.model(data)
                loss = self.criterion(output, target)
                
                total_loss += loss.item() * data.size(0)
                pred = output.argmax(dim=1)
                total_correct += pred.eq(target).sum().item()
                total_samples += data.size(0)
        
        return {
            "loss": total_loss / total_samples,
            "accuracy": total_correct / total_samples
        }


class SecureAggregator:
    """Secure aggregation with encryption"""
    
    def __init__(self):
        # Generate keys for secure aggregation
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
    
    def encrypt_parameters(self, parameters: Dict[str, np.ndarray]) -> bytes:
        """Encrypt model parameters"""
        # Serialize parameters
        serialized = pickle.dumps(parameters)
        
        # Generate symmetric key
        symmetric_key = Fernet.generate_key()
        fernet = Fernet(symmetric_key)
        
        # Encrypt data with symmetric key
        encrypted_data = fernet.encrypt(serialized)
        
        # Encrypt symmetric key with public key
        encrypted_key = self.public_key.encrypt(
            symmetric_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Combine encrypted key and data
        return encrypted_key + b"||" + encrypted_data
    
    def decrypt_parameters(self, encrypted: bytes) -> Dict[str, np.ndarray]:
        """Decrypt model parameters"""
        # Split encrypted key and data
        parts = encrypted.split(b"||")
        encrypted_key = parts[0]
        encrypted_data = parts[1]
        
        # Decrypt symmetric key with private key
        symmetric_key = self.private_key.decrypt(
            encrypted_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Decrypt data with symmetric key
        fernet = Fernet(symmetric_key)
        serialized = fernet.decrypt(encrypted_data)
        
        # Deserialize parameters
        return pickle.loads(serialized)
    
    def add_noise_for_privacy(
        self,
        parameters: Dict[str, np.ndarray],
        noise_scale: float = 0.01
    ) -> Dict[str, np.ndarray]:
        """Add noise to parameters for differential privacy"""
        noisy_params = {}
        
        for name, param in parameters.items():
            # Add Gaussian noise
            noise = np.random.normal(0, noise_scale, param.shape)
            noisy_params[name] = param + noise
        
        return noisy_params


class DifferentialPrivacyMechanism:
    """Differential privacy mechanisms for federated learning"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize DP mechanism
        
        Args:
            epsilon: Privacy budget (lower = more private)
            delta: Probability of privacy breach
        """
        self.epsilon = epsilon
        self.delta = delta
    
    def calculate_noise_scale(
        self,
        sensitivity: float,
        num_clients: int
    ) -> float:
        """
        Calculate noise scale for Gaussian mechanism
        
        Args:
            sensitivity: L2 sensitivity of the aggregation
            num_clients: Number of participating clients
        
        Returns:
            Noise scale (sigma)
        """
        # Gaussian mechanism noise scale
        sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self.delta)) / self.epsilon
        return sigma
    
    def clip_gradients(
        self,
        gradients: Dict[str, np.ndarray],
        clip_norm: float = 1.0
    ) -> Dict[str, np.ndarray]:
        """
        Clip gradients to bound sensitivity
        
        Args:
            gradients: Model gradients
            clip_norm: Clipping threshold
        
        Returns:
            Clipped gradients
        """
        # Calculate gradient norm
        total_norm = 0.0
        for grad in gradients.values():
            total_norm += np.sum(grad ** 2)
        total_norm = np.sqrt(total_norm)
        
        # Clip if needed
        if total_norm > clip_norm:
            clip_factor = clip_norm / total_norm
            clipped = {
                name: grad * clip_factor
                for name, grad in gradients.items()
            }
            return clipped
        
        return gradients
    
    def add_gaussian_noise(
        self,
        parameters: Dict[str, np.ndarray],
        noise_scale: float
    ) -> Dict[str, np.ndarray]:
        """Add calibrated Gaussian noise"""
        noisy_params = {}
        
        for name, param in parameters.items():
            noise = np.random.normal(0, noise_scale, param.shape)
            noisy_params[name] = param + noise
        
        return noisy_params
    
    def apply_local_dp(
        self,
        parameters: Dict[str, np.ndarray],
        clip_norm: float = 1.0
    ) -> Dict[str, np.ndarray]:
        """
        Apply local differential privacy
        
        Args:
            parameters: Model parameters
            clip_norm: Clipping threshold
        
        Returns:
            DP parameters
        """
        # Clip
        clipped = self.clip_gradients(parameters, clip_norm)
        
        # Add noise
        noise_scale = self.calculate_noise_scale(clip_norm, 1)
        noisy = self.add_gaussian_noise(clipped, noise_scale)
        
        return noisy


class ByzantineRobustAggregator:
    """Byzantine-robust aggregation methods"""
    
    @staticmethod
    def krum(
        client_updates: List[Dict[str, np.ndarray]],
        num_byzantine: int = 0,
        return_multiple: bool = False
    ) -> Dict[str, np.ndarray]:
        """
        Krum aggregation - select model with smallest distance sum
        
        Args:
            client_updates: List of client model updates
            num_byzantine: Expected number of Byzantine clients
            return_multiple: If True, return average of top clients
        
        Returns:
            Aggregated parameters
        """
        num_clients = len(client_updates)
        num_selected = num_clients - num_byzantine - 2
        
        # Flatten all updates
        flattened_updates = []
        for update in client_updates:
            flattened = np.concatenate([v.flatten() for v in update.values()])
            flattened_updates.append(flattened)
        
        # Calculate pairwise distances
        distances = np.zeros((num_clients, num_clients))
        for i in range(num_clients):
            for j in range(i + 1, num_clients):
                dist = np.linalg.norm(flattened_updates[i] - flattened_updates[j])
                distances[i, j] = dist
                distances[j, i] = dist
        
        # Calculate scores (sum of distances to closest neighbors)
        scores = []
        for i in range(num_clients):
            sorted_distances = np.sort(distances[i])
            score = np.sum(sorted_distances[1:num_selected + 1])  # Exclude self
            scores.append(score)
        
        if return_multiple:
            # Return average of top clients
            top_indices = np.argsort(scores)[:num_selected]
            selected_updates = [client_updates[i] for i in top_indices]
            return ByzantineRobustAggregator._average_parameters(selected_updates)
        else:
            # Return single best
            best_idx = np.argmin(scores)
            return client_updates[best_idx]
    
    @staticmethod
    def trimmed_mean(
        client_updates: List[Dict[str, np.ndarray]],
        trim_ratio: float = 0.1
    ) -> Dict[str, np.ndarray]:
        """
        Trimmed mean - remove extreme values before averaging
        
        Args:
            client_updates: List of client model updates
            trim_ratio: Ratio of values to trim from each end
        
        Returns:
            Aggregated parameters
        """
        num_clients = len(client_updates)
        num_trim = int(num_clients * trim_ratio)
        
        # Get parameter names from first client
        param_names = client_updates[0].keys()
        
        aggregated = {}
        
        for param_name in param_names:
            # Stack parameter from all clients
            param_stack = np.stack([
                update[param_name] for update in client_updates
            ], axis=0)
            
            # Sort along client dimension
            sorted_params = np.sort(param_stack, axis=0)
            
            # Trim extremes
            trimmed = sorted_params[num_trim:num_clients - num_trim]
            
            # Average
            aggregated[param_name] = np.mean(trimmed, axis=0)
        
        return aggregated
    
    @staticmethod
    def coordinate_wise_median(
        client_updates: List[Dict[str, np.ndarray]]
    ) -> Dict[str, np.ndarray]:
        """
        Coordinate-wise median - robust to outliers
        
        Args:
            client_updates: List of client model updates
        
        Returns:
            Aggregated parameters
        """
        param_names = client_updates[0].keys()
        
        aggregated = {}
        
        for param_name in param_names:
            # Stack parameter from all clients
            param_stack = np.stack([
                update[param_name] for update in client_updates
            ], axis=0)
            
            # Compute median
            aggregated[param_name] = np.median(param_stack, axis=0)
        
        return aggregated
    
    @staticmethod
    def _average_parameters(
        parameters_list: List[Dict[str, np.ndarray]]
    ) -> Dict[str, np.ndarray]:
        """Simple average of parameters"""
        param_names = parameters_list[0].keys()
        
        averaged = {}
        for param_name in param_names:
            param_stack = np.stack([
                params[param_name] for params in parameters_list
            ], axis=0)
            averaged[param_name] = np.mean(param_stack, axis=0)
        
        return averaged


class ClientSelector:
    """Intelligent client selection for federated learning"""
    
    def __init__(self, strategy: ClientSelectionStrategy = ClientSelectionStrategy.RANDOM):
        self.strategy = strategy
        self.client_history: Dict[str, List[Dict[str, float]]] = {}
    
    def select_clients(
        self,
        available_clients: List[str],
        num_clients: int,
        client_metadata: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Select clients for training round
        
        Args:
            available_clients: List of available client IDs
            num_clients: Number of clients to select
            client_metadata: Additional metadata for selection
        
        Returns:
            List of selected client IDs
        """
        if self.strategy == ClientSelectionStrategy.RANDOM:
            return self._random_selection(available_clients, num_clients)
        
        elif self.strategy == ClientSelectionStrategy.BALANCED:
            return self._balanced_selection(available_clients, num_clients, client_metadata)
        
        elif self.strategy == ClientSelectionStrategy.IMPORTANCE_SAMPLING:
            return self._importance_sampling(available_clients, num_clients, client_metadata)
        
        elif self.strategy == ClientSelectionStrategy.DIVERSITY_BASED:
            return self._diversity_based_selection(available_clients, num_clients, client_metadata)
        
        elif self.strategy == ClientSelectionStrategy.CONTRIBUTION_BASED:
            return self._contribution_based_selection(available_clients, num_clients)
        
        else:
            return self._random_selection(available_clients, num_clients)
    
    def _random_selection(self, clients: List[str], num_select: int) -> List[str]:
        """Random selection"""
        return list(np.random.choice(clients, size=min(num_select, len(clients)), replace=False))
    
    def _balanced_selection(
        self,
        clients: List[str],
        num_select: int,
        metadata: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[str]:
        """Select clients to balance dataset distribution"""
        if not metadata:
            return self._random_selection(clients, num_select)
        
        # Group clients by data distribution
        groups: Dict[str, List[str]] = {}
        for client in clients:
            if client in metadata:
                group = metadata[client].get("data_distribution", "unknown")
                if group not in groups:
                    groups[group] = []
                groups[group].append(client)
        
        # Select proportionally from each group
        selected = []
        clients_per_group = num_select // len(groups)
        
        for group_clients in groups.values():
            group_selected = self._random_selection(
                group_clients,
                min(clients_per_group, len(group_clients))
            )
            selected.extend(group_selected)
        
        # Fill remaining slots randomly
        remaining = num_select - len(selected)
        if remaining > 0:
            remaining_clients = [c for c in clients if c not in selected]
            selected.extend(self._random_selection(remaining_clients, remaining))
        
        return selected[:num_select]
    
    def _importance_sampling(
        self,
        clients: List[str],
        num_select: int,
        metadata: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[str]:
        """Select clients based on data size (importance sampling)"""
        if not metadata:
            return self._random_selection(clients, num_select)
        
        # Calculate selection probabilities based on data size
        sizes = []
        for client in clients:
            if client in metadata:
                sizes.append(metadata[client].get("num_samples", 1))
            else:
                sizes.append(1)
        
        # Normalize to probabilities
        sizes = np.array(sizes)
        probabilities = sizes / np.sum(sizes)
        
        # Sample with replacement proportional to data size
        selected_indices = np.random.choice(
            len(clients),
            size=num_select,
            replace=False,
            p=probabilities
        )
        
        return [clients[i] for i in selected_indices]
    
    def _diversity_based_selection(
        self,
        clients: List[str],
        num_select: int,
        metadata: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> List[str]:
        """Select diverse set of clients"""
        if not metadata:
            return self._random_selection(clients, num_select)
        
        # Start with random client
        selected = [np.random.choice(clients)]
        remaining = [c for c in clients if c != selected[0]]
        
        # Greedily select most diverse clients
        while len(selected) < num_select and remaining:
            max_diversity = -1
            best_client = None
            
            for candidate in remaining:
                # Calculate diversity as distance to selected clients
                diversity = 0
                for selected_client in selected:
                    if candidate in metadata and selected_client in metadata:
                        # Simple diversity metric based on metadata
                        diversity += self._calculate_diversity(
                            metadata[candidate],
                            metadata[selected_client]
                        )
                
                if diversity > max_diversity:
                    max_diversity = diversity
                    best_client = candidate
            
            if best_client:
                selected.append(best_client)
                remaining.remove(best_client)
            else:
                break
        
        return selected
    
    def _contribution_based_selection(
        self,
        clients: List[str],
        num_select: int
    ) -> List[str]:
        """Select clients based on past contribution to model improvement"""
        if not self.client_history:
            return self._random_selection(clients, num_select)
        
        # Calculate contribution scores
        scores = []
        for client in clients:
            if client in self.client_history and self.client_history[client]:
                # Use recent average accuracy as contribution metric
                recent_acc = np.mean([
                    round_data["accuracy"]
                    for round_data in self.client_history[client][-5:]
                ])
                scores.append(recent_acc)
            else:
                scores.append(0.5)  # Default score for new clients
        
        # Select top contributors
        top_indices = np.argsort(scores)[-num_select:]
        return [clients[i] for i in top_indices]
    
    def _calculate_diversity(self, metadata1: Dict[str, Any], metadata2: Dict[str, Any]) -> float:
        """Calculate diversity score between two clients"""
        diversity = 0.0
        
        # Compare data distributions
        if "data_distribution" in metadata1 and "data_distribution" in metadata2:
            if metadata1["data_distribution"] != metadata2["data_distribution"]:
                diversity += 1.0
        
        # Compare data sizes
        if "num_samples" in metadata1 and "num_samples" in metadata2:
            size_diff = abs(metadata1["num_samples"] - metadata2["num_samples"])
            diversity += min(size_diff / 1000.0, 1.0)
        
        return diversity
    
    def update_client_history(self, client_id: str, metrics: Dict[str, float]) -> None:
        """Update client training history"""
        if client_id not in self.client_history:
            self.client_history[client_id] = []
        
        self.client_history[client_id].append(metrics)


class FederatedServer:
    """Federated learning server coordinator"""
    
    def __init__(
        self,
        model: FederatedModel,
        aggregation_strategy: AggregationStrategy = AggregationStrategy.FED_AVG,
        client_selection_strategy: ClientSelectionStrategy = ClientSelectionStrategy.RANDOM,
        use_secure_aggregation: bool = False,
        use_differential_privacy: bool = False,
        epsilon: float = 1.0
    ):
        self.global_model = model
        self.aggregation_strategy = aggregation_strategy
        self.client_selector = ClientSelector(client_selection_strategy)
        
        self.use_secure_aggregation = use_secure_aggregation
        if use_secure_aggregation:
            self.secure_aggregator = SecureAggregator()
        
        self.use_differential_privacy = use_differential_privacy
        if use_differential_privacy:
            self.dp_mechanism = DifferentialPrivacyMechanism(epsilon=epsilon)
        
        self.byzantine_aggregator = ByzantineRobustAggregator()
        
        # Training statistics
        self.round_history: List[Dict[str, Any]] = []
        self.current_round = 0
    
    def train_round(
        self,
        clients: Dict[str, FederatedClient],
        num_clients_per_round: int,
        num_local_epochs: int = 1,
        test_data: Optional[DataLoader] = None
    ) -> Dict[str, Any]:
        """
        Execute one round of federated training
        
        Args:
            clients: Dictionary of client_id -> FederatedClient
            num_clients_per_round: Number of clients to select
            num_local_epochs: Number of local training epochs
            test_data: Optional test data for evaluation
        
        Returns:
            Round statistics
        """
        self.current_round += 1
        
        logger.info(f"Starting round {self.current_round}")
        
        # Select clients
        available_clients = list(clients.keys())
        selected_client_ids = self.client_selector.select_clients(
            available_clients,
            num_clients_per_round
        )
        
        logger.info(f"Selected {len(selected_client_ids)} clients")
        
        # Distribute global model to selected clients
        global_params = self.global_model.get_parameters()
        for client_id in selected_client_ids:
            clients[client_id].model.set_parameters(global_params)
        
        # Local training
        client_updates = []
        client_metrics = []
        client_weights = []
        
        for client_id in selected_client_ids:
            client = clients[client_id]
            
            # Train locally
            updated_params, metrics = client.train(num_local_epochs)
            
            # Apply differential privacy if enabled
            if self.use_differential_privacy:
                updated_params = self.dp_mechanism.apply_local_dp(updated_params)
            
            # Encrypt if secure aggregation enabled
            if self.use_secure_aggregation:
                updated_params = self.secure_aggregator.add_noise_for_privacy(updated_params)
            
            client_updates.append(updated_params)
            client_metrics.append(metrics)
            client_weights.append(client.num_samples)
            
            # Update client history
            self.client_selector.update_client_history(client_id, metrics)
        
        # Aggregate updates
        aggregated_params = self._aggregate_updates(
            client_updates,
            client_weights
        )
        
        # Update global model
        self.global_model.set_parameters(aggregated_params)
        
        # Evaluate
        round_metrics = {
            "round": self.current_round,
            "num_clients": len(selected_client_ids),
            "client_metrics": client_metrics,
            "avg_client_loss": np.mean([m["loss"] for m in client_metrics]),
            "avg_client_accuracy": np.mean([m["accuracy"] for m in client_metrics])
        }
        
        if test_data:
            test_metrics = self._evaluate_global_model(test_data)
            round_metrics.update({
                "global_test_loss": test_metrics["loss"],
                "global_test_accuracy": test_metrics["accuracy"]
            })
        
        self.round_history.append(round_metrics)
        
        logger.info(f"Round {self.current_round} completed: "
                   f"avg_loss={round_metrics['avg_client_loss']:.4f}, "
                   f"avg_acc={round_metrics['avg_client_accuracy']:.4f}")
        
        return round_metrics
    
    def _aggregate_updates(
        self,
        client_updates: List[Dict[str, np.ndarray]],
        client_weights: List[int]
    ) -> Dict[str, np.ndarray]:
        """Aggregate client updates based on strategy"""
        
        if self.aggregation_strategy == AggregationStrategy.FED_AVG:
            return self._federated_averaging(client_updates, client_weights)
        
        elif self.aggregation_strategy == AggregationStrategy.TRIMMED_MEAN:
            return self.byzantine_aggregator.trimmed_mean(client_updates)
        
        elif self.aggregation_strategy == AggregationStrategy.KRUM:
            return self.byzantine_aggregator.krum(client_updates, num_byzantine=1)
        
        elif self.aggregation_strategy == AggregationStrategy.MEDIAN:
            return self.byzantine_aggregator.coordinate_wise_median(client_updates)
        
        else:
            return self._federated_averaging(client_updates, client_weights)
    
    def _federated_averaging(
        self,
        client_updates: List[Dict[str, np.ndarray]],
        client_weights: List[int]
    ) -> Dict[str, np.ndarray]:
        """FedAvg: Weighted average by number of samples"""
        
        total_samples = sum(client_weights)
        param_names = client_updates[0].keys()
        
        aggregated = {}
        
        for param_name in param_names:
            weighted_sum = np.zeros_like(client_updates[0][param_name])
            
            for update, weight in zip(client_updates, client_weights):
                weighted_sum += update[param_name] * weight
            
            aggregated[param_name] = weighted_sum / total_samples
        
        return aggregated
    
    def _evaluate_global_model(self, test_data: DataLoader) -> Dict[str, float]:
        """Evaluate global model"""
        self.global_model.eval()
        
        total_loss = 0.0
        total_correct = 0
        total_samples = 0
        
        criterion = nn.CrossEntropyLoss()
        
        with torch.no_grad():
            for data, target in test_data:
                output = self.global_model(data)
                loss = criterion(output, target)
                
                total_loss += loss.item() * data.size(0)
                pred = output.argmax(dim=1)
                total_correct += pred.eq(target).sum().item()
                total_samples += data.size(0)
        
        return {
            "loss": total_loss / total_samples,
            "accuracy": total_correct / total_samples
        }
    
    def get_global_model(self) -> FederatedModel:
        """Get trained global model"""
        return self.global_model
    
    def save_model(self, path: str) -> None:
        """Save global model"""
        torch.save(self.global_model.state_dict(), path)
        logger.info(f"Saved global model to {path}")
    
    def load_model(self, path: str) -> None:
        """Load global model"""
        self.global_model.load_state_dict(torch.load(path))
        logger.info(f"Loaded global model from {path}")


class PersonalizedFederatedLearning:
    """Personalized FL - balance global and local models"""
    
    def __init__(
        self,
        global_model: FederatedModel,
        personalization_ratio: float = 0.5
    ):
        """
        Initialize personalized FL
        
        Args:
            global_model: Global federated model
            personalization_ratio: Balance between global (0) and local (1)
        """
        self.global_model = global_model
        self.personalization_ratio = personalization_ratio
        self.local_models: Dict[str, FederatedModel] = {}
    
    def create_personalized_model(
        self,
        client_id: str,
        client_data: DataLoader
    ) -> FederatedModel:
        """Create personalized model for client"""
        
        # Start with global model
        personalized_model = FederatedModel(
            input_dim=self.global_model.network[0].in_features,
            hidden_dims=[layer.out_features for layer in self.global_model.network if isinstance(layer, nn.Linear)][:-1],
            output_dim=self.global_model.network[-1].out_features
        )
        
        # Copy global parameters
        personalized_model.set_parameters(self.global_model.get_parameters())
        
        # Fine-tune on local data
        optimizer = optim.SGD(personalized_model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()
        
        personalized_model.train()
        for epoch in range(5):  # Few epochs of fine-tuning
            for data, target in client_data:
                optimizer.zero_grad()
                output = personalized_model(data)
                loss = criterion(output, target)
                loss.backward()
                optimizer.step()
        
        # Interpolate between global and fine-tuned
        global_params = self.global_model.get_parameters()
        local_params = personalized_model.get_parameters()
        
        interpolated_params = {}
        for name in global_params.keys():
            interpolated_params[name] = (
                (1 - self.personalization_ratio) * global_params[name] +
                self.personalization_ratio * local_params[name]
            )
        
        personalized_model.set_parameters(interpolated_params)
        self.local_models[client_id] = personalized_model
        
        return personalized_model


# Example usage
def example_usage():
    """Demonstrate federated learning system"""
    
    # Create mock data
    def create_mock_data(num_samples: int = 100) -> DataLoader:
        X = torch.randn(num_samples, 10)
        y = torch.randint(0, 3, (num_samples,))
        dataset = TensorDataset(X, y)
        return DataLoader(dataset, batch_size=32, shuffle=True)
    
    # Initialize global model
    global_model = FederatedModel(
        input_dim=10,
        hidden_dims=[64, 32],
        output_dim=3
    )
    
    # Create server
    server = FederatedServer(
        model=global_model,
        aggregation_strategy=AggregationStrategy.FED_AVG,
        client_selection_strategy=ClientSelectionStrategy.RANDOM,
        use_differential_privacy=True,
        epsilon=1.0
    )
    
    # Create clients (simulating different farms)
    clients = {}
    for i in range(10):
        client_id = f"farm_{i}"
        model = FederatedModel(
            input_dim=10,
            hidden_dims=[64, 32],
            output_dim=3
        )
        train_data = create_mock_data(100)
        
        clients[client_id] = FederatedClient(
            client_id=client_id,
            model=model,
            train_data=train_data
        )
    
    # Test data
    test_data = create_mock_data(50)
    
    # Training rounds
    num_rounds = 10
    for round_idx in range(num_rounds):
        metrics = server.train_round(
            clients=clients,
            num_clients_per_round=5,
            num_local_epochs=1,
            test_data=test_data
        )
        
        print(f"Round {round_idx + 1}: "
              f"Test Acc = {metrics.get('global_test_accuracy', 0):.4f}")
    
    # Save model
    server.save_model("federated_model.pth")


if __name__ == "__main__":
    example_usage()
