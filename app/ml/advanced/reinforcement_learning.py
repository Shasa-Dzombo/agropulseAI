"""
Reinforcement Learning for Agricultural Optimization

Intelligent decision-making systems using RL algorithms.

Features:
- Deep Q-Networks (DQN) for irrigation scheduling
- Proximal Policy Optimization (PPO) for resource allocation
- Multi-armed bandits for crop selection
- Model-based RL for planning
- Actor-Critic methods
- Reward shaping
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import json
from collections import deque
import random

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    from torch.distributions import Categorical
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.warning("PyTorch not available")


logger = logging.getLogger(__name__)


@dataclass
class Experience:
    """Single experience for replay buffer"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool
    metadata: Dict = field(default_factory=dict)


@dataclass
class TrainingMetrics:
    """Training metrics"""
    episode: int
    total_reward: float
    average_reward: float
    epsilon: float
    loss: float
    steps: int
    timestamp: datetime = field(default_factory=datetime.now)


class DQNetwork(nn.Module):
    """Deep Q-Network architecture"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dims: List[int] = [256, 256]):
        """
        Initialize DQN
        
        Args:
            state_dim: State space dimension
            action_dim: Action space dimension
            hidden_dims: Hidden layer dimensions
        """
        super(DQNetwork, self).__init__()
        
        layers = []
        input_dim = state_dim
        
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(input_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.2))
            input_dim = hidden_dim
        
        layers.append(nn.Linear(input_dim, action_dim))
        
        self.network = nn.Sequential(*layers)
    
    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """Forward pass"""
        return self.network(state)


class ReplayBuffer:
    """Experience replay buffer"""
    
    def __init__(self, capacity: int = 10000):
        """
        Initialize replay buffer
        
        Args:
            capacity: Maximum buffer size
        """
        self.buffer = deque(maxlen=capacity)
    
    def push(self, experience: Experience):
        """Add experience to buffer"""
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Sample random batch"""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self) -> int:
        return len(self.buffer)


class IrrigationDQNAgent:
    """
    DQN agent for optimal irrigation scheduling
    
    State: soil moisture, weather forecast, crop stage, water availability
    Actions: no irrigation, light irrigation, medium irrigation, heavy irrigation
    Reward: crop yield - water cost - stress penalty
    """
    
    def __init__(
        self,
        state_dim: int = 10,
        action_dim: int = 4,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        buffer_capacity: int = 10000,
        batch_size: int = 64,
        target_update_freq: int = 10
    ):
        """
        Initialize DQN agent
        
        Args:
            state_dim: State space dimension
            action_dim: Action space dimension
            learning_rate: Learning rate
            gamma: Discount factor
            epsilon_start: Starting exploration rate
            epsilon_end: Minimum exploration rate
            epsilon_decay: Exploration decay rate
            buffer_capacity: Replay buffer capacity
            batch_size: Training batch size
            target_update_freq: Target network update frequency
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Q-networks
        self.q_network = DQNetwork(state_dim, action_dim).to(self.device)
        self.target_network = DQNetwork(state_dim, action_dim).to(self.device)
        self.target_network.load_state_dict(self.q_network.state_dict())
        
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=learning_rate)
        self.replay_buffer = ReplayBuffer(buffer_capacity)
        
        self.training_step = 0
        self.episode_count = 0
        
        logger.info(f"IrrigationDQNAgent initialized on {self.device}")
    
    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select action using epsilon-greedy policy
        
        Args:
            state: Current state
            training: Whether in training mode
            
        Returns:
            Selected action
        """
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.q_network(state_tensor)
            return q_values.argmax(1).item()
    
    def train_step(self) -> float:
        """
        Perform one training step
        
        Returns:
            Training loss
        """
        if len(self.replay_buffer) < self.batch_size:
            return 0.0
        
        # Sample batch
        experiences = self.replay_buffer.sample(self.batch_size)
        
        states = torch.FloatTensor([e.state for e in experiences]).to(self.device)
        actions = torch.LongTensor([e.action for e in experiences]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in experiences]).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in experiences]).to(self.device)
        dones = torch.FloatTensor([e.done for e in experiences]).to(self.device)
        
        # Compute Q-values
        current_q_values = self.q_network(states).gather(1, actions.unsqueeze(1))
        
        # Compute target Q-values
        with torch.no_grad():
            next_q_values = self.target_network(next_states).max(1)[0]
            target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        # Compute loss
        loss = F.mse_loss(current_q_values.squeeze(), target_q_values)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_network.parameters(), 1.0)
        self.optimizer.step()
        
        # Update target network
        self.training_step += 1
        if self.training_step % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.q_network.state_dict())
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
        return loss.item()
    
    def store_experience(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool
    ):
        """Store experience in replay buffer"""
        experience = Experience(state, action, reward, next_state, done)
        self.replay_buffer.push(experience)
    
    def save_model(self, filepath: str):
        """Save model weights"""
        torch.save({
            'q_network': self.q_network.state_dict(),
            'target_network': self.target_network.state_dict(),
            'optimizer': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'training_step': self.training_step
        }, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """Load model weights"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.q_network.load_state_dict(checkpoint['q_network'])
        self.target_network.load_state_dict(checkpoint['target_network'])
        self.optimizer.load_state_dict(checkpoint['optimizer'])
        self.epsilon = checkpoint['epsilon']
        self.training_step = checkpoint['training_step']
        logger.info(f"Model loaded from {filepath}")


class ActorCriticNetwork(nn.Module):
    """Actor-Critic network for PPO"""
    
    def __init__(self, state_dim: int, action_dim: int, hidden_dim: int = 256):
        """
        Initialize Actor-Critic network
        
        Args:
            state_dim: State space dimension
            action_dim: Action space dimension
            hidden_dim: Hidden layer dimension
        """
        super(ActorCriticNetwork, self).__init__()
        
        # Shared layers
        self.shared = nn.Sequential(
            nn.Linear(state_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU()
        )
        
        # Actor head
        self.actor = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, action_dim),
            nn.Softmax(dim=-1)
        )
        
        # Critic head
        self.critic = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1)
        )
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        
        Returns:
            (action_probs, value)
        """
        shared = self.shared(state)
        action_probs = self.actor(shared)
        value = self.critic(shared)
        return action_probs, value


class ResourceAllocationPPOAgent:
    """
    PPO agent for agricultural resource allocation
    
    State: available resources, crop demands, market prices, weather
    Actions: resource distribution across crops/fields
    Reward: total profit - resource costs
    """
    
    def __init__(
        self,
        state_dim: int = 20,
        action_dim: int = 10,
        learning_rate: float = 0.0003,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        epochs: int = 10,
        batch_size: int = 64
    ):
        """
        Initialize PPO agent
        
        Args:
            state_dim: State space dimension
            action_dim: Action space dimension
            learning_rate: Learning rate
            gamma: Discount factor
            gae_lambda: GAE lambda parameter
            clip_epsilon: PPO clipping parameter
            epochs: Training epochs per update
            batch_size: Batch size
        """
        if not TORCH_AVAILABLE:
            raise RuntimeError("PyTorch not available")
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.epochs = epochs
        self.batch_size = batch_size
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.network = ActorCriticNetwork(state_dim, action_dim).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)
        
        self.trajectory_buffer = []
        
        logger.info(f"ResourceAllocationPPOAgent initialized on {self.device}")
    
    def select_action(self, state: np.ndarray) -> Tuple[int, float, float]:
        """
        Select action using current policy
        
        Args:
            state: Current state
            
        Returns:
            (action, log_prob, value)
        """
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            action_probs, value = self.network(state_tensor)
            
            dist = Categorical(action_probs)
            action = dist.sample()
            log_prob = dist.log_prob(action)
        
        return action.item(), log_prob.item(), value.item()
    
    def compute_gae(
        self,
        rewards: List[float],
        values: List[float],
        dones: List[bool]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute Generalized Advantage Estimation
        
        Args:
            rewards: List of rewards
            values: List of values
            dones: List of done flags
            
        Returns:
            (advantages, returns)
        """
        advantages = []
        gae = 0
        
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0
            else:
                next_value = values[t + 1]
            
            delta = rewards[t] + self.gamma * next_value * (1 - dones[t]) - values[t]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[t]) * gae
            advantages.insert(0, gae)
        
        advantages = np.array(advantages)
        returns = advantages + np.array(values)
        
        return advantages, returns
    
    def update(self):
        """Update policy using PPO"""
        if not self.trajectory_buffer:
            return
        
        # Extract trajectory data
        states = torch.FloatTensor([t['state'] for t in self.trajectory_buffer]).to(self.device)
        actions = torch.LongTensor([t['action'] for t in self.trajectory_buffer]).to(self.device)
        old_log_probs = torch.FloatTensor([t['log_prob'] for t in self.trajectory_buffer]).to(self.device)
        rewards = [t['reward'] for t in self.trajectory_buffer]
        values = [t['value'] for t in self.trajectory_buffer]
        dones = [t['done'] for t in self.trajectory_buffer]
        
        # Compute advantages and returns
        advantages, returns = self.compute_gae(rewards, values, dones)
        advantages = torch.FloatTensor(advantages).to(self.device)
        returns = torch.FloatTensor(returns).to(self.device)
        
        # Normalize advantages
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # PPO update
        for _ in range(self.epochs):
            # Forward pass
            action_probs, new_values = self.network(states)
            dist = Categorical(action_probs)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Compute ratios
            ratios = torch.exp(new_log_probs - old_log_probs)
            
            # Compute surrogate losses
            surr1 = ratios * advantages
            surr2 = torch.clamp(ratios, 1 - self.clip_epsilon, 1 + self.clip_epsilon) * advantages
            
            # Compute losses
            actor_loss = -torch.min(surr1, surr2).mean()
            critic_loss = F.mse_loss(new_values.squeeze(), returns)
            
            # Total loss
            loss = actor_loss + 0.5 * critic_loss - 0.01 * entropy
            
            # Optimize
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), 0.5)
            self.optimizer.step()
        
        # Clear buffer
        self.trajectory_buffer = []
        
        logger.info(f"PPO update completed")
    
    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        log_prob: float,
        value: float,
        done: bool
    ):
        """Store transition in trajectory buffer"""
        self.trajectory_buffer.append({
            'state': state,
            'action': action,
            'reward': reward,
            'log_prob': log_prob,
            'value': value,
            'done': done
        })


class MultiArmedBandit:
    """
    Multi-armed bandit for crop selection
    
    Each arm represents a crop variety.
    Reward is based on yield and market price.
    """
    
    def __init__(
        self,
        n_arms: int = 10,
        algorithm: str = 'ucb'  # 'ucb', 'thompson', 'epsilon_greedy'
    ):
        """
        Initialize multi-armed bandit
        
        Args:
            n_arms: Number of arms (crop varieties)
            algorithm: Bandit algorithm
        """
        self.n_arms = n_arms
        self.algorithm = algorithm
        
        self.counts = np.zeros(n_arms)
        self.values = np.zeros(n_arms)
        self.total_count = 0
        
        # For Thompson sampling
        self.alpha = np.ones(n_arms)
        self.beta = np.ones(n_arms)
        
        logger.info(f"MultiArmedBandit initialized with {n_arms} arms using {algorithm}")
    
    def select_arm(self, epsilon: float = 0.1) -> int:
        """
        Select arm based on algorithm
        
        Args:
            epsilon: Exploration rate for epsilon-greedy
            
        Returns:
            Selected arm index
        """
        if self.algorithm == 'ucb':
            return self._select_ucb()
        elif self.algorithm == 'thompson':
            return self._select_thompson()
        elif self.algorithm == 'epsilon_greedy':
            return self._select_epsilon_greedy(epsilon)
        else:
            raise ValueError(f"Unknown algorithm: {self.algorithm}")
    
    def _select_ucb(self, c: float = 2.0) -> int:
        """Upper Confidence Bound selection"""
        if self.total_count < self.n_arms:
            return self.total_count
        
        ucb_values = self.values + c * np.sqrt(
            np.log(self.total_count + 1) / (self.counts + 1)
        )
        return np.argmax(ucb_values)
    
    def _select_thompson(self) -> int:
        """Thompson Sampling selection"""
        samples = np.random.beta(self.alpha, self.beta)
        return np.argmax(samples)
    
    def _select_epsilon_greedy(self, epsilon: float) -> int:
        """Epsilon-greedy selection"""
        if random.random() < epsilon:
            return random.randint(0, self.n_arms - 1)
        return np.argmax(self.values)
    
    def update(self, arm: int, reward: float):
        """
        Update arm statistics
        
        Args:
            arm: Arm index
            reward: Observed reward
        """
        self.counts[arm] += 1
        self.total_count += 1
        
        # Update value estimate
        n = self.counts[arm]
        value = self.values[arm]
        self.values[arm] = ((n - 1) / n) * value + (1 / n) * reward
        
        # Update Beta distribution parameters for Thompson sampling
        if reward > 0.5:  # Threshold for success
            self.alpha[arm] += 1
        else:
            self.beta[arm] += 1
    
    def get_best_arm(self) -> int:
        """Get current best arm"""
        return np.argmax(self.values)
    
    def get_statistics(self) -> Dict:
        """Get bandit statistics"""
        return {
            'counts': self.counts.tolist(),
            'values': self.values.tolist(),
            'total_count': self.total_count,
            'best_arm': self.get_best_arm(),
            'best_value': np.max(self.values)
        }


class CropSelectionBandit:
    """
    Specialized bandit for crop variety selection
    
    Considers multiple factors:
    - Historical yield
    - Market prices
    - Weather patterns
    - Soil suitability
    """
    
    def __init__(
        self,
        crop_varieties: List[str],
        features_dim: int = 5
    ):
        """
        Initialize crop selection bandit
        
        Args:
            crop_varieties: List of crop variety names
            features_dim: Dimension of contextual features
        """
        self.crop_varieties = crop_varieties
        self.n_varieties = len(crop_varieties)
        self.features_dim = features_dim
        
        # Contextual bandit with linear model
        self.weights = np.zeros((self.n_varieties, features_dim))
        self.A = [np.identity(features_dim) for _ in range(self.n_varieties)]
        self.b = [np.zeros(features_dim) for _ in range(self.n_varieties)]
        
        logger.info(f"CropSelectionBandit initialized with {self.n_varieties} varieties")
    
    def select_variety(
        self,
        context: np.ndarray,
        alpha: float = 1.0
    ) -> Tuple[int, str]:
        """
        Select crop variety based on context
        
        Args:
            context: Contextual features (weather, soil, etc.)
            alpha: Exploration parameter
            
        Returns:
            (variety_index, variety_name)
        """
        ucb_scores = []
        
        for i in range(self.n_varieties):
            # Compute ridge regression estimate
            A_inv = np.linalg.inv(self.A[i])
            theta = A_inv.dot(self.b[i])
            
            # Compute UCB
            mean_reward = theta.dot(context)
            uncertainty = alpha * np.sqrt(context.dot(A_inv).dot(context))
            ucb = mean_reward + uncertainty
            
            ucb_scores.append(ucb)
        
        selected_idx = np.argmax(ucb_scores)
        return selected_idx, self.crop_varieties[selected_idx]
    
    def update(
        self,
        variety_idx: int,
        context: np.ndarray,
        reward: float
    ):
        """
        Update model with observed reward
        
        Args:
            variety_idx: Selected variety index
            context: Context features
            reward: Observed reward
        """
        self.A[variety_idx] += np.outer(context, context)
        self.b[variety_idx] += reward * context
        
        # Update weight estimate
        A_inv = np.linalg.inv(self.A[variety_idx])
        self.weights[variety_idx] = A_inv.dot(self.b[variety_idx])
